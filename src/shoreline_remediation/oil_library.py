"""Look up measured oil properties instead of guessing an oil category.

Data: data/oil_properties.csv, built by scripts/build_oil_table.py from NOAA's ADIOS oil database
(https://github.com/NOAA-ORR-ERD/noaa-oil-data, also served at https://adios.orr.noaa.gov). 1,460 oils.

The category rule below is this tool's own convention, taken from the API gravity bands already used in
data_dictionary.py. It is not a regulatory classification:

    light   API gravity 25 or more
    medium  API gravity 15 to under 25
    heavy   API gravity under 15
    solid   pour point above the shoreline temperature, whatever the API gravity (the oil will not flow)

Viscosity is reported at the temperature it was measured at. It changes steeply with temperature, so it is
not adjusted to the scenario temperature here.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "oil_properties.csv"


@lru_cache(maxsize=1)
def load_oils() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


def find_oil(query: str, limit: int = 10) -> pd.DataFrame:
    """Oils whose name contains every word of the query, most complete records first."""
    oils = load_oils()
    names = oils["name"].fillna("").str.lower()
    match = pd.Series(True, index=oils.index)
    for word in query.lower().split():
        match &= names.str.contains(word, regex=False)
    found = oils[match].copy()
    found["_filled"] = found[["api_gravity", "density_kg_m3", "kinematic_viscosity_cst", "pour_point_c"]].notna().sum(axis=1)
    return found.sort_values(["_filled", "reference_year"], ascending=False).drop(columns="_filled").head(limit)


def search_options(query: str, limit: int = 25) -> list[tuple[str, str]]:
    """(oil_id, label) pairs for a name search, for a dropdown. Oils without an API gravity are left out
    because they cannot be given a category."""
    if not query.strip():
        return []
    found = find_oil(query, limit=limit * 2)
    found = found[found["api_gravity"].notna()].head(limit)
    labels = []
    for oil in found.itertuples():
        place = f", {oil.location}" if isinstance(oil.location, str) and oil.location else ""
        labels.append((oil.oil_id, f"{oil.name}{place} (API {oil.api_gravity:.1f}, {oil.oil_id})"))
    return labels


def oil_category(api_gravity: float, pour_point_c: float | None = None, temperature_c: float = 20.0) -> str:
    if pour_point_c is not None and not pd.isna(pour_point_c) and pour_point_c > temperature_c:
        return "solid"
    if api_gravity >= 25:
        return "light"
    return "medium" if api_gravity >= 15 else "heavy"


def scenario_oil_inputs(oil_id: str, temperature_c: float = 20.0) -> dict:
    """Measured properties for one oil, with the category this tool would assign at the given temperature."""
    oils = load_oils()
    rows = oils[oils["oil_id"] == oil_id]
    if rows.empty:
        raise KeyError(f"No oil with id {oil_id!r}. Use find_oil() to search by name.")
    oil = rows.iloc[0]
    if pd.isna(oil["api_gravity"]):
        raise ValueError(f"{oil_id} ({oil['name']}) has no API gravity, so it cannot be categorised.")
    return {
        "oil_id": oil_id, "name": oil["name"],
        "oil_category": oil_category(float(oil["api_gravity"]), oil["pour_point_c"], temperature_c),
        "api_gravity": float(oil["api_gravity"]),
        "density_kg_m3": None if pd.isna(oil["density_kg_m3"]) else float(oil["density_kg_m3"]),
        "kinematic_viscosity_cst": None if pd.isna(oil["kinematic_viscosity_cst"]) else float(oil["kinematic_viscosity_cst"]),
        "viscosity_measured_at_c": None if pd.isna(oil["viscosity_ref_c"]) else float(oil["viscosity_ref_c"]),
        "pour_point_c": None if pd.isna(oil["pour_point_c"]) else float(oil["pour_point_c"]),
    }
