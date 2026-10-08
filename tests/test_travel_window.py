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


def _register():
    import pandas as pd

    return pd.DataFrame(
        {
            "incident_id": ["INC0001", "INC0002", "INC0003", "INC0004", "INC0005"],
            "event_date": ["2020-03-01", "2020-03-02", "2020-04-01", "2020-05-01", "2020-06-01"],
            "date_precision": ["day", "day", "month", "day", "day"],
            "lifecycle_stage": ["travel_to_camp", "personal_travel", "camp", "travel_to_ppa", "ppa"],
            "coding_note": ["", "", "", "Leaving camp [A05].", "Weekday only [A07]."],
        }
    )


def test_h2_sample_keeps_day_precision_in_stages() -> None:
    """The main sample keeps day-precision incidents in the four H2 stages."""
    from nysc_safety.travel_window import h2_sample

    sample = h2_sample(_register())
    assert list(sample["incident_id"]) == ["INC0001", "INC0004"]
    assert str(sample["event_day"].iloc[0]) == "2020-03-01"


def test_h2_sample_variants() -> None:
    """Adding personal_travel and excluding cited incidents change the sample as expected."""
    from nysc_safety.travel_window import H2_STAGES, h2_sample, ids_citing

    register = _register()
    wider = h2_sample(register, H2_STAGES + ("personal_travel",))
    assert list(wider["incident_id"]) == ["INC0001", "INC0002", "INC0004"]
    assert ids_citing(register, "A05") == frozenset({"INC0004"})
    assert list(h2_sample(register, exclude=ids_citing(register, "A05"))["incident_id"]) == ["INC0001"]


def test_travel_window_test_reports_exact_interval() -> None:
    """The observed share carries an exact 95% interval."""
    from datetime import date

    from nysc_safety.travel_window import travel_window_test

    result = travel_window_test([date(2020, 1, 5), date(2020, 6, 1)], [date(2020, 1, 1)], date(2020, 1, 1), date(2020, 12, 31))
    assert result["in_window"] == 1 and result["share_ci_lower"] < 0.5 < result["share_ci_upper"]
