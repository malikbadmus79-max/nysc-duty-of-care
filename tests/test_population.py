"""Tests for nysc_safety.population, on synthetic text laid out like the two PDFs."""

import pandas as pd
import pytest

from nysc_safety import population


def _s551_table(area: str, base: int, run_together: bool = False, misprint: bool = False) -> str:
    """One S551 table: title, 2006 TOTAL row, and three Total rows for 2007-2022."""
    if area == "Nigeria":
        heading = "Table3.2.1:NigeriaPopulationbyageandsex,2006"
    else:
        heading = f"Table 3.2. 3: {'FCT Abuja' if area == 'FCT' else area + ' State'} 2006 Reported Figures"
    lines = [heading, f"TOTAL {base:,} {base // 2:,} {base - base // 2:,}"]
    years = list(population.S551_YEARS)
    for chunk in (years[0:5], years[5:10], years[10:16]):
        cells = []
        for year in chunk:
            total = base + (year - 2006) * 1_000
            male = total // 2
            female = total - male + (7 if misprint and year == 2022 else 0)
            cells.append(f"{total:,} {male:,} {female:,}")
        joined = "".join(cells).replace(" ", "") if run_together and chunk[-1] == 2022 else " ".join(cells)
        lines.append(f"Total {joined}")
    return "\n".join(lines)


def _s551_text(**kwargs) -> str:
    return "\n".join(
        _s551_table(area, 1_000_000 + 10_000 * i, **(kwargs if area == "Kano" else {}))
        for i, area in enumerate(population.S551_ORDER)
    )


def test_s551_tables_are_read_for_every_area_and_year() -> None:
    """All 38 tables give 16 years each; totals follow the table order."""
    frame = population.parse_s551(_s551_text())
    assert len(frame) == 38 * 16 and frame["sum_check"].all()
    kano = frame[(frame["area"] == "Kano") & (frame["year"] == 2022)].iloc[0]
    index = population.S551_ORDER.index("Kano")
    assert kano["population"] == 1_000_000 + 10_000 * index + 16_000


def test_figures_run_together_are_split() -> None:
    """Figures printed without spaces between them are separated by the three-digit groups."""
    frame = population.parse_s551(_s551_text(run_together=True))
    kano = frame[frame["area"] == "Kano"]
    assert kano["sum_check"].all() and kano["population"].is_monotonic_increasing


def test_misprinted_sex_split_is_flagged() -> None:
    """A Total row whose male and female figures do not add to the total is flagged."""
    frame = population.parse_s551(_s551_text(misprint=True))
    flagged = frame[~frame["sum_check"]]
    assert list(zip(flagged["area"], flagged["year"])) == [("Kano", 2022)]


def test_table_out_of_order_is_rejected() -> None:
    """A title that does not match the expected area stops the parse."""
    text = _s551_text().replace("Abia State 2006", "Adamawa State 2006", 1)
    with pytest.raises(ValueError, match="not Abia"):
        population.parse_s551(text)


def test_s552_rows_and_names() -> None:
    """S552 rows are read with state names normalised, including a name split over two lines."""
    values = " ".join(f"{1_000_000 + k:,}" for k in range(11))
    text = "\n".join(
        [
            "POPULATION FORECASTS 2006 - 2016",
            "STATE 2006 2007 2008 2009 2010 2011 2012 2013 2014 2015 2016",
            f"AKWA/IBOM {values}",
            "CROSS",
            f"RIVER {values}",
            f"FCT ABUJA {values}",
            f"NIGERIA {values}",
            "Source: National Population Commission and National Bureau of Statistics Estimates",
        ]
    )
    frame = population.parse_s552(text)
    assert set(frame["area"]) == {"Akwa Ibom", "Cross River", "FCT", "Nigeria"}
    assert frame[(frame["area"] == "FCT") & (frame["year"] == 2016)]["population"].iloc[0] == 1_000_010


def test_crosscheck_difference() -> None:
    """The cross-check gives the S552 minus S551 difference and its percentage."""
    a = pd.DataFrame({"area": ["Lagos"], "year": [2016], "population": [1_000]})
    b = pd.DataFrame({"area": ["Lagos"], "year": [2016], "population": [1_050]})
    row = population.crosscheck(a, b).iloc[0]
    assert row["difference"] == 50 and row["difference_pct"] == 5.0
