"""Configuration management.

Loads config from (in priority order):
1. CLI flags (highest)
2. Environment variables (CLOCKIFY_API_KEY, CLOCKIFY_EXPORT_DIR)
3. ~/.config/clockify-export/config.toml
4. ~/.config/clockify-export/config.json (deprecated fallback)
5. Defaults (lowest)
"""

from __future__ import annotations

import json
import os
import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "clockify-export"
CONFIG_FILE = CONFIG_DIR / "config.toml"
LEGACY_CONFIG_FILE = CONFIG_DIR / "config.json"
STATE_FILE = CONFIG_DIR / "state.json"

DEFAULTS = {
    "api_key": None,
    "export_dir": "export",
    "refetch": 1,
}

CONFIG_HELP = """
Supported configuration options (config.toml):
  api_key       - Clockify API key (required)
  export_dir    - Output directory for CSV files (default: "export")
  refetch       - Number of months to re-fetch from last exported date (default: 1)

Example config.toml:
  # Clockify export configuration
  api_key = "YOUR_API_KEY"
  export_dir = "export"
  refetch = 1
"""


@dataclass
class Config:
    api_key: str
    export_dir: Path
    full: bool = False
    workspaces: list[str] = field(default_factory=list)
    from_date: str | None = None
    refetch: int = 0

    @classmethod
    def load(cls, args=None) -> Config:
        """Load config from file, env, and CLI args. CLI args win."""
        file_cfg = _load_config_file()

        # Priority: CLI > env > config file > defaults
        api_key = (
            getattr(args, "api_key", None)
            or os.environ.get("CLOCKIFY_API_KEY")
            or file_cfg.get("api_key")
        )
        if not api_key:
            # Try .env file as last resort
            api_key = _load_dotenv()

        export_dir = Path(
            getattr(args, "output_dir", None)
            or os.environ.get("CLOCKIFY_EXPORT_DIR")
            or file_cfg.get("export_dir")
            or DEFAULTS["export_dir"]
        )

        full = getattr(args, "full", False) if args else False
        workspaces = getattr(args, "workspace", []) if args else []
        from_date = getattr(args, "from_date", None) if args else None
        
        # For refetch: CLI arg wins, then config file, then default
        if args and getattr(args, "refetch", None) is not None:
            refetch = args.refetch
        else:
            refetch = file_cfg.get("refetch", DEFAULTS["refetch"])

        return cls(
            api_key=api_key or "",
            export_dir=export_dir,
            full=full,
            workspaces=workspaces or [],
            from_date=from_date,
            refetch=refetch,
        )


def _load_config_file() -> dict:
    """Read config.toml (preferred) or legacy config.json."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "rb") as f:
                return tomllib.load(f)
        except (tomllib.TOMLDecodeError, OSError):
            pass
    if LEGACY_CONFIG_FILE.exists():
        try:
            import warnings
            warnings.warn(
                f"{LEGACY_CONFIG_FILE} is deprecated, use {CONFIG_FILE} instead",
                DeprecationWarning,
                stacklevel=2,
            )
            return json.loads(LEGACY_CONFIG_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _load_dotenv() -> str | None:
    """Read CLOCKIFY_API_KEY from .env in current directory."""
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("CLOCKIFY_API_KEY="):
                return line.split("=", 1)[1].strip().strip("\"'")
    return None


def create_config_file(api_key: str = "", export_dir: str = "export") -> Path:
    """Create a default TOML config file. Returns the path."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        "# Clockify export configuration\n"
        f'api_key = "{api_key}"\n'
        f'export_dir = "{export_dir}"\n'
        "# Number of months to re-fetch from last exported date (default: 1)\n"
        "refetch = 1\n"
    )
    return CONFIG_FILE


def parse_from_date(date_str: str) -> datetime:
    """Parse --from date string (YYYY-MM or YYYY-MM-DD) and return first day of that month."""
    parts = date_str.split("-")
    if len(parts) < 2:
        raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM or YYYY-MM-DD")
    year = int(parts[0])
    month = int(parts[1])
    return datetime(year, month, 1, tzinfo=timezone.utc)


def calculate_last_months(last: int) -> datetime:
    """Calculate the first day of the month that is 'last' complete months ago."""
    now = datetime.now(timezone.utc)
    # Go back 'last' months from the current month, then get the first day of that month
    # If last=1, we want last complete month (not current month)
    year = now.year
    month = now.month - last
    while month <= 0:
        month += 12
        year -= 1
    return datetime(year, month, 1, tzinfo=timezone.utc)


def calculate_refetch_date(refetch: int, last_exported: str | None) -> datetime | None:
    """Calculate the date to start re-fetching from, going back 'refetch' months from last exported."""
    if not last_exported or refetch <= 0:
        return None
    last_dt = datetime.fromisoformat(last_exported)
    year = last_dt.year
    month = last_dt.month - refetch
    while month <= 0:
        month += 12
        year -= 1
    return datetime(year, month, 1, tzinfo=timezone.utc)


def get_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_state(state: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


def get_last_exported(workspace_id: str) -> str | None:
    state = get_state()
    return state.get(workspace_id, {}).get("last_exported")


def set_last_exported(workspace_id: str, timestamp: str) -> None:
    state = get_state()
    ws = state.setdefault(workspace_id, {})
    ws["last_exported"] = timestamp
    ws["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_state(state)