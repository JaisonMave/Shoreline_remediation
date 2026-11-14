"""V5 Phase 0.1: oil excess estimated out of sample, tested against the no-excess baseline (plan: docs/V5_P0_PLAN.md,
Part 0.1). Run once.

For each held-out basin (Terrebonne, Barataria, Breton in turn), the excess for oiling class c (Heavy, Moderate,
Light) is the weighted mean within-2-km-block difference in observed NAIP edge-loss rate between class-c cells and
no-oil-observed (NOO) cells, from the OTHER two basins only (weights n_c*n_NOO/(n_c+n_NOO), i.e. a block-fixed-
effects estimate). No Zengel term. It is added to the clean-edge baseline prediction fitted without the held-out
basin (lobo_pred_clean). Gate 0.1 (verbatim in the plan) applies to held-out basins with >= 30 heavy cells.

Run    : python -m validation.v5_p0_oil_excess
Reads  : data/demo/p5_sites_clean_lobo.csv, data/demo/p5_sites.csv, results/scenario_composer/c1b_cells.csv (check),
         results/p3_treatment/A_prespill_adjusted.csv and models/oil_excess_d32.json (reference rows only)
Writes : results/v5_p0/{oil_excess_cells.csv, oil_excess_estimates.csv, oil_excess_by_basin_class.csv,
         oil_excess_mae_diff_boot.csv, oil_excess_gate.csv, oil_excess_summary.txt}
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

from validation.v5_p0_common import (BASINS, EXCESS_CLASSES, N_BOOT, RESULTS, SEED, add_excess,  # noqa: E402
                                     block_table, bootstrap_excess, load_cells, weighted_excess)

GATE_MIN_HEAVY = 30
GATE_BIAS = 0.25
P3_A = ROOT / "results" / "p3_treatment" / "A_prespill_adjusted.csv"
D32 = ROOT / "models" / "oil_excess_d32.json"
C1B = ROOT / "results" / "scenario_composer" / "c1b_cells.csv"


def zengel_mean_years_1_5() -> float:
    a = pd.read_csv(P3_A)
    a = a[a.contrast == "Oiled, untreated minus Reference (unoiled)"]
    e12 = float(a[a.analysis.str.startswith("A 2010-2012")]["difference"].iloc[0])
    e38 = float(a[a.analysis.str.startswith("A 2012-2018")]["difference"].iloc[0])
    return (2 * e12 + 3 * e38) / 5


def check_known(d: pd.DataFrame) -> None:
    """Plan 0.1 choice 10: reproduce the orchestrator's no-excess numbers on the 532 heavy cells before the gate."""
    h = d[d.basin.isin(["barataria", "breton"]) & (d.max_oiling == "Heavy")]
    c1b = pd.read_csv(C1B, dtype={"cell": str})
    if set(h.cell) != set(c1b.cell) or len(h) != 532:
        raise RuntimeError("heavy held-out cells differ from results/scenario_composer/c1b_cells.csv")
    err = h.lobo_pred_clean - h.observed_rate
    mae, bias = float(err.abs().mean()), float(err.mean())
    if abs(mae - 1.044) > 0.001 or abs(bias + 0.475) > 0.001:
        raise RuntimeError(f"no-excess baseline does not reproduce: MAE {mae:.4f}, bias {bias:.4f}")


def _rng(*keys) -> np.random.Generator:
    return np.random.default_rng([SEED, *keys])


def estimate(train: pd.DataFrame, label: str, key: int) -> tuple[dict, list[dict]]:
    excess, rows = {}, []
    for j, c in enumerate(EXCESS_CLASSES):
        t = block_table(train, c)
        e = weighted_excess(t)
        boot = bootstrap_excess(t, _rng(key, j))
        excess[c] = e
        row = {"held_out_basin": label, "oiling_class": c, "excess_m_per_yr": e,
               "boot_lo90": float(np.percentile(boot, 5)), "boot_hi90": float(np.percentile(boot, 95)),
               "boot_sd": float(np.std(boot, ddof=1)), "n_blocks": int(len(t)),
               "n_class_cells_in_blocks": int(t.n_c.sum()) if len(t) else 0,
               "n_noo_cells_in_blocks": int(t.n_noo.sum()) if len(t) else 0,
               "no_contributing_block": len(t) == 0}
        for b in BASINS:
            row[f"n_blocks_{b}"] = int((t.basin == b).sum()) if len(t) else 0
        rows.append(row)
    return excess, rows


def metrics(g: pd.DataFrame) -> dict:
    out = {"n_cells": len(g)}
    for p in ("pred_clean", "pred_oos", "pred_zengel_ref", "pred_d32_ref"):
        e = g[p] - g.observed_rate
        tag = p.replace("pred_", "")
        out[f"mae_{tag}"] = float(e.abs().mean())
        out[f"bias_{tag}"] = float(e.mean())
    return out


def mae_diff_boot(h: pd.DataFrame, rng: np.random.Generator, n_boot: int = N_BOOT) -> np.ndarray:
    """Block bootstrap of mean(|oos error| - |no-excess error|) over held-out heavy cells (descriptive)."""
    h = h.assign(dd=(h.pred_oos - h.observed_rate).abs() - (h.pred_clean - h.observed_rate).abs())
    blocks = [g.dd.to_numpy() for _, g in h.groupby("block")]
    out = np.empty(n_boot)
    for i in range(n_boot):
        k = rng.integers(0, len(blocks), len(blocks))
        v = np.concatenate([blocks[j] for j in k])
        out[i] = v.mean()
    return out


def run() -> dict:
    RESULTS.mkdir(parents=True, exist_ok=True)
    d = load_cells()
    check_known(d)
    z = zengel_mean_years_1_5()
    d32 = float(json.loads(D32.read_text())["E_field_size_weighted"])

    est_rows, cells, boots = [], [], []
    for i, b in enumerate(BASINS):
        train, test = d[d.basin != b], d[d.basin == b].copy()
        excess, rows = estimate(train, b, i)
        est_rows += rows
        test["excess"] = add_excess(test, excess)
        test["pred_clean"] = test.lobo_pred_clean
        test["pred_oos"] = test.pred_clean + test.excess
        heavy = (test.max_oiling == "Heavy").to_numpy()
        test["pred_zengel_ref"] = test.pred_clean + np.where(heavy, z, 0.0)
        test["pred_d32_ref"] = test.pred_clean + np.where(heavy, d32, 0.0)
        cells.append(test)
        bd = mae_diff_boot(test[heavy], _rng(100 + i))
        boots.append({"held_out_basin": b, "n_heavy_cells": int(heavy.sum()),
                      "n_heavy_blocks": int(test[heavy].block.nunique()),
                      "mae_diff_oos_minus_clean": float(((test[heavy].pred_oos - test[heavy].observed_rate).abs()
                                                         - (test[heavy].pred_clean - test[heavy].observed_rate).abs()).mean()),
                      "boot_lo90": float(np.percentile(bd, 5)), "boot_hi90": float(np.percentile(bd, 95))})
    # descriptive (c): deployable excess from all three basins
    _, rows = estimate(d, "all_basins_deployable", 9)
    est_rows += rows

    cells = pd.concat(cells, ignore_index=True)
    cells["residual_oos"] = cells.observed_rate - cells.pred_oos
    est = pd.DataFrame(est_rows)
    tab = []
    for (b, c), g in cells.groupby(["basin", "max_oiling"]):
        tab.append({"basin": b, "oiling_class": c, **metrics(g)})
    for b, g in cells.groupby("basin"):
        tab.append({"basin": b, "oiling_class": "all", **metrics(g)})
    g = cells[cells.basin.isin(["barataria", "breton"]) & (cells.max_oiling == "Heavy")]
    tab.append({"basin": "barataria+breton", "oiling_class": "Heavy", **metrics(g)})
    tab = pd.DataFrame(tab)
    boots = pd.DataFrame(boots)

    gate_rows = []
    for b in BASINS:
        h = tab[(tab.basin == b) & (tab.oiling_class == "Heavy")].iloc[0]
        n = tab[(tab.basin == b) & (tab.oiling_class == "NOO")].iloc[0]
        rel = h.bias_oos - n.bias_oos
        gated = h.n_cells >= GATE_MIN_HEAVY
        gate_rows.append({"basin": b, "n_heavy": int(h.n_cells), "gated": bool(gated),
                          "mae_clean": h.mae_clean, "mae_oos": h.mae_oos, "mae_below": bool(h.mae_oos < h.mae_clean),
                          "heavy_bias_oos": h.bias_oos, "noo_bias": n.bias_oos, "heavy_minus_noo_bias_oos": rel,
                          "heavy_minus_noo_bias_clean": h.bias_clean - n.bias_clean,
                          "bias_within": bool(abs(rel) <= GATE_BIAS)})
    gates = pd.DataFrame(gate_rows)
    gp = gates[gates.gated]
    passed = bool((gp.mae_below & gp.bias_within).all())

    keep = ["basin", "block", "cell", "cell_2km", "max_oiling", "observed_rate", "pred_clean", "excess", "pred_oos",
            "residual_oos", "pred_zengel_ref", "pred_d32_ref"]
    cells[keep].to_csv(RESULTS / "oil_excess_cells.csv", index=False)
    est.to_csv(RESULTS / "oil_excess_estimates.csv", index=False)
    tab.to_csv(RESULTS / "oil_excess_by_basin_class.csv", index=False)
    boots.to_csv(RESULTS / "oil_excess_mae_diff_boot.csv", index=False)
    gates.to_csv(RESULTS / "oil_excess_gate.csv", index=False)

    L = ["V5 Phase 0.1: out-of-sample oil excess (docs/V5_P0_PLAN.md Part 0.1). Run once.",
         "Gate 0.1: \"In each held-out basin with 30 or more heavy cells, the heavy-cell mean absolute error with the "
         "out-of-sample excess is strictly below that of the no-excess baseline, AND (heavy-cell bias minus unoiled-cell "
         "bias) is within plus or minus 0.25 m/yr.\"", "",
         "Excess per held-out basin (m/yr, estimated from the other two basins; 90% block-bootstrap interval):"]
    for r in est.itertuples():
        L.append(f"  {r.held_out_basin:>22} {r.oiling_class:>8}: {r.excess_m_per_yr:+.3f} ({r.boot_lo90:+.3f} to "
                 f"{r.boot_hi90:+.3f}); {r.n_blocks} blocks, {r.n_class_cells_in_blocks} class cells, "
                 f"{r.n_noo_cells_in_blocks} NOO cells" + ("; NO contributing block, excess set to 0" if r.no_contributing_block else ""))
    L += ["", f"Reference constant excesses (Heavy only, descriptive): Zengel years 1-5 mean {z:+.3f}, D32 {d32:+.3f}.", "",
          "Heavy cells per held-out basin (MAE / bias pred-obs, m/yr):"]
    for r in gates.itertuples():
        t = tab[(tab.basin == r.basin) & (tab.oiling_class == "Heavy")].iloc[0]
        L.append(f"  {r.basin}: n={r.n_heavy}{'' if r.gated else ' (not gated, < 30 heavy cells)'}; no excess "
                 f"{t.mae_clean:.3f} / {t.bias_clean:+.3f}; out-of-sample excess {t.mae_oos:.3f} / {t.bias_oos:+.3f}; "
                 f"Zengel ref {t.mae_zengel_ref:.3f} / {t.bias_zengel_ref:+.3f}; D32 ref {t.mae_d32_ref:.3f} / "
                 f"{t.bias_d32_ref:+.3f}")
        L.append(f"     NOO bias {r.noo_bias:+.3f}; heavy minus NOO bias: out-of-sample {r.heavy_minus_noo_bias_oos:+.3f} "
                 f"(no excess {r.heavy_minus_noo_bias_clean:+.3f}); MAE strictly below baseline: "
                 f"{'yes' if r.mae_below else 'NO'}; bias within +/-0.25: {'yes' if r.bias_within else 'NO'}")
        bb = boots[boots.held_out_basin == r.basin].iloc[0]
        L.append(f"     MAE difference (oos - no excess) {bb.mae_diff_oos_minus_clean:+.3f}, 90% block bootstrap "
                 f"{bb.boot_lo90:+.3f} to {bb.boot_hi90:+.3f} ({bb.n_heavy_blocks} blocks; descriptive)")
    pooled = tab[tab.basin == "barataria+breton"].iloc[0]
    L += ["", f"Pooled Barataria+Breton heavy (n={pooled.n_cells}, descriptive): no excess {pooled.mae_clean:.3f} / "
          f"{pooled.bias_clean:+.3f}; out-of-sample {pooled.mae_oos:.3f} / {pooled.bias_oos:+.3f}",
          "", f"GATE 0.1: {'PASSED' if passed else 'FAILED'}"]
    text = "\n".join(L) + "\n"
    (RESULTS / "oil_excess_summary.txt").write_text(text)
    print(text)
    return {"passed": passed, "gates": gates, "estimates": est, "table": tab}


if __name__ == "__main__":
    run()
