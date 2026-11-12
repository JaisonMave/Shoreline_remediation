"""Period-split check of the heavy-oiling marsh-edge excess (plan: docs/PERIOD_SPLIT_CHECK_PLAN.md, parts A1-A3). Run once.

  A1  Heavy minus clean, edge loss 2015-2017 and 2010-2015 on the same cells (P1 check-4 model + Landsat pre-spill trend)
  A2  difference of the two Heavy coefficients, block bootstrap (2,000 resamples of 2 km blocks, seed 20261112)
  A3  same contrasts for Very Light and Light oiling (null baseline: residual exposure confounding)
  (Part B is not implemented.)

Model, both periods: rate ~ oiling class (NOO reference) + water_1km_2010 + water_250m_2010 + log_fetch
                      + rate_AB (Landsat 1999.6-2008.6 trend) + 2 km block effects.
A1 intervals: least squares, standard errors clustered by 2 km block, 90% (as in P1).
A2/A3 differences: percentile 90% interval over block-bootstrap replicates (whole 2 km blocks resampled with
replacement; a block drawn twice counts as two blocks; both periods refitted on the same resample).
Block effects are absorbed by within-block demeaning (identical point estimates to explicit dummies; checked in tests).

Panel filters (all applied in this order; counts written to summary.txt):
  F1-F4  the NAIP filters, inherited by calling validation.naip_edge_loss.cell_rates for 2015 and 2017:
         0.1 <= land fraction 2010 <= 0.9; valid fraction >= 0.9 in 2010 and in the later year;
         1 km block land share within 0.15 of 2010. Cells must pass for BOTH 2015 and 2017.
  F5     1 km block land share 2015 vs 2017 within 0.15 (analogue of the block filter for the new interval; ASSUMED).
  F6     exposure covariates and Landsat pre-spill trend available (P1 landsat panel filters).
  F7     flight dates in 2015 and 2017 give a positive interval.

Run:  python -m validation.period_split_check
Writes results/period_split/{A1,A2,A3}.csv and summary.txt
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

RESULTS = ROOT / "results" / "period_split"
NAIP = ROOT / "data" / "external" / "naip_edge"
P1 = ROOT / "data" / "external" / "p1"
SEED, N_BOOT = 20261112, 2000
FORMULA = ("rate ~ C(max_oiling, Treatment('NOO')) + water_1km_2010 + C(cell_2km)"
           " + water_250m_2010 + log_fetch + rate_AB")
COVARS = ["water_1km_2010", "water_250m_2010", "log_fetch", "rate_AB"]
TESTED = CLASSES[1:]  # Very_Light, Light, Moderate, Heavy (coefficients; Moderate is fitted but not reported)


def coef_key(cls: str) -> str:
    return f"C(max_oiling, Treatment('NOO'))[T.{cls}]"


def build_panel(naip_dir: Path = NAIP, p1_dir: Path = P1, landsat_rates: Path | None = None):
    """Return (panel, filter_log). Panel has rate_1015, rate_1517 and covariates."""
    log = []
    a = cell_rates(naip_dir, 2015).set_index("cell")
    b = cell_rates(naip_dir, 2017).set_index("cell")
    log.append(("2010-2015 sample after F1-F4", len(a)))
    log.append(("2010-2017 sample after F1-F4", len(b)))
    d = a[["max_oiling", "cell_2km", "water_1km_2010", "land_fraction_2010", "land_fraction_t", "flight_date_t",
           "block_land_fraction_t", "rate", "years"]].rename(columns={
        "land_fraction_t": "f15", "flight_date_t": "date15", "block_land_fraction_t": "blk15",
        "rate": "rate_1015", "years": "years_1015"})
    j = d.join(b[["land_fraction_t", "flight_date_t", "block_land_fraction_t"]].rename(columns={
        "land_fraction_t": "f17", "flight_date_t": "date17", "block_land_fraction_t": "blk17"}), how="inner")
    log.append(("cells passing F1-F4 in both periods", len(j)))
    n = len(j)
    j = j[(j.blk17 - j.blk15).abs() <= 0.15]
    log.append(("removed by F5 (block share 2015 vs 2017 > 0.15)", n - len(j)))
    ex = pd.read_csv(p1_dir / "exposure.csv").set_index("cell")
    ls = pd.read_csv(landsat_rates or ROOT / "results" / "p1_prespill" / "landsat_cell_rates.csv").set_index("cell")[["rate_AB"]]
    n = len(j)
    j = j.join(ex, how="inner").join(ls, how="inner")
    j["log_fetch"] = np.log(j.fetch_mean_m + 16)
    j = j.dropna(subset=["water_250m_2010", "log_fetch", "rate_AB", "water_1km_2010"])
    log.append(("removed by F6 (no exposure / Landsat pre-spill trend)", n - len(j)))
    yrs = (pd.to_datetime(j.date17) - pd.to_datetime(j.date15)).dt.days / 365.25
    n = len(j)
    j = j[yrs > 0]; yrs = yrs[yrs > 0]
    log.append(("removed by F7 (non-positive 2015-2017 interval)", n - len(j)))
    j["years_1517"] = yrs
    j["rate_1517"] = (j.f15 - j.f17) * 100 / yrs  # same conversion as 2010-2015: (f_start - f_end) * 100 m / years
    j["max_oiling"] = pd.Categorical(j.max_oiling, CLASSES)
    log.append(("final cells", len(j)))
    return j.reset_index(), log


def _design(d: pd.DataFrame):
    X = np.column_stack([(d.max_oiling == c).to_numpy(float) for c in TESTED] + [d[v].to_numpy(float) for v in COVARS])
    return X


def _within(X, y, blocks):
    """Absorb block effects by within-block demeaning; return coefficient vector (classes first)."""
    codes = pd.factorize(blocks)[0]
    cnt = np.bincount(codes)
    Xd = X - np.column_stack([np.bincount(codes, X[:, k]) / cnt for k in range(X.shape[1])])[codes]
    yd = y - (np.bincount(codes, y) / cnt)[codes]
    return np.linalg.lstsq(Xd, yd, rcond=None)[0]


def class_effects(d: pd.DataFrame, ycol: str) -> dict:
    beta = _within(_design(d), d[ycol].to_numpy(float), d.cell_2km.to_numpy())
    return dict(zip(TESTED, beta[:len(TESTED)]))


def ols_interval(d: pd.DataFrame, ycol: str, cls: str) -> tuple[float, float, float]:
    m = fit(d.assign(rate=d[ycol]), FORMULA)
    lo, hi = m.conf_int(alpha=0.10).loc[coef_key(cls)]
    return float(m.params[coef_key(cls)]), float(lo), float(hi)


def bootstrap_diff(d: pd.DataFrame, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """Block bootstrap: per class, array of (2015-2017 minus 2010-2015) coefficient differences."""
    rng = np.random.default_rng(seed)
    X = _design(d); y1 = d.rate_1015.to_numpy(float); y2 = d.rate_1517.to_numpy(float)
    codes, uniq = pd.factorize(d.cell_2km)
    idx_by_block = [np.flatnonzero(codes == k) for k in range(len(uniq))]
    out = {c: np.full(n_boot, np.nan) for c in TESTED}
    for i in range(n_boot):
        draw = rng.integers(0, len(uniq), len(uniq))
        rows = np.concatenate([idx_by_block[k] for k in draw])
        blocks = np.concatenate([np.full(len(idx_by_block[k]), n) for n, k in enumerate(draw)])  # a repeated block = new block
        try:
            b1 = _within(X[rows], y1[rows], blocks); b2 = _within(X[rows], y2[rows], blocks)
        except np.linalg.LinAlgError:
            continue
        for k, c in enumerate(TESTED):
            out[c][i] = b2[k] - b1[k]
    return out


def reading(est_new: float, lo: float, hi: float, est_old: float) -> tuple[str, str]:
    """Plan 'Pre-specified reading' table, applied to the A1 Heavy 2015-2017 result."""
    includes_zero = lo <= 0 <= hi
    if includes_zero and est_new < 0.5 * est_old:
        return "row 1", "Fade: consistent with an oil effect of limited duration"
    if (not includes_zero) and est_new >= est_old:
        return "row 2", "No fade: exposure confounding likely"
    return "row 3", "Inconclusive: report as such; run B"


def analyse(d: pd.DataFrame, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    n_cls = {f"n_{c}": int((d.max_oiling == c).sum()) for c in CLASSES}
    nb = int(d.cell_2km.nunique())
    base = {**n_cls, "n_cells": len(d), "n_blocks": nb}
    est = {}
    for c in TESTED:
        for per, col in (("2010-2015", "rate_1015"), ("2015-2017", "rate_1517")):
            est[(c, per)] = ols_interval(d, col, c)
    boot = bootstrap_diff(d, n_boot, seed)
    diffs = {}
    for c in TESTED:
        v = boot[c][~np.isnan(boot[c])]
        e = est[(c, "2015-2017")][0] - est[(c, "2010-2015")][0]
        diffs[c] = (e, float(np.percentile(v, 5)), float(np.percentile(v, 95)), len(v), float(v.mean()))
    def rows(classes, kind):
        r = []
        for c in classes:
            for per in ("2010-2015", "2015-2017"):
                e, lo, hi = est[(c, per)]
                r.append({"contrast": f"{c} minus clean", "period": per, "estimate": e, "lo90": lo, "hi90": hi,
                          "interval": "clustered-SE 90%", **base})
            if kind == "A3":
                e, lo, hi, nv, _ = diffs[c]
                r.append({"contrast": f"{c} minus clean", "period": "difference (2015-2017 minus 2010-2015)",
                          "estimate": e, "lo90": lo, "hi90": hi, "interval": f"block-bootstrap 5th-95th pct, {nv} valid resamples", **base})
        return pd.DataFrame(r)
    a2 = diffs["Heavy"]
    A2 = pd.DataFrame([{"contrast": "Heavy minus clean", "period": "difference (2015-2017 minus 2010-2015)",
                        "estimate": a2[0], "lo90": a2[1], "hi90": a2[2],
                        "interval": f"block-bootstrap 5th-95th pct, {a2[3]} valid resamples", "boot_mean": a2[4], **base}])
    return {"A1": rows(["Heavy"], "A1"), "A2": A2, "A3": rows(["Very_Light", "Light"], "A3"), "est": est, "diffs": diffs}


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    d, log = build_panel()
    res = analyse(d)
    for k in ("A1", "A2", "A3"):
        res[k].round(4).to_csv(RESULTS / f"{k}.csv", index=False)
    e_new, lo, hi = res["est"][("Heavy", "2015-2017")]; e_old, lo0, hi0 = res["est"][("Heavy", "2010-2015")]
    row, text = reading(e_new, lo, hi, e_old)
    df = res["diffs"]
    lines = ["Period-split check (plan: docs/PERIOD_SPLIT_CHECK_PLAN.md, parts A1-A3). Run once; part B not run.", "",
             "FILTERS (cells)"] + [f"  {k}: {v}" for k, v in log]
    lines += ["", f"CELLS PER CLASS: " + ", ".join(f"{c} {int((d.max_oiling == c).sum())}" for c in CLASSES) + f"; 2 km blocks {d.cell_2km.nunique()}",
              f"median interval 2010-2015 {d.years_1015.median():.2f} y; 2015-2017 {d.years_1517.median():.2f} y", "",
              "A1 Heavy minus clean (m/yr, 90% interval, SE clustered by 2 km block)",
              f"  2010-2015: {e_old:.3f} ({lo0:.3f} to {hi0:.3f})", f"  2015-2017: {e_new:.3f} ({lo:.3f} to {hi:.3f})",
              "A2 difference 2015-2017 minus 2010-2015 (Heavy), block bootstrap 90%",
              f"  {df['Heavy'][0]:.3f} ({df['Heavy'][1]:.3f} to {df['Heavy'][2]:.3f})", "A3 null baseline"]
    for c in ("Very_Light", "Light"):
        a, b = res["est"][(c, "2010-2015")], res["est"][(c, "2015-2017")]
        lines.append(f"  {c}: 2010-2015 {a[0]:.3f} ({a[1]:.3f} to {a[2]:.3f}); 2015-2017 {b[0]:.3f} ({b[1]:.3f} to {b[2]:.3f}); "
                     f"difference {df[c][0]:.3f} ({df[c][1]:.3f} to {df[c][2]:.3f})")
    lines += ["", f"PRE-SPECIFIED READING: {row} of the plan table. {text}.",
              f"  Quoted: 2015-2017 interval {'includes' if lo <= 0 <= hi else 'excludes'} zero; estimate {e_new:.3f} vs half of "
              f"2010-2015 ({0.5 * e_old:.3f}); at least as large as 2010-2015 ({e_old:.3f}): {e_new >= e_old}.",
              "", "LIMITS (plan, plus): two-year interval, power not computed (ASSUMED adequate); cells eroded away by 2015 drop out;",
              "bootstrap percentile interval for the difference is not the same object as the clustered-SE intervals in A1.",
              "DEVIATIONS: none from the plan. F5 is an added filter (documented above); the Landsat trend is the P1 rate_AB column."]
    (RESULTS / "summary.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
