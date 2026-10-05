"""Exposure-adjusted incident rates with exact Poisson confidence intervals."""

from __future__ import annotations

from scipy import stats

PER: int = 10_000
"""Rates are expressed per 10,000 corps members deployed."""


def poisson_ci(count: int, confidence: float = 0.95) -> tuple[float, float]:
    """Exact (Garwood) confidence interval for a Poisson count."""
    if count < 0:
        raise ValueError("count must be non-negative")
    alpha = 1 - confidence
    lower = 0.0 if count == 0 else stats.chi2.ppf(alpha / 2, 2 * count) / 2
    upper = stats.chi2.ppf(1 - alpha / 2, 2 * (count + 1)) / 2
    return float(lower), float(upper)


def rate(count: int, exposed: float, per: int = PER, confidence: float = 0.95) -> dict[str, float]:
    """Incident rate per `per` exposed persons, with an exact confidence interval."""
    if exposed <= 0:
        raise ValueError("exposed must be positive")
    lower, upper = poisson_ci(count, confidence)
    scale = per / exposed
    return {
        "count": float(count),
        "exposed": float(exposed),
        "rate": count * scale,
        "ci_lower": lower * scale,
        "ci_upper": upper * scale,
    }
