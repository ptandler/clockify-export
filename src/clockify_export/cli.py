"""CLI entry point for clockify-export."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone

from .api import ClockifyAPI, ClockifyError
from .config import CONFIG_FILE, Config, create_config_file, get_last_exported, set_last_exported
from .export import export_workspace
from . import __version__


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="clockify-export",
        description="Export Clockify time entries to CSV",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=None,
        help="Output directory for CSV files (default: ./export or config export_dir)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Clockify API key (overrides config/env). Alternatively use CLOCKIFY_API_KEY or config.",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Full export: ignore incremental state, export everything",
    )
    parser.add_argument(
        "--from",
        dest="from_date",
        type=str,
        default=None,
        help="Export entries from this date (YYYY-MM-DD). Overrides incremental state.",
    )
    parser.add_argument(
        "--workspace",
        "-w",
        action="append",
        help="Export only this workspace (can be repeated). Default: all workspaces.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show export state and exit",
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help="Create ~/.config/clockify-export/config.toml and exit",
    )
    args = parser.parse_args()

    if args.init_config:
        path = create_config_file()
        print(f"Created config file: {path}")
        print("Edit it to set your API key and export directory.")
        return

    # Load configuration
    cfg = Config.load(args)

    if not cfg.api_key:
        print(
            "Error: No API key found.\n"
            "  Set it via:\n"
            "    1.  --api-key flag\n"
            "    2.  CLOCKIFY_API_KEY environment variable\n"
            "    3.  ~/.config/clockify-export/config.toml\n"
            "    4.  .env file in the current directory\n"
            "  Run: clockify-export --init-config to create a config file.",
            file=sys.stderr,
        )
        sys.exit(1)

    api = ClockifyAPI(cfg.api_key)

    # Status mode
    if args.status:
        import json
        from .config import get_state
        state = get_state()
        print(f"Export directory: {cfg.export_dir}")
        print(f"Config file: {CONFIG_FILE}")
        if not state:
            print("No export state found.")
            return
        print("Export state:")
        for ws_id, info in state.items():
            print(f"  {ws_id}: last_exported={info.get('last_exported', 'never')}")
        return

    # Discover workspaces
    try:
        workspaces = api.get_workspaces()
    except ClockifyError as e:
        print(f"Error fetching workspaces: {e}", file=sys.stderr)
        sys.exit(1)

    if not workspaces:
        print("No workspaces found.", file=sys.stderr)
        sys.exit(1)

    # Filter workspaces if specified
    if cfg.workspaces:
        ws_names = set(cfg.workspaces)
        workspaces = [w for w in workspaces if w.get("name") in ws_names]
        if not workspaces:
            print(
                f"Workspace(s) not found. Available: {[w['name'] for w in api.get_workspaces()]}",
                file=sys.stderr,
            )
            sys.exit(1)

    print(f"Found {len(workspaces)} workspace(s): {', '.join(w['name'] for w in workspaces)}")
    print()

    output_dir = cfg.export_dir
    for ws in workspaces:
        ws_id = ws["id"]
        ws_name = ws["name"]
        print(f"── {ws_name} ({ws_id}) ──")

        # Determine start date
        since = None
        if cfg.from_date:
            # Explicit --from flag overrides everything
            since = datetime.strptime(cfg.from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            print(f"  --from: fetching since {cfg.from_date}")
        elif not cfg.full:
            last = get_last_exported(ws_id)
            if last:
                # Start from the day after last export
                since = datetime.fromisoformat(last) + timedelta(days=1)
                print(f"  Incremental: fetching since {since.strftime('%Y-%m-%d')}")
            else:
                print("  No prior export found — exporting all data")
        else:
            print("  Full export mode")

        try:
            counts = export_workspace(api, ws_id, ws_name, output_dir, since=since)
            if counts:
                # Update state to the latest entry date
                latest_month = max(counts.keys())
                latest_ts = datetime.strptime(latest_month, "%Y-%m").replace(tzinfo=timezone.utc)
                # Set to end of month to mark the whole month as exported
                from calendar import monthrange
                _, last_day = monthrange(latest_ts.year, latest_ts.month)
                latest_ts = latest_ts.replace(day=last_day)
                set_last_exported(ws_id, latest_ts.isoformat())
                total = sum(counts.values())
                print(f"  Total: {total} entries across {len(counts)} month(s)")
            else:
                print("  No entries found")
        except ClockifyError as e:
            print(f"  Error: {e}", file=sys.stderr)
        print()

    print("Done.")


if __name__ == "__main__":
    main()