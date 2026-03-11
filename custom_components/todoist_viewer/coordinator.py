from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any, TypedDict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    TodoistApiClient,
    TodoistApiError,
    TodoistAuthenticationError,
    TodoistConnectionError,
    TodoistProject,
    TodoistProjectAmbiguousError,
    TodoistProjectNotFoundError,
    TodoistRateLimitError,
)
from .const import (
    ALL_PROJECTS_ID,
    ALL_PROJECTS_NAME,
    CONF_ALL_PROJECTS,
    CONF_PROJECT_ID,
    CONF_PROJECT_NAME,
    CONF_TOKEN,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MIN_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)
TASK_URL_BASE = "https://app.todoist.com/app/task/"


class TodoistDueData(TypedDict, total=False):
    """Serialized due data returned by Todoist."""

    string: str
    date: str
    datetime: str
    timezone: str


class TodoistTaskData(TypedDict):
    """Normalized task data exposed by the integration."""

    id: str
    content: str
    description: str
    completed: bool
    priority: int
    labels: list[str]
    parent_id: str | None
    section_id: str | None
    project_id: str | None
    due: TodoistDueData | None
    order: int
    url: str


class TodoistSectionData(TypedDict):
    """Normalized section data exposed by the integration."""

    id: str
    name: str
    order: int


class TodoistProjectData(TypedDict):
    """Normalized project data exposed by the integration."""

    id: str
    name: str
    order: int


class TodoistCoordinatorData(TypedDict):
    """Coordinator payload for the sensor platform."""

    projects: dict[str, TodoistProjectData]
    sections: dict[str, TodoistSectionData]
    tasks: list[TodoistTaskData]


class TodoistCoordinator(DataUpdateCoordinator[TodoistCoordinatorData]):
    """Coordinator that fetches Todoist tasks for one project or all projects."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.config_entry = entry
        self.api = TodoistApiClient(
            async_get_clientsession(hass), entry.data[CONF_TOKEN]
        )
        self.all_projects = bool(entry.data.get(CONF_ALL_PROJECTS, False))
        interval = max(
            int(entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)),
            MIN_UPDATE_INTERVAL,
        )
        self.project: TodoistProject | None = None
        self.projects: dict[str, TodoistProjectData] = {}

        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}-{entry.entry_id}",
            update_interval=timedelta(seconds=interval),
            always_update=False,
        )

    async def _async_setup(self) -> None:
        """Resolve project metadata before the first refresh."""
        try:
            if self.all_projects:
                self.projects = _normalize_projects(await self.api.list_projects())
                project = TodoistProject(ALL_PROJECTS_ID, ALL_PROJECTS_NAME)
            else:
                project = await self.api.async_resolve_project(
                    self.config_entry.data.get(CONF_PROJECT_ID),
                    self.config_entry.data.get(CONF_PROJECT_NAME),
                )
                self.projects = {
                    project.id: {
                        "id": project.id,
                        "name": project.name,
                        "order": 0,
                    }
                }
        except TodoistAuthenticationError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="invalid_auth",
            ) from err
        except TodoistConnectionError as err:
            raise ConfigEntryNotReady(
                "Unable to connect to the Todoist API"
            ) from err
        except TodoistRateLimitError as err:
            retry_after = (
                f" Retry after {int(err.retry_after)} seconds."
                if err.retry_after is not None
                else ""
            )
            raise ConfigEntryNotReady(
                f"Todoist API rate limited setup.{retry_after}"
            ) from err
        except TodoistProjectAmbiguousError as err:
            raise ConfigEntryError(
                translation_domain=DOMAIN,
                translation_key="project_name_ambiguous",
                translation_placeholders={"project_name": err.project_name},
            ) from err
        except TodoistProjectNotFoundError as err:
            raise ConfigEntryError(
                translation_domain=DOMAIN,
                translation_key="project_not_found",
            ) from err
        except TodoistApiError as err:
            raise ConfigEntryNotReady("Unexpected Todoist API error") from err

        self.project = project
        self._async_update_entry_metadata(project)

    async def _async_update_data(self) -> TodoistCoordinatorData:
        """Fetch tasks and sections for the configured project."""
        if self.project is None:
            raise UpdateFailed("Todoist project metadata was not initialized")

        try:
            if self.all_projects:
                raw_projects = await self.api.list_projects()
                self.projects = _normalize_projects(raw_projects)
                sections, tasks = await _async_fetch_all_project_data(
                    self.api, list(self.projects)
                )
            else:
                sections = await self.api.list_sections(self.project.id)
                tasks = await self.api.list_tasks(self.project.id)
        except TodoistAuthenticationError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="invalid_auth",
            ) from err
        except TodoistConnectionError as err:
            raise UpdateFailed("Unable to connect to the Todoist API") from err
        except TodoistRateLimitError as err:
            raise UpdateFailed(
                "Todoist API rate limited refresh",
                retry_after=err.retry_after,
            ) from err
        except TodoistProjectNotFoundError as err:
            raise ConfigEntryError(
                translation_domain=DOMAIN,
                translation_key="project_not_found",
            ) from err
        except TodoistApiError as err:
            raise UpdateFailed("Unexpected Todoist API error") from err

        normalized_sections = {
            str(section["id"]): {
                "id": str(section["id"]),
                "name": str(section.get("name", "")),
                "order": int(
                    section.get("section_order", section.get("order", 0))
                ),
            }
            for section in sorted(
                sections,
                key=lambda value: (
                    int(value.get("section_order", value.get("order", 0))),
                    str(value.get("id", "")),
                ),
            )
            if section.get("id") is not None
        }

        normalized_tasks = sorted(
            (
                {
                    "id": str(task.get("id")),
                    "content": str(task.get("content", "")),
                    "description": str(task.get("description", "")),
                    "completed": bool(
                        task.get(
                            "checked",
                            task.get("is_completed", task.get("completed", False)),
                        )
                    ),
                    "priority": int(task.get("priority", 1)),
                    "labels": [str(label) for label in task.get("labels", [])],
                    "parent_id": _string_or_none(task.get("parent_id")),
                    "section_id": _string_or_none(task.get("section_id")),
                    "project_id": _string_or_none(task.get("project_id")),
                    "due": _normalize_due(task.get("due")),
                    "order": int(task.get("child_order", task.get("order", 0))),
                    "url": _task_url(task),
                }
                for task in tasks
                if task.get("id") is not None
            ),
            key=lambda task: (
                task["section_id"] or "",
                task["order"],
                task["id"],
            ),
        )

        return {
            "projects": self.projects,
            "sections": normalized_sections,
            "tasks": normalized_tasks,
        }

    def _async_update_entry_metadata(self, project: TodoistProject) -> None:
        """Store normalized project metadata back on the config entry."""
        entry_project_id = "" if self.all_projects else project.id
        entry_project_name = "" if self.all_projects else project.name
        entry_title = ALL_PROJECTS_NAME if self.all_projects else project.name
        entry_unique_id = ALL_PROJECTS_ID if self.all_projects else project.id

        updated_data = {
            **self.config_entry.data,
            CONF_ALL_PROJECTS: self.all_projects,
            CONF_PROJECT_ID: entry_project_id,
            CONF_PROJECT_NAME: entry_project_name,
        }

        if (
            updated_data != self.config_entry.data
            or self.config_entry.title != entry_title
            or self.config_entry.unique_id != entry_unique_id
        ):
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=updated_data,
                title=entry_title,
                unique_id=entry_unique_id,
            )


TodoistConfigEntry = ConfigEntry[TodoistCoordinator]


def _string_or_none(value: Any) -> str | None:
    """Return a string representation or None."""
    if value in (None, ""):
        return None
    return str(value)


def _normalize_due(value: Any) -> TodoistDueData | None:
    """Normalize Todoist due data to a JSON-serializable shape."""
    if not isinstance(value, dict):
        return None

    normalized: TodoistDueData = {}
    for key in ("string", "date", "datetime", "timezone"):
        item = value.get(key)
        if item not in (None, ""):
            normalized[key] = str(item)

    return normalized or None


async def _async_fetch_all_project_data(
    api: TodoistApiClient, project_ids: list[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Fetch sections and tasks for all configured projects."""
    if not project_ids:
        return [], []

    section_pages, task_pages = await asyncio.gather(
        asyncio.gather(*(api.list_sections(project_id) for project_id in project_ids)),
        asyncio.gather(*(api.list_tasks(project_id) for project_id in project_ids)),
    )

    return (
        [section for page in section_pages for section in page],
        [task for page in task_pages for task in page],
    )


def _normalize_projects(projects: list[dict[str, Any]]) -> dict[str, TodoistProjectData]:
    """Normalize Todoist project data to a JSON-serializable shape."""
    normalized_projects: dict[str, TodoistProjectData] = {}

    for project in sorted(
        projects,
        key=lambda value: (
            int(value.get("child_order", value.get("order", 0))),
            str(value.get("name", "")),
            str(value.get("id", "")),
        ),
    ):
        project_id = project.get("id")
        if project_id in (None, ""):
            continue

        normalized_projects[str(project_id)] = {
            "id": str(project_id),
            "name": str(project.get("name", project_id)),
            "order": int(project.get("child_order", project.get("order", 0))),
        }

    return normalized_projects


def _task_url(task: dict[str, Any]) -> str:
    """Return a stable Todoist task URL for the public sensor payload."""
    if task.get("url") not in (None, ""):
        return str(task["url"])

    task_id = task.get("id")
    if task_id in (None, ""):
        return ""

    return f"{TASK_URL_BASE}{task_id}"
