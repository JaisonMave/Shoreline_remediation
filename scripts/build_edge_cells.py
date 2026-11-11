"""Shoreline edge cells for Barataria Bay, from SCAT data only (no imagery, no outcome).

Unit: a 100 m x 100 m UTM 15N grid cell (ASSUMED size) crossed by SCAT-surveyed shoreline.
  max_oiling   worst category among maximum-oiling zones crossing the cell, TB variants folded in:
               Heavy > Moderate > Light > Very_Light > NOO. Surveyed cells with no oiled zone -> NOO.
  esi_main     most frequent ESI code among survey records crossing the cell
  first_oil    earliest survey date recording oil in the cell
  segment      SCAT segment with most survey records in the cell
  cell_2km     2 km block, for clustered standard errors
Box (ASSUMED extent of Barataria Bay): -90.15..-89.75 E, 29.25..29.62 N.
Usage: python scripts/build_edge_cells.py all_surveys.shp max_oiling.shp out.gpkg
"""
import sys
import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box

BOX = (-90.15, 29.25, -89.75, 29.62)
UTM, SIZE = 32615, 100
RANK = {"NOO": 0, "NLE": 0, "Neg_TB": 0, "Very_Light": 1, "Light": 2, "Light_TB": 2, "Moderate": 3,
        "Mod_TB": 3, "Heavy": 4, "Heavy_TB": 4}
NAMES = ["NOO", "Very_Light", "Light", "Moderate", "Heavy"]


def main(all_path, max_path, out):
    a = gpd.read_file(all_path).cx[BOX[0]:BOX[2], BOX[1]:BOX[3]].to_crs(UTM)
    m = gpd.read_file(max_path).to_crs(4326).cx[BOX[0]:BOX[2], BOX[1]:BOX[3]].to_crs(UTM)
    a["rank"] = a.OilCatCode.map(RANK); m["rank"] = m.OilCatCode.map(RANK)
    # candidate cells: only those within reach of a line (fast prefilter via sampled points)
    pts = gpd.GeoSeries(a.geometry.apply(lambda g: [g.interpolate(d) for d in np.arange(0, g.length + 1, 20)]).explode(), crs=UTM)
    keys = set(zip((pts.x // SIZE).astype(int), (pts.y // SIZE).astype(int)))
    grid = gpd.GeoDataFrame({"ix": [k[0] for k in keys], "iy": [k[1] for k in keys]},
                            geometry=[box(i * SIZE, j * SIZE, (i + 1) * SIZE, (j + 1) * SIZE) for i, j in keys], crs=UTM)
    grid["cell"] = grid.ix.astype(str) + "_" + grid.iy.astype(str)
    ja = gpd.sjoin(grid[["cell", "geometry"]], a[["Segment", "ESIType", "rank", "SurvDate", "geometry"]], predicate="intersects")
    jm = gpd.sjoin(grid[["cell", "geometry"]], m[["rank", "geometry"]], predicate="intersects")
    g = grid.set_index("cell")
    g = g[g.index.isin(ja.cell)]
    g["esi_main"] = ja.groupby("cell").ESIType.agg(lambda s: s.value_counts().index[0])
    g["segment"] = ja.groupby("cell").Segment.agg(lambda s: s.value_counts().index[0])
    r = pd.concat([jm.groupby("cell")["rank"].max(), ja.groupby("cell")["rank"].max()], axis=1).max(axis=1)
    g["rank"] = r.reindex(g.index).fillna(0).astype(int)
    g["max_oiling"] = g["rank"].map(dict(enumerate(NAMES)))
    fo = ja[ja["rank"] > 0].groupby("cell").SurvDate.min()
    g["first_oil"] = fo.reindex(g.index).dt.date.astype(str)
    g["cell_2km"] = (g.ix * SIZE // 2000).astype(str) + "_" + (g.iy * SIZE // 2000).astype(str)
    g = g.reset_index()
    g.to_file(out, driver="GPKG")
    marsh = g[g.esi_main == "10A"]
    print(len(g), "cells;", len(marsh), "salt-marsh (ESI 10A) cells")
    print("10A cells by class:", marsh.max_oiling.value_counts().reindex(NAMES).to_dict())
    print("2 km blocks with 10A cells:", marsh.cell_2km.nunique(), "; with Heavy:",
          marsh[marsh.max_oiling == "Heavy"].cell_2km.nunique(), "; with NOO:", marsh[marsh.max_oiling == "NOO"].cell_2km.nunique())
    print("blocks with both Heavy and NOO:", len(set(marsh[marsh.max_oiling == "Heavy"].cell_2km) & set(marsh[marsh.max_oiling == "NOO"].cell_2km)))


if __name__ == "__main__":
    main(*sys.argv[1:4])
