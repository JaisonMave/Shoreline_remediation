"""Check C1b: C1 (plan A2) rerun with the R3 clean-edge baseline (plan: docs/R3_OIL_DOUBLE_COUNT_PLAN.md
section 4). Run once. The original C1 (results/scenario_composer/c1_coverage.csv etc.) is not rerun or
overwritten.

Same definition as C1: for heavily oiled in-scope cells of the two P2 held-out basins (barataria, breton),
the composed 90% range of the 2010-2015 mean edge loss under natural recovery should contain the observed
NAIP rate in 80-97% of cells. The baseline for each cell is now its clean-edge-model leave-one-basin-out
prediction (data/demo/p5_sites_clean_lobo.csv), and the residual pool is the clean-edge model's own
leave-one-basin-out residuals of the OTHER basin(s) only (same small leak as C1, now on the clean model).

New bias gate (plan section 4): heavy-cell mean bias (composed median minus observed) within +/-0.25 m/yr,
and NOO-cell bias not worse than the ORIGINAL (v1-baseline) NOO bias for the same cells by more than
0.1 m/yr in absolute value. C1 itself never tested NOO cells, so the original NOO bias is computed here,
using the unchanged v1 model/pool, purely for this comparison (no new fitting; same compose() machinery).

Run    : python -m validation.scenario_composer_check_b
Writes : results/scenario_composer/{c1b_coverage.csv, c1b_cells.csv, c1b_noo_bias_cells.csv}; appends a C1b
         paragraph to results/scenario_composer/summary_v4_r3.txt (new file; summary.txt is not touched).
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

N_DRAWS = 5000
RESULTS = ROOT / "results" / "scenario_composer"
SUMMARY = RESULTS / "summary_v4_r3.txt"
HEAVY_BIAS_GATE = 0.25
NOO_WORSE_GATE = 0.10


def _compose_median5(site: dict, pool: np.ndarray, n_draws: int = N_DRAWS) -> tuple[float, float, float]:
    tidy, _ = sc.compose(site, ["natural_attenuation"], horizon_years=5, n_draws=n_draws, seed=SEED, residual_pool=pool)
    c = tidy[(tidy.option == "natural_attenuation") & (tidy.outcome == "cumulative_edge_loss_m") & (tidy.year == 5)].iloc[0]
    return c.lo90 / 5, c["median"] / 5, c.hi90 / 5


def heavy_coverage(clean: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for b in HELD_OUT:
        pool = (clean.loc[clean.basin != b, "observed_rate"] - clean.loc[clean.basin != b, "lobo_pred_clean"]).to_numpy()
        cells = clean[(clean.basin == b) & (clean.max_oiling == "Heavy")]
        for r in cells.itertuples():
            site = {"max_oiling": "Heavy", "pred_rate": float(r.lobo_pred_clean)}
            lo, med, hi = _compose_median5(site, pool)
            rows.append({"basin": b, "cell": r.cell, "observed_rate": r.observed_rate, "pred_clean": r.lobo_pred_clean,
                        "median": med, "lo90": lo, "hi90": hi, "covered": bool(lo <= r.observed_rate <= hi)})
    cells = pd.DataFrame(rows)
    g = cells.groupby("basin").agg(n_heavy_cells=("covered", "size"), coverage=("covered", "mean"),
                                   mean_observed=("observed_rate", "mean"), mean_median=("median", "mean")).reset_index()
    pooled = pd.DataFrame([{"basin": "pooled", "n_heavy_cells": len(cells), "coverage": cells.covered.mean(),
                            "mean_observed": cells.observed_rate.mean(), "mean_median": cells["median"].mean()}])
    out = pd.concat([g, pooled], ignore_index=True)
    out["passes_80_97"] = out.coverage.between(*GATE)
    out["heavy_bias"] = out.mean_median - out.mean_observed
    out["passes_heavy_bias"] = out.heavy_bias.abs() <= HEAVY_BIAS_GATE
    return out, cells


def noo_bias(clean: pd.DataFrame, sites: pd.DataFrame) -> pd.DataFrame:
    """NOO-cell bias, clean baseline vs the original (v1) baseline, same held-out basins and cells."""
    rows = []
    for b in HELD_OUT:
        clean_pool = (clean.loc[clean.basin != b, "observed_rate"] - clean.loc[clean.basin != b, "lobo_pred_clean"]).to_numpy()
        orig_pool = (sites.loc[sites.basin != b, "observed_rate"] - sites.loc[sites.basin != b, "lobo_pred"]).to_numpy()
        noo_clean = clean[(clean.basin == b) & (clean.max_oiling == "NOO")]
        noo_orig = sites.loc[(sites.basin == b) & (sites.max_oiling == "NOO"), ["cell", "lobo_pred"]].set_index("cell")
        for r in noo_clean.itertuples():
            if r.cell not in noo_orig.index:
                continue
            _, med_c, _ = _compose_median5({"max_oiling": "NOO", "pred_rate": float(r.lobo_pred_clean)}, clean_pool)
            _, med_o, _ = _compose_median5({"max_oiling": "NOO", "pred_rate": float(noo_orig.loc[r.cell, "lobo_pred"])}, orig_pool)
            rows.append({"basin": b, "cell": r.cell, "observed_rate": r.observed_rate,
                        "median_clean": med_c, "median_original": med_o})
    return pd.DataFrame(rows)


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    clean = sc._baseline_lobo()
    clean = clean[clean.observed_rate.notna() & clean.lobo_pred_clean.notna()]
    sites = se.load_sites()
    sites = sites[(sites.status == "in_scope") & sites.observed_rate.notna() & sites.lobo_pred.notna()]

    cov, cells = heavy_coverage(clean)
    noo = noo_bias(clean, sites)
    noo["bias_clean"] = noo.median_clean - noo.observed_rate
    noo["bias_original"] = noo.median_original - noo.observed_rate
    noo_bias_clean = float(noo.bias_clean.mean())
    noo_bias_original = float(noo.bias_original.mean())
    worse_by = abs(noo_bias_clean) - abs(noo_bias_original)
    passes_noo = worse_by <= NOO_WORSE_GATE

    cov.to_csv(RESULTS / "c1b_coverage.csv", index=False)
    cells.to_csv(RESULTS / "c1b_cells.csv", index=False)
    noo.to_csv(RESULTS / "c1b_noo_bias_cells.csv", index=False)

    pooled = cov[cov.basin == "pooled"].iloc[0]
    L = ["Check C1b: C1 rerun with the R3 clean-edge baseline (plan section 4, docs/R3_OIL_DOUBLE_COUNT_PLAN.md). "
         "Run once.", ""]
    for r in cov.itertuples():
        L.append(f"  {r.basin}: {r.n_heavy_cells} heavy cells, coverage {r.coverage:.3f}, mean observed {r.mean_observed:.2f} "
                 f"m/yr, mean composed median {r.mean_median:.2f} m/yr, heavy bias {r.heavy_bias:+.3f} m/yr -> "
                 f"{'PASSES' if r.passes_80_97 else 'DOES NOT PASS'} 80-97% coverage, "
                 f"{'PASSES' if r.passes_heavy_bias else 'DOES NOT PASS'} heavy bias +/-0.25")
    L += [f"NOO-cell bias (same held-out cells, n={len(noo)}): clean {noo_bias_clean:+.3f} m/yr, original (v1) "
          f"{noo_bias_original:+.3f} m/yr; |clean| - |original| = {worse_by:+.3f} -> "
          f"{'PASSES' if passes_noo else 'DOES NOT PASS'} (gate: not worse by more than 0.10 m/yr).", "",
          f"Overall: pooled coverage {pooled.coverage:.3f} ({'PASSES' if pooled.passes_80_97 else 'DOES NOT PASS'} 80-97%), "
          f"pooled heavy bias {pooled.heavy_bias:+.3f} m/yr ({'PASSES' if pooled.passes_heavy_bias else 'DOES NOT PASS'} "
          f"+/-0.25), NOO bias gate {'PASSES' if passes_noo else 'DOES NOT PASS'}.",
          f"C1b {'PASSES all gates' if pooled.passes_80_97 and pooled.passes_heavy_bias and passes_noo else 'DOES NOT PASS all gates'}.", ""]
    with open(SUMMARY, "a") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
