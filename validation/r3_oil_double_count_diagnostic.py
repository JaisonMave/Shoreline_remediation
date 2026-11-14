"""R3 diagnostic (plan: docs/R3_OIL_DOUBLE_COUNT_PLAN.md section 2). Run once, before any fix is built.

Mean in-sample M1 residual (observed minus fitted), by SCAT maximum-oiling class, in the exact training
panel used to build models/p5_edge_loss_v1.json, with 90% cluster-bootstrap intervals by 2 km block
(cell_2km). Confirms the suspected double count if the Heavy interval lies entirely above zero.

Run    : python -m validation.r3_oil_double_count_diagnostic
Writes : results/scenario_composer/r3_diagnostic.csv; creates results/scenario_composer/summary_v4_r3.txt
         (new file; results/scenario_composer/summary.txt, the C1/C2/B1 record, is not touched).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from validation.naip_edge_loss import CLASSES  # noqa: E402
from validation.p2_basin_holdout import BASINS, EXPOSURE, load_basin  # noqa: E402

P2 = ROOT / "data" / "external" / "p2"
MODEL_V1 = ROOT / "models" / "p5_edge_loss_v1.json"
RESULTS = ROOT / "results" / "scenario_composer"
SUMMARY = RESULTS / "summary_v4_r3.txt"
N_BOOT = 2000           # ASSUMED, plan section 2
SEED = 20261112


def fit_m1(d: pd.DataFrame):
    return sm.OLS(d.rate.values, sm.add_constant(d[EXPOSURE].astype(float), has_constant="add")).fit()


def cluster_bootstrap_mean_ci(blocks: np.ndarray, classes: np.ndarray, residual: np.ndarray, target_class: str,
                              n_boot: int, rng: np.random.Generator) -> tuple[float, float, int]:
    """90% interval of the mean residual for `target_class`, resampling that class's own 2 km blocks with
    replacement (same number of blocks as observed), keeping every cell of each drawn block that belongs to
    the class (so a block drawn twice counts its cells twice, standard cluster bootstrap)."""
    mask = classes == target_class
    cls_blocks, cls_res = blocks[mask], residual[mask]
    uniq = pd.unique(cls_blocks)
    if len(uniq) == 0:
        return float("nan"), float("nan"), n_boot
    by_block = {b: cls_res[cls_blocks == b] for b in uniq}
    means, dropped = [], 0
    for _ in range(n_boot):
        drawn = rng.choice(uniq, size=len(uniq), replace=True)
        vals = np.concatenate([by_block[b] for b in drawn])
        if vals.size == 0:
            dropped += 1
            continue
        means.append(vals.mean())
    means = np.asarray(means)
    lo, hi = (float("nan"), float("nan")) if len(means) == 0 else (float(np.quantile(means, 0.05)), float(np.quantile(means, 0.95)))
    return lo, hi, dropped


def main() -> None:
    import json
    panel = pd.concat([load_basin(P2 / b, b) for b in BASINS])
    m1 = fit_m1(panel)

    card = json.loads(MODEL_V1.read_text())
    max_diff = float(np.max(np.abs(np.array(card["coefficients"]) - m1.params.values)))
    matches = max_diff < 1e-6

    fitted = m1.predict(sm.add_constant(panel[EXPOSURE].astype(float), has_constant="add")).values
    residual = panel.rate.values - fitted
    blocks = panel.cell_2km.to_numpy()
    classes = panel.max_oiling.astype(str).to_numpy()

    rng = np.random.default_rng(SEED)
    rows = []
    for c in CLASSES:
        sel = classes == c
        lo, hi, dropped = cluster_bootstrap_mean_ci(blocks, classes, residual, c, N_BOOT, rng)
        rows.append({"oiling_class": c, "n_cells": int(sel.sum()), "n_blocks": int(pd.unique(blocks[sel]).size),
                     "mean_residual": float(residual[sel].mean()), "ci_lo90": lo, "ci_hi90": hi,
                     "n_bootstrap_draws": N_BOOT, "n_dropped_resamples": dropped,
                     "confirmed_above_zero": bool(lo > 0) if not np.isnan(lo) else False})
    out = pd.DataFrame(rows)
    RESULTS.mkdir(parents=True, exist_ok=True)
    out.to_csv(RESULTS / "r3_diagnostic.csv", index=False)

    heavy = out[out.oiling_class == "Heavy"].iloc[0]
    noo = out[out.oiling_class == "NOO"].iloc[0]
    L = ["R3 diagnostic (plan docs/R3_OIL_DOUBLE_COUNT_PLAN.md section 2). Run once, before any fix.", "",
         f"Refit M1 on the full {len(panel)}-cell p5-edge-loss-v1 training panel; max |coefficient difference| vs the "
         f"deployed model card = {max_diff:.2e} -> {'matches' if matches else 'DOES NOT MATCH'} models/p5_edge_loss_v1.json."]
    if not matches:
        L.append("Numbers below do not reliably describe the deployed model (refit mismatch); treat with caution.")
    L += ["", "Mean in-sample residual (observed minus fitted) by SCAT maximum oiling class, 90% cluster bootstrap "
          f"by 2 km block ({N_BOOT} resamples):"]
    for r in out.itertuples():
        L.append(f"  {r.oiling_class}: n {r.n_cells} cells, {r.n_blocks} blocks, mean residual {r.mean_residual:+.3f} m/yr, "
                 f"90% CI ({r.ci_lo90:+.3f} to {r.ci_hi90:+.3f}), {r.n_dropped_resamples} resamples dropped (no cells of this "
                 f"class drawn)")
    confirmed = bool(heavy.confirmed_above_zero)
    L += ["", f"Confirmation rule (pre-specified): Heavy interval entirely above zero -> "
          f"{'CONFIRMED' if confirmed else 'NOT CONFIRMED'}: {heavy.mean_residual:+.3f} m/yr "
          f"({heavy.ci_lo90:+.3f} to {heavy.ci_hi90:+.3f})."]
    if not confirmed:
        L.append("Per the plan, the fix is still built and C1b/C2b/B1b are still run exactly as pre-specified; the "
                 "final reading will say the diagnostic did not confirm the mechanism and will rely on the b-checks' "
                 "own bias numbers.")
    L += [f"For reference, NOO (clean, used only as a sanity reference, not part of the confirmation rule): "
          f"{noo.mean_residual:+.3f} m/yr ({noo.ci_lo90:+.3f} to {noo.ci_hi90:+.3f})."]
    SUMMARY.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
