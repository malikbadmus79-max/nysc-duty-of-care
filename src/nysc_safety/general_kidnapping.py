"""General kidnapping series by state, from news headlines (H4 main comparison series).

Run from the repository root with `python -m nysc_safety.general_kidnapping`.

Reads the article index of the general archive search
(`data/interim/general_kidnapping_index.csv`, written by
`python -m nysc_safety.news_search --series general` [S555]) and applies four
rule-based steps to the headlines:

1. Screening. A headline is kept when it reports a kidnapping or abduction:
   it uses a verb or participle of kidnapping or abduction ("abduct",
   "kidnapped") or names the act ("abduction of", "kidnap of"). It is dropped,
   with the reason recorded, when it reports a court case or trial, is an
   opinion piece or editorial, or names a place or nationality outside
   Nigeria and no Nigerian state or place (an event abroad).
2. State. The state is taken from a state name in the headline; failing that,
   from a place name in the gazetteer (`nysc_safety.gazetteer` [S553, S554]).
   Where several states are named, the first in the headline is used. The
   state is left empty when no state or place is found [A13].
3. Events. Reports in the same state whose publication dates are within
   `MERGE_DAYS` of the first report of an event, and whose headlines share at
   least `MIN_SHARED_KEYWORDS` keywords, are merged into one event [A14].
4. Rates. Events from 2010 to 2026 are counted by state and divided by the
   state's projected population in 2022 [S551, A12].

Outputs:

- `data/interim/general_kidnapping_screened.csv`: every headline with its
  screening decision, reason, state and event ID.
- `data/processed/general_kidnapping_events.csv`: one row per event.
- `data/processed/general_kidnapping_by_state.csv`: events per state and per
  100,000 population.
- `data/processed/general_kidnapping_by_state_year.csv`: events per state and
  year.
- `data/interim/general_kidnapping_precision_check.csv`: a random sample of
  `PRECISION_SAMPLE` kept headlines for manual checking, written once and
  never overwritten, since the coding columns are filled by hand (see
  `docs/coding_protocol.md`, general kidnapping series).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

import pandas as pd
from scipy import stats

from nysc_safety import coding, gazetteer, paths

PERIOD: tuple[int, int] = (2010, 2026)
MERGE_DAYS = 7
MIN_SHARED_KEYWORDS = 2
PER = 100_000
SOURCE_IDS = "S555;S551;S553;S554"
PRECISION_SAMPLE = 200
PRECISION_SEED = 20261009
PRECISION_PATH = paths.DATA_INTERIM / "general_kidnapping_precision_check.csv"
CHECK_FIELDS = ("is_kidnapping_report", "state_correct", "true_state", "check_note")
"""Columns filled by hand in the precision check."""

EVENT = re.compile(
    r"\b(kidnap|kidnaps|kidnapped|abduct|abducts|abducted|re-abducted|re-kidnapped)\b"
    r"|\b(kidnap|kidnapping|abduction)\s+of\b",
    re.IGNORECASE,
)
"""Wording that reports an act of kidnapping, as opposed to wording about kidnappers or kidnapping in general."""

COURT = re.compile(
    r"\b(court|courts|trial|tribunal|judge|sentence[sd]?|sentencing|convict(s|ed|ion)?|arraign(s|ed|ment)?"
    r"|jail(s|ed)?|imprison(ed|ment)?|prosecut\w*|plead(s|ed)?|remand(s|ed)?|verdict|acquit(s|ted|tal)?"
    r"|bail|testif(y|ies|ied)|death penalty|hang(ed)? for|life imprisonment)\b",
    re.IGNORECASE,
)
"""Court, trial and sentencing follow-ups."""

FOREIGN = re.compile(
    r"\b(Niger Republic|Republic of Niger|Benin Republic|Cameroon\w*|Chad|Chadian|Mali|Malian|Burkina\w*"
    r"|Ghana\w*|Togo|Ivory Coast|Cote d'Ivoire|Senegal|Liberia|Sierra Leone|Guinea|Mozambique|Kenya\w*"
    r"|Somali\w*|Ethiopia\w*|Sudan\w*|Libya\w*|Egypt\w*|Congo\w*|DRC|Uganda\w*|Tanzania\w*|South Africa\w*"
    r"|Haiti\w*|Mexic\w*|Colombia\w*|Venezuela\w*|Ecuador\w*|Brazil\w*|Israel\w*|Gaza|Hamas|Palestin\w*"
    r"|Iraq\w*|Iran\w*|Syria\w*|Yemen\w*|Afghan\w*|Taliban|Pakistan\w*|India|Indian|China|Chinese national"
    r"|Philippine\w*|Ukrain\w*|Russia\w*|Turkey|Syrian|ISIS in|US|U\.S\.|USA|America\w*|Canada|UK|Britain"
    r"|British|London|France|French|Germany|German|Italy|Italian|Spain|Australia\w*)\b"
)
"""Countries, places and groups outside Nigeria, matched with their usual capitalisation."""

OPINION_URL = re.compile(r"/(opinion|opinions|editorial|editorials|columnists?|op-ed|oped|blog)/", re.IGNORECASE)
OPINION_HEADLINE = re.compile(
    r"^\s*(\[?\s*(opinion|editorial|op-ed|column|analysis|interview|letter)\s*\]?\s*[:|\-–]|editorial\b)"
    r"|\b(by\s+[A-Z][a-z]+\s+[A-Z][a-z]+)\s*$|[:|–-]\s*(opinion|editorial)\s*$",
    re.IGNORECASE,
)

STATE_PATTERNS: dict[str, re.Pattern[str]] = {
    state: re.compile(pattern)
    for state, pattern in {
        **{s: rf"\b{s}\b" for s in coding.STATES if s not in {"FCT", "Akwa Ibom", "Cross River", "Nasarawa", "Niger", "Delta"}},
        "FCT": r"\b(FCT|Federal Capital Territory)\b",
        "Akwa Ibom": r"\bAkwa[\s-]?Ibom\b",
        "Cross River": r"\bCross[\s-]?River\b",
        "Nasarawa": r"\bNass?arawa\b",
        "Niger": r"\bNiger\b(?![\s-]+(Delta|Republic|State House))",
        "Delta": r"(?<!Niger )(?<!Niger-)\bDelta\b",
    }.items()
}
"""Patterns for state names; "Niger Delta", "Niger Republic" and "Republic of Niger" are not states."""

STOPWORDS: frozenset[str] = frozenset(
    """a an the and or of in on at to for from by with as after over into near amid during again
    is are was were be been has have had says said say tells told reportedly allegedly suspected
    gunmen gunman bandits bandit kidnappers kidnapper kidnap kidnaps kidnapped kidnapping abduct
    abducts abducted abduction abductors police army troops military state govt government residents
    community village villages others people persons victims victim rescue rescued rescues release
    released releases free freed frees demand demands ransom attack attacks attacked kill kills killed
    news update breaking photos video new two three four five six seven eight nine ten one more many
    nigeria nigerian how why what who""".split()
)
"""Words ignored when comparing headlines for merging: function words and the common vocabulary of kidnapping reports."""


def screen(headline: str, url: str = "", nigerian_place: bool = False) -> tuple[bool, str]:
    """Whether a headline reports a kidnapping in Nigeria, and the reason for the decision.

    A headline naming a place or nationality outside Nigeria is kept only when
    `nigerian_place` is True, that is, when it also names a Nigerian state or place.
    """
    if OPINION_URL.search(url) or OPINION_HEADLINE.search(headline):
        return False, "opinion"
    if COURT.search(headline):
        return False, "court"
    if not EVENT.search(headline):
        return False, "no_kidnapping_event"
    if FOREIGN.search(headline) and not nigerian_place:
        return False, "foreign"
    return True, "kidnapping_report"


def _normalise(text: str) -> str:
    """Text with hyphens and slashes read as spaces and runs of spaces collapsed."""
    return re.sub(r"\s+", " ", re.sub(r"[-/–]", " ", text))


def place_pattern(places: Iterable[str]) -> re.Pattern[str]:
    """One pattern matching any gazetteer name as a whole word, longest names first."""
    names = sorted({_normalise(p) for p in places}, key=len, reverse=True)
    return re.compile(r"\b(" + "|".join(re.escape(n) for n in names) + r")\b")


def assign_state(headline: str, places: pd.DataFrame, pattern: re.Pattern[str] | None = None) -> tuple[str, str]:
    """State named in a headline, and how it was found (`state_name`, `place:<name>` or `none`)."""
    hits = [(m.start(), state) for state, p in STATE_PATTERNS.items() for m in p.finditer(headline)]
    if hits:
        return min(hits)[1], "state_name"
    pattern = pattern or place_pattern(places["place"])
    match = pattern.search(_normalise(headline))
    if match:
        lookup = dict(zip(places["place"].map(_normalise), places["state"]))
        return lookup[match.group(1)], f"place:{match.group(1)}"
    return "", "none"


def keywords(headline: str) -> set[str]:
    """Distinctive words of a headline: numbers and words of four or more letters outside `STOPWORDS`."""
    words = re.findall(r"[a-z0-9']+", headline.lower().replace("’", "'"))
    words = [w.removesuffix("'s") for w in words]
    states = {s.lower() for s in coding.STATES}
    return {w for w in words if (w.isdigit() or len(w) >= 4) and w not in STOPWORDS and w not in states}


def merge_events(reports: pd.DataFrame, days: int = MERGE_DAYS, min_shared: int = MIN_SHARED_KEYWORDS) -> pd.Series:
    """Event number for each report.

    Reports are taken in order of publication date. A report joins the
    earliest open event in the same state whose first report is at most
    `days` days earlier and with any report of which it shares at least
    `min_shared` keywords; otherwise it starts a new event. Reports with no
    state are merged among themselves by the same rule.
    """
    order = reports.assign(_date=pd.to_datetime(reports["published"])).sort_values(["_date", "url"])
    events: list[dict] = []
    event_of: dict[object, int] = {}
    for index, row in order.iterrows():
        words = keywords(row["headline"])
        chosen = None
        for number in range(len(events) - 1, -1, -1):
            event = events[number]
            if (row["_date"] - event["first"]).days > days:
                break
            if event["state"] == row["state"] and any(len(words & w) >= min_shared for w in event["words"]):
                chosen = number
        if chosen is None:
            events.append({"state": row["state"], "first": row["_date"], "words": [words]})
            chosen = len(events) - 1
        else:
            events[chosen]["words"].append(words)
        event_of[index] = chosen + 1
    return pd.Series(event_of).reindex(reports.index)


def event_table(reports: pd.DataFrame) -> pd.DataFrame:
    """One row per event: first report date, state, number of reports and outlets, first headline and URLs."""
    kept = reports.sort_values(["published", "url"])
    grouped = kept.groupby("event_number", sort=True)
    table = pd.DataFrame(
        {
            "first_report": grouped["published"].min(),
            "last_report": grouped["published"].max(),
            "state": grouped["state"].first(),
            "n_reports": grouped.size(),
            "outlets": grouped["outlet"].agg(lambda o: ";".join(sorted(set(o)))),
            "headline": grouped["headline"].first(),
            "urls": grouped["url"].agg(";".join),
        }
    ).reset_index(drop=True)
    table.insert(0, "event_id", [f"GK{n:05d}" for n in range(1, len(table) + 1)])
    table["year"] = pd.to_datetime(table["first_report"]).dt.year
    table["source_id"] = "S555"
    return table


def by_state(events: pd.DataFrame, population: pd.DataFrame, period: tuple[int, int] = PERIOD) -> pd.DataFrame:
    """Events per state over the period, and per 100,000 population (2022 and mean 2010-2022) [A12]."""
    inside = events[events["year"].between(*period) & (events["state"] != "")]
    counts = inside.groupby("state").size().reindex(list(coding.STATES), fill_value=0)
    pop = population[population["state"].isin(coding.STATES)]
    pop_2022 = pop[pop["year"] == 2022].set_index("state")["population"]
    pop_mean = pop[pop["year"].between(2010, 2022)].groupby("state")["population"].mean().round()
    table = pd.DataFrame({"events": counts, "population_2022": pop_2022, "population_mean_2010_2022": pop_mean})
    table["events_per_100k"] = PER * table["events"] / table["population_2022"]
    table["events_per_100k_mean_pop"] = PER * table["events"] / table["population_mean_2010_2022"]
    table.index.name = "state"
    table = table.reset_index()
    table.insert(1, "zone", table["state"].map(coding.zone_of))
    table.insert(2, "period", f"{period[0]}-{period[1]}")
    table["source_ids"] = SOURCE_IDS
    return table


def by_state_year(events: pd.DataFrame, period: tuple[int, int] = PERIOD) -> pd.DataFrame:
    """Events per state and year over the period, with zeros for state-years with no event."""
    inside = events[events["year"].between(*period) & (events["state"] != "")]
    grid = pd.MultiIndex.from_product([coding.STATES, range(period[0], period[1] + 1)], names=["state", "year"])
    table = inside.groupby(["state", "year"]).size().reindex(grid, fill_value=0).rename("events").reset_index()
    table["source_ids"] = "S555"
    return table


def screen_index(index: pd.DataFrame, places: pd.DataFrame) -> pd.DataFrame:
    """Screen every headline, assign states to kept ones and number the events."""
    frame = index.copy()
    frame["headline"] = frame["headline"].fillna("").astype(str)
    pattern = place_pattern(places["place"])
    assigned = [assign_state(h, places, pattern) for h in frame["headline"]]
    decisions = [
        screen(h, u, bool(a[0])) for h, u, a in zip(frame["headline"], frame["url"].fillna(""), assigned)
    ]
    frame["keep"] = [d[0] for d in decisions]
    frame["reason"] = [d[1] for d in decisions]
    frame["state"] = [a[0] if k else "" for a, k in zip(assigned, frame["keep"])]
    frame["state_basis"] = [a[1] if k else "" for a, k in zip(assigned, frame["keep"])]
    kept = frame[frame["keep"]]
    frame["event_number"] = merge_events(kept).astype("Int64")
    return frame


def precision_sample(screened: pd.DataFrame, n: int = PRECISION_SAMPLE, seed: int = PRECISION_SEED) -> pd.DataFrame:
    """Simple random sample of kept headlines, with empty columns for the manual check."""
    kept = screened[screened["keep"]]
    sample = kept.sample(n=min(n, len(kept)), random_state=seed).sort_values(["published", "url"])
    columns = ["outlet", "published", "headline", "url", "state", "state_basis", "event_id"]
    table = sample[columns].reset_index(drop=True)
    table.insert(0, "check_id", [f"PC{n:03d}" for n in range(1, len(table) + 1)])
    for field in CHECK_FIELDS:
        table[field] = ""
    table["source_id"] = "S555"
    return table


def proportion(successes: int, trials: int) -> dict[str, float]:
    """Proportion with a Wilson 95% interval."""
    if trials == 0:
        return {"successes": 0, "trials": 0, "proportion": float("nan"), "ci_low": float("nan"), "ci_high": float("nan")}
    ci = stats.binomtest(successes, trials).proportion_ci(confidence_level=0.95, method="wilson")
    return {"successes": successes, "trials": trials, "proportion": successes / trials, "ci_low": ci.low, "ci_high": ci.high}


def precision_summary(check: pd.DataFrame) -> pd.DataFrame:
    """Precision of screening and of state assignment from the coded check sample.

    `is_kidnapping_report` and `state_correct` hold "yes" or "no"; `state_correct`
    is coded only for headlines with an assigned state. A headline with no
    assigned state but a state identifiable from the headline is recorded in
    `true_state`.
    """
    yes = lambda column, rows: int((rows[column].str.strip().str.lower() == "yes").sum())
    reports = check[check["is_kidnapping_report"].str.strip().str.lower().isin(["yes", "no"])]
    true_reports = reports[reports["is_kidnapping_report"].str.strip().str.lower() == "yes"]
    with_state = true_reports[true_reports["state"].fillna("") != ""]
    without_state = true_reports[true_reports["state"].fillna("") == ""]
    rows = {
        "screening: headline reports a kidnapping in Nigeria": proportion(yes("is_kidnapping_report", reports), len(reports)),
        "state: assigned state is correct (true reports with a state)": proportion(
            yes("state_correct", with_state), len(with_state)
        ),
        "state: state identifiable but not assigned (true reports without a state)": proportion(
            int((without_state["true_state"].fillna("").str.strip() != "").sum()), len(without_state)
        ),
    }
    return pd.DataFrame(rows).T.rename_axis("measure").reset_index()


def write_precision_sample(screened: pd.DataFrame, path: Path = PRECISION_PATH) -> bool:
    """Write the check sample unless it already exists; return True if written."""
    if path.exists():
        return False
    precision_sample(screened).to_csv(path, index=False)
    return True


def main() -> None:
    """Build the screened headline file and the general kidnapping tables."""
    index = pd.read_csv(paths.DATA_INTERIM / "general_kidnapping_index.csv", dtype=str)
    places = gazetteer.load()
    population = pd.read_csv(paths.DATA_INTERIM / "population_by_state.csv")
    screened = screen_index(index, places)
    kept = screened[screened["keep"]].copy()
    events = event_table(kept)
    numbers = dict(zip(range(1, len(events) + 1), events["event_id"]))
    screened["event_id"] = screened["event_number"].map(numbers)
    screened.drop(columns="event_number").to_csv(paths.DATA_INTERIM / "general_kidnapping_screened.csv", index=False)
    events.to_csv(paths.DATA_PROCESSED / "general_kidnapping_events.csv", index=False)
    states = by_state(events, population)
    states.to_csv(paths.DATA_PROCESSED / "general_kidnapping_by_state.csv", index=False)
    by_state_year(events).to_csv(paths.DATA_PROCESSED / "general_kidnapping_by_state_year.csv", index=False)
    if write_precision_sample(screened):
        print(f"Precision check sample written to {PRECISION_PATH.relative_to(paths.ROOT)}")
    print(f"{len(screened):,} headlines; kept {len(kept):,}")
    print(screened["reason"].value_counts().to_string())
    print(f"State found for {(kept['state'] != '').mean():.1%} of kept headlines")
    print(f"{len(events):,} events; {int(states['events'].sum()):,} with a state in {PERIOD[0]}-{PERIOD[1]}")


if __name__ == "__main__":
    main()
