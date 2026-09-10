"""Incremental export state tracking.

Stores last-exported timestamps per workspace in ~/.config/clockify-export/state.json
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = Path.home() / ".config" / "clockify-export"
STATE_FILE = STATE_DIR / "state.json"


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def _save_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


def get_last_exported(workspace_id: str) -> datetime | None:
    """Get the last exported timestamp for a workspace (or None)."""
    state = _load_state()
    ts = state.get(workspace_id, {}).get("last_exported")
    if ts:
        return datetime.fromisoformat(ts)
    return None


def set_last_exported(workspace_id: str, ts: datetime) -> None:
    """Update the last exported timestamp for a workspace."""
    state = _load_state()
    ws = state.setdefault(workspace_id, {})
    ws["last_exported"] = ts.isoformat()
    ws["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_state(state)


def get_state_summary() -> dict:
    """Return full state for display."""
    return _load_state()
