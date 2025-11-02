from __future__ import annotations
from typing import Any, Dict
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_TOKEN,
    CONF_PROJECT_ID,
    CONF_PROJECT_NAME,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        errors = {}
        if user_input is not None:
            if not user_input.get(CONF_PROJECT_ID) and not user_input.get(CONF_PROJECT_NAME):
                errors["base"] = "project_required"
            else:
                return self.async_create_entry(title="Todoist Viewer", data=user_input)

        schema = vol.Schema({
            vol.Required(CONF_TOKEN): str,
            vol.Optional(CONF_PROJECT_ID, default=""): str,
            vol.Optional(CONF_PROJECT_NAME, default=""): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return OptionsFlow(config_entry)

class OptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema({
            vol.Optional(CONF_UPDATE_INTERVAL, default=self.config_entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)): int,
        })
        return self.async_show_form(step_id="init", data_schema=schema)
