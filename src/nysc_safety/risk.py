"""Exposure-adjusted risk by state (H3) and comparison with general kidnapping (H4)."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from nysc_safety import coding, exposure, rates

DISPERSION_LIMIT = 1.5
MIN_EXPOSED = 1_000


def exposure_variant(
    figures: pd.DataFrame,
    national: pd.DataFrame,
    count_types: tuple[str, ...] = exposure.COUNT_TYPES,
    min_batch_year: int | None = None,
) -> pd.DataFrame:
    """Exposure by state and year from a subset of the course figures [A09]: chosen count types, and
    optionally only batches from `min_batch_year` on. States with no figure in the subset are absent."""
    subset = figures
    if min_batch_year is not None:
        subset = subset[subset["batch_year"] >= min_batch_year]
    sizes = exposure.course_sizes(subset, count_types)
    return exposure.exposure_table(exposure.state_shares(sizes), exposure.annual_totals(national))


def state_year_panel(
    incidents: pd.DataFrame,
    exposure_table: pd.DataFrame,
    cutoff: date,
    start_year: int = 2010,
    window_years: int = 1,
) -> pd.DataFrame:
    """Incident counts and exposure by state and year, from `start_year` to the year of `cutoff`.

    Exposure in the cutoff year is scaled by the share of that year up to the
    cutoff [A15]. With `window_years` = 2, exposure in a year is the sum of the
    year and the year before, so that each corps member counts in both
    calendar years of service [A02].
    """
    table = exposure_table[["state", "year", "exposure"]].astype({"exposure": float})
    if window_years > 1:
        table = table.sort_values(["state", "year"])
        table["exposure"] = (
            table.groupby("state")["exposure"].transform(lambda s: s.rolling(window_years, min_periods=1).sum())
        )
    table = table[(table["year"] >= start_year) & (table["year"] <= cutoff.year)].copy()
    fraction = (cutoff - date(cutoff.year, 1, 1)).days / 365
    table.loc[table["year"] == cutoff.year, "exposure"] *= fraction
    dated = incidents.assign(year=pd.to_datetime(incidents["event_date"]).dt.year)
    dated = dated[pd.to_datetime(dated["event_date"]).dt.date <= cutoff]
    counts = dated.groupby(["state", "year"]).size().rename("incidents")
    table = table.merge(counts, left_on=["state", "year"], right_index=True, how="left")
    table["incidents"] = table["incidents"].fillna(0).astype(int)
    return table.reset_index(drop=True)


def drop_small_states(panel: pd.DataFrame, minimum: float = MIN_EXPOSED) -> tuple[pd.DataFrame, list[str]]:
    """Panel without states whose total exposure is below `minimum`, and the list of states dropped."""
    totals = panel.groupby("state")["exposure"].sum()
    small = sorted(totals[totals < minimum].index)
    return panel[~panel["state"].isin(small)].reset_index(drop=True), small


def h3_test(panel: pd.DataFrame, limit: float = DISPERSION_LIMIT) -> dict[str, object]:
    """Likelihood-ratio test of state terms against an intercept-only model, with log exposure as offset.

    A Poisson model is fitted first. If the Pearson dispersion statistic of
    the state model exceeds `limit`, both models are refitted as negative
    binomial models (NB2, with the dispersion parameter estimated by maximum
    likelihood) and the test uses those.
    """
    y = panel["incidents"].to_numpy()
    offset = np.log(panel["exposure"].to_numpy())
    x_state = pd.get_dummies(panel["state"], drop_first=True, dtype=float)
    x_state.insert(0, "const", 1.0)
    x_null = np.ones((len(panel), 1))
    full = sm.GLM(y, x_state, family=sm.families.Poisson(), offset=offset).fit()
    null = sm.GLM(y, x_null, family=sm.families.Poisson(), offset=offset).fit()
    dispersion = float(full.pearson_chi2 / full.df_resid)
    df = int(x_state.shape[1] - 1)
    model = "poisson"
    llf_full, llf_null = float(full.llf), float(null.llf)
    alpha = float("nan")
    if dispersion > limit:
        model = "negative_binomial"
        nb_full = sm.NegativeBinomial(y, x_state, offset=offset).fit(disp=0, maxiter=500, method="bfgs")
        nb_null = sm.NegativeBinomial(y, x_null, offset=offset).fit(disp=0, maxiter=500, method="bfgs")
        llf_full, llf_null = float(nb_full.llf), float(nb_null.llf)
        alpha = float(nb_full.params.iloc[-1])
    lr = max(2 * (llf_full - llf_null), 0.0)
    return {
        "model": model,
        "n_obs": len(panel),
        "n_states": int(panel["state"].nunique()),
        "incidents": int(y.sum()),
        "dispersion_poisson": dispersion,
        "nb_alpha": alpha,
        "lr_statistic": lr,
        "df": df,
        "p_value": float(stats.chi2.sf(lr, df)),
    }


def state_rates(panel: pd.DataFrame) -> pd.DataFrame:
    """Incidents, exposure and rate per 10,000 exposed by state over the panel, with exact 95% intervals,
    and the rank of each state by count and by rate (1 = highest)."""
    totals = panel.groupby("state")[["incidents", "exposure"]].sum()
    rows = [{"state": s, **rates.rate(int(r.incidents), float(r.exposure))} for s, r in totals.iterrows()]
    table = pd.DataFrame(rows).rename(columns={"count": "incidents"})
    table["incidents"] = table["incidents"].astype(int)
    table["rank_count"] = table["incidents"].rank(ascending=False, method="min").astype(int)
    table["rank_rate"] = table["rate"].rank(ascending=False, method="min").astype(int)
    table.insert(1, "zone", table["state"].map(coding.zone_of))
    return table.sort_values("rate", ascending=False).reset_index(drop=True)


def top_states(panel: pd.DataFrame, n: int = 5) -> list[str]:
    """The `n` states with the most incidents (ties broken alphabetically)."""
    totals = panel.groupby("state")["incidents"].sum().reset_index()
    return list(totals.sort_values(["incidents", "state"], ascending=[False, True])["state"].head(n))


def spearman_one_sided(x: pd.Series, y: pd.Series, n_boot: int = 10_000, seed: int = 2026) -> dict[str, float]:
    """Spearman correlation with a one-sided p-value (rho > 0) and a bootstrap 95% interval."""
    frame = pd.DataFrame({"x": x, "y": y}).dropna()
    rho, p_two = stats.spearmanr(frame["x"], frame["y"])
    p_one = p_two / 2 if rho > 0 else 1 - p_two / 2
    rng = np.random.default_rng(seed)
    values = frame.to_numpy()
    boot = []
    for _ in range(n_boot):
        sample = values[rng.integers(0, len(values), len(values))]
        if np.unique(sample[:, 0]).size > 1 and np.unique(sample[:, 1]).size > 1:
            boot.append(stats.spearmanr(sample[:, 0], sample[:, 1])[0])
    return {
        "n_states": float(len(frame)),
        "rho": float(rho),
        "p_value_one_sided": float(p_one),
        "ci_lower": float(np.nanpercentile(boot, 2.5)),
        "ci_upper": float(np.nanpercentile(boot, 97.5)),
    }
