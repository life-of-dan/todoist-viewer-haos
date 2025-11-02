# Todoist Viewer (Read-Only) for Home Assistant

Display a single Todoist project (including sections and subtasks) inside Home Assistant with a Todoist-like UI.
This integration is read-only and polls roughly hourly by default.

## Features

- Fetches active tasks from a chosen Todoist project via REST v2.
- Preserves hierarchy (parent → subtasks) and groups by sections.
- Shows priority, labels, and due string.
- Exposes a sensor with the full task payload for a custom Lovelace card to render.

## Requirements

- Home Assistant (2023.12+ recommended)
- A Todoist API token
- Internet connectivity from your HA host

Get your Todoist API token from Todoist → `Settings` → `Integrations` → `Developer` → `“API token”`.

## Installation

### 1. Copy the files

Place these exactly under your Home Assistant config directory:

```txt
config/
├─ custom_components/
│  └─ todoist_viewer/
│     ├─ __init__.py
│     ├─ manifest.json
│     ├─ const.py
│     ├─ api.py
│     ├─ coordinator.py
│     ├─ sensor.py
│     └─ config_flow.py
└─ www/
   └─ todoist-project-card.js
```

> If `www/` doesn’t exist, create it.

### 2. Restart Home Assistant

A full restart is required for Home Assistant to register the new integration and frontend resource.

### 3. Add the integration (UI)

- Go to **Settings** → **Devices & Services** → **Add Integration**.
- Search for **Todoist Viewer (Read-Only)**.
- Enter:
  - API token
  - Either Project ID or Project Name (ID is most reliable)
- Finish the flow.
  - You can change the refresh interval later in the integration Options (default: 3600 seconds).

### 4. Add the Lovelace resource

Depending on dashboard mode:

**Storage mode (default):**

- **Settings** → **Dashboards** → **( ⋮ )** → **Manage resources** → **Add resource**
- URL: `/local/todoist-project-card.js?v=1`
- Type: `JavaScript Module`

#### YAML mode:

```yaml
lovelace:
  mode: yaml
  resources:
    - url: /local/todoist-project-card.js?v=1
      type: module
```

### 5. Add the card to a view

Create a manual card with:

```yaml
type: custom:todoist-project-card
entity: sensor.todoist_tasks
show_completed: false
```

## Entities & Data Model

- `sensor.todoist_tasks`
  - state: number of active (incomplete) tasks
  - attributes:
    - `tasks`: array of normalized task objects
    - `sections`: map of section id → { id, name, order }

Each task contains:

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
  "due": { "string": "tomorrow 17:00", "date": "2025-11-03" },
  "order": 1,
  "url": "https://todoist.com/showTask?id=..."
}
```

## Troubleshooting

“Custom element doesn’t exist: todoist-project-card.”

- Ensure the file name is exactly todoist-project-card.js in config/www/.
- Confirm the resource URL is `/local/todoist-project-card.js` (with a cache-buster like ?v=2).
- Hard-refresh the dashboard (Shift + Reload).
- In the browser console, check:
  - `customElements.get('todoist-project-card')` → should return a function.
  - No red syntax errors for `/local/todoist-project-card.js`.

“Config flow could not be loaded: Invalid handler specified.”

- Verify the folder path and domain name match exactly:
`config/custom_components/todoist_viewer/`
- Ensure `config_flow.py` exists and `manifest.json` has `"config_flow": true`.
- Restart Home Assistant after copying files.
- Remove any stale copies / `__pycache__` and copy cleanly.

No tasks show up

- The Todoist /tasks REST endpoint returns active tasks only. Completed tasks aren’t included.
- Confirm the correct Project ID/Name.
- Check Settings → System → Logs for any Todoist API errors.

## Updating

- Replace the files in custom_components/todoist_viewer/ and www/todoist-project-card.js.
- Bump the resource cache buster in your resource URL (e.g., ?v=3).
- Restart Home Assistant.

## Uninstalling

- Settings → Devices & Services → Remove Todoist Viewer.
- Delete config/custom_components/todoist_viewer/.
- Remove the /local/todoist-project-card.js resource from Dashboard Resources.
- Restart Home Assistant.

## Configuration Options

- Update interval (seconds): default 3600 (1 hour). Adjust via the integration’s Options.

## Security & Privacy

- The Todoist API token is stored by Home Assistant’s config entries system.
- This integration is read-only and does not modify Todoist data.
- Revoke or rotate your token from Todoist if needed, then update the integration config.

License MIT
