"""Shared chart settings and saving, with a source line on every chart."""

from __future__ import annotations

from collections.abc import Iterable

import matplotlib.pyplot as plt

from nysc_safety import paths

SERIES: tuple[str, ...] = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100")
"""Categorical colours in fixed order (blue, orange, aqua, yellow), from the validated reference palette."""
TEXT = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"
SEQUENTIAL = "Blues"


def style() -> None:
    """Apply the project chart style: light surface, recessive grid and axes, neutral text."""
    plt.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "axes.edgecolor": GRID,
            "axes.labelcolor": TEXT_SECONDARY,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.color": TEXT_SECONDARY,
            "ytick.color": TEXT_SECONDARY,
            "text.color": TEXT,
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "legend.frameon": False,
        }
    )


def id_ranges(ids: Iterable[str], max_parts: int = 8) -> str:
    """Source IDs written as ranges ("S18-S20, S22-S146"); a long list is shortened to first-last and count."""
    numbers = sorted({int(i.strip()[1:]) for i in ids if i.strip()})
    if not numbers:
        return ""
    parts, start, prev = [], numbers[0], numbers[0]
    for n in numbers[1:] + [None]:
        if n is not None and n == prev + 1:
            prev = n
            continue
        parts.append(f"S{start:02d}" if start == prev else f"S{start:02d}-S{prev:02d}")
        if n is not None:
            start = prev = n
    if len(parts) > max_parts:
        return f"S{numbers[0]:02d} to S{numbers[-1]:02d} ({len(numbers)} sources)"
    return ", ".join(parts)


def save(fig: plt.Figure, name: str, source: str) -> list[str]:
    """Add a source line under the chart and save it as PNG to `reports/figures/`; return the saved paths."""
    fig.text(0.01, 0.005, f"Source: {source}", ha="left", va="bottom", fontsize=7, color=TEXT_SECONDARY, wrap=True)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    paths.FIGURES.mkdir(parents=True, exist_ok=True)
    out = paths.FIGURES / f"{name}.png"
    fig.savefig(out, dpi=200, facecolor=SURFACE)
    return [str(out.relative_to(paths.ROOT))]
