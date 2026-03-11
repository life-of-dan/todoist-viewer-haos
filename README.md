# Todoist Viewer for Home Assistant

Todoist Viewer is a read-only Home Assistant custom integration that exposes either one Todoist project or every accessible project in a Todoist account as a sensor and ships a matching Lovelace card. It is packaged so it can be installed and upgraded through HACS on Home Assistant OS.

## Features

- Fetches active tasks from a selected Todoist project or from all accessible projects through the current Todoist API.
- Preserves sections and parent/subtask hierarchy.
- Exposes a sensor with normalized `projects`, `tasks`, and `sections` attributes for dashboards.
- Bundles the Lovelace card inside the integration, so HACS upgrades keep the backend and frontend together.
- Ships a Lovelace visual editor with a Todoist sensor dropdown, a show-completed toggle, and project selection when the sensor exposes multiple projects.
- Supports config flow, options flow, reauth, reconfigure, diagnostics, and clean unloads.

## Requirements

- Home Assistant OS / Home Assistant Core `2026.3.0` or newer
- Internet access from your Home Assistant host
- A Todoist API token

Get your Todoist API token from Todoist: `Settings` -> `Integrations` -> `Developer` -> `API token`.

## Install with HACS

1. Open HACS in Home Assistant.
2. Add this repository as a custom repository:
   - URL: `https://github.com/life-of-dan/todoist-viewer-haos`
   - Category: `Integration`
3. Install `Todoist Viewer`.
4. Restart Home Assistant.

## Manual installation

Copy `custom_components/todoist_viewer` into your Home Assistant config directory:

```txt
config/
└─ custom_components/
   └─ todoist_viewer/
```

Then restart Home Assistant.

## Set up the integration

1. Go to **Settings** -> **Devices & Services**.
2. Select **Add Integration**.
3. Search for `Todoist Viewer`.
4. Enter:
   - `API token`
   - either `Project ID`, `Project name`, or enable `All projects`
5. Finish the flow.

The integration stores the resolved Todoist project ID and project name automatically for single-project entries. `Project ID` can be a current Todoist string ID or a legacy numeric project ID. If `All projects` is enabled, one sensor will expose every accessible Todoist project and the card can filter that sensor per project. The update interval can be changed later in the integration options.

## Add the Lovelace card

The custom card is served by the integration itself from:

`/api/todoist_viewer/todoist-project-card.js?v=2`

### Storage mode

1. Go to **Settings** -> **Dashboards** -> **Resources**.
2. Add a new resource:
   - URL: `/api/todoist_viewer/todoist-project-card.js?v=2`
   - Type: `JavaScript Module`

### YAML mode

```yaml
lovelace:
  mode: yaml
  resources:
    - url: /api/todoist_viewer/todoist-project-card.js?v=2
      type: module
```

### Visual editor

After the resource is loaded, add `Todoist Project Card` from the dashboard card picker. The visual editor lets you choose:

- a Todoist Viewer sensor
- whether completed tasks should be shown
- a specific Todoist project when the selected sensor exposes multiple projects

### Example card

```yaml
type: custom:todoist-project-card
entity: sensor.todoist_tasks
show_completed: false
# Optional when the selected sensor exposes multiple projects:
# project_id: 6XGgm6PHrGgMpCFX
```

## Entity and payload

- `sensor.todoist_tasks`
  - state: number of active tasks
  - attributes:
    - `projects`: project map keyed by project ID
    - `tasks`: normalized list of Todoist tasks
    - `sections`: section map keyed by section ID

Example project payload:

```json
{
  "6XGgm6PHrGgMpCFX": {
    "id": "6XGgm6PHrGgMpCFX",
    "name": "Home",
    "order": 1
  }
}
```

Example task payload:

```json
{
  "id": "6XR4GqQQCW6Gv9h4",
  "content": "Task title",
  "description": "Optional description",
  "completed": false,
  "priority": 1,
  "labels": ["home", "urgent"],
  "parent_id": null,
  "section_id": "6fFPHV272WWh3gpW",
  "project_id": "6XGgm6PHrGgMpCFX",
  "due": {
    "string": "tomorrow 17:00",
    "date": "2026-03-11"
  },
  "order": 1,
  "url": "https://app.todoist.com/app/task/6XR4GqQQCW6Gv9h4"
}
```

## Updating

### HACS

- Update the integration through HACS.
- Restart Home Assistant.
- Refresh the browser once if the custom card resource was cached.

### Manual

- Replace `custom_components/todoist_viewer/`.
- Restart Home Assistant.
- Refresh the browser once if needed.

## Troubleshooting

### `Custom element doesn't exist: todoist-project-card`

- Verify the resource URL is `/api/todoist_viewer/todoist-project-card.js?v=2`.
- Hard-refresh the browser.
- Confirm the integration is installed and loaded.

### `Config flow could not be loaded: Invalid handler specified`

- Verify the integration path is exactly `config/custom_components/todoist_viewer/`.
- Confirm `manifest.json` contains `"config_flow": true`.
- Restart Home Assistant after copying files manually.

### No tasks appear

- The Todoist `/tasks` endpoint returns active tasks only.
- Confirm the selected project ID or project name, or verify that `All projects` is enabled for the intended entry.
- If the card is using an all-projects sensor, confirm the selected card project still exists in the entity `projects` attribute.
- Check **Settings** -> **System** -> **Logs** for Todoist API errors.

### `Todoist API request failed with status 410`

- Update to version `0.3.0` or newer through HACS.
- Restart Home Assistant after the upgrade.
- Reopen the integration setup flow if you were blocked during initial configuration.

## Security and privacy

- The Todoist API token is stored in the Home Assistant config entry.
- The integration is read-only and does not modify Todoist data.
- Diagnostics redact the API token and avoid exposing task content or descriptions.

## License

MIT
