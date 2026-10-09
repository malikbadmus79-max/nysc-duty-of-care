"""Headlines and URLs of article indexes kept out of committed files.

Headlines of news articles, the URLs of articles (whose slugs often repeat
the headline), and titles of Nigeria Watch events can name victims and
relatives. Under the Nigeria Data Protection Act 2023 and the privacy rules
of the project, such names are not stored in any committed file.

The large article indexes, which list every article returned by the archive
searches whether or not it is cited, are therefore written in two parts: the
committed index (outlet, date, article ID and queries) and a local file
(article ID, URL and headline) in a `headlines/` folder beside it, which is
excluded from version control by `.gitignore`. The article ID is derived from
the URL (`article_id`), so it is stable across searches. Code that needs the
URL or headline joins the two on the article ID. Nigeria Watch titles are
stored locally in the same way, keyed by event ID.

URLs of published articles that are cited as evidence are kept as citations:
in the source log, the incident register, the screening files and the
precision check (`CITATION_FILES`). A few of these files also keep a headline
column, checked by hand for personal names (`REVIEWED_FILES`).
`committed_text_columns` and `committed_url_columns` list committed CSV files
with headline or URL columns so that tests can confirm that no other file has
them.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pandas as pd

from nysc_safety import paths

LOCAL_FIELDS: tuple[str, ...] = ("article_id", "url", "headline")
TEXT_COLUMNS: frozenset[str] = frozenset({"headline", "headlines", "title", "titles"})
"""Column names that hold headline or title text."""
URL_COLUMNS: frozenset[str] = frozenset({"url", "urls"})
"""Column names that hold article URLs."""

REVIEWED_FILES: frozenset[str] = frozenset(
    {
        "data/interim/general_kidnapping_precision_check.csv",
        "data/interim/screening/headline_screening.csv",
    }
)
"""Committed files whose headline or title text was checked by hand for personal names."""

CITATION_FILES: frozenset[str] = frozenset(
    {
        "data/interim/general_kidnapping_precision_check.csv",
        "data/interim/screening/headline_screening.csv",
    }
)
"""Committed CSV files with a URL column whose URLs cite specific articles as evidence."""


def article_id(url: str) -> str:
    """Stable identifier of an article: "A" and the first 12 hexadecimal digits of the SHA-256 hash of its URL."""
    return "A" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]


def local_path(index_path: Path) -> Path:
    """Path of the local file for an index: `headlines/<index file name>` in the index's folder."""
    return index_path.parent / "headlines" / index_path.name


def write_local(index_path: Path, frame: pd.DataFrame, key: str = "article_id", text: str = "headline") -> Path:
    """Write the key, URL (when present) and text column of each row to the local file of an index."""
    target = local_path(index_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    columns = [key, "url", text] if "url" in frame.columns and key != "url" else [key, text]
    frame.reindex(columns=columns).fillna("").to_csv(target, index=False)
    return target


def attach(index: pd.DataFrame, index_path: Path) -> pd.DataFrame:
    """Index rows with their URL and headline from the local file; "" where none is stored."""
    source = local_path(index_path)
    if not source.exists():
        raise FileNotFoundError(
            f"No local headline file {source}; run the archive search to rebuild it (URLs and headlines are not committed)"
        )
    stored = pd.read_csv(source, dtype=str, keep_default_na=False).drop_duplicates("article_id")
    merged = index.drop(columns=["headline", "url"], errors="ignore").merge(stored, on="article_id", how="left")
    for column in ("url", "headline"):
        merged[column] = merged[column].fillna("")
    return merged


def committed_files(root: Path = paths.ROOT) -> list[str]:
    """Paths of files tracked by git, relative to the repository root, with forward slashes."""
    result = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _committed_columns(names: frozenset[str], root: Path) -> dict[str, list[str]]:
    """Committed CSV files with a column whose name is in `names`, with those columns."""
    found = {}
    for name in committed_files(root):
        if not name.lower().endswith(".csv"):
            continue
        path = root / name
        if not path.exists():
            continue
        header = pd.read_csv(path, nrows=0).columns
        columns = [c for c in header if c.strip().lower() in names]
        if columns:
            found[name] = columns
    return found


def committed_text_columns(root: Path = paths.ROOT) -> dict[str, list[str]]:
    """Committed CSV files that have a headline or title column, with those columns."""
    return _committed_columns(TEXT_COLUMNS, root)


def committed_url_columns(root: Path = paths.ROOT) -> dict[str, list[str]]:
    """Committed CSV files that have a URL column, with those columns."""
    return _committed_columns(URL_COLUMNS, root)
