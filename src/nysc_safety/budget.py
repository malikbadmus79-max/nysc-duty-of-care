"""Budget audit of National Youth Service Corps allocations, 2018 to 2026 (H5).

Line items of the National Youth Service Corps in the federal budget
documents [S556-S565] are classified as security-related when their
description refers to security, orientation camps, transport or insurance.
Nominal amounts are converted to constant 2024 naira with the National Bureau
of Statistics consumer price index, spliced across the 2025 rebasing, and
divided by the number of corps members in the year
(`data/processed/exposure_by_state.csv`, national totals [A10]).
"""

from __future__ import annotations

import re

import pandas as pd

YEARS: tuple[int, int] = (2018, 2026)
BASE_YEAR = 2024

CATEGORIES: dict[str, re.Pattern[str]] = {
    "security": re.compile(r"\bsecurity\b|\bsafety\b|\bsurveillance\b|\bcctv\b|\bperimeter fenc\w*|\bfencing\b|\bguard(s|ing)?\b", re.I),
    "camps": re.compile(r"\bcamps?\b|\borientation\b", re.I),
    "transport": re.compile(r"\btransport\w*\b|\bvehicles?\b|\bbus(es)?\b|\btravel\w*\b|\bmotor\b|\bmobili[sz]ation\b", re.I),
    "insurance": re.compile(r"\binsurance\b|\bassurance\b|\bindemnit\w*\b", re.I),
}
"""Description patterns for each security-related category, checked in this order."""


def classify(description: str) -> str:
    """First security-related category whose pattern matches the description, or "" for other lines."""
    for category, pattern in CATEGORIES.items():
        if pattern.search(description or ""):
            return category
    return ""


def annual_cpi(monthly: pd.DataFrame) -> pd.DataFrame:
    """Mean all-items index by series and year, with the number of months averaged.

    `monthly` has columns `series` (`2009` for the index with November 2009 =
    100, `2024` for the rebased index with 2024 = 100), `year`, `month` and
    `index`.
    """
    grouped = monthly.groupby(["series", "year"])["index"]
    return grouped.agg(index="mean", months="count").reset_index()


def deflators(annual: pd.DataFrame, base_year: int = BASE_YEAR) -> pd.Series:
    """Factor converting naira of each year to naira of `base_year`, by year [A16].

    Years up to `base_year` use the November 2009 series: factor =
    mean index in `base_year` / mean index in the year. Years after
    `base_year` use the rebased series, whose mean over `base_year` is 100:
    factor = 100 / mean index in the year.
    """
    old = annual[annual["series"].astype(str) == "2009"].set_index("year")["index"]
    new = annual[annual["series"].astype(str) == "2024"].set_index("year")["index"]
    if base_year not in old.index:
        raise ValueError(f"The November 2009 series has no months in {base_year}")
    factors = {year: old[base_year] / value for year, value in old.items() if year <= base_year}
    factors.update({year: 100 / value for year, value in new.items() if year > base_year})
    return pd.Series(factors, name="factor_to_2024").sort_index()


def summarise(lines: pd.DataFrame, factors: pd.Series, members: pd.Series) -> pd.DataFrame:
    """Nominal and real security-related allocation by year and per corps member.

    `lines` has columns `year`, `amount_naira` and `category` ("" for lines
    that are not security-related). `members` is corps members by year.
    """
    related = lines[lines["category"] != ""]
    nominal = related.groupby("year")["amount_naira"].sum()
    total = lines.groupby("year")["amount_naira"].sum()
    years = sorted(set(total.index))
    table = pd.DataFrame(index=pd.Index(years, name="year"))
    table["nysc_total_nominal"] = total
    table["security_related_nominal"] = nominal.reindex(years, fill_value=0)
    table["factor_to_2024"] = factors.reindex(years)
    table["security_related_real_2024"] = table["security_related_nominal"] * table["factor_to_2024"]
    table["corps_members"] = members.reindex(years)
    table["real_per_member_2024"] = table["security_related_real_2024"] / table["corps_members"]
    table["share_of_nysc_total"] = table["security_related_nominal"] / table["nysc_total_nominal"]
    for category in CATEGORIES:
        amounts = related[related["category"] == category].groupby("year")["amount_naira"].sum()
        table[f"{category}_real_2024"] = amounts.reindex(years, fill_value=0) * table["factor_to_2024"]
    return table.reset_index()
