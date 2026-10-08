"""Tests for nysc_safety.nigeria_watch, on HTML laid out like the Nigeria Watch event list. No network requests."""

import pandas as pd
import pytest

from nysc_safety import coding, nigeria_watch as nw

FORM = """<form name="form1" id="chercheForm" method="post" action="index.php?urlaction=evtList">
<input type="hidden" name="F_evt_form" value="1"/>
<input type="text" name="chValues[3]" value=""/>
<select name='chValues[5]' id='selectState' name="">
<option value=''>All</option><option value="2">Abia</option><option value="16">FCT (Abuja)</option>
<option value="38">Zamfara</option></select>
<select name="chTypes[9]"><option value="C">=</option><option value="CVLT">&lt;</option></select>
</form>"""

RESULTS = """<div>1258 Result(s) / 26</div><table>
<tr><td>IBD035927</td><td>Police vs Kidnapers, Delta</td><td>2026-09-23</td><td>2026-09-23</td><td>2</td></tr>
<tr><td>IBD035804</td><td><b>Kidnapped</b> Children Die in Captivity, Oyo</td><td>2026-08-01</td><td>2026-08-31</td><td>6</td></tr>
<tr><td>IBD035521</td><td>Kidnappers Kill Army Colonel, FCT (Abuja)</td><td>2026-07-27</td><td>2026-07-27</td><td>1</td></tr>
<tr><td>PAR000123</td><td>Kidnap Victim Dies, Kano</td><td>2015-01-02</td><td>2015-01-02</td><td>1</td></tr>
<tr><td>IBD000001</td><td>Abduction</td><td>2009-05-01</td><td>2009-05-01</td><td>1</td></tr>
</table>"""


def test_search_form_defaults_include_select_fields() -> None:
    """Form defaults include the select lists whose name the parser cannot read."""
    data = nw.search_form(FORM)
    assert data["F_evt_form"] == "1" and data["chTypes[9]"] == "C"
    assert all(data[field] == "" for field in nw.SELECT_FIELDS)


def test_state_options() -> None:
    """State names are read with their option values."""
    assert nw.state_options(FORM) == {"Abia": "2", "FCT (Abuja)": "16", "Zamfara": "38"}


def test_result_count() -> None:
    """The reported number of results is read from the page."""
    assert nw.result_count(RESULTS) == 1258
    with pytest.raises(ValueError):
        nw.result_count("<p>No match</p>")


def test_events_are_parsed_including_split_titles() -> None:
    """Each event gives identifier, full title, dates and deaths, including titles split by markup."""
    events = nw.parse_events(RESULTS)
    assert list(events["event_id"]) == ["IBD035927", "IBD035804", "IBD035521", "PAR000123", "IBD000001"]
    assert events.loc[1, "title"] == "Kidnapped Children Die in Captivity, Oyo"
    assert events.loc[1, "end_date"] == "2026-08-31" and events.loc[1, "deaths"] == 6


@pytest.mark.parametrize(
    ("title", "state"),
    [
        ("Police vs Kidnapers, Delta", "Delta"),
        ("Kidnappers Kill Army Colonel, FCT (Abuja)", "FCT"),
        ("Abduction", ""),
        ("Gunmen Kill Travellers, Lagos-Ibadan Expressway", ""),
    ],
)
def test_title_state(title: str, state: str) -> None:
    """The state is the last part of the title when it names a state."""
    assert nw.title_state(title) == state


def test_by_state_counts_period_and_rates() -> None:
    """Events and deaths are counted by state within 2010-2026; rates use the 2022 population."""
    events = nw.parse_events(RESULTS)
    events["state"] = events["title"].map(nw.title_state)
    population = pd.DataFrame([(s, 2022, 1_000_000) for s in coding.STATES], columns=["state", "year", "population"])
    table = nw.by_state(events, population).set_index("state")
    assert len(table) == 37 and table["events"].sum() == 4
    assert table.loc["Oyo", "deaths"] == 6
    assert table.loc["Delta", "events_per_100k"] == pytest.approx(0.1)
