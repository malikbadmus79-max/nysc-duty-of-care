"""Tests for nysc_safety.budget."""

import pandas as pd
import pytest

from nysc_safety import budget


@pytest.mark.parametrize(
    ("description", "category"),
    [
        ("PROVISION OF SECURITY EQUIPMENT AT ORIENTATION CAMPS", "security"),
        ("REHABILITATION OF PERMANENT ORIENTATION CAMP, KUBWA", "camps"),
        ("PURCHASE OF OPERATIONAL VEHICLES", "transport"),
        ("LOCAL TRAVEL & TRANSPORT: OTHERS", "transport"),
        ("INSURANCE PREMIUM", "insurance"),
        ("GROUP LIFE ASSURANCE FOR CORPS MEMBERS", "insurance"),
        ("OFFICE STATIONERIES / COMPUTER CONSUMABLES", ""),
        ("", ""),
    ],
)
def test_classify(description: str, category: str) -> None:
    """Descriptions map to the first matching category, or to none."""
    assert budget.classify(description) == category


def monthly() -> pd.DataFrame:
    """Two months a year: November 2009 series for 2023-2024, rebased series for 2024-2025."""
    rows = [
        ("2009", 2023, 1, 600.0), ("2009", 2023, 2, 700.0),
        ("2009", 2024, 1, 900.0), ("2009", 2024, 2, 1100.0),
        ("2024", 2024, 1, 95.0), ("2024", 2024, 2, 105.0),
        ("2024", 2025, 1, 120.0), ("2024", 2025, 2, 130.0),
    ]
    return pd.DataFrame(rows, columns=["series", "year", "month", "index"])


def test_annual_cpi_means_and_months() -> None:
    """Annual values are the mean of the months, kept apart by series."""
    annual = budget.annual_cpi(monthly()).set_index(["series", "year"])
    assert annual.loc[("2009", 2024), "index"] == 1000
    assert annual.loc[("2024", 2025), "months"] == 2


def test_deflators_splice_at_2024() -> None:
    """Up to 2024 the old series is rescaled to its 2024 mean; after 2024 the rebased series is used."""
    factors = budget.deflators(budget.annual_cpi(monthly()))
    assert factors[2023] == pytest.approx(1000 / 650)
    assert factors[2024] == pytest.approx(1.0)
    assert factors[2025] == pytest.approx(100 / 125)


def test_deflators_need_base_year() -> None:
    """Without months of the base year in the old series the splice is impossible."""
    data = monthly()
    with pytest.raises(ValueError):
        budget.deflators(budget.annual_cpi(data[~((data["series"] == "2009") & (data["year"] == 2024))]))


def test_summarise() -> None:
    """Only security-related lines count; real values use the factor; per member divides by members."""
    lines = pd.DataFrame(
        {
            "year": [2023, 2023, 2024],
            "amount_naira": [100.0, 400.0, 300.0],
            "category": ["camps", "", "insurance"],
        }
    )
    factors = pd.Series({2023: 2.0, 2024: 1.0})
    members = pd.Series({2023: 10, 2024: 30})
    table = budget.summarise(lines, factors, members).set_index("year")
    assert table.loc[2023, "security_related_real_2024"] == 200
    assert table.loc[2023, "real_per_member_2024"] == 20
    assert table.loc[2023, "share_of_nysc_total"] == pytest.approx(0.2)
    assert table.loc[2024, "insurance_real_2024"] == 300 and table.loc[2024, "camps_real_2024"] == 0
