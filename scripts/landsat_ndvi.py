"""Landsat Collection 2 Level-2 NDVI for SCAT-selected sites, via Microsoft Planetary Computer.
Pass 1: per-pixel median NDVI from May-Oct 2008-2009 (pre-spill) -> marsh mask (ASSUMED threshold 0.3).
Pass 2: per-scene mean NDVI over masked site pixels; keep a scene for a site if >= 50% (ASSUMED) of
its masked pixels are clear. Clear = QA_PIXEL bits 1 (dilated cloud), 3 (cloud), 4 (shadow), 5 (snow) off.
All rasters are warped to one 30 m UTM 15N grid."""
import sys, numpy as np, pandas as pd, geopandas as gpd, rasterio, pystac_client, planetary_computer as pc
from rasterio.vrt import WarpedVRT; from rasterio.enums import Resampling
from rasterio.features import rasterize; from rasterio.transform import from_origin
from concurrent.futures import ThreadPoolExecutor
sites_path, out_csv, mask_npy = sys.argv[1:4]
sites = gpd.read_file(sites_path).to_crs(32615)
x0, y0, x1, y1 = sites.total_bounds; x0 = np.floor(x0/30)*30-60; y1 = np.ceil(y1/30)*30+60
W = int(np.ceil((x1-x0)/30))+4; H = int(np.ceil((y1-y0)/30))+4
T = from_origin(x0, y1, 30, 30)
labels = {}
for k, r in enumerate(sites.itertuples()):
    labels[k] = (r.pair, r.group, r.segment)
site_masks = [rasterize([(r.geometry, 1)], out_shape=(H, W), transform=T, dtype="uint8", all_touched=False).astype(bool)
              for r in sites.itertuples()]
cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=pc.sign_inplace)
bbox = list(sites.to_crs(4326).total_bounds)
def search(dt): return list(cat.search(collections=["landsat-c2-l2"], bbox=bbox, datetime=dt,
                                       query={"eo:cloud_cover": {"lt": 70}, "platform": {"in": ["landsat-5","landsat-7","landsat-8"]}}).items())
def read(href):
    for attempt in range(3):
        try:
            with rasterio.open(pc.sign(href)) as src, WarpedVRT(src, crs="EPSG:32615", transform=T, width=W, height=H,
                                                    resampling=Resampling.nearest, nodata=0) as v:
                return v.read(1)
        except Exception as e:
            err = e
    raise err
def ndvi(item):
    try:
        red, nir, qa = (read(item.assets[b].href) for b in ("red", "nir08", "qa_pixel"))
    except Exception as e:
        print("skip", item.id, str(e)[:80], flush=True); return None
    ok = (red > 0) & (nir > 0) & (qa > 1) & ((qa & 0b111010) == 0)
    r = red*2.75e-5-0.2; n = nir*2.75e-5-0.2
    with np.errstate(all="ignore"): v = (n-r)/(n+r)
    v[~ok] = np.nan; return v
# Pass 1
pre = [i for i in search("2008-05-01/2009-10-31") if 5 <= int(i.datetime.month) <= 10]
print("pre-spill scenes:", len(pre), flush=True)
with ThreadPoolExecutor(12) as ex: stack = [a for a in ex.map(ndvi, pre) if a is not None]
with np.errstate(all="ignore"): med = np.nanmedian(np.stack(stack), axis=0)
marsh = med >= 0.3; np.save(mask_npy, med)
for k, sm in enumerate(site_masks):
    sm &= marsh
print("masked pixels per site:", sorted(int(s.sum()) for s in site_masks), flush=True)
# Pass 2
items = search("2006-01-01/2016-12-31"); print("all scenes:", len(items), flush=True)
def per_scene(item):
    v = ndvi(item)
    if v is None: return []
    out = []
    for k, sm in enumerate(site_masks):
        n = int(sm.sum())
        if n == 0: continue
        vals = v[sm]; good = np.isfinite(vals)
        if good.sum() < 0.5*n: continue
        p, g, s = labels[k]
        out.append({"date": item.datetime.date().isoformat(), "pair": p, "group": g, "segment": s,
                    "ndvi": float(np.nanmean(vals)), "n_pixels": int(good.sum()), "n_site_pixels": n,
                    "platform": item.properties["platform"], "scene": item.id})
    return out
rows = []
with ThreadPoolExecutor(12) as ex:
    for i, r in enumerate(ex.map(per_scene, items)):
        rows += r
        if i % 100 == 0: print(i, len(rows), flush=True)
pd.DataFrame(rows).sort_values(["date","pair","group"]).to_csv(out_csv, index=False)
print("rows", len(rows))
