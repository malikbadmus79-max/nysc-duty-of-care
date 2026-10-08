"""Nigeria Watch fatal kidnapping events by state (H4 secondary series) [S09, S10].

Run from the repository root with `python -m nysc_safety.nigeria_watch`.

The public event list of Nigeria Watch (`index.php?urlaction=evtList`) is
searched for the text "kidnapped", as in the source log entry for S10. The
Excel export described in the user manual is not offered to visitors who are
not logged in, so the result list is read instead: 500 events per page, with
the event identifier, title, start date, end date and number of deaths. Each
result page is saved unchanged to `data/raw/nigeria_watch/`.

The state of an event is taken from the site's own state field: the same
search is repeated with the state filter set to each state in turn, and every
event listed under a state is assigned to it. An event listed under two
states counts in both. The last part of the title ("Kidnappers Kill 2,
Nasarawa") is kept as `title_state` for checking. Outputs:

- `data/interim/nigeria_watch_kidnapped_events.csv`: one row per event.
- `data/interim/nigeria_watch_state_check.csv`: counts by state from the
  state filter and from titles.
- `data/processed/nigeria_watch_kidnapping_by_state.csv`: events and deaths
  per state, 2010 to 2026, and events per 100,000 population [S551, A12].
"""

from __future__ import annotations

import re
import time
from datetime import date

import pandas as pd
import requests
from bs4 import BeautifulSoup

from nysc_safety import coding, paths
from nysc_safety.news_search import DELAY_SECONDS, USER_AGENT

BASE = "https://www.nigeriawatch.org/index.php"
SEARCH_TEXT = "kidnapped"
PAGE_SIZE = 500
PERIOD: tuple[int, int] = (2010, 2026)
STATE_ALIASES: dict[str, str] = {"FCT (Abuja)": "FCT", "Abuja": "FCT", "Nassarawa": "Nasarawa", "Akwa-Ibom": "Akwa Ibom"}
SELECT_FIELDS: tuple[str, ...] = ("chValues[5]", "chValues[6]", "chValues[7]", "chValues[8]")
"""State, LGA, cause and relation lists. The page gives each two `name` attributes; browsers send the first."""
ID_PATTERN = re.compile(r"^[A-Z]{3}\d{3,}$")
"""Event identifiers, such as IBD035927 or PAR000123."""
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def search_form(html: str) -> dict[str, str]:
    """Default field values of the event search form."""
    form = BeautifulSoup(html, "html.parser").find("form", id="chercheForm")
    if form is None:
        raise ValueError("search form not found")
    data = {i["name"]: i.get("value") or "" for i in form.find_all("input") if i.get("name")}
    for select in form.find_all("select"):
        if select.get("name"):
            first = select.find("option")
            data[select["name"]] = first.get("value") if first else ""
    for field in SELECT_FIELDS:
        data.setdefault(field, "")
    return data


def state_options(html: str) -> dict[str, str]:
    """State names and their option values in the search form's state list."""
    form = BeautifulSoup(html, "html.parser").find("form", id="chercheForm")
    selects = [s for s in form.find_all("select") if any(o.get_text(strip=True) == "Zamfara" for o in s.find_all("option"))]
    if not selects:
        raise ValueError("state list not found")
    return {o.get_text(strip=True): o.get("value") for o in selects[0].find_all("option") if o.get("value")}


def result_count(html: str) -> int:
    """Number of results reported on a result page."""
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    match = re.search(r"(\d[\d,]*)\W*Result\(s\)", text)
    if match is None:
        raise ValueError("result count not found")
    return int(match.group(1).replace(",", ""))


def parse_events(html: str) -> pd.DataFrame:
    """Events on a result page: identifier, title, start date, end date and deaths.

    The list is read as a sequence of text cells: an identifier, then the title
    (which can span more than one cell), two dates and the number of deaths.
    """
    cells = BeautifulSoup(html, "html.parser").get_text("\n", strip=True).split("\n")
    rows = []
    for i, cell in enumerate(cells):
        if not ID_PATTERN.match(cell):
            continue
        j = i + 1
        title_parts = []
        while j < len(cells) and not DATE_PATTERN.match(cells[j]):
            title_parts.append(cells[j])
            j += 1
        if j + 2 >= len(cells) or not DATE_PATTERN.match(cells[j + 1]) or not cells[j + 2].isdigit():
            continue
        rows.append(
            {"event_id": cell, "title": " ".join(title_parts), "start_date": cells[j], "end_date": cells[j + 1],
             "deaths": int(cells[j + 2])}
        )
    return pd.DataFrame(rows, columns=["event_id", "title", "start_date", "end_date", "deaths"])


def title_state(title: str) -> str:
    """State named after the last comma of an event title, or an empty string if it is not a state."""
    if "," not in title:
        return ""
    name = title.rsplit(",", 1)[1].strip()
    name = STATE_ALIASES.get(name, name)
    return name if name in coding.STATES else ""


def by_state(events: pd.DataFrame, population: pd.DataFrame, period: tuple[int, int] = PERIOD) -> pd.DataFrame:
    """Events and deaths per state over the period, with events per 100,000 population in 2022 [A12]."""
    years = pd.to_datetime(events["start_date"]).dt.year
    inside = events[years.between(*period) & (events["state"] != "")]
    grouped = inside.groupby("state")
    # an event listed under two states appears in both rows of `events`
    table = pd.DataFrame(
        {
            "events": grouped.size().reindex(list(coding.STATES), fill_value=0),
            "deaths": grouped["deaths"].sum().reindex(list(coding.STATES), fill_value=0),
        }
    )
    pop = population[(population["year"] == 2022) & population["state"].isin(coding.STATES)].set_index("state")
    table["population_2022"] = pop["population"]
    table["events_per_100k"] = 100_000 * table["events"] / table["population_2022"]
    table.index.name = "state"
    table = table.reset_index()
    table.insert(1, "zone", table["state"].map(coding.zone_of))
    table.insert(2, "period", f"{period[0]}-{period[1]}")
    table["source_ids"] = "S10;S551"
    return table


class Client:
    """A session for the Nigeria Watch event list with a pause between requests."""

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.form_html = self._get(f"{BASE}?urlaction=evtList&cherche=1")

    def _get(self, url: str) -> str:
        time.sleep(DELAY_SECONDS)
        response = self.session.get(url, timeout=120)
        response.raise_for_status()
        return response.text

    def _post(self, url: str, data: dict[str, str]) -> str:
        time.sleep(DELAY_SECONDS)
        response = self.session.post(url, data=data, timeout=180)
        response.raise_for_status()
        return response.text

    def search(self, text: str, state_value: str = "") -> str:
        """Run a search and return the first result page."""
        data = search_form(self.form_html)
        data["chValues[3]"] = text
        data["chValues[5]"] = state_value
        return self._post(f"{BASE}?urlaction=evtList", data)

    def page(self, number: int, size: int = PAGE_SIZE) -> str:
        """A page of the current search's results."""
        data = {"commande": "", "ligne": "", "nbLignes": str(size), "page": str(number), "tri": "", "rang": str(number)}
        return self._post(f"{BASE}?urlaction=evtList&id=&", data)


def main() -> None:
    """Download the "kidnapped" event list, check states against the site's filter, and write the tables."""
    raw = paths.DATA_RAW / "nigeria_watch"
    raw.mkdir(parents=True, exist_ok=True)
    stamp = date.today().isoformat()
    client = Client()
    first = client.search(SEARCH_TEXT)
    total = result_count(first)
    frames, seen, number = [], set(), 1
    while len(seen) < total:
        html = client.page(number)
        frame = parse_events(html)
        new = frame[~frame["event_id"].isin(seen)]
        if new.empty:
            break
        (raw / f"evtlist_{SEARCH_TEXT}_{stamp}_p{number}.html").write_text(html, encoding="utf-8")
        frames.append(new)
        seen.update(new["event_id"])
        number += 1
    events = pd.concat(frames).reset_index(drop=True)
    events["title_state"] = events["title"].map(title_state)
    print(f"{total:,} results reported; {len(events):,} events read")

    options = state_options(client.form_html)
    listed, check = [], []
    for name, value in options.items():
        state = STATE_ALIASES.get(name, name)
        if state not in coding.STATES:
            continue
        count = result_count(client.search(SEARCH_TEXT, value))
        html = client.page(1)
        ids = parse_events(html)["event_id"]
        if len(ids) < count:
            raise RuntimeError(f"{state}: {count} results but {len(ids)} listed")
        (raw / f"evtlist_{SEARCH_TEXT}_{stamp}_state_{value}.html").write_text(html, encoding="utf-8")
        listed.extend((event_id, state) for event_id in ids)
        check.append({"state": state, "filter_count": count, "title_count": int((events["title_state"] == state).sum())})
    states = pd.DataFrame(listed, columns=["event_id", "state"])
    events = events.merge(states, on="event_id", how="left")
    events["state"] = events["state"].fillna("")
    events["source_id"] = "S10"
    events.to_csv(paths.DATA_INTERIM / "nigeria_watch_kidnapped_events.csv", index=False)
    check = pd.DataFrame(check)
    check["source_id"] = "S10"
    check.to_csv(paths.DATA_INTERIM / "nigeria_watch_state_check.csv", index=False)
    agree = events[(events["title_state"] != "")]
    print(f"State filter: {states['event_id'].nunique():,} events, {len(states):,} event-state pairs; "
          f"no state for {int((events['state'] == '').sum())}")
    print(f"Title state agrees with the state field for {(agree['title_state'] == agree['state']).mean():.1%} "
          f"of {len(agree):,} events whose title ends in a state")

    population = pd.read_csv(paths.DATA_INTERIM / "population_by_state.csv")
    table = by_state(events, population)
    table.to_csv(paths.DATA_PROCESSED / "nigeria_watch_kidnapping_by_state.csv", index=False)
    print(f"{int(table['events'].sum()):,} event-state pairs in {PERIOD[0]}-{PERIOD[1]}")


if __name__ == "__main__":
    main()
