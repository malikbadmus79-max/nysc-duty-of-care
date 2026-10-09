"""Tests for nysc_safety.risk, on synthetic data."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from nysc_safety import coding, risk


def _exposure(states=("Abia", "Kano", "Lagos"), years=range(2010, 2027), size=10_000) -> pd.DataFrame:
    return pd.DataFrame([(s, y, size) for s in states for y in years], columns=["state", "year", "exposure"])


def _incidents(rows) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["state", "event_date"])


def test_panel_counts_scales_cutoff_year_and_drops_later_events() -> None:
    """Counts by state-year; the cutoff year's exposure is scaled; events after the cutoff are left out."""
    incidents = _incidents([("Kano", "2015-03-01"), ("Kano", "2015-09-01"), ("Lagos", "2026-12-01")])
    panel = risk.state_year_panel(incidents, _exposure(), date(2026, 7, 2))
    assert len(panel) == 3 * 17
    kano_2015 = panel[(panel["state"] == "Kano") & (panel["year"] == 2015)].iloc[0]
    assert kano_2015["incidents"] == 2
    assert panel["incidents"].sum() == 2
    assert panel[(panel["year"] == 2026)]["exposure"].iloc[0] == pytest.approx(10_000 * 182 / 365)


def test_two_year_window_sums_consecutive_years() -> None:
    """With a two-year window, exposure is the year plus the year before (the first year has no year before)."""
    panel = risk.state_year_panel(_incidents([]), _exposure(), date(2026, 12, 31), window_years=2)
    abia = panel[panel["state"] == "Abia"].set_index("year")["exposure"]
    assert abia[2010] == 10_000 and abia[2011] == 20_000


def test_drop_small_states() -> None:
    """States with total exposure below the minimum are dropped and listed."""
    panel = pd.DataFrame({"state": ["A", "A", "B"], "year": [1, 2, 1], "exposure": [400, 400, 5_000], "incidents": [0, 1, 2]})
    kept, small = risk.drop_small_states(panel)
    assert small == ["A"] and set(kept["state"]) == {"B"}


def _panel(rates_by_state: dict[str, float], years: int = 15, exposure: float = 10_000, seed: int = 1, nb_alpha: float = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for state, rate in rates_by_state.items():
        for year in range(years):
            mean = rate * exposure / 10_000
            if nb_alpha:
                mean = rng.gamma(1 / nb_alpha, mean * nb_alpha)
            rows.append((state, 2010 + year, exposure, rng.poisson(mean)))
    return pd.DataFrame(rows, columns=["state", "year", "exposure", "incidents"])


def test_h3_detects_different_rates() -> None:
    """Very different state rates give a small p-value; equal rates do not."""
    different = risk.h3_test(_panel({"A": 0.2, "B": 3.0, "C": 6.0}))
    assert different["model"] == "poisson" and different["p_value"] < 0.001 and different["df"] == 2
    equal = risk.h3_test(_panel({"A": 2.0, "B": 2.0, "C": 2.0}, seed=3))
    assert equal["p_value"] > 0.05


def test_h3_switches_to_negative_binomial_when_overdispersed() -> None:
    """A Pearson dispersion above 1.5 leads to the negative binomial model."""
    result = risk.h3_test(_panel({"A": 5.0, "B": 5.0, "C": 5.0}, years=40, nb_alpha=2.0, seed=4))
    assert result["dispersion_poisson"] > 1.5 and result["model"] == "negative_binomial"
    assert result["nb_alpha"] > 0


def test_state_rates_and_ranks() -> None:
    """Rates are per 10,000 exposed; ranks by count and by rate can differ."""
    panel = pd.DataFrame(
        {"state": ["Kano", "Lagos"], "year": [2020, 2020], "exposure": [100_000, 10_000], "incidents": [5, 2]}
    )
    table = risk.state_rates(panel).set_index("state")
    assert table.loc["Lagos", "rate"] == pytest.approx(2.0)
    assert table.loc["Kano", "rank_count"] == 1 and table.loc["Kano", "rank_rate"] == 2
    assert table.loc["Lagos", "ci_lower"] < 2.0 < table.loc["Lagos", "ci_upper"]


def test_top_states_breaks_ties_alphabetically() -> None:
    """The states with most incidents come first; ties are alphabetical."""
    panel = pd.DataFrame({"state": ["B", "A", "C"], "year": [1, 1, 1], "exposure": [1, 1, 1], "incidents": [3, 3, 1]})
    assert risk.top_states(panel, 2) == ["A", "B"]


def test_spearman_one_sided() -> None:
    """A positive association gives rho > 0 and a small one-sided p; a negative one gives p near 1."""
    x = pd.Series(range(20), dtype=float)
    up = risk.spearman_one_sided(x, x + np.random.default_rng(0).normal(0, 3, 20), n_boot=300)
    assert up["rho"] > 0.5 and up["p_value_one_sided"] < 0.01 and up["ci_lower"] < up["rho"] < up["ci_upper"]
    down = risk.spearman_one_sided(x, -x, n_boot=50)
    assert down["p_value_one_sided"] > 0.99


def test_exposure_variant_uses_subset_of_figures() -> None:
    """Variants use only the chosen count types and batch years; states without figures drop out."""
    figures = pd.DataFrame(
        {
            "state": ["Abia", "Abia", "Kano", "Kano"],
            "batch_year": [2017, 2021, 2018, 2022],
            "count": [1_000, 3_000, 2_000, 2_000],
            "count_type": ["sworn_in", "registered", "sworn_in", "sworn_in"],
        }
    )
    national = pd.DataFrame({"year": [2010], "count": [100_000], "use": ["yes"]})
    sworn = risk.exposure_variant(figures, national, ("sworn_in",))
    assert sworn[sworn["year"] == 2020].set_index("state")["share"].to_dict() == pytest.approx({"Abia": 1 / 3, "Kano": 2 / 3})
    recent = risk.exposure_variant(figures, national, ("sworn_in",), min_batch_year=2019)
    assert set(recent["state"]) == {"Kano"}


def test_h4_frame_aligns_states_and_ranks() -> None:
    """Every state appears once, in the order of coding.STATES, with rank 1 for the highest rate."""
    nysc = pd.Series({"Kaduna": 0.5, "Lagos": 0.1})
    general = pd.Series({"Kaduna": 9.0, "Lagos": 2.0, "Kano": 4.0})
    frame = risk.h4_frame(nysc, general)
    assert list(frame["state"]) == list(coding.STATES)
    row = frame.set_index("state")
    assert row.loc["Kaduna", "rank_nysc"] == 1 and row.loc["Kaduna", "rank_general"] == 1
    assert pd.isna(row.loc["Kano", "nysc_rate"]) and row.loc["Kano", "rank_general"] == 2
    assert row.loc["Kaduna", "zone"] == "North West"
