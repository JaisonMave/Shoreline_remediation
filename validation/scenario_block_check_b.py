"""Check C2b: C2 (plan A4.2) rerun with the R3 clean-edge baseline (plan: docs/R3_OIL_DOUBLE_COUNT_PLAN.md
section 4). Run once. The original C2 (results/scenario_composer/c2_block_coverage.csv etc.) is not rerun
or overwritten.

Same definition as C2: for 2 km blocks (>= 5 valid cells) in the two P2 held-out basins, natural recovery,
each cell given the oil excess only if Heavy: the composed 90% range of the block mean 2010-2015 edge loss
should contain the observed block mean NAIP rate in 80-97% of blocks. Baseline and block/within-block
residual pools now come from the clean-edge model (data/demo/p5_sites_clean_lobo.csv), same held-out-basin
leak as C2.

New bias gate (plan section 4): because a block mixes oiling classes, the heavy and NOO bias legs are
computed at single-cell resolution (sc.compose(), same machinery as C1b) over the cells that fall inside the
>= 5-cell blocks already used for the coverage gate (ASSUMED scope: cells in smaller, unused blocks are not
included). Heavy-cell bias within +/-0.25 m/yr; NOO-cell bias not worse than the ORIGINAL (v1) NOO bias for
the same cells by more than 0.1 m/yr in absolute value (computed here with the unchanged v1 model/pool, as
in C1b; no new fitting).

Run    : python -m validation.scenario_block_check_b
Writes : results/scenario_composer/{c2b_block_coverage.csv, c2b_blocks.csv, c2b_cell_bias.csv}; appends a C2b
         paragraph to results/scenario_composer/summary_v4_r3.txt.
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
from validation.scenario_composer_check import GATE, HELD_OUT, SEED  # noqa: E402
from validation.scenario_composer_check_b import HEAVY_BIAS_GATE, NOO_WORSE_GATE, RESULTS, SUMMARY, _compose_median5  # noqa: E402

N_DRAWS = 2000
MIN_CELLS = 5


def c2b(clean: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Block coverage, and the single-cell rows (heavy/NOO) inside the qualifying blocks for the bias gate."""
    rows, cell_rows = [], []
    for b in HELD_OUT:
        o = clean[clean.basin != b]
        pools = sc.split_block_residuals(o.cell_2km, o.observed_rate - o.lobo_pred_clean)
        d = clean[(clean.basin == b)]
        for blk, g in d.groupby("cell_2km"):
            if len(g) < MIN_CELLS:
                continue
            cells = pd.DataFrame({"pred_rate": g.lobo_pred_clean.to_numpy(), "max_oiling": g.max_oiling.to_numpy()})
            tidy, _ = sc.compose_block(cells, ["natural_attenuation"], horizon_years=5, n_draws=N_DRAWS, seed=SEED, residual_pools=pools)
            c = tidy[(tidy.option == "natural_attenuation") & (tidy.outcome == "mean_cumulative_edge_loss_m") & (tidy.year == 5)].iloc[0]
            lo, hi = c.lo90 / 5, c.hi90 / 5
            obs = float(g.observed_rate.mean())
            rows.append({"basin": b, "block": blk, "n_cells": len(g), "observed_block_mean": obs, "median": c["median"] / 5,
                        "lo90": lo, "hi90": hi, "covered": bool(lo <= obs <= hi)})
            for r in g.itertuples():
                if r.max_oiling in ("Heavy", "NOO"):
                    cell_rows.append({"basin": b, "block": blk, "cell": r.cell, "max_oiling": r.max_oiling,
                                      "observed_rate": r.observed_rate, "lobo_pred_clean": r.lobo_pred_clean})
    return pd.DataFrame(rows), cell_rows


def summarise(blocks: pd.DataFrame) -> pd.DataFrame:
    def agg(d, name):
        return {"basin": name, "n_blocks": len(d), "coverage": d.covered.mean(),
                "mean_observed_block": d.observed_block_mean.mean(), "mean_composed_median": d["median"].mean()}
    out = pd.DataFrame([agg(g, b) for b, g in blocks.groupby("basin")] + [agg(blocks, "pooled")])
    out["passes_80_97"] = out.coverage.between(*GATE)
    return out


def cell_bias(cell_rows: list[dict], clean: pd.DataFrame, sites: pd.DataFrame) -> pd.DataFrame:
    """Single-cell composed median (clean and, for NOO, original) for every Heavy/NOO cell in a qualifying block."""
    cells = pd.DataFrame(cell_rows).drop_duplicates(subset="cell")
    out = []
    for b in HELD_OUT:
        clean_pool = (clean.loc[clean.basin != b, "observed_rate"] - clean.loc[clean.basin != b, "lobo_pred_clean"]).to_numpy()
        orig_pool = (sites.loc[sites.basin != b, "observed_rate"] - sites.loc[sites.basin != b, "lobo_pred"]).to_numpy()
        orig_lookup = sites.loc[sites.basin == b, ["cell", "lobo_pred"]].set_index("cell")
        for r in cells[cells.basin == b].itertuples():
            _, med_c, _ = _compose_median5({"max_oiling": r.max_oiling, "pred_rate": float(r.lobo_pred_clean)}, clean_pool, N_DRAWS)
            row = {"basin": b, "cell": r.cell, "max_oiling": r.max_oiling, "observed_rate": r.observed_rate,
                  "median_clean": med_c, "bias_clean": med_c - r.observed_rate}
            if r.max_oiling == "NOO" and r.cell in orig_lookup.index:
                _, med_o, _ = _compose_median5({"max_oiling": "NOO", "pred_rate": float(orig_lookup.loc[r.cell, "lobo_pred"])},
                                               orig_pool, N_DRAWS)
                row["median_original"] = med_o
                row["bias_original"] = med_o - r.observed_rate
            out.append(row)
    return pd.DataFrame(out)


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    clean = sc._baseline_lobo()
    clean = clean[clean.observed_rate.notna() & clean.lobo_pred_clean.notna()]
    sites = se.load_sites()
    sites = sites[(sites.status == "in_scope") & sites.observed_rate.notna() & sites.lobo_pred.notna()]

    blocks, cell_rows = c2b(clean)
    cov = summarise(blocks)
    bias_cells = cell_bias(cell_rows, clean, sites)

    cov.to_csv(RESULTS / "c2b_block_coverage.csv", index=False)
    blocks.to_csv(RESULTS / "c2b_blocks.csv", index=False)
    bias_cells.to_csv(RESULTS / "c2b_cell_bias.csv", index=False)

    heavy = bias_cells[bias_cells.max_oiling == "Heavy"]
    noo = bias_cells[bias_cells.max_oiling == "NOO"].dropna(subset=["bias_original"])
    heavy_bias = float(heavy.bias_clean.mean())
    noo_bias_clean = float(noo.bias_clean.mean())
    noo_bias_original = float(noo.bias_original.mean())
    worse_by = abs(noo_bias_clean) - abs(noo_bias_original)
    passes_heavy = abs(heavy_bias) <= HEAVY_BIAS_GATE
    passes_noo = worse_by <= NOO_WORSE_GATE

    pooled = cov[cov.basin == "pooled"].iloc[0]
    L = ["", "Check C2b: C2 rerun with the R3 clean-edge baseline (plan section 4, docs/R3_OIL_DOUBLE_COUNT_PLAN.md). "
         "Run once.", ""]
    for r in cov.itertuples():
        L.append(f"  {r.basin}: {r.n_blocks} blocks, coverage {r.coverage:.3f}, mean observed block mean "
                 f"{r.mean_observed_block:.2f} m/yr, mean composed median {r.mean_composed_median:.2f} m/yr -> "
                 f"{'PASSES' if r.passes_80_97 else 'DOES NOT PASS'} 80-97%")
    L += [f"Cell-level bias within the >= {MIN_CELLS}-cell blocks used above: heavy cells (n={len(heavy)}) bias "
          f"{heavy_bias:+.3f} m/yr -> {'PASSES' if passes_heavy else 'DOES NOT PASS'} +/-0.25.",
          f"NOO cells (n={len(noo)}) bias: clean {noo_bias_clean:+.3f} m/yr, original (v1) {noo_bias_original:+.3f} m/yr; "
          f"|clean| - |original| = {worse_by:+.3f} -> {'PASSES' if passes_noo else 'DOES NOT PASS'} (gate: not worse "
          "by more than 0.10 m/yr).", "",
          f"Overall: pooled coverage {pooled.coverage:.3f} ({'PASSES' if pooled.passes_80_97 else 'DOES NOT PASS'} 80-97%).",
          f"C2b {'PASSES all gates' if pooled.passes_80_97 and passes_heavy and passes_noo else 'DOES NOT PASS all gates'}.", ""]
    with open(SUMMARY, "a") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
