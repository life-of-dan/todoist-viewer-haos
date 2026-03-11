from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import UnitOfTime
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    TodoistApiClient,
    TodoistApiError,
    TodoistAuthenticationError,
    TodoistConnectionError,
    TodoistProject,
    TodoistProjectAmbiguousError,
    TodoistProjectNotFoundError,
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


class TodoistViewerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Todoist Viewer."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._reauth_entry_data: dict[str, Any] | None = None

    @staticmethod
    @callback
    def async_get_options_flow(_config_entry: ConfigEntry) -> TodoistOptionsFlow:
        """Get the options flow for this handler."""
        return TodoistOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors, project, data = await self._async_validate_user_input(user_input)
            if not errors:
                await self.async_set_unique_id(project.id, raise_on_progress=False)
                duplicate_abort = self._async_abort_duplicate_project(project.id)
                if duplicate_abort is not None:
                    return duplicate_abort

                return self.async_create_entry(title=project.name, data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle a reauth flow."""
        self._reauth_entry_data = dict(entry_data)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm the reauth flow."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()

        if user_input is not None and self._reauth_entry_data is not None:
            merged_input = {
                CONF_TOKEN: user_input[CONF_TOKEN],
                CONF_PROJECT_ID: self._reauth_entry_data.get(CONF_PROJECT_ID, ""),
                CONF_PROJECT_NAME: self._reauth_entry_data.get(CONF_PROJECT_NAME, ""),
            }
            errors, project, data = await self._async_validate_user_input(merged_input)
            if not errors:
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=project.id,
                    title=project.name,
                    data_updates=data,
                )

        project_name = entry.title
        if not project_name and self._reauth_entry_data is not None:
            project_name = self._reauth_entry_data.get(
                CONF_PROJECT_NAME, "Todoist project"
            )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_token_schema(),
            description_placeholders={"project_name": project_name},
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of an existing entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            errors, project, data = await self._async_validate_project_input(
                entry.data[CONF_TOKEN], user_input
            )
            if not errors:
                duplicate_abort = self._async_abort_duplicate_project(
                    project.id, current_entry=entry
                )
                if duplicate_abort is not None:
                    return duplicate_abort

                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=project.id,
                    title=project.name,
                    data={
                        **entry.data,
                        **data,
                    },
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                _project_schema(),
                {
                    CONF_PROJECT_ID: entry.data.get(CONF_PROJECT_ID, ""),
                    CONF_PROJECT_NAME: entry.data.get(CONF_PROJECT_NAME, ""),
                },
            ),
            errors=errors,
        )

    async def _async_validate_user_input(
        self, user_input: dict[str, Any]
    ) -> tuple[dict[str, str], TodoistProject, dict[str, str]]:
        """Validate the full user-input payload."""
        token = str(user_input[CONF_TOKEN]).strip()
        errors, project, data = await self._async_validate_project_input(
            token,
            user_input,
        )

        if errors:
            return errors, project, data

        return (
            errors,
            project,
            {
                CONF_TOKEN: token,
                **data,
            },
        )

    async def _async_validate_project_input(
        self, token: str, user_input: dict[str, Any]
    ) -> tuple[dict[str, str], TodoistProject, dict[str, str]]:
        """Validate Todoist project selection."""
        project_id = str(user_input.get(CONF_PROJECT_ID, "") or "").strip()
        project_name = str(user_input.get(CONF_PROJECT_NAME, "") or "").strip()

        if not project_id and not project_name:
            return {"base": "project_required"}, TodoistProject("", ""), {}

        api = TodoistApiClient(async_get_clientsession(self.hass), token)
        try:
            project = await api.async_resolve_project(project_id, project_name)
        except TodoistAuthenticationError:
            return {"base": "invalid_auth"}, TodoistProject("", ""), {}
        except TodoistConnectionError:
            return {"base": "cannot_connect"}, TodoistProject("", ""), {}
        except TodoistProjectNotFoundError:
            return {"base": "project_not_found"}, TodoistProject("", ""), {}
        except TodoistProjectAmbiguousError:
            return {"base": "project_name_ambiguous"}, TodoistProject("", ""), {}
        except TodoistApiError:
            _LOGGER.exception("Unexpected Todoist API error during config flow")
            return {"base": "unknown"}, TodoistProject("", ""), {}

        return (
            {},
            project,
            {
                CONF_PROJECT_ID: project.id,
                CONF_PROJECT_NAME: project.name,
            },
        )

    def _async_abort_duplicate_project(
        self, project_id: str, current_entry: ConfigEntry | None = None
    ) -> ConfigFlowResult | None:
        """Abort if another entry already tracks this Todoist project."""
        for entry in self._async_current_entries():
            if current_entry is not None and entry.entry_id == current_entry.entry_id:
                continue

            if entry.unique_id == project_id or entry.data.get(CONF_PROJECT_ID) == project_id:
                return self.async_abort(reason="already_configured")

        return None


class TodoistOptionsFlow(OptionsFlowWithReload):
    """Handle the Todoist Viewer options flow."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the update-interval option."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_UPDATE_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                        ),
                    ): vol.All(_update_interval_selector(), vol.Coerce(int))
                }
            ),
        )


def _token_schema() -> vol.Schema:
    """Build the token-only schema."""
    return vol.Schema(
        {
            vol.Required(CONF_TOKEN): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.PASSWORD,
                    autocomplete="off",
                )
            ),
        }
    )


def _project_schema() -> vol.Schema:
    """Build the project-selection schema."""
    return vol.Schema(
        {
            vol.Optional(CONF_PROJECT_ID): selector.TextSelector(),
            vol.Optional(CONF_PROJECT_NAME): selector.TextSelector(),
        }
    )


def _user_schema() -> vol.Schema:
    """Build the initial user-step schema."""
    return vol.Schema(
        {
            **_token_schema().schema,
            **_project_schema().schema,
        }
    )


def _update_interval_selector() -> selector.NumberSelector:
    """Build the update interval selector."""
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=MIN_UPDATE_INTERVAL,
            step=60,
            mode=selector.NumberSelectorMode.BOX,
            unit_of_measurement=UnitOfTime.SECONDS,
        )
    )
