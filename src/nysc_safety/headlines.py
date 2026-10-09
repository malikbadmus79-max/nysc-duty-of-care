"""Headline text kept out of committed files.

Headlines of news articles, and titles of Nigeria Watch events, can name
victims and relatives. Under the Nigeria Data Protection Act 2023 and the
privacy rules of the project, such names are not stored in any committed
file. Article indexes are therefore written in two parts: the committed index
(outlet, date, URL and queries) and a local headline file (URL and headline)
in a `headlines/` folder beside it, which is excluded from version control by
`.gitignore`. Code that needs the headlines joins the two on the URL. Nigeria
Watch titles are stored the same way, keyed by event ID.

A few small files keep a headline column because their headlines were
checked by hand and personal names of victims and relatives were removed
(`REVIEWED_FILES`). `committed_text_columns` lists committed CSV files with
a headline or title column so that a test can confirm that no other file has
one.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pandas as pd

from nysc_safety import paths

HEADLINE_FIELDS: tuple[str, ...] = ("url", "headline")
TEXT_COLUMNS: frozenset[str] = frozenset({"headline", "headlines", "title", "titles"})
"""Column names that hold headline or title text."""

REVIEWED_FILES: frozenset[str] = frozenset(
    {
        "data/interim/general_kidnapping_precision_check.csv",
        "data/interim/screening/headline_screening.csv",
    }
)
"""Committed files whose headline or title text was checked by hand for personal names."""


def local_path(index_path: Path) -> Path:
    """Path of the local headline file for an index: `headlines/<index file name>` in the index's folder."""
    return index_path.parent / "headlines" / index_path.name


def write_local(index_path: Path, frame: pd.DataFrame, key: str = "url", text: str = "headline") -> Path:
    """Write the key and text column of each row to the local headline file of an index; return its path."""
    target = local_path(index_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    frame.reindex(columns=[key, text]).fillna("").to_csv(target, index=False)
    return target


def attach(index: pd.DataFrame, index_path: Path) -> pd.DataFrame:
    """Index rows with their headlines from the local headline file; "" where no headline is stored."""
    source = local_path(index_path)
    if not source.exists():
        raise FileNotFoundError(
            f"No local headline file {source}; run the archive search to rebuild it (headlines are not committed)"
        )
    stored = pd.read_csv(source, dtype=str, keep_default_na=False).drop_duplicates("url")
    merged = index.drop(columns=["headline"], errors="ignore").merge(stored, on="url", how="left")
    merged["headline"] = merged["headline"].fillna("")
    return merged


def committed_files(root: Path = paths.ROOT) -> list[str]:
    """Paths of files tracked by git, relative to the repository root, with forward slashes."""
    result = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def committed_text_columns(root: Path = paths.ROOT) -> dict[str, list[str]]:
    """Committed CSV files that have a headline or title column, with those columns."""
    found = {}
    for name in committed_files(root):
        if not name.lower().endswith(".csv"):
            continue
        path = root / name
        if not path.exists():
            continue
        header = pd.read_csv(path, nrows=0).columns
        columns = [c for c in header if c.strip().lower() in TEXT_COLUMNS]
        if columns:
            found[name] = columns
    return found
