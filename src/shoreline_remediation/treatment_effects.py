"""Treatment-effect priors for heavily oiled salt marsh, from Zengel et al. (2015).

Source
------
Zengel S, Bernik BM, Rutherford N, Nixon Z, Michel J (2015). Heavily oiled salt marsh following the
Deepwater Horizon oil spill, ecological comparisons of shoreline cleanup treatments and recovery.
PLoS ONE 10(7): e0132324. doi:10.1371/journal.pone.0132324.
Values come from the authors' S1 Table (Excel, downloaded from journals.plos.org on 2026-11-11),
parsed to data/external/zengel2015/zengel2015_group_means.csv. No values were read off figures.

What the study is (and is not)
------------------------------
* One spill (Deepwater Horizon), one bay (northern Barataria Bay, LA), heavily oiled Spartina
  alterniflora marsh edge only. 2011 and 2012 surveys, i.e. about 1 and 2 years after oiling.
* Plots were placed at random WITHIN each class, but the classes themselves were not assigned at
  random: mechanical plots are where response crews worked, and untreated plots were the only
  comparable untreated areas. Pre-treatment oiling was similar across classes (2010 rows).
  So treatment contrasts are observational, not experimental.
* The planting contrast (planted vs unplanted, both inside mechanically treated areas) WAS randomly
  assigned, so it is the cleanest causal estimate here.
* n = 5 per class (9 for no treatment). Effects are therefore imprecise.

Method (fixed before computing anything)
---------------------------------------
Baseline is "No Treatment" (natural recovery). For each treatment, year and metric:
    effect   = mean(treatment) - mean(no treatment)
    SE       = sqrt(SE_t^2 + SE_nt^2)
    90% CI   = effect +/- t(0.95, Welch df) * SE
Welch df uses the Welch-Satterthwaite formula with each group's SD = SE * sqrt(n). This is the usual
two-sample t comparison allowing unequal spread; it is computed from published summary statistics.
Vegetation is also expressed as a fraction of the reference plots ("recovery fraction").

Hold-out validation across spills is impossible with one study. Treat these as priors to be
updated by other spills, never as validated predictions.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

DATA = Path(__file__).resolve().parents[2] / "data" / "external" / "zengel2015" / "zengel2015_group_means.csv"
BASELINE = "No Treatment"
TREATMENTS = ("Manual Treatment", "Mechanical Treatment")
KEY_METRICS = (
    "Total Vegetation Cover (%)",
    "Spartina alterniflora Cover (%)",
    "Surface Oil Cover (%)",
    "Shoreline Retreat (m yr-1)",
)
YEARS_SINCE_SPILL = {2011: 1, 2012: 2}  # oiling of these plots began in 2010
SCOPE = {"habitat": "salt marsh (Spartina alterniflora)", "oiling": "heavy", "region": "northern Gulf of Mexico"}


def load(path: Path | str = DATA) -> pd.DataFrame:
    return pd.read_csv(path)


def welch_contrast(m1, se1, n1, m2, se2, n2, level: float = 0.90) -> dict:
    """Difference m1 - m2 with a Welch t interval, from means, standard errors and sample sizes."""
    diff = m1 - m2
    se = float(np.hypot(se1, se2))
    v1, v2 = se1**2, se2**2
    denom = (v1**2 / (n1 - 1) if v1 else 0.0) + (v2**2 / (n2 - 1) if v2 else 0.0)
    df = (v1 + v2) ** 2 / denom if denom > 0 else float(min(n1, n2) - 1)
    t = stats.t.ppf(0.5 + level / 2, df)
    return {"effect": diff, "se": se, "df": df, "lo": diff - t * se, "hi": diff + t * se}


def effect_table(df: pd.DataFrame | None = None, level: float = 0.90) -> pd.DataFrame:
    """Every treatment vs no-treatment contrast, plus the randomized planting contrast."""
    df = load() if df is None else df
    main = df[(df.study == "main") & df.metric.isin(KEY_METRICS)].dropna(subset=["mean"])
    rows = []
    for (year, metric), g in main.groupby(["year", "metric"]):
        g = g.set_index("treatment")
        if BASELINE not in g.index:
            continue
        b = g.loc[BASELINE]
        ref = g.loc["Reference", "mean"] if "Reference" in g.index else np.nan
        for t in TREATMENTS:
            if t not in g.index:
                continue
            r = g.loc[t]
            c = welch_contrast(r["mean"], r.se, r.n, b["mean"], b.se, b.n, level)
            rows.append({"comparison": f"{t} vs {BASELINE}", "year": year,
                         "years_since_spill": YEARS_SINCE_SPILL[year], "metric": metric,
                         "treated_mean": r["mean"], "baseline_mean": b["mean"], "reference_mean": ref,
                         "design": "observational (classes not randomly assigned)", **c})
    pl = df[df.study == "planting"].set_index(["metric", "treatment"])
    for metric in pl.index.get_level_values(0).unique():
        p, c0 = pl.loc[(metric, "Mechanical (Planted)")], pl.loc[(metric, "Mechanical (Control)")]
        c = welch_contrast(p["mean"], p.se, p.n, c0["mean"], c0.se, c0.n, level)
        rows.append({"comparison": "Planting vs no planting (after mechanical)", "year": 2012,
                     "years_since_spill": 2, "metric": metric, "treated_mean": p["mean"],
                     "baseline_mean": c0["mean"], "reference_mean": np.nan,
                     "design": "randomized", **c})
    out = pd.DataFrame(rows)
    out["interval_excludes_zero"] = (out.lo > 0) | (out.hi < 0)
    return out


def recovery_fraction(df: pd.DataFrame | None = None, metric: str = "Total Vegetation Cover (%)") -> pd.DataFrame:
    """Group mean as a fraction of the reference plots, by class and year (1.0 = like reference)."""
    df = load() if df is None else df
    m = df[(df.study == "main") & (df.metric == metric)].dropna(subset=["mean"])
    ref = m[m.treatment == "Reference"].set_index("year")["mean"]
    m = m[m.treatment != "Reference"].copy()
    m["recovery_fraction"] = m["mean"] / m.year.map(ref)
    m["years_since_spill"] = m.year.map(YEARS_SINCE_SPILL)
    return m[["treatment", "year", "years_since_spill", "mean", "se", "n", "recovery_fraction"]]


@dataclass
class TreatmentPrior:
    treatment: str
    years_since_spill: int
    veg_cover_effect: float      # percentage points vs natural recovery
    veg_cover_lo: float
    veg_cover_hi: float
    recovery_fraction: float     # treated cover / reference cover
    in_scope: bool
    note: str


def treatment_prior(treatment: str, years_since_spill: int, habitat: str = "salt marsh",
                    oiling: str = "heavy", df: pd.DataFrame | None = None) -> TreatmentPrior:
    """Prior effect of a treatment on total vegetation cover, relative to no treatment.

    Only defined for heavily oiled salt marsh at 1 or 2 years. Outside that scope the function still
    answers, but `in_scope` is False and the note says why, so the dashboard can grey it out.
    """
    df = load() if df is None else df
    name = {"manual": "Manual Treatment", "mechanical": "Mechanical Treatment",
            "none": BASELINE, "no treatment": BASELINE}.get(treatment.lower(), treatment)
    if years_since_spill not in (1, 2):
        raise ValueError("Zengel et al. (2015) only observed years 1 and 2 after oiling; no extrapolation.")
    year = {1: 2011, 2: 2012}[years_since_spill]
    in_scope = "marsh" in habitat.lower() and oiling.lower() == "heavy"
    note = ("Observational contrast from one spill, n = 5 vs 9 plots."
            if in_scope else "OUT OF SCOPE: Zengel 2015 covers heavily oiled salt marsh only.")
    rf = recovery_fraction(df).set_index(["treatment", "year"]).loc[(name, year), "recovery_fraction"]
    if name == BASELINE:
        return TreatmentPrior(name, years_since_spill, 0.0, 0.0, 0.0, float(rf), in_scope, note)
    e = effect_table(df)
    r = e[(e.comparison == f"{name} vs {BASELINE}") & (e.year == year)
          & (e.metric == "Total Vegetation Cover (%)")].iloc[0]
    return TreatmentPrior(name, years_since_spill, float(r.effect), float(r.lo), float(r.hi), float(rf), in_scope, note)


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    t = effect_table()
    print(t[["comparison", "year", "metric", "treated_mean", "baseline_mean", "effect", "lo", "hi",
             "interval_excludes_zero", "design"]].round(2).to_string(index=False))
    print()
    print(recovery_fraction().round(3).to_string(index=False))


# ---------------------------------------------------------------------------------------------
# Erosion priors from Zengel et al. (2022), added in P3 (docs/P3_TREATMENT_PLAN.md, analysis A/D).
# Source: GRIIDC doi:10.7266/VF524143 (CC0), file data/external/zengel2022/zengel2022_griidc_erosion.xlsx.
# Outcome: aerial-photo marsh-edge erosion per plot (m/yr, positive = erosion), change from the pre-spill period
# 2005-2010 to 2010-2012 (spill period) or 2012-2018 (later). Baseline: oiled, untreated (natural recovery).
# Same Welch interval as above. One site (Bay Jimmy, northern Barataria Bay), 5-9 plots per group; not
# randomized except planting; the plots overlap Zengel et al. (2015), so this is not independent of the
# vegetation priors above.
# ---------------------------------------------------------------------------------------------
EROSION_DATA = DATA.parents[1] / "zengel2022" / "zengel2022_griidc_erosion.xlsx"
EROSION_GROUPS = {"REFERENCE": "reference", "UNTREATED": "none", "TREATED - MANUAL": "manual",
                  "TREATED - MECHANICAL": "mechanical", "TREATED - PLANTED": "mechanical+planting"}


def erosion_effects(period: str = "2010-2012", level: float = 0.90, path: Path | str = EROSION_DATA) -> pd.DataFrame:
    """Pre-spill-adjusted erosion change per treatment, against oiled-untreated plots, with Welch intervals."""
    d = pd.read_excel(path, sheet_name="DSAS lumped")
    d["treatment"] = d.PLOT_TYPE.str.strip().map(EROSION_GROUPS)
    w = d.pivot_table(index=["PLOT_ID", "treatment"], columns="TIME_PERIOD", values="EROSION_RATE").reset_index()
    w["change"] = w[period] - w["2005-2010"]
    base = w.loc[w.treatment == "none", "change"]
    rows = []
    for t in ("manual", "mechanical", "mechanical+planting", "reference"):
        x = w.loc[w.treatment == t, "change"]
        c = welch_contrast(x.mean(), x.std(ddof=1) / np.sqrt(len(x)), len(x),
                           base.mean(), base.std(ddof=1) / np.sqrt(len(base)), len(base), level)
        rows.append({"treatment": t, "period": period, "n": len(x), "n_untreated": len(base),
                     "extra_erosion_vs_untreated": c["effect"], "lo": c["lo"], "hi": c["hi"]})
    return pd.DataFrame(rows)


def erosion_prior(treatment: str, period: str = "2010-2012", habitat: str = "salt marsh", oiling: str = "heavy") -> dict:
    """Extra marsh-edge erosion (m/yr) of a treatment against natural recovery, with a 90% interval.

    period "2010-2012" is the first two years after oiling; "2012-2018" the following six. `in_scope` is False
    outside heavily oiled salt marsh. Point values must be shown with their interval, never alone.
    """
    name = {"natural recovery": "none", "no treatment": "none", "none": "none", "manual": "manual",
            "mechanical": "mechanical", "planting": "mechanical+planting",
            "mechanical+planting": "mechanical+planting"}[treatment.lower()]
    in_scope = "marsh" in habitat.lower() and oiling.lower() == "heavy"
    note = ("Zengel et al. 2022, one site, 5-9 plots per group; observational except planting."
            if in_scope else "OUT OF SCOPE: Zengel et al. 2022 covers heavily oiled salt marsh only.")
    if name == "none":
        return {"treatment": name, "period": period, "effect": 0.0, "lo": 0.0, "hi": 0.0, "in_scope": in_scope, "note": note}
    r = erosion_effects(period).set_index("treatment").loc[name]
    return {"treatment": name, "period": period, "effect": float(r.extra_erosion_vs_untreated), "lo": float(r.lo),
            "hi": float(r.hi), "in_scope": in_scope, "note": note}
