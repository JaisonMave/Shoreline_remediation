"""Check B1 (plan: docs/SCENARIO_PROGRAMME_PLAN.md Phase B1): long-horizon forecast check. Run once.

Barataria cells with a NAIP 2010-2017 rate (results/naip_edge_loss/cell_rates.csv) AND a P2 held-out prediction (M1, model fitted on the
other basins; results/p2_basin_holdout/predictions.csv), matched on cell id. Natural-recovery option. The composed 90% range of the
2010-2017 mean edge-loss rate (cumulative loss at year 7 / 7; 2010-2017 spans 7 years, the NAIP interval averages 7.1) should contain
the observed rate in 80-97% of cells and of 2 km blocks with >= 5 matched cells. Also by oiling class, and bias (composed median minus
observed). Residual pools come from the OTHER basin (breton) only, as in C1/C2 (small leak, stated). Nothing tuned after results.

Run    : python -m validation.forecast_horizon_check
Writes : results/scenario_composer/b1_horizon_coverage.csv (+ b1_cells.csv); appends a B1 paragraph to summary.txt
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
from src.shoreline_remediation import site_evidence as se  # noqa: E402
from validation.scenario_composer_check import GATE, PRED, RESULTS, SEED  # noqa: E402

NAIP = ROOT / "results" / "naip_edge_loss" / "cell_rates.csv"
BASIN, H, N_DRAWS, MIN_CELLS = "barataria", 7, 2000, 5


def build() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    sites = se.load_sites()
    sites = sites[(sites.status == "in_scope") & sites.observed_rate.notna() & sites.lobo_pred.notna()]
    other = sites[sites.basin != BASIN]
    pool = (other.observed_rate - other.lobo_pred).to_numpy()
    pools = sc.split_block_residuals(other.cell_2km, other.observed_rate - other.lobo_pred)
    naip = pd.read_csv(NAIP, dtype={"cell": str})
    naip = naip[(naip.period == "2010-2017") & naip.rate.notna()]
    pred = pd.read_csv(PRED, dtype={"cell": str})
    pred = pred[(pred.basin == BASIN) & pred.M1.notna()]
    m = pred[["cell", "cell_2km", "max_oiling", "M1"]].merge(naip[["cell", "rate", "max_oiling", "cell_2km"]], on="cell", how="inner",
                                                             suffixes=("", "_naip"))
    info = {"naip_2010_2017_cells": int(naip.cell.nunique()), "naip_barataria_in_p2": int(naip.cell.isin(
        pd.read_csv(PRED, dtype={"cell": str}).query("basin == @BASIN").cell).sum()), "p2_barataria_with_M1": int(pred.cell.nunique()),
            "matched": len(m), "oiling_mismatch": int((m.max_oiling != m.max_oiling_naip).sum()),
            "block_mismatch": int((m.cell_2km != m.cell_2km_naip).sum())}
    rows = []
    for r in m.itertuples():
        t = sc.forecast({"max_oiling": r.max_oiling, "pred_rate": float(r.M1)}, horizons=(H,), n_draws=N_DRAWS, seed=SEED, residual_pool=pool)
        c = t.iloc[0]
        rows.append({"cell": r.cell, "block": r.cell_2km, "oiling": r.max_oiling, "observed": r.rate, "median": c["median"] / H,
                     "lo90": c.lo90 / H, "hi90": c.hi90 / H})
    cells = pd.DataFrame(rows)
    cells["covered"] = (cells.lo90 <= cells.observed) & (cells.observed <= cells.hi90)
    brow = []
    for b, g in cells.groupby("block"):
        if len(g) < MIN_CELLS:
            continue
        df = pd.DataFrame({"pred_rate": m.set_index("cell").loc[g.cell, "M1"].to_numpy(), "max_oiling": g.oiling.to_numpy()})
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
    out.to_csv(RESULTS / "b1_horizon_coverage.csv", index=False)
    cells.to_csv(RESULTS / "b1_cells.csv", index=False)
    L = ["", "Check B1 (plan Phase B1, long-horizon forecast). Run once.", "",
         f"B1: Barataria cells with a NAIP 2010-2017 rate and a P2 held-out M1 prediction; natural recovery; composed 90% range of the 2010-2017 "
         f"mean edge-loss rate (cumulative loss at year 7 / 7; ASSUMED mapping of 2010-2017 to 7 model years, NAIP interval averages 7.1 yr) vs observed. "
         f"Residual pools from Breton only (small leak as in C1). Gate 80-97% (pre-specified). One basin has a 7-year outcome and it is the basin "
         f"used to develop the methods, and cleanup is unrecorded, so this is the weakest hold-out check.",
         f"Matching: {info['naip_2010_2017_cells']} cells have a NAIP 2010-2017 rate; {info['p2_barataria_with_M1']} Barataria cells have a P2 held-out "
         f"prediction; {info['matched']} matched on cell id; oiling class mismatches {info['oiling_mismatch']}, 2 km block mismatches {info['block_mismatch']}. "
         f"Dropped: NAIP cells in Breton or outside the P2 table, and P2 cells without a valid 2010-2017 NAIP rate. Blocks: {info['blocks_total']} with "
         f"matched cells, {info['blocks_ge5']} with >= {MIN_CELLS} (used)."]
    for r in out.itertuples():
        L.append(f"  {r.unit}: n {r.n}, coverage {r.coverage:.3f}, mean observed {r.mean_observed:.3f}, mean composed median {r.mean_composed_median:.3f}, "
                 f"bias {r.bias:+.3f} m/yr -> {'PASSES' if r.passes_80_97 else 'DOES NOT PASS'} 80-97%")
    with open(RESULTS / "summary.txt", "a") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
