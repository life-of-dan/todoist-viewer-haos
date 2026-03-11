from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import aiohttp

API_BASE = "https://api.todoist.com/rest/v2"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)


class TodoistApiError(Exception):
    """Base exception for Todoist API errors."""


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

    async def _get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
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
                        f"Todoist API request failed with status {response.status}"
                    )

                payload = await response.json()
        except aiohttp.ClientError as err:
            raise TodoistConnectionError from err
        except TimeoutError as err:
            raise TodoistConnectionError from err

        if not isinstance(payload, list):
            raise TodoistApiError("Unexpected Todoist API response payload")

        return payload

    async def list_projects(self) -> list[dict[str, Any]]:
        """Fetch all projects available to the user."""
        return await self._get("/projects")

    async def list_sections(self, project_id: str) -> list[dict[str, Any]]:
        """Fetch all sections for a project."""
        return await self._get("/sections", params={"project_id": project_id})

    async def list_tasks(self, project_id: str) -> list[dict[str, Any]]:
        """Fetch all active tasks for a project."""
        return await self._get("/tasks", params={"project_id": project_id})

    async def async_resolve_project(
        self, project_id: str | None, project_name: str | None
    ) -> TodoistProject:
        """Resolve a project by ID or name."""
        normalized_id = project_id.strip() if project_id else ""
        normalized_name = project_name.strip() if project_name else ""

        if not normalized_id and not normalized_name:
            raise TodoistProjectNotFoundError

        projects = await self.list_projects()

        if normalized_id:
            for project in projects:
                if str(project.get("id")) == normalized_id:
                    return TodoistProject(
                        id=str(project["id"]),
                        name=str(project.get("name", normalized_id)),
                    )
            raise TodoistProjectNotFoundError

        exact_matches = [
            project
            for project in projects
            if str(project.get("name", "")).strip() == normalized_name
        ]
        if len(exact_matches) == 1:
            project = exact_matches[0]
            return TodoistProject(
                id=str(project["id"]),
                name=str(project.get("name", normalized_name)),
            )
        if len(exact_matches) > 1:
            raise TodoistProjectAmbiguousError(normalized_name)

        casefold_matches = [
            project
            for project in projects
            if str(project.get("name", "")).strip().casefold()
            == normalized_name.casefold()
        ]
        if len(casefold_matches) == 1:
            project = casefold_matches[0]
            return TodoistProject(
                id=str(project["id"]),
                name=str(project.get("name", normalized_name)),
            )
        if len(casefold_matches) > 1:
            raise TodoistProjectAmbiguousError(normalized_name)

        raise TodoistProjectNotFoundError


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
