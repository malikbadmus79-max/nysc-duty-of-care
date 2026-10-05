"""Test of whether incidents cluster around official travel dates (H2)."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta

from scipy import stats


def window_days(anchors: Iterable[date], half_width: int = 7) -> set[date]:
    """All calendar days within `half_width` days either side of any anchor date."""
    days: set[date] = set()
    for anchor in anchors:
        for offset in range(-half_width, half_width + 1):
            days.add(anchor + timedelta(days=offset))
    return days


def travel_window_test(
    events: Iterable[date],
    anchors: Iterable[date],
    start: date,
    end: date,
    half_width: int = 7,
) -> dict[str, float]:
    """One-sided binomial test of excess incidents inside travel windows.

    The expected share is the share of calendar days from `start` to `end`
    (both included) that fall inside a window. Events outside the period are
    ignored.
    """
    if end < start:
        raise ValueError("end is before start")
    period_days = (end - start).days + 1
    in_window = {d for d in window_days(anchors, half_width) if start <= d <= end}
    expected_share = len(in_window) / period_days

    kept = [e for e in events if start <= e <= end]
    hits = sum(1 for e in kept if e in in_window)
    n = len(kept)
    p_value = (
        float(stats.binomtest(hits, n, expected_share, alternative="greater").pvalue) if n else float("nan")
    )
    return {
        "n_events": float(n),
        "in_window": float(hits),
        "observed_share": hits / n if n else float("nan"),
        "expected_share": expected_share,
        "p_value": p_value,
    }
