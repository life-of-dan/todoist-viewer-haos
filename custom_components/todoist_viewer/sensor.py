from __future__ import annotations
from typing import Any
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN, ATTR_TASKS, ATTR_SECTIONS
from .coordinator import TodoistCoordinator

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator: TodoistCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TodoistTasksSensor(coordinator, entry)])

class TodoistTasksSensor(CoordinatorEntity[TodoistCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: TodoistCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = "Todoist Tasks"
        self._attr_unique_id = f"{entry.entry_id}_tasks"
        self._attr_icon = "mdi:format-list-checkbox"

    @property
    def native_value(self) -> int | None:
        data = self.coordinator.data or {}
        tasks = data.get("tasks", [])
        return len([t for t in tasks if not t.get("completed")])

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.coordinator.data or {}
        return {
            ATTR_TASKS: data.get("tasks", []),
            ATTR_SECTIONS: data.get("sections", {}),
        }

    @property
    def device_info(self) -> DeviceInfo | None:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="Todoist Viewer",
            manufacturer="Todoist",
            model="REST v2",
        )
