"""Tests for nysc_safety.figures."""

import matplotlib.pyplot as plt

from nysc_safety import figures


def test_id_ranges_compresses_runs() -> None:
    """Consecutive IDs become ranges; single IDs stay single."""
    assert figures.id_ranges(["S18", "S19", "S20", "S22", "S147", "S23"]) == "S18-S20, S22-S23, S147"


def test_id_ranges_shortens_long_lists() -> None:
    """More parts than the limit give first, last and count."""
    assert figures.id_ranges([f"S{n}" for n in range(100, 140, 2)], max_parts=5) == "S100 to S138 (20 sources)"


def test_save_writes_png_with_source_line(tmp_path, monkeypatch) -> None:
    """A saved chart is a PNG in the figures folder and carries the source text."""
    monkeypatch.setattr(figures.paths, "FIGURES", tmp_path / "figures")
    monkeypatch.setattr(figures.paths, "ROOT", tmp_path)
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    saved = figures.save(fig, "test_chart", "S01")
    assert saved == ["figures/test_chart.png".replace("/", __import__("os").sep)]
    assert (tmp_path / "figures" / "test_chart.png").stat().st_size > 0
    assert any(t.get_text() == "Source: S01" for t in fig.texts)
