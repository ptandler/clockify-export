"""Tests for clockify_export.export module."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from clockify_export.export import (
    CSV_HEADERS,
    _cleanup_old_current_month_files,
    _fmt_date,
    _fmt_time,
    _is_current_month,
    _sanitize_dirname,
    export_workspace,
)


class TestFmtDate:
    """Tests for _fmt_date function."""

    def test_valid_iso(self):
        assert _fmt_date("2026-01-15T09:00:00Z") == "2026-01-15"

    def test_valid_iso_with_tz(self):
        assert _fmt_date("2026-01-15T09:00:00+00:00") == "2026-01-15"

    def test_none(self):
        assert _fmt_date(None) == ""

    def test_empty_string(self):
        assert _fmt_date("") == ""


class TestFmtTime:
    """Tests for _fmt_time function."""

    def test_valid_iso(self):
        assert _fmt_time("2026-01-15T09:30:00Z") == "09:30"

    def test_valid_iso_with_tz(self):
        assert _fmt_time("2026-01-15T09:30:00+00:00") == "09:30"

    def test_none(self):
        assert _fmt_time(None) == ""

    def test_empty_string(self):
        assert _fmt_time("") == ""


class TestSanitizeDirname:
    """Tests for _sanitize_dirname function."""

    def test_special_chars(self):
        assert _sanitize_dirname('test<>:"/\\|?*name') == "test_________name"

    def test_spaces(self):
        assert _sanitize_dirname("  spaced name  ") == "spaced name"

    def test_empty(self):
        assert _sanitize_dirname("") == ""

    def test_unicode(self):
        assert _sanitize_dirname("ünïcödé") == "ünïcödé"

    def test_no_special_chars(self):
        assert _sanitize_dirname("normal-name") == "normal-name"


class TestIsCurrentMonth:
    """Tests for _is_current_month function."""

    def test_current_month(self):
        now = datetime.now(timezone.utc)
        assert _is_current_month(str(now.year), f"{now.month:02d}") is True

    def test_past_month(self):
        now = datetime.now(timezone.utc)
        if now.month == 1:
            year, month = now.year - 1, 12
        else:
            year, month = now.year, now.month - 1
        assert _is_current_month(str(year), f"{month:02d}") is False

    def test_future_month(self):
        now = datetime.now(timezone.utc)
        if now.month == 12:
            year, month = now.year + 1, 1
        else:
            year, month = now.year, now.month + 1
        assert _is_current_month(str(year), f"{month:02d}") is False


class TestCleanupOldCurrentMonthFiles:
    """Tests for _cleanup_old_current_month_files function."""

    def test_removes_old_files(self, tmp_path):
        year_dir = tmp_path / "2026"
        year_dir.mkdir()
        current_file = year_dir / "ws_2026-01-2026-01-15.csv"
        old_file = year_dir / "ws_2026-01-2026-01-10.csv"
        current_file.write_text("data")
        old_file.write_text("old data")
        _cleanup_old_current_month_files(year_dir, "ws", "2026", "01", "2026-01-15")
        assert current_file.exists()
        assert not old_file.exists()

    def test_keeps_current_file(self, tmp_path):
        year_dir = tmp_path / "2026"
        year_dir.mkdir()
        current_file = year_dir / "ws_2026-01-2026-01-15.csv"
        current_file.write_text("data")
        _cleanup_old_current_month_files(year_dir, "ws", "2026", "01", "2026-01-15")
        assert current_file.exists()

    def test_no_files(self, tmp_path):
        year_dir = tmp_path / "2026"
        year_dir.mkdir()
        _cleanup_old_current_month_files(year_dir, "ws", "2026", "01", "2026-01-15")


class TestExportWorkspace:
    """Integration tests for export_workspace function."""

    def test_export_creates_csv_files(self, tmp_path, mock_clockify_api):
        output_dir = tmp_path / "export"
        mock_api = mock_clockify_api
        mock_api.get_time_entries.return_value = [
            {
                "id": "e1",
                "timeInterval": {"start": "2026-01-15T09:00:00Z", "end": "2026-01-15T17:00:00Z", "duration": "PT8H", "timeZone": "UTC"},
                "projectId": "proj1",
                "taskId": "task1",
                "tagIds": ["tag1"],
                "description": "Test",
                "billable": True,
                "hourlyRate": {"amount": 5000, "currency": "USD"},
                "type": "REGULAR",
            }
        ]

        counts, latest = export_workspace(
            mock_api, "ws123", "Test Workspace", output_dir, since=None, use_cache=False
        )

        assert counts == {"2026-01": 1}
        assert latest == datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc)
        csv_files = list(output_dir.rglob("*.csv"))
        assert len(csv_files) == 1
        with open(csv_files[0]) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["Project"] == "Project Alpha"
            assert rows[0]["Customer"] == "Client A"

    def test_export_groups_by_month(self, tmp_path, mock_clockify_api):
        output_dir = tmp_path / "export"
        mock_api = mock_clockify_api
        mock_api.get_time_entries.return_value = [
            {
                "id": "e1",
                "timeInterval": {"start": "2026-01-15T09:00:00Z", "end": "2026-01-15T17:00:00Z", "duration": "PT8H", "timeZone": "UTC"},
                "projectId": "proj1",
                "taskId": None,
                "tagIds": [],
                "description": "Jan",
                "billable": True,
                "hourlyRate": {"amount": 5000, "currency": "USD"},
                "type": "REGULAR",
            },
            {
                "id": "e2",
                "timeInterval": {"start": "2026-02-01T09:00:00Z", "end": "2026-02-01T17:00:00Z", "duration": "PT8H", "timeZone": "UTC"},
                "projectId": "proj1",
                "taskId": None,
                "tagIds": [],
                "description": "Feb",
                "billable": True,
                "hourlyRate": {"amount": 5000, "currency": "USD"},
                "type": "REGULAR",
            },
        ]

        counts, latest = export_workspace(
            mock_api, "ws123", "Test Workspace", output_dir, since=None, use_cache=False
        )

        assert counts == {"2026-01": 1, "2026-02": 1}
        csv_files = list(output_dir.rglob("*.csv"))
        assert len(csv_files) == 2

    def test_export_respects_since_filter(self, tmp_path, mock_clockify_api):
        output_dir = tmp_path / "export"
        mock_api = mock_clockify_api
        # Mock get_time_entries to return different results based on since parameter
        def mock_get_time_entries(workspace_id, user_id, start=None, end=None):
            if start and start >= datetime(2026, 2, 1, tzinfo=timezone.utc):
                return [
                    {
                        "id": "e2",
                        "timeInterval": {"start": "2026-02-01T09:00:00Z", "end": "2026-02-01T17:00:00Z", "duration": "PT8H", "timeZone": "UTC"},
                        "projectId": "proj1",
                        "taskId": None,
                        "tagIds": [],
                        "description": "Feb",
                        "billable": True,
                        "hourlyRate": {"amount": 5000, "currency": "USD"},
                        "type": "REGULAR",
                    }
                ]
            return [
                {
                    "id": "e1",
                    "timeInterval": {"start": "2026-01-15T09:00:00Z", "end": "2026-01-15T17:00:00Z", "duration": "PT8H", "timeZone": "UTC"},
                    "projectId": "proj1",
                    "taskId": None,
                    "tagIds": [],
                    "description": "Jan",
                    "billable": True,
                    "hourlyRate": {"amount": 5000, "currency": "USD"},
                    "type": "REGULAR",
                },
                {
                    "id": "e2",
                    "timeInterval": {"start": "2026-02-01T09:00:00Z", "end": "2026-02-01T17:00:00Z", "duration": "PT8H", "timeZone": "UTC"},
                    "projectId": "proj1",
                    "taskId": None,
                    "tagIds": [],
                    "description": "Feb",
                    "billable": True,
                    "hourlyRate": {"amount": 5000, "currency": "USD"},
                    "type": "REGULAR",
                },
            ]
        mock_api.get_time_entries.side_effect = mock_get_time_entries
        since = datetime(2026, 2, 1, tzinfo=timezone.utc)

        counts, _ = export_workspace(
            mock_api, "ws123", "Test Workspace", output_dir, since=since, use_cache=False
        )

        assert counts == {"2026-02": 1}

    def test_export_uses_cache(self, tmp_path, mock_clockify_api):
        output_dir = tmp_path / "export"
        mock_api = mock_clockify_api

        counts, _ = export_workspace(
            mock_api, "ws123", "Test Workspace", output_dir, since=None, use_cache=True
        )

        mock_api.get_projects.assert_called_once()
        mock_api.get_clients.assert_called_once()
        mock_api.get_tags.assert_called_once()

    def test_export_no_cache(self, tmp_path, mock_clockify_api):
        output_dir = tmp_path / "export"
        mock_api = mock_clockify_api

        counts, _ = export_workspace(
            mock_api, "ws123", "Test Workspace", output_dir, since=None, use_cache=False
        )

        mock_api.get_projects.assert_called_once()
        mock_api.get_clients.assert_called_once()
        mock_api.get_tags.assert_called_once()

    def test_export_sanitizes_workspace_name(self, tmp_path, mock_clockify_api):
        output_dir = tmp_path / "export"
        mock_api = mock_clockify_api
        mock_api.get_time_entries.return_value = [
            {
                "id": "e1",
                "timeInterval": {"start": "2026-01-15T09:00:00Z", "end": "2026-01-15T17:00:00Z", "duration": "PT8H", "timeZone": "UTC"},
                "projectId": "proj1",
                "taskId": None,
                "tagIds": [],
                "description": "Test",
                "billable": True,
                "hourlyRate": {"amount": 5000, "currency": "USD"},
                "type": "REGULAR",
            }
        ]

        counts, _ = export_workspace(
            mock_api, "ws123", "Test/Workspace:Name", output_dir, since=None, use_cache=False
        )

        csv_files = list(output_dir.rglob("*.csv"))
        assert len(csv_files) == 1
        assert "Test_Workspace_Name" in str(csv_files[0])

    def test_export_current_month_filename_has_date(self, tmp_path, mock_clockify_api):
        output_dir = tmp_path / "export"
        mock_api = mock_clockify_api
        now = datetime.now(timezone.utc)
        mock_api.get_time_entries.return_value = [
            {
                "id": "e1",
                "timeInterval": {"start": f"{now.year}-{now.month:02d}-15T09:00:00Z", "end": f"{now.year}-{now.month:02d}-15T17:00:00Z", "duration": "PT8H", "timeZone": "UTC"},
                "projectId": "proj1",
                "taskId": None,
                "tagIds": [],
                "description": "Current month",
                "billable": True,
                "hourlyRate": {"amount": 5000, "currency": "USD"},
                "type": "REGULAR",
            }
        ]

        counts, _ = export_workspace(
            mock_api, "ws123", "Test Workspace", output_dir, since=None, use_cache=False
        )

        csv_files = list(output_dir.rglob("*.csv"))
        assert len(csv_files) == 1
        assert now.strftime("%Y-%m-%d") in csv_files[0].name

    def test_export_handles_missing_project(self, tmp_path, mock_clockify_api):
        output_dir = tmp_path / "export"
        mock_api = mock_clockify_api
        mock_api.get_time_entries.return_value = [
            {
                "id": "e1",
                "timeInterval": {"start": "2026-01-15T09:00:00Z", "end": "2026-01-15T17:00:00Z", "duration": "PT8H", "timeZone": "UTC"},
                "projectId": "unknown_proj",
                "taskId": None,
                "tagIds": [],
                "description": "No project",
                "billable": True,
                "hourlyRate": {"amount": 5000, "currency": "USD"},
                "type": "REGULAR",
            }
        ]

        counts, _ = export_workspace(
            mock_api, "ws123", "Test Workspace", output_dir, since=None, use_cache=False
        )

        csv_files = list(output_dir.rglob("*.csv"))
        with open(csv_files[0]) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert rows[0]["Project"] == ""
            assert rows[0]["Customer"] == ""