"""Tests for nysc_safety.sources and for source references in repository data files."""

import pandas as pd
import pytest

from nysc_safety import paths, scorecard, sources


def test_source_log_ids_are_sequential() -> None:
    """The source log has IDs S01 to Sn with no gaps."""
    ids = sorted(sources.logged_ids(), key=lambda s: int(s[1:]))
    assert ids == [f"S{i:02d}" for i in range(1, len(ids) + 1)]


def test_referenced_ids_parses_lists() -> None:
    """IDs are read from ;-separated lists and empty cells are ignored."""
    frame = pd.DataFrame({"source_ids": ["S01;S02", None, "S02"]})
    assert sources.referenced_ids(frame) == {"S01", "S02"}


@pytest.mark.parametrize(
    "csv_path",
    sorted(p for folder in (paths.DATA_INTERIM, paths.DATA_PROCESSED) for p in folder.glob("*.csv")),
    ids=lambda p: p.name,
)
def test_data_files_cite_logged_sources(csv_path) -> None:
    """Every source ID cited in an interim or processed CSV has a row in docs/sources.md."""
    frame = pd.read_csv(csv_path)
    if "source_ids" in frame.columns:
        assert sources.missing_ids(frame) == set()


def test_policy_evidence_criteria_are_known() -> None:
    """Evidence rows refer only to scorecard criteria D1 to D12."""
    frame = pd.read_csv(paths.DATA_INTERIM / "policy_evidence.csv")
    assert set(frame["criterion_id"]) <= set(scorecard.CRITERIA)
    assert frame["evidence_id"].is_unique
