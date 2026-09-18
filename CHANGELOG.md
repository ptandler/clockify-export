# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Auto-refresh cache when unknown project/client/tag ID encountered during entry processing
- Cache for workspaces, projects, clients, tags with 1-week expiry
- `--no-cache` flag to bypass cache and force fresh API fetch
- Current month CSV includes date in filename (e.g., `...-2026-09-17.csv`)
- Auto-cleanup of old current-month files with different dates
- Mutually exclusive date range options: `--from`, `--last`, `--refetch`

### Changed
- Removed `last` option from config file (prevents inconsistent behavior)
- `last` is now CLI-only flag
- Cache now stores timestamp and expires after 1 week

### Fixed
- Cache validation: expired cache entries are ignored

---

## [0.1.0] - 2026-09-10

### Added
- Initial release
- Multi-workspace export
- Incremental export with state tracking
- Monthly CSV output per workspace/year
- Config file support (`~/.config/clockify-export/config.toml`)
- `--full`, `--from`, `--last`, `--refetch`, `--workspace`, `--status` flags
- Zero dependencies (stdlib only)
- systemd timer support for scheduled exports
