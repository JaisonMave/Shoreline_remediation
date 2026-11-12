"""Check C2 of the block-level composer (plan: docs/SCENARIO_PROGRAMME_PLAN.md A4.2) and the worked block. Run once.

C2: for 2 km blocks (cell_2km) with at least 5 valid cells in the two P2 held-out basins (barataria, breton), natural-recovery
option, each cell given its own oiling class effect only if Heavy: the composed 90% range of the block mean 2010-2015 edge loss
(mean over cells of cumulative loss at year 5, divided by 5) should contain the observed block mean (mean NAIP rate over the
block's valid cells) in 80-97% of blocks. Blocks are the unit. Baseline per cell = P2 held-out M1 prediction; the block and
within-block residual pools come from the OTHER basin(s) only (leave-one-basin-out residuals of data/demo/p5_sites.csv; small
leak as in C1). Report per basin and pooled, with the median width of the block range against the median width of the cell range
(compose(), same pool, each cell's own oiling class). Nothing is tuned after seeing coverage.

Run    : python -m validation.scenario_block_check
Writes : results/scenario_composer/{c2_block_coverage.csv, worked_block.csv}; appends a C2 paragraph to summary.txt
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
from validation.scenario_composer_check import GATE, HELD_OUT, PRED, RESULTS, SEED, WORKED_CELL  # noqa: E402

N_DRAWS = 2000
MIN_CELLS = 5
ELICITED_PRIORS = ROOT / "data" / "knowledge" / "elicited_priors.csv"


def c2() -> pd.DataFrame:
    sites = se.load_sites()
    sites = sites[(sites.status == "in_scope") & sites.observed_rate.notna() & sites.lobo_pred.notna()]
    pred = pd.read_csv(PRED, dtype={"cell": str})
    rows = []
    for b in HELD_OUT:
        o = sites[sites.basin != b]
        pools = sc.split_block_residuals(o.cell_2km, o.observed_rate - o.lobo_pred)
        full_pool = (o.observed_rate - o.lobo_pred).to_numpy()
        d = pred[(pred.basin == b) & pred.rate.notna() & pred.M1.notna()]
        for blk, g in d.groupby("cell_2km"):
            if len(g) < MIN_CELLS:
                continue
            cells = pd.DataFrame({"pred_rate": g.M1.to_numpy(), "max_oiling": g.max_oiling.to_numpy()})
            tidy, _ = sc.compose_block(cells, ["natural_attenuation"], horizon_years=5, n_draws=N_DRAWS, seed=SEED, residual_pools=pools)
            c = tidy[(tidy.option == "natural_attenuation") & (tidy.outcome == "mean_cumulative_edge_loss_m") & (tidy.year == 5)].iloc[0]
            lo, hi = c.lo90 / 5, c.hi90 / 5
            cw = []
            for r in g.itertuples():
                t, _ = sc.compose({"max_oiling": r.max_oiling, "pred_rate": float(r.M1)}, ["natural_attenuation"], horizon_years=5,
                                  n_draws=N_DRAWS, seed=SEED, residual_pool=full_pool)
                x = t[(t.outcome == "cumulative_edge_loss_m") & (t.year == 5)].iloc[0]
                cw.append((x.hi90 - x.lo90) / 5)
            obs = float(g.rate.mean())
            rows.append({"basin": b, "block": blk, "n_cells": len(g), "observed_block_mean": obs, "median": c["median"] / 5, "lo90": lo, "hi90": hi,
                         "covered": bool(lo <= obs <= hi), "block_width": hi - lo, "median_cell_width": float(np.median(cw))})
    return pd.DataFrame(rows)


def summarise(blocks: pd.DataFrame) -> pd.DataFrame:
    def agg(d, name):
        return {"basin": name, "n_blocks": len(d), "coverage": d.covered.mean(), "median_block_width": d.block_width.median(),
                "median_cell_width": d.median_cell_width.median(), "mean_observed_block": d.observed_block_mean.mean(),
                "mean_composed_median": d["median"].mean()}
    out = pd.DataFrame([agg(g, b) for b, g in blocks.groupby("basin")] + [agg(blocks, "pooled")])
    out["passes_80_97"] = out.coverage.between(*GATE)
    return out


def worked_block() -> tuple[pd.DataFrame, int, str]:
    s = se.load_sites()
    blk = s.loc[s.cell == WORKED_CELL, "cell_2km"].iloc[0]
    cells = s[(s.cell_2km == blk) & (s.status == "in_scope")].reset_index(drop=True)
    pri = pd.read_csv(ELICITED_PRIORS)
    pri = pri[pri.tool_code.notna() & (pri.tool_code != "")]
    elicited = {r.tool_code: (float(r.tau_multiplier_lo), float(r.tau_multiplier_hi)) for r in pri.itertuples()}
    options = ["natural_attenuation", "manual_removal", "mechanical_removal", sc.PLANTING] + list(elicited)
    tidy, summ = sc.compose_block(cells, options, horizon_years=8, n_draws=N_DRAWS, seed=SEED, elicited=elicited)
    keep = [c for c in summ.columns if c.startswith(("paired", "area_dist")) or c in ("option", "n_cells", "n_heavy_cells")]
    return tidy.merge(summ[keep], on="option", how="left"), len(cells), blk


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    blocks = c2()
    cov = summarise(blocks)
    cov.to_csv(RESULTS / "c2_block_coverage.csv", index=False)
    blocks.to_csv(RESULTS / "c2_blocks.csv", index=False)
    wb, n_cells, blk = worked_block()
    wb.to_csv(RESULTS / "worked_block.csv", index=False)
    L = ["", "Check C2 (plan A4.2, block-level composer). Run once.", "",
         f"C2: composed 90% range of the block mean 2010-2015 edge loss (natural recovery) vs observed block mean NAIP rate, 2 km blocks with "
         f">= {MIN_CELLS} valid cells in the held-out basins; baseline = P2 held-out M1 prediction per cell, block and within-block residual pools "
         "from the other basin(s) (small leak as in C1), Heavy cells only get the oil excess. Gate: coverage 80-97% (pre-specified). Blocks are the unit."]
    for r in cov.itertuples():
        L.append(f"  {r.basin}: {r.n_blocks} blocks, coverage {r.coverage:.3f}, median block range width {r.median_block_width:.2f} m/yr vs median "
                 f"cell range width {r.median_cell_width:.2f} m/yr -> {'PASSES' if r.passes_80_97 else 'DOES NOT PASS'} 80-97%")
    L.append(f"Worked block {blk} ({n_cells} in-scope cells, containing {WORKED_CELL}): see worked_block.csv. One cell is ASSUMED to hold 100 m of edge.")
    with open(RESULTS / "summary.txt", "a") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))
    s = wb[(wb.outcome == "cumulative_area_lost_ha") & (wb.year == 8)]
    for r in s.itertuples():
        print(f"  {r.option}: median {r.median:.2f} ha ({r.lo90:.2f} to {r.hi90:.2f}); paired diff y8 {r.paired_diff_area_ha_y8_median:.3f} "
              f"({r.paired_diff_area_ha_y8_lo90:.3f} to {r.paired_diff_area_ha_y8_hi90:.3f}) distinguished {r.area_distinguished_y8}")


if __name__ == "__main__":
    main()
