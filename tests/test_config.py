"""Tests for clockify_export.config module."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from clockify_export.config import (
    Config,
    calculate_last_months,
    calculate_refetch_date,
    parse_from_date,
)


class TestParseFromDate:
    """Tests for parse_from_date function."""

    def test_yyyy_mm(self):
        result = parse_from_date("2026-01")
        expected = datetime(2026, 1, 1, tzinfo=timezone.utc)
        assert result == expected

    def test_yyyy_mm_dd(self):
        result = parse_from_date("2026-01-15")
        expected = datetime(2026, 1, 1, tzinfo=timezone.utc)
        assert result == expected

    def test_invalid_format_short(self):
        with pytest.raises(ValueError, match="Invalid date format"):
            parse_from_date("2026")

    def test_invalid_format_no_dash(self):
        with pytest.raises(ValueError, match="Invalid date format"):
            parse_from_date("202601")

    def test_invalid_month(self):
        with pytest.raises(ValueError):
            parse_from_date("2026-13")

    def test_invalid_day(self):
        # parse_from_date only uses year and month, ignores day
        result = parse_from_date("2026-02-30")
        expected = datetime(2026, 2, 1, tzinfo=timezone.utc)
        assert result == expected


class TestCalculateLastMonths:
    """Tests for calculate_last_months function."""

    def test_last_1(self):
        result = calculate_last_months(1)
        now = datetime.now(timezone.utc)
        # Should be first day of last complete month
        if now.month == 1:
            expected = datetime(now.year - 1, 12, 1, tzinfo=timezone.utc)
        else:
            expected = datetime(now.year, now.month - 1, 1, tzinfo=timezone.utc)
        assert result == expected

    def test_last_3(self):
        result = calculate_last_months(3)
        now = datetime.now(timezone.utc)
        month = now.month - 3
        year = now.year
        while month <= 0:
            month += 12
            year -= 1
        expected = datetime(year, month, 1, tzinfo=timezone.utc)
        assert result == expected

    def test_last_12(self):
        result = calculate_last_months(12)
        now = datetime.now(timezone.utc)
        expected = datetime(now.year - 1, now.month, 1, tzinfo=timezone.utc)
        assert result == expected

    def test_last_13_year_rollover(self):
        result = calculate_last_months(13)
        now = datetime.now(timezone.utc)
        month = now.month - 13
        year = now.year
        while month <= 0:
            month += 12
            year -= 1
        expected = datetime(year, month, 1, tzinfo=timezone.utc)
        assert result == expected


class TestCalculateRefetchDate:
    """Tests for calculate_refetch_date function."""

    def test_with_last_exported(self):
        result = calculate_refetch_date(1, "2026-01-15T17:00:00+00:00")
        expected = datetime(2025, 12, 1, tzinfo=timezone.utc)
        assert result == expected

    def test_with_last_exported_3_months(self):
        result = calculate_refetch_date(3, "2026-05-15T17:00:00+00:00")
        expected = datetime(2026, 2, 1, tzinfo=timezone.utc)
        assert result == expected

    def test_with_last_exported_year_rollover(self):
        result = calculate_refetch_date(2, "2026-01-15T17:00:00+00:00")
        expected = datetime(2025, 11, 1, tzinfo=timezone.utc)
        assert result == expected

    def test_no_last_exported(self):
        result = calculate_refetch_date(1, None)
        assert result is None

    def test_zero_refetch(self):
        result = calculate_refetch_date(0, "2026-01-15T17:00:00+00:00")
        assert result is None

    def test_negative_refetch(self):
        result = calculate_refetch_date(-1, "2026-01-15T17:00:00+00:00")
        assert result is None


class TestConfigLoad:
    """Tests for Config.load priority chain."""

    def test_cli_overrides_env(self, monkeypatch):
        monkeypatch.setenv("CLOCKIFY_API_KEY", "env_key")
        args = type("Args", (), {"api_key": "cli_key", "output_dir": None, "full": False, "workspace": [], "from_date": None, "refetch": None})()
        cfg = Config.load(args)
        assert cfg.api_key == "cli_key"

    def test_env_overrides_config_file(self, monkeypatch, temp_config_dir):
        import clockify_export.config as config_module
        config_module.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        config_module.CONFIG_FILE.write_text('api_key = "file_key"\n')
        monkeypatch.setenv("CLOCKIFY_API_KEY", "env_key")
        args = type("Args", (), {"api_key": None, "output_dir": None, "full": False, "workspace": [], "from_date": None, "refetch": None})()
        cfg = Config.load(args)
        assert cfg.api_key == "env_key"

    def test_config_file_overrides_defaults(self, temp_config_dir, monkeypatch):
        import clockify_export.config as config_module
        config_module.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        config_module.CONFIG_FILE.write_text('api_key = "file_key"\nexport_dir = "/custom/export"\nrefetch = 3\n')
        monkeypatch.delenv("CLOCKIFY_API_KEY", raising=False)
        args = type("Args", (), {"api_key": None, "output_dir": None, "full": False, "workspace": [], "from_date": None, "refetch": None})()
        cfg = Config.load(args)
        assert cfg.api_key == "file_key"
        assert str(cfg.export_dir) == "/custom/export"
        assert cfg.refetch == 3

    def test_defaults_when_nothing_set(self, monkeypatch, tmp_path):
        import clockify_export.config as config_module
        # Run in temp dir to avoid .env file
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("CLOCKIFY_API_KEY", raising=False)
        args = type("Args", (), {"api_key": None, "output_dir": None, "full": False, "workspace": [], "from_date": None, "refetch": None})()
        cfg = Config.load(args)
        assert cfg.api_key == ""
        assert str(cfg.export_dir) == "export"
        assert cfg.refetch == 1  # default from DEFAULTS

    def test_cli_output_dir(self, monkeypatch, temp_config_dir):
        monkeypatch.setenv("CLOCKIFY_API_KEY", "test_key")
        args = type("Args", (), {"api_key": None, "output_dir": "/cli/output", "full": False, "workspace": [], "from_date": None, "refetch": None})()
        cfg = Config.load(args)
        assert str(cfg.export_dir) == "/cli/output"

    def test_cli_workspaces(self, monkeypatch, temp_config_dir):
        monkeypatch.setenv("CLOCKIFY_API_KEY", "test_key")
        args = type("Args", (), {"api_key": None, "output_dir": None, "full": False, "workspace": ["WS1", "WS2"], "from_date": None, "refetch": None})()
        cfg = Config.load(args)
        assert cfg.workspaces == ["WS1", "WS2"]

    def test_cli_full(self, monkeypatch, temp_config_dir):
        monkeypatch.setenv("CLOCKIFY_API_KEY", "test_key")
        args = type("Args", (), {"api_key": None, "output_dir": None, "full": True, "workspace": [], "from_date": None, "refetch": None})()
        cfg = Config.load(args)
        assert cfg.full is True

    def test_cli_from_date(self, monkeypatch, temp_config_dir):
        monkeypatch.setenv("CLOCKIFY_API_KEY", "test_key")
        args = type("Args", (), {"api_key": None, "output_dir": None, "full": False, "workspace": [], "from_date": "2026-01", "refetch": None})()
        cfg = Config.load(args)
        assert cfg.from_date == "2026-01"

    def test_cli_refetch(self, monkeypatch, temp_config_dir):
        monkeypatch.setenv("CLOCKIFY_API_KEY", "test_key")
        args = type("Args", (), {"api_key": None, "output_dir": None, "full": False, "workspace": [], "from_date": None, "refetch": 5})()
        cfg = Config.load(args)
        assert cfg.refetch == 5

    def test_dotenv_fallback(self, monkeypatch, tmp_path):
        import clockify_export.config as config_module
        env_file = tmp_path / ".env"
        env_file.write_text('CLOCKIFY_API_KEY="dotenv_key"\n')
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("CLOCKIFY_API_KEY", raising=False)
        args = type("Args", (), {"api_key": None, "output_dir": None, "full": False, "workspace": [], "from_date": None, "refetch": None})()
        cfg = Config.load(args)
        assert cfg.api_key == "dotenv_key"