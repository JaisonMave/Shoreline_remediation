"""V5 sand-beach persistence of visible oil: gated validation and packaging (D39).

Plan (fixed before the run): docs/V5_BEACH_SAND_PLAN.md. Run once:

    python -m validation.v5_beach_sand

Reads  data/external/scat_dwh_mobile/beach_series.csv (built by scripts/build_beach_series.py)
Writes results/v5_beach/*.csv, results/v5_beach/summary.txt, models/beach_sand_persistence_v1.json

Bootstrap sizes (modest, fixed): 200 refits per held-out state (gate B-2 intervals), 100 per held-out county
(descriptive), 200 for the packaged all-states model. Seed 20261114.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.shoreline_remediation import beach_model as bm

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "external" / "scat_dwh_mobile" / "beach_series.csv"
OUT = ROOT / "results" / "v5_beach"
CARD = ROOT / "models" / "beach_sand_persistence_v1.json"
SEED = 20261114
H = np.array(bm.HORIZONS, dtype=float)
B_STATE, B_COUNTY, B_FINAL = 200, 100, 200
MAX_GAP_SENS = 60  # ASSUMED (plan section 6)
STATES = ("AL", "MS", "FL")
MIN_GROUP = 20


def load(path=DATA) -> pd.DataFrame:
    s = pd.read_csv(path)
    d = s[(s["esi_class"] == "3A") & (s["ever_oiled"] == 1) & (s["n_visits_after_first_oiled"] > 0)].copy()
    d["R"] = d["R_days"].fillna(np.inf).astype(float)
    d["L"] = d["L_days"].astype(float)
    d["county_key"] = d["state"] + "-" + d["county"]
    return d.reset_index(drop=True)


def design(df, mean=None, sd=None):
    return bm.standardise(bm.raw_terms(df.to_dict("records")), mean, sd)


# ---------------------------------------------------------------------------------------------------------------
def fit_model(train):
    X, m, s = design(train)
    return {"theta": bm.fit_pe(X, train["L"].to_numpy(), train["R"].to_numpy()), "mean": m, "sd": s}


def predict_model(fit, test):
    X, _, _ = design(test, fit["mean"], fit["sd"])
    return bm.surv_pe(fit["theta"], X)


def fit_baseline(train):
    pooled = bm.turnbull_surv(bm.turnbull(train["L"], train["R"]))
    curves = {}
    for g in bm.CAT_LEVELS:
        t = train[train["first_cat_group"] == g]
        curves[g] = bm.turnbull_surv(bm.turnbull(t["L"], t["R"])) if len(t) >= MIN_GROUP else pooled
    return curves


def predict_baseline(curves, test):
    return np.vstack([curves[g] for g in test["first_cat_group"]])


def known_status(df):
    """y[i,h] = 1 persistent, 0 cleared, nan unknown at horizon h."""
    L, R = df["L"].to_numpy()[:, None], df["R"].to_numpy()[:, None]
    y = np.full((len(df), len(H)), np.nan)
    y[R <= H[None, :]] = 0.0
    y[L >= H[None, :]] = 1.0
    return y


def brier(pred, y):
    ok = ~np.isnan(y)
    per_h = np.array([np.mean((pred[ok[:, j], j] - y[ok[:, j], j]) ** 2) if ok[:, j].any() else np.nan
                      for j in range(len(H))])
    return per_h, ok.mean(axis=0)


def boot_state_interval(train, test, B, rng):
    """5-95% interval of the state-mean of 0/1 draws from S(h|x), over segment-bootstrap refits."""
    draws = np.empty((B, len(H)))
    theta0 = None
    for b in range(B):
        idx = rng.integers(0, len(train), len(train))
        tr = train.iloc[idx]
        X, m, s = design(tr)
        th = bm.fit_pe(X, tr["L"].to_numpy(), tr["R"].to_numpy(), theta0)
        p = predict_model({"theta": th, "mean": m, "sd": s}, test)
        draws[b] = (rng.random(p.shape) < p).mean(axis=0)
    return np.percentile(draws, 5, axis=0), np.percentile(draws, 95, axis=0)


def calibration(pred, test, label, model_name, rows):
    for j, h in enumerate(H):
        q = pd.qcut(pd.Series(pred[:, j]).rank(method="first"), 5, labels=False)
        for b in range(5):
            sel = (q == b).to_numpy()
            t = test[sel]
            obs = bm.turnbull_surv(bm.turnbull(t["L"], t["R"]), [h])[0]
            rows.append({"holdout": label, "model": model_name, "horizon_days": int(h), "bin": b + 1,
                         "n": int(sel.sum()), "mean_predicted": pred[sel, j].mean(), "observed_turnbull": obs})


def evaluate(d, group_col, groups, B, rng, tag, cal_rows=None, xgb=False):
    rows, pooled = [], {"model": [], "base": [], "xgb": [], "y": []}
    for g in groups:
        train, test = d[d[group_col] != g], d[d[group_col] == g]
        fm, fb = fit_model(train), fit_baseline(train)
        pm, pb = predict_model(fm, test), predict_baseline(fb, test)
        y = known_status(test)
        bsm, share = brier(pm, y)
        bsb, _ = brier(pb, y)
        obs = bm.turnbull_surv(bm.turnbull(test["L"], test["R"]))
        lo, hi = boot_state_interval(train, test, B, rng)
        rec = {"holdout": g, "n_series": len(test)}
        for j, h in enumerate(H):
            h = int(h)
            rec.update({f"brier_model_{h}": bsm[j], f"brier_base_{h}": bsb[j], f"share_scored_{h}": share[j],
                        f"obs_persist_{h}": obs[j], f"pred_model_{h}": pm[:, j].mean(),
                        f"pred_base_{h}": pb[:, j].mean(), f"lo90_{h}": lo[j], f"hi90_{h}": hi[j],
                        f"covered_{h}": bool(lo[j] <= obs[j] <= hi[j])})
        rec["ibs_model"], rec["ibs_base"] = np.nanmean(bsm), np.nanmean(bsb)
        if xgb:
            px = xgb_predict(train, test)
            bsx, _ = brier(px, y)
            rec["ibs_xgb_secondary"] = np.nanmean(bsx)
            pooled["xgb"].append(px)
        rows.append(rec)
        pooled["model"].append(pm); pooled["base"].append(pb); pooled["y"].append(y)
        if cal_rows is not None:
            calibration(pm, test, g, "model", cal_rows)
            calibration(pb, test, g, "baseline", cal_rows)
    y = np.vstack(pooled["y"])
    pm_, _ = brier(np.vstack(pooled["model"]), y)
    pb_, share = brier(np.vstack(pooled["base"]), y)
    rec = {"holdout": "pooled", "n_series": len(y), "ibs_model": np.nanmean(pm_), "ibs_base": np.nanmean(pb_)}
    for j, h in enumerate(H):
        rec.update({f"brier_model_{int(h)}": pm_[j], f"brier_base_{int(h)}": pb_[j], f"share_scored_{int(h)}": share[j]})
    if xgb:
        px_, _ = brier(np.vstack(pooled["xgb"]), y)
        rec["ibs_xgb_secondary"] = np.nanmean(px_)
    rows.append(rec)
    out = pd.DataFrame(rows)
    out.insert(0, "analysis", tag)
    return out


def xgb_predict(train, test):
    """Secondary, not gated: XGBoost AFT (normal, scale 1.0, depth 3, eta 0.05, 300 rounds; ASSUMED, untuned)."""
    import xgboost as xgb
    from scipy.stats import norm
    Xtr, m, s = design(train)
    Xte, _, _ = design(test, m, s)
    dtr = xgb.DMatrix(Xtr)
    dtr.set_float_info("label_lower_bound", train["L"].to_numpy())
    dtr.set_float_info("label_upper_bound", train["R"].to_numpy())
    params = {"objective": "survival:aft", "aft_loss_distribution": "normal", "aft_loss_distribution_scale": 1.0,
              "max_depth": 3, "eta": 0.05, "seed": SEED, "verbosity": 0}
    bst = xgb.train(params, dtr, num_boost_round=300)
    mu = np.log(np.maximum(bst.predict(xgb.DMatrix(Xte)), 1e-6))
    return 1.0 - norm.cdf((np.log(H)[None, :] - mu[:, None]) / 1.0)


def reoiling(d):
    c = d[d["censor"] == "interval"]
    c = c[c["n_visits_after_clear"] > 0]
    rows = []
    for key, g in [("all", c)] + [(f"state={k}", v) for k, v in c.groupby("state")] + \
                  [(f"group={k}", v) for k, v in c.groupby("first_cat_group")]:
        rows.append({"subset": key, "n_cleared_with_later_visit": len(g), "n_reoiled": int(g["reoiled"].sum()),
                     "share_reoiled": g["reoiled"].mean(),
                     "median_days_clear_to_reoil": g["days_clear_to_reoil"].median(),
                     "reoil_category_counts": json.dumps(g["reoil_cat"].value_counts().to_dict())})
    return pd.DataFrame(rows)


def final_fit(d, rng):
    fm = fit_model(d)
    X, m, s = design(d)
    thetas = []
    for _ in range(B_FINAL):
        idx = rng.integers(0, len(d), len(d))
        tr = d.iloc[idx]
        Xb, _, _ = design(tr, m, s)  # keep the full-data standardisation so coefficients are comparable
        thetas.append(bm.fit_pe(Xb, tr["L"].to_numpy(), tr["R"].to_numpy(), fm["theta"]))
    base = {}
    for g in bm.CAT_LEVELS:
        t = d[d["first_cat_group"] == g]
        cur = bm.turnbull_surv(bm.turnbull(t["L"], t["R"]))
        bs = []
        for _ in range(B_FINAL):
            tb = t.iloc[rng.integers(0, len(t), len(t))]
            bs.append(bm.turnbull_surv(bm.turnbull(tb["L"], tb["R"])))
        bs = np.array(bs)
        base[g] = {"n": len(t), "point": cur.tolist(), "median": np.median(bs, 0).tolist(),
                   "lo90": np.percentile(bs, 5, 0).tolist(), "hi90": np.percentile(bs, 95, 0).tolist()}
    return fm, np.array(thetas), base


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    d = load()
    cal = []
    loso = evaluate(d, "state", STATES, B_STATE, rng, "leave_one_state_out", cal, xgb=True)
    loso.to_csv(OUT / "loso_brier_and_persistence.csv", index=False)
    pd.DataFrame(cal).to_csv(OUT / "calibration_by_state.csv", index=False)

    # Gates
    st = loso[loso["holdout"] != "pooled"].set_index("holdout")
    pooled = loso[loso["holdout"] == "pooled"].iloc[0]
    wins = int((st["ibs_model"] < st["ibs_base"]).sum())
    b1 = bool(wins >= 2 and pooled["ibs_model"] < pooled["ibs_base"])
    b2_rows = {s: {"pred": st.loc[s, "pred_model_365"], "obs": st.loc[s, "obs_persist_365"],
                   "lo90": st.loc[s, "lo90_365"], "hi90": st.loc[s, "hi90_365"]} for s in STATES}
    for s, r in b2_rows.items():
        r["abs_diff_pp"] = abs(r["pred"] - r["obs"]) * 100
        r["pass"] = bool(r["abs_diff_pp"] <= 10 and r["lo90"] <= r["obs"] <= r["hi90"])
    b2 = all(r["pass"] for r in b2_rows.values())

    cov = []
    for s in STATES:
        for h in bm.HORIZONS:
            cov.append({"holdout": s, "horizon_days": h, "observed": st.loc[s, f"obs_persist_{h}"],
                        "predicted": st.loc[s, f"pred_model_{h}"], "lo90": st.loc[s, f"lo90_{h}"],
                        "hi90": st.loc[s, f"hi90_{h}"], "covered": st.loc[s, f"covered_{h}"]})
    pd.DataFrame(cov).to_csv(OUT / "interval_coverage_by_state.csv", index=False)

    # Secondary hold-out: counties with >= 40 series
    cc = d["county_key"].value_counts()
    counties = sorted(cc[cc >= 40].index)
    county = evaluate(d, "county_key", counties, B_COUNTY, rng, "leave_one_county_out")
    county.to_csv(OUT / "secondary_county_holdout.csv", index=False)

    # Sensitivity: informative visiting
    ds = d[d["max_gap_days"] <= MAX_GAP_SENS].reset_index(drop=True)
    sens = evaluate(ds, "state", STATES, B_COUNTY, rng, f"sensitivity_max_gap_le_{MAX_GAP_SENS}d")
    sens.to_csv(OUT / "sensitivity_visit_frequency.csv", index=False)
    n_alt = int(((d["alt_R_days"].fillna(-1) != d["R_days"].fillna(-1)) |
                 (d["alt_L_days"] != d["L_days"])).sum())

    reo = reoiling(d)
    reo.to_csv(OUT / "reoiling.csv", index=False)

    # Final fit and card
    fm, thetas, base = final_fit(d, rng)
    pd.DataFrame({"term": [f"baseline_log_hazard_piece_{int(c)}d" for c in bm.CUTS] + list(bm.TERMS),
                  "estimate": fm["theta"], "boot_lo90": np.percentile(thetas, 5, 0),
                  "boot_hi90": np.percentile(thetas, 95, 0)}).to_csv(OUT / "coefficients_all_states.csv", index=False)
    if b1 and b2:
        declared = "experimental (gates passed, awaiting owner review)"
    else:
        failed = [n for n, ok in (("B-1", b1), ("B-2", b2)) if not ok]
        declared = "experimental (gate failed: " + ", ".join(failed) + ")"
    packaged = "model" if b1 else "baseline"
    write_card(d, fm, thetas, base, loso, b1, b2, wins, b2_rows, declared, packaged, county, sens, reo, n_alt)
    write_summary(d, loso, b1, b2, wins, b2_rows, declared, packaged, county, sens, reo, n_alt, ds)


def write_card(d, fm, thetas, base, loso, b1, b2, wins, b2_rows, declared, packaged, county, sens, reo, n_alt):
    st = loso.set_index("holdout")
    card = {
        "name": "beach_sand_persistence_v1",
        "title": "Sand-beach (ESI 3A) persistence of visible oil, DWH SCAT",
        "decision": "D39",
        "plan": "docs/V5_BEACH_SAND_PLAN.md",
        "validation": "validation/v5_beach_sand.py (leave-one-state-out; results/v5_beach/)",
        "declared_state": declared,
        "packaged_prediction": packaged,
        "baseline_beaten": bool(b1),
        "data": {"source": "NCEI Accession 0163818 layer 18613 (SCAT All zones, Mobile), DOI 10.7289/v53t9ffx",
                 "derived_table": "data/external/scat_dwh_mobile/beach_series.csv",
                 "n_series": int(len(d)), "n_by_state": d["state"].value_counts().to_dict(),
                 "survey_period": "2010-05-05 to 2013-06-18"},
        "definition": {"unit": "SCAT segment classed ESI 3A (>=80% of ESI-coded zone length), ever oiled, with a later visit",
                       "time_zero": "first oiled visit",
                       "event": "first visit with every zone NOO (No Oil Observed) covering >=50% of the segment",
                       "target": "P(visible oil still recorded at 90, 180, 365, 730 days)",
                       "censoring": "interval-censored between last oiled and first clear visit; right-censored at last visit"},
        "predictors": {"first_cat_group or first_cat": list(bm.CAT_LEVELS),
                       "first_tidal_zone": ["UI", "SU", "MI", "LI"], "first_thickness": ["none", "thick", "thin"],
                       "first_sodistro_pct": "0-100 %", "first_tb_count": "count",
                       "days_spill_to_first_oiled": "days from 20 April 2010",
                       "exposure_open_frac": "0-1, share of 7 southward rays (20 km) crossing no other SCAT shoreline"},
        "model": "piecewise-exponential proportional hazards, interval-censored ML, ridge 0.01 on standardised terms",
        "terms": list(bm.TERMS), "cuts_days": bm.CUTS.tolist(),
        "theta_all_states": fm["theta"].tolist(),
        "standardisation": {"columns": list(bm.CONT), "mean": fm["mean"].tolist(), "sd": fm["sd"].tolist()},
        "bootstrap_theta": np.round(thetas, 6).tolist(),
        "interval_method": f"5th-95th percentile over {B_FINAL} refits resampling whole segments (parameter "
                           "uncertainty for one segment's persistence probability)",
        "interval_level": 0.9,
        "baseline_curves_all_states": base,
        "per_state_results": {h: {k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
                                  for k, v in st.loc[h].items() if k != "analysis"} for h in st.index},
        "gates": {"B-1": {"pass": bool(b1), "states_model_better": wins,
                          "pooled_ibs_model": float(st.loc["pooled", "ibs_model"]),
                          "pooled_ibs_base": float(st.loc["pooled", "ibs_base"])},
                  "B-2": {"pass": bool(b2), "by_state": {k: {kk: (bool(vv) if isinstance(vv, (bool, np.bool_)) else float(vv))
                                                             for kk, vv in v.items()} for k, v in b2_rows.items()}}},
        "interval_coverage": "results/v5_beach/interval_coverage_by_state.csv",
        "training_range": {"states": list(STATES), "esi": ["3A"],
                           "continuous": {k: [float(d[k].min()), float(d[k].max())] for k in
                                          ("days_spill_to_first_oiled", "first_sodistro_pct", "first_tb_count",
                                           "exposure_open_frac")}},
        "secondary": {"county_holdout": "results/v5_beach/secondary_county_holdout.csv",
                      "sensitivity_visit_frequency": "results/v5_beach/sensitivity_visit_frequency.csv",
                      "partial_clear_series_changed": n_alt,
                      "reoiling": "results/v5_beach/reoiling.csv",
                      "xgboost_aft_pooled_ibs": float(st.loc["pooled", "ibs_xgb_secondary"])},
        "caveats": [
            "Treatment is not recorded per segment and most oiled sand beach was treated (Michel et al. 2017: about 683 of 965 km with documented treatment). This is persistence under the response as carried out, NOT natural recovery; it cannot rank treatments.",
            "Surveys were scheduled by response priority, not at random (informative visiting); see the sensitivity check.",
            "SCAT oiling is visible surface oil and a cleanup endpoint, not chemical or ecological recovery; buried oil is not captured.",
            "One spill (Deepwater Horizon), three states (AL, MS, FL panhandle).",
            "The orchestrator and an earlier agent had seen record counts, but not outcomes, before the gates were set.",
            "ESI 4 (coarse sand) not included: 9 segments, none oiled. Series are segments, not zones (zone IDs are re-assigned every survey)."],
        "caveats_short": ["DWH only; persistence under the 2010-2013 cleanup, not natural recovery; visible surface oil only"],
    }
    with open(CARD, "w") as f:
        json.dump(card, f, indent=1, default=_json_default)


def _json_default(o):
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def write_summary(d, loso, b1, b2, wins, b2_rows, declared, packaged, county, sens, reo, n_alt, ds):
    st = loso.set_index("holdout")
    L = ["V5 sand-beach persistence (D39) - summary", f"series: {len(d)} {d['state'].value_counts().to_dict()}",
         f"censoring: {d['censor'].value_counts().to_dict()}", "",
         "Leave-one-state-out integrated Brier score (lower is better):"]
    for h in list(STATES) + ["pooled"]:
        r = st.loc[h]
        L.append(f"  {h:6s} model {r['ibs_model']:.4f}  baseline {r['ibs_base']:.4f}  xgb(secondary) {r['ibs_xgb_secondary']:.4f}")
    L.append("")
    L.append("Persistence at 365 d (held-out state): observed Turnbull / model mean [90% interval] / baseline mean")
    for s in STATES:
        r = b2_rows[s]
        L.append(f"  {s}: {r['obs']:.3f} / {r['pred']:.3f} [{r['lo90']:.3f}, {r['hi90']:.3f}] / "
                 f"{st.loc[s, 'pred_base_365']:.3f}  |diff| {r['abs_diff_pp']:.1f} pp  -> {'pass' if r['pass'] else 'FAIL'}")
    L += ["", f"Gate B-1: {'PASS' if b1 else 'FAIL'} (model better in {wins}/3 states; pooled "
              f"{st.loc['pooled', 'ibs_model']:.4f} vs {st.loc['pooled', 'ibs_base']:.4f})",
          f"Gate B-2: {'PASS' if b2 else 'FAIL'}", f"Declared state: {declared}",
          f"Packaged prediction: {packaged}", ""]
    sp = sens[sens["holdout"] == "pooled"].iloc[0]
    L.append(f"Sensitivity (max visit gap <= {MAX_GAP_SENS} d, n={len(ds)}): pooled IBS model {sp['ibs_model']:.4f} "
             f"vs baseline {sp['ibs_base']:.4f}; model better in "
             f"{int((sens[sens.holdout!='pooled'].ibs_model < sens[sens.holdout!='pooled'].ibs_base).sum())}/3 states")
    for _, r in sens[sens.holdout != "pooled"].iterrows():
        L.append(f"   {r['holdout']}: observed 365 d persistence {r['obs_persist_365']:.3f} (full data {st.loc[r['holdout'], 'obs_persist_365']:.3f})")
    L.append(f"Partial-clear visits counted as clear would change {n_alt} series.")
    cp = county[county.holdout != "pooled"]
    L.append(f"County hold-out (descriptive, {len(cp)} counties): model better in {int((cp.ibs_model < cp.ibs_base).sum())}; "
             f"365 d interval covers observed in {int(cp['covered_365'].sum())}; pooled IBS model "
             f"{county[county.holdout=='pooled'].ibs_model.iloc[0]:.4f} vs baseline {county[county.holdout=='pooled'].ibs_base.iloc[0]:.4f}")
    a = reo[reo.subset == "all"].iloc[0]
    L.append(f"Re-oiling (descriptive): {a['n_reoiled']} of {a['n_cleared_with_later_visit']} cleared series with a "
             f"later visit were oiled again ({a['share_reoiled']:.1%}); median {a['median_days_clear_to_reoil']:.0f} days after clearing")
    (OUT / "summary.txt").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
