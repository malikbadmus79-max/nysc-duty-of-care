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


def test_general_series_writes_its_own_files(tmp_path, monkeypatch) -> None:
    """The general series searches only the three full-archive outlets and writes separately named files."""
    seen: list[str] = []

    def fake_search(outlet, base_url, queries, session, max_pages, retries):
        seen.append(outlet)
        assert queries == news_search.GENERAL_QUERIES and max_pages == news_search.GENERAL_MAX_PAGES
        assert retries == news_search.GENERAL_RETRIES
        return [news_search._log_row(outlet, "kidnap", 200, 0, 0)], {}

    monkeypatch.setattr(news_search, "search_outlet", fake_search)
    monkeypatch.setattr(news_search.paths, "DATA_INTERIM", tmp_path)
    news_search.main(["--series", "general"])
    assert seen == list(news_search.GENERAL_OUTLETS)
    assert (tmp_path / "general_kidnapping_index.csv").exists()
    assert (tmp_path / "general_kidnapping_search_log.csv").exists()
    assert not (tmp_path / "news_index.csv").exists()


def test_general_queries_use_substring_matching() -> None:
    """The general series uses "kidnap", which the WordPress search also matches inside longer words."""
    assert news_search.GENERAL_QUERIES == ("kidnap", "abducted")


def _counting_search(seen: list[str]):
    """A stand-in for search_outlet that records each outlet searched and returns one article."""

    def fake_search(outlet, base_url, queries, session, max_pages, retries):
        seen.append(outlet)
        article = news_search.Article(outlet, f"{base_url}/x", "2024-01-02", "Gunmen kidnap two", ["kidnapped"])
        return [news_search._log_row(outlet, "kidnapped", 200, 1, 1)], {article.url: article}

    return fake_search


def test_each_outlet_is_saved_when_finished(tmp_path, monkeypatch) -> None:
    """Each outlet's log and index are saved under the parts folder of the series."""
    seen: list[str] = []
    monkeypatch.setattr(news_search, "search_outlet", _counting_search(seen))
    monkeypatch.setattr(news_search.paths, "DATA_INTERIM", tmp_path)
    news_search.main(["--series", "general"])
    parts = tmp_path / "general_kidnapping_parts"
    for outlet in news_search.GENERAL_OUTLETS:
        log_path, index_path = news_search.part_paths(parts, outlet)
        assert log_path.exists() and index_path.exists()
    assert news_search.part_paths(parts, "Premium Times")[0].name == "premium_times_search_log.csv"


def test_rerun_skips_saved_outlets_and_rebuilds_combined_files(tmp_path, monkeypatch) -> None:
    """A rerun searches only outlets without saved results; the combined index still lists all outlets."""
    monkeypatch.setattr(news_search.paths, "DATA_INTERIM", tmp_path)
    parts = tmp_path / "general_kidnapping_parts"
    news_search.save_outlet(
        parts,
        "Premium Times",
        [news_search._log_row("Premium Times", "kidnapped", 200, 1, 1)],
        [{"outlet": "Premium Times", "published": "2020-05-01", "headline": "h", "url": "u", "queries": "kidnapped"}],
    )
    seen: list[str] = []
    monkeypatch.setattr(news_search, "search_outlet", _counting_search(seen))
    news_search.main(["--series", "general"])
    assert seen == ["Daily Trust", "Channels Television"]
    index = (tmp_path / "general_kidnapping_index.csv").read_text(encoding="utf-8").splitlines()
    assert len(index) == 4 and index[1].startswith("Premium Times,2020-05-01")
    log = (tmp_path / "general_kidnapping_search_log.csv").read_text(encoding="utf-8").splitlines()
    assert len(log) == 4


def test_force_searches_saved_outlets_again(tmp_path, monkeypatch) -> None:
    """With --force, outlets with saved results are searched again."""
    monkeypatch.setattr(news_search.paths, "DATA_INTERIM", tmp_path)
    seen: list[str] = []
    monkeypatch.setattr(news_search, "search_outlet", _counting_search(seen))
    news_search.main(["--series", "general"])
    news_search.main(["--series", "general", "--force"])
    assert seen == list(news_search.GENERAL_OUTLETS) * 2


def test_outlet_with_only_an_index_is_not_treated_as_finished(tmp_path) -> None:
    """An outlet whose log was not written (interrupted save) counts as not finished."""
    _, index_path = news_search.part_paths(tmp_path, "Daily Trust")
    news_search.write_csv(index_path, [], news_search.INDEX_FIELDS)
    assert news_search.load_outlet(tmp_path, "Daily Trust") is None


class RateLimitedSession:
    """Answers 429 a set number of times, then answers normally."""

    def __init__(self, refusals: int) -> None:
        self.refusals = refusals
        self.calls = 0

    def get(self, url: str, params: dict, timeout: int) -> FakeResponse:
        self.calls += 1
        if self.calls <= self.refusals:
            return FakeResponse(429, [], 0, 0)
        item = {"date": "2024-07-20T08:00:00", "link": "https://example.org/c", "title": {"rendered": "y"}}
        return FakeResponse(200, [item], 1, 1)


def test_rate_limit_is_retried() -> None:
    """A 429 refusal is retried and the query succeeds once the outlet answers."""
    session = RateLimitedSession(refusals=2)
    log, articles = news_search.search_outlet("Test", "https://example.org", ["corps"], session)
    assert log[0]["http_status"] == 200 and len(articles) == 1 and session.calls == 3


def test_persistent_rate_limit_is_logged_with_its_status() -> None:
    """A refusal that lasts beyond the retry limit is logged with its status code."""
    session = RateLimitedSession(refusals=10_000)
    log, _ = news_search.search_outlet("Test", "https://example.org", ["corps"], session, retries=5)
    assert log[0]["http_status"] == 429 and session.calls == 5


def test_pages_read_before_a_drop_are_kept() -> None:
    """Articles from pages read before a persistent drop are kept, and pages read are logged."""

    class DropAfterFirstPage:
        def __init__(self) -> None:
            self.calls = 0

        def get(self, url: str, params: dict, timeout: int) -> FakeResponse:
            self.calls += 1
            if params["page"] > 1:
                raise requests.ConnectionError("dropped")
            item = {"date": "2024-07-20T08:00:00", "link": "https://example.org/d", "title": {"rendered": "z"}}
            return FakeResponse(200, [item], 300, 3)

    log, articles = news_search.search_outlet("Test", "https://example.org", ["corps"], DropAfterFirstPage())
    assert len(articles) == 1
    assert log[0]["http_status"] == "connection_error" and log[0]["pages_read"] == 1
