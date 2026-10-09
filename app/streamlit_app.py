"""Streamlit dashboard: Duty of Care to NYSC Corps Members in an Era of Insecurity.

Run from the repository root with `streamlit run app/streamlit_app.py`
after `pip install -e .`.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from nysc_safety import camp_calendar, coding, dashboard, figures, paths, scorecard
from nysc_safety.travel_window import H2_STAGES, h2_sample

BLUE = figures.SERIES[0]
INK = figures.TEXT_SECONDARY
SEQUENTIAL = [[0.0, "#eef4fb"], [1.0, "#0b3d7a"]]
"""Single-hue scale from light to dark for magnitudes."""
REGISTER_SOURCE = "NYSC incident register, data/processed/incidents.csv (source IDs per incident)"
EXPOSURE_SOURCE = "modelled exposure, data/processed/exposure_by_state.csv [A09, A10]"
BOUNDARY_SOURCE = "state boundaries, geoBoundaries NGA ADM1 [S566]"

st.set_page_config(page_title="NYSC duty of care", layout="wide")


@st.cache_data
def load() -> dict[str, object]:
    """All inputs of the dashboard."""
    calendar = pd.read_csv(paths.DATA_PROCESSED / "nysc_calendar.csv")
    for column in camp_calendar.EVENTS:
        calendar[column] = pd.to_datetime(calendar[column]).dt.date
    dates = pd.read_csv(paths.DATA_INTERIM / "calendar" / "nysc_dates.csv", dtype=str)
    return {
        "incidents": pd.read_csv(paths.DATA_PROCESSED / "incidents.csv"),
        "exposure": pd.read_csv(paths.DATA_PROCESSED / "exposure_by_state.csv"),
        "scores": pd.read_csv(paths.DATA_PROCESSED / "policy_scorecard.csv"),
        "geo": dashboard.load_states_geojson(),
        "anchors": camp_calendar.anchors(calendar, dates[dates["status"] == "use_extra"]),
    }


def caption(text: str) -> None:
    """Source line under a chart or table."""
    st.caption(f"Source: {text}.")


def overview(data: dict[str, object]) -> None:
    """Headline numbers and the pre-registered results."""
    incidents: pd.DataFrame = data["incidents"]
    killed = int(incidents["victims_killed"].fillna(0).sum())
    abducted = int(incidents["victims_abducted"].fillna(0).sum())
    cols = st.columns(4)
    cols[0].metric("Incidents recorded, 2010 to 5 October 2026", f"{len(incidents):,}")
    cols[1].metric("Kidnapping incidents", f"{(incidents['harm_type'] == 'kidnapping').sum():,}")
    cols[2].metric("Corps members abducted", f"{abducted:,}")
    cols[3].metric("Corps members killed", f"{killed:,}")
    caption(REGISTER_SOURCE)

    st.subheader("Pre-registered hypotheses")
    rows = []
    h1 = dashboard.read_table("h1_results")
    if h1 is not None:
        r = h1.iloc[0]
        rows.append(("H1 Salience gap", f"Median articles per incident {r['median_north']:.0f} (north) and {r['median_south']:.0f} (south); Mann-Whitney p = {r['p_value']:.3f}", "Supported" if r["p_value"] < 0.05 and r["median_north"] < r["median_south"] else "Not supported"))
    h2 = dashboard.read_table("h2_results")
    if h2 is not None:
        r = h2.iloc[0]
        rows.append(("H2 Travel window", f"{r['in_window']:.0f} of {r['n_events']:.0f} incidents within 7 days of camp-opening or passing-out dates ({r['observed_share']:.0%}), against {r['expected_share']:.1%} of calendar days; p = {r['p_value']:.3f}", "Supported" if r["p_value"] < 0.05 else "Not supported"))
    h3 = dashboard.read_table("h3_robustness")
    if h3 is not None:
        r = h3.iloc[0]
        rows.append(("H3 Exposure-adjusted risk", f"State rates differ: likelihood ratio {r['lr_statistic']:.1f}, df {r['df']:.0f}, p = {r['p_value']:.6f} ({r['model']})", "Supported" if r["p_value"] < 0.05 else "Not supported"))
    h4 = dashboard.read_table("h4_spearman")
    if h4 is not None:
        r = h4.iloc[0]
        rows.append(("H4 Relative risk", f"Spearman rho {r['rho']:.2f} (95% interval {r['ci_lower']:.2f} to {r['ci_upper']:.2f}), one-sided p = {r['p_value_one_sided']:.3f}, {r['n_states']:.0f} states", "Supported" if r["rho"] > 0 and r["p_value_one_sided"] < 0.05 else "Not supported"))
    h5 = dashboard.read_table("h5_change_2018_2026")
    if h5 is not None:
        r = h5.set_index("measure").loc["full"]
        rows.append(("H5 Resources", f"Security-related allocation per corps member, constant 2024 naira: {r['per_member_2018']:,.0f} in 2018 and "
                     f"{r['per_member_2026']:,.0f} in 2026 ({r['change_percent']:+.0f}%)", "Descriptive"))
    st.dataframe(pd.DataFrame(rows, columns=["Hypothesis", "Result", "Decision"]), hide_index=True, width="stretch")
    caption("result tables in reports/tables/, written by notebooks 02 to 04; tests and decision rules in docs/preregistration.md")


def incidents_view(data: dict[str, object]) -> None:
    """Map and table of incidents, with filters."""
    incidents: pd.DataFrame = data["incidents"]
    years = pd.to_datetime(incidents["event_date"]).dt.year
    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
    harms = c1.multiselect("Harm type", coding.HARM_TYPES, default=list(coding.HARM_TYPES))
    stages = c2.multiselect("Stage of the service year", coding.LIFECYCLE_STAGES, default=list(coding.LIFECYCLE_STAGES))
    span = c3.slider("Years", 2010, int(dashboard.CUTOFF.year), (2010, int(dashboard.CUTOFF.year)))
    measure = c4.radio("Map shows", ["Rate per 10,000", "Incidents"])
    chosen = dashboard.filter_incidents(incidents, harms, stages, span)
    table = dashboard.state_table(chosen, data["exposure"], span)
    column = "rate" if measure == "Rate per 10,000" else "incidents"
    fig = px.choropleth(
        table, geojson=data["geo"], locations="state", featureidkey="properties.state", color=column,
        color_continuous_scale=SEQUENTIAL, hover_name="state",
        hover_data={"state": False, "incidents": True, "rate": ":.2f", "exposed": ":,.0f"},
        labels={"rate": "Per 10,000 exposed", "incidents": "Incidents", "exposed": "Corps members exposed"},
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_traces(marker_line_color="white", marker_line_width=1)
    fig.update_layout(height=520, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, width="stretch")
    caption(f"{REGISTER_SOURCE}; {EXPOSURE_SOURCE}; {BOUNDARY_SOURCE}. {len(chosen)} incidents selected; years {span[0]} to {span[1]}")
    columns = ["incident_id", "event_date", "state", "lga", "lifecycle_stage", "harm_type", "member_status",
               "victims_total", "victims_killed", "victims_abducted", "outcome", "n_articles", "source_ids", "coding_note"]
    st.dataframe(chosen[columns].sort_values("event_date", ascending=False), hide_index=True, width="stretch")
    caption(f"{REGISTER_SOURCE}. Locations are given at local government area level at the finest; no names are stored")


def rates_view(data: dict[str, object]) -> None:
    """State rates with intervals (H3) and the comparison with general kidnapping (H4)."""
    table = dashboard.state_table(data["incidents"], data["exposure"]).sort_values("rate")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=table["rate"], y=table["state"], mode="markers",
        marker=dict(color=BLUE, size=9, line=dict(color="white", width=1.5)),
        error_x=dict(type="data", symmetric=False, array=table["ci_upper"] - table["rate"],
                     arrayminus=table["rate"] - table["ci_lower"], color=BLUE, thickness=1.5, width=0),
        customdata=table[["incidents", "ci_lower", "ci_upper"]],
        hovertemplate="%{y}: %{x:.2f} per 10,000 (95%% interval %{customdata[1]:.2f} to %{customdata[2]:.2f}); %{customdata[0]} incidents<extra></extra>",
    ))
    fig.update_layout(height=900, margin=dict(l=0, r=0, t=30, b=0), title="Incidents per 10,000 corps members exposed, 2010 to 5 October 2026 (95% exact interval)",
                      xaxis_title="Incidents per 10,000 exposed", plot_bgcolor="white")
    fig.update_xaxes(gridcolor="#e6e6e6", rangemode="tozero")
    st.plotly_chart(fig, width="stretch")
    caption(f"{REGISTER_SOURCE}; {EXPOSURE_SOURCE}")

    h4 = dashboard.read_table("h4_state_rates_news")
    if h4 is not None:
        fig = px.scatter(h4, x="general_rate", y="nysc_rate", hover_name="state", color_discrete_sequence=[BLUE],
                         labels={"general_rate": "General kidnapping events per 100,000 (coded news series)",
                                 "nysc_rate": "Corps-member incidents per 10,000 exposed"},
                         title="Corps-member incident rates and general kidnapping rates by state (H4)")
        fig.update_traces(marker=dict(size=10, line=dict(color="white", width=1.5)))
        fig.update_layout(height=480, plot_bgcolor="white", margin=dict(l=0, r=0, t=40, b=0))
        fig.update_xaxes(gridcolor="#e6e6e6", rangemode="tozero")
        fig.update_yaxes(gridcolor="#e6e6e6", rangemode="tozero")
        st.plotly_chart(fig, width="stretch")
        caption(f"{REGISTER_SOURCE}; {EXPOSURE_SOURCE}; general kidnapping news series [S555, S551, S553, S554] [A12, A13, A14]")


def scorecard_view(data: dict[str, object]) -> None:
    """Duty-of-care scores before and after the June 2026 reform."""
    table = dashboard.scorecard_table(data["scores"])
    totals = scorecard.summarise(data["scores"]).set_index("framework")
    cols = st.columns(2)
    for col, key, label in ((cols[0], "current", "Current framework"), (cols[1], "reform_2026", "With the June 2026 reform")):
        col.metric(label, f"{int(totals.loc[key, 'total'])} of {int(totals.loc[key, 'max_possible'])}")
    long = table.melt(id_vars=["criterion_id", "criterion"], value_vars=["current", "reform_2026"], var_name="framework", value_name="score")
    long["framework"] = long["framework"].map({"current": "Current framework", "reform_2026": "With June 2026 reform"})
    long["label"] = long["criterion_id"] + " " + long["criterion"]
    fig = px.bar(long, x="score", y="label", color="framework", barmode="group", orientation="h",
                 color_discrete_sequence=[figures.SERIES[1], BLUE], range_x=[0, scorecard.MAX_SCORE],
                 labels={"score": "Score (0 to 3)", "label": "", "framework": ""})
    fig.update_layout(height=640, plot_bgcolor="white", margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=1.05),
                      yaxis=dict(autorange="reversed"), bargap=0.3, bargroupgap=0.1)
    fig.update_xaxes(gridcolor="#e6e6e6", dtick=1)
    st.plotly_chart(fig, width="stretch")
    st.dataframe(table, hide_index=True, width="stretch")
    with st.expander("Score scale"):
        for score, text in scorecard.SCALE.items():
            st.write(f"{score}: {text}")
    caption("data/processed/policy_scorecard.csv; criteria and evidence in docs/policy_audit.md [S01, S02, S03]")


def travel_view(data: dict[str, object]) -> None:
    """Days from each travel-stage incident to the nearest camp-opening or passing-out date (H2)."""
    sample = h2_sample(data["incidents"], H2_STAGES)
    sample = sample[sample["event_day"] <= dashboard.CUTOFF]
    offsets = dashboard.nearest_anchor_days(sample["event_day"], data["anchors"])
    frame = pd.DataFrame({"days": offsets, "incident_id": sample["incident_id"].to_numpy()})
    frame["inside"] = frame["days"].abs() <= 7
    fig = go.Figure()
    for inside, name, color in ((True, "Within 7 days", BLUE), (False, "Outside the window", "#9aa5b1")):
        part = frame[frame["inside"] == inside]
        fig.add_trace(go.Histogram(x=part["days"], xbins=dict(start=-90.5, end=90.5, size=3), name=name, marker_color=color,
                                   marker_line=dict(color="white", width=1)))
    fig.add_vrect(x0=-7.5, x1=7.5, fillcolor=BLUE, opacity=0.07, line_width=0)
    fig.update_layout(barmode="overlay", height=420, plot_bgcolor="white", margin=dict(l=0, r=0, t=40, b=0),
                      title="Days from each incident to the nearest camp-opening or passing-out date",
                      xaxis_title="Days (negative: before the date)", yaxis_title="Incidents", legend=dict(orientation="h", y=1.08))
    fig.update_yaxes(gridcolor="#e6e6e6", dtick=1)
    st.plotly_chart(fig, width="stretch")
    h2 = dashboard.read_table("h2_results")
    if h2 is not None:
        r = h2.iloc[0]
        st.write(f"{r['in_window']:.0f} of {r['n_events']:.0f} day-dated incidents in the travel, camp and passing-out stages "
                 f"fell within 7 days of an official date, against {r['expected_share']:.1%} of calendar days in such windows "
                 f"(one-sided exact binomial p = {r['p_value']:.3f}).")
    caption(f"{REGISTER_SOURCE}; NYSC calendar, data/processed/nysc_calendar.csv [A11]. Incidents more than 90 days from any date are outside the chart range")


st.title("Duty of care to NYSC corps members")
st.write("Incidents of serious harm to prospective and serving corps members, 2010 to 5 October 2026, "
         "rates by state, the duty-of-care scorecard and the travel-window test. Methods: docs/analysis_plan.md.")
DATA = load()
tabs = st.tabs(["Overview", "Incidents", "Rates by state", "Scorecard", "Travel window"])
with tabs[0]:
    overview(DATA)
with tabs[1]:
    incidents_view(DATA)
with tabs[2]:
    rates_view(DATA)
with tabs[3]:
    scorecard_view(DATA)
with tabs[4]:
    travel_view(DATA)
