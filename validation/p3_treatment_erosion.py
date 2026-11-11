"""P3: cleanup treatment and marsh-edge erosion, Zengel et al. (2022) plot data (plan: docs/P3_TREATMENT_PLAN.md).
Run once:  python -m validation.p3_treatment_erosion
Writes results/p3_treatment/{A_prespill_adjusted.csv, A2_wave_power.csv, B_field.csv, C_naip_check.csv,
C_naip_plots.csv, summary.txt}
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from pyproj import Transformer
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.shoreline_remediation.treatment_effects import welch_contrast  # noqa: E402

DATA = ROOT / "data" / "external" / "zengel2022" / "zengel2022_griidc_erosion.xlsx"
RESULTS = ROOT / "results" / "p3_treatment"
BASE = "UNTREATED"
GROUPS = {"REFERENCE": "Reference (unoiled)", "UNTREATED": "Oiled, untreated",
          "TREATED - MANUAL": "Manual", "TREATED - MECHANICAL": "Mechanical", "TREATED - PLANTED": "Mechanical + planted",
          "MAN. TREATMENT": "Manual", "MECH. TREATMENT": "Mechanical"}
CONTRASTS = [("Manual", "Oiled, untreated"), ("Mechanical", "Oiled, untreated"),
             ("Mechanical + planted", "Oiled, untreated"), ("Oiled, untreated", "Reference (unoiled)")]


def read(sheet: str) -> pd.DataFrame:
    d = pd.read_excel(DATA, sheet_name=sheet)
    if "PLOT_TYPE" in d:
        d["group"] = d.PLOT_TYPE.str.strip().map(GROUPS)
    return d


def contrasts(per_plot: pd.DataFrame, value: str, label: str) -> pd.DataFrame:
    rows = []
    for a, b in CONTRASTS:
        x, y = per_plot.loc[per_plot.group == a, value].dropna(), per_plot.loc[per_plot.group == b, value].dropna()
        if len(x) < 2 or len(y) < 2:
            rows.append({"analysis": label, "contrast": f"{a} minus {b}", "n_a": len(x), "n_b": len(y)})
            continue
        c = welch_contrast(x.mean(), x.std(ddof=1) / np.sqrt(len(x)), len(x), y.mean(), y.std(ddof=1) / np.sqrt(len(y)), len(y))
        rows.append({"analysis": label, "contrast": f"{a} minus {b}", "n_a": len(x), "n_b": len(y),
                     "mean_a": x.mean(), "mean_b": y.mean(), "difference": c["effect"], "lo90": c["lo"], "hi90": c["hi"],
                     "excludes_zero": bool(c["lo"] > 0 or c["hi"] < 0)})
    return pd.DataFrame(rows)


def prespill_change(lumped: pd.DataFrame, period: str) -> pd.DataFrame:
    w = lumped.pivot_table(index=["PLOT_ID", "group"], columns="TIME_PERIOD", values="EROSION_RATE").reset_index()
    w["change"] = w[period] - w["2005-2010"]
    return w


def analysis_a(lumped, wave):
    out, a2 = [], []
    for period in ("2010-2012", "2012-2018"):
        w = prespill_change(lumped, period)
        label = f"A {period} minus 2005-2010" + (" (primary)" if period == "2010-2012" else " (secondary)")
        out.append(contrasts(w, "change", label))
        wp = wave[wave.TIME_PERIOD == period].groupby("PLOT_ID").WE_WM.mean()
        w["log_wave"] = np.log(w.PLOT_ID.map(wp))
        m = smf.ols("change ~ C(group, Treatment('Oiled, untreated')) + log_wave", data=w).fit(cov_type="HC3")
        ci = m.conf_int(alpha=0.10)
        for k in m.params.index:
            if k.startswith("C(group"):
                a2.append({"period": period, "term": k.split("[T.")[1].rstrip("]") + " minus Oiled, untreated",
                           "estimate": m.params[k], "lo90": ci.loc[k, 0], "hi90": ci.loc[k, 1], "p": m.pvalues[k]})
        a2.append({"period": period, "term": "log wave power", "estimate": m.params["log_wave"],
                   "lo90": ci.loc["log_wave", 0], "hi90": ci.loc["log_wave", 1], "p": m.pvalues["log_wave"]})
    return pd.concat(out, ignore_index=True), pd.DataFrame(a2)


def analysis_b(field):
    per = field.groupby(["PLOT_ID", "group"]).EROSION_RATE.mean().reset_index(name="mean_2010_2016")
    return contrasts(per, "mean_2010_2016", "B field 2010-2016 mean")


def plot_positions(points: pd.DataFrame) -> pd.DataFrame:
    p = points.groupby("PLOT_ID")[["LAT_DD", "LON_DD"]].mean().reset_index()
    x, y = Transformer.from_crs(4326, 32615, always_xy=True).transform(p.LON_DD.values, p.LAT_DD.values)
    p["cell"] = (np.floor(x / 100).astype(int)).astype(str) + "_" + (np.floor(y / 100).astype(int)).astype(str)
    return p


def spearman_boot(a, b, n=2000, seed=0):
    rng = np.random.default_rng(seed); a, b = np.asarray(a), np.asarray(b)
    vals = []
    for _ in range(n):
        i = rng.integers(0, len(a), len(a))
        if len(np.unique(a[i])) > 1 and len(np.unique(b[i])) > 1:
            vals.append(stats.spearmanr(a[i], b[i])[0])
    return stats.spearmanr(a, b)[0], float(np.quantile(vals, 0.05)), float(np.quantile(vals, 0.95))


def analysis_c(annual, points, naip_rates: pd.DataFrame):
    yrs = {"2010-2011": 1, "2011-2012": 1, "2012-2013": 1, "2013-2015": 2}
    a = annual[annual.TIME_PERIOD.isin(yrs)].copy(); a["w"] = a.TIME_PERIOD.map(yrs)
    plot_rate = a.groupby("PLOT_ID").apply(lambda g: np.average(g.EROSION_RATE, weights=g.w), include_groups=False)
    pos = plot_positions(points)
    pos["plot_rate_2010_2015"] = pos.PLOT_ID.map(plot_rate)
    m = pos.merge(naip_rates[["cell", "rate"]], on="cell", how="left").rename(columns={"rate": "naip_cell_rate"})
    m["group"] = m.PLOT_ID.map(annual.drop_duplicates("PLOT_ID").set_index("PLOT_ID").group)
    ok = m.dropna(subset=["plot_rate_2010_2015", "naip_cell_rate"])
    row = {"plots_with_gps": len(pos), "plots_in_naip_cells": len(ok), "distinct_cells": ok.cell.nunique()}
    if len(ok) >= 5:
        rho, lo, hi = spearman_boot(ok.plot_rate_2010_2015, ok.naip_cell_rate)
        row.update({"spearman": rho, "lo90": lo, "hi90": hi, "tracks": bool(lo > 0),
                    "mean_naip_minus_plot": float((ok.naip_cell_rate - ok.plot_rate_2010_2015).mean()),
                    "pearson": float(stats.pearsonr(ok.plot_rate_2010_2015, ok.naip_cell_rate)[0])})
    return pd.DataFrame([row]), m


def naip_barataria_rates():
    from validation.p2_basin_holdout import load_basin
    return load_basin(ROOT / "data" / "external" / "p2" / "barataria", "barataria")


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    lumped, annual, field = read("DSAS lumped"), read("DSAS annual"), read("GIS field erosion")
    wave, points = read("Wave Power"), read("GIS field erosion points")
    A, A2 = analysis_a(lumped, wave)
    B = analysis_b(field)
    C, Cplots = analysis_c(annual, points, naip_barataria_rates())
    for name, t in [("A_prespill_adjusted", A), ("A2_wave_power", A2), ("B_field", B), ("C_naip_check", C), ("C_naip_plots", Cplots)]:
        t.round(4).to_csv(RESULTS / f"{name}.csv", index=False)
    pd.set_option("display.width", 220)
    text = "\n\n".join(t.round(3).to_string(index=False) for t in (A, A2, B, C))
    (RESULTS / "summary.txt").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
