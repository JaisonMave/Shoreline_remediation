"""Map data for the Home page Gulf map (Stage 1 of the map-first dashboard). No Streamlit import: data access and mapping
rules only, so they can be tested without the app.

Everything plotted here is a real row of data/demo/p5_sites.csv. A clicked or typed coordinate is only ever matched to an
existing row within a small tolerance; this module never creates a site and never assigns an in_scope status.
Habitat demonstrations that have no Gulf coordinates are returned as a list for display, not as map points.
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import pandas as pd

SITES_PATH = Path(__file__).resolve().parents[2] / "data" / "demo" / "p5_sites.csv"
COLUMNS = ["cell", "lat", "lon", "basin", "segment", "esi_main", "max_oiling", "status", "observed_rate"]

# Duplicated from site_view (which imports Streamlit); tests/test_map_sites.py asserts they stay equal.
EXAMPLE_CELL = "8018_32612"
SITE_MODE_WORKED = "Worked example (Bay Jimmy, Barataria Bay)"
SITE_MODE_PICK = "Pick a Louisiana edge cell"
PICKER_BASINS = ("barataria", "breton", "terrebonne", "birdfoot")
LAYER_BASINS = ("barataria", "breton", "terrebonne")
LAYER_CAP = 1500
LOOKUP_TOLERANCE_DEG = 0.0005      # about 55 m
GULF_VIEW = {"latitude": 25.0, "longitude": -90.0, "zoom": 4.2}

# Habitat demonstrations without Gulf coordinates: (site_habitat key, label, evidence note). Not plotted.
HABITAT_DEMOS = (
    ("beach_fine", "Sand beach (ESI 3A)", "Habitat screening only. No site record and no numerical forecast."),
    ("esi_1A", "Rocky shore (ESI 1A)", "Habitat screening only. No site record, no outcome model; natural recovery stays the reference."),
    ("esi_8A", "Rocky shore (ESI 8A)", "Habitat screening only. No site record, no outcome model; natural recovery stays the reference."),
    ("mangrove", "Mangrove: Bahía Las Minas, Panama",
     "Limited-evidence case outside the Gulf of Mexico: one field study of one 1986 spill, oiling damage only. "
     "Not plotted on this map; the platform abstains from a cleanup forecast."),
)


@lru_cache(maxsize=1)
def load_cells(path: str = str(SITES_PATH)) -> pd.DataFrame:
    """The p5 cell table, reduced to the map columns. Raises FileNotFoundError if the repository file is missing."""
    d = pd.read_csv(path, usecols=COLUMNS, dtype={"cell": str})
    return d.dropna(subset=["lat", "lon"]).reset_index(drop=True)


def demonstration_pins(cells: pd.DataFrame | None = None) -> pd.DataFrame:
    """Rows to plot as demonstration pins: only the Bay Jimmy worked cell. Empty if the cell is not in the table."""
    cells = load_cells() if cells is None else cells
    d = cells[cells.cell == EXAMPLE_CELL].copy()
    d["name"] = "Bay Jimmy worked example"
    return d.reset_index(drop=True)


def cell_layer(basin: str | None, cap: int = LAYER_CAP, cells: pd.DataFrame | None = None) -> pd.DataFrame:
    """In-scope ESI 10A cells of one basin, deterministically downsampled to at most `cap` rows. Never the whole table.
    An unknown basin or None gives an empty frame."""
    if basin not in LAYER_BASINS:
        return pd.DataFrame(columns=COLUMNS)
    cells = load_cells() if cells is None else cells
    d = cells[(cells.basin == basin) & (cells.esi_main == "10A") & (cells.status == "in_scope")]
    cap = max(0, min(int(cap), LAYER_CAP))
    if len(d) > cap:
        d = d.sample(n=cap, random_state=0)
    return d.sort_values("cell").reset_index(drop=True)


def lookup_cell(lat, lon, tol: float = LOOKUP_TOLERANCE_DEG, cells: pd.DataFrame | None = None) -> dict | None:
    """The nearest existing p5 row within `tol` degrees of (lat, lon), as a dict; None otherwise (open water, other coastlines,
    invalid input). Whatever status the row has in the table is reported unchanged; no status is ever invented."""
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(lat) and math.isfinite(lon)):
        return None
    cells = load_cells() if cells is None else cells
    near = cells[((cells.lat - lat).abs() <= tol) & ((cells.lon - lon).abs() <= tol)]
    if near.empty:
        return None
    dist = (near.lat - lat) ** 2 + (near.lon - lon) ** 2
    return near.loc[dist.idxmin()].to_dict()


def cell_by_id(cell_id: str, cells: pd.DataFrame | None = None) -> dict | None:
    cells = load_cells() if cells is None else cells
    row = cells[cells.cell == str(cell_id)]
    return None if row.empty else row.iloc[0].to_dict()


def session_updates_for_cell(row: dict) -> dict:
    """Session-state values that point the existing site selection at this cell.

    The worked-example cell uses exactly what site_view.select_site("marsh") sets. Any other known cell fills the existing
    'Pick a Louisiana edge cell' widgets (site_mode, pick_basin, pick_oil, pick_scope, pick_seg, pick_cell). Returns {} when
    the row cannot be reproduced by that picker (not ESI 10A or unknown basin), so nothing is selected."""
    if row.get("cell") == EXAMPLE_CELL:
        return {"site_habitat": "marsh", "site_mode": SITE_MODE_WORKED}
    if row.get("esi_main") != "10A" or row.get("basin") not in PICKER_BASINS or not isinstance(row.get("segment"), str):
        return {}
    return {"site_habitat": "marsh", "site_mode": SITE_MODE_PICK, "pick_basin": row["basin"], "pick_oil": "any",
            "pick_scope": row.get("status") == "in_scope", "pick_seg": row["segment"], "pick_cell": str(row["cell"])}
