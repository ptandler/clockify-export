# Agent Instructions

When generating documentation and comments, be as concise and brief as possible without loosing relevant information.

## Project Files

| File | Purpose |
|------|---------|
| `PLAN.md` | Development roadmap and task tracking |
| `CHANGELOG.md` | Version history (Keep a Changelog format) |
| `README.md` | User documentation |

---

## Updating the Plan

When **adding/removing/starting/resolving tasks**:

1. Edit `PLAN.md`
2. Use status markers:
   - `[ ]` — Not started
   - `🔄` — In progress
3. When a task is implemented, update `CHANGELOG.md` (in "Unreleased" section) and remove from `PLAN.md`

---

## Updating the Changelog

1. Edit `CHANGELOG.md`
3. Keep `[Unreleased]` section for things done since last release
4. Follow [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format

---

## Versioning

This project uses [Semantic Versioning](https://semver.org/):
- **MAJOR** — Breaking changes
- **MINOR** — New features (backward compatible)
- **PATCH** — Bug fixes (backward compatible)

Current version defined in: `pyproject.toml` (also read by `src/clockify_export/__init__.py`)

---

## Code Locations

| Feature | File |
|---------|------|
| CLI entry point | `src/clockify_export/cli.py` |
| Export logic | `src/clockify_export/export.py` |
| API client | `src/clockify_export/api.py` |
| Config/state | `src/clockify_export/config.py` |
| Cache | `src/clockify_export/cache.py` |
