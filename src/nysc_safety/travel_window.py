"""Test of whether incidents cluster around official travel dates (H2)."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta

import pandas as pd
from scipy import stats

H2_STAGES: tuple[str, ...] = ("travel_to_camp", "camp", "travel_to_ppa", "passing_out")
"""Lifecycle stages in the main H2 sample (`docs/preregistration.md`, section 2)."""


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
    if n:
        test = stats.binomtest(hits, n, expected_share, alternative="greater")
        p_value = float(test.pvalue)
        ci = stats.binomtest(hits, n, expected_share).proportion_ci(confidence_level=0.95, method="exact")
        ci_lower, ci_upper = float(ci.low), float(ci.high)
    else:
        p_value = ci_lower = ci_upper = float("nan")
    return {
        "n_events": float(n),
        "in_window": float(hits),
        "observed_share": hits / n if n else float("nan"),
        "share_ci_lower": ci_lower,
        "share_ci_upper": ci_upper,
        "expected_share": expected_share,
        "p_value": p_value,
    }


def h2_sample(
    incidents: pd.DataFrame,
    stages: tuple[str, ...] = H2_STAGES,
    exclude: frozenset[str] = frozenset(),
) -> pd.DataFrame:
    """Incidents with day-precision dates in the given stages, without the excluded incident IDs [A01, A04]."""
    keep = (
        (incidents["date_precision"] == "day")
        & incidents["lifecycle_stage"].isin(stages)
        & ~incidents["incident_id"].isin(exclude)
    )
    sample = incidents[keep].copy()
    sample["event_day"] = pd.to_datetime(sample["event_date"]).dt.date
    return sample


def ids_citing(incidents: pd.DataFrame, assumption: str) -> frozenset[str]:
    """IDs of incidents whose coding note cites an assumption, such as `A05`."""
    cited = incidents["coding_note"].fillna("").str.contains(rf"\b{assumption}\b")
    return frozenset(incidents.loc[cited, "incident_id"])
