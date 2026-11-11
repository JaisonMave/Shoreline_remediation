"""2010 NAIP land/water mosaic and finer exposure measures per edge cell (P1, check 4).

Writes:
  naip2010_land16.tif  2010 land (1) / water (0) on a 16 m UTM 15N grid, NaN = no data. Same 2010 rule as the
                       NAIP edge-loss analysis: NDVI and near-infrared both at or above that tile's Otsu values.
  exposure.csv         per cell: water_250m_2010 (open-water share within 250 m of the cell centre) and
                       fetch_mean_m (mean distance to the first land pixel along 16 compass directions, capped
                       at 10 km; leaving the mosaic counts as open water to the cap).
All from 2010 imagery only, i.e. fixed before the outcome.
Usage: python scripts/exposure_metrics.py cells_10A.csv out_dir
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import planetary_computer as pc
import pystac_client
import rasterio
import rasterio.warp
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
from naip_edge_extract import land_of, ndvi_of, otsu, read_on_grid  # noqa: E402

RES, CELL, MARGIN, FETCH_CAP = 16.0, 100, 12000, 10000.0


def build_land16(cells: pd.DataFrame):
    x0 = cells.ix.min() * CELL - MARGIN; x1 = (cells.ix.max() + 1) * CELL + MARGIN
    y0 = cells.iy.min() * CELL - MARGIN; y1 = (cells.iy.max() + 1) * CELL + MARGIN
    W, H = int((x1 - x0) / RES), int((y1 - y0) / RES); T = from_origin(x0, y1, RES, RES)
    ll = rasterio.warp.transform_bounds("EPSG:32615", "EPSG:4326", x0, y0, x1, y1)
    cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
    items = [i for i in cat.search(collections=["naip"], bbox=list(ll)).items() if int(i.properties["naip:year"]) == 2010]
    land = np.full((H, W), np.nan, dtype="float32")
    for it in items:
        href = pc.sign(it.assets["image"].href)
        with rasterio.open(href) as src:
            f = max(1, int(RES / abs(src.transform.a)))
            red, nir = src.read([1, 4], out_shape=(2, src.height // f, src.width // f), resampling=Resampling.average)
        v = ndvi_of(red, nir); ok = np.isfinite(v)
        t_ndvi, t_nir = otsu(v[ok]), otsu(nir[ok].astype("float32"), value_range=(0, 256))
        b = read_on_grid(href, T, W, H, bands=(1, 4))
        lv = land_of(b[0], b[1], t_ndvi, t_nir)
        put = np.isfinite(lv) & np.isnan(land)
        land[put] = lv[put]
    return land, T, len(items)


def main(cells_path, out_dir):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    cells = pd.read_csv(cells_path)
    land, T, n = build_land16(cells)
    print("2010 NAIP tiles:", n, "valid share:", round(float(np.isfinite(land).mean()), 3), flush=True)
    with rasterio.open(out / "naip2010_land16.tif", "w", driver="GTiff", height=land.shape[0], width=land.shape[1],
                       count=1, dtype="float32", crs="EPSG:32615", transform=T, nodata=np.nan, compress="deflate") as dst:
        dst.write(land, 1)
    H, W = land.shape
    cx = ((cells.ix * CELL + CELL / 2 - T.c) / RES).astype(int).clip(0, W - 1).values
    cy = ((T.f - (cells.iy * CELL + CELL / 2)) / RES).astype(int).clip(0, H - 1).values
    # open water within 250 m
    valid = np.isfinite(land).astype(float); water = np.where(valid > 0, 1 - np.nan_to_num(land), 0)
    r = int(250 / RES); yy, xx = np.mgrid[-r:r + 1, -r:r + 1]; disk = (xx ** 2 + yy ** 2 <= r * r).astype(float)
    w250 = ndimage.convolve(water, disk, mode="constant") / np.maximum(ndimage.convolve(valid, disk, mode="constant"), 1)
    cells["water_250m_2010"] = w250[cy, cx]
    # fetch: march outward from the cell centre; distances counted from the first water pixel
    is_land = np.nan_to_num(land, nan=0.0) >= 0.5
    steps = np.arange(1, int(FETCH_CAP / RES) + 1)
    fetch = np.zeros(len(cells))
    for ang in np.deg2rad(np.arange(0, 360, 22.5)):
        dx, dy = np.cos(ang), -np.sin(ang)
        px = cx[:, None] + np.outer(np.ones(len(cx)), steps) * dx
        py = cy[:, None] + np.outer(np.ones(len(cy)), steps) * dy
        inside = (px >= 0) & (px < W) & (py >= 0) & (py < H)
        hit = np.zeros(px.shape, dtype=bool)
        hit[inside] = is_land[py[inside].astype(int), px[inside].astype(int)]
        # skip the cell's own land: start counting after the first water pixel along the ray
        seen_water = np.cumsum(~hit & inside, axis=1) > 0
        blocked = hit & seen_water
        first = np.where(blocked.any(axis=1), blocked.argmax(axis=1), len(steps) - 1)
        start = np.where(seen_water.any(axis=1), seen_water.argmax(axis=1), first)
        fetch += np.clip((first - start) * RES, 0, FETCH_CAP)
    cells["fetch_mean_m"] = fetch / 16
    cells[["cell", "water_250m_2010", "fetch_mean_m"]].to_csv(out / "exposure.csv", index=False)
    print(cells[["water_1km_2010", "water_250m_2010", "fetch_mean_m"]].describe().round(3).to_string())
    print("correlations:", cells[["water_1km_2010", "water_250m_2010", "fetch_mean_m"]].corr().round(2).to_dict())


if __name__ == "__main__":
    main(*sys.argv[1:3])
