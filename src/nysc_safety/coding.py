"""Controlled vocabularies and validation for the incident register.

The categories match `docs/coding_protocol.md`. Any change to a category list
is made in both places and recorded in the protocol's change log.
"""

from __future__ import annotations

import re
from datetime import date

import pandas as pd

LIFECYCLE_STAGES: tuple[str, ...] = (
    "travel_to_camp",
    "camp",
    "travel_to_ppa",
    "ppa",
    "cds",
    "personal_travel",
    "passing_out",
    "unknown",
)
"""Stages of the service year, in chronological order, plus a residual code."""

HARM_TYPES: tuple[str, ...] = (
    "kidnapping",
    "killing",
    "sexual_violence",
    "physical_assault",
    "robbery",
    "road_crash",
    "other",
)
"""Primary harm suffered in the incident."""

MEMBER_STATUS: tuple[str, ...] = ("prospective", "serving", "mixed", "unknown")
"""Service status of the people harmed at the time of the incident."""

DATE_PRECISION: tuple[str, ...] = ("day", "month", "year")
"""Precision with which the incident date is known."""

OPTIONAL_CATEGORIES: dict[str, tuple[str, ...]] = {
    "outcome": (
        "released",
        "rescued",
        "killed_in_captivity",
        "escaped",
        "still_held",
        "unknown",
        "not_applicable",
    ),
    "ransom_reported": ("yes", "no", "unknown"),
    "perpetrator_type": (
        "armed_group",
        "bandits",
        "cult",
        "robbers",
        "community",
        "state_actor",
        "unknown",
    ),
}
"""Category lists for columns that are checked when present in a record."""

ZONES: dict[str, tuple[str, ...]] = {
    "North Central": ("Benue", "FCT", "Kogi", "Kwara", "Nasarawa", "Niger", "Plateau"),
    "North East": ("Adamawa", "Bauchi", "Borno", "Gombe", "Taraba", "Yobe"),
    "North West": ("Jigawa", "Kaduna", "Kano", "Katsina", "Kebbi", "Sokoto", "Zamfara"),
    "South East": ("Abia", "Anambra", "Ebonyi", "Enugu", "Imo"),
    "South South": ("Akwa Ibom", "Bayelsa", "Cross River", "Delta", "Edo", "Rivers"),
    "South West": ("Ekiti", "Lagos", "Ogun", "Ondo", "Osun", "Oyo"),
}
"""Six geopolitical zones and their 36 states plus the Federal Capital Territory."""

STATES: tuple[str, ...] = tuple(sorted(s for states in ZONES.values() for s in states))
"""The 36 states and the FCT, in alphabetical order."""

INCIDENT_ID_PATTERN = re.compile(r"^INC\d{4}$")

REQUIRED_COLUMNS: tuple[str, ...] = (
    "incident_id",
    "event_date",
    "date_precision",
    "state",
    "lga",
    "lifecycle_stage",
    "harm_type",
    "member_status",
    "victims_total",
    "victims_killed",
    "victims_abducted",
    "source_ids",
)


def zone_of(state: str) -> str:
    """Return the geopolitical zone of a state; raise KeyError if the state is unknown."""
    for zone, states in ZONES.items():
        if state in states:
            return zone
    raise KeyError(f"Unknown state: {state!r}")


def _check_category(value: object, allowed: tuple[str, ...], column: str) -> list[str]:
    """Return an error message list for a value outside an allowed category list."""
    if value not in allowed:
        return [f"{column}: {value!r} is not one of {allowed}"]
    return []


def validate_record(record: dict[str, object]) -> list[str]:
    """Return a list of problems in one incident record; an empty list means valid."""
    errors: list[str] = []
    missing = [c for c in REQUIRED_COLUMNS if c not in record]
    if missing:
        return [f"missing columns: {missing}"]

    if not INCIDENT_ID_PATTERN.match(str(record["incident_id"])):
        errors.append(f"incident_id: {record['incident_id']!r} does not match INC0000")

    try:
        event = date.fromisoformat(str(record["event_date"]))
        if not date(2010, 1, 1) <= event <= date(2026, 12, 31):
            errors.append(f"event_date: {event} is outside 2010 to 2026")
    except ValueError:
        errors.append(f"event_date: {record['event_date']!r} is not an ISO date")

    errors += _check_category(record["date_precision"], DATE_PRECISION, "date_precision")
    errors += _check_category(record["state"], STATES, "state")
    errors += _check_category(record["lifecycle_stage"], LIFECYCLE_STAGES, "lifecycle_stage")
    errors += _check_category(record["harm_type"], HARM_TYPES, "harm_type")
    errors += _check_category(record["member_status"], MEMBER_STATUS, "member_status")
    for column, allowed in OPTIONAL_CATEGORIES.items():
        if column in record:
            errors += _check_category(record[column], allowed, column)

    counts = {}
    for column in ("victims_total", "victims_killed", "victims_abducted"):
        value = record[column]
        if pd.isna(value):
            counts[column] = None
            continue
        try:
            number = int(value)
        except (TypeError, ValueError):
            errors.append(f"{column}: {value!r} is not a whole number")
            continue
        if number < 0 or number != value:
            errors.append(f"{column}: {value!r} is not a non-negative whole number")
            continue
        counts[column] = number

    total = counts.get("victims_total")
    for part in ("victims_killed", "victims_abducted"):
        part_value = counts.get(part)
        if total is not None and part_value is not None and part_value > total:
            errors.append(f"{part} ({part_value}) exceeds victims_total ({total})")

    if not re.fullmatch(r"S\d{2,3}(;S\d{2,3})*", str(record["source_ids"])):
        errors.append(f"source_ids: {record['source_ids']!r} is not a ;-separated list of S IDs")

    return errors


def validate_register(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate every row of an incident register.

    Returns a frame with columns `incident_id` and `error`, one row per problem.
    Duplicate incident IDs are reported as problems.
    """
    rows: list[dict[str, str]] = []
    for record in frame.to_dict(orient="records"):
        for error in validate_record(record):
            rows.append({"incident_id": str(record.get("incident_id")), "error": error})
    if "incident_id" in frame.columns:
        for dup in frame.loc[frame["incident_id"].duplicated(), "incident_id"]:
            rows.append({"incident_id": str(dup), "error": "duplicate incident_id"})
    return pd.DataFrame(rows, columns=["incident_id", "error"])
