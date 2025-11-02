from __future__ import annotations
import logging
from datetime import timedelta
from typing import Any, Dict, List
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import (
    DOMAIN,
    CONF_TOKEN,
    CONF_PROJECT_ID,
    CONF_PROJECT_NAME,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
)
from .api import TodoistApiClient

_LOGGER = logging.getLogger(__name__)

class TodoistCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Coordinator that fetches Todoist tasks for a single project."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.session = async_get_clientsession(hass)
        self.api = TodoistApiClient(self.session, entry.data[CONF_TOKEN])
        interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}-{entry.entry_id}",
            update_interval=timedelta(seconds=interval),
        )

    async def _async_setup(self) -> None:
        # Resolve project ID if only project name was provided
        if self.entry.data.get(CONF_PROJECT_ID):
            return
        project_name = self.entry.data.get(CONF_PROJECT_NAME)
        if not project_name:
            return
        projects = await self.api.list_projects()
        match = next((p for p in projects if p.get("name") == project_name), None)
        if not match:
            raise ValueError(f"Project named '{project_name}' not found in Todoist account.")
        data = dict(self.entry.data)
        data[CONF_PROJECT_ID] = str(match["id"])
        await self.hass.config_entries.async_update_entry(self.entry, data=data)

    async def _async_update_data(self) -> Dict[str, Any]:
        project_id = self.entry.data.get(CONF_PROJECT_ID)
        if not project_id:
            await self._async_setup()
            project_id = self.entry.data.get(CONF_PROJECT_ID)
            if not project_id:
                raise ValueError("Todoist project not resolved. Provide project_id or project_name.")
        sections = await self.api.list_sections(project_id)
        tasks = await self.api.list_tasks(project_id)

        section_map = {str(s["id"]): {"id": str(s["id"]), "name": s.get("name", ""), "order": s.get("order", 0)} for s in sections}
        norm_tasks: List[Dict[str, Any]] = []
        for t in tasks:
            norm_tasks.append({
                "id": str(t.get("id")),
                "content": t.get("content", ""),
                "description": t.get("description", ""),
                "completed": bool(t.get("is_completed", False) or t.get("completed", False)),
                "priority": int(t.get("priority", 1)),
                "labels": t.get("labels", []),
                "parent_id": str(t["parent_id"]) if t.get("parent_id") else None,
                "section_id": str(t["section_id"]) if t.get("section_id") else None,
                "project_id": str(t.get("project_id")) if t.get("project_id") else None,
                "due": t.get("due", None),
                "order": int(t.get("order", 0)),
                "url": t.get("url", ""),
            })

        return {"sections": section_map, "tasks": norm_tasks}
