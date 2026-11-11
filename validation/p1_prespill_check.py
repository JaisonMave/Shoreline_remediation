"""P1 checks of the NAIP edge-loss result (plan: docs/P1_PRESPILL_CHECK_PLAN.md). Run once.

  1 instrument check   Landsat edge loss 2008.6 -> 2015.6 (epochs B -> C), Heavy vs clean
  2 pre-spill placebo  Landsat edge loss 1999.6 -> 2008.6 (epochs A -> B), before any oil
  3 adjusted effect    (B -> C rate) - (A -> B rate) per cell
  4 finer exposure     NAIP 2010-2015 model + open water within 250 m + log mean fetch

Model in every check: rate ~ oiling class (NOO reference) + open water within 1 km (2010) + 2 km block,
least squares, standard errors clustered by 2 km block, 90% intervals.

Run:  python -m validation.p1_prespill_check data/external/p1
Inputs: data/external/naip_edge/{cells_10A.csv, cell_land_by_year.csv};
        <p1 dir>/{landsat_cell_fraction.csv, exposure.csv}
Writes results/p1_prespill/{summary.csv, checks.csv}
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from validation.naip_edge_loss import CLASSES, cell_rates, fit  # noqa: E402

RESULTS = ROOT / "results" / "p1_prespill"
NAIP = ROOT / "data" / "external" / "naip_edge"
MID = {"A": 1999.55, "B": 2008.55, "C": 2015.55}  # mid-points of April-October in each epoch's years
HEAVY = "C(max_oiling, Treatment('NOO'))[T.Heavy]"
FORMULA = "rate ~ C(max_oiling, Treatment('NOO')) + water_1km_2010 + C(cell_2km)"
NAIP_PRIMARY = (1.003, 0.578, 1.428)  # results/naip_edge_loss/summary.csv, 2010-2015


def landsat_panel(p1_dir: Path, naip_dir: Path = NAIP) -> pd.DataFrame:
    cells = pd.read_csv(naip_dir / "cells_10A.csv")
    land = pd.read_csv(naip_dir / "cell_land_by_year.csv")
    l10 = land[land.year == 2010].set_index("cell")
    keep = l10[(l10.land_fraction.between(0.1, 0.9)) & (l10.valid_fraction >= 0.9)].index
    ls = pd.read_csv(p1_dir / "landsat_cell_fraction.csv")
    ls = ls[ls.valid_fraction >= 0.9]
    wide = ls.pivot(index="cell", columns="epoch", values="land_fraction").add_prefix("f_")  # "C" would clash with patsy's C()
    d = cells.set_index("cell").loc[lambda x: x.index.isin(keep)].join(wide, how="inner")
    d["rate_AB"] = (d["f_A"] - d["f_B"]) * 100 / (MID["B"] - MID["A"])
    d["rate_BC"] = (d["f_B"] - d["f_C"]) * 100 / (MID["C"] - MID["B"])
    d["max_oiling"] = pd.Categorical(d.max_oiling, CLASSES)
    return d.reset_index()


def heavy_row(name: str, d: pd.DataFrame, formula: str = FORMULA) -> dict:
    d = d.dropna(subset=["rate"])
    m = fit(d, formula)
    lo, hi = m.conf_int(alpha=0.10).loc[HEAVY]
    noo = d[d.max_oiling == "NOO"].rate
    return {"check": name, "cells": len(d), "heavy_cells": int((d.max_oiling == "Heavy").sum()),
            "blocks_2km": d.cell_2km.nunique(), "noo_mean_rate": round(float(noo.mean()), 3),
            "heavy_effect": round(float(m.params[HEAVY]), 3), "lo": round(float(lo), 3), "hi": round(float(hi), 3),
            "p": round(float(m.pvalues[HEAVY]), 4), "excludes_zero": bool(lo > 0 or hi < 0)}


def judge(c1: dict, c2: dict, c4: dict) -> str:
    if not (c1["excludes_zero"] and c1["heavy_effect"] > 0):
        return "Inconclusive: Landsat does not see the post-spill effect (check 1), so the pre-spill check cannot be read."
    pre_ok = (not c2["excludes_zero"]) and abs(c2["heavy_effect"]) < 0.5 * c1["heavy_effect"]
    exp_ok = c4["excludes_zero"] and c4["heavy_effect"] > 0
    if pre_ok and exp_ok:
        return "Holds: no pre-spill difference and the effect survives finer exposure."
    if not pre_ok:
        return "Revised: part of the gap predates the spill; use the check 3 estimate as the headline."
    return "Revised: the effect does not survive finer exposure (check 4)."


def main(p1_dir: str) -> None:
    p1 = Path(p1_dir); RESULTS.mkdir(parents=True, exist_ok=True)
    d = landsat_panel(p1)
    c1 = heavy_row("1 instrument: Landsat 2008.6-2015.6", d.assign(rate=d.rate_BC))
    c2 = heavy_row("2 placebo: Landsat 1999.6-2008.6", d.assign(rate=d.rate_AB))
    c3 = heavy_row("3 adjusted: (B-C) minus (A-B)", d.assign(rate=d.rate_BC - d.rate_AB))
    naip = cell_rates(NAIP, 2015).merge(pd.read_csv(p1 / "exposure.csv"), on="cell")
    naip["log_fetch"] = np.log(naip.fetch_mean_m + 16)  # +16 m (one pixel) so zero fetch is defined
    c0 = heavy_row("0 reference: NAIP 2010-2015 as published", naip)
    c4 = heavy_row("4 finer exposure: NAIP 2010-2015 + water 250 m + log fetch", naip,
                   FORMULA + " + water_250m_2010 + log_fetch")
    checks = pd.DataFrame([c0, c1, c2, c3, c4])
    verdict = judge(c1, c2, c4)
    checks.to_csv(RESULTS / "checks.csv", index=False)
    pd.DataFrame([{"verdict": verdict, "naip_primary_reference": NAIP_PRIMARY}]).to_csv(RESULTS / "summary.csv", index=False)
    d.to_csv(RESULTS / "landsat_cell_rates.csv", index=False)
    pd.set_option("display.width", 250)
    print(checks.to_string(index=False)); print(); print("VERDICT:", verdict)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "data" / "external" / "p1"))
