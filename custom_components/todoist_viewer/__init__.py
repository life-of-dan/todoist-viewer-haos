from __future__ import annotations

from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import CARD_RESOURCE_PATH, CARD_URL_PATH, DOMAIN, PLATFORMS
from .coordinator import TodoistConfigEntry, TodoistCoordinator

STATIC_PATH_REGISTERED = f"{DOMAIN}_static_path_registered"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Todoist Viewer integration."""
    if not hass.data.get(STATIC_PATH_REGISTERED):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    CARD_URL_PATH,
                    str(Path(__file__).parent / CARD_RESOURCE_PATH),
                )
            ]
        )
        hass.data[STATIC_PATH_REGISTERED] = True

    return True


async def async_setup_entry(hass: HomeAssistant, entry: TodoistConfigEntry) -> bool:
    """Set up Todoist Viewer from a config entry."""
    coordinator = TodoistCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TodoistConfigEntry) -> bool:
    """Unload a Todoist Viewer config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
