from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote

import aiohttp

API_BASE = "https://api.todoist.com/api/v1"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)
MAX_PAGE_SIZE = 200

JsonObject = dict[str, Any]


class TodoistApiError(Exception):
    """Base exception for Todoist API errors."""

    def __init__(self, message: str, status: int | None = None) -> None:
        """Initialize the error."""
        super().__init__(message)
        self.status = status


class TodoistAuthenticationError(TodoistApiError):
    """Raised when Todoist authentication fails."""


class TodoistConnectionError(TodoistApiError):
    """Raised when the Todoist API cannot be reached."""


class TodoistProjectNotFoundError(TodoistApiError):
    """Raised when the configured project cannot be found."""


class TodoistProjectAmbiguousError(TodoistApiError):
    """Raised when a project name matches multiple projects."""

    def __init__(self, project_name: str) -> None:
        """Initialize the error."""
        super().__init__(project_name)
        self.project_name = project_name


class TodoistRateLimitError(TodoistApiError):
    """Raised when the Todoist API rate-limits requests."""

    def __init__(self, retry_after: float | None = None) -> None:
        """Initialize the error."""
        super().__init__(retry_after)
        self.retry_after = retry_after


@dataclass(frozen=True, slots=True)
class TodoistProject:
    """Resolved Todoist project metadata."""

    id: str
    name: str


class TodoistApiClient:
    """Async client for the Todoist REST API."""

    def __init__(self, session: aiohttp.ClientSession, token: str) -> None:
        """Initialize the client."""
        self._session = session
        self._token = token

    async def _request(
        self, path: str, params: dict[str, Any] | None = None
    ) -> Any:
        """Issue a GET request to Todoist."""
        headers = {"Authorization": f"Bearer {self._token}"}
        url = f"{API_BASE}{path}"

        try:
            async with self._session.get(
                url,
                headers=headers,
                params=params,
                timeout=REQUEST_TIMEOUT,
            ) as response:
                if response.status in (401, 403):
                    raise TodoistAuthenticationError
                if response.status == 404:
                    raise TodoistProjectNotFoundError
                if response.status == 429:
                    raise TodoistRateLimitError(
                        _parse_retry_after(response.headers.get("Retry-After"))
                    )
                if response.status >= 400:
                    raise TodoistApiError(
                        f"Todoist API request failed with status {response.status}",
                        status=response.status,
                    )

                try:
                    return await response.json(content_type=None)
                except (aiohttp.ContentTypeError, ValueError) as err:
                    raise TodoistApiError(
                        "Unexpected Todoist API response payload"
                    ) from err
        except aiohttp.ClientError as err:
            raise TodoistConnectionError from err
        except TimeoutError as err:
            raise TodoistConnectionError from err

    async def _get_object(
        self, path: str, params: dict[str, Any] | None = None
    ) -> JsonObject:
        """Issue a GET request that returns a single JSON object."""
        payload = await self._request(path, params=params)
        if not isinstance(payload, dict):
            raise TodoistApiError("Unexpected Todoist API response payload")
        return payload

    async def _get_paginated(
        self, path: str, params: dict[str, Any] | None = None
    ) -> list[JsonObject]:
        """Collect all pages from a cursor-paginated Todoist endpoint."""
        results: list[JsonObject] = []
        base_params = dict(params or {})
        cursor: str | None = None

        while True:
            page_params = {**base_params, "limit": MAX_PAGE_SIZE}
            if cursor is not None:
                page_params["cursor"] = cursor

            payload = await self._get_object(path, params=page_params)
            page_results = payload.get("results")
            if not isinstance(page_results, list):
                raise TodoistApiError("Unexpected Todoist API response payload")

            for item in page_results:
                if not isinstance(item, dict):
                    raise TodoistApiError("Unexpected Todoist API response payload")
                results.append(item)

            next_cursor = payload.get("next_cursor")
            if next_cursor in (None, ""):
                return results
            if not isinstance(next_cursor, str):
                raise TodoistApiError("Unexpected Todoist API response payload")
            cursor = next_cursor

    async def get_project(self, project_id: str) -> JsonObject:
        """Fetch a project by ID."""
        try:
            return await self._get_object(f"/projects/{quote(project_id, safe='')}")
        except TodoistApiError as err:
            if err.status == 400:
                raise TodoistProjectNotFoundError from err
            raise

    async def list_projects(self) -> list[JsonObject]:
        """Fetch all projects available to the user."""
        return await self._get_paginated("/projects")

    async def list_sections(self, project_id: str | None = None) -> list[JsonObject]:
        """Fetch sections, optionally filtered to a project."""
        params = {"project_id": project_id} if project_id else None
        return await self._get_paginated("/sections", params=params)

    async def list_tasks(self, project_id: str | None = None) -> list[JsonObject]:
        """Fetch active tasks, optionally filtered to a project."""
        params = {"project_id": project_id} if project_id else None
        return await self._get_paginated("/tasks", params=params)

    async def async_resolve_project(
        self, project_id: str | None, project_name: str | None
    ) -> TodoistProject:
        """Resolve a project by ID or name."""
        normalized_id = project_id.strip() if project_id else ""
        normalized_name = project_name.strip() if project_name else ""

        if not normalized_id and not normalized_name:
            raise TodoistProjectNotFoundError

        if normalized_id:
            try:
                project = await self.get_project(normalized_id)
            except TodoistProjectNotFoundError:
                if not normalized_name:
                    raise
            else:
                return _normalize_project(project, normalized_id)

        projects = await self.list_projects()

        exact_matches = [
            project
            for project in projects
            if str(project.get("name", "")).strip() == normalized_name
        ]
        if len(exact_matches) == 1:
            return _normalize_project(exact_matches[0], normalized_name)
        if len(exact_matches) > 1:
            raise TodoistProjectAmbiguousError(normalized_name)

        casefold_matches = [
            project
            for project in projects
            if str(project.get("name", "")).strip().casefold()
            == normalized_name.casefold()
        ]
        if len(casefold_matches) == 1:
            return _normalize_project(casefold_matches[0], normalized_name)
        if len(casefold_matches) > 1:
            raise TodoistProjectAmbiguousError(normalized_name)

        raise TodoistProjectNotFoundError


def _normalize_project(project: JsonObject, fallback_name: str) -> TodoistProject:
    """Normalize a Todoist project payload into the integration model."""
    project_id = project.get("id")
    if project_id in (None, ""):
        raise TodoistApiError("Unexpected Todoist project payload")

    return TodoistProject(
        id=str(project_id),
        name=str(project.get("name", fallback_name)),
    )


def _parse_retry_after(retry_after: str | None) -> float | None:
    """Parse a Retry-After header into seconds."""
    if retry_after is None:
        return None

    try:
        return float(retry_after)
    except ValueError:
        pass

    try:
        retry_datetime = parsedate_to_datetime(retry_after)
    except (TypeError, ValueError, IndexError):
        return None

    return max(
        (retry_datetime - datetime.now(timezone.utc)).total_seconds(),
        0.0,
    )
