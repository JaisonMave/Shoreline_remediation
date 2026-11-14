"""Check B1b: B1 (plan Phase B1) rerun with the R3 clean-edge baseline (plan: docs/R3_OIL_DOUBLE_COUNT_PLAN.md
section 4). Run once. The original B1 (results/scenario_composer/b1_horizon_coverage.csv etc.) is not rerun
or overwritten; its NOO bias row is read (not recomputed) for the new bias gate below.

Same definition as B1: Barataria cells with a NAIP 2010-2017 rate and a clean-edge-model leave-one-basin-out
prediction (data/demo/p5_sites_clean_lobo.csv, in place of results/p2_basin_holdout/predictions.csv's M1
column); natural recovery; composed 90% range of the 2010-2017 mean edge-loss rate vs observed, by oiling
class, cells and >= 5-cell 2 km blocks. Residual pools from the other basins' clean-model residuals only
(same small leak as B1).

New bias gate (plan section 4): heavy-cell mean bias within +/-0.25 m/yr; NOO-cell bias not worse than the
ORIGINAL B1 NOO bias (read from results/scenario_composer/b1_horizon_coverage.csv, "cells, oiling NOO" row)
by more than 0.1 m/yr in absolute value.

Run    : python -m validation.forecast_horizon_check_b
Writes : results/scenario_composer/{b1b_horizon_coverage.csv, b1b_cells.csv}; appends a B1b paragraph (and
         the final R3 reading) to results/scenario_composer/summary_v4_r3.txt.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

from src.shoreline_remediation import scenario_composer as sc  # noqa: E402
from validation.scenario_composer_check import GATE, SEED  # noqa: E402
from validation.scenario_composer_check_b import HEAVY_BIAS_GATE, NOO_WORSE_GATE, RESULTS, SUMMARY  # noqa: E402

NAIP = ROOT / "results" / "naip_edge_loss" / "cell_rates.csv"
ORIGINAL_B1 = RESULTS / "b1_horizon_coverage.csv"
BASIN, H, N_DRAWS, MIN_CELLS = "barataria", 7, 2000, 5


def build() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    clean = sc._baseline_lobo()
    clean = clean[clean.observed_rate.notna() & clean.lobo_pred_clean.notna()]
    other = clean[clean.basin != BASIN]
    pool = (other.observed_rate - other.lobo_pred_clean).to_numpy()
    pools = sc.split_block_residuals(other.cell_2km, other.observed_rate - other.lobo_pred_clean)
    naip = pd.read_csv(NAIP, dtype={"cell": str})
    naip = naip[(naip.period == "2010-2017") & naip.rate.notna()]
    pred = clean[clean.basin == BASIN]
    m = pred[["cell", "cell_2km", "max_oiling", "lobo_pred_clean"]].merge(
        naip[["cell", "rate", "max_oiling", "cell_2km"]], on="cell", how="inner", suffixes=("", "_naip"))
    info = {"naip_2010_2017_cells": int(naip.cell.nunique()), "p2_barataria_with_clean_pred": int(pred.cell.nunique()),
            "matched": len(m), "oiling_mismatch": int((m.max_oiling != m.max_oiling_naip).sum()),
            "block_mismatch": int((m.cell_2km != m.cell_2km_naip).sum())}
    rows = []
    for r in m.itertuples():
        t = sc.forecast({"max_oiling": r.max_oiling, "pred_rate": float(r.lobo_pred_clean)}, horizons=(H,), n_draws=N_DRAWS,
                        seed=SEED, residual_pool=pool)
        c = t.iloc[0]
        rows.append({"cell": r.cell, "block": r.cell_2km, "oiling": r.max_oiling, "observed": r.rate, "median": c["median"] / H,
                     "lo90": c.lo90 / H, "hi90": c.hi90 / H})
    cells = pd.DataFrame(rows)
    cells["covered"] = (cells.lo90 <= cells.observed) & (cells.observed <= cells.hi90)
    brow = []
    for b, g in cells.groupby("block"):
        if len(g) < MIN_CELLS:
            continue
        df = pd.DataFrame({"pred_rate": m.set_index("cell").loc[g.cell, "lobo_pred_clean"].to_numpy(), "max_oiling": g.oiling.to_numpy()})
        t = sc.forecast(df, horizons=(H,), n_draws=N_DRAWS, seed=SEED, residual_pools=pools)
        c = t[t.outcome == "mean_cumulative_edge_loss_m"].iloc[0]
        obs = float(g.observed.mean())
        brow.append({"block": b, "n_cells": len(g), "observed": obs, "median": c["median"] / H, "lo90": c.lo90 / H, "hi90": c.hi90 / H,
                     "covered": bool(c.lo90 / H <= obs <= c.hi90 / H)})
    blocks = pd.DataFrame(brow)
    info["blocks_total"] = int(cells.block.nunique())
    info["blocks_ge5"] = len(blocks)
    return cells, blocks, info


def row(name, d):
    return {"unit": name, "n": len(d), "coverage": d.covered.mean(), "mean_observed": d.observed.mean(), "mean_composed_median": d["median"].mean(),
            "bias": (d["median"] - d.observed).mean(), "passes_80_97": bool(GATE[0] <= d.covered.mean() <= GATE[1])}


def main() -> None:
    cells, blocks, info = build()
    out = pd.DataFrame([row("cells pooled", cells), row("blocks pooled (>=5 cells)", blocks)] +
                       [row(f"cells, oiling {k}", g) for k, g in cells.groupby("oiling")])
    out.to_csv(RESULTS / "b1b_horizon_coverage.csv", index=False)
    cells.to_csv(RESULTS / "b1b_cells.csv", index=False)

    heavy = out[out.unit == "cells, oiling Heavy"].iloc[0]
    noo = out[out.unit == "cells, oiling NOO"].iloc[0]
    orig = pd.read_csv(ORIGINAL_B1)
    noo_bias_original = float(orig.loc[orig.unit == "cells, oiling NOO", "bias"].iloc[0])
    heavy_bias_original = float(orig.loc[orig.unit == "cells, oiling Heavy", "bias"].iloc[0])
    worse_by = abs(float(noo.bias)) - abs(noo_bias_original)
    passes_heavy = abs(float(heavy.bias)) <= HEAVY_BIAS_GATE
    passes_noo = worse_by <= NOO_WORSE_GATE

    L = ["", "Check B1b: B1 rerun with the R3 clean-edge baseline (plan section 4, docs/R3_OIL_DOUBLE_COUNT_PLAN.md). "
         "Run once.", "",
         f"Matching: {info['naip_2010_2017_cells']} cells have a NAIP 2010-2017 rate; {info['p2_barataria_with_clean_pred']} "
         f"Barataria cells have a clean-edge-model held-out prediction; {info['matched']} matched on cell id; oiling class "
         f"mismatches {info['oiling_mismatch']}, 2 km block mismatches {info['block_mismatch']}. Blocks: {info['blocks_total']} "
         f"with matched cells, {info['blocks_ge5']} with >= {MIN_CELLS} (used)."]
    for r in out.itertuples():
        L.append(f"  {r.unit}: n {r.n}, coverage {r.coverage:.3f}, mean observed {r.mean_observed:.3f}, mean composed median "
                 f"{r.mean_composed_median:.3f}, bias {r.bias:+.3f} m/yr -> {'PASSES' if r.passes_80_97 else 'DOES NOT PASS'} 80-97%")
    L += [f"Heavy-cell bias: clean {float(heavy.bias):+.3f} m/yr (original v1 was {heavy_bias_original:+.3f}) -> "
          f"{'PASSES' if passes_heavy else 'DOES NOT PASS'} +/-0.25.",
          f"NOO-cell bias: clean {float(noo.bias):+.3f} m/yr, original (v1, read from b1_horizon_coverage.csv) "
          f"{noo_bias_original:+.3f} m/yr; |clean| - |original| = {worse_by:+.3f} -> "
          f"{'PASSES' if passes_noo else 'DOES NOT PASS'} (gate: not worse by more than 0.10 m/yr).", ""]
    all_pass_cells = bool(row("cells pooled", cells)["passes_80_97"]) and passes_heavy and passes_noo
    L.append(f"B1b {'PASSES all gates (cells pooled coverage + bias)' if all_pass_cells else 'DOES NOT PASS all gates'}.")
    with open(SUMMARY, "a") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
