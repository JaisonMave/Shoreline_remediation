"""Mangrove oiling-effect model (plan: docs/SCENARIO_PROGRAMME_PLAN.md, Phase C2).

Estimates the OILING EFFECT over time (oiled minus unoiled sites) from Galeta site-year means. It is not a
treatment or recovery-after-cleanup model: the data have no pre-spill values and no cleanup variable.

Unit    : the site. Input rows are site-year means (one value per outcome, site, year); never roots or trees.
M0      : prediction for a held-out site-year = mean of the training UNOILED sites in that year (no oiling effect).
M1      : linear mixed model  value ~ oiled * C(year since spill), random intercept per site. Prediction for a held-out
          site uses the fixed effects only (its group and year), because its own intercept is unknown.
Time    : year since spill = calendar year - SPILL_YEAR (ASSUMED convention; spill April 1986, so 1987 = year 1).
Validation: leave one whole site out (a site's years are never split between train and test).
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

SPILL_YEAR = 1986   # ASSUMED: year-since-spill = calendar year - 1986
SEED, N_BOOT = 20261112, 2000
LEVEL = 0.90
OUTCOMES = {
    "root_documented_dead_share": "share of prop roots recorded dead (primary)",
    "leaves_per_shoot": "leaves per shoot, R. mangle (primary)",
    "root_oil_cover": "root oil cover, % (secondary)",
}


def load_site_year(path, outcome: str) -> pd.DataFrame:
    """Site-year means for one outcome: columns site, oiled (0/1), year, ys (year since spill), value."""
    d = pd.read_csv(path)
    d = d[(d.outcome == outcome) & d.cond.isin(["oiled", "unoiled"])].copy()
    if d.empty:
        raise ValueError(f"no rows for outcome {outcome}")
    d["oiled"] = (d.cond == "oiled").astype(int)
    d["ys"] = d.year.astype(int) - SPILL_YEAR
    return d[["site", "oiled", "year", "ys", "value"]].dropna().reset_index(drop=True)


def _fit_mixed(df: pd.DataFrame):
    import statsmodels.formula.api as smf
    d = df.copy()
    d["ys"] = d.ys.astype(int)
    last = None
    for method in ("lbfgs", "powell", "nm"):   # optimiser fallback only if the first hits a singular matrix
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                return smf.mixedlm("value ~ oiled * C(ys)", d, groups=d["site"]).fit(reml=True, method=method)
        except np.linalg.LinAlgError as e:
            last = e
    raise last


def _fixed_mean(params, oiled: int, ys: int, years: list[int]) -> float:
    """Fixed-effect value for a group in a year, built from the formula's coefficient names."""
    v = params["Intercept"] + (params["oiled"] if oiled else 0.0)
    if ys != min(years):
        v += params.get(f"C(ys)[T.{ys}]", 0.0)
        if oiled:
            v += params.get(f"oiled:C(ys)[T.{ys}]", 0.0)
    return float(v)


class M1:
    def __init__(self, df: pd.DataFrame):
        self.res = _fit_mixed(df)
        self.years = sorted(df.ys.astype(int).unique())

    def predict(self, oiled: int, ys: int) -> float:
        if ys not in self.years:
            raise ValueError(f"year since spill {ys} not in the training data")
        return _fixed_mean(self.res.fe_params, oiled, ys, self.years)

    def effects(self, level: float = LEVEL) -> pd.DataFrame:
        """Oiled minus unoiled by year since spill, with a Wald interval from the mixed model."""
        from scipy import stats
        p, cov = self.res.fe_params, self.res.cov_params().loc[self.res.fe_params.index, self.res.fe_params.index]
        z = stats.norm.ppf(0.5 + level / 2)
        rows = []
        for ys in self.years:
            c = pd.Series(0.0, index=p.index)
            c["oiled"] = 1.0
            nm = f"oiled:C(ys)[T.{ys}]"
            if nm in c.index:
                c[nm] = 1.0
            est = float(c @ p)
            se = float(np.sqrt(c.values @ cov.values @ c.values))
            rows.append({"year_since_spill": ys, "year": ys + SPILL_YEAR, "effect": est, "lo90": est - z * se,
                         "hi90": est + z * se, "se": se})
        return pd.DataFrame(rows)


def m0_predict(train: pd.DataFrame, ys: int) -> float:
    u = train[(train.oiled == 0) & (train.ys == ys)]
    if u.empty:
        raise ValueError(f"no unoiled training site in year since spill {ys}")
    return float(u.value.mean())


def loso(df: pd.DataFrame) -> pd.DataFrame:
    """Leave one whole site out. One row per held-out site-year with M0 and M1 predictions."""
    out = []
    for site in sorted(df.site.unique()):
        test = df[df.site == site]
        train = df[df.site != site]
        assert not set(train.site) & set(test.site)
        m1 = M1(train)
        for r in test.itertuples():
            out.append({"site": site, "oiled": r.oiled, "year": r.year, "ys": r.ys, "obs": r.value,
                        "M0": m0_predict(train, r.ys), "M1": m1.predict(r.oiled, r.ys)})
    return pd.DataFrame(out)


def per_site_table(pred: pd.DataFrame, offsets: dict | None = None) -> pd.DataFrame:
    """MAE of M0 and M1 per held-out site, and coverage of the 90% interval (M1 prediction + residual quantiles)."""
    if offsets is None:
        offsets = {m: np.quantile(pred.obs - pred[m], [0.05, 0.95]) for m in ("M0", "M1")}
    rows = []
    for site, g in pred.groupby("site"):
        r = {"site": site, "oiled": int(g.oiled.iloc[0]), "n_years": len(g)}
        for m in ("M0", "M1"):
            r[f"MAE_{m}"] = float((g.obs - g[m]).abs().mean())
            lo, hi = g[m] + offsets[m][0], g[m] + offsets[m][1]
            r[f"coverage_{m}"] = float(((g.obs >= lo) & (g.obs <= hi)).mean())
        rows.append(r)
    return pd.DataFrame(rows)


def bootstrap_difference(tab: pd.DataFrame, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """Site-averaged MAE(M1) - MAE(M0) (negative = M1 better) with a 90% bootstrap over sites."""
    rng = np.random.default_rng(seed)
    d = (tab.MAE_M1 - tab.MAE_M0).to_numpy()
    n = len(d)
    boots = np.array([d[rng.integers(0, n, n)].mean() for _ in range(n_boot)])
    return {"diff": float(d.mean()), "lo": float(np.percentile(boots, 5)), "hi": float(np.percentile(boots, 95)),
            "M0": float(tab.MAE_M0.mean()), "M1": float(tab.MAE_M1.mean())}


def verdict(diff: dict) -> str:
    """Rule as A1: M1 below M0 and the 90% interval excludes zero -> validated; M1 below M0 only -> suggestive."""
    if diff["diff"] < 0 and diff["hi"] < 0:
        return "validated"
    if diff["diff"] < 0:
        return "suggestive"
    return "not usable"


def run_outcome(df: pd.DataFrame, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    pred = loso(df)
    offsets = {m: [float(x) for x in np.quantile(pred.obs - pred[m], [0.05, 0.95])] for m in ("M0", "M1")}
    tab = per_site_table(pred, offsets)
    diff = bootstrap_difference(tab, n_boot, seed)
    full = M1(df)
    cov_all = {m: float(np.mean([((r.obs >= r[m] + offsets[m][0]) & (r.obs <= r[m] + offsets[m][1]))
                                 for _, r in pred.iterrows()])) for m in ("M0", "M1")}
    return {"pred": pred, "tab": tab, "diff": diff, "verdict": verdict(diff), "effects": full.effects(),
            "offsets": offsets, "coverage": cov_all, "n_oiled": int(df[df.oiled == 1].site.nunique()),
            "n_unoiled": int(df[df.oiled == 0].site.nunique()), "years": sorted(df.year.unique().tolist()),
            "sites": sorted(df.site.unique().tolist()), "fe_params": {k: float(v) for k, v in full.res.fe_params.items()}}
