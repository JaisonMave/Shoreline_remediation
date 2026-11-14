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
from validation.scenario_composer_check_b import HEAVY_BIAS_GATE, NOO_WORSE_GATE, RESULTS  # noqa: E402

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
    out.to_csv(RESULTS / "b1c_horizon_coverage.csv", index=False)
    cells.to_csv(RESULTS / "b1c_cells.csv", index=False)

    heavy = out[out.unit == "cells, oiling Heavy"].iloc[0]
    noo = out[out.unit == "cells, oiling NOO"].iloc[0]
    orig = pd.read_csv(ORIGINAL_B1)
    noo_bias_original = float(orig.loc[orig.unit == "cells, oiling NOO", "bias"].iloc[0])
    worse_by = abs(float(noo.bias)) - abs(noo_bias_original)
    passes_heavy = abs(float(heavy.bias)) <= HEAVY_BIAS_GATE
    passes_noo = worse_by <= NOO_WORSE_GATE

    print("Check B1c (scaled oil excess):")
    print(f"  matched={info['matched']} pooled_coverage={float(out[out.unit == 'cells pooled'].coverage.iloc[0]):.3f}")
    print(f"  heavy_bias={float(heavy.bias):+.3f} NOO_worse_by={worse_by:+.3f}")
    print(f"  gates -> heavy={passes_heavy}, noo={passes_noo}")


if __name__ == "__main__":
    main()
