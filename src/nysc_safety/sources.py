"""Reading the source log and checking source ID references."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from nysc_safety import paths

SOURCE_ID = re.compile(r"\bS\d{2,3}\b")


def logged_ids(sources_md: Path = paths.DOCS / "sources.md") -> set[str]:
    """Source IDs that have a row in the source log table."""
    ids = set()
    for line in sources_md.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\|\s*(S\d{2,3})\s*\|", line)
        if match:
            ids.add(match.group(1))
    return ids


def referenced_ids(frame: pd.DataFrame, column: str = "source_ids") -> set[str]:
    """Source IDs referenced in a ;-separated column of a data frame."""
    ids: set[str] = set()
    for value in frame[column].dropna().astype(str):
        ids.update(SOURCE_ID.findall(value))
    return ids


def missing_ids(frame: pd.DataFrame, column: str = "source_ids") -> set[str]:
    """Referenced source IDs that have no row in the source log."""
    return referenced_ids(frame, column) - logged_ids()
