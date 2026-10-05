"""Tests for nysc_safety.news_search. No network requests are made."""

import pytest
import requests

from nysc_safety import news_search


class FakeResponse:
    """Stand-in for a requests response from the WordPress search endpoint."""

    def __init__(self, status: int, items: list[dict] | None, total: int, pages: int) -> None:
        self.status_code = status
        self._items = items
        self.headers = {"X-WP-Total": str(total), "X-WP-TotalPages": str(pages)}

    def json(self) -> list[dict]:
        if self._items is None:
            raise ValueError("not JSON")
        return self._items


class FakeSession:
    """Returns two pages for the first query and a refusal for the second."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def get(self, url: str, params: dict, timeout: int) -> FakeResponse:
        self.calls.append(params)
        if params["search"] == "blocked":
            return FakeResponse(403, [], 0, 0)
        item = {
            "date": "2023-08-21T10:00:00",
            "link": f"https://example.org/a{params['page']}",
            "title": {"rendered": "Gunmen abduct eight NYSC members &#8211; Police"},
        }
        return FakeResponse(200, [item], 2, 2)


@pytest.fixture(autouse=True)
def no_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip the pause between requests."""
    monkeypatch.setattr(news_search.time, "sleep", lambda seconds: None)


def test_search_reads_all_pages_and_logs_refusals() -> None:
    """All result pages are read; refused queries are logged with their status."""
    session = FakeSession()
    log, articles = news_search.search_outlet("Test", "https://example.org", ["corps", "blocked"], session)
    assert len(articles) == 2
    first = log[0]
    assert first["results_reported"] == 2 and first["pages_read"] == 2 and first["http_status"] == 200
    assert log[1]["http_status"] == 403


def test_headlines_are_unescaped_and_dated() -> None:
    """HTML entities in headlines are decoded and dates keep the day only."""
    _, articles = news_search.search_outlet("Test", "https://example.org", ["corps"], FakeSession())
    article = articles["https://example.org/a1"]
    assert article.headline == "Gunmen abduct eight NYSC members – Police"
    assert article.published == "2023-08-21"
    assert article.queries == ["corps"]


class DroppingSession:
    """Drops the connection a set number of times, then answers normally."""

    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    def get(self, url: str, params: dict, timeout: int) -> FakeResponse:
        self.calls += 1
        if self.calls <= self.failures:
            raise requests.ConnectionError("Remote end closed connection without response")
        item = {"date": "2024-07-20T08:00:00", "link": "https://example.org/b", "title": {"rendered": "x"}}
        return FakeResponse(200, [item], 1, 1)


def test_dropped_connection_is_retried() -> None:
    """A connection dropped fewer times than the retry limit is retried and succeeds."""
    session = DroppingSession(failures=news_search.RETRIES - 1)
    log, articles = news_search.search_outlet("Test", "https://example.org", ["corps"], session)
    assert log[0]["http_status"] == 200 and len(articles) == 1


def test_persistent_drops_are_logged_and_outlet_skipped() -> None:
    """Persistent drops are logged as connection errors; later queries are skipped without requests."""
    session = DroppingSession(failures=10_000)
    queries = ["q1", "q2", "q3", "q4", "q5"]
    log, articles = news_search.search_outlet("Test", "https://example.org", queries, session)
    assert articles == {}
    statuses = [row["http_status"] for row in log]
    assert statuses == ["connection_error"] * 3 + ["skipped"] * 2
    assert session.calls == news_search.RETRIES * news_search.MAX_FAILED_QUERIES


def test_non_json_page_is_logged_as_blocked() -> None:
    """A 200 response that is not JSON, such as a bot-check page, is logged as blocked."""

    class CheckPageSession:
        def get(self, url: str, params: dict, timeout: int) -> FakeResponse:
            return FakeResponse(200, None, 0, 0)

    log, articles = news_search.search_outlet("Test", "https://example.org", ["corps"], CheckPageSession())
    assert log[0]["http_status"] == "blocked" and articles == {}


def test_empty_index_is_written_with_header(tmp_path) -> None:
    """An index with no articles is still written, with its header row."""
    path = tmp_path / "index.csv"
    news_search.write_csv(path, [], news_search.INDEX_FIELDS)
    assert path.read_text(encoding="utf-8").strip() == "outlet,published,headline,url,queries"
