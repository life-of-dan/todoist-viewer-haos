# AGENTS.md

## Project Scope
- This repository contains a Home Assistant custom integration in `custom_components/todoist_viewer` and a companion Lovelace card in `www/todoist-project-card.js`.
- The integration is intentionally read-only. Do not add Todoist write/mutation features unless the user explicitly asks for them.
- Treat the backend payload exposed to Home Assistant (`tasks`, `sections`, entity names, unique IDs, options) as a public contract with both `README.md` and the Lovelace card.

## Primary Python Executable
- Use `C:\Users\nyx\.pyenv-win-venv\envs\haos\Scripts\python.exe` as the primary Python executable for every Python command in this repo.
- In PowerShell, invoke it as:
  - `& 'C:\Users\nyx\.pyenv-win-venv\envs\haos\Scripts\python.exe' ...`
- Use that interpreter for:
  - package installs: `& 'C:\Users\nyx\.pyenv-win-venv\envs\haos\Scripts\python.exe' -m pip ...`
  - syntax checks: `& 'C:\Users\nyx\.pyenv-win-venv\envs\haos\Scripts\python.exe' -m compileall custom_components\todoist_viewer`
  - tests, scripts, and ad hoc inspection code
- Do not assume `python`, `py`, or another virtual environment points at the correct Home Assistant-compatible interpreter.

## Repo-Aware Validation
- This is a standalone custom integration repo, not a Home Assistant Core checkout.
- Do not assume Home Assistant Core helper commands such as `python -m script.hassfest` exist here.
- Prefer targeted validation that works inside this repo:
  - Python compile/syntax checks for `custom_components/todoist_viewer`
  - focused tests if the repo later gains a test suite
- If a task truly needs full Home Assistant Core tooling, say so explicitly instead of inventing missing local commands.

## Home Assistant Coding Practices
- Follow current Home Assistant Integration Quality Scale practices, even though this is a custom integration. Aim for current Bronze/Silver patterns and prefer higher-tier practices when they are a natural fit.
- Keep the integration fully async. Do not introduce blocking I/O, synchronous HTTP clients, or executor work unless there is no async alternative.
- Prefer injected Home Assistant helpers and clients, such as `async_get_clientsession`, over standalone networking setup.
- Prefer modern Python typing throughout:
  - use built-in generics like `dict[str, Any]` and `list[str]`
  - prefer typed aliases, dataclasses, and narrow types over loose `Any`-heavy dictionaries
  - keep new/modified modules fully typed

## Config Entries and Runtime Data
- Prefer `ConfigEntry.runtime_data` over `hass.data` for per-entry runtime objects.
- Use a typed config-entry alias when runtime data is stored, for example a typed `ConfigEntry[TodoistRuntimeData]`.
- Keep `async_setup_entry` focused on creating the runtime objects, performing the first refresh, storing `runtime_data`, and forwarding platforms.
- Support clean unloads for every platform.

## Coordinator and API Patterns
- Use `DataUpdateCoordinator` for polling work.
- Put one-time async initialization in `DataUpdateCoordinator._async_setup` and keep `_async_update_data` focused on refresh logic.
- If the normalized data is equality-comparable, set `always_update=False` to avoid unnecessary callbacks and state writes.
- Map failures to Home Assistant exceptions correctly:
  - temporary connectivity/service failures during setup -> `ConfigEntryNotReady`
  - temporary refresh failures after setup -> `UpdateFailed`
  - invalid or expired Todoist auth -> `ConfigEntryAuthFailed`
  - permanent unsupported-account or unrecoverable setup problems -> `ConfigEntryError`
- If Todoist returns HTTP 429 or `Retry-After`, honor it with `UpdateFailed(retry_after=...)` instead of hammering the API.
- Avoid log spam. Let Home Assistant handle setup-retry and coordinator-unavailable logging where possible.

## Config Flow, Options, Reauth, and Reconfigure
- Validate credentials and project access in the config flow before creating the entry.
- Set a stable config-entry unique ID and abort duplicates instead of replacing existing entries. For this integration, prefer a stable Todoist-backed identifier such as the resolved project ID combined with the account identifier if available.
- Prefer selectors and `add_suggested_values_to_schema(...)` when building config/option forms if they improve the UX.
- Prefer `OptionsFlowWithReload` when option changes should reload the integration.
- Use a `reconfigure` step for non-optional setup data changes and a `reauth` step for token/auth issues.
- If auth breaks at runtime, raise `ConfigEntryAuthFailed` or start reauth from the linked entry rather than manually kicking off unscoped flows.

## Entities, Translations, and Diagnostics
- Prefer translated entity names over hard-coded English names:
  - keep `_attr_has_entity_name = True`
  - use `_attr_translation_key` where practical
  - keep device names and entity names separated the way Home Assistant expects
- For this custom integration, user-facing strings belong in `custom_components/todoist_viewer/translations/*.json`. Keep `translations/en.json` current whenever adding config-flow, options, abort, repair, diagnostics, or exception text.
- Keep exception messages translatable where they are user-facing.
- Add diagnostics for supportable failures and always redact secrets such as the Todoist token, auth headers, and any sensitive personal data.
- If user action is required beyond a transient failure or simple reauth, prefer a repair issue over repeated warnings.

## Manifest and Metadata
- Keep `custom_components/todoist_viewer/manifest.json` aligned with current custom-integration expectations:
  - valid `version`
  - explicit `integration_type`
  - accurate `documentation`
  - accurate `issue_tracker`
  - correct `iot_class`
  - correct `loggers`
  - `config_flow` when UI setup exists
- For this project, `integration_type` should be explicit instead of relying on the implicit default.
- If the repo adopts Home Assistant quality-scale tracking, add or update `custom_components/todoist_viewer/quality_scale.yaml` alongside substantive quality improvements.
- If branding is added, use `custom_components/todoist_viewer/brand/` for custom-integration logos/icons supported by recent Home Assistant releases.

## Project-Specific Guardrails
- Preserve the read-only nature of the integration unless the task explicitly expands scope.
- Keep token values out of logs, state attributes, diagnostics, and raised error text.
- Preserve the sensor payload shape consumed by `www/todoist-project-card.js` unless the card and docs are updated in the same change.
- When refactoring task normalization, prefer stable typed models and keep the exposed JSON-compatible attribute structure backward-compatible unless the user requests a breaking change.
- If a change affects installation, configuration, options, entity semantics, or Lovelace usage, update `README.md` in the same task.

## Testing Expectations
- For Python changes, run at least a syntax/compile validation with the primary interpreter when feasible.
- If tests are added later, follow Home Assistant-style layout under `tests/components/todoist_viewer/`.
- Do not add unrelated tooling or CI scaffolding unless the user asks for it.
