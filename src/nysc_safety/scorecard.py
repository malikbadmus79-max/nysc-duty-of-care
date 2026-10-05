"""Duty-of-care scorecard: criteria, score scale and aggregation.

Criteria follow the duty-of-care obligations and security risk management
elements set out by the Global Interagency Security Forum [S01, S02], as
adapted in `docs/policy_audit.md`.
"""

from __future__ import annotations

import pandas as pd

SCALE: dict[int, str] = {
    0: "No provision found",
    1: "Provision stated in general terms, with no procedure or responsible office",
    2: "Provision with a procedure or responsible office, but not both, or not applied to all stages",
    3: "Provision with a procedure and a responsible office, covering all stages of the service year",
}
"""Score levels applied to each criterion."""

MAX_SCORE: int = max(SCALE)

CRITERIA: dict[str, str] = {
    "D1": "Governance and accountability for corps member safety",
    "D2": "Risk assessment of states, routes and places of primary assignment",
    "D3": "Risk-informed deployment, redeployment and exemption",
    "D4": "Informed consent and pre-deployment risk information",
    "D5": "Travel management for camp, posting and passing-out journeys",
    "D6": "Security at orientation camps",
    "D7": "Security at places of primary assignment and during community development service",
    "D8": "Security awareness and training",
    "D9": "Incident reporting and recording",
    "D10": "Crisis management and kidnap response",
    "D11": "Post-incident support, insurance and compensation",
    "D12": "Review, learning and public reporting",
}
"""Scorecard criteria with short labels."""


def validate_scores(scores: pd.DataFrame) -> None:
    """Raise ValueError if a score sheet has unknown criteria, bad scores or no source."""
    unknown = set(scores["criterion_id"]) - set(CRITERIA)
    if unknown:
        raise ValueError(f"Unknown criteria: {sorted(unknown)}")
    bad = scores.loc[~scores["score"].isin(list(SCALE)), "criterion_id"]
    if not bad.empty:
        raise ValueError(f"Scores outside {sorted(SCALE)} for: {sorted(bad)}")
    unsourced = scores.loc[scores["source_ids"].fillna("").str.strip() == "", "criterion_id"]
    if not unsourced.empty:
        raise ValueError(f"Scores without source_ids for: {sorted(unsourced)}")


def summarise(scores: pd.DataFrame, by: str = "framework") -> pd.DataFrame:
    """Total score and percentage of the maximum, per framework (for example before and after reform)."""
    validate_scores(scores)
    grouped = scores.groupby(by)["score"].agg(total="sum", criteria="count").reset_index()
    grouped["max_possible"] = grouped["criteria"] * MAX_SCORE
    grouped["percent"] = 100 * grouped["total"] / grouped["max_possible"]
    return grouped


def sensitivity(scores: pd.DataFrame, by: str = "framework") -> pd.DataFrame:
    """Range of totals if every borderline score moved one point down or up.

    Rows flagged in the `borderline` column are shifted by one point within
    the 0 to 3 scale; other scores are held fixed.
    """
    validate_scores(scores)
    flagged = scores["borderline"].astype(bool)
    low = scores["score"].where(~flagged, (scores["score"] - 1).clip(lower=0))
    high = scores["score"].where(~flagged, (scores["score"] + 1).clip(upper=MAX_SCORE))
    frame = scores.assign(low=low, high=high)
    result = frame.groupby(by).agg(
        total=("score", "sum"), low=("low", "sum"), high=("high", "sum"), criteria=("score", "count")
    )
    result["max_possible"] = result["criteria"] * MAX_SCORE
    for column in ("total", "low", "high"):
        result[f"{column}_percent"] = 100 * result[column] / result["max_possible"]
    return result.reset_index()
