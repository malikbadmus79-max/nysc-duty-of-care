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


def test_parse_cpi_rows_rolls_year_without_label() -> None:
    """Rows without a year label continue the year; January after December starts the next year."""
    rows = [
        ("Table 1", None, None),
        ("Weights", None, 1000),
        (2023, "January", 500.0),
        (None, "December", 600.0),
        (None, "January", 610.0),
        (None, "February", 620.0),
        (None, None, None),
    ]
    frame = budget.parse_cpi_rows(rows)
    assert list(zip(frame["year"], frame["month"])) == [(2023, 1), (2023, 12), (2024, 1), (2024, 2)]
    assert frame["index"].iloc[-1] == 620.0


def test_parse_cpi_rows_uses_explicit_years() -> None:
    """A year label on the January row is taken as given, not added to."""
    rows = [(2024, "Jan", 95.0), (None, "Dec", 105.0), (2025, "Jan", 120.0)]
    frame = budget.parse_cpi_rows(rows)
    assert list(frame["year"]) == [2024, 2024, 2025]


PAGE_ONE = """Federal Republic of Nigeria 2018 APPROPRIATION BILL
0513001001 FEDERAL MINISTRY OF YOUTH & SPORTS DEVELOPMENT - HQTRS
CODE LINE ITEM AMOUNT
23010105 PURCHASE OF MOTOR VEHICLES 29,000,000
0513003001 NATIONAL YOUTH SERVICE CORPS (NYSC)
CODE LINE ITEM AMOUNT
2 EXPENDITURE 1,410,000
21010101 SALARY 1,000,000
22020601 SECURITY SERVICES 200,000
22021051 SERVICE WIDE TRAINING ON GIFMIS (BUDGET PREPARATION,
EXECUTION & REPORTING) 50,000
NATIONAL ASSEMBLY Page 5 2018 APPROPRIATION BILL"""

PAGE_TWO = """Federal Republic of Nigeria 2018 APPROPRIATION BILL
0513001001 FEDERAL MINISTRY OF YOUTH & SPORTS DEVELOPMENT - HQTRS
CODE LINE ITEM AMOUNT
23010128 PURCHASE OF SECURITY EQUIPMENT 160,000
TOTAL PERSONNEL 1,000,000
TOTAL OVERHEAD 250,000
TOTAL RECURRENT 1,250,000
TOTAL CAPITAL 160,000
TOTAL ALLOCATION 1,410,000
0513003001 NATIONAL YOUTH SERVICE CORPS (NYSC)
CODE PROJECT NAME TYPE AMOUNT
ERGP22100762
PROCUREMENT AND INSTALLATION OF 37 SETS OF CCTV
CAMERAS NEW 60,000
ERGP22100778 PURCHASE OF TRACTORS FOR NYSC FARM 100,000
0513021002 NIGERIA FOOTBALL FEDERATION
CODE LINE ITEM AMOUNT
21010101 SALARY 9,999"""


def test_nysc_block_starts_at_heading_and_stops_at_next_organisation() -> None:
    """The block skips the headquarters lines before it, drops running headers and ends at the next organisation."""
    block = budget.nysc_block([(4, PAGE_ONE), (5, PAGE_TWO)])
    assert block[0].startswith("0513003001")
    assert not any("FOOTBALL" in line or "MOTOR VEHICLES" in line or "HQTRS" in line for line in block)


def test_parse_nysc_block_reconciles_with_totals() -> None:
    """Leaf lines (including a wrapped one) and wrapped projects add up to the printed totals."""
    lines, totals = budget.parse_nysc_block(budget.nysc_block([(4, PAGE_ONE), (5, PAGE_TWO)]))
    check = budget.check_totals(lines, totals)
    assert check["recurrent_matches"] and check["projects_match"]
    projects = lines[lines["kind"] == "capital_project"].set_index("code")
    assert projects.loc["ERGP22100762", "description"] == "PROCUREMENT AND INSTALLATION OF 37 SETS OF CCTV CAMERAS"
    assert projects.loc["ERGP22100778", "amount_naira"] == 100_000
    wrapped = lines[lines["code"] == "22021051"]
    assert wrapped["amount_naira"].iloc[0] == 50_000


def test_summarise_skips_lines_outside_total() -> None:
    """Capital economic lines, flagged in_total False, are not counted twice."""
    lines = pd.DataFrame(
        {"year": [2018, 2018], "amount_naira": [100.0, 100.0], "category": ["security", "security"], "in_total": [True, False]}
    )
    table = budget.summarise(lines, pd.Series({2018: 1.0}), pd.Series({2018: 1})).set_index("year")
    assert table.loc[2018, "security_related_nominal"] == 100


def test_printing_of_security_documents_is_not_security() -> None:
    """Secure printing and social security are excluded from the security category."""
    assert budget.classify("PRINTING OF SECURITY DOCUMENTS") == ""
    assert budget.classify("PROCUREMENT AND INSTALLATION OF 37 SETS OF CCTV CAMERAS") == "security"
    assert budget.classify("FIELD & CAMPING MATERIALS SUPPLIES") == "camps"


def test_measures_and_change() -> None:
    """The three measures drop the allowance or non-security lines; change compares first and last year."""
    lines = pd.DataFrame(
        {
            "year": [2018, 2018, 2018, 2026, 2026, 2026],
            "description": ["SECURITY SERVICES", "CORPS MEMBERS KITTING, TRANSPORT AND FEEDING ALLOWANCE", "SALARY"] * 2,
            "amount_naira": [10.0, 90.0, 900.0, 20.0, 180.0, 800.0],
            "category": ["security", "transport", ""] * 2,
            "in_total": [True] * 6,
        }
    )
    factors = pd.Series({2018: 2.0, 2026: 1.0})
    members = pd.Series({2018: 10, 2026: 20})
    table = budget.measures_table(lines, factors, members).set_index(["measure", "year"])
    assert table.loc[("full", 2018), "real_per_member_2024"] == 20
    assert table.loc[("without_allowance", 2018), "real_per_member_2024"] == 2
    assert table.loc[("security_only", 2026), "real_per_member_2024"] == 1
    changes = budget.change(table.reset_index()).set_index("measure")
    assert changes.loc["full", "change_percent"] == pytest.approx(-50)


def test_running_header_without_column_heading_is_stripped() -> None:
    """A page header with the ministry line but no CODE line is removed, so the ministry code is not read as a project."""
    page = """Federal Republic of Nigeria 2026 APPROPRIATION ACT
0555001001 FEDERAL MINISTRY OF YOUTH DEVELOPMENT - HQTRS
2026
APPROPRIATION
ACT
ERGP25210747 PURCHASE OF 4 AMBULANCE BUSES ONGOING 364,000,000"""
    assert budget.body_lines(page) == ["ERGP25210747 PURCHASE OF 4 AMBULANCE BUSES ONGOING 364,000,000"]


def test_zero_amount_projects_end_at_their_type() -> None:
    """A project printed as "NEW 0" ends there instead of absorbing the next project."""
    block = [
        "0513003001 NATIONAL YOUTH SERVICE CORPS (NYSC)",
        "CODE PROJECT NAME TYPE AMOUNT",
        "ERGP22138950 PURCHASE OF 3 HILUX VANS NEW 0",
        "ERGP22138970 PURCHASE OF ONE (1) FARM TRACTOR NEW 22,000,000",
    ]
    lines, _ = budget.parse_nysc_block(block)
    assert list(lines["amount_naira"]) == [0, 22_000_000]
    assert budget.classify(lines["description"].iloc[1]) == ""


def test_missing_year_is_listed_with_reason() -> None:
    """2024 appears in the table with empty values and its reason."""
    lines = pd.DataFrame({"year": [2023], "description": ["SECURITY SERVICES"], "amount_naira": [10.0],
                          "category": ["security"], "in_total": [True]})
    table = budget.measures_table(lines, pd.Series({2023: 1.0}), pd.Series({2023: 1})).set_index(["measure", "year"])
    assert table.loc[("full", 2024), "status"].startswith("missing")
    assert pd.isna(table.loc[("full", 2024), "real_per_member_2024"])
    assert table.loc[("full", 2023), "status"] == "covered"
