"""V4 R7 sensitivity A: edge-loss model covariance (not a change to any default).

validation/naip_edge_loss.py and validation/p1_prespill_check.py fit
``rate ~ C(max_oiling, Treatment('NOO')) + water_1km_2010 + C(cell_2km)`` with standard errors
clustered by cell_2km. For 2010-2015 that is 181 parameters (176 cell_2km dummies + intercept +
4 oiling dummies + water term) estimated with only 176 clusters -- the cluster-robust sandwich is
rank-deficient there (and similarly for 2010-2017: 185 params / 180 clusters; and for the P1
headline check: 205 params / 200 clusters). This script:

  1. Refits each model with the within (cell_2km-absorbed) transform: demean rate, the oiling
     dummies and water_1km_2010 within cell_2km, then OLS *without* the block dummies, clustered by
     cell_2km (statsmodels cov_type="cluster"; with only ~6 parameters left the sandwich is no
     longer rank-deficient). By the Frisch-Waugh-Lovell theorem the point estimates must equal the
     original block-dummy model's (asserted below); only the clustered covariance differs.
  2. Reports a wild cluster bootstrap (Rademacher weights, 999 draws, seed fixed) 90% interval for
     the Heavy coefficient, built from the within-model residuals (equivalent to the full model's
     by FWL, and much cheaper to refit 999 times).
  3. Does the same for the P1 headline model (check 3, "adjusted": (2008.6-2015.6 rate) minus
     (1999.6-2008.6 rate)), since validation/p1_prespill_check.py uses the identical block-dummy +
     cluster pattern for its primary (pre-registered headline) model.

Run:    python -m validation.v4_r7_edge_loss_covariance
Writes: results/v4_r7/edge_loss_covariance.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import patsy
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from validation.naip_edge_loss import CLASSES, PERIODS, cell_rates, fit  # noqa: E402
from validation.p1_prespill_check import FORMULA as P1_FORMULA  # noqa: E402
from validation.p1_prespill_check import HEAVY as P1_HEAVY  # noqa: E402
from validation.p1_prespill_check import landsat_panel  # noqa: E402

RESULTS = ROOT / "results" / "v4_r7"
NAIP_DIR = ROOT / "data" / "external" / "naip_edge"
P1_DIR = ROOT / "data" / "external" / "p1"
NAIP_COEFS = ROOT / "results" / "naip_edge_loss" / "coefficients.csv"
RHS = "C(max_oiling, Treatment('NOO')) + water_1km_2010"  # the model's RHS minus the C(cell_2km) block dummies
HEAVY_TERM = "C(max_oiling, Treatment('NOO'))[T.Heavy]"
ALPHA = 0.10
N_BOOT = 999
BOOT_SEED = 20261113


def _term_label(col: str) -> str:
    return col.split("[T.")[-1].rstrip("]") if "[T." in col else col


def within_design(d: pd.DataFrame, rhs: str, group_col: str) -> tuple[np.ndarray, pd.DataFrame, np.ndarray]:
    """Demean the outcome and the RHS design matrix (dropping Intercept) within group_col groups."""
    y_df, X_df = patsy.dmatrices(f"rate ~ {rhs}", data=d, return_type="dataframe")
    groups = d[group_col].reset_index(drop=True).to_numpy()
    y = y_df.iloc[:, 0]
    y_dm = (y - y.groupby(groups).transform("mean")).to_numpy()
    X_dm = X_df.apply(lambda col: col - col.groupby(groups).transform("mean"))
    X_dm = X_dm.drop(columns=["Intercept"])
    return y_dm, X_dm, groups


def within_fit(d: pd.DataFrame, rhs: str, group_col: str = "cell_2km", alpha: float = ALPHA):
    y_dm, X_dm, groups = within_design(d, rhs, group_col)
    codes, _ = pd.factorize(groups)
    model = sm.OLS(y_dm, X_dm.to_numpy()).fit(cov_type="cluster", cov_kwds={"groups": codes})
    params = pd.Series(model.params, index=X_dm.columns)
    ci = pd.DataFrame(model.conf_int(alpha=alpha), index=X_dm.columns, columns=["lo", "hi"])
    pvals = pd.Series(model.pvalues, index=X_dm.columns)
    return {"model": model, "X_dm": X_dm, "y_dm": y_dm, "groups": groups, "codes": codes,
            "params": params, "ci": ci, "pvalues": pvals}


def wild_cluster_bootstrap(X_dm: pd.DataFrame, y_dm: np.ndarray, codes: np.ndarray, term: str,
                            n_boot: int = N_BOOT, seed: int = BOOT_SEED, alpha: float = ALPHA):
    """Wild cluster bootstrap (Rademacher weights, one draw per cluster applied to all its rows)."""
    Xv = X_dm.to_numpy()
    base = sm.OLS(y_dm, Xv).fit()
    fitted, resid = base.fittedvalues, base.resid
    col = list(X_dm.columns).index(term)
    n_clusters = codes.max() + 1
    XtX_inv = np.linalg.inv(Xv.T @ Xv)
    rng = np.random.default_rng(seed)
    betas = np.empty(n_boot)
    for b in range(n_boot):
        w = rng.choice(np.array([-1.0, 1.0]), size=n_clusters)
        y_star = fitted + w[codes] * resid
        betas[b] = (XtX_inv @ (Xv.T @ y_star))[col]
    lo, hi = np.percentile(betas, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi), betas


def assert_matches_original(label: str, within_params: pd.Series, original: dict, atol: float = 0.0015) -> None:
    for col, est in within_params.items():
        term = _term_label(col)
        if term not in original:
            continue
        orig_est = original[term]
        diff = abs(float(est) - orig_est)
        assert diff <= atol, (
            f"{label}: within estimate for {term} = {est:.4f} does not match original {orig_est:.4f} "
            f"(FWL should make these identical to rounding; diff {diff:.5f})"
        )


def run_naip() -> list[dict]:
    orig_coef = pd.read_csv(NAIP_COEFS)
    rows = []
    for label in PERIODS:
        year = PERIODS[label][0]
        d = cell_rates(NAIP_DIR, year)
        full_formula = f"rate ~ {RHS} + C(cell_2km)"
        full = fit(d, full_formula)  # original block-dummy model, for the original (singular) 90% CI
        orig_slice = orig_coef[orig_coef.period == label].set_index("term")
        original = {t: float(r.estimate) for t, r in orig_slice.iterrows()}

        wf = within_fit(d, RHS)
        assert_matches_original(f"naip {label}", wf["params"], original)

        boot_lo, boot_hi, _ = wild_cluster_bootstrap(wf["X_dm"], wf["y_dm"], wf["codes"], HEAVY_TERM)

        for col in wf["params"].index:
            term = _term_label(col)
            orig_lo = orig_slice.loc[term, "lo"] if term in orig_slice.index else np.nan
            orig_hi = orig_slice.loc[term, "hi"] if term in orig_slice.index else np.nan
            rows.append({
                "model": f"naip_edge_loss {label}", "term": term,
                "estimate": round(float(wf["params"][col]), 4),
                "original_lo": orig_lo, "original_hi": orig_hi,
                "within_lo": round(float(wf["ci"].loc[col, "lo"]), 4), "within_hi": round(float(wf["ci"].loc[col, "hi"]), 4),
                "within_p": round(float(wf["pvalues"][col]), 4),
                "bootstrap_lo": round(boot_lo, 4) if term == "Heavy" else np.nan,
                "bootstrap_hi": round(boot_hi, 4) if term == "Heavy" else np.nan,
                "n_obs": int(d.shape[0]), "n_clusters": int(d.cell_2km.nunique()),
                "n_params_original_model": len(full.params),
                "note": "cluster-robust sandwich in the original (block-dummy) model is rank-deficient "
                        f"({len(full.params)} params, {d.cell_2km.nunique()} clusters); within model has "
                        f"{wf['X_dm'].shape[1]} params.",
            })
    return rows


def run_p1() -> list[dict]:
    d = landsat_panel(P1_DIR)
    d3 = d.assign(rate=d.rate_BC - d.rate_AB).dropna(subset=["rate"]).reset_index(drop=True)
    full_formula = f"rate ~ {RHS} + C(cell_2km)"
    full = fit(d3, full_formula)
    full_ci = full.conf_int(alpha=ALPHA)

    wf = within_fit(d3, RHS)
    original = {_term_label(col): float(full.params[col]) for col in full.params.index if col != "Intercept" and not col.startswith("C(cell_2km")}
    assert_matches_original("p1 headline (check 3, adjusted)", wf["params"], original)

    boot_lo, boot_hi, _ = wild_cluster_bootstrap(wf["X_dm"], wf["y_dm"], wf["codes"], P1_HEAVY)
    assert P1_HEAVY == HEAVY_TERM, "p1 and naip must use the same Heavy term name for this to be comparable"

    rows = []
    for col in wf["params"].index:
        term = _term_label(col)
        rows.append({
            "model": "p1_headline check3_adjusted", "term": term,
            "estimate": round(float(wf["params"][col]), 4),
            "original_lo": round(float(full_ci.loc[col, 0]), 4), "original_hi": round(float(full_ci.loc[col, 1]), 4),
            "within_lo": round(float(wf["ci"].loc[col, "lo"]), 4), "within_hi": round(float(wf["ci"].loc[col, "hi"]), 4),
            "within_p": round(float(wf["pvalues"][col]), 4),
            "bootstrap_lo": round(boot_lo, 4) if term == "Heavy" else np.nan,
            "bootstrap_hi": round(boot_hi, 4) if term == "Heavy" else np.nan,
            "n_obs": int(d3.shape[0]), "n_clusters": int(d3.cell_2km.nunique()),
            "n_params_original_model": len(full.params),
            "note": "original (full block-dummy model, same spec as naip_edge_loss.fit()) recomputed here; "
                    "results/p1_prespill/checks.csv only stores the Heavy row. cluster-robust sandwich in the "
                    f"original model is rank-deficient ({len(full.params)} params, {d3.cell_2km.nunique()} clusters); "
                    f"within model has {wf['X_dm'].shape[1]} params.",
        })
    return rows


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    rows = run_naip() + run_p1()
    out = pd.DataFrame(rows)
    out.to_csv(RESULTS / "edge_loss_covariance.csv", index=False)
    pd.set_option("display.width", 250)
    print(out.to_string(index=False))
    print("\nAll within-model point estimates matched their original block-dummy models to rounding (FWL theorem); see asserts above.")


if __name__ == "__main__":
    main()
