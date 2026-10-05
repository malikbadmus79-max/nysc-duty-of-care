"""Tests for nysc_safety.coding."""

import pandas as pd
import pytest

from nysc_safety import coding


def valid_record(**changes: object) -> dict[str, object]:
    """A valid incident record, with optional field changes."""
    record: dict[str, object] = {
        "incident_id": "INC0001",
        "event_date": "2019-08-20",
        "date_precision": "day",
        "state": "Kaduna",
        "lga": "Chikun",
        "lifecycle_stage": "travel_to_camp",
        "harm_type": "kidnapping",
        "member_status": "prospective",
        "victims_total": 3,
        "victims_killed": 0,
        "victims_abducted": 3,
        "source_ids": "S10;S11",
    }
    record.update(changes)
    return record


def test_states_count() -> None:
    """There are 36 states plus the FCT, each in exactly one zone."""
    assert len(coding.STATES) == 37
    assert len(set(coding.STATES)) == 37


def test_zone_of() -> None:
    """States map to their geopolitical zone."""
    assert coding.zone_of("Zamfara") == "North West"
    assert coding.zone_of("FCT") == "North Central"
    with pytest.raises(KeyError):
        coding.zone_of("Lagoss")


def test_valid_record_has_no_errors() -> None:
    """A correctly coded record passes validation."""
    assert coding.validate_record(valid_record()) == []


def test_unknown_victim_counts_are_allowed() -> None:
    """Missing victim counts are recorded as unknown, not as errors."""
    assert coding.validate_record(valid_record(victims_killed=float("nan"))) == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("incident_id", "INC1"),
        ("event_date", "2009-12-31"),
        ("event_date", "20/08/2019"),
        ("date_precision", "week"),
        ("state", "Lagoss"),
        ("lifecycle_stage", "orientation"),
        ("harm_type", "abduction"),
        ("member_status", "former"),
        ("victims_total", -1),
        ("victims_total", 2.5),
        ("source_ids", "S10, S11"),
    ],
)
def test_invalid_field_is_reported(field: str, value: object) -> None:
    """Each invalid field produces at least one error naming the field."""
    errors = coding.validate_record(valid_record(**{field: value}))
    assert any(field in e for e in errors)


def test_part_cannot_exceed_total() -> None:
    """Abducted or killed counts larger than the total are errors."""
    errors = coding.validate_record(valid_record(victims_total=2, victims_abducted=3))
    assert any("exceeds victims_total" in e for e in errors)


def test_missing_columns_reported() -> None:
    """A record without required columns is rejected."""
    record = valid_record()
    del record["state"]
    assert coding.validate_record(record) == ["missing columns: ['state']"]


def test_validate_register_finds_duplicates() -> None:
    """Duplicate incident IDs are reported once per duplicate."""
    frame = pd.DataFrame([valid_record(), valid_record()])
    problems = coding.validate_register(frame)
    assert list(problems["error"]) == ["duplicate incident_id"]


def test_optional_categories_checked_when_present() -> None:
    """Optional columns are validated only when the record contains them."""
    assert coding.validate_record(valid_record(outcome="released", ransom_reported="yes")) == []
    errors = coding.validate_record(valid_record(perpetrator_type="gunmen"))
    assert any("perpetrator_type" in e for e in errors)
