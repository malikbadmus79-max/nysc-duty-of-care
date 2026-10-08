"""Tests for nysc_safety.salience."""

import pandas as pd
import pytest

from nysc_safety import salience


def _incidents() -> pd.DataFrame:
    rows = [
        ("Kano", "North West", 0), ("Borno", "North East", 1), ("Sokoto", "North West", 1),
        ("Lagos", "South West", 3), ("Imo", "South East", 4), ("Rivers", "South South", 5),
        ("Kwara", "North Central", 9),
    ]
    return pd.DataFrame(rows, columns=["state", "zone", "n_articles"])


def test_zone_groups_leave_out_north_central() -> None:
    """The northern group is NW and NE, the southern group SW, SE and SS; NC is in neither."""
    north, south = salience.zone_groups(_incidents())
    assert sorted(north) == [0, 1, 1] and sorted(south) == [3, 4, 5]


def test_mann_whitney_direction_and_effect_size() -> None:
    """Fewer northern articles give a small one-sided p-value and a rank-biserial of -1."""
    north, south = salience.zone_groups(_incidents())
    result = salience.mann_whitney(north, south, n_boot=200)
    assert result["rank_biserial"] == -1.0
    assert 0 < result["p_value"] < 0.05
    assert result["median_north"] == 1 and result["median_south"] == 4
    assert result["rb_ci_lower"] <= result["rank_biserial"] <= result["rb_ci_upper"]


def test_rank_biserial_is_zero_for_identical_groups() -> None:
    """Identical groups give a rank-biserial of 0."""
    assert salience.rank_biserial(4.5, 3, 3) == 0.0


def test_state_shares_sum_to_one_and_cover_all_states() -> None:
    """Shares of incidents and of articles each sum to 1 over the 37 states."""
    table = salience.state_shares(_incidents())
    assert len(table) == 37
    assert table["incident_share"].sum() == pytest.approx(1) and table["article_share"].sum() == pytest.approx(1)
    assert table.loc["Kwara", "article_share"] == pytest.approx(9 / 23)


def test_spearman_interval_contains_estimate() -> None:
    """The Fisher-z interval contains the estimate and perfect agreement gives rho 1."""
    result = salience.spearman(pd.Series([1, 2, 3, 4, 5, 6]), pd.Series([2, 3, 4, 5, 6, 8]))
    assert result["rho"] == pytest.approx(1.0)
    noisy = salience.spearman(pd.Series([1, 2, 3, 4, 5, 6]), pd.Series([2, 1, 4, 3, 6, 5]))
    assert noisy["ci_lower"] < noisy["rho"] < noisy["ci_upper"]
