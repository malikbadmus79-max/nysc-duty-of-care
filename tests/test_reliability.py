"""Tests for nysc_safety.reliability."""

import pandas as pd
import pytest

from nysc_safety import reliability


def test_kappa_textbook_example() -> None:
    """50 items: 20 yes-yes, 5 yes-no, 10 no-yes, 15 no-no gives p_o 0.70, p_e 0.50, kappa 0.40."""
    a = ["yes"] * 20 + ["yes"] * 5 + ["no"] * 10 + ["no"] * 15
    b = ["yes"] * 20 + ["no"] * 5 + ["yes"] * 10 + ["no"] * 15
    assert reliability.percent_agreement(a, b) == pytest.approx(0.70)
    assert reliability.cohens_kappa(a, b) == pytest.approx(0.40)


def test_kappa_perfect_agreement() -> None:
    """Identical codes give kappa 1."""
    codes = ["camp", "ppa", "cds", "camp"]
    assert reliability.cohens_kappa(codes, codes) == pytest.approx(1.0)


def test_kappa_single_shared_code() -> None:
    """When both coders use one identical code throughout, kappa is defined as 1."""
    assert reliability.cohens_kappa(["camp"] * 3, ["camp"] * 3) == 1.0


def test_unequal_lengths_rejected() -> None:
    """Code lists of different length raise ValueError."""
    with pytest.raises(ValueError):
        reliability.cohens_kappa(["a", "b"], ["a"])


def test_kappa_table_joins_on_id() -> None:
    """kappa_table joins the two sheets on incident_id and reports one row per variable."""
    a = pd.DataFrame({"incident_id": ["INC0001", "INC0002", "INC0003"], "stage": ["camp", "ppa", "cds"]})
    b = pd.DataFrame({"incident_id": ["INC0003", "INC0001", "INC0002"], "stage": ["cds", "camp", "ppa"]})
    table = reliability.kappa_table(a, b, ["stage"])
    assert table.loc[0, "n"] == 3
    assert table.loc[0, "kappa"] == pytest.approx(1.0)
