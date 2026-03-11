from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "todoist_viewer"

CONF_TOKEN = "token"
CONF_PROJECT_ID = "project_id"
CONF_PROJECT_NAME = "project_name"
CONF_UPDATE_INTERVAL = "update_interval"

DEFAULT_UPDATE_INTERVAL = 3600
MIN_UPDATE_INTERVAL = 300

PLATFORMS: tuple[Platform, ...] = (Platform.SENSOR,)

ATTR_TASKS = "tasks"
ATTR_SECTIONS = "sections"

CARD_FILENAME = "todoist-project-card.js"
CARD_URL_PATH = f"/api/{DOMAIN}/{CARD_FILENAME}"
CARD_RESOURCE_PATH = f"frontend/{CARD_FILENAME}"

REDACT_CONFIG = {CONF_TOKEN}
