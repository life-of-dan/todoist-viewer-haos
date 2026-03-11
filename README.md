# Todoist Viewer for Home Assistant

Todoist Viewer is a read-only Home Assistant custom integration that exposes one Todoist project as a sensor and ships a matching Lovelace card. It is packaged so it can be installed and upgraded through HACS on Home Assistant OS.

## Features

- Fetches active tasks from a selected Todoist project through the Todoist REST API v2.
- Preserves sections and parent/subtask hierarchy.
- Exposes a sensor with normalized `tasks` and `sections` attributes for dashboards.
- Bundles the Lovelace card inside the integration, so HACS upgrades keep the backend and frontend together.
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
   - either `Project ID` or `Project name`
5. Finish the flow.

The integration stores the resolved Todoist project ID and project name automatically. The update interval can be changed later in the integration options.

## Add the Lovelace card

The custom card is served by the integration itself from:

`/api/todoist_viewer/todoist-project-card.js?v=1`

### Storage mode

1. Go to **Settings** -> **Dashboards** -> **Resources**.
2. Add a new resource:
   - URL: `/api/todoist_viewer/todoist-project-card.js?v=1`
   - Type: `JavaScript Module`

### YAML mode

```yaml
lovelace:
  mode: yaml
  resources:
    - url: /api/todoist_viewer/todoist-project-card.js?v=1
      type: module
```

### Example card

```yaml
type: custom:todoist-project-card
entity: sensor.todoist_tasks
show_completed: false
```

## Entity and payload

- `sensor.todoist_tasks`
  - state: number of active tasks
  - attributes:
    - `tasks`: normalized list of Todoist tasks
    - `sections`: section map keyed by section ID

Example task payload:

```json
{
  "id": "123456789",
  "content": "Task title",
  "description": "Optional description",
  "completed": false,
  "priority": 1,
  "labels": ["home", "urgent"],
  "parent_id": null,
  "section_id": "987654321",
  "project_id": "111222333",
  "due": {
    "string": "tomorrow 17:00",
    "date": "2026-03-11"
  },
  "order": 1,
  "url": "https://todoist.com/showTask?id=123456789"
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

- Verify the resource URL is `/api/todoist_viewer/todoist-project-card.js`.
- Hard-refresh the browser.
- Confirm the integration is installed and loaded.

### `Config flow could not be loaded: Invalid handler specified`

- Verify the integration path is exactly `config/custom_components/todoist_viewer/`.
- Confirm `manifest.json` contains `"config_flow": true`.
- Restart Home Assistant after copying files manually.

### No tasks appear

- The Todoist `/tasks` endpoint returns active tasks only.
- Confirm the selected project ID or project name.
- Check **Settings** -> **System** -> **Logs** for Todoist API errors.

## Security and privacy

- The Todoist API token is stored in the Home Assistant config entry.
- The integration is read-only and does not modify Todoist data.
- Diagnostics redact the API token and avoid exposing task content or descriptions.

## License

MIT
