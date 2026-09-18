"""CSV export logic for Clockify time entries."""

from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path

from .api import ClockifyAPI, parse_iso_duration_to_hours
from .cache import load_workspace_data, save_workspace_data, DEFAULT_MAX_AGE_SECONDS

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


def _is_current_month(year: str, month: str) -> bool:
    """Check if the given year/month is the current month."""
    now = datetime.now(timezone.utc)
    return int(year) == now.year and int(month) == now.month


def _cleanup_old_current_month_files(year_dir: Path, safe_ws_name: str, year: str, month: str, current_date_str: str) -> None:
    """Remove old current-month files with different dates."""
    pattern = f"{safe_ws_name}_{year}-{month}-*.csv"
    for old_file in year_dir.glob(pattern):
        if current_date_str not in old_file.name:
            print(f"  Removing old current-month file: {old_file.relative_to(year_dir.parent.parent)}")
            old_file.unlink(missing_ok=True)


def export_workspace(
    api: ClockifyAPI,
    workspace_id: str,
    workspace_name: str,
    output_dir: Path,
    since: datetime | None = None,
    use_cache: bool = True,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
) -> tuple[dict[str, int], datetime | None]:
    """Export all time entries for a workspace, grouped by year/month.

    Directory structure: {output_dir}/{workspace_name}/{year}/{MM}.csv
    Returns (counts_dict, latest_entry_date) where latest_entry_date is the
    most recent entry's start time (or None if no entries).
    """
    # Resolve current user
    user = api.get_current_user()
    user_id = user["id"]
    print(f"  User: {user.get('name', user_id)}")

    # Try to load from cache first
    if use_cache:
        cached = load_workspace_data(output_dir, workspace_id, max_age_seconds)
        if cached:
            projects = {p["id"]: p for p in cached.get("projects", [])}
            clients = {c["id"]: c for c in cached.get("clients", [])}
            tags = {t["id"]: t for t in cached.get("tags", [])}
            print("  Using cached projects, clients, tags")
        else:
            # Fetch lookup tables
            print("  Fetching projects...")
            projects = {p["id"]: p for p in api.get_projects(workspace_id)}
            print("  Fetching clients...")
            clients = {c["id"]: c for c in api.get_clients(workspace_id)}
            print("  Fetching tags...")
            tags = {t["id"]: t for t in api.get_tags(workspace_id)}
            # Save to cache
            save_workspace_data(output_dir, workspace_id, list(projects.values()), list(clients.values()), list(tags.values()))
    else:
        # Fetch lookup tables (no cache)
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

    # Group by year/month, track latest entry date
    by_month: dict[str, list[dict]] = {}
    latest_entry_dt: datetime | None = None
    for entry in entries:
        start_str = entry.get("timeInterval", {}).get("start")
        if not start_str:
            continue
        dt = datetime.fromisoformat(start_str)
        if latest_entry_dt is None or dt > latest_entry_dt:
            latest_entry_dt = dt
        month_key = dt.strftime("%Y-%m")
        by_month.setdefault(month_key, []).append(entry)

    # Write CSVs: output_dir / workspace_name / year / <workspace>_<year>-<month>.csv
    safe_ws_name = _sanitize_dirname(workspace_name)
    ws_dir = output_dir / safe_ws_name
    counts: dict[str, int] = {}
    now = datetime.now(timezone.utc)
    current_date_str = now.strftime("%Y-%m-%d")
    for month_key, month_entries in sorted(by_month.items()):
        year, month = month_key.split("-")
        year_dir = ws_dir / year
        year_dir.mkdir(parents=True, exist_ok=True)

        # For current month, include date in filename; otherwise just year-month
        if _is_current_month(year, month):
            csv_filename = f"{safe_ws_name}_{year}-{month}-{current_date_str}.csv"
        else:
            csv_filename = f"{safe_ws_name}_{year}-{month}.csv"
        csv_path = year_dir / csv_filename

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

        # Clean up old current-month files if this is the current month
        if _is_current_month(year, month):
            _cleanup_old_current_month_files(year_dir, safe_ws_name, year, month, current_date_str)

        counts[month_key] = len(month_entries)
        print(f"  Wrote {csv_path.relative_to(output_dir)} ({len(month_entries)} entries)")

    return counts, latest_entry_dt
