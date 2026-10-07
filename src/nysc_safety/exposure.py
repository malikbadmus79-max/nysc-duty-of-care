"""Exposure: corps members sworn in, by state and year.

Run from the repository root with `python -m nysc_safety.exposure`.

No official series of corps members sworn in by state and year is published.
Exposure is therefore modelled in two parts [A09, A10]:

1. State share. Each state's typical orientation-course size is the median of
   the counts reported for that state's camp across batches and streams
   (`data/interim/exposure/state_course_figures.csv`). A state's share is its
   course size divided by the sum of course sizes over all states.
2. National total. The number of corps members deployed or mobilised each year
   (`data/interim/exposure/national_totals.csv`, rows with `use` = yes), with
   years that have no figure filled by linear interpolation between the nearest
   years that have one, and held constant beyond the first or last such year.

Exposure for a state and year is its share multiplied by the national total.
The result is written to `data/processed/exposure_by_state.csv`.
"""

from __future__ import annotations

import pandas as pd

from nysc_safety import coding, paths

YEARS: range = range(2010, 2027)
COUNT_TYPES: tuple[str, ...] = ("sworn_in", "registered", "deployed")


def course_sizes(figures: pd.DataFrame, count_types: tuple[str, ...] = COUNT_TYPES) -> pd.DataFrame:
    """Median reported course size per state, with the number of figures and years covered."""
    rows = figures[figures["count_type"].isin(count_types)]
    unknown = set(rows["state"]) - set(coding.STATES)
    if unknown:
        raise ValueError(f"unknown states: {sorted(unknown)}")
    grouped = rows.groupby("state")
    return pd.DataFrame(
        {
            "n_figures": grouped["count"].size(),
            "course_size": grouped["count"].median(),
            "first_batch_year": grouped["batch_year"].min(),
            "last_batch_year": grouped["batch_year"].max(),
        }
    )


def state_shares(sizes: pd.DataFrame) -> pd.Series:
    """Each state's share of all corps members, from median course sizes."""
    return (sizes["course_size"] / sizes["course_size"].sum()).rename("share")


def annual_totals(national: pd.DataFrame, years: range = YEARS) -> pd.DataFrame:
    """National total per year from the rows marked for use, with interpolated gaps flagged."""
    chosen = national[national["use"] == "yes"]
    if chosen["year"].duplicated().any():
        raise ValueError("more than one national total marked for use in a year")
    series = chosen.set_index("year")["count"].astype(float).reindex(list(years))
    filled = series.interpolate(method="linear", limit_direction="both")
    return pd.DataFrame({"national_total": filled, "interpolated": series.isna()})


def exposure_table(shares: pd.Series, totals: pd.DataFrame) -> pd.DataFrame:
    """Exposure for every state and year: share times national total."""
    frame = pd.DataFrame(
        [(state, year) for state in shares.index for year in totals.index], columns=["state", "year"]
    )
    frame["share"] = frame["state"].map(shares)
    frame["national_total"] = frame["year"].map(totals["national_total"])
    frame["national_interpolated"] = frame["year"].map(totals["interpolated"])
    frame["exposure"] = (frame["share"] * frame["national_total"]).round().astype(int)
    return frame


def main() -> None:
    """Build `data/processed/exposure_by_state.csv`."""
    folder = paths.DATA_INTERIM / "exposure"
    figures = pd.read_csv(folder / "state_course_figures.csv")
    national = pd.read_csv(folder / "national_totals.csv")
    sizes = course_sizes(figures)
    table = exposure_table(state_shares(sizes), annual_totals(national))
    table = table.merge(sizes[["n_figures", "course_size"]], left_on="state", right_index=True)
    out = paths.DATA_PROCESSED / "exposure_by_state.csv"
    table.to_csv(out, index=False)
    missing = sorted(set(coding.STATES) - set(sizes.index))
    print(f"{table['state'].nunique()} states x {table['year'].nunique()} years written to {out.relative_to(paths.ROOT)}")
    if missing:
        print(f"No course figures for: {', '.join(missing)}")


if __name__ == "__main__":
    main()
