"""Tests for nysc_safety.general_kidnapping and nysc_safety.gazetteer."""

import pandas as pd
import pytest

from nysc_safety import coding, gazetteer
from nysc_safety import general_kidnapping as gk

PLACES = pd.DataFrame(
    {
        "place": ["Birnin Gwari", "Kajuru", "Ado Ekiti", "Abuja", "Port Harcourt", "Kuje"],
        "state": ["Kaduna", "Kaduna", "Ekiti", "FCT", "Rivers", "FCT"],
    }
)


@pytest.mark.parametrize(
    "headline",
    [
        "Gunmen abduct 20 worshippers in Kaduna church",
        "Bandits kidnap traditional ruler in Zamfara",
        "Three students kidnapped in Ekiti",
        "Police confirm abduction of pastor in Ondo",
        "Kidnappers abducted 10 passengers on Abuja-Kaduna highway",
    ],
)
def test_kidnapping_reports_are_kept(headline: str) -> None:
    """Headlines that report an act of kidnapping are kept."""
    assert gk.screen(headline) == (True, "kidnapping_report")


@pytest.mark.parametrize(
    ("headline", "url", "reason"),
    [
        ("Court sentences three kidnappers to death in Ondo", "", "court"),
        ("Man jailed 20 years for kidnapping of pupil in Kaduna", "", "court"),
        ("Kidnappers of Ekiti pupils arraigned", "", "court"),
        ("Police arrest suspected kidnappers in Delta", "", "no_kidnapping_event"),
        ("Senate passes anti-kidnapping bill", "", "no_kidnapping_event"),
        ("Gunmen kidnap aid workers in Mali", "", "foreign"),
        ("Haitian gangs kidnap missionaries", "", "foreign"),
        ("The rising tide of abducted children in the North", "https://www.premiumtimesng.com/opinion/123-x.html", "opinion"),
        ("EDITORIAL: Pupils abducted again", "", "opinion"),
    ],
)
def test_exclusions_carry_their_reason(headline: str, url: str, reason: str) -> None:
    """Court follow-ups, non-events, foreign events and opinion pieces are dropped with their reason."""
    assert gk.screen(headline, url) == (False, reason)


def test_foreign_nationals_kidnapped_in_nigeria_are_kept() -> None:
    """A headline naming a foreign nationality is kept when it also names a Nigerian place."""
    headline = "Chinese nationals abducted in Ogun quarry"
    state, _ = gk.assign_state(headline, PLACES)
    assert state == "Ogun"
    assert gk.screen(headline, nigerian_place=True) == (True, "kidnapping_report")


@pytest.mark.parametrize(
    ("headline", "state", "basis"),
    [
        ("Bandits abduct 30 in Birnin Gwari", "Kaduna", "place:Birnin Gwari"),
        ("Gunmen kidnap lecturer in Ado-Ekiti", "Ekiti", "state_name"),
        ("Kidnappers strike in Kuje, abduct four", "FCT", "place:Kuje"),
        ("Gunmen abduct oil workers in Niger Delta creeks", "", "none"),
        ("Gunmen kidnap farmers in Niger community", "Niger", "state_name"),
        ("Gunmen abduct 5 in Akwa-Ibom", "Akwa Ibom", "state_name"),
        ("Gunmen abduct 5 on Abuja-Kaduna road", "Kaduna", "state_name"),
        ("Gunmen abduct housewife", "", "none"),
        ("Gunmen kidnap Nasarawa monarch", "Nasarawa", "state_name"),
    ],
)
def test_state_assignment(headline: str, state: str, basis: str) -> None:
    """State names come first; gazetteer places are used otherwise; Niger Delta is not Niger or Delta."""
    assert gk.assign_state(headline, PLACES) == (state, basis)


def _reports(rows: list[tuple[str, str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"published": d, "state": s, "headline": h, "url": f"u{i}", "outlet": "Premium Times"}
            for i, (d, s, h) in enumerate(rows)
        ]
    )


def test_reports_of_one_event_are_merged() -> None:
    """Same state, within 7 days and two shared keywords: one event."""
    reports = _reports(
        [
            ("2021-03-01", "Kaduna", "Bandits abduct 39 students of forestry college in Kaduna"),
            ("2021-03-04", "Kaduna", "Afaka forestry college: 39 students still held"),
            ("2021-03-03", "Zamfara", "Gunmen kidnap 39 forestry students in Zamfara"),
        ]
    )
    events = gk.merge_events(reports)
    assert events[0] == events[1] and events[2] != events[0]


def test_reports_far_apart_or_unrelated_stay_separate() -> None:
    """Reports more than 7 days apart, or with fewer than two shared keywords, are separate events."""
    reports = _reports(
        [
            ("2021-03-01", "Kaduna", "Bandits abduct 39 students of forestry college"),
            ("2021-03-20", "Kaduna", "Bandits abduct 39 students of forestry college"),
            ("2021-03-02", "Kaduna", "Gunmen kidnap pastor in Kajuru church"),
        ]
    )
    events = gk.merge_events(reports)
    assert len(set(events)) == 3


def test_keywords_ignore_common_vocabulary_and_state_names() -> None:
    """Keywords leave out function words, kidnapping vocabulary and state names."""
    assert gk.keywords("Gunmen abduct 39 students of Kaduna forestry college") == {"39", "students", "forestry", "college"}


def test_by_state_counts_and_rates() -> None:
    """Events in the period are counted per state; rates use the 2022 population."""
    events = pd.DataFrame(
        {"state": ["Kaduna", "Kaduna", "Lagos", "", "Kaduna"], "year": [2015, 2020, 2021, 2021, 2009]}
    )
    population = pd.DataFrame(
        [(s, y, 1_000_000) for s in coding.STATES for y in range(2007, 2023)], columns=["state", "year", "population"]
    )
    table = gk.by_state(events, population).set_index("state")
    assert len(table) == 37
    assert table.loc["Kaduna", "events"] == 2 and table.loc["Abia", "events"] == 0
    assert table.loc["Kaduna", "events_per_100k"] == pytest.approx(0.2)
    assert table.loc["Kaduna", "zone"] == "North West"


def test_event_table_and_screen_index_link_reports_to_events() -> None:
    """Each kept headline gets an event; dropped headlines get none."""
    index = pd.DataFrame(
        {
            "outlet": ["Daily Trust", "Channels Television", "Daily Trust"],
            "published": ["2022-06-05", "2022-06-06", "2022-06-07"],
            "headline": [
                "Gunmen abduct 12 worshippers at Kajuru church",
                "Kajuru church attack: 12 worshippers abducted",
                "Court remands kidnappers",
            ],
            "url": ["a", "b", "c"],
        }
    )
    screened = gk.screen_index(index, PLACES)
    assert list(screened["keep"]) == [True, True, False]
    assert screened["event_number"].iloc[0] == screened["event_number"].iloc[1]
    assert pd.isna(screened["event_number"].iloc[2])
    events = gk.event_table(screened[screened["keep"]])
    assert len(events) == 1 and events.loc[0, "n_reports"] == 2 and events.loc[0, "state"] == "Kaduna"
    assert events.loc[0, "outlets"] == "Channels Television;Daily Trust"


LGA_TEXT = """===[[Abia State]]===
* [[Aba North]]
* [[Bende, Nigeria|Bende]]
===[[Kogi State]]===
* [[Bassa, Kogi|Bassa]]
* [[Kabba/Bunu]]
===[[Plateau State]]===
* [[Bassa, Plateau|Bassa]]
* [[Jos North]]
===[[Federal Capital Territory, Nigeria]]===
* [[Kuje]]
"""

CITY_TEXT = """{| class="wikitable"
|-
| 1
| [[Jos]]
| [[Plateau State|Plateau]]
|-
| 2
| [[Garki]]
| [[Jigawa State|Jigawa]]
|}"""


def test_gazetteer_variants_ambiguity_and_stoplist() -> None:
    """Compass points and "/" are split off; names in two states and stoplisted names are dropped."""
    places = gazetteer.build(gazetteer.parse_lgas(LGA_TEXT), gazetteer.parse_cities(CITY_TEXT))
    lookup = dict(zip(places["place"], places["state"]))
    assert lookup["Aba"] == "Abia" and lookup["Aba North"] == "Abia"
    assert lookup["Kabba"] == "Kogi" and lookup["Bunu"] == "Kogi"
    assert lookup["Kuje"] == "FCT" and lookup["Jos"] == "Plateau"
    assert "Bassa" not in lookup and "Garki" not in lookup
    assert places.set_index("place").loc["Jos", "source_ids"] == "S553;S554"


def test_precision_sample_is_seeded_and_from_kept_headlines() -> None:
    """The sample is drawn only from kept headlines, is reproducible and has empty check columns."""
    screened = pd.DataFrame(
        {
            "outlet": ["A"] * 10,
            "published": [f"2020-01-{d:02d}" for d in range(1, 11)],
            "headline": [f"h{d}" for d in range(10)],
            "url": [f"u{d}" for d in range(10)],
            "state": ["Kaduna"] * 10,
            "state_basis": ["state_name"] * 10,
            "event_id": [f"GK{d:05d}" for d in range(10)],
            "keep": [True, False] * 5,
        }
    )
    first = gk.precision_sample(screened, n=3, seed=1)
    assert first.equals(gk.precision_sample(screened, n=3, seed=1))
    assert set(first["url"]) <= {"u0", "u2", "u4", "u6", "u8"}
    assert list(first["check_id"]) == ["PC001", "PC002", "PC003"]
    assert (first[list(gk.CHECK_FIELDS)] == "").all().all()
    assert len(gk.precision_sample(screened, n=50)) == 5


def test_precision_summary_counts_and_interval() -> None:
    """Screening precision uses all coded rows; state measures use true reports only."""
    check = pd.DataFrame(
        {
            "state": ["Kaduna", "Kaduna", "", "", "Ogun"],
            "is_kidnapping_report": ["yes", "yes", "yes", "yes", "no"],
            "state_correct": ["yes", "no", "", "", ""],
            "true_state": ["", "", "FCT", "", ""],
        }
    )
    summary = gk.precision_summary(check).set_index("measure")
    screening, assigned, missed = summary.iloc[0], summary.iloc[1], summary.iloc[2]
    assert (screening["successes"], screening["trials"]) == (4, 5)
    assert screening["ci_low"] < 0.8 < screening["ci_high"]
    assert (assigned["successes"], assigned["trials"]) == (1, 2)
    assert (missed["successes"], missed["trials"]) == (1, 2)


def test_write_precision_sample_never_overwrites(tmp_path) -> None:
    """An existing check file, which holds manual coding, is left unchanged."""
    target = tmp_path / "check.csv"
    target.write_text("coded", encoding="utf-8")
    assert gk.write_precision_sample(pd.DataFrame(), target) is False
    assert target.read_text(encoding="utf-8") == "coded"
