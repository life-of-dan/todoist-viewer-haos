from __future__ import annotations
from typing import Any, Dict, List, Optional
import aiohttp

API_BASE = "https://api.todoist.com/rest/v2"

class TodoistApiClient:
    def __init__(self, session: aiohttp.ClientSession, token: str) -> None:
        self._session = session
        self._token = token

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        headers = {"Authorization": f"Bearer {self._token}"}
        url = f"{API_BASE}{path}"
        async with self._session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Todoist API {path} failed: {resp.status} {text}")
            return await resp.json()

    async def list_projects(self) -> List[Dict[str, Any]]:
        return await self._get("/projects")

    async def list_sections(self, project_id: str) -> List[Dict[str, Any]]:
        return await self._get("/sections", params={"project_id": project_id})

    async def list_tasks(self, project_id: str) -> List[Dict[str, Any]]:
        # Returns only active tasks
        return await self._get("/tasks", params={"project_id": project_id})
