"""Retrieve SSURGO and SoilGrids values at the CRMS site positions (plan: docs/SOIL_LAYER_CHECK_PLAN.md). Cached.

Inputs : data/external/crms_soil/CRMS_Soil_Properties.csv (site list and mean positions from
         validation.soil_layer_check.build_sites)
Outputs: data/external/soil_layers/ssurgo_sites.csv      site, lon, lat, mukey (blank = no map unit at the point)
         data/external/soil_layers/ssurgo_horizons.csv   mukey, cokey, compname, comppct_r, chkey, hzdept_r, hzdepb_r,
                                                          om_r, dbthirdbar_r, ec_r, ph1to1h2o_r (raw SSURGO)
         data/external/soil_layers/soilgrids_raw.csv     site, lon, lat, prop, depth, stat, raw (integer as mapped)
         <cache-dir>/ssurgo_*.json                       every raw SDA response (default: ../soil_cache next to the repo's parent)
A CSV that already exists is reused, so reruns are offline. Delete it to refetch.

SSURGO: Soil Data Access, POST https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest, JSON+COLUMNNAME; sites are batched
        (UNION ALL of the point-intersection function), then horizons are fetched per batch of map units. One call a second.
SoilGrids: ISRIC cloud rasters https://files.isric.org/soilgrids/latest/data/<prop>/<prop>_<depth>_<stat>.vrt read with
        rasterio over /vsicurl/; coordinates transformed to the raster CRS (Interrupted Goode Homolosine) with pyproj.
        The REST fallback of the plan (100 random sites, seed 20261112, about 5 calls a minute) is NOT implemented: not needed
        if the rasters answer.
Run    : python scripts/fetch_soil_layers.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from validation.soil_layer_check import CRMS_CSV, LAYERS, build_sites  # noqa: E402

SDA = "https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest"
SG_BASE = "https://files.isric.org/soilgrids/latest/data"
PROPS = ["bdod", "phh2o", "soc"]
DEPTHS = ["0-5cm", "5-15cm"]
STATS = ["mean", "Q0.05", "Q0.95"]


def sda(query: str, cache: Path, name: str) -> list[list[str]]:
    """POST one query; cache the raw response; return the rows (first row = column names). {} -> []."""
    f = cache / f"{name}.json"
    if f.exists():
        txt = f.read_text()
    else:
        req = urllib.request.Request(SDA, data=json.dumps({"query": query, "format": "JSON+COLUMNNAME"}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:  # proxy and CA bundle come from the environment
            txt = r.read().decode()
        f.write_text(txt)
        time.sleep(1.0)
    j = json.loads(txt) if txt.strip() else {}
    return j.get("Table", [])


def fetch_ssurgo(sites: pd.DataFrame, cache: Path, batch=20) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    rows = []
    for i in range(0, len(sites), batch):
        b = sites.iloc[i:i + batch]
        q = " UNION ALL ".join(
            f"SELECT '{r.site}' AS site, d.mukey FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('POINT({r.lon:.6f} {r.lat:.6f})') d"
            for r in b.itertuples())
        t = sda(q, cache, f"ssurgo_mukeys_{i:04d}")
        got = {x[0]: x[1] for x in t[1:]}
        for r in b.itertuples():
            rows.append({"site": r.site, "lon": round(r.lon, 6), "lat": round(r.lat, 6), "mukey": got.get(r.site, "")})
    sm = pd.DataFrame(rows)
    sm.to_csv(LAYERS / "ssurgo_sites.csv", index=False)
    mu = sorted(set(sm.mukey[sm.mukey != ""]))
    hz = []
    for i in range(0, len(mu), 40):
        ids = ",".join(mu[i:i + 40])
        q = ("SELECT mu.mukey, co.cokey, co.compname, co.comppct_r, ch.chkey, ch.hzdept_r, ch.hzdepb_r, ch.om_r, ch.dbthirdbar_r, "
             "ch.ec_r, ch.ph1to1h2o_r FROM mapunit mu INNER JOIN component co ON co.mukey = mu.mukey "
             f"LEFT JOIN chorizon ch ON ch.cokey = co.cokey WHERE mu.mukey IN ({ids}) ORDER BY mu.mukey, co.cokey, ch.hzdept_r")
        t = sda(q, cache, f"ssurgo_horizons_{i:04d}")
        if t:
            hz.append(pd.DataFrame(t[1:], columns=t[0]))
    (pd.concat(hz) if hz else pd.DataFrame()).to_csv(LAYERS / "ssurgo_horizons.csv", index=False)


def fetch_soilgrids(sites: pd.DataFrame) -> None:
    import rasterio
    from pyproj import Transformer
    ca = os.path.expanduser("~/.ccr/ca-bundle.crt")
    if os.path.exists(ca):
        os.environ.setdefault("GDAL_HTTP_CAINFO", ca)
    out = []
    with rasterio.Env(GDAL_HTTP_MAX_RETRY="3", GDAL_HTTP_RETRY_DELAY="2", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        for prop in PROPS:
            for depth in DEPTHS:
                for stat in STATS:
                    url = f"/vsicurl/{SG_BASE}/{prop}/{prop}_{depth}_{stat}.vrt"
                    with rasterio.open(url) as s:
                        tr = Transformer.from_crs("EPSG:4326", s.crs, always_xy=True)
                        xy = [tr.transform(lo, la) for lo, la in zip(sites.lon, sites.lat)]
                        vals = [v[0] for v in s.sample(xy)]
                        nod = s.nodata
                    for r, v in zip(sites.itertuples(), vals):
                        miss = nod is not None and v == nod
                        out.append({"site": r.site, "lon": round(r.lon, 6), "lat": round(r.lat, 6), "prop": prop, "depth": depth,
                                    "stat": stat, "raw": "" if miss else int(v)})
                    print(f"  {prop} {depth} {stat}: read {len(vals)} points", flush=True)
    pd.DataFrame(out).to_csv(LAYERS / "soilgrids_raw.csv", index=False)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", default=str(ROOT.parent / "soil_cache"), help="raw SDA responses (not committed)")
    a = ap.parse_args()
    LAYERS.mkdir(parents=True, exist_ok=True)
    sites, counts = build_sites(pd.read_csv(CRMS_CSV, encoding="latin-1", low_memory=False))
    print(f"{len(sites)} sites ({counts})")
    if not (LAYERS / "ssurgo_horizons.csv").exists():
        fetch_ssurgo(sites, Path(a.cache_dir))
    else:
        print("SSURGO csv present; skipped")
    if not (LAYERS / "soilgrids_raw.csv").exists():
        fetch_soilgrids(sites)
    else:
        print("SoilGrids csv present; skipped")


if __name__ == "__main__":
    main()
