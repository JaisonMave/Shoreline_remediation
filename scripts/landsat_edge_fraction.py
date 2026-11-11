"""Landsat land fraction per edge cell for three epochs (P1, docs/P1_PRESPILL_CHECK_PLAN.md).

Per scene (Landsat C2 L2, April-October, cloud < 30%, Microsoft Planetary Computer):
  SWIR1 surface reflectance on a 30 m UTM 15N grid; clouds, shadows, snow removed with QA_PIXEL;
  land fraction = (SWIR1 - water value) / (marsh value - water value), clipped 0-1, where the two values are
  medians over that scene's clear pixels more than 60 m inside 2010 water / 2010 land (2010 NAIP mosaic).
Per epoch: per-pixel median over scenes (pixel needs >= 5 clear scenes, ASSUMED), then each 100 m cell's mean,
computed by warping to 10 m (nearest) and averaging; a cell needs >= 90% valid area.
Writes landsat_cell_fraction.csv (cell, epoch, land_fraction, valid_fraction, n_scenes_median),
scene_endmembers.csv, and per-epoch median rasters for the quality check.
Usage: python scripts/landsat_edge_fraction.py cells_10A.csv naip2010_land16.tif out_dir [--epochs AB]
"""
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import planetary_computer as pc
import pystac_client
import rasterio
import rasterio.warp
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from scipy import ndimage

EPOCHS = {"A": ("1998-01-01/2000-12-31", "landsat-5"),
          "B": ("2007-01-01/2009-12-31", "landsat-5"),
          "C": ("2014-01-01/2016-12-31", "landsat-8")}
RES, CELL, MIN_SCENES, MIN_ENDMEMBER = 30.0, 100, 5, 500
UTM = "EPSG:32615"


def grid_for(cells):
    x0 = cells.ix.min() * CELL - 300; x1 = (cells.ix.max() + 1) * CELL + 300
    y0 = cells.iy.min() * CELL - 300; y1 = (cells.iy.max() + 1) * CELL + 300
    return from_origin(x0, y1, RES, RES), int(np.ceil((x1 - x0) / RES)), int(np.ceil((y1 - y0) / RES)), (x0, y0, x1, y1)


def warp(href, T, W, H, resampling=Resampling.nearest, nodata=None):
    for attempt in range(4):
        try:
            with rasterio.open(href) as src, WarpedVRT(src, crs=UTM, transform=T, width=W, height=H,
                                                     resampling=resampling, nodata=nodata if nodata is not None else src.nodata) as v:
                return v.read(1)
        except Exception as e:
            err = e
    raise err


def main(cells_path, land16_path, out_dir):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    cells = pd.read_csv(cells_path)
    T, W, H, bounds = grid_for(cells)
    # 2010 land fraction on the 30 m grid, then interior masks (2 pixels = 60 m inside)
    land30 = warp(land16_path, T, W, H, resampling=Resampling.average, nodata=np.nan)
    inner_land = ndimage.binary_erosion(land30 >= 0.999, iterations=2)
    inner_water = ndimage.binary_erosion(land30 <= 0.001, iterations=2)
    print("interior pixels land/water:", int(inner_land.sum()), int(inner_water.sum()), flush=True)
    ll = rasterio.warp.transform_bounds(UTM, "EPSG:4326", *bounds)
    cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")

    def scene_fraction(item):
        swir = warp(pc.sign(item.assets["swir16"].href), T, W, H).astype("float32")
        qa = warp(pc.sign(item.assets["qa_pixel"].href), T, W, H)
        clear = (swir > 0) & (qa > 1) & ((qa & 0b111010) == 0)
        s = swir * 2.75e-5 - 0.2
        wl, ww = inner_land & clear, inner_water & clear
        if wl.sum() < MIN_ENDMEMBER or ww.sum() < MIN_ENDMEMBER:
            return None, {"scene": item.id, "used": False}
        lv, wv = float(np.median(s[wl])), float(np.median(s[ww]))
        if lv - wv < 0.02:  # no usable contrast (ASSUMED floor)
            return None, {"scene": item.id, "used": False, "land_value": lv, "water_value": wv}
        f = np.clip((s - wv) / (lv - wv), 0, 1).astype("float32"); f[~clear] = np.nan
        return f, {"scene": item.id, "used": True, "land_value": lv, "water_value": wv,
                   "clear_share": float(clear.mean()), "date": item.datetime.date().isoformat()}

    rows, endm = [], []
    for epoch, (dt, platform) in EPOCHS.items():
        items = [i for i in cat.search(collections=["landsat-c2-l2"], bbox=list(ll), datetime=dt,
                                       query={"eo:cloud_cover": {"lt": 30}, "platform": {"eq": platform}}).items()
                 if 4 <= i.datetime.month <= 10]
        with ThreadPoolExecutor(6) as ex:
            res = list(ex.map(scene_fraction, items))
        stack = [f for f, _ in res if f is not None]
        endm += [dict(m, epoch=epoch) for _, m in res]
        stack = np.stack(stack)
        n = np.isfinite(stack).sum(axis=0)
        with np.errstate(all="ignore"):
            med = np.nanmedian(stack, axis=0)
        med[n < MIN_SCENES] = np.nan
        del stack
        np.save(out / f"median_fraction_{epoch}.npy", med)
        print(f"epoch {epoch}: {len(items)} scenes, {sum(f is not None for f, _ in res)} used", flush=True)
        # cell means: 30 m -> 10 m nearest, then 10 x 10 blocks aligned to the 100 m cell grid
        x0, y1 = T.c, T.f
        for c in cells.itertuples():
            cx0, cy1 = c.ix * CELL, (c.iy + 1) * CELL
            j0 = (y1 - cy1) / RES; i0 = (cx0 - x0) / RES
            ys = (j0 + (np.arange(10) + 0.5) / 10 * (CELL / RES)).astype(int)
            xs = (i0 + (np.arange(10) + 0.5) / 10 * (CELL / RES)).astype(int)
            sub = med[np.ix_(ys, xs)]
            good = np.isfinite(sub)
            rows.append({"cell": c.cell, "epoch": epoch, "land_fraction": float(np.nanmean(sub)) if good.any() else np.nan,
                         "valid_fraction": float(good.mean()),
                         "n_scenes_median": float(np.median(n[np.ix_(ys, xs)]))})
    pd.DataFrame(rows).to_csv(out / "landsat_cell_fraction.csv", index=False)
    pd.DataFrame(endm).to_csv(out / "scene_endmembers.csv", index=False)
    print("done", len(rows), flush=True)


if __name__ == "__main__":
    if "--epochs" in sys.argv:
        keep = sys.argv[sys.argv.index("--epochs") + 1]
        for k in list(EPOCHS):
            if k not in keep:
                del EPOCHS[k]
    main(*sys.argv[1:4])
