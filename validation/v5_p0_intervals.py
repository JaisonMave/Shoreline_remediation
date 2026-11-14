"""V5 Phase 0.2: 90% intervals calibrated without the target basin, per oiling class (plan: docs/V5_P0_PLAN.md,
Part 0.2). Run once, after validation.v5_p0_oil_excess (its cell file feeds the descriptive composer interval).

Gated interval: point prediction = deployed p5-edge-loss-v1 (P2 M1) leave-one-basin-out prediction (`lobo_pred`).
Offsets for held-out basin B = split-conformal 5th/95th rank offsets (finite-sample correction) of NESTED out-of-sample
residuals of the other two basins: with training basins A and C, A's residuals come from M1 fitted on C alone and C's
from M1 fitted on A alone, so no calibration model has seen B. Offsets are per oiling class; a class with < 100
calibration cells falls back to the all-class offsets. Baseline M0: training-basin mean + 5th/95th percentiles of
training deviations from it. Gate 0.2 (verbatim in the plan).

Descriptive (not gated): all-class nested offsets; v1 deployed offsets; the same per-class nested procedure around the
composer point prediction of Part 0.1 (clean-edge baseline + out-of-sample class excess).

Run    : python -m validation.v5_p0_intervals
Reads  : data/demo/p5_sites.csv, data/demo/p5_sites_clean_lobo.csv, models/p5_edge_loss_v1.json,
         results/v5_p0/oil_excess_cells.csv, results/v5_p0/oil_excess_summary.txt
Writes : results/v5_p0/{interval_cells.csv, interval_offsets.csv, interval_inner_excess.csv,
         interval_by_basin_class.csv, interval_by_basin.csv, interval_coverage_gate.csv, deployable_offsets.csv,
         interval_summary.txt, summary.txt}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from validation.v5_p0_common import (ALPHA, BASINS, CLASSES, CLEAN_CLASSES, MIN_CAL_CELLS, RESULTS,  # noqa: E402
                                     add_excess, class_excess, class_offsets, fit_ols, load_cells, predict_ols,
                                     winkler)

V1 = ROOT / "models" / "p5_edge_loss_v1.json"
COV_GATE = (0.80, 0.97)
MIN_GROUP = 100
REFIT_TOL = 0.01
METHODS = {
    "m1_class_oos": "GATED: M1 + per-class nested out-of-sample conformal offsets",
    "m0": "BASELINE: training-basin mean + 5th/95th percentiles of training deviations",
    "m1_all_oos": "descriptive: M1 + all-class nested out-of-sample conformal offsets",
    "m1_v1_deployed": "descriptive: M1 + deployed v1 offsets (calibrated on the pooled residuals they are scored on)",
    "composer_class_oos": "descriptive: clean baseline + out-of-sample class excess + per-class nested conformal offsets",
}


def refit_check(d: pd.DataFrame) -> dict:
    """Plan 0.2 choice 2: the refit code must reproduce the committed LOBO predictions within 0.01 m/yr."""
    out = {}
    for b in BASINS:
        te = d[d.basin == b]
        m1 = predict_ols(fit_ols(d[d.basin != b]), te)
        cl = predict_ols(fit_ols(d[(d.basin != b) & d.max_oiling.isin(CLEAN_CLASSES)]), te)
        out[b] = (float(np.max(np.abs(m1 - te.lobo_pred))), float(np.max(np.abs(cl - te.lobo_pred_clean))))
        if max(out[b]) > REFIT_TOL:
            raise RuntimeError(f"refit does not reproduce committed LOBO predictions in {b}: {out[b]}")
    return out


def inner_residuals(d: pd.DataFrame, target: str) -> tuple[pd.DataFrame, list[dict]]:
    """Nested out-of-sample residuals for the two training basins of `target` (M1 and composer predictor)."""
    tr = [b for b in BASINS if b != target]
    parts, ex_rows = [], []
    for a, other in ((tr[0], tr[1]), (tr[1], tr[0])):
        cal, fit = d[d.basin == a], d[d.basin == other]
        p_m1 = predict_ols(fit_ols(fit), cal)
        p_clean = predict_ols(fit_ols(fit[fit.max_oiling.isin(CLEAN_CLASSES)]), cal)
        ex = class_excess(fit)
        for c, v in ex.items():
            ex_rows.append({"held_out_basin": target, "calibration_basin": a, "fitted_on": other, "oiling_class": c,
                            "excess_m_per_yr": v})
        p_comp = p_clean + add_excess(cal, ex)
        parts.append(pd.DataFrame({"basin": a, "max_oiling": cal.max_oiling.values,
                                   "r_m1": cal.observed_rate.values - p_m1,
                                   "r_comp": cal.observed_rate.values - p_comp}))
    return pd.concat(parts, ignore_index=True), ex_rows


def apply(pred: np.ndarray, classes: np.ndarray, offs: dict, use_class: bool = True) -> tuple[np.ndarray, np.ndarray]:
    key = classes if use_class else np.full(len(classes), "__all__")
    lo = np.array([offs[k][0] for k in key]); hi = np.array([offs[k][1] for k in key])
    return pred + lo, pred + hi


def offsets_rows(offs: dict, target: str, predictor: str) -> list[dict]:
    return [{"held_out_basin": target, "predictor": predictor, "oiling_class": k, "lo_offset": v[0], "hi_offset": v[1],
             "n_calibration_cells": v[2], "fallback_to_all_class": v[3]} for k, v in offs.items()]


def summarise(g: pd.DataFrame) -> dict:
    out = {"n_cells": len(g)}
    y = g.observed_rate.to_numpy()
    for m in METHODS:
        lo, hi, p = g[f"{m}_lo"].to_numpy(), g[f"{m}_hi"].to_numpy(), g[f"{m}_pred"].to_numpy()
        out[f"{m}_coverage"] = float(np.mean((lo <= y) & (y <= hi)))
        out[f"{m}_mean_width"] = float(np.mean(hi - lo))
        out[f"{m}_winkler"] = float(np.mean(winkler(lo, hi, y, ALPHA)))
        out[f"{m}_mae"] = float(np.mean(np.abs(p - y)))
        out[f"{m}_bias"] = float(np.mean(p - y))
    return out


def run() -> dict:
    RESULTS.mkdir(parents=True, exist_ok=True)
    d = load_cells()
    refit = refit_check(d)
    v1 = json.loads(V1.read_text())
    v1_lo, v1_hi = v1["interval_offsets"]
    ox = pd.read_csv(RESULTS / "oil_excess_cells.csv", dtype={"cell": str, "cell_2km": str})[["cell", "pred_oos"]]
    d = d.merge(ox, on="cell", how="left", validate="one_to_one")
    if d.pred_oos.isna().any():
        raise RuntimeError("results/v5_p0/oil_excess_cells.csv does not cover every cell; run v5_p0_oil_excess first")

    cells, off_rows, ex_rows = [], [], []
    for b in BASINS:
        te = d[d.basin == b].copy()
        tr = d[d.basin != b]
        cal, ex = inner_residuals(d, b)
        ex_rows += ex
        cls = te.max_oiling.to_numpy()
        o_m1 = class_offsets(cal.r_m1.to_numpy(), cal.max_oiling.to_numpy(), MIN_CAL_CELLS)
        o_comp = class_offsets(cal.r_comp.to_numpy(), cal.max_oiling.to_numpy(), MIN_CAL_CELLS)
        off_rows += offsets_rows(o_m1, b, "M1") + offsets_rows(o_comp, b, "composer")
        p = te.lobo_pred.to_numpy()
        te["m1_class_oos_pred"] = p
        te["m1_class_oos_lo"], te["m1_class_oos_hi"] = apply(p, cls, o_m1)
        te["m1_all_oos_pred"] = p
        te["m1_all_oos_lo"], te["m1_all_oos_hi"] = apply(p, cls, o_m1, use_class=False)
        te["m1_v1_deployed_pred"] = p
        te["m1_v1_deployed_lo"], te["m1_v1_deployed_hi"] = p + v1_lo, p + v1_hi
        pc = te.pred_oos.to_numpy()
        te["composer_class_oos_pred"] = pc
        te["composer_class_oos_lo"], te["composer_class_oos_hi"] = apply(pc, cls, o_comp)
        mu = float(tr.observed_rate.mean())
        dev = tr.observed_rate.to_numpy() - mu
        te["m0_pred"] = mu
        te["m0_lo"], te["m0_hi"] = mu + float(np.quantile(dev, 0.05)), mu + float(np.quantile(dev, 0.95))
        te["m1_class_offsets_fallback"] = [o_m1[c][3] for c in cls]
        cells.append(te)
    cells = pd.concat(cells, ignore_index=True)

    by_bc = pd.DataFrame([{"basin": b, "oiling_class": c, **summarise(g)}
                          for (b, c), g in cells.groupby(["basin", "max_oiling"])])
    by_bc["gated_group"] = by_bc.n_cells >= MIN_GROUP
    by_b = pd.DataFrame([{"basin": b, **summarise(g)} for b, g in cells.groupby("basin")]
                        + [{"basin": "pooled", **summarise(cells)}])
    cov = by_bc[by_bc.gated_group][["basin", "oiling_class", "n_cells", "m1_class_oos_coverage"]].copy()
    cov["passes"] = cov.m1_class_oos_coverage.between(*COV_GATE)
    wk = by_b[by_b.basin != "pooled"][["basin", "n_cells", "m1_class_oos_winkler", "m0_winkler"]].copy()
    wk["passes"] = wk.m1_class_oos_winkler < wk.m0_winkler
    passed = bool(cov.passes.all() and wk.passes.all())

    # deployable offsets (plan 0.2 choice 9): plain LOBO residuals of all three basins, per class
    dep = []
    r_m1 = (d.observed_rate - d.lobo_pred).to_numpy()
    r_cp = (d.observed_rate - d.pred_oos).to_numpy()
    dep += offsets_rows(class_offsets(r_m1, d.max_oiling.to_numpy()), "none (all three basins)", "M1")
    dep += offsets_rows(class_offsets(r_cp, d.max_oiling.to_numpy()), "none (all three basins)", "composer")
    dep = pd.DataFrame(dep)
    offs = pd.DataFrame(off_rows)

    keep = ["basin", "block", "cell", "max_oiling", "observed_rate", "m1_class_offsets_fallback"] + \
        [f"{m}_{k}" for m in METHODS for k in ("pred", "lo", "hi")]
    cells[keep].to_csv(RESULTS / "interval_cells.csv", index=False)
    offs.to_csv(RESULTS / "interval_offsets.csv", index=False)
    pd.DataFrame(ex_rows).to_csv(RESULTS / "interval_inner_excess.csv", index=False)
    by_bc.to_csv(RESULTS / "interval_by_basin_class.csv", index=False)
    by_b.to_csv(RESULTS / "interval_by_basin.csv", index=False)
    cov.to_csv(RESULTS / "interval_coverage_gate.csv", index=False)
    dep.to_csv(RESULTS / "deployable_offsets.csv", index=False)

    fb = offs[(offs.predictor == "M1") & offs.fallback_to_all_class & (offs.oiling_class != "__all__")]
    L = ["V5 Phase 0.2: per-class out-of-sample 90% intervals (docs/V5_P0_PLAN.md Part 0.2). Run once.",
         "Gate 0.2: \"Coverage of the 90% interval is between 80% and 97% in every basin-by-oiling-class group with 100 "
         "or more cells, AND the interval (Winkler) score is lower than that of the no-predictor baseline interval in "
         "each held-out basin.\"", "",
         "Refit check (max |refit - committed LOBO prediction|, M1 / clean): " +
         "; ".join(f"{b} {v[0]:.4f} / {v[1]:.4f}" for b, v in refit.items()), "",
         "Fallbacks to all-class offsets (fewer than 100 calibration cells), M1: " +
         ("; ".join(f"held-out {r.held_out_basin} {r.oiling_class} (n_cal={r.n_calibration_cells})" for r in fb.itertuples()) or "none"),
         "", "Coverage of the gated interval in basin x class groups with >= 100 cells (gate 0.80-0.97):"]
    for r in cov.itertuples():
        L.append(f"  {r.basin:>10} {r.oiling_class:>10}: n={r.n_cells:5d} coverage {r.m1_class_oos_coverage:.3f} "
                 f"{'pass' if r.passes else 'FAIL'}")
    small = by_bc[~by_bc.gated_group]
    L.append("  not gated (< 100 cells): " + "; ".join(f"{r.basin} {r.oiling_class} n={r.n_cells} coverage "
                                                      f"{r.m1_class_oos_coverage:.3f}" for r in small.itertuples()))
    L += ["", "Winkler score per held-out basin (lower is better), gated interval vs M0 baseline:"]
    for r in wk.itertuples():
        L.append(f"  {r.basin:>10}: n={r.n_cells} gated {r.m1_class_oos_winkler:.3f} vs M0 {r.m0_winkler:.3f} "
                 f"{'pass' if r.passes else 'FAIL'}")
    L += ["", "All methods per basin (coverage / mean width / Winkler):"]
    for r in by_b.itertuples():
        L.append(f"  {r.basin}: " + "; ".join(
            f"{m} {getattr(r, m + '_coverage'):.3f}/{getattr(r, m + '_mean_width'):.2f}/{getattr(r, m + '_winkler'):.2f}"
            for m in METHODS))
    L += ["", "Method labels: " + "; ".join(f"{k} = {v}" for k, v in METHODS.items()), "",
          f"GATE 0.2: {'PASSED' if passed else 'FAILED'}"]
    text = "\n".join(L) + "\n"
    (RESULTS / "interval_summary.txt").write_text(text)
    g1 = [x for x in (RESULTS / "oil_excess_summary.txt").read_text().splitlines() if x.startswith("GATE 0.1")]
    (RESULTS / "summary.txt").write_text(
        "V5 Phase 0 summary (docs/V5_P0_PLAN.md). Details: oil_excess_summary.txt, interval_summary.txt.\n"
        + (g1[0] if g1 else "GATE 0.1: not run") + "\n" + f"GATE 0.2: {'PASSED' if passed else 'FAILED'}\n")
    print(text)
    return {"passed": passed, "coverage": cov, "winkler": wk, "by_basin": by_b, "by_basin_class": by_bc}


if __name__ == "__main__":
    run()
