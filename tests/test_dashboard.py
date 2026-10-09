"""Tests for nysc_safety.dashboard."""

from datetime import date

import pandas as pd
import pytest

from nysc_safety import coding, dashboard, scorecard


def test_geojson_covers_every_state() -> None:
    """The committed boundaries carry all 37 state names used in the register."""
    geo = dashboard.load_states_geojson()
    names = {f["properties"]["state"] for f in geo["features"]}
    assert names == set(coding.STATES)


def test_filter_incidents() -> None:
    """Filters on harm type, stage and year combine."""
    incidents = pd.DataFrame(
        {
            "event_date": ["2015-03-01", "2020-06-01", "2020-07-01"],
            "harm_type": ["kidnapping", "kidnapping", "killing"],
            "lifecycle_stage": ["camp", "ppa", "ppa"],
        }
    )
    assert len(dashboard.filter_incidents(incidents, harm_types=["kidnapping"])) == 2
    assert len(dashboard.filter_incidents(incidents, harm_types=["kidnapping"], years=(2016, 2026))) == 1
    assert len(dashboard.filter_incidents(incidents, stages=["camp"])) == 1
    assert len(dashboard.filter_incidents(incidents)) == 3


def test_state_table_has_every_state() -> None:
    """Every state appears, including states with no incident."""
    states = list(coding.STATES)
    exposure = pd.DataFrame({"state": states * 2, "year": [2019] * 37 + [2020] * 37, "exposure": [5_000.0] * 74})
    incidents = pd.DataFrame({"event_date": ["2020-05-01"], "state": ["Kaduna"]})
    table = dashboard.state_table(incidents, exposure, years=(2019, 2020)).set_index("state")
    assert len(table) == 37
    assert table.loc["Kaduna", "incidents"] == 1
    assert table.loc["Kaduna", "rate"] == pytest.approx(10_000 / 10_000)
    assert table.loc["Lagos", "incidents"] == 0


def test_nearest_anchor_days() -> None:
    """Offsets are signed and measured to the closest anchor; ties go to the earlier offset."""
    anchors = [date(2020, 1, 10), date(2020, 1, 20)]
    events = [date(2020, 1, 8), date(2020, 1, 15), date(2020, 1, 22)]
    assert dashboard.nearest_anchor_days(events, anchors) == [-2, -5, 2]
    with pytest.raises(ValueError):
        dashboard.nearest_anchor_days(events, [])


def test_scorecard_table() -> None:
    """One row per criterion in the order of the scorecard, with the change under the reform."""
    rows = [
        {"framework": f, "criterion_id": c, "score": 1 + (f == "reform_2026" and c == "D2"), "source_ids": "S03"}
        for f in ("current", "reform_2026")
        for c in scorecard.CRITERIA
    ]
    table = dashboard.scorecard_table(pd.DataFrame(rows)).set_index("criterion_id")
    assert list(table.index) == list(scorecard.CRITERIA)
    assert table.loc["D2", "change"] == 1 and table.loc["D1", "change"] == 0


def test_rewind_outer_clockwise_holes_counterclockwise() -> None:
    """The outer ring is reversed to clockwise and a hole to counterclockwise."""
    outer = [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]
    hole = [[0.2, 0.2], [0.2, 0.8], [0.8, 0.8], [0.8, 0.2], [0.2, 0.2]]
    assert dashboard.signed_area(outer) > 0 and dashboard.signed_area(hole) < 0
    result = dashboard.rewind([outer, hole])
    assert dashboard.signed_area(result[0]) < 0 and dashboard.signed_area(result[1]) > 0
