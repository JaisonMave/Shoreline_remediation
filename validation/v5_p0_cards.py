"""V5 Phase 0: write the model cards from the Phase 0 results files (plan: docs/V5_P0_PLAN.md). No new analysis.

Run    : python -m validation.v5_p0_cards   (after validation.v5_p0_oil_excess and validation.v5_p0_intervals)
Reads  : results/v5_p0/*.csv, results/v5_p0/*summary.txt, models/p5_edge_loss_v1.json (point model, unchanged),
         results/p3_treatment/A_prespill_adjusted.csv (Zengel time shape for the composer option)
Writes : models/oil_excess_oos_v1.json, models/p5_edge_loss_v2.json
Neither card is registered in models/registry.json (integration is a separate step). Neither is "validated".
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from validation.v5_p0_common import CLASSES, RESULTS  # noqa: E402
from validation.v5_p0_oil_excess import zengel_mean_years_1_5  # noqa: E402

V1 = ROOT / "models" / "p5_edge_loss_v1.json"
OIL_CARD = ROOT / "models" / "oil_excess_oos_v1.json"
V2_CARD = ROOT / "models" / "p5_edge_loss_v2.json"
P3_A = ROOT / "results" / "p3_treatment" / "A_prespill_adjusted.csv"
STATE_PASS, STATE_FAIL = "experimental (gate passed, awaiting owner review)", "experimental (gate failed)"
DISCLOSURE = ("Gates were set on 14 Nov 2026 after the reviewer had already seen the no-excess baseline's error and "
              "bias on these same cells, so the test is not blind; only three basins have data (Terrebonne, "
              "Barataria, Breton), so the training set for held-out Barataria has few heavy cells (51); all cells "
              "are one spill (Deepwater Horizon).")
GATE_01 = ("In each held-out basin with 30 or more heavy cells, the heavy-cell mean absolute error with the "
           "out-of-sample excess is strictly below that of the no-excess baseline, AND (heavy-cell bias minus "
           "unoiled-cell bias) is within plus or minus 0.25 m/yr.")
GATE_02 = ("Coverage of the 90% interval is between 80% and 97% in every basin-by-oiling-class group with 100 or more "
           "cells, AND the interval (Winkler) score is lower than that of the no-predictor baseline interval in each "
           "held-out basin.")


def _r(x, n=6):
    return None if pd.isna(x) else round(float(x), n)


def _verdict(name: str) -> bool:
    line = [x for x in (RESULTS / "summary.txt").read_text().splitlines() if x.startswith(f"GATE {name}")][0]
    return line.endswith("PASSED")


def zengel_shape() -> dict:
    a = pd.read_csv(P3_A)
    a = a[a.contrast == "Oiled, untreated minus Reference (unoiled)"]
    e12 = float(a[a.analysis.str.startswith("A 2010-2012")]["difference"].iloc[0])
    e38 = float(a[a.analysis.str.startswith("A 2012-2018")]["difference"].iloc[0])
    return {"2010-2012": e12, "2012-2018": e38, "mean_years_1_5": zengel_mean_years_1_5()}


def oil_card() -> dict:
    est = pd.read_csv(RESULTS / "oil_excess_estimates.csv")
    tab = pd.read_csv(RESULTS / "oil_excess_by_basin_class.csv")
    gates = pd.read_csv(RESULTS / "oil_excess_gate.csv")
    boot = pd.read_csv(RESULTS / "oil_excess_mae_diff_boot.csv")
    dep = pd.read_csv(RESULTS / "deployable_offsets.csv")
    passed = _verdict("0.1")
    deploy = {r.oiling_class: {"excess_m_per_yr": _r(r.excess_m_per_yr), "lo90": _r(r.boot_lo90), "hi90": _r(r.boot_hi90),
                               "n_blocks": int(r.n_blocks), "n_class_cells_in_blocks": int(r.n_class_cells_in_blocks),
                               "n_noo_cells_in_blocks": int(r.n_noo_cells_in_blocks)}
              for r in est[est.held_out_basin == "all_basins_deployable"].itertuples()}
    held = [{"held_out_basin": r.held_out_basin, "oiling_class": r.oiling_class, "excess_m_per_yr": _r(r.excess_m_per_yr),
             "lo90": _r(r.boot_lo90), "hi90": _r(r.boot_hi90), "n_blocks": int(r.n_blocks),
             "n_class_cells_in_blocks": int(r.n_class_cells_in_blocks)}
            for r in est[est.held_out_basin != "all_basins_deployable"].itertuples()]
    res = [{"basin": r.basin, "oiling_class": r.oiling_class, "n_cells": int(r.n_cells),
            "mae_no_excess": _r(r.mae_clean), "mae_oos_excess": _r(r.mae_oos), "bias_no_excess": _r(r.bias_clean),
            "bias_oos_excess": _r(r.bias_oos), "mae_zengel_ref": _r(r.mae_zengel_ref), "mae_d32_ref": _r(r.mae_d32_ref)}
           for r in tab.itertuples()]
    gate_rows = [{"basin": r.basin, "n_heavy": int(r.n_heavy), "gated": bool(r.gated), "mae_no_excess": _r(r.mae_clean),
                  "mae_oos_excess": _r(r.mae_oos), "mae_strictly_below": bool(r.mae_below),
                  "heavy_minus_noo_bias_oos": _r(r.heavy_minus_noo_bias_oos),
                  "heavy_minus_noo_bias_no_excess": _r(r.heavy_minus_noo_bias_clean),
                  "bias_within_0_25": bool(r.bias_within),
                  "mae_diff_boot90": [_r(b.boot_lo90), _r(b.boot_hi90)]}
                 for r, b in zip(gates.itertuples(), boot.set_index("held_out_basin").loc[gates.basin].itertuples())]
    comp = dep[dep.predictor == "composer"]
    return {
        "name": "oil-excess-oos-v1",
        "built": date.today().isoformat(),
        "state": STATE_PASS if passed else STATE_FAIL,
        "decision": "D37 (Proposed)",
        "plan": "docs/V5_P0_PLAN.md Part 0.1 (written before the run)",
        "target": "Extra NAIP marsh-edge loss rate 2010-2015 (m/yr, positive = more land lost) of oiling-class-c "
                  "100 m edge cells over no-oil-observed (NOO) cells in the same 2 km block",
        "data": "data/demo/p5_sites_clean_lobo.csv (12,696 in-scope ESI 10A cells in Terrebonne, Barataria, Breton; "
                "observed NAIP rate, SCAT max_oiling, 2 km block, clean-edge baseline leave-one-basin-out prediction)",
        "method": "Weighted mean of within-block differences (class c minus NOO), weights n_c*n_NOO/(n_c+n_NOO) "
                  "(block fixed effects); for a held-out basin estimated from the other two basins only; no Zengel "
                  "term; added to the clean-edge baseline prediction fitted without the held-out basin. 90% interval: "
                  "2,000 block-bootstrap replicates stratified by basin, seed 20261114.",
        "baseline": "Clean-edge baseline (p5-edge-loss-clean-v1 leave-one-basin-out prediction) with no excess",
        "excess_by_class_deployable": deploy,
        "excess_by_class_deployable_note": "Estimated from all three basins (for use at a new site). The held-out "
                                           "test below used the two-basin estimates.",
        "held_out_excess": held,
        "held_out_results_by_basin_class": res,
        "gate": {"text": GATE_01, "rows": gate_rows, "verdict": "PASSED" if passed else "FAILED"},
        "composer_time_profile": {
            "status": "ASSUMED",
            "rule": "Zengel et al. 2022 untreated-minus-reference time shape, scaled so that its years 1-5 mean equals "
                    "the class excess (as D32 did); level drawn as a normal from the 90% bootstrap interval. Years 6-8 "
                    "are not tested by any data.",
            "zengel_untreated_minus_reference_m_per_yr": zengel_shape()},
        "composer_residual_offsets_by_class_deployable": {
            r.oiling_class: [_r(r.lo_offset), _r(r.hi_offset)] for r in comp.itertuples()},
        "composer_residual_offsets_note": "Descriptive only: conformal 5th/95th offsets of the leave-one-basin-out "
                                          "residuals of (clean baseline + out-of-sample excess), all three basins "
                                          "(results/v5_p0/deployable_offsets.csv). Not gated.",
        "results_files": ["results/v5_p0/oil_excess_summary.txt", "results/v5_p0/oil_excess_estimates.csv",
                          "results/v5_p0/oil_excess_by_basin_class.csv", "results/v5_p0/oil_excess_gate.csv",
                          "results/v5_p0/oil_excess_mae_diff_boot.csv", "results/v5_p0/oil_excess_cells.csv"],
        "run": "python -m validation.v5_p0_oil_excess && python -m validation.v5_p0_intervals && "
               "python -m validation.v5_p0_cards",
        "disclosure": DISCLOSURE,
        "limits": [
            "Gate " + ("passed" if passed else "failed") + ": " + "; ".join(
                f"{g['basin']} (n={g['n_heavy']}) MAE {g['mae_oos_excess']:.3f} vs no excess {g['mae_no_excess']:.3f}, "
                f"heavy-minus-NOO bias {g['heavy_minus_noo_bias_oos']:+.3f}" for g in gate_rows if g["gated"]) + ".",
            "A mean-based excess shifts the average error; it need not lower MAE (MAE is minimised by the median, "
            "and heavy-cell residuals need not be symmetric).",
            "Within-block differencing removes exposure differences between blocks, not within them.",
            "Hidden manual treatment and oiling misclassification (worst class ever recorded, whole cell) are not "
            "addressed.",
            "One spill, one oil, one marsh type, one period (NAIP 2010-2015); NAIP reads about 1.2 m/yr below field "
            "measurements.",
        ],
    }


def v2_card() -> dict:
    v1 = json.loads(V1.read_text())
    dep = pd.read_csv(RESULTS / "deployable_offsets.csv")
    m1 = dep[dep.predictor == "M1"].set_index("oiling_class")
    by_b = pd.read_csv(RESULTS / "interval_by_basin.csv")
    by_bc = pd.read_csv(RESULTS / "interval_by_basin_class.csv")
    cov = pd.read_csv(RESULTS / "interval_coverage_gate.csv")
    offs = pd.read_csv(RESULTS / "interval_offsets.csv")
    passed = _verdict("0.2")
    fb = offs[(offs.predictor == "M1") & offs.fallback_to_all_class & (offs.oiling_class != "__all__")]
    keep = ["target", "terms", "fetch_offset_m", "coefficients", "standard_errors_unclustered", "training_cells",
            "training_cells_by_basin", "training_range", "training_box", "measurement_note", "training_files_sha256"]
    card = {"name": "p5-edge-loss-v2", "built": date.today().isoformat(),
            "state": STATE_PASS if passed else STATE_FAIL, "decision": "D38 (Proposed)",
            "plan": "docs/V5_P0_PLAN.md Part 0.2 (written before the run)",
            "algorithm": v1["algorithm"] + "; point model identical to p5-edge-loss-v1 (same coefficients); only the "
                         "interval changes"}
    card.update({k: v1[k] for k in keep})
    card.update({
        "interval_level": 0.90,
        "interval_offsets": [_r(m1.loc["__all__", "lo_offset"]), _r(m1.loc["__all__", "hi_offset"])],
        "interval_offsets_by_class": {c: [_r(m1.loc[c, "lo_offset"]), _r(m1.loc[c, "hi_offset"])] for c in CLASSES},
        "interval_calibration_cells_by_class": {c: int(m1.loc[c, "n_calibration_cells"]) for c in CLASSES},
        "interval_fallback_by_class": {c: bool(m1.loc[c, "fallback_to_all_class"]) for c in CLASSES},
        "interval_method": "Split-conformal offsets with the finite-sample rank correction (k_lo = floor(0.05(n+1)), "
                           "k_hi = ceil(0.95(n+1))) of leave-one-basin-out residuals of all three basins, computed "
                           "separately per SCAT oiling class (classes with < 100 cells fall back to all classes), "
                           "added to the full-data prediction. Tested one level down: for each held-out basin the "
                           "offsets came from nested residuals of the other two basins only.",
        "baseline": "M0: training-basin mean plus 5th/95th percentiles of training deviations (no predictor)",
        "held_out_by_basin": [{"basin": r.basin, "n_cells": int(r.n_cells),
                               "coverage": _r(r.m1_class_oos_coverage), "mean_width": _r(r.m1_class_oos_mean_width),
                               "winkler": _r(r.m1_class_oos_winkler), "m0_coverage": _r(r.m0_coverage),
                               "m0_mean_width": _r(r.m0_mean_width), "m0_winkler": _r(r.m0_winkler),
                               "all_class_oos_winkler": _r(r.m1_all_oos_winkler),
                               "v1_deployed_winkler": _r(r.m1_v1_deployed_winkler),
                               "mae": _r(r.m1_class_oos_mae), "m0_mae": _r(r.m0_mae), "bias_pred_minus_obs": _r(r.m1_class_oos_bias)}
                              for r in by_b.itertuples()],
        "held_out_by_basin_class": [{"basin": r.basin, "oiling_class": r.oiling_class, "n_cells": int(r.n_cells),
                                     "gated_group": bool(r.gated_group), "coverage": _r(r.m1_class_oos_coverage),
                                     "mean_width": _r(r.m1_class_oos_mean_width), "winkler": _r(r.m1_class_oos_winkler),
                                     "v1_deployed_coverage": _r(r.m1_v1_deployed_coverage),
                                     "bias_pred_minus_obs": _r(r.m1_class_oos_bias)}
                                    for r in by_bc.itertuples()],
        "held_out_fallbacks": [f"held-out {r.held_out_basin} {r.oiling_class}: {r.n_calibration_cells} calibration "
                               "cells, all-class offsets used" for r in fb.itertuples()],
        "gate": {"text": GATE_02, "coverage_failures": [f"{r.basin} {r.oiling_class} {r.m1_class_oos_coverage:.3f}"
                                                         for r in cov[~cov.passes].itertuples()],
                 "winkler_failures": [r["basin"] for r in
                                      by_b[(by_b.basin != "pooled") & ~(by_b.m1_class_oos_winkler < by_b.m0_winkler)]
                                      .to_dict("records")],
                 "verdict": "PASSED" if passed else "FAILED"},
        "results_files": ["results/v5_p0/interval_summary.txt", "results/v5_p0/interval_by_basin.csv",
                          "results/v5_p0/interval_by_basin_class.csv", "results/v5_p0/interval_coverage_gate.csv",
                          "results/v5_p0/interval_offsets.csv", "results/v5_p0/deployable_offsets.csv",
                          "results/v5_p0/interval_cells.csv"],
        "run": "python -m validation.v5_p0_oil_excess && python -m validation.v5_p0_intervals && "
               "python -m validation.v5_p0_cards",
        "disclosure": DISCLOSURE,
        "limits": [
            "Gate " + ("passed" if passed else "failed") + ": coverage outside 80-97% in "
            + (", ".join(f"{r.basin} {r.oiling_class} ({r.m1_class_oos_coverage:.3f})" for r in cov[~cov.passes].itertuples())
               or "no group") + "; Winkler not below the no-predictor interval in "
            + (", ".join(by_b[(by_b.basin != "pooled") & ~(by_b.m1_class_oos_winkler < by_b.m0_winkler)].basin) or "no basin")
            + ".",
            "The point model has no oiling term; class offsets shift the interval for heavy cells but the point "
            "prediction still under-predicts them.",
            "Compare winkler with all_class_oos_winkler in held_out_by_basin to see whether conditioning on class "
            "helped (it is not part of the gate).",
            "Intervals are about 6 m/yr wide against a signal of about 1 m/yr.",
            "One spill, three basins; conformal guarantees assume exchangeable cells, which basins are not.",
        ],
        "validation": "Not validated. V5 Phase 0.2 (docs/V5_P0_PLAN.md): per-class out-of-sample intervals, gate "
                      + ("passed" if passed else "failed") + "; see held_out_by_basin and held_out_by_basin_class.",
    })
    return card


def main() -> None:
    for path, card in ((OIL_CARD, oil_card()), (V2_CARD, v2_card())):
        path.write_text(json.dumps(card, indent=2) + "\n")
        print("wrote", path.relative_to(ROOT), "state:", card["state"])


if __name__ == "__main__":
    main()
