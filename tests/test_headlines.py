"""Tests for nysc_safety.headlines, including the check that no committed file carries unreviewed headlines."""

import pandas as pd
import pytest

from nysc_safety import headlines


def test_local_path_is_in_headlines_folder(tmp_path) -> None:
    """The local headline file sits in a `headlines` folder beside the index, under the same name."""
    index_path = tmp_path / "parts" / "x_index.csv"
    assert headlines.local_path(index_path) == tmp_path / "parts" / "headlines" / "x_index.csv"


def test_write_and_attach_round_trip(tmp_path) -> None:
    """URLs and headlines written locally are joined back on the article ID; missing ones become empty."""
    index_path = tmp_path / "index.csv"
    rows = pd.DataFrame({"url": ["a", "b"], "headline": ["First", "Second"], "outlet": ["X", "X"]})
    rows["article_id"] = rows["url"].map(headlines.article_id)
    headlines.write_local(index_path, rows)
    index = pd.DataFrame({"outlet": ["X", "X", "X"], "article_id": [headlines.article_id(u) for u in ["b", "a", "c"]]})
    joined = headlines.attach(index, index_path)
    assert list(joined["headline"]) == ["Second", "First", ""]
    assert list(joined["url"]) == ["b", "a", ""]


def test_article_id_is_stable_and_short() -> None:
    """The ID depends only on the URL."""
    first = headlines.article_id("https://example.org/x")
    assert first == headlines.article_id("https://example.org/x") and first.startswith("A") and len(first) == 13
    assert first != headlines.article_id("https://example.org/y")


def test_attach_without_local_file_explains(tmp_path) -> None:
    """A missing local file raises an error that says headlines are not committed."""
    with pytest.raises(FileNotFoundError, match="not committed"):
        headlines.attach(pd.DataFrame({"article_id": ["A1"]}), tmp_path / "index.csv")


def test_no_committed_csv_has_unreviewed_headline_column() -> None:
    """Only the hand-reviewed files may have a headline or title column among committed CSV files."""
    found = headlines.committed_text_columns()
    unreviewed = sorted(set(found) - headlines.REVIEWED_FILES)
    assert unreviewed == [], f"Committed CSV files with headline or title columns: {unreviewed}"


def test_no_committed_csv_has_url_column_outside_citation_files() -> None:
    """URL columns appear only in files that cite specific articles; the large indexes carry article IDs."""
    found = headlines.committed_url_columns()
    uncited = sorted(set(found) - headlines.CITATION_FILES)
    assert uncited == [], f"Committed CSV files with URL columns: {uncited}"
