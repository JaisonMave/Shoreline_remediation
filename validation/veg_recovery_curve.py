"""Vegetation recovery curve of oiled marsh (plan: docs/SCENARIO_PROGRAMME_PLAN.md section A1). Run once.

Data   : data/external/zengel2022_meta/dataset_compiled_for_GRIIDC.xlsx, sheet 'Dataset' (Source, Site ID, Site type,
         Site type (HO), Marsh Zone, Year, TotalCover). The table has no treatment variable: this is the recovery of
         oiled marsh as it was managed, not a treatment effect.
Unit   : one Source x Year x Marsh Zone that has at least one oiled and one reference site with TotalCover.
         lnRR = ln((mean oiled cover + 1) / (mean reference cover + 1)); the +1 percentage point is ASSUMED.
         t = Year - 2010 + 0.5 years (ASSUMED late growing season). 0 means recovered.
Models : M0 constant; M1 a + b ln t; M2 (primary) -A exp(-t/tau); M3 M2 with one A per marsh zone (common tau).
         M2/M3 are fitted by least squares: tau on a log grid TAU_GRID (ASSUMED 0.25 to 50 years, 400 points), A in
         closed form for each tau and constrained to A >= 0 (ASSUMED: recovery is towards the reference from below).
         Secondary: M0 and M2 on the heavy-oiling subset (Site type (HO)).
Validation: leave one whole Source out; error = MAE of lnRR per held-out study, averaged over studies. 90% prediction
         interval = 5th/95th percentile of the pooled leave-one-study-out residuals of that model; coverage per study.
         Every summary is bootstrapped over studies (2,000 resamples, seed 20261112). The difference M2 - M0 (and M1,
         M3 - M0) is bootstrapped from the per-study leave-one-study-out errors (the leave-one-out predictions are not
         recomputed inside the bootstrap); A, tau and years to 80% are refitted in every bootstrap resample.
Reading (fixed in the plan): M2 below M0 and 90% interval of the difference excludes zero -> validated; M2 below M0 but
         the interval includes zero -> suggestive; otherwise not usable.
Also   : years until expected cover reaches 80% of reference (lnRR = ln 0.8), flagged beyond t = 7.5 as extrapolation.

Run    : python -m validation.veg_recovery_curve
Writes : results/veg_recovery/{units,loso_by_study,summary}.csv, summary.txt; models/veg_recovery_v1.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATA = ROOT / "data" / "external" / "zengel2022_meta" / "dataset_compiled_for_GRIIDC.xlsx"
RESULTS = ROOT / "results" / "veg_recovery"
MODEL_JSON = ROOT / "models" / "veg_recovery_v1.json"
SEED, N_BOOT = 20261112, 2000
COVER_OFFSET = 1.0            # ASSUMED, percentage points
T0_YEAR, T_SHIFT = 2010, 0.5  # ASSUMED t = Year - 2010 + 0.5
TAU_GRID = np.geomspace(0.25, 50.0, 400)   # ASSUMED search range, years
TARGET_FRACTION = 0.8
EXTRAPOLATION_T = 7.5
COLS = {"study": "Source", "site": "Site ID", "type": "Site type", "type_ho": "Site type (HO)",
        "zone": "Marsh Zone", "year": "Year", "cover": "TotalCover"}
ALL_MODELS = ["M0", "M1", "M2", "M3"]
HEAVY_MODELS = ["M0", "M2"]


# ------------------------------------------------------------------ units
def build_units(raw: pd.DataFrame, type_col: str = "type") -> tuple[pd.DataFrame, dict]:
    """Study x year x zone units with both oiled and reference sites, and the counts surviving each filter.

    raw has the original column names (COLS). type_col: 'type' (all) or 'type_ho' (heavy-oiling subset, where rows
    outside the subset have an empty type and are dropped).
    """
    d = pd.DataFrame({k: raw[v] for k, v in COLS.items() if v in raw.columns})
    counts = {"rows": len(d)}
    d = d[d[type_col].isin(["Oiled", "Reference"])]
    counts["rows_with_oiled_or_reference_label"] = len(d)
    d = d.assign(cover=pd.to_numeric(d["cover"], errors="coerce")).dropna(subset=["cover", "year", "zone"])
    counts["rows_with_cover_year_zone"] = len(d)
    counts["studies_with_rows"] = int(d.study.nunique())
    g = d.groupby(["study", "year", "zone", type_col])["cover"].agg(["mean", "count"]).unstack(type_col)
    counts["cells_study_year_zone"] = int(d.groupby(["study", "year", "zone"]).ngroups)
    for stat in ("mean", "count"):
        for typ in ("Oiled", "Reference"):
            if (stat, typ) not in g.columns:
                g[(stat, typ)] = np.nan          # a subset with no site of one type has no units
    g = g.dropna(subset=[("mean", "Oiled"), ("mean", "Reference")])
    u = pd.DataFrame({"study": g.index.get_level_values("study"), "year": g.index.get_level_values("year").astype(int),
                      "zone": g.index.get_level_values("zone").astype(int),
                      "n_oiled": g[("count", "Oiled")].values.astype(int),
                      "n_reference": g[("count", "Reference")].values.astype(int),
                      "oiled_cover": g[("mean", "Oiled")].values, "reference_cover": g[("mean", "Reference")].values})
    u["lnRR"] = np.log((u.oiled_cover + COVER_OFFSET) / (u.reference_cover + COVER_OFFSET))
    u["t"] = u.year - T0_YEAR + T_SHIFT
    u = u.reset_index(drop=True)
    counts["units"] = len(u)
    counts["studies_with_units"] = int(u.study.nunique())
    counts["units_by_study"] = u.groupby("study").size().to_dict()
    return u, counts


# ------------------------------------------------------------------ models: fit(train) -> predict(df) -> array
def _profile_fit(t: np.ndarray, y: np.ndarray, zone: np.ndarray | None):
    """Least squares for y = -A[z] exp(-t/tau), A[z] >= 0, tau on TAU_GRID. Returns (A dict, tau, sse)."""
    e = np.exp(-t[None, :] / TAU_GRID[:, None])               # (grid, n)
    zones = [None] if zone is None else sorted(set(zone.tolist()))
    sse = np.zeros(len(TAU_GRID))
    amps = {}
    for z in zones:
        m = np.ones(len(t), bool) if z is None else zone == z
        ez, yz = e[:, m], y[m]
        a = np.clip(-(ez @ yz) / np.maximum((ez ** 2).sum(1), 1e-300), 0.0, None)
        amps[z] = a
        sse += ((yz[None, :] + a[:, None] * ez) ** 2).sum(1)
    k = int(np.argmin(sse))
    return {z: float(amps[z][k]) for z in zones}, float(TAU_GRID[k]), float(sse[k])


def fit_m0(train: pd.DataFrame):
    c = float(train.lnRR.mean())
    return lambda d: np.full(len(d), c)


def fit_m1(train: pd.DataFrame):
    x = np.log(train.t.to_numpy())
    b, a = np.polyfit(x, train.lnRR.to_numpy(), 1) if np.ptp(x) > 0 else (0.0, float(train.lnRR.mean()))
    return lambda d: a + b * np.log(d.t.to_numpy())


def fit_m2(train: pd.DataFrame):
    A, tau, _ = _profile_fit(train.t.to_numpy(float), train.lnRR.to_numpy(float), None)
    f = lambda d: -A[None] * np.exp(-d.t.to_numpy() / tau)
    f.params = {"A": A[None], "tau": tau}
    return f


def fit_m3(train: pd.DataFrame):
    A, tau, _ = _profile_fit(train.t.to_numpy(float), train.lnRR.to_numpy(float), train.zone.to_numpy())
    mean_a = float(np.mean(list(A.values())))

    def f(d):
        a = np.array([A.get(z, mean_a) for z in d.zone])   # a zone unseen in training gets the mean A
        return -a * np.exp(-d.t.to_numpy() / tau)
    f.params = {"A": A, "tau": tau}
    return f


FITTERS = {"M0": fit_m0, "M1": fit_m1, "M2": fit_m2, "M3": fit_m3}


def t_to_fraction(A: float, tau: float, fraction: float = TARGET_FRACTION) -> float:
    """t (years) at which -A exp(-t/tau) reaches ln(fraction); 0 if already there at t = 0 (including A = 0)."""
    target = -np.log(fraction)            # positive
    if A <= target:
        return 0.0
    return float(tau * np.log(A / target))


# ------------------------------------------------------------------ validation
def loso(units: pd.DataFrame, fitters: dict | None = None) -> pd.DataFrame:
    """Leave one whole study out. Returns one row per held-out unit: study, unit index, observed, one prediction per model.
    A study is never in the training data of its own predictions."""
    fitters = fitters or FITTERS
    rows = []
    for s in sorted(units.study.unique()):
        train, test = units[units.study != s], units[units.study == s]
        assert s not in set(train.study)
        out = pd.DataFrame({"study": s, "unit": test.index.values, "obs": test.lnRR.values})
        for name, fit in fitters.items():
            out[name] = fit(train)(test)
        rows.append(out)
    return pd.concat(rows, ignore_index=True)


def per_study_table(pred: pd.DataFrame, models: list[str], level: float = 0.90) -> pd.DataFrame:
    """Per-study n units, MAE per model, and coverage of the pooled-residual 90% interval per model."""
    lo_q, hi_q = (1 - level) / 2, 1 - (1 - level) / 2
    off = {m: np.quantile(pred.obs - pred[m], [lo_q, hi_q]) for m in models}
    rows = []
    for s, g in pred.groupby("study"):
        r = {"study": s, "n_units": len(g)}
        for m in models:
            res = g.obs - g[m]
            r[f"MAE_{m}"] = float(res.abs().mean())
            r[f"coverage_{m}"] = float(((res >= off[m][0]) & (res <= off[m][1])).mean())
        rows.append(r)
    return pd.DataFrame(rows)


def study_average(tab: pd.DataFrame, models: list[str]) -> dict:
    return {m: float(tab[f"MAE_{m}"].mean()) for m in models}


def bootstrap_differences(tab: pd.DataFrame, models: list[str], n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """Study-averaged MAE of each model minus M0, with the 90% bootstrap interval over studies."""
    rng = np.random.default_rng(seed)
    n = len(tab)
    idx = rng.integers(0, n, size=(n_boot, n))
    out = {}
    for m in models:
        if m == "M0":
            continue
        d = (tab[f"MAE_{m}"] - tab["MAE_M0"]).to_numpy()
        boot = d[idx].mean(1)
        out[m] = {"diff": float(d.mean()), "lo": float(np.percentile(boot, 5)), "hi": float(np.percentile(boot, 95))}
    return out


def bootstrap_m2(units: pd.DataFrame, n_boot: int = N_BOOT, seed: int = SEED) -> pd.DataFrame:
    """Refit M2 on studies resampled with replacement. Returns A, tau, years_to_80 per resample."""
    rng = np.random.default_rng(seed)
    studies = np.array(sorted(units.study.unique()))
    by = {s: units[units.study == s] for s in studies}
    rows = []
    for _ in range(n_boot):
        pick = rng.choice(studies, size=len(studies), replace=True)
        b = pd.concat([by[s] for s in pick], ignore_index=True)
        A, tau, _ = _profile_fit(b.t.to_numpy(float), b.lnRR.to_numpy(float), None)
        rows.append({"A": A[None], "tau": tau, "years_to_80": t_to_fraction(A[None], tau)})
    return pd.DataFrame(rows)


def verdict(diff: dict) -> str:
    """Plan reading table, applied to the M2 - M0 study-averaged difference (negative = M2 better)."""
    if diff["diff"] < 0 and diff["hi"] < 0:
        return "validated"
    if diff["diff"] < 0:
        return "suggestive"
    return "not usable"


def run_subset(units: pd.DataFrame, models: list[str], n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """Everything for one subset: LOSO predictions, per-study table, averages, differences, M2 fit and bootstrap."""
    fitters = {m: FITTERS[m] for m in models}
    pred = loso(units, fitters)
    tab = per_study_table(pred, models)
    diffs = bootstrap_differences(tab, models, n_boot, seed)
    full = fit_m2(units)
    boot = bootstrap_m2(units, n_boot, seed)
    p = full.params
    res = {"pred": pred, "tab": tab, "avg": study_average(tab, models), "diffs": diffs,
           "A": p["A"], "tau": p["tau"], "years_to_80": t_to_fraction(p["A"], p["tau"]), "boot": boot,
           "verdict": verdict(diffs["M2"])}
    res["resid_offsets"] = {m: [float(x) for x in np.quantile(pred.obs - pred[m], [0.05, 0.95])] for m in models}
    return res


# ------------------------------------------------------------------ main
def _ci(x) -> tuple[float, float]:
    return float(np.percentile(x, 5)), float(np.percentile(x, 95))


def main() -> None:
    raw = pd.read_excel(DATA, sheet_name="Dataset")
    units, c_all = build_units(raw, "type")
    units_ho, c_ho = build_units(raw, "type_ho")
    A = run_subset(units, ALL_MODELS)
    H = run_subset(units_ho, HEAVY_MODELS)
    RESULTS.mkdir(parents=True, exist_ok=True)

    pd.concat([units.assign(subset="all"), units_ho.assign(subset="heavy")]).to_csv(RESULTS / "units.csv", index=False)
    t_all = A["tab"].assign(subset="all")
    t_ho = H["tab"].assign(subset="heavy")
    pd.concat([t_all, t_ho], ignore_index=True).to_csv(RESULTS / "loso_by_study.csv", index=False)

    rows = []
    for tag, R, models in (("all", A, ALL_MODELS), ("heavy", H, HEAVY_MODELS)):
        for m in models:
            r = {"subset": tag, "row": f"study_averaged_MAE_{m}", "estimate": R["avg"][m], "lo90": np.nan, "hi90": np.nan}
            rows.append(r)
            if m != "M0":
                d = R["diffs"][m]
                rows.append({"subset": tag, "row": f"MAE_{m}_minus_M0", "estimate": d["diff"], "lo90": d["lo"], "hi90": d["hi"]})
        for key in ("A", "tau", "years_to_80"):
            lo, hi = _ci(R["boot"][key])
            rows.append({"subset": tag, "row": f"M2_{key}", "estimate": R[key], "lo90": lo, "hi90": hi})
    pd.DataFrame(rows).to_csv(RESULTS / "summary.csv", index=False)

    lo, hi = _ci(A["boot"].years_to_80)
    d2 = A["diffs"]["M2"]
    reading = {"validated": "row 1 (validated: use the curve)", "suggestive": "row 2 (suggestive: show the curve with its interval and say so)",
               "not usable": "row 3 (not usable: show study-year means only)"}[A["verdict"]]
    L = ["Vegetation recovery curve, plan section A1 (docs/SCENARIO_PROGRAMME_PLAN.md). Run once.", "",
         "Filters (all oiled vs reference sites)",
         f"  rows {c_all['rows']} -> with Oiled/Reference label {c_all['rows_with_oiled_or_reference_label']} -> with cover, year, zone "
         f"{c_all['rows_with_cover_year_zone']} (studies with rows: {c_all['studies_with_rows']})",
         f"  study x year x zone cells {c_all['cells_study_year_zone']} -> cells with both oiled and reference {c_all['units']} units "
         f"from {c_all['studies_with_units']} studies",
         "  units by study: " + ", ".join(f"{k} {v}" for k, v in c_all["units_by_study"].items()),
         "Filters (heavy-oiling subset, Site type (HO))",
         f"  rows with HO label {c_ho['rows_with_oiled_or_reference_label']} -> with cover {c_ho['rows_with_cover_year_zone']} -> units "
         f"{c_ho['units']} from {c_ho['studies_with_units']} studies",
         "  units by study: " + ", ".join(f"{k} {v}" for k, v in c_ho["units_by_study"].items()), "",
         "Study-averaged leave-one-study-out MAE of lnRR (all sites)"]
    for m in ALL_MODELS:
        L.append(f"  {m}: {A['avg'][m]:.3f}")
    for m in ("M1", "M2", "M3"):
        d = A["diffs"][m]
        L.append(f"  {m} minus M0: {d['diff']:+.3f} (90% bootstrap over studies {d['lo']:+.3f} to {d['hi']:+.3f})")
    L += ["", f"VERDICT (primary, M2 vs M0): {A['verdict'].upper()}. Plan reading table row applying: {reading}.",
          f"  M2 {A['avg']['M2']:.3f} vs M0 {A['avg']['M0']:.3f}; difference {d2['diff']:+.3f}, 90% interval {d2['lo']:+.3f} to {d2['hi']:+.3f}.", "",
          "M2 fitted on all units: A = {:.2f} (90% {:.2f} to {:.2f}), tau = {:.2f} years (90% {:.2f} to {:.2f}); tau grid {:.2f} to {:.0f} years (ASSUMED).".format(
              A["A"], *_ci(A["boot"].A), A["tau"], *_ci(A["boot"].tau), TAU_GRID[0], TAU_GRID[-1]),
          f"Years until expected cover reaches 80% of reference: {A['years_to_80']:.1f} (90% {lo:.1f} to {hi:.1f})"
          + ("; EXTRAPOLATION beyond t = 7.5 (the data end at 2017)" if hi > EXTRAPOLATION_T or A["years_to_80"] > EXTRAPOLATION_T else
             "; within the observed time range") + ". Bootstrap resamples with A <= {:.3f} (already at 80% at t = 0) count as 0 years.".format(-np.log(TARGET_FRACTION)),
          "", "Per study (MAE of lnRR: M0, M1, M2, M3; coverage of the 90% interval M0 / M2):"]
    for r in A["tab"].itertuples():
        worse = " <- M2 worse than M0" if r.MAE_M2 > r.MAE_M0 else ""
        L.append(f"  {r.study}: n={r.n_units}  {r.MAE_M0:.3f} {r.MAE_M1:.3f} {r.MAE_M2:.3f} {r.MAE_M3:.3f}  cov {r.coverage_M0:.2f} / {r.coverage_M2:.2f}{worse}")
    n_worse = int((A["tab"].MAE_M2 > A["tab"].MAE_M0).sum())
    L.append(f"  M2 worse than M0 in {n_worse} of {len(A['tab'])} studies.")
    h2 = H["diffs"]["M2"]
    L += ["", "Secondary: heavy-oiling subset (M0 and M2 only)",
          f"  study-averaged MAE M0 {H['avg']['M0']:.3f}, M2 {H['avg']['M2']:.3f}; M2 minus M0 {h2['diff']:+.3f} (90% {h2['lo']:+.3f} to {h2['hi']:+.3f}); "
          f"reading would be {H['verdict']} (secondary, not a gate)",
          "  M2: A = {:.2f} (90% {:.2f} to {:.2f}), tau = {:.2f} (90% {:.2f} to {:.2f}); years to 80% {:.1f} (90% {:.1f} to {:.1f})".format(
              H["A"], *_ci(H["boot"].A), H["tau"], *_ci(H["boot"].tau), H["years_to_80"], *_ci(H["boot"].years_to_80)),
          "", "Limits known in advance (plan): ten studies, several with one or two years; one spill; no coordinates; oiling severity differs",
          "between studies; cleanup unrecorded and mixed into 'oiled'. lnRR uses +1 pp and t = Year - 2010 + 0.5 (both ASSUMED).",
          "Bootstrap of M2 - M0 resamples the per-study leave-one-study-out errors; the 90% prediction interval offsets come from the pooled",
          "leave-one-study-out residuals, which include the held-out study's own residuals (as pre-specified)."]
    (RESULTS / "summary.txt").write_text("\n".join(L) + "\n")

    card = {"name": "veg-recovery-v1", "built": "2026-11-12", "plan": "docs/SCENARIO_PROGRAMME_PLAN.md A1",
            "target": "lnRR = ln((oiled TotalCover + 1)/(reference TotalCover + 1)); t = Year - 2010 + 0.5 years",
            "model": "M2: lnRR = -A exp(-t/tau)", "verdict": A["verdict"],
            "parameters": {"A": A["A"], "tau": A["tau"]},
            "intervals_90": {"A": list(_ci(A["boot"].A)), "tau": list(_ci(A["boot"].tau)), "years_to_80": [lo, hi]},
            "years_to_80_of_reference": A["years_to_80"], "extrapolation_beyond_t": EXTRAPOLATION_T,
            "study_averaged_mae": A["avg"], "m2_minus_m0": A["diffs"]["M2"],
            "training_studies": sorted(units.study.unique()), "n_units": len(units),
            "residual_offsets_90": A["resid_offsets"]["M2"],
            "loso_residuals": [float(x) for x in (A["pred"].obs - A["pred"].M2)],
            "bootstrap_draws": {"A": [float(x) for x in A["boot"].A], "tau": [float(x) for x in A["boot"].tau]},
            "assumed": {"cover_offset_pp": COVER_OFFSET, "t_shift_years": T_SHIFT, "tau_grid_years": [float(TAU_GRID[0]), float(TAU_GRID[-1])]},
            "limits": "ten studies, one spill, cleanup unrecorded; curve is oiled marsh as managed, not a treatment effect"}
    MODEL_JSON.parent.mkdir(exist_ok=True)
    MODEL_JSON.write_text(json.dumps(card, indent=1))
    print((RESULTS / "summary.txt").read_text())


if __name__ == "__main__":
    main()
