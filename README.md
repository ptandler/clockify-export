# Clockify Export

Export your Clockify time entries to CSV files, even on the Free plan.

In April/May 2026, Clockify restricted the Free plan: CSV/Excel exports and
reports longer than 31 days now require a paid plan. The API itself, however,
is still available on the Free plan (30 requests/hour/workspace).

This tool uses the **time entries API** (not the reports API), so it is **not**
subject to the 31-day reporting window. It paginates through all your entries
and writes one CSV per calendar month.

## Features

- ✅ **Multi-workspace** — exports all your workspaces (or select with `-w`)
- ✅ **Incremental** — remembers what was exported and only fetches new entries
- ✅ **Monthly CSVs** — one file per calendar month, current month gets re-exported/overwritten
- ✅ **Per-workspace stat** — state is tracked in `~/.config/clockify-export/state.json`
- ✅ **Zero dependencies** — stdlib only (`urllib`, `csv`, `json`), Python ≥ 3.11
- ✅ **Config file** — API key + export path in `~/.config/clockify-export/config.toml`

## Installation

Requires [uv](https://docs.astral.sh/uv/) (or any Python 3.11+ + pip).

### Global install (recommended, adds `clockify-export` to your PATH)

```bash
uv tool install clockify-export      # from PyPI
# or from a local checkout:
uv tool install .
```

Updates: `uv tool upgrade clockify-export`.

### Development (from a checkout)

```bash
uv sync
```

## Setup

### 1. API key

Generate an API key in Clockify: **Profile → Preferences → API → Manage API Keys → Generate**.

Provide it via one of (highest priority first):

```bash
# a) Config file (recommended)
clockify-export --init-config
# then edit ~/.config/clockify-export/config.toml:
#
#   # Clockify export configuration
#   api_key = "YOUR_KEY"
#   export_dir = "export"

# b) Environment variable
export CLOCKIFY_API_KEY=YOUR_KEY

# c) .env file in the project directory
echo "CLOCKIFY_API_KEY=YOUR_KEY" > .env

# d) Command line flag
clockify-export --api-key YOUR_KEY
```

> Note: TOML is parsed with Python's stdlib `tomllib` — no extra dependency.

### 2. Export directory

Defaults to `./export`. Override via config file or `-o` flag:

```bash
clockify-export -o /data/clockify
```

## Usage

```bash
# Full export of all workspaces (everything since the beginning)
clockify-export --full

# Incremental export (default — only fetches entries after last run)
clockify-export

# Export only specific workspace(s)
clockify-export -w "Peter's workspace"

# Export since a specific date (ignores incremental state)
clockify-export --from 2026-01-01

# Show export state
clockify-export --status
```

## Output structure

```
export/
└── <workspace name>/
    └── <year>/
        └── <workspace name>_<year>-<month>.csv
```

Each filename carries the workspace and year, so files stay identifiable even
if you copy or move them out of the directory tree:

```
export/etalytics workspace/2026/etalytics workspace_2026-09.csv
```

### CSV columns

| Column | Description |
|--------|-------------|
| `Date` | Entry date (YYYY-MM-DD) |
| `Start` | Start time (HH:MM, UTC) |
| `End` | End time (HH:MM, UTC) |
| `Duration (h)` | Duration in decimal hours (e.g. 1.5 = 1h 30m) |
| `Project` | Project name |
| `Customer` | Client/customer name |
| `Task` | Task name |
| `Description` | Entry description |
| `Tags` | Comma-separated tags |
| `Billable` | True/False |
| `Hourly Rate` | Billable rate (e.g. 13.00) |
| `Currency` | Currency code (e.g. EUR) |
| `Type` | Entry type (REGULAR, BREAK, …) |
| `Timezone` | Timezone of the entry (e.g. Europe/Berlin) |

## How incremental export works

The tool stores the last exported date per workspace in
`~/.config/clockify-export/state.json`:

```json
{
  "5e9d613a265d3c117c6f3aeb": {
    "last_exported": "2026-09-30T00:00:00+00:00",
    "updated_at": "2026-09-10T10:20:38.530213+00:00"
  }
}
```

On the next run, entries are fetched starting the day after `last_exported`.
Monthly CSVs are overwritten entirely, so a partially written current month is
always consistent.

## Free plan considerations

- **Rate limit**: 30 API requests/hour/workspace on Free plan. Each page of
  200 entries = 1 request. A full export of thousands of entries can exhaust
  the quota — that's why `--from` and `--full` exist, and why the tool fetches
  tasks only for projects that actually have entries.
- If you hit the rate limit (HTTP 429), wait an hour and run again — the
  incremental state means you won't re-fetch everything.

## Related projects

- [Clockify API docs](https://docs.clockify.me/)
- [damirarh/ClockifyExport](https://github.com/damirarh/ClockifyExport) — C# tool
  using shared reports (paid-only on Free plan now)
- [apet97/clockify-ts-sdk](https://github.com/apet97/clockify-ts-sdk) — community
  TypeScript SDK/CLI

## License

MIT
