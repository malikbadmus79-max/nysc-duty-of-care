"""Tests for nysc_safety.news_search. No network requests are made."""

import pytest

from nysc_safety import news_search


class FakeResponse:
    """Stand-in for a requests response from the WordPress search endpoint."""

    def __init__(self, status: int, items: list[dict], total: int, pages: int) -> None:
        self.status_code = status
        self._items = items
        self.headers = {"X-WP-Total": str(total), "X-WP-TotalPages": str(pages)}

    def json(self) -> list[dict]:
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
