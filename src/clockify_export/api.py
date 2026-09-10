"""Minimal Clockify API client using only stdlib."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

BASE_URL = "https://api.clockify.me/api/v1"


class ClockifyError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(f"HTTP {status}: {message}")


class ClockifyAPI:
    """Minimal Clockify REST API client."""

    def __init__(self, api_key: str, base_url: str = BASE_URL):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, body: dict | None = None) -> tuple[Any, dict[str, str]]:
        """Make a request, return (parsed_json, headers_dict)."""
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "X-Api-Key": self.api_key,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req) as resp:
                headers = dict(resp.headers)
                raw = resp.read()
                return json.loads(raw) if raw else None, headers
        except urllib.error.HTTPError as e:
            body_text = e.read().decode(errors="replace")
            raise ClockifyError(e.code, body_text) from e

    def _get(self, path: str) -> tuple[Any, dict[str, str]]:
        return self._request("GET", path)

    # ── Workspaces ──

    def get_workspaces(self) -> list[dict]:
        data, _ = self._get("/workspaces")
        return data

    # ── Current user ──

    def get_current_user(self) -> dict:
        data, _ = self._get("/user")
        return data

    # ── Projects ──

    def get_projects(self, workspace_id: str) -> list[dict]:
        """Fetch all projects (paginated)."""
        projects: list[dict] = []
        page = 1
        while True:
            data, headers = self._get(
                f"/workspaces/{workspace_id}/projects?page={page}&page-size=50"
            )
            if not data:
                break
            projects.extend(data)
            if headers.get("Last-Page", "false").lower() == "true":
                break
            page += 1
        return projects

    # ── Tasks ──

    def get_tasks(self, workspace_id: str, project_id: str) -> list[dict]:
        """Fetch all tasks for a project (paginated)."""
        tasks: list[dict] = []
        page = 1
        while True:
            data, headers = self._get(
                f"/workspaces/{workspace_id}/projects/{project_id}/tasks?page={page}&page-size=50"
            )
            if not data:
                break
            tasks.extend(data)
            if headers.get("Last-Page", "false").lower() == "true":
                break
            page += 1
        return tasks

    # ── Clients ──

    def get_clients(self, workspace_id: str) -> list[dict]:
        """Fetch all clients (paginated)."""
        clients: list[dict] = []
        page = 1
        while True:
            data, headers = self._get(
                f"/workspaces/{workspace_id}/clients?page={page}&page-size=50"
            )
            if not data:
                break
            clients.extend(data)
            if headers.get("Last-Page", "false").lower() == "true":
                break
            page += 1
        return clients

    # ── Tags ──

    def get_tags(self, workspace_id: str) -> list[dict]:
        """Fetch all tags (paginated)."""
        tags: list[dict] = []
        page = 1
        while True:
            data, headers = self._get(
                f"/workspaces/{workspace_id}/tags?page={page}&page-size=50"
            )
            if not data:
                break
            tags.extend(data)
            if headers.get("Last-Page", "false").lower() == "true":
                break
            page += 1
        return tags

    # ── Time entries ──

    def get_time_entries(
        self,
        workspace_id: str,
        user_id: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[dict]:
        """Fetch all time entries for a user, paginated."""
        entries: list[dict] = []
        page = 1
        while True:
            params = f"page={page}&page-size=200"
            if start:
                # Clockify expects "yyyy-MM-ddThh:mm:ssZ" format
                utc = start.astimezone(timezone.utc)
                params += f"&start={utc.strftime('%Y-%m-%dT%H:%M:%SZ')}"
            if end:
                utc = end.astimezone(timezone.utc)
                params += f"&end={utc.strftime('%Y-%m-%dT%H:%M:%SZ')}"
            data, headers = self._get(
                f"/workspaces/{workspace_id}/user/{user_id}/time-entries?{params}"
            )
            if not data:
                break
            entries.extend(data)
            if headers.get("Last-Page", "false").lower() == "true":
                break
            page += 1
            if page % 10 == 0:
                print(f"    ... fetched {len(entries)} entries so far (page {page})")
        return entries


# ── Duration parsing ──

_DURATION_RE = re.compile(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def parse_iso_duration_to_hours(duration_str: str) -> float:
    """Parse ISO 8601 duration (e.g. 'PT1H30M') to decimal hours."""
    m = _DURATION_RE.match(duration_str)
    if not m:
        return 0.0
    days = int(m.group(1) or 0)
    hours = int(m.group(2) or 0)
    minutes = int(m.group(3) or 0)
    seconds = int(m.group(4) or 0)
    total_minutes = days * 24 * 60 + hours * 60 + minutes + seconds / 60
    return round(total_minutes / 60, 2)
