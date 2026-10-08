"""Projected population by state, from two National Population Commission series.

Run from the repository root with `python -m nysc_safety.population`.

Reads two PDFs saved by `nysc_safety.download`:

- S551, National Population Commission projections for 2007 to 2022. Each
  state table ("<State> Projected Population by Age and Sex, 2007-2022") has
  a `TOTAL` row for the 2006 census and three `Total` rows covering 2007-2011,
  2012-2016 and 2017-2022, each listing total, male and female for every year.
- S552, National Bureau of Statistics forecasts for 2006 to 2016, one row per
  state with one total per year.

Writes `data/interim/population_by_state.csv` (S551, every state and year
2007 to 2022) and `data/interim/population_crosscheck.csv` (S551 against S552
for 2016, the last year both cover).
"""

from __future__ import annotations

import re

import pandas as pd

from nysc_safety import coding, paths

NUMBER = re.compile(r"\d{1,3}(?:,\d{3})+")
"""A figure with thousands separators. Figures run together in the PDF text are split correctly
because each group after the first has exactly three digits."""

S551_FILE = "S551_npc_population_projections_2022.pdf"
S552_FILE = "S552_nbs_population_forecasts_2016.pdf"
S551_PAGES = range(52, 205)
"""Zero-based page range of the national and state tables in S551 (printed pages 53 to 204)."""
S551_YEARS = range(2007, 2023)
S552_YEARS = range(2006, 2017)

S551_TITLE = re.compile(
    r"Table\s*3\.2\.\s*\d+:\s*(.+?)\s*(?:2006\s*Reported\s*Figure|Population\s*by\s*age\s*and\s*sex,\s*2006)",
    re.IGNORECASE,
)
S551_ORDER: tuple[str, ...] = ("Nigeria",) + tuple(s for s in coding.STATES if s != "FCT") + ("FCT",)
"""Order of the tables in S551: national, the 36 states alphabetically, then the FCT."""

S552_NAMES: dict[str, str] = {"AKWA/IBOM": "Akwa Ibom", "FCT ABUJA": "FCT", "NIGERIA": "Nigeria"}


def _numbers(line: str) -> list[int]:
    """All figures with thousands separators in a line, as integers."""
    return [int(x.replace(",", "")) for x in NUMBER.findall(line)]


def _compact(name: str) -> str:
    """Lower-case name with spaces removed, for matching table titles."""
    return re.sub(r"[^a-z]", "", name.lower())


def parse_s551(text: str) -> pd.DataFrame:
    """Total, male and female population by area and year from the text of the S551 tables.

    Each table is matched to its title; a title that does not name the area
    expected in `S551_ORDER` raises ValueError. `sum_check` is False where
    male plus female differs from the total.
    """
    titles: list[str] = []
    blocks: list[list[int]] = []
    for line in text.splitlines():
        title = S551_TITLE.search(line)
        if title:
            titles.append(title.group(1))
        if line.startswith("TOTAL "):
            blocks.append([])
        elif line.startswith("Total ") and blocks:
            blocks[-1].extend(_numbers(line))
    if len(blocks) != len(S551_ORDER):
        raise ValueError(f"expected {len(S551_ORDER)} tables, found {len(blocks)}")
    rows = []
    for area, values, title in zip(S551_ORDER, blocks, titles[-len(blocks):]):
        if _compact(area) not in _compact(title):
            raise ValueError(f"table titled {title!r} is not {area}")
        if len(values) != 3 * len(S551_YEARS):
            raise ValueError(f"{area}: expected {3 * len(S551_YEARS)} figures, found {len(values)}")
        for k, year in enumerate(S551_YEARS):
            total, male, female = values[3 * k : 3 * k + 3]
            rows.append(
                {"area": area, "year": year, "population": total, "male": male, "female": female,
                 "sum_check": total == male + female}
            )
    return pd.DataFrame(rows)


def parse_s552(text: str) -> pd.DataFrame:
    """Total population by area and year from the text of the S552 state table, 2006 to 2016."""
    rows = []
    pending = ""
    for line in text.splitlines():
        values = _numbers(line)
        name = NUMBER.split(line)[0].strip()
        if len(values) != len(S552_YEARS):
            pending = line.strip() if line.strip().isupper() and not values else ""
            continue
        if not name and pending:
            name = pending
        elif pending and name and not pending.startswith(("STATE", "POPULATION")):
            name = f"{pending} {name}"
        pending = ""
        area = S552_NAMES.get(name, name.title())
        rows.extend({"area": area, "year": y, "population": v} for y, v in zip(S552_YEARS, values))
    frame = pd.DataFrame(rows)
    unknown = set(frame["area"]) - set(S551_ORDER)
    if unknown:
        raise ValueError(f"unknown areas in S552: {sorted(unknown)}")
    return frame


def crosscheck(s551: pd.DataFrame, s552: pd.DataFrame, year: int = 2016) -> pd.DataFrame:
    """Both series for one year, with the difference and percentage difference (S552 minus S551)."""
    a = s551[s551["year"] == year].set_index("area")["population"].rename("population_s551")
    b = s552[s552["year"] == year].set_index("area")["population"].rename("population_s552")
    frame = pd.concat([a, b], axis=1).reset_index().rename(columns={"index": "area"})
    frame.insert(1, "year", year)
    frame["difference"] = frame["population_s552"] - frame["population_s551"]
    frame["difference_pct"] = (100 * frame["difference"] / frame["population_s551"]).round(1)
    return frame


def _pdf_text(path, pages: range | None = None) -> str:
    """Text of the given pages of a PDF."""
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        chosen = pdf.pages if pages is None else [pdf.pages[i] for i in pages]
        return "\n".join(page.extract_text() or "" for page in chosen)


def main() -> None:
    """Build `data/interim/population_by_state.csv` and `data/interim/population_crosscheck.csv`."""
    pdfs = paths.DATA_RAW / "pdfs"
    s551 = parse_s551(_pdf_text(pdfs / S551_FILE, S551_PAGES))
    s552 = parse_s552(_pdf_text(pdfs / S552_FILE, range(1, 3)))
    s551 = s551.rename(columns={"area": "state"})
    s551["source_id"] = "S551"
    s551["note"] = ""
    misprint = ~s551["sum_check"]
    s551.loc[misprint, "note"] = (
        "Male and female in the Total row do not add to the total; the total equals the sum of the "
        "age groups and is used (C18)."
    )
    out = s551[["state", "year", "population", "male", "female", "source_id", "note"]]
    out.to_csv(paths.DATA_INTERIM / "population_by_state.csv", index=False)
    check = crosscheck(s551.rename(columns={"state": "area"}), s552).rename(columns={"area": "state"})
    check["source_ids"] = "S551;S552"
    check.to_csv(paths.DATA_INTERIM / "population_crosscheck.csv", index=False)
    states_2022 = out[(out["year"] == 2022) & (out["state"] != "Nigeria")]["population"].sum()
    national_2022 = int(out[(out["year"] == 2022) & (out["state"] == "Nigeria")]["population"].iloc[0])
    print(f"S551: {out['state'].nunique() - 1} states and the national total, {len(S551_YEARS)} years")
    print(f"2022: states sum to {states_2022:,}; national table {national_2022:,}")
    print(f"Rows failing the male + female check: {int(misprint.sum())}")
    states = check[check["state"] != "Nigeria"]
    print(f"2016 S552 vs S551: median absolute difference {states['difference_pct'].abs().median():.1f}%; "
          f"Spearman rho {states['population_s551'].corr(states['population_s552'], method='spearman'):.3f}")


if __name__ == "__main__":
    main()
