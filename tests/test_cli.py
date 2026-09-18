"""Tests for clockify_export.cli module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from clockify_export.cli import main
from clockify_export import __version__


def run_main(args: list[str]):
    """Helper to run main with patched sys.argv."""
    with patch("sys.argv", ["clockify-export"] + args):
        main()


from contextlib import contextmanager


@contextmanager
def isolated_env(tmp_path):
    """Context manager for isolated test environment."""
    import os
    old_home = os.environ.get("HOME")
    old_api_key = os.environ.pop("CLOCKIFY_API_KEY", None)
    old_cwd = os.getcwd()
    config_dir = tmp_path / ".config" / "clockify-export"
    config_dir.mkdir(parents=True)
    os.environ["HOME"] = str(tmp_path)
    os.chdir(tmp_path)
    try:
        yield config_dir
    finally:
        if old_home:
            os.environ["HOME"] = old_home
        else:
            os.environ.pop("HOME", None)
        if old_api_key:
            os.environ["CLOCKIFY_API_KEY"] = old_api_key
        os.chdir(old_cwd)


class TestCLI:
    """Tests for CLI entry point."""

    def test_version_flag(self, capsys):
        with pytest.raises(SystemExit) as exc:
            run_main(["--version"])
        assert exc.value.code == 0
        captured = capsys.readouterr()
        assert __version__ in captured.out

    def test_init_config_creates_file(self, tmp_path):
        with isolated_env(tmp_path) as config_dir:
            with patch("clockify_export.config.CONFIG_DIR", config_dir):
                with patch("clockify_export.config.CONFIG_FILE", config_dir / "config.toml"):
                    run_main(["--init-config"])
                    config_file = config_dir / "config.toml"
                    assert config_file.exists()
                    content = config_file.read_text()
                    assert "api_key" in content
                    assert "export_dir" in content

    def test_missing_api_key_exits(self, capsys, tmp_path):
        with isolated_env(tmp_path) as config_dir:
            with patch("clockify_export.config.CONFIG_DIR", config_dir):
                with patch("clockify_export.config.CONFIG_FILE", config_dir / "config.toml"):
                    with patch("clockify_export.config.STATE_FILE", config_dir / "state.json"):
                        with pytest.raises(SystemExit) as exc:
                            run_main([])
                        assert exc.value.code == 1
                        captured = capsys.readouterr()
                        assert "Error: No API key found" in captured.err

    def test_mutually_exclusive_date_options(self, tmp_path):
        with isolated_env(tmp_path) as config_dir:
            (config_dir / "config.toml").write_text('api_key = "test_key"\n')
            with patch("clockify_export.config.CONFIG_DIR", config_dir):
                with patch("clockify_export.config.CONFIG_FILE", config_dir / "config.toml"):
                    with patch("clockify_export.config.STATE_FILE", config_dir / "state.json"):
                        with patch("clockify_export.cli.ClockifyAPI") as mock_api_class:
                            mock_api = MagicMock()
                            mock_api.get_workspaces.return_value = [{"id": "ws1", "name": "WS"}]
                            mock_api_class.return_value = mock_api

                            with pytest.raises(SystemExit):
                                run_main(["--from", "2026-01", "--last", "3"])

    def test_status_flag_shows_state(self, capsys, tmp_path, sample_state):
        with isolated_env(tmp_path) as config_dir:
            (config_dir / "config.toml").write_text('api_key = "test_key"\nexport_dir = "export"\n')
            (config_dir / "state.json").write_text('{"ws123": {"last_exported": "2026-01-15T17:00:00+00:00"}}')
            with patch("clockify_export.config.CONFIG_DIR", config_dir):
                with patch("clockify_export.config.CONFIG_FILE", config_dir / "config.toml"):
                    with patch("clockify_export.config.STATE_FILE", config_dir / "state.json"):
                        with patch("clockify_export.cli.ClockifyAPI") as mock_api_class:
                            mock_api = MagicMock()
                            mock_api.get_workspaces.return_value = [{"id": "ws1", "name": "WS"}]
                            mock_api_class.return_value = mock_api

                            run_main(["--status"])
                            captured = capsys.readouterr()
                            assert "Export directory:" in captured.out
                            assert "Export state:" in captured.out
                            assert "ws123" in captured.out

    def test_workspace_filtering(self, tmp_path):
        with isolated_env(tmp_path) as config_dir:
            (config_dir / "config.toml").write_text('api_key = "test_key"\n')
            with patch("clockify_export.config.CONFIG_DIR", config_dir):
                with patch("clockify_export.config.CONFIG_FILE", config_dir / "config.toml"):
                    with patch("clockify_export.config.STATE_FILE", config_dir / "state.json"):
                        with patch("clockify_export.cli.ClockifyAPI") as mock_api_class:
                            mock_api = MagicMock()
                            mock_api.get_workspaces.return_value = [
                                {"id": "ws1", "name": "Workspace One"},
                                {"id": "ws2", "name": "Workspace Two"},
                            ]
                            mock_api.get_current_user.return_value = {"id": "user1", "name": "User"}
                            mock_api.get_projects.return_value = []
                            mock_api.get_clients.return_value = []
                            mock_api.get_tags.return_value = []
                            mock_api.get_time_entries.return_value = []
                            mock_api_class.return_value = mock_api

                            run_main(["--workspace", "Workspace One"])
                            mock_api.get_workspaces.assert_called_once()

    def test_invalid_workspace_exits(self, capsys, tmp_path):
        with isolated_env(tmp_path) as config_dir:
            (config_dir / "config.toml").write_text('api_key = "test_key"\n')
            with patch("clockify_export.config.CONFIG_DIR", config_dir):
                with patch("clockify_export.config.CONFIG_FILE", config_dir / "config.toml"):
                    with patch("clockify_export.config.STATE_FILE", config_dir / "state.json"):
                        with patch("clockify_export.cli.ClockifyAPI") as mock_api_class:
                            mock_api = MagicMock()
                            mock_api.get_workspaces.return_value = [{"id": "ws1", "name": "WS"}]
                            mock_api_class.return_value = mock_api

                            with pytest.raises(SystemExit) as exc:
                                run_main(["--workspace", "NonExistent"])
                            assert exc.value.code == 1
                            captured = capsys.readouterr()
                            assert "Workspace(s) not found" in captured.err

    def test_no_cache_flag(self, tmp_path):
        with isolated_env(tmp_path) as config_dir:
            (config_dir / "config.toml").write_text('api_key = "test_key"\n')
            with patch("clockify_export.config.CONFIG_DIR", config_dir):
                with patch("clockify_export.config.CONFIG_FILE", config_dir / "config.toml"):
                    with patch("clockify_export.config.STATE_FILE", config_dir / "state.json"):
                        with patch("clockify_export.cli.ClockifyAPI") as mock_api_class:
                            mock_api = MagicMock()
                            mock_api.get_workspaces.return_value = [{"id": "ws1", "name": "WS"}]
                            mock_api.get_current_user.return_value = {"id": "user1", "name": "User"}
                            mock_api.get_projects.return_value = []
                            mock_api.get_clients.return_value = []
                            mock_api.get_tags.return_value = []
                            mock_api.get_time_entries.return_value = []
                            mock_api_class.return_value = mock_api

                            run_main(["--no-cache"])

    def test_full_flag(self, tmp_path):
        with isolated_env(tmp_path) as config_dir:
            (config_dir / "config.toml").write_text('api_key = "test_key"\n')
            with patch("clockify_export.config.CONFIG_DIR", config_dir):
                with patch("clockify_export.config.CONFIG_FILE", config_dir / "config.toml"):
                    with patch("clockify_export.config.STATE_FILE", config_dir / "state.json"):
                        with patch("clockify_export.cli.ClockifyAPI") as mock_api_class:
                            mock_api = MagicMock()
                            mock_api.get_workspaces.return_value = [{"id": "ws1", "name": "WS"}]
                            mock_api.get_current_user.return_value = {"id": "user1", "name": "User"}
                            mock_api.get_projects.return_value = []
                            mock_api.get_clients.return_value = []
                            mock_api.get_tags.return_value = []
                            mock_api.get_time_entries.return_value = []
                            mock_api_class.return_value = mock_api

                            run_main(["--full"])

    def test_from_date_option(self, tmp_path):
        with isolated_env(tmp_path) as config_dir:
            (config_dir / "config.toml").write_text('api_key = "test_key"\n')
            with patch("clockify_export.config.CONFIG_DIR", config_dir):
                with patch("clockify_export.config.CONFIG_FILE", config_dir / "config.toml"):
                    with patch("clockify_export.config.STATE_FILE", config_dir / "state.json"):
                        with patch("clockify_export.cli.ClockifyAPI") as mock_api_class:
                            mock_api = MagicMock()
                            mock_api.get_workspaces.return_value = [{"id": "ws1", "name": "WS"}]
                            mock_api.get_current_user.return_value = {"id": "user1", "name": "User"}
                            mock_api.get_projects.return_value = []
                            mock_api.get_clients.return_value = []
                            mock_api.get_tags.return_value = []
                            mock_api.get_time_entries.return_value = []
                            mock_api_class.return_value = mock_api

                            run_main(["--from", "2026-01"])

    def test_last_option(self, tmp_path):
        with isolated_env(tmp_path) as config_dir:
            (config_dir / "config.toml").write_text('api_key = "test_key"\n')
            with patch("clockify_export.config.CONFIG_DIR", config_dir):
                with patch("clockify_export.config.CONFIG_FILE", config_dir / "config.toml"):
                    with patch("clockify_export.config.STATE_FILE", config_dir / "state.json"):
                        with patch("clockify_export.cli.ClockifyAPI") as mock_api_class:
                            mock_api = MagicMock()
                            mock_api.get_workspaces.return_value = [{"id": "ws1", "name": "WS"}]
                            mock_api.get_current_user.return_value = {"id": "user1", "name": "User"}
                            mock_api.get_projects.return_value = []
                            mock_api.get_clients.return_value = []
                            mock_api.get_tags.return_value = []
                            mock_api.get_time_entries.return_value = []
                            mock_api_class.return_value = mock_api

                            run_main(["--last", "3"])

    def test_refetch_option(self, tmp_path):
        with isolated_env(tmp_path) as config_dir:
            (config_dir / "config.toml").write_text('api_key = "test_key"\nrefetch = 2\n')
            with patch("clockify_export.config.CONFIG_DIR", config_dir):
                with patch("clockify_export.config.CONFIG_FILE", config_dir / "config.toml"):
                    with patch("clockify_export.config.STATE_FILE", config_dir / "state.json"):
                        with patch("clockify_export.cli.ClockifyAPI") as mock_api_class:
                            mock_api = MagicMock()
                            mock_api.get_workspaces.return_value = [{"id": "ws1", "name": "WS"}]
                            mock_api.get_current_user.return_value = {"id": "user1", "name": "User"}
                            mock_api.get_projects.return_value = []
                            mock_api.get_clients.return_value = []
                            mock_api.get_tags.return_value = []
                            mock_api.get_time_entries.return_value = []
                            mock_api_class.return_value = mock_api

                            run_main(["--refetch", "3"])