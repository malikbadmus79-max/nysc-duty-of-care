"""Calendar of orientation-course and passing-out dates, 2010 to 2026.

Run from the repository root with `python -m nysc_safety.camp_calendar`.

Reads `data/interim/calendar/nysc_dates.csv`, where every reported date has a
`status`: `use` (the date chosen for that batch, stream and event), `use_extra`
(an additional travel date for the same stream, such as a camp that opened and
was suspended), `alt` (a corroborating or competing report) or `drop`
(superseded, never held or implausible, with the reason). Writes
`data/processed/nysc_calendar.csv` with one row per batch and stream, filling
missing dates by the rules in [A11]:

- camp closing = camp opening + 20 days, and the reverse (21-day course);
- a passing-out date reported for a batch without a stream applies to each
  stream of that batch that has no passing-out date of its own;
- a passing-out date still missing = camp closing + the median interval
  between camp closing and passing-out among streams where both are reported.

Each date has a `*_basis` column: `reported`, `batch_report` or `derived`.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from nysc_safety import paths

COURSE_OFFSET = timedelta(days=20)
"""Days from the first to the last day of the 21-day orientation course."""

KEYS: list[str] = ["batch_year", "batch", "stream"]
EVENTS: tuple[str, ...] = ("camp_opening", "camp_closing", "passing_out")


def stream_table(dates: pd.DataFrame) -> pd.DataFrame:
    """One row per batch and stream with the chosen (`use`) date of each event."""
    chosen = dates[dates["status"] == "use"].copy()
    chosen["stream"] = chosen["stream"].fillna("")
    if chosen.duplicated(KEYS + ["event"]).any():
        raise ValueError("more than one date marked `use` for a batch, stream and event")
    chosen["date"] = pd.to_datetime(chosen["date"]).dt.date
    wide = chosen.pivot(index=KEYS, columns="event", values="date").reindex(columns=list(EVENTS))
    return wide.reset_index()


def complete(table: pd.DataFrame) -> pd.DataFrame:
    """Fill missing dates by the rules in the module docstring and record the basis of each date."""
    frame = table.copy()
    for event in EVENTS:
        frame[f"{event}_basis"] = frame[event].map(lambda v: "reported" if isinstance(v, date) else None)

    batch_level = frame[(frame["stream"] == "") & frame["passing_out"].map(lambda v: isinstance(v, date))]
    streamed = set(map(tuple, frame.loc[frame["stream"] != "", ["batch_year", "batch"]].values))
    for row in batch_level.itertuples():
        if (row.batch_year, row.batch) not in streamed:
            continue
        target = (frame["batch_year"] == row.batch_year) & (frame["batch"] == row.batch) & (frame["stream"] != "")
        missing = target & frame["passing_out"].isna()
        frame.loc[missing, "passing_out"] = row.passing_out
        frame.loc[missing, "passing_out_basis"] = "batch_report"
    frame = frame[~((frame["stream"] == "") & frame[["batch_year", "batch"]].apply(tuple, axis=1).isin(streamed))]

    open_only = frame["camp_closing"].isna() & frame["camp_opening"].notna()
    frame.loc[open_only, "camp_closing"] = frame.loc[open_only, "camp_opening"].map(lambda d: d + COURSE_OFFSET)
    frame.loc[open_only, "camp_closing_basis"] = "derived"
    close_only = frame["camp_opening"].isna() & frame["camp_closing"].notna()
    frame.loc[close_only, "camp_opening"] = frame.loc[close_only, "camp_closing"].map(lambda d: d - COURSE_OFFSET)
    frame.loc[close_only, "camp_opening_basis"] = "derived"

    both = frame[(frame["passing_out_basis"] == "reported") & frame["camp_closing"].notna()]
    gaps = [(p - c).days for p, c in zip(both["passing_out"], both["camp_closing"])]
    lag = timedelta(days=int(pd.Series(gaps).median())) if gaps else None
    no_pop = frame["passing_out"].isna() & frame["camp_closing"].notna()
    if lag is not None:
        frame.loc[no_pop, "passing_out"] = frame.loc[no_pop, "camp_closing"].map(lambda d: d + lag)
        frame.loc[no_pop, "passing_out_basis"] = "derived"
    frame.attrs["passing_out_lag_days"] = lag.days if lag is not None else None
    return frame.sort_values("camp_opening", na_position="first").reset_index(drop=True)


def anchors(calendar: pd.DataFrame, extras: pd.DataFrame | None = None, until: date | None = None,
            bases: tuple[str, ...] = ("reported", "batch_report", "derived")) -> list[date]:
    """Sorted unique camp-opening and passing-out dates (H2 anchors), optionally limited by basis and end date."""
    days: set[date] = set()
    for event in ("camp_opening", "passing_out"):
        keep = calendar[calendar[f"{event}_basis"].isin(bases)]
        days.update(keep[event].dropna())
    if extras is not None:
        days.update(pd.to_datetime(extras["date"]).dt.date)
    return sorted(d for d in days if until is None or d <= until)


def main() -> None:
    """Build `data/processed/nysc_calendar.csv`."""
    dates = pd.read_csv(paths.DATA_INTERIM / "calendar" / "nysc_dates.csv", dtype=str)
    calendar = complete(stream_table(dates))
    out = paths.DATA_PROCESSED / "nysc_calendar.csv"
    calendar.to_csv(out, index=False)
    counts = {e: calendar[f"{e}_basis"].value_counts().to_dict() for e in EVENTS}
    print(f"{len(calendar)} batch-streams written to {out.relative_to(paths.ROOT)}")
    print(f"Median camp closing to passing-out: {calendar.attrs['passing_out_lag_days']} days")
    for event, c in counts.items():
        print(f"{event}: {c}")


if __name__ == "__main__":
    main()
