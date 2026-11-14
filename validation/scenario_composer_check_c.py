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

    cov.to_csv(RESULTS / "c1c_coverage.csv", index=False)
    cells.to_csv(RESULTS / "c1c_cells.csv", index=False)
    noo.to_csv(RESULTS / "c1c_noo_bias_cells.csv", index=False)

    pooled = cov[cov.basin == "pooled"].iloc[0]
    print("Check C1c (scaled oil excess):")
    print(f"  pooled coverage={pooled.coverage:.3f} heavy_bias={pooled.heavy_bias:+.3f} NOO_worse_by={worse_by:+.3f}")
    print(f"  gates -> coverage={bool(pooled.passes_80_97)}, heavy={bool(pooled.passes_heavy_bias)}, noo={passes_noo}")


if __name__ == "__main__":
    main()
