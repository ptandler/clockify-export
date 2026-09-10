"""CSV export logic for Clockify time entries."""

from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path

from .api import ClockifyAPI, parse_iso_duration_to_hours

CSV_HEADERS = [
    "Date",
    "Start",
    "End",
    "Duration (h)",
    "Project",
    "Customer",
    "Task",
    "Description",
    "Tags",
    "Billable",
    "Hourly Rate",
    "Currency",
    "Type",
    "Timezone",
]


def _fmt_date(iso_str: str | None) -> str:
    if not iso_str:
        return ""
    dt = datetime.fromisoformat(iso_str)
    return dt.strftime("%Y-%m-%d")


def _fmt_time(iso_str: str | None) -> str:
    if not iso_str:
        return ""
    dt = datetime.fromisoformat(iso_str)
    return dt.strftime("%H:%M")


def _sanitize_dirname(name: str) -> str:
    """Make a string safe for use as a directory name."""
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip()


def export_workspace(
    api: ClockifyAPI,
    workspace_id: str,
    workspace_name: str,
    output_dir: Path,
    since: datetime | None = None,
) -> dict[str, int]:
    """Export all time entries for a workspace, grouped by year/month.

    Directory structure: {output_dir}/{workspace_name}/{year}/{MM}.csv
    Returns dict of {YYYY-MM: row_count}.
    """
    # Resolve current user
    user = api.get_current_user()
    user_id = user["id"]
    print(f"  User: {user.get('name', user_id)}")

    # Fetch lookup tables
    print("  Fetching projects...")
    projects = {p["id"]: p for p in api.get_projects(workspace_id)}
    print("  Fetching clients...")
    clients = {c["id"]: c for c in api.get_clients(workspace_id)}
    print("  Fetching tags...")
    tags = {t["id"]: t for t in api.get_tags(workspace_id)}

    # Fetch time entries first to know which projects have entries
    print("  Fetching time entries...")
    entries = api.get_time_entries(workspace_id, user_id, start=since)
    print(f"  Got {len(entries)} entries")

    # Only fetch tasks for projects that have entries (saves API calls)
    project_ids_in_entries = {e.get("projectId") for e in entries if e.get("projectId")}
    print(f"  Fetching tasks for {len(project_ids_in_entries)} active projects...")
    tasks: dict[str, dict] = {}
    for proj_id in project_ids_in_entries:
        for t in api.get_tasks(workspace_id, proj_id):
            tasks[t["id"]] = t

    # Build project -> client mapping
    project_client: dict[str, str] = {}
    for p in projects.values():
        client_id = p.get("clientId")
        if client_id and client_id in clients:
            project_client[p["id"]] = clients[client_id].get("name", "")

    # Group by year/month
    by_month: dict[str, list[dict]] = {}
    for entry in entries:
        start_str = entry.get("timeInterval", {}).get("start")
        if not start_str:
            continue
        dt = datetime.fromisoformat(start_str)
        month_key = dt.strftime("%Y-%m")
        by_month.setdefault(month_key, []).append(entry)

    # Write CSVs: output_dir / workspace_name / year / <workspace>_<year>-<month>.csv
    safe_ws_name = _sanitize_dirname(workspace_name)
    ws_dir = output_dir / safe_ws_name
    counts: dict[str, int] = {}
    for month_key, month_entries in sorted(by_month.items()):
        year, month = month_key.split("-")
        year_dir = ws_dir / year
        year_dir.mkdir(parents=True, exist_ok=True)
        # Filename carries workspace + year so files stay identifiable when moved
        csv_path = year_dir / f"{safe_ws_name}_{year}-{month}.csv"

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)
            for entry in sorted(
                month_entries,
                key=lambda e: e.get("timeInterval", {}).get("start", ""),
            ):
                start = entry.get("timeInterval", {}).get("start")
                end = entry.get("timeInterval", {}).get("end")
                duration_str = entry.get("timeInterval", {}).get("duration", "")
                duration_h = parse_iso_duration_to_hours(duration_str) if duration_str else 0

                project_id = entry.get("projectId", "")
                task_id = entry.get("taskId", "")
                tag_ids = entry.get("tagIds") or []

                # Hourly rate is in cents
                hourly_rate_obj = entry.get("hourlyRate") or {}
                rate_cents = hourly_rate_obj.get("amount", 0)
                currency = hourly_rate_obj.get("currency", "")

                writer.writerow([
                    _fmt_date(start),
                    _fmt_time(start),
                    _fmt_time(end),
                    duration_h,
                    projects.get(project_id, {}).get("name", ""),
                    project_client.get(project_id, ""),
                    tasks.get(task_id, {}).get("name", ""),
                    entry.get("description", ""),
                    ", ".join(tags.get(tid, {}).get("name", "") for tid in tag_ids),
                    entry.get("billable", ""),
                    f"{rate_cents / 100:.2f}" if rate_cents else "",
                    currency,
                    entry.get("type", ""),
                    (entry.get("timeInterval") or {}).get("timeZone", ""),
                ])

        counts[month_key] = len(month_entries)
        print(f"  Wrote {csv_path.relative_to(output_dir)} ({len(month_entries)} entries)")

    return counts
