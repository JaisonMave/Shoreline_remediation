"""R3 fix, primary (plan: docs/R3_OIL_DOUBLE_COUNT_PLAN.md section 3). Run once.

Refits the P2 M1 model (exposure + pre-spill trend, no oiling term) on clean-edge cells only (max_oiling in
NOO, Very_Light), same terms and method as models/p5_edge_loss_v1.json, so the composer's baseline no longer
includes heavily (or lightly/moderately) oiled cells in its own training data before the Zengel oil excess is
added on top.

Run:  python scripts/build_clean_baseline.py
Needs the analysis requirements (statsmodels). Reads data/external/p2 (unchanged) and data/demo/p5_sites.csv
(read only, not modified: training_box uses its lat/lon). Writes:
    models/p5_edge_loss_clean_v1.json     clean-edge baseline model card (same structure as p5_edge_loss_v1.json)
    data/demo/p5_sites_clean_lobo.csv     per-cell leave-one-basin-out predictions/residuals from the clean model
                                          (new file; data/demo/p5_sites.csv is not touched)
Appends a comparison paragraph to results/scenario_composer/summary_v4_r3.txt (created by the R3 diagnostic).
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

from validation.p2_basin_holdout import BASINS, EXPOSURE, load_basin  # noqa: E402

P2 = ROOT / "data" / "external" / "p2"
MODEL_V1 = ROOT / "models" / "p5_edge_loss_v1.json"
MODEL_CLEAN = ROOT / "models" / "p5_edge_loss_clean_v1.json"
SITES = ROOT / "data" / "demo" / "p5_sites.csv"
LOBO_CLEAN = ROOT / "data" / "demo" / "p5_sites_clean_lobo.csv"
SUMMARY = ROOT / "results" / "scenario_composer" / "summary_v4_r3.txt"
FETCH_OFFSET = 16.0
TERMS = ["const", "water_1km_2010", "water_250m_2010", "log_fetch", "pre_rate"]
CLEAN_CLASSES = ["NOO", "Very_Light"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fit_m1(d: pd.DataFrame):
    return sm.OLS(d.rate.values, sm.add_constant(d[EXPOSURE].astype(float), has_constant="add")).fit()


def predict(m, d: pd.DataFrame) -> np.ndarray:
    return m.predict(sm.add_constant(d[EXPOSURE].astype(float), has_constant="add")).values


def build() -> dict:
    panel = pd.concat([load_basin(P2 / b, b) for b in BASINS])
    clean = panel[panel.max_oiling.isin(CLEAN_CLASSES)]
    full_clean = fit_m1(clean)

    # leave-one-basin-out: train on the OTHER basins' clean cells, predict every cell (any class) of the held-out
    # basin, built the same way as p5-edge-loss-v1's own interval_offsets.
    lobo_rows, res_all = [], []
    for b in BASINS:
        train = clean[clean.basin != b]
        test = panel[panel.basin == b]
        p = predict(fit_m1(train), test)
        r = test.rate.values - p
        res_all.append(r)
        lobo_rows.append(pd.DataFrame({"cell": test.cell.values, "basin": b, "cell_2km": test.cell_2km.values,
                                       "max_oiling": test.max_oiling.astype(str).values,
                                       "observed_rate": test.rate.values, "lobo_pred_clean": p}))
    lobo = pd.concat(lobo_rows, ignore_index=True)
    res_all = np.concatenate(res_all)
    lo, hi = float(np.quantile(res_all, 0.05)), float(np.quantile(res_all, 0.95))
    base_mae = float(np.mean(np.abs(clean.rate.values - clean.rate.values.mean())))

    for c in ["observed_rate", "lobo_pred_clean"]:
        lobo[c] = lobo[c].round(4)
    LOBO_CLEAN.parent.mkdir(parents=True, exist_ok=True)
    lobo.to_csv(LOBO_CLEAN, index=False)

    v1 = json.loads(MODEL_V1.read_text())
    sites = pd.read_csv(SITES, dtype={"cell": str, "segment": str, "cell_2km": str})
    clean_sites = sites[(sites.status == "in_scope") & sites.max_oiling.isin(CLEAN_CLASSES)]
    raw_features = ["water_1km_2010", "water_250m_2010", "fetch_mean_m", "pre_rate"]  # log_fetch is derived, not raw
    rng = {f: {"p01": float(clean[f].quantile(0.01)), "p99": float(clean[f].quantile(0.99)),
               "min": float(clean[f].min()), "max": float(clean[f].max())} for f in raw_features}

    model = {
        "name": "p5-edge-loss-clean-v1",
        "built": date.today().isoformat(),
        "target": v1["target"],
        "algorithm": "ordinary least squares (P2 model M1: exposure + pre-spill trend, no oiling term; fitted on "
                    "clean-edge cells only, max_oiling in NOO and Very_Light, to avoid the composer's separate "
                    "oil-excess term being added on top of a baseline that already includes heavily oiled cells; "
                    "docs/R3_OIL_DOUBLE_COUNT_PLAN.md)",
        "terms": TERMS,
        "fetch_offset_m": FETCH_OFFSET,
        "coefficients": [float(x) for x in full_clean.params.values],
        "standard_errors_unclustered": [float(x) for x in full_clean.bse.values],
        "interval_level": 0.90,
        "interval_offsets": [lo, hi],
        "interval_method": "5th/95th percentiles of leave-one-basin-out residuals (each basin's cells, any oiling "
                           "class, predicted by a clean-edge-only model fitted on the other two basins' clean "
                           "cells), added to the full-data prediction",
        "training_cells": int(len(clean)),
        "training_cells_by_basin": {b: int((clean.basin == b).sum()) for b in BASINS},
        "training_range": rng,
        "training_box": {"lat_min": float(clean_sites.lat.min()), "lat_max": float(clean_sites.lat.max()),
                         "lon_min": float(clean_sites.lon.min()), "lon_max": float(clean_sites.lon.max())},
        "lobo_mae": float(np.mean(np.abs(res_all))),
        "lobo_mae_no_predictor": base_mae,
        "heavy_uplift_range_m_per_yr": v1["heavy_uplift_range_m_per_yr"],
        "heavy_uplift_source": v1["heavy_uplift_source"],
        "p1_headline": v1["p1_headline"],
        "measurement_note": v1["measurement_note"],
        "validation": "R3 fix (docs/R3_OIL_DOUBLE_COUNT_PLAN.md): refit of P2 M1 on clean-edge cells (NOO, "
                      "Very_Light) only, leave-one-basin-out residuals computed over every cell (any oiling class) "
                      "of each held-out basin, as for p5-edge-loss-v1. See results/scenario_composer/c1b_coverage.csv, "
                      "c2b_block_coverage.csv, b1b_horizon_coverage.csv for held-out coverage and bias.",
        "training_files_sha256": v1["training_files_sha256"],
        "clean_training_filter": {"kept_oiling_classes": CLEAN_CLASSES, "excluded_oiling_classes": ["Light", "Moderate", "Heavy"]},
        "fixes": "docs/R3_OIL_DOUBLE_COUNT_PLAN.md; docs/V4_PROGRAMME_PLAN.md section R3",
    }
    MODEL_CLEAN.parent.mkdir(parents=True, exist_ok=True)
    MODEL_CLEAN.write_text(json.dumps(model, indent=2) + "\n")
    return {"panel": panel, "clean": clean, "model": model, "v1": v1}


def main() -> None:
    out = build()
    m, v1 = out["model"], out["v1"]
    L = ["", "R3 fix: clean-edge baseline model (plan section 3). Run once.", "",
         f"models/p5_edge_loss_clean_v1.json: {m['training_cells']} clean-edge cells (NOO + Very_Light; v1 used "
         f"{v1['training_cells']} cells of all classes).", "Coefficients (const, water_1km_2010, water_250m_2010, "
         "log_fetch, pre_rate):"]
    for name, a, b in zip(TERMS, v1["coefficients"], m["coefficients"]):
        L.append(f"  {name}: v1 {a:+.4f} -> clean {b:+.4f}")
    L.append(f"90% interval offsets: v1 ({v1['interval_offsets'][0]:+.3f} to {v1['interval_offsets'][1]:+.3f}) -> "
             f"clean ({m['interval_offsets'][0]:+.3f} to {m['interval_offsets'][1]:+.3f})")
    L.append(f"LOBO MAE: v1 {v1['lobo_mae']:.3f} -> clean {m['lobo_mae']:.3f} (clean no-predictor baseline "
             f"{m['lobo_mae_no_predictor']:.3f})")
    with open(SUMMARY, "a") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))
    print("wrote", MODEL_CLEAN.relative_to(ROOT), LOBO_CLEAN.relative_to(ROOT))


if __name__ == "__main__":
    main()
