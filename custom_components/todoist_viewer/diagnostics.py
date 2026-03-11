from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import ATTR_PROJECTS, ATTR_SECTIONS, ATTR_TASKS, REDACT_CONFIG
from .coordinator import TodoistConfigEntry


async def async_get_config_entry_diagnostics(
    _hass: HomeAssistant,
    config_entry: TodoistConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = config_entry.runtime_data
    project_payload = coordinator.data.get(ATTR_PROJECTS, {})
    task_payload = coordinator.data.get(ATTR_TASKS, [])
    section_payload = coordinator.data.get(ATTR_SECTIONS, {})

    return {
        "entry": async_redact_data(config_entry.as_dict(), REDACT_CONFIG),
        "project": {
            "id": coordinator.project.id if coordinator.project else None,
            "name": coordinator.project.name if coordinator.project else None,
        },
        "summary": {
            "project_count": len(project_payload),
            "section_count": len(section_payload),
            "task_count": len(task_payload),
            "active_task_count": sum(
                1 for task in task_payload if not task.get("completed", False)
            ),
            "completed_task_count": sum(
                1 for task in task_payload if task.get("completed", False)
            ),
        },
        "tasks": [
            {
                "id": task["id"],
                "completed": task["completed"],
                "priority": task["priority"],
                "label_count": len(task["labels"]),
                "has_due": task["due"] is not None,
                "parent_id": task["parent_id"],
                "project_id": task["project_id"],
                "section_id": task["section_id"],
            }
            for task in task_payload
        ],
        "projects": project_payload,
        "sections": section_payload,
    }
