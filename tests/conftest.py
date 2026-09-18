"""Shared test fixtures."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def sample_workspace() -> dict[str, Any]:
    return {"id": "ws123", "name": "Test Workspace"}


@pytest.fixture
def sample_user() -> dict[str, Any]:
    return {"id": "user123", "name": "Test User"}


@pytest.fixture
def sample_projects() -> list[dict[str, Any]]:
    return [
        {"id": "proj1", "name": "Project Alpha", "clientId": "client1"},
        {"id": "proj2", "name": "Project Beta", "clientId": "client2"},
        {"id": "proj3", "name": "Project Gamma", "clientId": None},
    ]


@pytest.fixture
def sample_clients() -> list[dict[str, Any]]:
    return [
        {"id": "client1", "name": "Client A"},
        {"id": "client2", "name": "Client B"},
    ]


@pytest.fixture
def sample_tags() -> list[dict[str, Any]]:
    return [
        {"id": "tag1", "name": "tag-a"},
        {"id": "tag2", "name": "tag-b"},
    ]


@pytest.fixture
def sample_tasks() -> list[dict[str, Any]]:
    return [
        {"id": "task1", "name": "Task 1", "projectId": "proj1"},
        {"id": "task2", "name": "Task 2", "projectId": "proj1"},
    ]


@pytest.fixture
def sample_time_entries() -> list[dict[str, Any]]:
    return [
        {
            "id": "entry1",
            "timeInterval": {
                "start": "2026-01-15T09:00:00Z",
                "end": "2026-01-15T17:00:00Z",
                "duration": "PT8H",
                "timeZone": "UTC",
            },
            "projectId": "proj1",
            "taskId": "task1",
            "tagIds": ["tag1"],
            "description": "Work on feature",
            "billable": True,
            "hourlyRate": {"amount": 5000, "currency": "USD"},
            "type": "REGULAR",
        },
        {
            "id": "entry2",
            "timeInterval": {
                "start": "2026-01-16T10:00:00Z",
                "end": "2026-01-16T14:00:00Z",
                "duration": "PT4H",
                "timeZone": "UTC",
            },
            "projectId": "proj2",
            "taskId": "task2",
            "tagIds": ["tag1", "tag2"],
            "description": "Meeting",
            "billable": True,
            "hourlyRate": {"amount": 7500, "currency": "USD"},
            "type": "REGULAR",
        },
        {
            "id": "entry3",
            "timeInterval": {
                "start": "2026-02-01T09:00:00Z",
                "end": "2026-02-01T17:00:00Z",
                "duration": "PT8H",
                "timeZone": "UTC",
            },
            "projectId": "proj1",
            "taskId": None,
            "tagIds": [],
            "description": "February work",
            "billable": False,
            "hourlyRate": {"amount": 0, "currency": ""},
            "type": "REGULAR",
        },
    ]


@pytest.fixture
def mock_clockify_api(mocker, sample_workspace, sample_user, sample_projects, sample_clients, sample_tags, sample_tasks, sample_time_entries):
    """Mock ClockifyAPI with typical responses."""
    from clockify_export.api import ClockifyAPI

    mock = mocker.MagicMock(spec=ClockifyAPI)
    mock.get_workspaces.return_value = [sample_workspace]
    mock.get_current_user.return_value = sample_user
    mock.get_projects.return_value = sample_projects
    mock.get_clients.return_value = sample_clients
    mock.get_tags.return_value = sample_tags
    mock.get_tasks.return_value = sample_tasks
    mock.get_time_entries.return_value = sample_time_entries
    return mock


@pytest.fixture
def temp_export_dir(tmp_path) -> Path:
    """Temporary export directory."""
    return tmp_path / "export"


@pytest.fixture
def temp_config_dir(tmp_path) -> Path:
    """Temporary config directory."""
    return tmp_path / ".config" / "clockify-export"


@pytest.fixture(autouse=True)
def isolate_config(monkeypatch, temp_config_dir):
    """Isolate config by patching CONFIG_DIR."""
    import clockify_export.config as config_module
    monkeypatch.setattr(config_module, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(config_module, "CONFIG_FILE", temp_config_dir / "config.toml")
    monkeypatch.setattr(config_module, "LEGACY_CONFIG_FILE", temp_config_dir / "config.json")
    monkeypatch.setattr(config_module, "STATE_FILE", temp_config_dir / "state.json")


@pytest.fixture
def sample_state() -> dict[str, Any]:
    return {
        "ws123": {
            "last_exported": "2026-01-15T17:00:00+00:00",
            "updated_at": "2026-01-16T00:00:00+00:00",
        }
    }