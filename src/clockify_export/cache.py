"""Cache management for Clockify data."""

from __future__ import annotations

import json
from pathlib import Path


CACHE_DIR = ".cache"


def get_cache_dir(export_dir: Path) -> Path:
    """Get the cache directory path."""
    return export_dir / CACHE_DIR


def _read_json(path: Path) -> dict | None:
    """Read JSON file, return None if not exists or invalid."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _write_json(path: Path, data: dict) -> None:
    """Write JSON file, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def load_cache(export_dir: Path, name: str) -> dict | None:
    """Load cached data by name."""
    cache_dir = get_cache_dir(export_dir)
    return _read_json(cache_dir / f"{name}.json")


def save_cache(export_dir: Path, name: str, data: dict) -> bool:
    """Save data to cache if changed. Returns True if written."""
    cache_dir = get_cache_dir(export_dir)
    path = cache_dir / f"{name}.json"
    existing = _read_json(path)
    if existing == data:
        return False
    _write_json(path, data)
    return True


def load_workspaces(export_dir: Path) -> list[dict] | None:
    """Load cached workspaces."""
    data = load_cache(export_dir, "workspaces")
    return data.get("workspaces") if data else None


def save_workspaces(export_dir: Path, workspaces: list[dict]) -> bool:
    """Save workspaces to cache if changed."""
    return save_cache(export_dir, "workspaces", {"workspaces": workspaces})


def load_workspace_data(export_dir: Path, workspace_id: str) -> dict | None:
    """Load cached workspace data (projects, clients, tags)."""
    return load_cache(export_dir, f"workspace_{workspace_id}")


def save_workspace_data(
    export_dir: Path,
    workspace_id: str,
    projects: list[dict],
    clients: list[dict],
    tags: list[dict],
) -> bool:
    """Save workspace data to cache if changed."""
    data = {
        "projects": projects,
        "clients": clients,
        "tags": tags,
    }
    return save_cache(export_dir, f"workspace_{workspace_id}", data)