"""Assign each edge cell to a hold-out basin for P2 (docs/P2_BASIN_HOLDOUT_PLAN.md). Geography only.

Basins (fixed before any outcome outside Barataria Bay was measured; lines ASSUMED, approximate):
  terrebonne  west of -90.42 E (Terrebonne and Timbalier bays)
  barataria   east of -90.42 E, west/south of the Mississippi River, not in the birdfoot
  birdfoot    Mississippi River birdfoot delta: south of 29.30 N and east of -89.45 E
  breton      east/north of the river, not in the birdfoot (Breton Sound, St Bernard, Chandeleur, Lake Borgne)
  west        west of -91.20 E is outside the cell box; nothing is assigned there
The river is approximated by a polyline through (lon, lat): (-90.10, 29.95) (-89.95, 29.80) (-89.75, 29.62)
(-89.62, 29.47) (-89.45, 29.30). A cell is east of the river if it lies to the left of the line going downstream.
Usage: python scripts/assign_basins.py cells.gpkg out.csv
"""
import sys

import geopandas as gpd
import numpy as np
import pandas as pd

RIVER = np.array([(-90.10, 29.95), (-89.95, 29.80), (-89.75, 29.62), (-89.62, 29.47), (-89.45, 29.30)])


def east_of_river(lon, lat):
    """True where the point lies left of the downstream river polyline (i.e. east/north side)."""
    lon, lat = np.asarray(lon), np.asarray(lat)
    out = np.zeros(len(lon), dtype=bool)
    # Use the segment whose latitude span contains the point; extend end segments beyond the polyline.
    for k in range(len(RIVER) - 1):
        (x0, y0), (x1, y1) = RIVER[k], RIVER[k + 1]
        lo = -np.inf if k == len(RIVER) - 2 else y1
        hi = np.inf if k == 0 else y0
        sel = (lat <= hi) & (lat > lo)
        cross = (x1 - x0) * (lat[sel] - y0) - (y1 - y0) * (lon[sel] - x0)  # >0 left of the downstream direction
        out[sel] = cross > 0
    return out


def basin_of(lon, lat):
    lon, lat = np.asarray(lon), np.asarray(lat)
    east = east_of_river(lon, lat)
    b = np.where(lon < -90.42, "terrebonne", np.where(east, "breton", "barataria"))
    b = np.where((lat < 29.30) & (lon > -89.45), "birdfoot", b)
    return b


def main(cells_path, out):
    c = gpd.read_file(cells_path)
    pt = c.geometry.centroid.to_crs(4326)
    c["lon"], c["lat"] = pt.x.round(5), pt.y.round(5)
    c["basin"] = basin_of(c.lon.values, c.lat.values)
    c.drop(columns="geometry").to_csv(out, index=False)
    m = c[c.esi_main == "10A"]
    print(pd.crosstab(m.basin, m.max_oiling)[["NOO", "Very_Light", "Light", "Moderate", "Heavy"]].to_string())
    print(m.groupby("basin").cell_2km.nunique().to_dict())


if __name__ == "__main__":
    main(*sys.argv[1:3])
