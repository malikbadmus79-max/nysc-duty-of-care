"""Inter-coder reliability for the double-coded sample of the incident register."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd


def percent_agreement(coder_a: Sequence[object], coder_b: Sequence[object]) -> float:
    """Share of items on which two coders assigned the same code."""
    a, b = _paired(coder_a, coder_b)
    return float((a == b).mean())


def cohens_kappa(coder_a: Sequence[object], coder_b: Sequence[object]) -> float:
    """Cohen's kappa for two coders assigning one nominal code per item.

    kappa = (p_o - p_e) / (1 - p_e), where p_o is observed agreement and p_e is
    the agreement expected from each coder's marginal code shares. Returns 1.0
    when both coders use a single identical code for every item (p_e = 1).
    """
    a, b = _paired(coder_a, coder_b)
    p_o = float((a == b).mean())
    shares_a = a.value_counts(normalize=True)
    shares_b = b.value_counts(normalize=True)
    p_e = float(shares_a.mul(shares_b, fill_value=0).sum())
    if p_e == 1.0:
        return 1.0
    return (p_o - p_e) / (1 - p_e)


def weighted_kappa(
    coder_a: Sequence[int], coder_b: Sequence[int], categories: Sequence[int], power: int = 2
) -> float:
    """Weighted Cohen's kappa for ordinal scores such as the 0 to 3 scorecard scale.

    Disagreement weights are |i - j| ** power divided by the largest such
    distance; power 2 gives quadratic weights and power 1 linear weights.
    kappa = 1 - sum(w * observed) / sum(w * expected).
    """
    a, b = _paired(coder_a, coder_b)
    cats = list(categories)
    index = {c: i for i, c in enumerate(cats)}
    unknown = (set(a) | set(b)) - set(cats)
    if unknown:
        raise ValueError(f"Scores outside the categories: {sorted(unknown)}")
    k = len(cats)
    observed = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        observed[index[x]][index[y]] += 1 / len(a)
    row = [sum(r) for r in observed]
    col = [sum(observed[i][j] for i in range(k)) for j in range(k)]
    span = (k - 1) ** power
    num = den = 0.0
    for i in range(k):
        for j in range(k):
            w = abs(i - j) ** power / span
            num += w * observed[i][j]
            den += w * row[i] * col[j]
    if den == 0:
        return 1.0
    return 1 - num / den


def kappa_table(
    sample_a: pd.DataFrame, sample_b: pd.DataFrame, columns: Sequence[str], key: str = "incident_id"
) -> pd.DataFrame:
    """Kappa and percent agreement for each coded column in two coders' sheets.

    The sheets are joined on `key`; items present in only one sheet are dropped
    and counted in the `n` column of the result.
    """
    merged = sample_a.merge(sample_b, on=key, suffixes=("_a", "_b"))
    rows = []
    for column in columns:
        a = merged[f"{column}_a"]
        b = merged[f"{column}_b"]
        rows.append(
            {
                "variable": column,
                "n": len(merged),
                "percent_agreement": percent_agreement(a, b),
                "kappa": cohens_kappa(a, b),
            }
        )
    return pd.DataFrame(rows)


def _paired(coder_a: Sequence[object], coder_b: Sequence[object]) -> tuple[pd.Series, pd.Series]:
    """Return the two code lists as aligned Series; reject unequal or empty input."""
    a = pd.Series(list(coder_a), dtype="object")
    b = pd.Series(list(coder_b), dtype="object")
    if len(a) != len(b):
        raise ValueError(f"Coders rated different numbers of items: {len(a)} and {len(b)}")
    if len(a) == 0:
        raise ValueError("No items to compare")
    return a, b
