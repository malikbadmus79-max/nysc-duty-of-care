"""Tests for nysc_safety.travel_window."""

from datetime import date, timedelta

import pytest

from nysc_safety import travel_window


def test_window_days_size() -> None:
    """One anchor with half-width 7 covers 15 days."""
    assert len(travel_window.window_days([date(2024, 3, 1)], 7)) == 15


def test_overlapping_windows_not_double_counted() -> None:
    """Overlapping windows count each day once."""
    days = travel_window.window_days([date(2024, 3, 1), date(2024, 3, 3)], 7)
    assert len(days) == 17


def test_expected_share_and_clustering() -> None:
    """All events inside a window that covers 15 of 366 days give a very small p-value."""
    anchor = date(2024, 6, 15)
    events = [anchor + timedelta(days=k) for k in range(-3, 4)] * 2
    result = travel_window.travel_window_test(events, [anchor], date(2024, 1, 1), date(2024, 12, 31))
    assert result["expected_share"] == pytest.approx(15 / 366)
    assert result["in_window"] == 14
    assert result["p_value"] < 1e-10


def test_events_outside_period_ignored() -> None:
    """Events before the start date are not counted."""
    result = travel_window.travel_window_test(
        [date(2023, 12, 31), date(2024, 2, 1)], [date(2024, 6, 1)], date(2024, 1, 1), date(2024, 12, 31)
    )
    assert result["n_events"] == 1
    assert result["in_window"] == 0
