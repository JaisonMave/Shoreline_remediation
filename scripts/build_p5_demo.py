"""Build the P5 demo artefacts (plan: docs/P5_DEMO_PLAN.md). Rerun after any change to data/external/p2.

Run:  python scripts/build_p5_demo.py
Needs the analysis requirements (statsmodels). Writes:
    models/p5_edge_loss_v1.json   deployed edge-loss model (P2's M1 on all valid cells) with 90% interval offsets
    data/demo/p5_sites.csv        every Louisiana SCAT edge cell with inputs, scope status, observed rate and the
                                  P2 held-out prediction where one exists
    docs/P5_WORKED_EXAMPLE.md     worked Barataria example chosen by the plan's rule (section 5)
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from validation.p2_basin_holdout import AGREE, BASINS, EXPOSURE, MID_A, MID_B, load_basin  # noqa: E402

P2 = ROOT / "data" / "external" / "p2"
MODEL = ROOT / "models" / "p5_edge_loss_v1.json"
SITES = ROOT / "data" / "demo" / "p5_sites.csv"
EXAMPLE = ROOT / "docs" / "P5_WORKED_EXAMPLE.md"
ZENGEL = ROOT / "data" / "external" / "zengel2022" / "zengel2022_griidc_erosion.xlsx"
FETCH_OFFSET = 16.0  # as in validation.p2_basin_holdout.load_basin
RAW = ["water_1km_2010", "water_250m_2010", "fetch_mean_m", "pre_rate"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fit_m1(d: pd.DataFrame):
    return sm.OLS(d.rate.values, sm.add_constant(d[EXPOSURE].astype(float), has_constant="add")).fit()


def predict(m, d: pd.DataFrame) -> np.ndarray:
    return m.predict(sm.add_constant(d[EXPOSURE].astype(float), has_constant="add")).values


def basin_status(basin: str) -> pd.DataFrame:
    """Every 10A cell in a basin folder with its inputs and the first filter it fails (mirrors cell_rates/load_basin)."""
    d = P2 / basin
    cells = pd.read_csv(d / "cells_10A.csv")[["cell", "water_1km_2010"]]
    ex = pd.read_csv(d / "exposure.csv")
    land = pd.read_csv(d / "cell_land_by_year.csv")
    a = land[land.year == 2010].set_index("cell"); b = land[land.year == 2015].set_index("cell")
    ls = pd.read_csv(d / "landsat_cell_fraction.csv")
    lsv = ls[ls.valid_fraction >= 0.9].pivot(index="cell", columns="epoch", values="land_fraction")
    lsv["pre_rate"] = (lsv["A"] - lsv["B"]) * 100 / (MID_B - MID_A)
    out = cells.merge(ex, on="cell", how="left").set_index("cell")
    out = out.join(lsv[["pre_rate", "B"]])
    out = out.join(a[["land_fraction", "valid_fraction", "block_land_fraction"]].add_suffix("_2010"))
    out = out.join(b[["land_fraction", "valid_fraction", "block_land_fraction"]].add_suffix("_t"))
    status = pd.Series("in_scope", index=out.index)
    no_pair = out.land_fraction_2010.isna() | out.land_fraction_t.isna()
    not_edge = ~no_pair & ~out.land_fraction_2010.between(0.1, 0.9)
    quality = ~no_pair & ~not_edge & ~((out.valid_fraction_2010 >= 0.9) & (out.valid_fraction_t >= 0.9)
                                       & ((out.block_land_fraction_t - out.block_land_fraction_2010).abs() <= 0.15))
    status[no_pair | quality] = "image_quality"
    status[not_edge] = "not_edge_2010"
    left = status == "in_scope"
    status[left & out.pre_rate.isna()] = "no_pre_spill_trend"
    left = status == "in_scope"
    status[left & ((out.land_fraction_2010 - out["B"]).abs() > AGREE)] = "measurement_disagreement"
    out["status"] = status
    return out.reset_index()[["cell", "status"] + RAW]


def build() -> dict:
    panel = pd.concat([load_basin(P2 / b, b) for b in BASINS])
    full = fit_m1(panel)
    res, base, lobo = [], [], []
    for b in BASINS:
        tr, te = panel[panel.basin != b], panel[panel.basin == b]
        p = predict(fit_m1(tr), te)
        res.append(te.rate.values - p)
        base.append(te.rate.values - tr.rate.mean())
        lobo.append(pd.DataFrame({"cell": te.cell.values, "lobo_pred": p}))
    res = np.concatenate(res); base = np.concatenate(base)
    lo, hi = float(np.quantile(res, 0.05)), float(np.quantile(res, 0.95))

    allc = pd.read_csv(P2 / "la_cells_basins.csv")
    status = pd.concat([basin_status(b) for b in BASINS])
    sites = allc.merge(status, on="cell", how="left")
    sites.loc[sites.status.isna() & (sites.esi_main == "10A") & (sites.basin != "birdfoot"), "status"] = "classification_unreliable"
    sites.loc[sites.basin == "birdfoot", "status"] = "river_delta"
    sites.loc[sites.esi_main != "10A", "status"] = "not_salt_marsh"
    n_in = int((sites.status == "in_scope").sum())
    assert n_in == len(panel), f"status rebuild disagrees with P2 panel: {n_in} vs {len(panel)}"
    sites = sites.merge(panel[["cell", "rate"]].rename(columns={"rate": "observed_rate"}), on="cell", how="left")
    sites = sites.merge(pd.concat(lobo), on="cell", how="left")
    p2 = pd.read_csv(ROOT / "results" / "p2_basin_holdout" / "predictions.csv")[["cell", "M1"]]
    sites = sites.merge(p2.rename(columns={"M1": "p2_heldout_M1"}), on="cell", how="left")
    keep = ["cell", "lat", "lon", "basin", "segment", "esi_main", "max_oiling", "first_oil", "cell_2km", "status",
            *RAW, "observed_rate", "lobo_pred", "p2_heldout_M1"]
    sites = sites[keep]
    for c in RAW + ["observed_rate", "lobo_pred", "p2_heldout_M1"]:
        sites[c] = sites[c].round(4)
    SITES.parent.mkdir(parents=True, exist_ok=True)
    sites.to_csv(SITES, index=False)

    rng = {f: {"p01": float(panel[f].quantile(0.01)), "p99": float(panel[f].quantile(0.99)),
               "min": float(panel[f].min()), "max": float(panel[f].max())} for f in RAW}
    inside = sites[sites.status == "in_scope"]
    transfer = pd.read_csv(ROOT / "results" / "p2_basin_holdout" / "oil_effect_transfer.csv")
    model = {
        "name": "p5-edge-loss-v1",
        "built": date.today().isoformat(),
        "target": "NAIP marsh-edge loss rate 2010-2015, m/yr (positive = land lost), per 100 m edge cell",
        "algorithm": "ordinary least squares (P2 model M1: exposure + pre-spill trend, no oiling term)",
        "terms": ["const", "water_1km_2010", "water_250m_2010", "log_fetch", "pre_rate"],
        "fetch_offset_m": FETCH_OFFSET,
        "coefficients": [float(x) for x in full.params.values],
        "standard_errors_unclustered": [float(x) for x in full.bse.values],
        "interval_level": 0.90,
        "interval_offsets": [lo, hi],
        "interval_method": "5th/95th percentiles of leave-one-basin-out residuals (each basin predicted by a model "
                           "fitted on the other two), added to the full-data prediction",
        "training_cells": int(len(panel)),
        "training_cells_by_basin": {b: int((panel.basin == b).sum()) for b in BASINS},
        "training_range": rng,
        "training_box": {"lat_min": float(inside.lat.min()), "lat_max": float(inside.lat.max()),
                         "lon_min": float(inside.lon.min()), "lon_max": float(inside.lon.max())},
        "lobo_mae": float(np.mean(np.abs(res))),
        "lobo_mae_no_predictor": float(np.mean(np.abs(base))),
        "heavy_uplift_range_m_per_yr": [float(transfer.train_heavy_coef.min()), float(transfer.train_heavy_coef.max())],
        "heavy_uplift_source": "P2 training-fold coefficients for Heavy vs no oil observed (results/p2_basin_holdout/oil_effect_transfer.csv)",
        "p1_headline": {"estimate": 0.85, "lo": 0.49, "hi": 1.22, "source": "docs/FINDINGS_2026-11-11.md section 7"},
        "measurement_note": "NAIP rates read about 1.2 m/yr below field erosion measurements (P3 analysis C); "
                            "differences between sites are more reliable than absolute values.",
        "validation": "P2 (docs/FINDINGS_2026-11-11.md section 8): held-out basins Barataria and western Breton, "
                      "M1 beat the no-predictor baseline; 90% intervals covered 89% of held-out cells.",
        "training_files_sha256": {f"{b}/{n}": sha(P2 / b / n) for b in BASINS
                                  for n in ("cells_10A.csv", "cell_land_by_year.csv", "exposure.csv",
                                            "landsat_cell_fraction.csv")},
    }
    MODEL.parent.mkdir(parents=True, exist_ok=True)
    MODEL.write_text(json.dumps(model, indent=2) + "\n")
    return {"panel": panel, "sites": sites, "model": model}


def zengel_centroid() -> tuple[float, float]:
    g = pd.read_excel(ZENGEL, sheet_name="GIS field erosion points")
    return float(g.LAT_DD.mean()), float(g.LON_DD.mean())


def example_cell(sites: pd.DataFrame) -> pd.Series:
    """Plan section 5: Heavy Barataria in-scope cell nearest the centroid of the Zengel et al. 2022 plots."""
    lat0, lon0 = zengel_centroid()
    c = sites[(sites.status == "in_scope") & (sites.basin == "barataria") & (sites.max_oiling == "Heavy")].copy()
    dy = (c.lat - lat0) * 111_320.0
    dx = (c.lon - lon0) * 111_320.0 * np.cos(np.radians(lat0))
    c["dist_m"] = np.hypot(dx, dy)
    return c.sort_values("dist_m").iloc[0]


def write_example(sites: pd.DataFrame) -> None:
    from src.shoreline_remediation.decision_framework import HybridDecisionModel
    from src.shoreline_remediation.site_evidence import (FEATURE_LABELS, FEATURES, load_model, predict_edge_loss,
                                                         site_flags, site_scenario, site_scenario_inputs,
                                                         treatment_evidence)
    load_model.cache_clear()
    m = load_model(str(MODEL))
    s = example_cell(sites)
    lat0, lon0 = zengel_centroid()
    v = {f: float(s[f]) for f in FEATURES}
    pr = predict_edge_loss(v, m)
    fl = site_flags(v, s.status, s.esi_main, s.max_oiling, s.lat, s.lon, m)
    ranked = HybridDecisionModel().rank_treatments(site_scenario(s.to_dict()))
    ev = treatment_evidence([r.treatment for r in ranked], s.max_oiling)
    ev_by = ev.set_index("treatment")
    up = m["heavy_uplift_range_m_per_yr"]
    L = ["# P5 worked example: heavily oiled salt-marsh edge, northern Barataria Bay", "",
         "Generated by `scripts/build_p5_demo.py`; do not edit by hand. Selection rule fixed in",
         "`docs/P5_DEMO_PLAN.md` section 5 before the numbers below were computed: the in-scope Heavy-class Barataria",
         f"cell nearest the centroid of the Zengel et al. (2022) field plots ({lat0:.5f} N, {abs(lon0):.5f} W).", "",
         "## Site", "",
         f"- Cell `{s.cell}` (100 m, UTM 15N), {s.lat:.5f} N, {abs(s.lon):.5f} W, {s.dist_m:.0f} m from the plot centroid",
         f"- SCAT segment {s.segment}; maximum oiling **{s.max_oiling}**; first oil recorded {s.first_oil}; ESI {s.esi_main}",
         f"- Basin: {s.basin}; scope: {s.status}", ""]
    L += ["| Input | Value | Source |", "| --- | --- | --- |"]
    src = {"water_1km_2010": "NAIP 2010", "water_250m_2010": "NAIP 2010", "fetch_mean_m": "NAIP 2010",
           "pre_rate": "Landsat 1998-2000 vs 2007-2009"}
    L += [f"| {FEATURE_LABELS[f]} | {v[f]:.3g} | {src[f]} |" for f in FEATURES]
    L += ["", "## Flags", ""]
    flags = fl.out_of_scope + fl.extrapolation + fl.evidence_scope
    L += [f"- {x}" for x in flags] or ["- None: inputs inside the central 98% of training cells; Heavy salt marsh."]
    L += ["", "## Expected marsh-edge loss (model p5-edge-loss-v1)", "",
          f"- Expected edge loss for marsh with this exposure and pre-spill trend: **{pr['rate']:.2f} m/yr**, 90% "
          f"interval {pr['lo']:.2f} to {pr['hi']:.2f} m/yr.",
          f"- Heavy oiling was associated with an extra {up[0]:.2f} to {up[1]:.2f} m/yr across P2 training folds "
          f"(P1 headline 0.85, 0.49 to 1.22). Not added to the number above: the effect was unstable between basins.",
          f"- Prediction for this cell from P2, when Barataria was held out entirely (M1): "
          + (f"{s.p2_heldout_M1:.2f} m/yr." if pd.notna(s.p2_heldout_M1) else "not available."),
          f"- Observed NAIP rate 2010-2015 for this cell: {s.observed_rate:.2f} m/yr. One cell is noisy; the interval "
          "is wide because single-cell rates are.",
          f"- {m['measurement_note']}", "",
          "## Cleanup options", "",
          "Rule screening uses the existing FAST-like rules with the inputs below. Evidence columns are differences "
          "against natural recovery with 90% intervals, from heavily oiled marsh at Bay Jimmy (Zengel et al. 2015, "
          "2022). Positive erosion = more edge lost than natural recovery.", "",
          "| Rank | Treatment | Rule screening | Utility | Extra erosion, years 0-2 | Extra erosion, years 2-8 | "
          "Vegetation cover, year 2 |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for i, r in enumerate(ranked, 1):
        e = ev_by.loc[r.treatment]
        L.append(f"| {i} | {r.treatment.replace('_', ' ')} | {r.feasibility} | {r.utility:.2f} | {e.erosion_0_2} | "
                 f"{e.erosion_2_8} | {e.veg_cover_yr2} |")
    for name in ev.treatment[~ev.treatment.isin([r.treatment for r in ranked])]:
        e = ev_by.loc[name]
        L.append(f"| - | {name} | restoration add-on | - | {e.erosion_0_2} | {e.erosion_2_8} | {e.veg_cover_yr2} |")
    L += ["", "Rule-screening inputs implied by the site:", "", "| Input | Value | Basis |", "| --- | --- | --- |"]
    L += [f"| {k} | {val} | {b} |" for k, val, b in site_scenario_inputs(s.to_dict())]
    L += ["", "## How to read this", "",
          "- The rules and the field evidence answer different questions: the rules screen what is operationally "
          "and ecologically acceptable; the evidence says what happened to edge erosion and vegetation where each "
          "method was used. Where they disagree, both are shown and neither overrides the other.",
          "- All evidence comes from one spill (Deepwater Horizon), one oil and one marsh type. Associations, not "
          "proven causes, except the planting contrast, which was randomized.",
          "- The tool predicts physical (edge loss) and biological (vegetation) recovery; it does not predict "
          "chemical recovery (no soil or sediment chemistry in the model; see REVIEW_NOTES E0)."]
    EXAMPLE.write_text("\n".join(L) + "\n")


def main() -> None:
    out = build()
    m = out["model"]
    print(f"model: {m['training_cells']} cells; coefficients {np.round(m['coefficients'], 4).tolist()}")
    print(f"90% interval offsets {np.round(m['interval_offsets'], 3).tolist()}; LOBO MAE {m['lobo_mae']:.3f}")
    print(out["sites"].status.value_counts().to_string())
    write_example(out["sites"])
    print("wrote", MODEL.relative_to(ROOT), SITES.relative_to(ROOT), EXAMPLE.relative_to(ROOT))


if __name__ == "__main__":
    main()
