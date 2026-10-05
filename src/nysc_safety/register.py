"""Build the analysis-ready incident register from the working register.

Run from the repository root with `python -m nysc_safety.register`.
Reads `data/interim/incidents_working.csv` and the screening files, adds
`n_articles` and writes `data/processed/incidents.csv`.

`n_articles` is the number of distinct articles in Premium Times, Daily Trust
and Channels Television, found by the logged archive search and linked to the
incident during headline screening, published from the event date to 30 days
after it (`docs/analysis_plan.md`, section 11). For an incident dated to the
month or year, the window starts on the event date and ends 30 days after the
end of that month or year.
"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from nysc_safety import coding, paths

COUNTED_OUTLETS: tuple[str, ...] = ("Premium Times", "Daily Trust", "Channels Television")
WINDOW_DAYS = 30
SPLIT_CANDIDATES: dict[str, tuple[str, ...]] = {"K03": ("K03", "K03b")}
"""Candidates whose reports cover more than one incident; their articles count for each."""

COLUMNS: tuple[str, ...] = (
    "incident_id", "event_date", "date_precision", "state", "zone", "lga", "lifecycle_stage",
    "harm_type", "member_status", "victims_total", "victims_killed", "victims_abducted",
    "outcome", "ransom_reported", "perpetrator_type", "n_articles", "source_ids", "coding_note",
)


def window_end(event_date: pd.Timestamp, precision: str) -> pd.Timestamp:
    """Last publication date counted for an incident."""
    if precision == "month":
        end = event_date + pd.offsets.MonthEnd(0)
    elif precision == "year":
        end = event_date + pd.offsets.YearEnd(0)
    else:
        end = event_date
    return end + timedelta(days=WINDOW_DAYS)


def article_links(screening: pd.DataFrame, decisions: pd.DataFrame) -> pd.DataFrame:
    """Return one row per (candidate_id, url, published) for counted outlets, after merges and splits."""
    linked = screening[
        screening["decision"].isin(["candidate", "existing_candidate"])
        & screening["outlet"].isin(COUNTED_OUTLETS)
    ][["candidate_id", "url", "published"]].copy()
    merged = decisions[decisions["decision"] == "merged"].set_index("candidate_id")["incident_candidate"]
    linked["candidate_id"] = linked["candidate_id"].replace(merged.to_dict())
    linked["candidate_id"] = linked["candidate_id"].map(lambda c: SPLIT_CANDIDATES.get(c, (c,)))
    linked = linked.explode("candidate_id")
    linked["published"] = pd.to_datetime(linked["published"])
    return linked.drop_duplicates(["candidate_id", "url"])


def count_articles(incidents: pd.DataFrame, links: pd.DataFrame) -> pd.Series:
    """Number of linked articles inside each incident's window, indexed like `incidents`."""
    counts = []
    for row in incidents.itertuples():
        start = pd.Timestamp(row.event_date)
        end = window_end(start, row.date_precision)
        own = links[links["candidate_id"] == row.candidate_id]
        counts.append(int(own["published"].between(start, end).sum()))
    return pd.Series(counts, index=incidents.index, name="n_articles")


def build(incidents: pd.DataFrame, screening: pd.DataFrame, decisions: pd.DataFrame) -> pd.DataFrame:
    """Add zone and `n_articles` and return the register in its published column order."""
    frame = incidents.copy()
    frame["zone"] = frame["state"].map(coding.zone_of)
    frame["n_articles"] = count_articles(frame, article_links(screening, decisions))
    return frame[list(COLUMNS)]


def main() -> None:
    """Build `data/processed/incidents.csv` and stop if any row fails validation."""
    screening_dir = paths.DATA_INTERIM / "screening"
    register = build(
        pd.read_csv(paths.DATA_INTERIM / "incidents_working.csv"),
        pd.read_csv(screening_dir / "headline_screening.csv", dtype=str).fillna(""),
        pd.read_csv(screening_dir / "screening_decisions.csv", dtype=str).fillna(""),
    )
    problems = coding.validate_register(register)
    if not problems.empty:
        raise SystemExit(problems.to_string(index=False))
    out = paths.DATA_PROCESSED / "incidents.csv"
    register.to_csv(out, index=False)
    print(f"{len(register)} incidents written to {out.relative_to(paths.ROOT)}")


if __name__ == "__main__":
    main()
