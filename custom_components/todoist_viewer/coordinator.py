from __future__ import annotations

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


class TodoistCoordinatorData(TypedDict):
    """Coordinator payload for the sensor platform."""

    sections: dict[str, TodoistSectionData]
    tasks: list[TodoistTaskData]


class TodoistCoordinator(DataUpdateCoordinator[TodoistCoordinatorData]):
    """Coordinator that fetches Todoist tasks for a single project."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.config_entry = entry
        self.api = TodoistApiClient(
            async_get_clientsession(hass), entry.data[CONF_TOKEN]
        )
        interval = max(
            int(entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)),
            MIN_UPDATE_INTERVAL,
        )
        self.project: TodoistProject | None = None

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
            project = await self.api.async_resolve_project(
                self.config_entry.data.get(CONF_PROJECT_ID),
                self.config_entry.data.get(CONF_PROJECT_NAME),
            )
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
            "sections": normalized_sections,
            "tasks": normalized_tasks,
        }

    def _async_update_entry_metadata(self, project: TodoistProject) -> None:
        """Store normalized project metadata back on the config entry."""
        updated_data = {
            **self.config_entry.data,
            CONF_PROJECT_ID: project.id,
            CONF_PROJECT_NAME: project.name,
        }

        if (
            updated_data != self.config_entry.data
            or self.config_entry.title != project.name
            or self.config_entry.unique_id != project.id
        ):
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=updated_data,
                title=project.name,
                unique_id=project.id,
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


def _task_url(task: dict[str, Any]) -> str:
    """Return a stable Todoist task URL for the public sensor payload."""
    if task.get("url") not in (None, ""):
        return str(task["url"])

    task_id = task.get("id")
    if task_id in (None, ""):
        return ""

    return f"{TASK_URL_BASE}{task_id}"
