"""Check C1 of the scenario composer (plan: docs/SCENARIO_PROGRAMME_PLAN.md A2) and the worked-example composition. Run once.

C1: for heavily oiled in-scope cells of the two P2 held-out basins (barataria, breton), the composed 90% range of the
2010-2015 mean edge loss under natural recovery should contain the observed NAIP rate in 80-97% of cells. Reported whether
or not it passes. Mean 2010-2015 rate = cumulative loss at year 5 / 5 (years 1-2 use the 0-2 oil excess, years 3-5 the
2-8 one). The baseline for each cell is its P2 held-out M1 prediction (basin predicted by a model fitted on the other
basins); the residual pool is the leave-one-basin-out residuals of the OTHER basin(s) only, taken from data/demo/p5_sites.csv
(those residuals come from models that did include the held-out basin in training: a small leak, stated). NAIP reads about
1.2 m/yr below field erosion measurements, which is expected to push coverage down.

Run    : python -m validation.scenario_composer_check
Writes : results/scenario_composer/{c1_coverage.csv, c1_cells.csv, summary.txt, worked_example.csv}
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

RESULTS = ROOT / "results" / "scenario_composer"
PRED = ROOT / "results" / "p2_basin_holdout" / "predictions.csv"
SEED, N_DRAWS = 20261112, 5000
HELD_OUT = ("barataria", "breton")
GATE = (0.80, 0.97)
WORKED_CELL = "8018_32612"
WORKED_OPTIONS = ["natural_attenuation", "manual_removal", "mechanical_removal", "planting (after mechanical cleanup)"]


def c1() -> tuple[pd.DataFrame, pd.DataFrame]:
    sites = se.load_sites()
    sites = sites[(sites.status == "in_scope") & sites.observed_rate.notna() & sites.lobo_pred.notna()]
    resid = sites.assign(res=sites.observed_rate - sites.lobo_pred)
    pred = pd.read_csv(PRED, dtype={"cell": str})
    rows = []
    for b in HELD_OUT:
        pool = resid.loc[resid.basin != b, "res"].to_numpy()
        cells = pred[(pred.basin == b) & (pred.max_oiling == "Heavy") & pred.rate.notna()].merge(
            sites[["cell"] + se.FEATURES], on="cell", how="left")
        for r in cells.itertuples():
            site = {f: getattr(r, f) for f in se.FEATURES}
            site.update(max_oiling="Heavy", pred_rate=float(r.M1))
            tidy, _ = sc.compose(site, ["natural_attenuation"], horizon_years=5, n_draws=N_DRAWS, seed=SEED, residual_pool=pool)
            c = tidy[(tidy.option == "natural_attenuation") & (tidy.outcome == "cumulative_edge_loss_m") & (tidy.year == 5)].iloc[0]
            lo, med, hi = c.lo90 / 5, c["median"] / 5, c.hi90 / 5
            rows.append({"basin": b, "cell": r.cell, "observed_rate": r.rate, "pred_M1": r.M1, "median": med, "lo90": lo, "hi90": hi,
                         "covered": bool(lo <= r.rate <= hi)})
    cells = pd.DataFrame(rows)
    g = cells.groupby("basin").agg(n_heavy_cells=("covered", "size"), coverage=("covered", "mean"),
                                   mean_observed=("observed_rate", "mean"), mean_median=("median", "mean")).reset_index()
    pooled = pd.DataFrame([{"basin": "pooled", "n_heavy_cells": len(cells), "coverage": cells.covered.mean(),
                            "mean_observed": cells.observed_rate.mean(), "mean_median": cells["median"].mean()}])
    out = pd.concat([g, pooled], ignore_index=True)
    out["passes_80_97"] = out.coverage.between(*GATE)
    return out, cells


def worked_example() -> pd.DataFrame:
    s = se.load_sites().set_index("cell").loc[WORKED_CELL]
    site = {f: float(s[f]) for f in se.FEATURES}
    site["max_oiling"] = s.max_oiling
    tidy, summ = sc.compose(site, WORKED_OPTIONS, horizon_years=8, n_draws=N_DRAWS, seed=SEED)
    return tidy.merge(summ[["option"] + [c for c in summ.columns if c.startswith(("p_", "edge_cannot", "veg_cannot", "paired"))]],
                      on="option", how="left")


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    cov, cells = c1()
    cov.to_csv(RESULTS / "c1_coverage.csv", index=False)
    cells.to_csv(RESULTS / "c1_cells.csv", index=False)
    wx = worked_example()
    wx.to_csv(RESULTS / "worked_example.csv", index=False)
    pooled = cov[cov.basin == "pooled"].iloc[0]
    L = ["Scenario composer check C1 (plan A2, docs/SCENARIO_PROGRAMME_PLAN.md). Run once.", "",
         "C1: composed 90% range of the 2010-2015 mean edge loss (natural recovery) vs observed NAIP rate, heavily oiled cells,",
         "baseline = P2 held-out M1 prediction, residual pool from the other basin(s). Gate: coverage 80-97% (pre-specified).", ""]
    for r in cov.itertuples():
        L.append(f"  {r.basin}: {r.n_heavy_cells} heavy cells, coverage {r.coverage:.3f}, mean observed {r.mean_observed:.2f} m/yr, "
                 f"mean composed median {r.mean_median:.2f} m/yr -> {'PASSES' if r.passes_80_97 else 'DOES NOT PASS'} 80-97%")
    L += ["", f"Overall (pooled over both held-out basins): coverage {pooled.coverage:.3f} -> {'PASSES' if pooled.passes_80_97 else 'DOES NOT PASS'}.",
          "Reported whether or not it passes. NAIP reads about 1.2 m/yr below field erosion measurements, which pushes coverage",
          "down; the composed oil excess comes from aerial-photo field plots at one bay (Bay Jimmy). Residual pools come from",
          "leave-one-basin-out predictions made by models that included the held-out basin in training (small leak).", ""]
    s = wx[wx.outcome == "cumulative_edge_loss_m"]
    L.append(f"Worked example cell {WORKED_CELL} (Bay Jimmy cell of docs/P5_WORKED_EXAMPLE.md): cumulative edge loss, m, median (90% range)")
    for opt in WORKED_OPTIONS:
        parts = []
        for y in sc.SUMMARY_YEARS:
            r = s[(s.option == opt) & (s.year == y)].iloc[0]
            parts.append(f"y{y} {r['median']:.1f} ({r.lo90:.1f} to {r.hi90:.1f})")
        r8 = s[(s.option == opt) & (s.year == 8)].iloc[0]
        p = r8.p_less_edge_loss_than_natural_y8
        L.append(f"  {opt}: " + "; ".join(parts) + ("" if pd.isna(p) else f"; P(less than natural, y8) {p:.2f}")
                 + ("" if opt == "natural_attenuation" else f"; ranges overlap natural: {bool(r8.edge_cannot_be_distinguished_y8)}"))
    L += ["Most of each range is baseline uncertainty shared by all options (the paired difference is much narrower), so ranges",
          "overlap natural recovery even where the paired probability is high. See worked_example.csv."]
    (RESULTS / "summary.txt").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
