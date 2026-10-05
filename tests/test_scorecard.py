"""Tests for nysc_safety.scorecard."""

import pandas as pd
import pytest

from nysc_safety import scorecard


def sheet(**changes: object) -> pd.DataFrame:
    """A two-criterion score sheet for two frameworks."""
    frame = pd.DataFrame(
        {
            "framework": ["current", "current", "reform_2026", "reform_2026"],
            "criterion_id": ["D1", "D2", "D1", "D2"],
            "score": [1, 0, 2, 3],
            "source_ids": ["S03", "S03", "S05", "S05"],
        }
    )
    for column, value in changes.items():
        frame.loc[0, column] = value
    return frame


def test_twelve_criteria() -> None:
    """The scorecard has criteria D1 to D12."""
    assert list(scorecard.CRITERIA) == [f"D{i}" for i in range(1, 13)]


def test_summarise_percent() -> None:
    """Totals and percentages are computed per framework."""
    result = scorecard.summarise(sheet()).set_index("framework")
    assert result.loc["current", "total"] == 1
    assert result.loc["current", "percent"] == pytest.approx(100 / 6)
    assert result.loc["reform_2026", "percent"] == pytest.approx(500 / 6)


@pytest.mark.parametrize(
    ("column", "value"),
    [("criterion_id", "D99"), ("score", 4), ("source_ids", "")],
)
def test_invalid_sheets_rejected(column: str, value: object) -> None:
    """Unknown criteria, out-of-range scores and missing sources raise ValueError."""
    with pytest.raises(ValueError):
        scorecard.validate_scores(sheet(**{column: value}))


def test_committed_scorecard_is_valid() -> None:
    """The committed scorecard covers D1 to D12 once per framework and cites existing evidence."""
    from nysc_safety import paths

    scores = pd.read_csv(paths.DATA_PROCESSED / "policy_scorecard.csv")
    evidence = pd.read_csv(paths.DATA_INTERIM / "policy_evidence.csv")
    scorecard.validate_scores(scores)
    for _, group in scores.groupby("framework"):
        assert sorted(group["criterion_id"], key=lambda c: int(c[1:])) == list(scorecard.CRITERIA)
    cited = {e for ids in scores["evidence_ids"] for e in ids.split(";")}
    assert cited <= set(evidence["evidence_id"])
