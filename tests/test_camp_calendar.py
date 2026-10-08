"""Tests for nysc_safety.camp_calendar."""

from datetime import date

import pandas as pd
import pytest

from nysc_safety import camp_calendar, paths


def _row(year, batch, stream, event, day, status="use"):
    return {"batch_year": year, "batch": batch, "stream": stream, "event": event, "date": day, "status": status}


DATES = pd.DataFrame(
    [
        _row("2020", "A", "I", "camp_opening", "2020-03-01"),
        _row("2020", "A", "I", "camp_closing", "2020-03-21"),
        _row("2020", "A", "I", "passing_out", "2021-02-01"),
        _row("2020", "A", "II", "camp_opening", "2020-05-01"),
        _row("2020", "A", None, "passing_out", "2021-04-01"),
        _row("2020", "B", "I", "camp_closing", "2020-08-21"),
        _row("2020", "B", "I", "camp_opening", "2020-07-01", status="drop"),
    ]
)


def test_closing_and_opening_derived_from_course_length() -> None:
    """A missing closing is opening + 20 days; a missing opening is closing - 20 days."""
    cal = camp_calendar.complete(camp_calendar.stream_table(DATES)).set_index(["batch", "stream"])
    assert cal.loc[("A", "II"), "camp_closing"] == date(2020, 5, 21)
    assert cal.loc[("A", "II"), "camp_closing_basis"] == "derived"
    assert cal.loc[("B", "I"), "camp_opening"] == date(2020, 8, 1)


def test_batch_level_passing_out_fills_streams() -> None:
    """A passing-out date without a stream fills streams that lack one, and the batch-only row is removed."""
    cal = camp_calendar.complete(camp_calendar.stream_table(DATES)).set_index(["batch", "stream"])
    assert cal.loc[("A", "II"), "passing_out"] == date(2021, 4, 1)
    assert cal.loc[("A", "II"), "passing_out_basis"] == "batch_report"
    assert cal.loc[("A", "I"), "passing_out"] == date(2021, 2, 1)
    assert ("A", "") not in cal.index


def test_passing_out_derived_from_median_lag() -> None:
    """A passing-out date still missing is closing plus the median reported lag."""
    cal = camp_calendar.complete(camp_calendar.stream_table(DATES))
    lag = (date(2021, 2, 1) - date(2020, 3, 21)).days
    assert cal.attrs["passing_out_lag_days"] == lag
    row = cal[(cal["batch"] == "B") & (cal["stream"] == "I")].iloc[0]
    assert (row["passing_out"] - date(2020, 8, 21)).days == lag
    assert row["passing_out_basis"] == "derived"


def test_duplicate_use_rows_rejected() -> None:
    """Two `use` dates for the same batch, stream and event raise an error."""
    dup = pd.concat([DATES, pd.DataFrame([_row("2020", "A", "I", "camp_opening", "2020-03-02")])])
    with pytest.raises(ValueError):
        camp_calendar.stream_table(dup)


def test_anchors_filter_by_basis_and_end_date() -> None:
    """Anchors are opening and passing-out dates, filtered by basis and end date."""
    cal = camp_calendar.complete(camp_calendar.stream_table(DATES))
    all_anchors = camp_calendar.anchors(cal, until=date(2020, 12, 31))
    assert all_anchors == [date(2020, 3, 1), date(2020, 5, 1), date(2020, 8, 1)]
    reported = camp_calendar.anchors(cal, bases=("reported",))
    assert date(2020, 8, 1) not in reported and date(2021, 2, 1) in reported


def test_committed_dates_have_one_use_row_per_event() -> None:
    """The committed date file has at most one `use` row per batch, stream and event."""
    dates = pd.read_csv(paths.DATA_INTERIM / "calendar" / "nysc_dates.csv", dtype=str)
    assert set(dates["status"]) <= {"use", "use_extra", "alt", "drop"}
    camp_calendar.stream_table(dates)
