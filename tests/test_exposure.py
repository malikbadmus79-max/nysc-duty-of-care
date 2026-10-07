"""Tests for nysc_safety.exposure."""

import pandas as pd
import pytest

from nysc_safety import exposure

FIGURES = pd.DataFrame(
    {
        "state": ["Lagos", "Lagos", "Lagos", "Ekiti", "Ekiti", "Ekiti"],
        "batch_year": [2018, 2020, 2022, 2018, 2019, 2023],
        "count": [6000, 5000, 7000, 1000, 3000, 2000],
        "count_type": ["sworn_in", "registered", "sworn_in", "sworn_in", "deployed", "sworn_in"],
    }
)

NATIONAL = pd.DataFrame(
    {
        "year": [2010, 2012, 2012, 2014],
        "count": [200_000, 240_000, 999_999, 260_000],
        "use": ["yes", "yes", "no", "yes"],
    }
)


def test_course_size_is_median_and_shares_sum_to_one() -> None:
    """Course size is the median of a state's figures; shares add up to 1."""
    sizes = exposure.course_sizes(FIGURES)
    assert sizes.loc["Lagos", "course_size"] == 6000
    assert sizes.loc["Ekiti", "course_size"] == 2000
    assert sizes.loc["Ekiti", "n_figures"] == 3
    shares = exposure.state_shares(sizes)
    assert shares.sum() == pytest.approx(1.0)
    assert shares["Lagos"] == pytest.approx(0.75)


def test_count_type_filter() -> None:
    """Restricting to sworn-in figures drops other types."""
    sizes = exposure.course_sizes(FIGURES, count_types=("sworn_in",))
    assert sizes.loc["Lagos", "n_figures"] == 2
    assert sizes.loc["Ekiti", "course_size"] == 1500


def test_unknown_state_rejected() -> None:
    """A misspelt state name raises an error."""
    bad = FIGURES.assign(state=["Lagos State"] * 6)
    with pytest.raises(ValueError):
        exposure.course_sizes(bad)


def test_annual_totals_interpolate_and_flag() -> None:
    """Gaps are filled linearly between used years, held flat at the ends, and flagged."""
    totals = exposure.annual_totals(NATIONAL, years=range(2010, 2017))
    assert totals.loc[2011, "national_total"] == 220_000
    assert totals.loc[2013, "national_total"] == 250_000
    assert totals.loc[2016, "national_total"] == 260_000
    assert bool(totals.loc[2011, "interpolated"]) and not bool(totals.loc[2012, "interpolated"])


def test_duplicate_used_year_rejected() -> None:
    """Two totals marked for use in the same year raise an error."""
    with pytest.raises(ValueError):
        exposure.annual_totals(NATIONAL.assign(use="yes"))


def test_exposure_table_is_share_times_total() -> None:
    """Exposure equals share times the national total, for every state and year."""
    shares = exposure.state_shares(exposure.course_sizes(FIGURES))
    table = exposure.exposure_table(shares, exposure.annual_totals(NATIONAL, years=range(2010, 2013)))
    assert len(table) == 2 * 3
    row = table[(table["state"] == "Lagos") & (table["year"] == 2012)].iloc[0]
    assert row["exposure"] == 180_000
