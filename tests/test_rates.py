"""Tests for nysc_safety.rates."""

import pytest

from nysc_safety import rates


def test_poisson_ci_zero() -> None:
    """For a count of 0 the exact 95% interval is 0 to 3.689."""
    lower, upper = rates.poisson_ci(0)
    assert lower == 0.0
    assert upper == pytest.approx(3.689, abs=1e-3)


def test_poisson_ci_ten() -> None:
    """For a count of 10 the exact 95% interval is 4.795 to 18.390."""
    lower, upper = rates.poisson_ci(10)
    assert lower == pytest.approx(4.795, abs=1e-3)
    assert upper == pytest.approx(18.390, abs=1e-3)


def test_rate_per_10000() -> None:
    """5 incidents among 25,000 corps members is 2 per 10,000."""
    result = rates.rate(5, 25_000)
    assert result["rate"] == pytest.approx(2.0)
    assert result["ci_lower"] < 2.0 < result["ci_upper"]


@pytest.mark.parametrize("exposed", [0, -10])
def test_rate_rejects_non_positive_exposure(exposed: float) -> None:
    """Exposure must be positive."""
    with pytest.raises(ValueError):
        rates.rate(1, exposed)
