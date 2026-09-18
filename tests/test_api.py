"""Tests for clockify_export.api module."""

from __future__ import annotations

import pytest

from clockify_export.api import ClockifyError, parse_iso_duration_to_hours


class TestParseISODurationToHours:
    """Tests for parse_iso_duration_to_hours function."""

    def test_hours_and_minutes(self):
        assert parse_iso_duration_to_hours("PT1H30M") == 1.5

    def test_minutes_only(self):
        assert parse_iso_duration_to_hours("PT30M") == 0.5

    def test_hours_only(self):
        assert parse_iso_duration_to_hours("PT2H") == 2.0

    def test_days(self):
        assert parse_iso_duration_to_hours("P1D") == 24.0

    def test_days_and_hours(self):
        assert parse_iso_duration_to_hours("P1DT2H") == 26.0

    def test_seconds(self):
        # 90 seconds = 1.5 minutes = 0.025 hours, rounded to 2 decimals = 0.03
        assert parse_iso_duration_to_hours("PT90S") == 0.03

    def test_zero(self):
        assert parse_iso_duration_to_hours("PT0S") == 0.0

    def test_empty_string(self):
        assert parse_iso_duration_to_hours("") == 0.0

    def test_invalid_format(self):
        assert parse_iso_duration_to_hours("INVALID") == 0.0

    def test_complex_duration(self):
        assert parse_iso_duration_to_hours("P2DT3H4M5S") == pytest.approx(51.07, rel=0.01)


class TestClockifyError:
    """Tests for ClockifyError exception."""

    def test_error_attributes(self):
        err = ClockifyError(404, "Not Found")
        assert err.status == 404
        assert str(err) == "HTTP 404: Not Found"

    def test_error_inheritance(self):
        err = ClockifyError(500, "Server Error")
        assert isinstance(err, Exception)