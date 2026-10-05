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
