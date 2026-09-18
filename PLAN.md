# Development Plan

## Current Version: 0.2.0

---

## ✅ Completed (v0.2.0)

- [x] Cache for workspaces, projects, clients, tags (1-week expiry)
- [x] `--no-cache` flag to bypass cache
- [x] Current month CSV includes date in filename (e.g., `...-2026-09-17.csv`)
- [x] Auto-cleanup of old current-month files
- [x] Mutually exclusive `--from`, `--last`, `--refetch` options
- [x] Removed `last` from config file (only CLI)

---

## 🔄 In Progress

- [ ] Auto-refresh cache when unknown project/client/tag ID encountered during entry processing

---

## 📋 Backlog

### Cache Improvements
- [ ] Add cache stats/debug command (`--cache-status`)
- [ ] Add config option for cache TTL (default 1 week)
- [ ] Cache workspaces list (currently only workspace data cached)

### Export Features
- [ ] Add `--dry-run` to show what would be exported without writing
- [ ] Add `--format json` output option
- [ ] Support exporting to single combined CSV (optionally)

### Reliability
- [ ] Add retry logic with exponential backoff for API requests
- [ ] Handle HTTP 429 rate limits gracefully (wait and retry)

### Developer Experience
- [ ] Add `--verbose` / `--quiet` flags
- [ ] Add progress bar for long exports

---

## 🐛 Known Issues

- None currently
