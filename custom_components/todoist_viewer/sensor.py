from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_SECTIONS, ATTR_TASKS, DOMAIN
from .coordinator import TodoistConfigEntry, TodoistCoordinator


async def async_setup_entry(
    _hass,
    entry: TodoistConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Todoist Viewer sensor platform."""
    async_add_entities([TodoistTasksSensor(entry.runtime_data, entry)])


class TodoistTasksSensor(CoordinatorEntity[TodoistCoordinator], SensorEntity):
    """Expose the selected Todoist project as a Home Assistant sensor."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: TodoistCoordinator, entry: TodoistConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = "Todoist Tasks"
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_tasks"
        self._attr_icon = "mdi:format-list-checkbox"

    @property
    def native_value(self) -> int:
        """Return the number of active tasks."""
        return sum(
            1
            for task in self.coordinator.data["tasks"]
            if not task.get("completed", False)
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return task and section payloads for the frontend card."""
        return {
            ATTR_TASKS: self.coordinator.data["tasks"],
            ATTR_SECTIONS: self.coordinator.data["sections"],
        }

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the Todoist project."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer="Todoist",
            model="REST API v2",
        )
