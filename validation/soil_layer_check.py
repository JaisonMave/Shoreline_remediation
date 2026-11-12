"""Do SSURGO and SoilGrids match measured Louisiana marsh soil? (plan: docs/SOIL_LAYER_CHECK_PLAN.md). Run once.

Unit of analysis: the CRMS site (first 8 characters of Station ID), never the core or depth slice.
Site value  = mean over all cores and dates of the depth slices whose top is shallower than 16 cm (ASSUMED to
              match the maps' 0 to 15 cm). Site position = mean of the cores' coordinates.
SSURGO      = horizons clipped to 0-15 cm, thickness-weighted within each component (over horizons with a value),
              then weighted by component percent over components with a value.
SoilGrids   = 0-5 cm and 5-15 cm layers weighted 1:2 (mean, Q0.05, Q0.95 each). Raw integers are converted with the
              d_factors in the service response: bdod /100 (g/cm3), phh2o /10, soc /10 (g/kg); OM % = soc g/kg x 1.724 / 10
              (1.724 ASSUMED).
Statistics per variable x product x scope (all sites / P5 box): n, missing, baseline MAE (median of measured), bias,
MAE, RMSE, Spearman, Lin's CCC, MAE minus baseline MAE, SoilGrids Q0.05-Q0.95 coverage; 90% percentile intervals
from 2,000 bootstrap resamples of sites (seed 20261112; the baseline median is recomputed inside each resample).
Salinity (SSURGO ec_r saturated paste vs CRMS field conductance): rank agreement only.
Verdict (thresholds ASSUMED, fixed in the plan): usable if Spearman >= 0.5 with lower bound > 0.3 AND the MAE
difference interval is entirely below zero; weak if the Spearman lower bound > 0; otherwise not usable.

Inputs : data/external/crms_soil/CRMS_Soil_Properties.csv, data/external/soil_layers/{ssurgo_sites,ssurgo_horizons,
         soilgrids_raw}.csv (written by scripts/fetch_soil_layers.py)
Run    : python -m validation.soil_layer_check
Writes : results/soil_layer_check/agreement.csv and summary.txt
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CRMS_CSV = ROOT / "data" / "external" / "crms_soil" / "CRMS_Soil_Properties.csv"
LAYERS = ROOT / "data" / "external" / "soil_layers"
RESULTS = ROOT / "results" / "soil_layer_check"
SEED, N_BOOT = 20261112, 2000
SLICE_TOP_MAX_CM = 16.0  # CRMS slices with top shallower than this (plan)
MAP_DEPTH_CM = 15.0       # map products' depth (plan)
OM_FACTOR = 1.724         # ASSUMED van Bemmelen factor
P5_BOX = dict(lat=(29.05, 30.32), lon=(-91.14, -89.38))

COLS = {"station": "Station ID", "depth": "Sample Depth (cm)", "ph": "Wet Soil pH (pH units)",
        "cond": "Soil Specific Conductance (uS/cm)", "bd": "Bulk Density (g/cm3)", "om": "Organic Matter (%)",
        "lat": "Latitude", "lon": "Longitude"}
MEASURED = ["bd", "om", "ph", "sal"]

# (variable, product, ssurgo column / soilgrids property, measured column, unit)
COMPARISONS = [
    ("bulk_density_g_cm3", "ssurgo", "dbthirdbar_r", "bd"),
    ("bulk_density_g_cm3", "soilgrids", "bdod", "bd"),
    ("om_pct", "ssurgo", "om_r", "om"),
    ("om_pct", "soilgrids", "soc", "om"),
    ("soc_g_kg", "soilgrids", "soc", "soc"),
    ("ph", "ssurgo", "ph1to1h2o_r", "ph"),
    ("ph", "soilgrids", "phh2o", "ph"),
    ("salinity_dS_m", "ssurgo", "ec_r", "sal"),
]
RANK_ONLY = {"salinity_dS_m"}


# ------------------------------------------------------------------ site table
def parse_depth(s) -> tuple[float, float] | None:
    """'0 to 4' -> (0.0, 4.0); None if it cannot be parsed."""
    try:
        a, b = str(s).split(" to ")
        return float(a), float(b)
    except (ValueError, TypeError):
        return None


def build_sites(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Site table (one row per CRMS site) from the raw CRMS rows, and the counts of sites dropped at each step.

    Columns: site, lat, lon, n_slices, bd, om, ph, sal (dS/m = uS/cm / 1000), soc (g/kg = OM % / 1.724 x 10).
    A site value is NaN if no kept slice has that variable.
    """
    d = pd.DataFrame({"station": raw[COLS["station"]].astype(str), "lat": pd.to_numeric(raw[COLS["lat"]], errors="coerce"),
                      "lon": pd.to_numeric(raw[COLS["lon"]], errors="coerce"), "depth": raw[COLS["depth"]]})
    for k in ("bd", "om", "ph"):
        d[k] = pd.to_numeric(raw[COLS[k]], errors="coerce")
    d["sal"] = pd.to_numeric(raw[COLS["cond"]], errors="coerce") / 1000.0
    d["site"] = d.station.str[:8]
    tb = d.depth.map(parse_depth)
    d["top"] = tb.map(lambda t: t[0] if t else np.nan)
    counts = {"rows": len(d), "sites_all": int(d.site.nunique())}
    # position: mean over the site's distinct cores (stations)
    pos = d.dropna(subset=["lat", "lon"]).drop_duplicates(["station", "lat", "lon"]).groupby("site")[["lat", "lon"]].mean()
    shallow = d[d.top < SLICE_TOP_MAX_CM]
    sites_shallow = set(shallow.site)
    counts["dropped_no_slice_shallower_than_16cm"] = counts["sites_all"] - len(sites_shallow)
    has_pos = set(pos.index)
    counts["dropped_no_coordinates"] = len(sites_shallow - has_pos)
    keep = sorted(sites_shallow & has_pos)
    g = shallow[shallow.site.isin(keep)].groupby("site")
    out = g[["bd", "om", "ph", "sal"]].mean()
    out["n_slices"] = g.size()
    out = out.join(pos, how="left")
    out["soc"] = out["om"] / OM_FACTOR * 10.0
    out = out.reset_index()[["site", "lat", "lon", "n_slices", "bd", "om", "ph", "sal", "soc"]]
    counts["sites_kept"] = len(out)
    return out, counts


def in_p5_box(sites: pd.DataFrame) -> pd.Series:
    return sites.lat.between(*P5_BOX["lat"]) & sites.lon.between(*P5_BOX["lon"])


# ------------------------------------------------------------------ map products to site values
def clipped_weighted_mean(top, bot, val, limit=MAP_DEPTH_CM) -> float:
    """Thickness-weighted mean of val over horizons clipped to 0..limit cm; horizons with no value or no
    overlap are skipped. NaN if nothing remains."""
    top, bot, val = (np.asarray(a, float) for a in (top, bot, val))
    th = np.clip(np.minimum(bot, limit) - np.maximum(top, 0.0), 0.0, None)
    ok = (th > 0) & ~np.isnan(val)
    return float(np.sum(th[ok] * val[ok]) / np.sum(th[ok])) if ok.any() else float("nan")


def ssurgo_value(hz: pd.DataFrame, col: str) -> float:
    """Component-percent-weighted mean (over components with a value) of the clipped, thickness-weighted
    horizon mean. hz: rows of one map unit with cokey, comppct_r, hzdept_r, hzdepb_r and col."""
    vals, pct = [], []
    for _, c in hz.groupby("cokey"):
        v = clipped_weighted_mean(c.hzdept_r, c.hzdepb_r, c[col])
        if not np.isnan(v):
            vals.append(v); pct.append(float(c.comppct_r.iloc[0]))
    return float(np.average(vals, weights=pct)) if vals and sum(pct) > 0 else float("nan")


def ssurgo_site_values(sites_map: pd.DataFrame, horizons: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (values, reasons). values: site x [om_r, dbthirdbar_r, ec_r, ph1to1h2o_r]; reasons: site x same,
    'ok' | 'no_unit' (no map unit at the point) | 'no_value' (map unit without a value in 0-15 cm)."""
    cols = ["om_r", "dbthirdbar_r", "ec_r", "ph1to1h2o_r"]
    h = horizons.copy()
    for c in ["comppct_r", "hzdept_r", "hzdepb_r"] + cols:
        h[c] = pd.to_numeric(h[c], errors="coerce")
    h["mukey"] = h["mukey"].astype(str)
    by_mu = {k: g for k, g in h.groupby("mukey")}
    cache = {}
    rows, why = [], []
    for r in sites_map.itertuples():
        mk = None if pd.isna(r.mukey) or str(r.mukey).strip() == "" else str(r.mukey).strip()
        v, w = {"site": r.site}, {"site": r.site}
        for c in cols:
            if mk is None:
                v[c], w[c] = np.nan, "no_unit"
                continue
            if (mk, c) not in cache:
                cache[(mk, c)] = ssurgo_value(by_mu[mk], c) if mk in by_mu else float("nan")
            v[c] = cache[(mk, c)]
            w[c] = "ok" if not np.isnan(v[c]) else "no_value"
        rows.append(v); why.append(w)
    return pd.DataFrame(rows), pd.DataFrame(why)


SG_SCALE = {"bdod": 1 / 100.0, "phh2o": 1 / 10.0, "soc": 1 / 10.0}  # d_factors from the service response -> g/cm3, pH, g/kg


def soilgrids_site_values(raw: pd.DataFrame) -> pd.DataFrame:
    """raw: site, prop, depth ('0-5cm'|'5-15cm'), stat ('mean'|'Q0.05'|'Q0.95'), raw (integer or NaN).
    Returns site x {prop}_{stat} with 0-5 and 5-15 cm weighted 1:2 (NaN if either layer is missing), converted to
    bdod g/cm3, phh2o pH, soc g/kg. Also adds om_{stat} (% OM, factor 1.724 ASSUMED)."""
    r = raw.copy()
    r["raw"] = pd.to_numeric(r["raw"], errors="coerce")
    r["v"] = r["raw"] * r["prop"].map(SG_SCALE)
    p = r.pivot_table(index=["site", "prop", "stat"], columns="depth", values="v", aggfunc="first", dropna=False)
    p["w"] = (p["0-5cm"] * 5 + p["5-15cm"] * 10) / 15.0  # 1:2; NaN if either layer is missing
    w = p["w"].unstack(["prop", "stat"])
    w.columns = [f"{a}_{b}" for a, b in w.columns]
    for s in ("mean", "Q0.05", "Q0.95"):
        if f"soc_{s}" in w:
            w[f"om_{s}"] = w[f"soc_{s}"] * OM_FACTOR / 10.0
    return w.reset_index()


# ------------------------------------------------------------------ statistics
def lin_ccc(x, y, axis=-1) -> np.ndarray:
    """Lin's concordance correlation coefficient (population variances)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    mx, my = x.mean(axis=axis), y.mean(axis=axis)
    vx, vy = x.var(axis=axis), y.var(axis=axis)
    cov = ((x - np.expand_dims(mx, axis)) * (y - np.expand_dims(my, axis))).mean(axis=axis)
    with np.errstate(divide="ignore", invalid="ignore"):
        return 2 * cov / (vx + vy + (mx - my) ** 2)


def spearman(x, y) -> np.ndarray:
    """Spearman rho along the last axis (average ranks for ties); NaN if either side is constant."""
    rx, ry = rankdata(x, axis=-1), rankdata(y, axis=-1)
    rx = rx - rx.mean(-1, keepdims=True); ry = ry - ry.mean(-1, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        return (rx * ry).sum(-1) / np.sqrt((rx ** 2).sum(-1) * (ry ** 2).sum(-1))


def stat_arrays(x, y, inside=None) -> dict:
    """x measured, y map; arrays of shape (B, n) (B=1 for the point estimate). Baseline = median of x."""
    med = np.median(x, axis=-1, keepdims=True)
    e = y - x
    mae = np.abs(e).mean(-1)
    base = np.abs(x - med).mean(-1)
    out = {"baseline_mae": base, "bias": e.mean(-1), "mae": mae, "rmse": np.sqrt((e ** 2).mean(-1)),
           "spearman": spearman(x, y), "ccc": lin_ccc(x, y), "mae_diff_vs_baseline": mae - base}
    if inside is not None:
        out["coverage_q05_q95"] = inside.mean(-1)
    return out


def bootstrap_stats(x, y, inside=None, n_boot=N_BOOT, seed=SEED) -> dict:
    """{stat: (estimate, lo, hi)} with 90% percentile intervals; resamples are of sites (pairs)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    ins = None if inside is None else np.asarray(inside, float)
    est = stat_arrays(x[None], y[None], None if ins is None else ins[None])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n_boot, len(x)))
    bs = stat_arrays(x[idx], y[idx], None if ins is None else ins[idx])
    return {k: (float(est[k][0]), float(np.nanpercentile(bs[k], 5)), float(np.nanpercentile(bs[k], 95))) for k in est}


def verdict(spearman_est, spearman_lo, diff_hi) -> str:
    """Plan's pre-specified reading."""
    if np.isnan(spearman_est) or np.isnan(spearman_lo):
        return "Not usable in marsh"
    if spearman_est >= 0.5 and spearman_lo > 0.3 and not np.isnan(diff_hi) and diff_hi < 0:
        return "Usable as a predictor where no core exists"
    if spearman_lo > 0:
        return "Weak: ranks sites roughly; do not use the values"
    return "Not usable in marsh"


def compare(meas, mapv, inside=None, rank_only=False, n_boot=N_BOOT, seed=SEED) -> dict:
    """Statistics and verdict for one variable x product over sites with both values. Returns a flat dict.
    rank_only: only n and Spearman (with interval) are reported, and no verdict is assigned."""
    meas, mapv = np.asarray(meas, float), np.asarray(mapv, float)
    ok = ~np.isnan(meas) & ~np.isnan(mapv)
    if inside is not None:
        ok &= ~np.isnan(np.asarray(inside, float))
    x, y = meas[ok], mapv[ok]
    ins = None if inside is None else np.asarray(inside, float)[ok]
    row = {"n": int(ok.sum())}
    if ok.sum() < 5:
        row["verdict"] = "not assessed (fewer than 5 sites)"
        return row
    s = bootstrap_stats(x, y, ins, n_boot, seed)
    keep = ["spearman"] if rank_only else list(s)
    for k in keep:
        row[k], row[k + "_lo"], row[k + "_hi"] = s[k]
    row["verdict"] = "rank agreement only (no verdict in plan)" if rank_only else verdict(
        s["spearman"][0], s["spearman"][1], s["mae_diff_vs_baseline"][2])
    return row


# ------------------------------------------------------------------ the real comparison
def assemble(sites, ss_vals, ss_why, sg_vals) -> pd.DataFrame:
    """One row per site with measured, SSURGO and SoilGrids values and the SSURGO missing reasons."""
    d = sites.copy()
    s = ss_vals.rename(columns={"om_r": "ssurgo_om", "dbthirdbar_r": "ssurgo_bd", "ec_r": "ssurgo_sal", "ph1to1h2o_r": "ssurgo_ph"})
    w = ss_why.rename(columns={"om_r": "why_ssurgo_om", "dbthirdbar_r": "why_ssurgo_bd", "ec_r": "why_ssurgo_sal",
                               "ph1to1h2o_r": "why_ssurgo_ph"})
    d = d.merge(s, on="site", how="left").merge(w, on="site", how="left").merge(sg_vals, on="site", how="left")
    return d


def run(sites, ss_vals, ss_why, sg_vals, n_boot=N_BOOT, seed=SEED) -> tuple[pd.DataFrame, dict]:
    d = assemble(sites, ss_vals, ss_why, sg_vals)
    d["p5_box"] = in_p5_box(d)
    short = {"dbthirdbar_r": "bd", "om_r": "om", "ec_r": "sal", "ph1to1h2o_r": "ph"}
    sg_short = {"bdod": "bdod", "phh2o": "phh2o", "soc": "soc"}
    rows = []
    for var, prod, src, mcol in COMPARISONS:
        for scope, mask in (("all_sites", np.ones(len(d), bool)), ("P5_box", d.p5_box.to_numpy())):
            sub = d[mask]
            meas = sub[mcol].to_numpy(float)
            inside = None
            if prod == "ssurgo":
                mp = sub[f"ssurgo_{short[src]}"].to_numpy(float)
                why = sub[f"why_ssurgo_{short[src]}"]
                n_nounit = int(((why == "no_unit") & ~np.isnan(meas)).sum())
                n_noval = int(((why == "no_value") & ~np.isnan(meas)).sum())
            else:
                key = "om" if var == "om_pct" else src
                mp = sub[f"{key}_mean"].to_numpy(float)
                if var == "soc_g_kg":
                    mp = sub["soc_mean"].to_numpy(float)
                lo, hi = sub[f"{key}_Q0.05"].to_numpy(float), sub[f"{key}_Q0.95"].to_numpy(float)
                inside = ((meas >= lo) & (meas <= hi)).astype(float)
                inside[np.isnan(lo) | np.isnan(hi) | np.isnan(meas)] = np.nan
                n_nounit, n_noval = int((np.isnan(mp) & ~np.isnan(meas)).sum()), 0
            n_meas_missing = int(np.isnan(meas).sum())
            r = {"variable": var, "product": prod, "scope": scope, "n_sites_in_scope": int(len(sub)),
                 "n_measured_missing": n_meas_missing, "n_map_no_unit_or_nodata": n_nounit, "n_map_no_value": n_noval}
            both = ~np.isnan(meas) & ~np.isnan(mp)
            ins = None if inside is None else inside
            r.update(compare(meas, mp, ins if ins is None else np.where(both, ins, np.nan), var in RANK_ONLY, n_boot, seed))
            rows.append(r)
    out = pd.DataFrame(rows)
    front = ["variable", "product", "scope", "n_sites_in_scope", "n_measured_missing", "n_map_no_unit_or_nodata",
             "n_map_no_value", "n"]
    stats = [f"{k}{s}" for k in ("baseline_mae", "bias", "mae", "rmse", "spearman", "ccc", "mae_diff_vs_baseline",
                                 "coverage_q05_q95") for s in ("", "_lo", "_hi")]
    return out.reindex(columns=front + stats + ["verdict"]), {"assembled": d}


def fmt(r, k, nd=3) -> str:
    v = r.get(k)
    if v is None or pd.isna(v):
        return "n/a"
    return f"{v:.{nd}f} [{r[k + '_lo']:.{nd}f}, {r[k + '_hi']:.{nd}f}]" if (k + "_lo") in r and not pd.isna(r.get(k + "_lo")) else f"{v:.{nd}f}"


def write_summary(path: Path, res: pd.DataFrame, counts: dict, extra: dict) -> None:
    L = ["Soil-layer check: do SSURGO and SoilGrids match CRMS marsh soil? (docs/SOIL_LAYER_CHECK_PLAN.md; run once)", "",
         f"SoilGrids route: {extra['route']}", "",
         "Sites dropped at each step",
         f"  CRMS rows read: {counts['rows']}; CRMS sites (first 8 characters of Station ID): {counts['sites_all']}",
         f"  dropped, no depth slice with top shallower than 16 cm: {counts['dropped_no_slice_shallower_than_16cm']}",
         f"  dropped, no coordinates: {counts['dropped_no_coordinates']}",
         f"  sites kept: {counts['sites_kept']} (of which inside the P5 box: {extra['n_p5']})"]
    L += [f"  {k}" for k in extra.get("notes", [])]
    L += ["", "Verdicts and numbers (90% bootstrap intervals over sites, 2,000 resamples, seed 20261112, in square brackets).",
          "Baseline = median measured value of the sites compared. Bias = map minus measured. Salinity: rank agreement only.", ""]
    for scope in ("all_sites", "P5_box"):
        L.append(f"== Scope: {scope} ==")
        for r in res[res.scope == scope].to_dict("records"):
            L.append(f"{r['variable']} | {r['product']}: n={r['n']} (scope {r['n_sites_in_scope']}; measured missing {r['n_measured_missing']}; "
                     f"map no unit/no data {r['n_map_no_unit_or_nodata']}; map unit without value {r['n_map_no_value']})")
            L.append(f"    VERDICT: {r['verdict']}")
            if r["variable"] in RANK_ONLY:
                L.append(f"    Spearman {fmt(r, 'spearman')}")
                continue
            if r["n"] < 5:
                continue
            L.append(f"    Spearman {fmt(r, 'spearman')}; Lin CCC {fmt(r, 'ccc')}")
            L.append(f"    baseline MAE {fmt(r, 'baseline_mae')}; map MAE {fmt(r, 'mae')}; MAE difference (map - baseline) {fmt(r, 'mae_diff_vs_baseline')}")
            L.append(f"    bias {fmt(r, 'bias')}; RMSE {fmt(r, 'rmse')}"
                     + (f"; share of measured values inside SoilGrids Q0.05-Q0.95 {fmt(r, 'coverage_q05_q95')}"
                        if not pd.isna(r.get("coverage_q05_q95")) else ""))
        L.append("")
    L += ["Notes", *extra.get("footer", [])]
    path.write_text("\n".join(L) + "\n")


def main() -> None:
    raw = pd.read_csv(CRMS_CSV, encoding="latin-1", low_memory=False)
    sites, counts = build_sites(raw)
    sm = pd.read_csv(LAYERS / "ssurgo_sites.csv", dtype=str)
    hz = pd.read_csv(LAYERS / "ssurgo_horizons.csv", dtype=str)
    sg = pd.read_csv(LAYERS / "soilgrids_raw.csv")
    sm = sm[sm.site.isin(sites.site)]
    ss_vals, ss_why = ssurgo_site_values(sm.drop_duplicates("site"), hz)
    sg_vals = soilgrids_site_values(sg[sg.site.isin(sites.site)])
    res, aux = run(sites, ss_vals, ss_why, sg_vals)
    RESULTS.mkdir(parents=True, exist_ok=True)
    res.to_csv(RESULTS / "agreement.csv", index=False, float_format="%.6g")
    d = aux["assembled"]
    n_sg = int(d.bdod_mean.notna().sum()) if "bdod_mean" in d else 0
    extra = {"route": "ISRIC cloud rasters (files.isric.org VRT read with rasterio; site coordinates transformed to Interrupted Goode "
                      "Homolosine with pyproj)", "n_p5": int(in_p5_box(sites).sum()),
             "notes": [f"sites with a SoilGrids raster value for bdod: {n_sg}",
                       f"sites with a SSURGO map unit at the point: {int((ss_why.om_r != 'no_unit').sum())}"],
             "footer": ["SoilGrids Q0.05/Q0.95 layers are combined 1:2 like the means (average of quantiles; ASSUMED approximation).",
                        "soc_g_kg row: measured SOC = CRMS OM / 1.724 x 10; because the same factor is applied to both sides, its Spearman and CCC "
                        "equal those of the om_pct row and its errors differ only by the scale factor.",
                        "No model fitted; no map value recalibrated to CRMS."]}
    write_summary(RESULTS / "summary.txt", res, counts, extra)
    print(f"wrote {RESULTS / 'agreement.csv'} ({len(res)} rows) and summary.txt")


if __name__ == "__main__":
    main()
