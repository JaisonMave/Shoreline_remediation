"""Soil PAH decline in oiled marsh, DIVER (plan: docs/PAH_DECLINE_PLAN.md, "Final choices"). Run once.

Data   : the per-sample table of src/shoreline_remediation/diver_soil.py (sum of compounds reported in all four PAH
         campaigns; second outcome = sum / hopane), aggregated to one cell per station x campaign x depth class (median of
         the samples). The station is the unit; a sample is never a unit.
Outcome: ln(cell value), for (a) PAH sum and (b) PAH sum / hopane.
Models : M0 each station keeps its first measured value (earliest campaign, same depth class): no decline.
         M1 first-order decline: ln value = station level - k[oiling class] x t + depth effect, t = years since April 2010,
            mixed model (random intercept per station) fitted on the training stations; for a held-out station the
            prediction is its own first measured value minus k[class] x (t - t_first). M0 and M1 are therefore anchored
            on the same first value and differ only by the fitted decline. Classes with fewer than MIN_CLASS_STATIONS
            training stations that have at least two campaigns use the pooled k (ASSUMED, logged). The depth effect is
            included only when the training set has at least MIN_DEEP_CELLS deeper cells (ASSUMED).
Validation: whole stations held out, grouped 5-fold, seed 20261112. Error per station = mean absolute error of ln value over
         its held-out cells (cells after the first campaign with an earlier same-depth anchor). Difference M1 - M0 averaged
         over stations; 90% interval = bootstrap over stations (2,000 resamples, seed 20261112) of the per-station
         differences (the fold predictions are not recomputed inside the bootstrap). 90% prediction interval of M1 = 5th/95th
         percentile of the pooled held-out residuals (same procedure as veg_recovery_curve); coverage per station.
         Half-life = ln 2 / k by oiling class with 90% interval from refitting M1 on stations resampled with replacement
         (N_BOOT_HL resamples, seed 20261112). k <= 0 means no decline (half-life infinite).
Verdict: validated if M1 error < M0 error and the 90% interval of the difference excludes zero; suggestive if M1 < M0 but
         the interval includes zero; otherwise not usable.
Also   : sensitivity runs (non-detects 0; non-detects = proxy limit; non-detects = half proxy limit, the plan's fallback
         for every sample; 0-2 cm only). A decline in the sum without a decline in the hopane ratio means physical loss.

Run    : python -m validation.pah_decline
Writes : results/pah_decline/{station_campaign.csv, processing_log.txt, summary.csv, by_oiling_class.csv, sensitivity.csv,
         summary.txt, station_medians_pah_sum.png, station_medians_pah_over_hopane.png}
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

SEED, N_BOOT, N_BOOT_HL = 20261112, 2000, 1000
N_FOLDS = 5
MIN_CLASS_STATIONS = 3        # ASSUMED
MIN_DEEP_CELLS = 5            # ASSUMED
LN2 = float(np.log(2.0))
RESULTS = ROOT / "results" / "pah_decline"
CAMPAIGN_ORDER = {"Spring2011": 0, "Fall2011": 1, "Fall2012": 2, "Fall2013": 3}
OUTCOMES = {"pah_sum": "PAH sum", "ratio": "PAH sum / hopane"}


# ------------------------------------------------------------------ cells
def make_cells(sc: pd.DataFrame, col: str) -> pd.DataFrame:
    """Station x campaign x depth cells with a positive value of outcome col; columns station, order, t, y, deep, oil_class, state."""
    c = sc[sc[col].notna() & (sc[col] > 0)].copy()
    c["y"] = np.log(c[col].astype(float))
    c["order"] = c.campaign.map(CAMPAIGN_ORDER)
    c["deep"] = (c.depth_class != "0-2cm").astype(float)
    return c[["station", "campaign", "order", "t", "y", "deep", "oil_class", "state", "depth_class"]].reset_index(drop=True)


def anchors(cells: pd.DataFrame) -> pd.DataFrame:
    """Targets: every cell that has an earlier-campaign cell of the same station and depth class. Adds anchor y, t."""
    c = cells.sort_values(["station", "depth_class", "order"])
    first = c.groupby(["station", "depth_class"]).first()[["order", "t", "y"]].add_prefix("a_").reset_index()
    m = c.merge(first, on=["station", "depth_class"])
    return m[m.order > m.a_order].reset_index(drop=True)


# ------------------------------------------------------------------ M1
def _mixed(y, X, groups):
    import statsmodels.api as sm
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            r = sm.MixedLM(y, X, groups=groups).fit(reml=True, method="lbfgs")
            if np.all(np.isfinite(r.fe_params)):
                return np.asarray(r.fe_params)
        except Exception:
            pass
        return np.linalg.lstsq(X, y, rcond=None)[0]          # fallback: pooled OLS (logged by caller via return flag)


def fit_m1(train: pd.DataFrame) -> dict:
    """Returns {'k': {class: k}, 'k_pooled': k, 'delta': depth effect, 'classes_used': [...]}. k > 0 means decline."""
    use_deep = int((train.deep > 0).sum()) >= MIN_DEEP_CELLS
    g = train.station.values
    # pooled: y ~ 1 + t (+ deep)
    cols = [np.ones(len(train)), train.t.values] + ([train.deep.values] if use_deep else [])
    b = _mixed(train.y.values, np.column_stack(cols), g)
    k_pooled = -float(b[1])
    delta = float(b[2]) if use_deep else 0.0
    # by class: y ~ 0 + class + class:t (+ deep), classes with enough multi-campaign stations
    multi = train.groupby("station").order.nunique()
    ok_st = set(multi[multi >= 2].index)
    k = {}
    keep = []
    for cl, d in train.groupby("oil_class"):
        if d.station[d.station.isin(ok_st)].nunique() >= MIN_CLASS_STATIONS:
            keep.append(cl)
    if keep:
        sub = train[train.oil_class.isin(keep)]
        cols = [(sub.oil_class.values == cl).astype(float) for cl in keep] + \
               [(sub.oil_class.values == cl) * sub.t.values for cl in keep] + ([sub.deep.values] if use_deep else [])
        b = _mixed(sub.y.values, np.column_stack(cols), sub.station.values)
        for i, cl in enumerate(keep):
            k[cl] = -float(b[len(keep) + i])
        if use_deep:
            delta = float(b[-1])
    return {"k": k, "k_pooled": k_pooled, "delta": delta, "classes_used": keep}


def predict_m1(model: dict, tg: pd.DataFrame) -> np.ndarray:
    k = tg.oil_class.map(model["k"]).fillna(model["k_pooled"]).values
    return tg.a_y.values - k * (tg.t.values - tg.a_t.values)


# ------------------------------------------------------------------ validation
def station_folds(stations, n_folds: int = N_FOLDS, seed: int = SEED) -> dict:
    s = np.array(sorted(set(stations)))
    perm = np.random.default_rng(seed).permutation(len(s))
    return {s[i]: int(j % n_folds) for j, i in enumerate(perm)}


def cross_validate(cells: pd.DataFrame, n_folds: int = N_FOLDS, seed: int = SEED) -> pd.DataFrame:
    """Held-out predictions of M0 and M1 for the target cells; one row per held-out cell."""
    fold = station_folds(cells.station, n_folds, seed)
    cells = cells.assign(fold=cells.station.map(fold))
    out = []
    for f in range(n_folds):
        train, test = cells[cells.fold != f], cells[cells.fold == f]
        assert not (set(train.station) & set(test.station)), "a station is split between folds"
        tg = anchors(test)
        if len(tg) == 0:
            continue
        model = fit_m1(train)
        tg = tg.assign(pred_m0=tg.a_y.values, pred_m1=predict_m1(model, tg), fold=f)
        out.append(tg)
    return pd.concat(out, ignore_index=True)


def per_station(pred: pd.DataFrame, level: float = 0.90) -> pd.DataFrame:
    lo_q, hi_q = (1 - level) / 2, 1 - (1 - level) / 2
    r1 = pred.y - pred.pred_m1
    lo, hi = np.quantile(r1, [lo_q, hi_q])
    p = pred.assign(e0=(pred.y - pred.pred_m0).abs(), e1=r1.abs(), inside=((r1 >= lo) & (r1 <= hi)).astype(float))
    t = p.groupby("station").agg(n_cells=("y", "size"), MAE_M0=("e0", "mean"), MAE_M1=("e1", "mean"), coverage=("inside", "mean"),
                                 oil_class=("oil_class", "first"), state=("state", "first")).reset_index()
    t.attrs["pi"] = (float(lo), float(hi))
    return t


def verdict(diff: float, lo: float, hi: float) -> str:
    if diff < 0 and hi < 0:
        return "validated"
    if diff < 0:
        return "suggestive"
    return "not usable"


def bootstrap_diff(tab: pd.DataFrame, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    d = (tab.MAE_M1 - tab.MAE_M0).to_numpy()
    idx = np.random.default_rng(seed).integers(0, len(d), size=(n_boot, len(d)))
    boot = d[idx].mean(1)
    lo, hi = float(np.percentile(boot, 5)), float(np.percentile(boot, 95))
    diff = float(d.mean())
    return {"diff": diff, "lo": lo, "hi": hi, "verdict": verdict(diff, lo, hi)}


def validate(cells: pd.DataFrame) -> dict:
    pred = cross_validate(cells)
    tab = per_station(pred)
    b = bootstrap_diff(tab)
    return {"pred": pred, "tab": tab, "boot": b, "MAE_M0": float(tab.MAE_M0.mean()), "MAE_M1": float(tab.MAE_M1.mean()),
            "n_stations": int(len(tab)), "n_cells": int(len(pred)), "pi": tab.attrs["pi"], "coverage": float(tab.coverage.mean())}


def half_life(k: float) -> float:
    return LN2 / k if k > 0 else float("inf")


def half_life_table(cells: pd.DataFrame, n_boot: int = N_BOOT_HL, seed: int = SEED) -> pd.DataFrame:
    """k and half-life by oiling class (and pooled), full-data fit, 90% interval from refits on resampled stations."""
    full = fit_m1(cells)
    rng = np.random.default_rng(seed)
    st = np.array(sorted(cells.station.unique()))
    by = {s: cells[cells.station == s] for s in st}
    boots = []
    for _ in range(n_boot):
        pick = rng.choice(st, size=len(st), replace=True)
        d = pd.concat([by[s].assign(station=f"{s}#{i}") for i, s in enumerate(pick)], ignore_index=True)
        m = fit_m1(d)
        boots.append({"pooled": m["k_pooled"], **{cl: m["k"].get(cl, np.nan) for cl in OIL_CLASSES}})
    B = pd.DataFrame(boots)
    rows = []
    for name, k in [("pooled", full["k_pooled"])] + [(cl, full["k"].get(cl, np.nan)) for cl in OIL_CLASSES]:
        kb = B[name].dropna()
        klo, khi = (np.percentile(kb, 5), np.percentile(kb, 95)) if len(kb) >= 20 else (np.nan, np.nan)
        n_st = cells.station.nunique() if name == "pooled" else cells[cells.oil_class == name].station.nunique()
        multi = cells.groupby("station").order.nunique()
        n_multi = int(((multi >= 2) & multi.index.isin(cells[cells.oil_class == name].station if name != "pooled" else multi.index)).sum())
        rows.append({"oil_class": name, "n_stations": n_st, "n_stations_2plus_campaigns": n_multi,
                     "k_per_year": k, "k_lo90": klo, "k_hi90": khi, "half_life_years": half_life(k) if np.isfinite(k) else np.nan,
                     "half_life_lo90": half_life(khi) if np.isfinite(khi) else np.nan,
                     "half_life_hi90": half_life(klo) if np.isfinite(klo) else np.nan,
                     "class_specific_fit": name == "pooled" or name in full["classes_used"]})
    return pd.DataFrame(rows)


OIL_CLASSES = ["none", "very_light", "light", "moderate", "heavy", "unknown"]


# ------------------------------------------------------------------ output helpers
def fmt_hl(x) -> str:
    return "no decline" if (isinstance(x, float) and np.isinf(x)) else ("NA" if pd.isna(x) else f"{x:.2f}")


def plot_medians(sc: pd.DataFrame, col: str, label: str, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    c = sc[(sc.depth_class == "0-2cm") & sc[col].notna() & (sc[col] > 0)]
    fig, axes = plt.subplots(2, 3, figsize=(12, 6.5), sharey=True)
    camps = list(CAMPAIGN_ORDER)
    for ax, cl in zip(axes.ravel(), OIL_CLASSES):
        d = c[c.oil_class == cl]
        for _, g in d.groupby("station"):
            g = g.sort_values("t")
            ax.plot(g.campaign.map(CAMPAIGN_ORDER), g[col], color="0.6", lw=0.6, alpha=0.6, marker="o", ms=2)
        med = d.groupby("campaign")[col].median().reindex(camps)
        ax.plot(range(4), med.values, color="C3", lw=2, marker="s", label="median of stations")
        ax.set_yscale("log"); ax.set_xticks(range(4)); ax.set_xticklabels(camps, fontsize=8)
        ax.set_title(f"{cl} (n stations {d.station.nunique()})", fontsize=10)
    for ax in axes[:, 0]:
        ax.set_ylabel(label)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle(f"{label}: station medians (0-2 cm) by campaign and SCAT oiling class", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


# ------------------------------------------------------------------ main
def main() -> None:
    from src.shoreline_remediation import diver_soil as ds
    RESULTS.mkdir(parents=True, exist_ok=True)
    csv_dir = ROOT / "data" / "external" / "diver_dwh" / "extracted_csv"
    shp = ROOT / "data/raw/scat/18611/SCAT_Max_OilZones_Louisiana_2014_09_30Sorted.shp"
    log = ds.Log()
    prep = ds.prepare(csv_dir, shp, log)
    s, sc = ds.build(prep, "tobit", False, log)
    log.add(f"[table] station-campaign-depth rows {len(sc)}; stations {sc.station.nunique()}; stations by number of campaigns: "
            f"{sc.groupby('station').campaign.nunique().value_counts().sort_index().to_dict()}")
    sc.to_csv(RESULTS / "station_campaign.csv", index=False)

    primary, rows_cls, lines = {}, [], []
    for col, label in OUTCOMES.items():
        cells = make_cells(sc, col)
        v = validate(cells)
        hl = half_life_table(cells)
        primary[col] = (cells, v, hl)
        log.add(f"[model] {label}: cells {len(cells)}; stations {cells.station.nunique()}; target cells {v['n_cells']} in "
                f"{v['n_stations']} stations")
        for cl in OIL_CLASSES:
            g = v["tab"][v["tab"].oil_class == cl]
            h = hl[hl.oil_class == cl].iloc[0]
            rows_cls.append({"outcome": label, "stratum_type": "oiling_class", "stratum": cl, "n_stations": h.n_stations,
                             "n_stations_2plus_campaigns": h.n_stations_2plus_campaigns, "n_heldout_stations": len(g),
                             "MAE_M0": g.MAE_M0.mean() if len(g) else np.nan, "MAE_M1": g.MAE_M1.mean() if len(g) else np.nan,
                             "k_per_year": h.k_per_year, "k_lo90": h.k_lo90, "k_hi90": h.k_hi90,
                             "half_life_years": h.half_life_years, "half_life_lo90": h.half_life_lo90, "half_life_hi90": h.half_life_hi90,
                             "class_specific_fit": h.class_specific_fit})
        h = hl[hl.oil_class == "pooled"].iloc[0]
        rows_cls.append({"outcome": label, "stratum_type": "all", "stratum": "pooled", "n_stations": h.n_stations,
                         "n_stations_2plus_campaigns": h.n_stations_2plus_campaigns, "n_heldout_stations": len(v["tab"]),
                         "MAE_M0": v["MAE_M0"], "MAE_M1": v["MAE_M1"], "k_per_year": h.k_per_year, "k_lo90": h.k_lo90,
                         "k_hi90": h.k_hi90, "half_life_years": h.half_life_years, "half_life_lo90": h.half_life_lo90,
                         "half_life_hi90": h.half_life_hi90, "class_specific_fit": True})
        for stt, g in v["tab"].groupby("state"):
            rows_cls.append({"outcome": label, "stratum_type": "state", "stratum": stt, "n_stations": cells[cells.state == stt].station.nunique(),
                             "n_heldout_stations": len(g), "MAE_M0": g.MAE_M0.mean(), "MAE_M1": g.MAE_M1.mean()})
        plot_medians(sc, col, label, RESULTS / ("station_medians_pah_sum.png" if col == "pah_sum" else "station_medians_pah_over_hopane.png"))
    log.write(RESULTS / "processing_log.txt")
    pd.DataFrame(rows_cls).to_csv(RESULTS / "by_oiling_class.csv", index=False)

    summ = []
    for col, label in OUTCOMES.items():
        cells, v, hl = primary[col]
        b = v["boot"]
        summ.append({"outcome": label, "n_cells": len(cells), "n_stations": cells.station.nunique(), "n_heldout_stations": v["n_stations"],
                     "n_heldout_cells": v["n_cells"], "MAE_M0": v["MAE_M0"], "MAE_M1": v["MAE_M1"], "diff_M1_minus_M0": b["diff"],
                     "diff_lo90": b["lo"], "diff_hi90": b["hi"], "verdict": b["verdict"], "pi90_lo": v["pi"][0], "pi90_hi": v["pi"][1],
                     "pi90_coverage": v["coverage"]})
    pd.DataFrame(summ).to_csv(RESULTS / "summary.csv", index=False)

    # sensitivity runs: each rebuilds the sample table from the same resolved rows
    sens = []
    runs = [("primary (Tobit)", "tobit", False), ("non-detects = 0", "zero", False), ("non-detects = proxy limit", "proxy", False),
            ("non-detects = half proxy limit (no Tobit)", "half", False), ("0-2 cm only (Tobit)", "tobit", True)]
    for name, mode, surf in runs:
        if name.startswith("primary"):
            ss, scs = s, sc
        else:
            ss, scs = ds.build(prep, mode, surf, None)
        for col, label in OUTCOMES.items():
            cells = make_cells(scs, col)
            v = validate(cells)
            m = fit_m1(cells)
            r = {"run": name, "outcome": label, "n_samples": len(ss), "n_stations": cells.station.nunique(), "n_heldout_stations": v["n_stations"],
                 "MAE_M0": v["MAE_M0"], "MAE_M1": v["MAE_M1"], "diff_M1_minus_M0": v["boot"]["diff"], "diff_lo90": v["boot"]["lo"],
                 "diff_hi90": v["boot"]["hi"], "verdict": v["boot"]["verdict"], "k_pooled": m["k_pooled"],
                 "half_life_pooled_years": half_life(m["k_pooled"]), "est_share_pooled": float(ss.est_sum.sum() / ss.pah_sum.sum())}
            for cl in OIL_CLASSES:
                r[f"k_{cl}"] = m["k"].get(cl, np.nan)
            sens.append(r)
    pd.DataFrame(sens).to_csv(RESULTS / "sensitivity.csv", index=False)

    # summary.txt
    L = ["PAH decline in oiled marsh, DIVER: run once (plan docs/PAH_DECLINE_PLAN.md, Final choices).", ""]
    for col, label in OUTCOMES.items():
        cells, v, hl = primary[col]
        b = v["boot"]
        L += [f"Outcome: {label}",
              f"  Verdict rule (validated if M1 beats M0 and the 90% interval of the difference excludes zero; suggestive if it only leans; else not usable): {b['verdict'].upper()}",
              f"  stations {cells.station.nunique()}, cells {len(cells)}, held-out stations {v['n_stations']}, held-out cells {v['n_cells']}",
              f"  M0 mean abs error (ln units) {v['MAE_M0']:.3f}; M1 {v['MAE_M1']:.3f}; M1 - M0 = {b['diff']:+.3f} (90% interval {b['lo']:+.3f} to {b['hi']:+.3f})",
              f"  M1 90% prediction interval for ln value: {v['pi'][0]:+.2f} to {v['pi'][1]:+.2f}; coverage {v['coverage']:.2f}",
              "  half-life (years, 90% interval) by oiling class:"]
        for _, h in hl.iterrows():
            L.append(f"    {h.oil_class:11s} stations {h.n_stations:3d} (2+ campaigns {h.n_stations_2plus_campaigns:3d}); k {h.k_per_year:+.3f}/yr "
                     f"({h.k_lo90:+.3f} to {h.k_hi90:+.3f}); half-life {fmt_hl(h.half_life_years)} ({fmt_hl(h.half_life_lo90)} to {fmt_hl(h.half_life_hi90)})"
                     + ("" if h.class_specific_fit else "  [pooled k used: too few stations]"))
        L.append("")
    L += ["Sum versus hopane: a decline in the sum with no decline in the ratio means physical loss (erosion, burial, removal), not degradation (plan).",
          "", "Sensitivity runs: see sensitivity.csv. Processing counts: processing_log.txt.",
          "", "Bug fixes after seeing real results: none recorded here unless listed below.", ""]
    (RESULTS / "summary.txt").write_text("\n".join(L))
    print("done")


if __name__ == "__main__":
    main()
