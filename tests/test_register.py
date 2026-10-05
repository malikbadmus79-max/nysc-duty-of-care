"""Tests for nysc_safety.register."""

import pandas as pd

from nysc_safety import coding, paths, register


def _incident(candidate: str, date: str, precision: str = "day") -> dict:
    return {
        "incident_id": "INC0001", "candidate_id": candidate, "event_date": date, "date_precision": precision,
        "state": "Kogi", "lga": "Ofu", "lifecycle_stage": "travel_to_ppa", "harm_type": "kidnapping",
        "member_status": "serving", "victims_total": 2, "victims_killed": 0, "victims_abducted": 2,
        "outcome": "rescued", "ransom_reported": "no", "perpetrator_type": "unknown",
        "source_ids": "S01", "coding_note": "Test row.",
    }


def _headline(candidate: str, published: str, url: str, outlet: str = "Daily Trust", decision: str = "candidate") -> dict:
    return {"published": published, "outlet": outlet, "headline": "h", "url": url, "decision": decision, "candidate_id": candidate, "reason": ""}


DECISIONS = pd.DataFrame(
    [{"candidate_id": "H02", "decision": "merged", "incident_candidate": "H01", "reason": ""}]
)


def test_window_counts_only_articles_within_30_days() -> None:
    """Articles before the event or more than 30 days after it are not counted."""
    incidents = pd.DataFrame([_incident("H01", "2020-01-10")])
    screening = pd.DataFrame([
        _headline("H01", "2020-01-09", "u0"),
        _headline("H01", "2020-01-10", "u1"),
        _headline("H01", "2020-02-09", "u2"),
        _headline("H01", "2020-02-10", "u3"),
    ])
    out = register.build(incidents, screening, DECISIONS.iloc[0:0])
    assert out.loc[0, "n_articles"] == 2


def test_merged_candidates_and_outlet_filter() -> None:
    """Articles of a merged candidate count for its target; uncounted outlets and duplicates are ignored."""
    incidents = pd.DataFrame([_incident("H01", "2020-01-10")])
    screening = pd.DataFrame([
        _headline("H01", "2020-01-11", "u1"),
        _headline("H02", "2020-01-12", "u2"),
        _headline("H02", "2020-01-12", "u2"),
        _headline("H01", "2020-01-12", "u3", outlet="The Guardian (Nigeria)"),
        _headline("", "2020-01-12", "u4", decision="excluded"),
    ])
    out = register.build(incidents, screening, DECISIONS)
    assert out.loc[0, "n_articles"] == 2


def test_month_precision_window_runs_from_month_end() -> None:
    """An incident dated to the month counts articles until 30 days after the month ends."""
    incidents = pd.DataFrame([_incident("H01", "2020-01-01", "month")])
    screening = pd.DataFrame([_headline("H01", "2020-02-25", "u1"), _headline("H01", "2020-03-05", "u2")])
    out = register.build(incidents, screening, DECISIONS.iloc[0:0])
    assert out.loc[0, "n_articles"] == 1


def test_split_candidate_counts_for_each_incident() -> None:
    """A report covering two incidents counts for both."""
    rows = [_incident("K03", "2016-12-10"), _incident("K03b", "2016-12-10")]
    rows[1]["incident_id"] = "INC0002"
    screening = pd.DataFrame([_headline("K03", "2016-12-11", "u1", decision="existing_candidate")])
    out = register.build(pd.DataFrame(rows), screening, DECISIONS.iloc[0:0])
    assert list(out["n_articles"]) == [1, 1]
    assert list(out["zone"]) == ["North Central", "North Central"]


def test_working_register_is_valid() -> None:
    """The committed working register passes validation."""
    frame = pd.read_csv(paths.DATA_INTERIM / "incidents_working.csv")
    assert coding.validate_register(frame).empty
