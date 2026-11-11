"""Land fraction per shoreline edge cell from NAIP, 2010-2017 (see docs/NAIP_EDGE_LOSS_PLAN.md).

Land classification (amended twice after the quality checks, before any outcome was compared by class):
  2010: land = NDVI and near-infrared both at or above Otsu thresholds of that tile (16 m overview).
  2013/2015/2017: a logistic-regression classifier per tile and year, on red, green, blue, near-infrared and
        NDVI, trained on pixels deep inside 2010 land or 2010 water (more than 32 m from any 2010 edge,
        8 m grid). Per-tile Otsu thresholds failed on 40% of later tiles (haze, turbid plumes).
  Tile-years whose land share moves more than 0.10 from 2010 are dropped as failures. For each 1 km block holding salt-marsh edge cells: read every overlapping tile on a
2 m UTM 15N grid, classify land, and compute each 100 m cell's land fraction and flight date. Also writes
the 2010 open-water fraction within 1 km of each cell (16 m grid), and a quality-check image per year for a
few blocks.

Usage: python scripts/naip_edge_extract.py cells.gpkg out_dir
Source: USDA NAIP via Microsoft Planetary Computer (collection 'naip').
"""
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import planetary_computer as pc
import pystac_client
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from scipy import ndimage
from sklearn.linear_model import LogisticRegression
from shapely.geometry import box, shape

YEARS = [2010, 2013, 2015, 2017]
RES, BLOCK, CELL, COARSE = 2.0, 1000, 100, 16.0
UTM = "EPSG:32615"


def otsu(values: np.ndarray, bins: int = 256, value_range=(-1, 1)) -> float:
    hist, edges = np.histogram(values, bins=bins, range=value_range)
    mids = (edges[:-1] + edges[1:]) / 2
    w0 = np.cumsum(hist); w1 = w0[-1] - w0
    m0 = np.cumsum(hist * mids) / np.maximum(w0, 1)
    m1 = (np.sum(hist * mids) - np.cumsum(hist * mids)) / np.maximum(w1, 1)
    between = w0 * w1 * (m0 - m1) ** 2
    return float(mids[np.argmax(between)])


def ndvi_of(red, nir):
    red = red.astype("float32"); nir = nir.astype("float32")
    with np.errstate(all="ignore"):
        v = (nir - red) / (nir + red)
    v[(red == 0) & (nir == 0)] = np.nan
    return v


def land_of(red, nir, t_ndvi, t_nir):
    """Land = NDVI and near-infrared both at or above their tile thresholds; NaN where no data."""
    v = ndvi_of(red, nir)
    land = ((v >= t_ndvi) & (nir.astype("float32") >= t_nir)).astype("float32")
    land[~np.isfinite(v)] = np.nan
    return land


def features(bands):
    r, g, b, n = (x.astype("float32") for x in bands)
    return np.stack([r, g, b, n, ndvi_of(r, n)], axis=-1)


def classify(bands, tile):
    """Land fraction map (1 land, 0 water, NaN no data) for one tile-year's bands on any grid."""
    if tile.year == 2010:
        land = land_of(bands[0], bands[3], tile.t_ndvi, tile.t_nir)
    else:
        X = features(bands); ok = np.isfinite(X).all(axis=-1) & (bands.sum(axis=0) > 0)
        z = X @ np.asarray(tile.coef) + tile.intercept
        land = (z >= 0).astype("float32"); land[~ok] = np.nan
    return land


def read_on_grid(href, transform, width, height, bands=(1, 2, 3, 4)):
    """Read bands warped onto a UTM grid, from the coarsest internal overview finer than the target cell."""
    target = abs(transform.a)
    for attempt in range(4):
        try:
            with rasterio.open(href) as probe:
                native = abs(probe.transform.a); n_ovr = len(probe.overviews(1))
            level = int(np.floor(np.log2(target / native + 1e-9))) - 1  # overview k has cell native * 2**(k+1)
            level = min(level, n_ovr - 1)
            kwargs = {"overview_level": level} if level >= 0 else {}
            with rasterio.open(href, **kwargs) as src, WarpedVRT(src, crs=UTM, transform=transform, width=width,
                                                               height=height, resampling=Resampling.average, nodata=0) as v:
                return v.read(list(bands))
        except Exception as e:  # transient network errors
            err = e
    raise err


def main(cells_path, out_dir):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    cells = gpd.read_file(cells_path)
    cells = cells[cells.esi_main == "10A"].copy()
    cells["bx"] = (cells.ix * CELL // BLOCK).astype(int); cells["by"] = (cells.iy * CELL // BLOCK).astype(int)
    cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
    bbox = list(cells.to_crs(4326).total_bounds)
    items = [i for i in cat.search(collections=["naip"], bbox=bbox).items() if int(i.properties["naip:year"]) in YEARS]
    tiles = gpd.GeoDataFrame({
        "id": [i.id for i in items], "year": [int(i.properties["naip:year"]) for i in items],
        "date": [i.datetime.date().isoformat() for i in items], "href": [i.assets["image"].href for i in items]},
        geometry=[shape(i.geometry) for i in items], crs=4326).to_crs(32615)
    print("tiles per year:", tiles.year.value_counts().sort_index().to_dict(), flush=True)

    # 1a. 2010: Otsu thresholds per tile (NDVI and near-infrared)
    def threshold(row):
        with rasterio.open(pc.sign(row.href)) as src:
            f = max(1, int(COARSE / abs(src.transform.a)))
            red, nir = src.read([1, 4], out_shape=(2, src.height // f, src.width // f), resampling=Resampling.average)
        v = ndvi_of(red, nir); ok = np.isfinite(v)
        return otsu(v[ok]), otsu(nir[ok].astype("float32"), value_range=(0, 256))
    t10 = tiles[tiles.year == 2010].copy()
    with ThreadPoolExecutor(12) as ex:
        res = list(ex.map(threshold, t10.itertuples()))
    tiles["t_ndvi"] = np.nan; tiles["t_nir"] = np.nan
    tiles.loc[t10.index, "t_ndvi"] = [r[0] for r in res]; tiles.loc[t10.index, "t_nir"] = [r[1] for r in res]
    tiles["quad"] = tiles.id.str[:15]
    tiles["coef"] = None; tiles["intercept"] = np.nan; tiles["train_accuracy"] = np.nan
    tiles["land_share"] = np.nan; tiles["land_share_2010"] = np.nan

    # 1b. later years: classifier trained on 2010 interior land and water of the same quarter-quad
    def train(row):
        base = tiles[(tiles.year == 2010) & (tiles.quad == row.quad)]
        if base.empty:
            return None
        b10 = base.iloc[0]
        x0, y0, x1, y1 = row.geometry.bounds
        T8 = from_origin(x0, y1, 8.0, 8.0); w, h = int((x1 - x0) / 8), int((y1 - y0) / 8)
        land10 = land_of(*read_on_grid(pc.sign(b10.href), T8, w, h, bands=(1, 4)), b10.t_ndvi, b10.t_nir)
        later = read_on_grid(pc.sign(row.href), T8, w, h)
        X = features(later); ok = np.isfinite(X).all(axis=-1) & (later.sum(axis=0) > 0) & np.isfinite(land10)
        inner_land = ndimage.binary_erosion(land10 == 1, iterations=4) & ok
        inner_water = ndimage.binary_erosion(land10 == 0, iterations=4) & ok
        rng = np.random.default_rng(0)
        pick = lambda m: rng.permutation(np.flatnonzero(m))[:20000]  # noqa: E731
        il, iw = pick(inner_land.ravel()), pick(inner_water.ravel())
        if len(il) < 200 or len(iw) < 200:
            return None
        Xs = np.vstack([X.reshape(-1, 5)[il], X.reshape(-1, 5)[iw]]); ys = np.r_[np.ones(len(il)), np.zeros(len(iw))]
        mu, sd = Xs.mean(0), Xs.std(0) + 1e-6
        half = rng.random(len(ys)) < 0.5
        m = LogisticRegression(class_weight="balanced", max_iter=1000).fit((Xs[half] - mu) / sd, ys[half])
        acc = float(m.score((Xs[~half] - mu) / sd, ys[~half]))
        coef = m.coef_[0] / sd; intercept = float(m.intercept_[0] - (m.coef_[0] * mu / sd).sum())
        land = (X @ coef + intercept >= 0).astype("float32"); land[~ok] = np.nan
        return list(coef), intercept, acc, float(np.nanmean(land)), float(np.nanmean(land10))
    later = tiles[tiles.year != 2010]
    with ThreadPoolExecutor(12) as ex:
        res = list(ex.map(train, later.itertuples()))
    for idx, r in zip(later.index, res):
        if r is not None:
            tiles.at[idx, "coef"] = r[0]; tiles.at[idx, "intercept"] = r[1]; tiles.at[idx, "train_accuracy"] = r[2]
            tiles.at[idx, "land_share"] = r[3]; tiles.at[idx, "land_share_2010"] = r[4]
    tiles["usable"] = (tiles.year == 2010) | (tiles.coef.notna() & ((tiles.land_share - tiles.land_share_2010).abs() <= 0.10))
    tiles.drop(columns="geometry").to_csv(out / "tile_classifiers.csv", index=False)
    print(tiles[tiles.year != 2010].groupby("year")[["train_accuracy"]].describe().round(3).to_string(), flush=True)
    print("usable tile-years:", tiles.groupby("year").usable.sum().to_dict(), flush=True)
    print(tiles[~tiles.usable][["id", "train_accuracy", "land_share", "land_share_2010"]].round(3).to_string(), flush=True)
    tiles = tiles[tiles.usable]

    # 2. 2010 open-water fraction within 1 km, on a 16 m grid over all cells
    x0, y0, x1, y1 = cells.total_bounds; x0 -= 1500; y0 -= 1500; x1 += 1500; y1 += 1500
    W, H = int((x1 - x0) / COARSE), int((y1 - y0) / COARSE); T16 = from_origin(x0, y1, COARSE, COARSE)
    land16 = np.full((H, W), np.nan, dtype="float32")
    for row in tiles[tiles.year == 2010].itertuples():
        lv = classify(read_on_grid(pc.sign(row.href), T16, W, H), row)
        ok = np.isfinite(lv) & np.isnan(land16)
        land16[ok] = lv[ok]
    valid = np.isfinite(land16).astype(float); water = np.where(valid > 0, 1 - np.nan_to_num(land16), 0)
    r = int(1000 / COARSE); yy, xx = np.mgrid[-r:r + 1, -r:r + 1]; disk = (xx ** 2 + yy ** 2 <= r * r).astype(float)
    wsum = ndimage.convolve(water, disk, mode="constant"); vsum = ndimage.convolve(valid, disk, mode="constant")
    water1k = np.where(vsum > 0, wsum / np.maximum(vsum, 1), np.nan)
    cx = (cells.ix * CELL + CELL / 2 - x0) / COARSE; cy = (y1 - (cells.iy * CELL + CELL / 2)) / COARSE
    cells["water_1km_2010"] = water1k[cy.astype(int).clip(0, H - 1), cx.astype(int).clip(0, W - 1)]

    # 3. Land fraction per cell, per year, block by block
    n = int(BLOCK / RES); k = int(CELL / RES)
    blocks = cells[["bx", "by"]].drop_duplicates().itertuples(index=False)
    def do_block(b):
        bx, by = b
        T = from_origin(bx * BLOCK, (by + 1) * BLOCK, RES, RES)
        geom = box(bx * BLOCK, by * BLOCK, (bx + 1) * BLOCK, (by + 1) * BLOCK)
        rows = []
        for year in YEARS:
            land = np.full((n, n), np.nan, dtype="float32"); date = np.full((n, n), "", dtype=object)
            for t in tiles[(tiles.year == year) & tiles.intersects(geom)].itertuples():
                lv = classify(read_on_grid(pc.sign(t.href), T, n, n), t)
                ok = np.isfinite(lv) & np.isnan(land)
                land[ok] = lv[ok]; date[ok] = t.date
            block_land = float(np.nanmean(land)) if np.isfinite(land).any() else np.nan
            for c in cells[(cells.bx == bx) & (cells.by == by)].itertuples():
                i0 = int((c.ix * CELL - bx * BLOCK) / RES); j0 = int(((by + 1) * BLOCK - (c.iy + 1) * CELL) / RES)
                sub = land[j0:j0 + k, i0:i0 + k]; ds = date[j0:j0 + k, i0:i0 + k]
                good = np.isfinite(sub)
                d = pd.Series(ds[good]).mode()
                rows.append({"cell": c.cell, "year": year, "land_fraction": float(np.nanmean(sub)) if good.any() else np.nan,
                             "valid_fraction": float(good.mean()), "flight_date": d.iloc[0] if len(d) else None,
                             "block": f"{bx}_{by}", "block_land_fraction": block_land})
            if (bx + by) % 37 == 0:
                np.save(out / f"qa_block_{bx}_{by}_{year}.npy", land)
        return rows
    allrows = []
    blist = list(blocks)
    with ThreadPoolExecutor(12) as ex:
        for i, r in enumerate(ex.map(do_block, blist)):
            allrows += r
            if i % 50 == 0:
                print(f"block {i}/{len(blist)}", flush=True)
    long = pd.DataFrame(allrows)
    long.to_csv(out / "cell_land_by_year.csv", index=False)
    cells.drop(columns="geometry").to_csv(out / "cells_10A.csv", index=False)
    print("done:", len(long), "cell-years", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:3])
