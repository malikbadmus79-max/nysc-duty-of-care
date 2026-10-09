"""Data preparation for the Streamlit dashboard in `app/`.

The dashboard reads only committed files: the processed data in
`data/processed/`, the result tables written by the notebooks to
`reports/tables/`, and the state boundaries in `data/raw/geo/` [S566].
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date
from pathlib import Path

import pandas as pd

from nysc_safety import coding, paths, risk, scorecard

GEO_PATH: Path = paths.DATA_RAW / "geo" / "geoBoundaries-NGA-ADM1_simplified.geojson"
GEO_NAMES: dict[str, str] = {"Abuja Federal Capital Territory": "FCT"}
"""Boundary names that differ from the state names in `coding.STATES`."""
TABLES: Path = paths.ROOT / "reports" / "tables"
CUTOFF = date(2026, 10, 5)
"""Data cutoff of the incident register [A15]."""


def signed_area(ring: list[list[float]]) -> float:
    """Shoelace area of a ring in degrees; positive when the ring runs counterclockwise."""
    return sum(x0 * y1 - x1 * y0 for (x0, y0, *_), (x1, y1, *_) in zip(ring, ring[1:] + ring[:1])) / 2


def rewind(polygon: list[list[list[float]]]) -> list[list[list[float]]]:
    """Polygon with the outer ring clockwise and holes counterclockwise, the order the map renderer expects."""
    rings = []
    for number, ring in enumerate(polygon):
        clockwise = signed_area(ring) < 0
        rings.append(ring if clockwise == (number == 0) else ring[::-1])
    return rings


def load_states_geojson(path: Path = GEO_PATH) -> dict:
    """State boundaries with a `state` property that matches `coding.STATES`, rings wound for plotting."""
    geo = json.loads(path.read_text(encoding="utf-8"))
    for feature in geo["features"]:
        geometry = feature["geometry"]
        if geometry["type"] == "Polygon":
            geometry["coordinates"] = rewind(geometry["coordinates"])
        elif geometry["type"] == "MultiPolygon":
            geometry["coordinates"] = [rewind(polygon) for polygon in geometry["coordinates"]]
        name = feature["properties"]["shapeName"]
        feature["properties"]["state"] = GEO_NAMES.get(name, name)
    missing = set(coding.STATES) - {f["properties"]["state"] for f in geo["features"]}
    if missing:
        raise ValueError(f"States without a boundary: {sorted(missing)}")
    return geo


def filter_incidents(
    incidents: pd.DataFrame,
    harm_types: Iterable[str] | None = None,
    stages: Iterable[str] | None = None,
    years: tuple[int, int] | None = None,
) -> pd.DataFrame:
    """Incidents of the chosen harm types and lifecycle stages with event dates in the year range."""
    keep = pd.Series(True, index=incidents.index)
    if harm_types is not None:
        keep &= incidents["harm_type"].isin(list(harm_types))
    if stages is not None:
        keep &= incidents["lifecycle_stage"].isin(list(stages))
    if years is not None:
        year = pd.to_datetime(incidents["event_date"]).dt.year
        keep &= year.between(*years)
    return incidents[keep]


def state_table(incidents: pd.DataFrame, exposure: pd.DataFrame, years: tuple[int, int] = (2010, CUTOFF.year)) -> pd.DataFrame:
    """Incidents, exposure and rate per 10,000 exposed for every state over the year range.

    The range ends at the data cutoff when it includes the cutoff year [A15].
    """
    end = CUTOFF if years[1] >= CUTOFF.year else date(years[1], 12, 31)
    panel = risk.state_year_panel(incidents, exposure, end, start_year=years[0])
    table = risk.state_rates(panel)
    return table.set_index("state").reindex(list(coding.STATES)).reset_index()


def nearest_anchor_days(events: Iterable[date], anchors: Iterable[date]) -> list[int]:
    """Signed days from each event to the nearest anchor date (negative: before the anchor)."""
    ordered = sorted(set(anchors))
    if not ordered:
        raise ValueError("No anchor dates")
    result = []
    for event in events:
        offsets = [(event - anchor).days for anchor in ordered]
        result.append(min(offsets, key=lambda d: (abs(d), d)))
    return result


def scorecard_table(scores: pd.DataFrame) -> pd.DataFrame:
    """Score per criterion for the current framework and the June 2026 reform, with the change."""
    scorecard.validate_scores(scores)
    table = scores.pivot(index="criterion_id", columns="framework", values="score")
    table = table.reindex(list(scorecard.CRITERIA))
    table.insert(0, "criterion", [scorecard.CRITERIA[c] for c in table.index])
    table["change"] = table["reform_2026"] - table["current"]
    table.columns.name = None
    return table.reset_index()


def read_table(name: str) -> pd.DataFrame | None:
    """A result table from `reports/tables/`, or None if the notebook that writes it has not been run."""
    path = TABLES / f"{name}.csv"
    return pd.read_csv(path) if path.exists() else None
