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
