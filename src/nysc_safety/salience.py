"""Salience gap (H1): news articles per incident, northern against southern zones."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from nysc_safety import coding

NORTH: tuple[str, ...] = ("North West", "North East")
SOUTH: tuple[str, ...] = ("South West", "South East", "South South")
"""Zone groups compared in H1; the North Central zone is in neither group [A03]."""


def zone_groups(incidents: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Articles per incident for the northern and the southern group."""
    north = incidents.loc[incidents["zone"].isin(NORTH), "n_articles"].astype(float)
    south = incidents.loc[incidents["zone"].isin(SOUTH), "n_articles"].astype(float)
    return north, south


def rank_biserial(u_north: float, n_north: int, n_south: int) -> float:
    """Rank-biserial correlation from the Mann-Whitney U of the northern group.

    Positive values mean northern incidents tend to have more articles,
    negative values fewer; 0 means no difference.
    """
    return 2 * u_north / (n_north * n_south) - 1


def mann_whitney(
    north: pd.Series, south: pd.Series, n_boot: int = 10_000, seed: int = 2026
) -> dict[str, float]:
    """One-sided Mann-Whitney U test (north fewer articles) with medians and a bootstrap 95% interval
    for the rank-biserial correlation."""
    result = stats.mannwhitneyu(north, south, alternative="less", method="auto")
    r = rank_biserial(float(result.statistic), len(north), len(south))
    rng = np.random.default_rng(seed)
    a, b = north.to_numpy(), south.to_numpy()
    boot = np.empty(n_boot)
    for i in range(n_boot):
        x, y = rng.choice(a, len(a)), rng.choice(b, len(b))
        boot[i] = rank_biserial(float(stats.mannwhitneyu(x, y).statistic), len(x), len(y))
    return {
        "n_north": float(len(north)),
        "n_south": float(len(south)),
        "median_north": float(north.median()),
        "median_south": float(south.median()),
        "mean_north": float(north.mean()),
        "mean_south": float(south.mean()),
        "u_north": float(result.statistic),
        "p_value": float(result.pvalue),
        "rank_biserial": r,
        "rb_ci_lower": float(np.percentile(boot, 2.5)),
        "rb_ci_upper": float(np.percentile(boot, 97.5)),
    }


def state_shares(incidents: pd.DataFrame, states: tuple[str, ...] = coding.STATES) -> pd.DataFrame:
    """Each state's share of incidents and share of articles."""
    grouped = incidents.groupby("state")
    table = pd.DataFrame(
        {
            "incidents": grouped.size().reindex(list(states), fill_value=0),
            "articles": grouped["n_articles"].sum().reindex(list(states), fill_value=0),
        }
    )
    table["incident_share"] = table["incidents"] / table["incidents"].sum()
    table["article_share"] = table["articles"] / table["articles"].sum()
    table.index.name = "state"
    return table


def spearman(x: pd.Series, y: pd.Series, confidence: float = 0.95) -> dict[str, float]:
    """Spearman correlation with a Fisher-z confidence interval (standard error sqrt(1.06 / (n - 3)))."""
    rho, p = stats.spearmanr(x, y)
    n = len(x)
    z = np.arctanh(np.clip(rho, -0.999999, 0.999999))
    half = stats.norm.ppf(0.5 + confidence / 2) * np.sqrt(1.06 / (n - 3))
    return {"n": float(n), "rho": float(rho), "p_value": float(p),
            "ci_lower": float(np.tanh(z - half)), "ci_upper": float(np.tanh(z + half))}
