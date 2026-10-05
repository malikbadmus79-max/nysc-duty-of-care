"""Keyword searches of outlet archives through the WordPress REST API.

Run from the repository root with `python -m nysc_safety.news_search`.
Each query is sent to each outlet's `/wp-json/wp/v2/posts` endpoint, all
result pages are read, and two files are written:

- `data/interim/news_search_log.csv`: one row per outlet and query, with the
  number of results reported by the outlet and the date of the search.
- `data/interim/news_index.csv`: one row per article URL found, with date,
  headline, outlet and the queries that returned it.

Outlets whose archive API refuses automated requests are recorded in the log
with the HTTP status and are searched by other means (see
`docs/analysis_plan.md`, section 4).
"""

from __future__ import annotations

import csv
import html
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import requests

from nysc_safety import paths

USER_AGENT = "nysc-duty-of-care research project (github.com/malikbadmus79-max)"
DELAY_SECONDS = 2.0
PER_PAGE = 100
MAX_PAGES = 20

OUTLETS: dict[str, str] = {
    "Premium Times": "https://www.premiumtimesng.com",
    "Daily Trust": "https://dailytrust.com",
    "Channels Television": "https://www.channelstv.com",
    "Punch": "https://punchng.com",
    "Vanguard": "https://www.vanguardngr.com",
    "The Guardian (Nigeria)": "https://guardian.ng",
    "The Cable": "https://www.thecable.ng",
}
"""Outlets with WordPress archives. Sahara Reporters does not run WordPress."""

QUERIES: tuple[str, ...] = (
    "corps members kidnapped",
    "corps member kidnapped",
    "corps members abducted",
    "corps member abducted",
    "NYSC members kidnapped",
    "NYSC member abducted",
    "corper kidnapped",
    "corps member killed",
    "corps members killed",
    "NYSC member killed",
    "corper killed",
    "corps member shot",
    "corps member raped",
    "corps members attacked",
    "corps members robbed",
    "corps members accident",
    "corps member murdered",
)
"""Search phrases, combining the terms in `docs/analysis_plan.md`, section 4."""


@dataclass
class Article:
    """One article found by one or more queries."""

    outlet: str
    url: str
    published: str
    headline: str
    queries: list[str] = field(default_factory=list)


def search_outlet(
    outlet: str, base_url: str, queries: Iterable[str], session: requests.Session
) -> tuple[list[dict[str, object]], dict[str, Article]]:
    """Run every query against one outlet; return log rows and articles keyed by URL."""
    log: list[dict[str, object]] = []
    articles: dict[str, Article] = {}
    for query in queries:
        page, pages, total, status = 1, 1, None, None
        while page <= min(pages, MAX_PAGES):
            response = session.get(
                f"{base_url}/wp-json/wp/v2/posts",
                params={"search": query, "per_page": PER_PAGE, "page": page, "_fields": "date,link,title"},
                timeout=60,
            )
            status = response.status_code
            if status != 200:
                break
            total = int(response.headers.get("X-WP-Total", 0))
            pages = int(response.headers.get("X-WP-TotalPages", 1))
            for item in response.json():
                url = item["link"]
                article = articles.setdefault(
                    url,
                    Article(outlet, url, item["date"][:10], html.unescape(item["title"]["rendered"])),
                )
                article.queries.append(query)
            page += 1
            time.sleep(DELAY_SECONDS)
        log.append(
            {
                "outlet": outlet,
                "query": query,
                "method": "WordPress REST API search",
                "http_status": status,
                "results_reported": total,
                "pages_read": page - 1,
                "searched_on": date.today().isoformat(),
            }
        )
    return log, articles


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    """Write rows to a CSV file with the keys of the first row as header."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """Search every outlet and write the search log and article index."""
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    log_rows: list[dict[str, object]] = []
    index_rows: list[dict[str, object]] = []
    for outlet, base_url in OUTLETS.items():
        log, articles = search_outlet(outlet, base_url, QUERIES, session)
        log_rows.extend(log)
        for article in articles.values():
            index_rows.append(
                {
                    "outlet": article.outlet,
                    "published": article.published,
                    "headline": article.headline,
                    "url": article.url,
                    "queries": ";".join(article.queries),
                }
            )
        print(f"{outlet}: {len(articles):,} articles")
    write_csv(paths.DATA_INTERIM / "news_search_log.csv", log_rows)
    write_csv(paths.DATA_INTERIM / "news_index.csv", index_rows)


if __name__ == "__main__":
    main()
