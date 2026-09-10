"""CLI entry point for clockify-export."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .api import ClockifyAPI, ClockifyError
from .export import export_workspace
from .state import get_last_exported, get_state_summary, set_last_exported


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="clockify-export",
        description="Export Clockify time entries to CSV",
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        default=Path("export"),
        help="Output directory for CSV files (default: ./export)",
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
    args = parser.parse_args()

    # Load API key
    api_key = os.environ.get("CLOCKIFY_API_KEY")
    if not api_key:
        env_file = Path(".env")
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line.startswith("CLOCKIFY_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip("\"'")
                    break
    if not api_key:
        print("Error: CLOCKIFY_API_KEY not set. Export it or put it in .env", file=sys.stderr)
        sys.exit(1)

    api = ClockifyAPI(api_key)

    # Status mode
    if args.status:
        state = get_state_summary()
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
    if args.workspace:
        ws_names = set(args.workspace)
        workspaces = [w for w in workspaces if w.get("name") in ws_names]
        if not workspaces:
            print(f"Workspace(s) not found. Available: {[w['name'] for w in api.get_workspaces()]}", file=sys.stderr)
            sys.exit(1)

    print(f"Found {len(workspaces)} workspace(s): {', '.join(w['name'] for w in workspaces)}")
    print()

    for ws in workspaces:
        ws_id = ws["id"]
        ws_name = ws["name"]
        print(f"── {ws_name} ({ws_id}) ──")

        # Determine start date
        since = None
        if args.from_date:
            # Explicit --from flag overrides everything
            since = datetime.strptime(args.from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            print(f"  --from: fetching since {args.from_date}")
        elif not args.full:
            last = get_last_exported(ws_id)
            if last:
                # Start from the day after last export
                since = last + timedelta(days=1)
                print(f"  Incremental: fetching since {since.strftime('%Y-%m-%d')}")
            else:
                print("  No prior export found — exporting all data")
        else:
            print("  Full export mode")

        try:
            counts = export_workspace(api, ws_id, ws_name, args.output_dir, since=since)
            if counts:
                # Update state to the latest entry date
                latest_month = max(counts.keys())
                latest_ts = datetime.strptime(latest_month, "%Y-%m").replace(tzinfo=timezone.utc)
                # Set to end of month to mark the whole month as exported
                from calendar import monthrange
                _, last_day = monthrange(latest_ts.year, latest_ts.month)
                latest_ts = latest_ts.replace(day=last_day)
                set_last_exported(ws_id, latest_ts)
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
