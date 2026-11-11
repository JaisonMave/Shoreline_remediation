"""Marsh-edge loss after Deepwater Horizon oiling, Barataria Bay, from NAIP (docs/NAIP_EDGE_LOSS_PLAN.md).

Run once:  python -m validation.naip_edge_loss data/external/naip_edge
Inputs (from scripts/naip_edge_extract.py): cells_10A.csv, cell_land_by_year.csv
Writes results/naip_edge_loss/{summary.csv, coefficients.csv, cell_rates.csv, edge_loss_by_class.png}

Implementation details fixed with the plan:
  edge cell        0.1 <= land fraction 2010 <= 0.9
  valid pixels     at least 90% of the cell classified in both years (ASSUMED)
  block filter     1 km block land share within 0.15 of 2010 (ASSUMED)
  rate (m/yr)      (land_2010 - land_year) * 100 m / years between the cell's flight dates
  model            rate ~ oiling class (NOO reference) + open-water fraction within 1 km (2010) + 2 km block,
                   least squares, standard errors clustered by 2 km block, 90% intervals
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "naip_edge_loss"
CLASSES = ["NOO", "Very_Light", "Light", "Moderate", "Heavy"]
PERIODS = {"2010-2015": (2015, "primary"), "2010-2017": (2017, "secondary")}
ZENGEL_EXCESS = (1.2, 2.3)  # m/yr, Zengel et al. 2015: untreated heavy 2.4-3.1 vs reference 0.8-1.2 (2011-12)


def cell_rates(data_dir: Path, year: int) -> pd.DataFrame:
    cells = pd.read_csv(data_dir / "cells_10A.csv")
    land = pd.read_csv(data_dir / "cell_land_by_year.csv")
    a = land[land.year == 2010].set_index("cell"); b = land[land.year == year].set_index("cell")
    d = cells.set_index("cell").join(a.add_suffix("_2010")).join(b.add_suffix("_t"), how="inner")
    d = d[d.land_fraction_2010.between(0.1, 0.9)]
    d = d[(d.valid_fraction_2010 >= 0.9) & (d.valid_fraction_t >= 0.9)]
    d = d[(d.block_land_fraction_t - d.block_land_fraction_2010).abs() <= 0.15]
    years = (pd.to_datetime(d.flight_date_t) - pd.to_datetime(d.flight_date_2010)).dt.days / 365.25
    d["years"] = years
    d["rate"] = (d.land_fraction_2010 - d.land_fraction_t) * 100 / years
    d["max_oiling"] = pd.Categorical(d.max_oiling, CLASSES)
    return d.reset_index()


def fit(d: pd.DataFrame, formula: str):
    return smf.ols(formula, data=d).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.cell_2km)[0]})


def main(data_dir: str) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    rows, coefs, all_cells = [], [], []
    for label, (year, role) in PERIODS.items():
        d = cell_rates(Path(data_dir), year)
        all_cells.append(d.assign(period=label))
        full = fit(d, "rate ~ C(max_oiling, Treatment('NOO')) + water_1km_2010 + C(cell_2km)")
        ci = full.conf_int(alpha=0.10)
        for name in full.params.index:
            if name.startswith("C(max_oiling") or name == "water_1km_2010":
                cls = name.split("[T.")[-1].rstrip("]") if "[T." in name else name
                coefs.append({"period": label, "term": cls, "estimate": full.params[name], "lo": ci.loc[name, 0],
                              "hi": ci.loc[name, 1], "p": full.pvalues[name]})
        hk = "C(max_oiling, Treatment('NOO'))[T.Heavy]"
        hn = d[d.max_oiling.isin(["NOO", "Heavy"])].assign(heavy=lambda x: (x.max_oiling == "Heavy").astype(float))
        raw = fit(hn, "rate ~ heavy"); rci = raw.conf_int(alpha=0.10)
        noo = fit(d[d.max_oiling == "NOO"], "rate ~ 1"); nci = noo.conf_int(alpha=0.10)
        heavy_blocks = d[d.max_oiling == "Heavy"].cell_2km.unique()
        shared = d[d.cell_2km.isin(heavy_blocks) & (d.max_oiling == "NOO")].cell_2km.nunique()
        lo, hi = ci.loc[hk, 0], ci.loc[hk, 1]
        bench = ("overlaps" if lo <= ZENGEL_EXCESS[1] and hi >= ZENGEL_EXCESS[0] else
                 "below" if hi < ZENGEL_EXCESS[0] else "above")
        rows.append({
            "period": label, "role": role, "cells": len(d),
            **{f"n_{c}": int((d.max_oiling == c).sum()) for c in CLASSES},
            "blocks_2km": d.cell_2km.nunique(), "heavy_blocks_with_clean_cells": int(shared),
            "median_years": round(float(d.years.median()), 2),
            "noo_mean_rate": round(noo.params.iloc[0], 3), "noo_rate_90ci": f"{nci.iloc[0, 0]:.3f} to {nci.iloc[0, 1]:.3f}",
            "raw_heavy_minus_noo": round(raw.params["heavy"], 3), "raw_90ci": f"{rci.loc['heavy', 0]:.3f} to {rci.loc['heavy', 1]:.3f}",
            "heavy_effect": round(full.params[hk], 3), "heavy_90ci": f"{lo:.3f} to {hi:.3f}", "heavy_p": round(full.pvalues[hk], 4),
            "zengel_excess_1.2_to_2.3": bench,
        })
    summary = pd.DataFrame(rows); coef = pd.DataFrame(coefs).round(4)
    summary.to_csv(RESULTS / "summary.csv", index=False); coef.to_csv(RESULTS / "coefficients.csv", index=False)
    pd.concat(all_cells).to_csv(RESULTS / "cell_rates.csv", index=False)
    plot(coef)
    pd.set_option("display.width", 250)
    print(summary.T.to_string()); print(); print(coef.to_string(index=False))


def plot(coef: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 4))
    for k, (period, g) in enumerate(coef[coef.term != "water_1km_2010"].groupby("period")):
        g = g.set_index("term").reindex(CLASSES[1:])
        x = np.arange(len(g)) + (k - 0.5) * 0.25
        ax.errorbar(x, g.estimate, yerr=[g.estimate - g.lo, g.hi - g.estimate], fmt="o", capsize=3, label=period)
    ax.axhspan(*ZENGEL_EXCESS, color="#E45756", alpha=0.12, label="Zengel 2015 excess retreat")
    ax.axhline(0, color="#999", lw=0.8)
    ax.set_xticks(range(4)); ax.set_xticklabels([c.replace("_", " ") for c in CLASSES[1:]])
    ax.set_ylabel("Extra edge loss vs clean edge (m/yr)"); ax.set_xlabel("SCAT maximum oiling")
    ax.spines[["top", "right"]].set_visible(False); ax.legend(frameon=False, fontsize=8)
    fig.tight_layout(); fig.savefig(RESULTS / "edge_loss_by_class.png", dpi=150)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "data" / "external" / "naip_edge"))
