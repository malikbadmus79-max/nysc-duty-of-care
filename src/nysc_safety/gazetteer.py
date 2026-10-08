"""Gazetteer of Nigerian places for assigning a state to a news headline.

Run from the repository root with `python -m nysc_safety.gazetteer`.

Built from two saved Wikipedia pages in `data/raw/gazetteer/`:

- "Local government areas of Nigeria" [S553]: the local government areas of
  each state. Each name is kept in full ("Aba North") and, where it ends in a
  compass point or "Municipal", without it ("Aba"); names joined by "/" are
  also split into their parts.
- "List of Nigerian cities by population" [S554]: towns and their states.

A name that maps to more than one state, and every name in `STOPLIST`, is
dropped. The result, one row per place name with its state and origin, is
written to `data/interim/gazetteer/places.csv`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from nysc_safety import coding, paths

LGA_FILE = "wikipedia_lga_list_rev1373216426.txt"
CITY_FILE = "wikipedia_cities_by_population_rev1375631714.txt"

DIRECTION = re.compile(
    r"[\s-]+(North|South|East|West|Central|Municipal|North[\s-]East|North[\s-]West|South[\s-]East|South[\s-]West)$"
)

STOPLIST: frozenset[str] = frozenset(
    {
        # English words and places outside Nigeria
        "Bali", "Brass", "Hong", "Song", "Logo", "Toro", "Gaya", "Kisi", "Tai", "Mani",
        # personal names that are also place names
        "Abi", "Bade", "Bayo", "Edu", "Isa", "Isah", "Ojo", "Rimi", "Uba", "Zaki", "Koko", "Tafawa Balewa",
        # names of more than one Nigerian place, where the listed state is not the usual reading
        "Garki", "Ado", "Ila",
    }
)
"""Names left out of the gazetteer: English words or places outside Nigeria; personal names
that are also place names (Uba is a Borno town and a common name); and names of more than one
Nigerian place where the listed state is not the usual reading (Garki is a Jigawa town and a district
of Abuja; Ado is a Benue LGA and part of Ado-Ekiti). Names that map to more than one state in the
sources are dropped automatically."""

MIN_LENGTH = 3


def _link_text(cell: str) -> str:
    """Display text of the first wiki link in a cell, without bold or italic markup."""
    cell = re.sub(r"\{\{refn.*", "", cell).replace("'''", "").replace("''", "")
    match = re.search(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", cell)
    text = (match.group(2) or match.group(1)) if match else cell
    text = re.sub(r"\s*\(.*?\)", "", text)
    return re.sub(r",\s*(Nigeria|[A-Z][a-z]+ State)$", "", text).strip()


def _state_name(heading: str) -> str | None:
    """State in `coding.STATES` named by a section heading or table cell, or None."""
    text = heading.replace(" State", "").replace(", Nigeria", "").strip()
    if text.startswith("Federal Capital Territory"):
        return "FCT"
    return text if text in coding.STATES else None


def name_variants(name: str) -> set[str]:
    """The name, the name without a trailing compass point, and the parts of a name joined by "/"."""
    names = {name}
    for part in name.split("/"):
        part = part.strip()
        names.add(part)
        names.add(DIRECTION.sub("", part).strip())
    return {n for n in names if len(n) >= MIN_LENGTH}


def parse_lgas(text: str) -> pd.DataFrame:
    """Local government areas by state from the wikitext of the LGA list."""
    rows, state = [], None
    for line in text.splitlines():
        heading = re.match(r"===\s*(.+?)\s*===", line)
        if heading:
            state = _state_name(re.sub(r"[\[\]]", "", heading.group(1)).split("|")[0])
            continue
        if state and line.startswith("* [["):
            rows.append({"lga": _link_text(line[2:]), "state": state})
    return pd.DataFrame(rows)


def parse_cities(text: str) -> pd.DataFrame:
    """Towns and their states from the wikitext of the city list."""
    rows = []
    for block in text.split("\n|-"):
        cells = [c.strip() for c in block.split("\n|")[1:]]
        if len(cells) < 3:
            continue
        town, state = _link_text(cells[1]), _state_name(_link_text(cells[2]))
        if state and "=" not in town:
            rows.append({"town": town, "state": state})
    return pd.DataFrame(rows)


def build(lgas: pd.DataFrame, cities: pd.DataFrame, stoplist: frozenset[str] = STOPLIST) -> pd.DataFrame:
    """One row per unambiguous place name: name, state and origin (`lga`, `town` or both)."""
    rows = [
        {"place": variant, "state": r.state, "origin": "lga"}
        for r in lgas.itertuples()
        for variant in name_variants(r.lga)
    ]
    rows += [{"place": r.town, "state": r.state, "origin": "town"} for r in cities.itertuples()]
    frame = pd.DataFrame(rows)
    frame = frame[~frame["place"].isin(stoplist) & ~frame["place"].isin(coding.STATES)]
    states_per_name = frame.groupby("place")["state"].nunique()
    frame = frame[frame["place"].map(states_per_name) == 1]
    grouped = frame.groupby("place").agg(state=("state", "first"), origin=("origin", lambda o: ";".join(sorted(set(o)))))
    grouped["source_ids"] = grouped["origin"].map(
        lambda o: ";".join(s for s, k in (("S553", "lga"), ("S554", "town")) if k in o)
    )
    return grouped.reset_index().sort_values("place").reset_index(drop=True)


def ambiguous_names(lgas: pd.DataFrame, cities: pd.DataFrame) -> pd.DataFrame:
    """Names that map to more than one state before the stoplist is applied, with their states."""
    rows = [(v, r.state) for r in lgas.itertuples() for v in name_variants(r.lga)]
    rows += [(r.town, r.state) for r in cities.itertuples()]
    frame = pd.DataFrame(rows, columns=["place", "state"]).drop_duplicates()
    multi = frame.groupby("place")["state"].agg(lambda s: ";".join(sorted(s)))
    return multi[multi.str.contains(";")].reset_index()


def load(folder: Path | None = None) -> pd.DataFrame:
    """The saved gazetteer, `data/interim/gazetteer/places.csv`."""
    folder = folder or paths.DATA_INTERIM / "gazetteer"
    return pd.read_csv(folder / "places.csv")


def main() -> None:
    """Build `data/interim/gazetteer/places.csv` and list the names dropped as ambiguous."""
    raw = paths.DATA_RAW / "gazetteer"
    lgas = parse_lgas((raw / LGA_FILE).read_text(encoding="utf-8"))
    cities = parse_cities((raw / CITY_FILE).read_text(encoding="utf-8"))
    places = build(lgas, cities)
    out = paths.DATA_INTERIM / "gazetteer"
    out.mkdir(parents=True, exist_ok=True)
    places.to_csv(out / "places.csv", index=False)
    ambiguous = ambiguous_names(lgas, cities)
    ambiguous.to_csv(out / "ambiguous_names.csv", index=False)
    print(f"{len(lgas)} LGAs in {lgas['state'].nunique()} states; {len(cities)} towns")
    print(f"{len(places)} place names written; {len(ambiguous)} names dropped as ambiguous across states")


if __name__ == "__main__":
    main()
