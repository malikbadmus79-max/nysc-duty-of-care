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
from collections.abc import Iterable
from pathlib import Path

import openpyxl
import pandas as pd

from nysc_safety import paths

YEARS: tuple[int, int] = (2018, 2026)
BASE_YEAR = 2024

CATEGORIES: dict[str, re.Pattern[str]] = {
    "security": re.compile(
        r"\bsecurity\b|\bsafety\b|\bsurveillance\b|\bcctv\b|\bfenc(e|es|ing)\b|\bguard(s|ing)?\b|\blife jackets?\b",
        re.I,
    ),
    "camps": re.compile(r"\bcamps?\b|\bcamping\b|\borientation\b", re.I),
    "transport": re.compile(
        r"\btransport\w*\b|\bvehicles?\b|\bbus(es)?\b|\bvans?\b|\btrucks?\b|\bmotor ?cycles?\b|\bhilux\b"
        r"|\bambulances?\b|\bjeeps?\b|\btravel\w*\b|\bmobili[sz]ation\b",
        re.I,
    ),
    "insurance": re.compile(r"\binsurance\b|\bassurance\b|\bindemnit\w*\b", re.I),
}
"""Description patterns for each security-related category, checked in this order [A18]."""

EXCLUDE = re.compile(r"\bsecurity documents?\b|\bsocial security\b", re.I)
"""Descriptions that match a category pattern but do not concern physical security: printing of
security documents (certificates and other secure stationery) and social security contributions."""


def classify(description: str) -> str:
    """First security-related category whose pattern matches the description, or "" for other lines."""
    text = description or ""
    if EXCLUDE.search(text):
        return ""
    for category, pattern in CATEGORIES.items():
        if pattern.search(text):
            return category
    return ""


NYSC_HEADING = re.compile(r"^(\d{10})\s+NATIONAL\s+YOUTH\s+SERVICE\s+CORPS", re.I)
"""Heading of the NYSC block in the budget details: the 10-digit organisation code and name."""
MDA_HEADING = re.compile(r"^(\d{10})\s+[A-Z]")
LEAF_LINE = re.compile(r"^(2[123]\d{6})\s+(.+?)\s+(-?[\d,]{1,})$")
"""Economic line with an 8-digit code (21 personnel, 22 overhead, 23 capital), description and amount."""
LEAF_START = re.compile(r"^2[123]\d{6}\s+\D")
"""Start of an economic line whose description wraps onto the next line, where the amount is printed."""
TOTAL_LINE = re.compile(r"^TOTAL\s+(PERSONNEL|OVERHEAD|RECURRENT|CAPITAL|ALLOCATION)\s+(-?[\d,]+)$", re.I)
PROJECT_START = re.compile(r"^([A-Z]{2,6}\d{6,}|\d{8,})\b\s*(.*)$")
AMOUNT_END = re.compile(r"^(.*?)\s*(?:\b(NEW|ONGOING|ON-GOING)\b\s*)?(\d{1,3}(?:,\d{3})+|\d+)$")
PAGE_FOOTER = re.compile(r"^NATIONAL ASSEMBLY\s+Page\b", re.I)
HEADER_WORD = re.compile(r"^(\d{4}|APPROPRIATION|ACT|BILL|AMENDMENT|DETAILS)$", re.I)
"""Words of the document title that the running header prints on separate lines."""


def pdf_page_texts(path: Path, pattern: re.Pattern[str]) -> list[tuple[int, str]]:
    """Text of the pages that match `pattern` and of the page after each, read one page at a time.

    Pages are opened and closed one by one with pypdfium2, so a document of
    several hundred megabytes is read without holding it in memory.
    """
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(str(path))
    try:
        texts: dict[int, str] = {}
        wanted: set[int] = set()
        for number in range(len(document)):
            page = document[number]
            textpage = page.get_textpage()
            text = textpage.get_text_range()
            textpage.close()
            page.close()
            if pattern.search(text) or number in wanted:
                texts[number] = text
                if pattern.search(text):
                    wanted.add(number + 1)
        return sorted(texts.items())
    finally:
        document.close()


def body_lines(page_text: str) -> list[str]:
    """Lines of a budget page without its footer and running header.

    The running header is the "Federal Republic of Nigeria" line, the line
    naming the first organisation of the ministry (a 10-digit code), the
    words of the document title ("2018", "APPROPRIATION", "ACT") and a
    column heading ("CODE LINE ITEM AMOUNT") directly after them.
    """
    lines = [line.strip() for line in page_text.replace("\r", "\n").split("\n") if line.strip()]
    lines = [line for line in lines if not PAGE_FOOTER.match(line)]
    index = 0
    if lines and lines[0].lower().startswith("federal republic of nigeria"):
        index = 1
        if index < len(lines) and MDA_HEADING.match(lines[index]) and not NYSC_HEADING.match(lines[index]):
            index += 1
        while index < len(lines) and HEADER_WORD.match(lines[index]):
            index += 1
        if index < len(lines) and lines[index].upper().startswith("CODE "):
            index += 1
    return lines[index:]


def nysc_block(pages: Iterable[tuple[int, str]]) -> list[str]:
    """Lines of the NYSC block: from its first detail heading to the heading of the next organisation."""
    lines: list[str] = []
    for _, text in pages:
        lines.extend(body_lines(text))
    block: list[str] = []
    code = None
    for index, line in enumerate(lines):
        heading = NYSC_HEADING.match(line)
        following = lines[index + 1].upper() if index + 1 < len(lines) else ""
        if code is None:
            if heading and following.startswith("CODE "):
                code = heading.group(1)
                block.append(line)
            continue
        other = MDA_HEADING.match(line)
        if other and other.group(1) != code and following.startswith("CODE "):
            break
        block.append(line)
    if code is None:
        raise ValueError("No NYSC detail heading found")
    return block


def _amount(text: str) -> int:
    """Whole naira from a printed amount such as "1,234,567"."""
    return int(text.replace(",", ""))


def parse_nysc_block(block: list[str]) -> tuple[pd.DataFrame, dict[str, int]]:
    """Leaf economic lines and capital projects of the NYSC block, and the printed totals.

    Economic lines with an 8-digit code are leaf items; codes of 2, 4 and 6
    digits are subtotals and are skipped. Capital projects follow the heading
    "CODE PROJECT NAME TYPE AMOUNT"; a project's description can run over
    several lines and ends with its type (NEW, ONGOING) and amount.
    """
    rows: list[dict[str, object]] = []
    totals: dict[str, int] = {}
    in_projects = False
    pending: list[str] | None = None
    wrapped: str | None = None
    for line in block:
        upper = line.upper()
        if upper.startswith("CODE ") and "PROJECT" in upper:
            in_projects = True
            pending = None
            continue
        if upper.startswith("CODE ") or NYSC_HEADING.match(line):
            continue
        total = TOTAL_LINE.match(line)
        if total:
            totals[total.group(1).lower()] = _amount(total.group(2))
            in_projects = False
            continue
        if not in_projects:
            if wrapped is not None:
                line, wrapped = f"{wrapped} {line}", None
            leaf = LEAF_LINE.match(line)
            if not leaf and LEAF_START.match(line):
                wrapped = line
                continue
            if leaf:
                kind = {"21": "personnel", "22": "overhead", "23": "capital"}[leaf.group(1)[:2]]
                rows.append({"kind": kind, "code": leaf.group(1), "description": leaf.group(2), "amount_naira": _amount(leaf.group(3))})
            continue
        start = PROJECT_START.match(line)
        if pending is None:
            if not start:
                continue
            pending = [start.group(1), start.group(2)]
        else:
            pending.append(line)
        text = " ".join(part for part in pending[1:] if part)
        end = AMOUNT_END.match(text)
        if end and ("," in end.group(3) or end.group(2)):
            rows.append({"kind": "capital_project", "code": pending[0], "description": end.group(1).strip(),
                         "amount_naira": _amount(end.group(3))})
            pending = None
    return pd.DataFrame(rows, columns=["kind", "code", "description", "amount_naira"]), totals


def check_totals(lines: pd.DataFrame, totals: dict[str, int]) -> dict[str, object]:
    """Compare the parsed lines with the printed totals of the NYSC block."""
    recurrent = int(lines.loc[lines["kind"].isin(["personnel", "overhead"]), "amount_naira"].sum())
    capital_leaf = int(lines.loc[lines["kind"] == "capital", "amount_naira"].sum())
    projects = int(lines.loc[lines["kind"] == "capital_project", "amount_naira"].sum())
    return {
        "recurrent_parsed": recurrent,
        "recurrent_printed": totals.get("recurrent"),
        "capital_leaf_parsed": capital_leaf,
        "capital_projects_parsed": projects,
        "capital_printed": totals.get("capital"),
        "recurrent_matches": recurrent == totals.get("recurrent"),
        "projects_match": projects == totals.get("capital"),
    }


MONTHS: tuple[str, ...] = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def parse_cpi_rows(rows: Iterable[tuple]) -> pd.DataFrame:
    """Monthly all-items index from the rows of Table 1 of a National Bureau of Statistics CPI workbook.

    Each data row holds a year (first row of the year only), a month name and
    the monthly all-items index. Where the year label is missing, as for 2024
    in the December 2024 tables, January after December starts the next year.
    """
    records = []
    year = None
    last_month = None
    for row in rows:
        first, month, value = (list(row) + [None, None, None])[:3]
        if isinstance(first, (int, float)) and 1900 < first < 2100:
            year = int(first)
        elif isinstance(first, str) and first.strip().isdigit():
            year = int(first.strip())
        if not (isinstance(month, str) and month.strip()[:3].title() in MONTHS and isinstance(value, (int, float))):
            continue
        number = MONTHS.index(month.strip()[:3].title()) + 1
        if year is None:
            continue
        if last_month == 12 and number == 1 and records and records[-1][0] == year:
            year += 1
        records.append((year, number, float(value)))
        last_month = number
    frame = pd.DataFrame(records, columns=["year", "month", "index"])
    if frame.duplicated(["year", "month"]).any():
        raise ValueError("Duplicate months in CPI table")
    return frame


def read_cpi_workbook(path: Path, series: str, source_id: str) -> pd.DataFrame:
    """Monthly all-items index from the first sheet (Table 1) of a CPI workbook, labelled with its series."""
    sheet = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0]
    frame = parse_cpi_rows(sheet.iter_rows(max_col=3, values_only=True))
    frame.insert(0, "series", series)
    frame["source_id"] = source_id
    return frame


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
    that are not security-related), and optionally `in_total`; rows with
    `in_total` False (capital economic lines, which the capital projects
    repeat) are left out. `members` is corps members by year.
    """
    if "in_total" in lines.columns:
        lines = lines[lines["in_total"].astype(bool)]
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


ALLOWANCE = re.compile(r"\bkitting\b", re.I)
"""The corps members' kitting, transport and feeding allowance, which dominates the transport category."""

MEASURES: dict[str, str] = {
    "full": "Security, camps, transport and insurance lines [A18]",
    "without_allowance": "As full, without the kitting, transport and feeding allowance",
    "security_only": "Security category only",
}


def measure_lines(lines: pd.DataFrame, measure: str) -> pd.DataFrame:
    """Lines with `category` set to "" for those outside the measure (see `MEASURES`)."""
    frame = lines.copy()
    if measure == "without_allowance":
        frame.loc[frame["description"].str.contains(ALLOWANCE), "category"] = ""
    elif measure == "security_only":
        frame.loc[frame["category"] != "security", "category"] = ""
    elif measure != "full":
        raise ValueError(f"Unknown measure: {measure}")
    return frame


def measures_table(lines: pd.DataFrame, factors: pd.Series, members: pd.Series) -> pd.DataFrame:
    """Real security-related allocation per corps member by year, in 2024 naira, for each measure."""
    rows = []
    for measure in MEASURES:
        table = summarise(measure_lines(lines, measure), factors, members)
        table.insert(1, "measure", measure)
        rows.append(table)
    return pd.concat(rows, ignore_index=True)


def change(table: pd.DataFrame, start: int = YEARS[0], end: int = YEARS[1]) -> pd.DataFrame:
    """Real allocation per corps member in the first and last year of each measure, and the change in percent."""
    out = []
    for measure, part in table.groupby("measure", sort=False):
        values = part.set_index("year")["real_per_member_2024"]
        first, last = values.get(start), values.get(end)
        out.append({"measure": measure, f"per_member_{start}": first, f"per_member_{end}": last,
                    "change_percent": 100 * (last / first - 1) if first and last is not None else float("nan")})
    return pd.DataFrame(out)


DOCUMENTS_BY_YEAR: dict[int, str] = {
    2018: "S556",
    2019: "S557",
    2020: "S559",
    2021: "S560",
    2022: "S561",
    2023: "S562",
    2025: "S571",
    2026: "S565",
}
"""Budget document used for each year [A17]: the approved details, or for 2020 the revised details.
2024 is absent because the signed 2024 Act [S563] is a scan without a text layer."""

BUDGET_DIR: Path = paths.DATA_INTERIM / "budget"
NYSC_PATTERN = re.compile(r"YOUTH\s+SERVICE\s+CORPS", re.I)


def extract_year(year: int, path: Path, source_id: str) -> tuple[pd.DataFrame, dict[str, object]]:
    """NYSC lines of one budget document with their category, and the check against the printed totals."""
    lines, totals = parse_nysc_block(nysc_block(pdf_page_texts(path, NYSC_PATTERN)))
    lines.insert(0, "year", year)
    lines["category"] = lines["description"].map(classify)
    lines["in_total"] = lines["kind"] != "capital"
    lines["source_id"] = source_id
    check = {"year": year, "source_id": source_id, **check_totals(lines, totals), "allocation_printed": totals.get("allocation")}
    return lines, check


def load_lines(force: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """NYSC lines and total checks for every year with a downloaded document.

    Each year is extracted once and cached in `data/interim/budget/`; `force`
    extracts again. Years whose document is missing are skipped and listed.
    """
    from nysc_safety import download

    files = {doc.source_id: download.PDF_DIR / doc.filename for doc in download.DOCUMENTS}
    BUDGET_DIR.mkdir(parents=True, exist_ok=True)
    all_lines, checks, missing = [], [], []
    for year, source_id in DOCUMENTS_BY_YEAR.items():
        cache = BUDGET_DIR / f"nysc_lines_{year}.csv"
        check_cache = BUDGET_DIR / f"nysc_totals_{year}.csv"
        if cache.exists() and check_cache.exists() and not force:
            lines = pd.read_csv(cache, dtype={"code": str}, keep_default_na=False)
            check = pd.read_csv(check_cache).iloc[0].to_dict()
        else:
            path = files.get(source_id)
            if path is None or not path.exists():
                missing.append(f"{year} ({source_id})")
                continue
            lines, check = extract_year(year, path, source_id)
            lines.to_csv(cache, index=False)
            pd.DataFrame([check]).to_csv(check_cache, index=False)
        all_lines.append(lines)
        checks.append(check)
    if missing:
        print(f"No budget document for: {', '.join(missing)}")
    return pd.concat(all_lines, ignore_index=True), pd.DataFrame(checks)


def corps_members(exposure: pd.DataFrame) -> pd.Series:
    """National number of corps members by year, from the exposure table [A10]."""
    return exposure.groupby("year")["national_total"].first()


def main() -> None:
    """Extract NYSC budget lines, deflate them to 2024 naira and write the H5 tables."""
    lines, checks = load_lines()
    cpi = pd.read_csv(paths.DATA_INTERIM / "cpi_monthly.csv", dtype={"series": str})
    factors = deflators(annual_cpi(cpi))
    members = corps_members(pd.read_csv(paths.DATA_PROCESSED / "exposure_by_state.csv"))
    lines.to_csv(paths.DATA_PROCESSED / "budget_lines.csv", index=False)
    checks.to_csv(BUDGET_DIR / "nysc_totals_check.csv", index=False)
    table = summarise(lines, factors, members)
    print(checks[["year", "source_id", "recurrent_matches", "projects_match"]].to_string(index=False))
    print(table[["year", "security_related_nominal", "security_related_real_2024", "real_per_member_2024"]].round(0).to_string(index=False))


if __name__ == "__main__":
    main()
