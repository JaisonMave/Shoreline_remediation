"""Continuous recovery trajectories for the heavily oiled Bay Jimmy plots (data and fitting layer; no Streamlit, no drawing).

EXPERIMENTAL research presentation. Nothing here is read by the decision pipeline, the comparison layer, the screening
statuses, the registry or the report. Each curve is either
- FIT: a simple model fitted to the group's own plot-level longitudinal observations and drawn only across their dates, or
- CONDITIONAL: a scenario that borrows a rate the group's own data cannot identify (a shared or external rate), labelled so.
Observed group means are kept as separate records. Equations, sources and the parameter audit: docs/V5_4_RECOVERY_VIEW.md.

Data (all already in the repository, read directly from the files):
- Shoreline position: Zengel et al. (2022) GRIIDC doi:10.7266/VF524143, sheet "GIS field erosion points": tape and DGPS
  (about 10 cm) positions of the marsh edge along two transects per plot, dated surveys 4 Dec 2010 to 5 Oct 2016.
- Total vegetation cover: GRIIDC doi:10.7266/n7-cn03-z792 (compiled dataset of the Zengel et al. 2022 Ecol. Appl. meta-analysis), source "Zengel (B)" =
  the Zengel et al. (2015) plots with later unpublished surveys, 2011 to 2016. The 2011 and 2012 plot means equal the
  Zengel et al. (2015) S1 Table group means.
- Soil tPAH: Zengel et al. (2015) S1 Table group means (2011, 2012) and the DIVER heavy-class decline rate of pah_decline_v1.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import least_squares

from src.shoreline_remediation import recovery_view as RV, treatment_effects as te

VEG_DATA = te.DATA.parents[1] / "zengel2022_meta" / "dataset_compiled_for_GRIIDC.xlsx"
PAH_CLASS_TABLE = RV.ROOT / "results" / "pah_decline" / "by_oiling_class.csv"
ORIGIN = pd.Timestamp("2010-12-04")      # first field survey with every untreated, manual and reference transect
N_BOOT = 400
N_MC = 4000
SEED = 20261117
Z90 = 1.6448536269514722
FIT, CONDITIONAL = "fit", "conditional"
ROLE_TEXT = {FIT: "Experimental model fit (own plots)", CONDITIONAL: "Conditional scenario (borrowed rate)"}
STATUS_NOTE = ("Experimental and model-conditioned. Fits describe the Bay Jimmy plots over the dates they were surveyed; conditional "
               "scenarios borrow a rate the group's own data cannot identify. None is a validated forecast, none extends past its "
               "data or source support, and none is used by the screening, comparison or report.")
SCOPE = "Heavily oiled Spartina/Juncus salt marsh, Bay Jimmy (northern Barataria Bay), Deepwater Horizon; one site"
# Survey dates are those of recovery_view (verified in Zengel et al. 2015 Methods). The months of the 2013-2016 vegetation surveys
# are not recorded: September ASSUMED, as in 2011 and 2012.
VEG_X = RV.VEG_SURVEY_X[2011] - 2011
PAH_X = RV.PAH_SURVEY_X
REF_PLOTS = RV.REF_PLOTS
FIELD_TYPES = {"UNTREATED": RV.UNTREATED, "MAN. TREATMENT": RV.MANUAL, "MECH. TREATMENT": RV.MECHANICAL, "REFERENCE": REF_PLOTS}
PLOT_TYPES = {"UNTREATED": RV.UNTREATED, "TREATED - MANUAL": RV.MANUAL, "TREATED - MECHANICAL": RV.MECHANICAL,
              "TREATED - PLANTED": RV.PLANTED, "REFERENCE": REF_PLOTS}


@dataclass(frozen=True)
class Param:
    name: str
    value: float
    lo: float | None
    hi: float | None
    kind: str          # "estimated", "fixed assumption", "estimated from reference plots", "shared from untreated fit", "external model coefficient"
    source: str
    unit: str = ""


@dataclass(frozen=True)
class Curve:
    key: str
    label: str
    role: str
    x: tuple
    y: tuple
    lo: tuple
    hi: tuple
    equation: str
    params: tuple
    interval: str
    excludes: str
    n_plots: int
    n_obs: int
    summary: str
    diagnostics: tuple = ()           # (name, value) pairs


@dataclass(frozen=True)
class Observed:
    key: str
    label: str
    x: tuple
    mean: tuple
    lo: tuple
    hi: tuple
    n: tuple
    dates: str
    source: str


@dataclass
class TrajectoryPanel:
    key: str
    title: str
    unit: str
    quantity: str
    observed: list = field(default_factory=list)
    curves: list = field(default_factory=list)
    note: str = ""
    checks: list = field(default_factory=list)
    unavailable: list = field(default_factory=list)   # (series, reason)


@dataclass
class Trajectories:
    cell: str
    oiling: str
    panels: list = field(default_factory=list)
    unavailable: str = ""

    def panel(self, key: str) -> TrajectoryPanel:
        return next(p for p in self.panels if p.key == key)


def decimal_year(ts) -> float:
    ts = pd.Timestamp(ts)
    start, end = pd.Timestamp(year=ts.year, month=1, day=1), pd.Timestamp(year=ts.year + 1, month=1, day=1)
    return ts.year + (ts - start) / (end - start)


def _t90(values: np.ndarray, lo_cap: float | None = None, hi_cap: float | None = None) -> tuple:
    v = np.asarray(values, float)
    m = float(v.mean())
    h = float(stats.t.ppf(0.95, len(v) - 1)) * float(v.std(ddof=1)) / math.sqrt(len(v)) if len(v) > 1 else float("nan")
    lo, hi = m - h, m + h
    return m, (max(lo_cap, lo) if lo_cap is not None else lo), (min(hi_cap, hi) if hi_cap is not None else hi)


def _pct(a: np.ndarray, axis=0) -> tuple:
    return np.percentile(a, 5, axis=axis), np.percentile(a, 95, axis=axis)


def _fit(resid, x0, lb, ub, jac) -> np.ndarray | None:
    r = least_squares(resid, x0, jac=jac, bounds=(lb, ub))
    return r.x if r.success else None


def _resampler(d: pd.DataFrame):
    """Cluster bootstrap: whole plots drawn with replacement; a plot drawn twice becomes two plots."""
    rows = list(d.groupby("pid", sort=True).indices.values())
    cols = {c: d[c].to_numpy() for c in d.columns if c != "pid"}

    def draw(rng) -> pd.DataFrame:
        pick = rng.integers(0, len(rows), size=len(rows))
        idx = np.concatenate([rows[i] for i in pick])
        return pd.DataFrame({**{c: v[idx] for c, v in cols.items()}, "pid": np.repeat(np.arange(len(pick)), [len(rows[i]) for i in pick])})
    return draw


# ---------------------------------------------------------------------------------------------------------------
# Shoreline retreat: cumulative landward movement of the marsh edge since 4 December 2010 (m; negative = advance)

def _m0(th, t):
    return th[0] * t


def _m1(th, t):
    return th[0] * t + th[1] * (1.0 - np.exp(-t / th[2]))


def _m0_jac(th, t, t0):
    return (t - t0)[:, None]


def _m1_jac(th, t, t0):
    et, e0 = np.exp(-t / th[2]), np.exp(-t0 / th[2])
    return np.column_stack([t - t0, e0 - et, th[1] * (t0 * e0 - t * et) / th[2] ** 2])


JACOBIANS = {"M0": _m0_jac, "M1": _m1_jac}
RETREAT_MODELS = {"M0": (_m0, [1.0], [-10.0], [10.0]), "M1": (_m1, [1.0, 1.0, 1.0], [-10.0, -20.0, 0.05], [10.0, 20.0, 10.0])}
RETREAT_EQ = {"M0": "R(t) = b t   (constant rate; the DSAS linear-regression-rate form)",
              "M1": "R(t) = b t + A (1 - exp(-t / tau))   (rate b + (A / tau) exp(-t / tau): an excess that fades)"}


@lru_cache(maxsize=1)
def field_positions() -> pd.DataFrame:
    """Plot-level retreat since each plot's first survey on or after ORIGIN. Columns plot, key, date, t, t0, inc (m)."""
    book = pd.read_excel(te.EROSION_DATA, sheet_name=["GIS field erosion points", "GIS field erosion"])
    pts, rates = book["GIS field erosion points"], book["GIS field erosion"]
    types = rates.assign(pid=rates.PLOT_ID.astype(str).str.replace(" ", ""))[["pid", "PLOT_TYPE"]].drop_duplicates()
    d = pts.assign(pid=pts.PLOT_ID.astype(str).str.replace(" ", ""), side=pts.GPS_POINT_ID.str.rsplit("_", n=1).str[-1],
                   date=pd.to_datetime(pts.GPS_DATE)).merge(types, on="pid", how="left")
    if d.PLOT_TYPE.isna().any():
        raise ValueError(f"Field positions without a plot type: {sorted(d[d.PLOT_TYPE.isna()].pid.unique())}")
    d["key"] = d.PLOT_TYPE.str.strip().map(FIELD_TYPES)
    d = d[d.date >= ORIGIN]
    # duplicate readings of one transect on one date are averaged (a few transects were re-staked)
    d = d.groupby(["pid", "key", "side", "date"], as_index=False).DIST_TRANSECT.mean()
    first = d.sort_values("date").groupby(["pid", "side"]).first()[["DIST_TRANSECT", "date"]].rename(columns={"DIST_TRANSECT": "d0", "date": "date0"})
    d = d.join(first, on=["pid", "side"])
    d["inc"] = d.d0 - d.DIST_TRANSECT                          # distance to the back stake shrinks as the edge retreats
    o = decimal_year(ORIGIN)
    d["t"] = d.date.map(decimal_year) - o
    d["t0"] = d.date0.map(decimal_year) - o
    return d.groupby(["pid", "key", "date", "t", "t0"], as_index=False).inc.mean()


def _retreat_fit(d: pd.DataFrame, name: str) -> np.ndarray | None:
    f, x0, lb, ub = RETREAT_MODELS[name]
    t, t0, y = d.t.values, d.t0.values, d.inc.values
    return _fit(lambda th: (f(th, t) - f(th, t0)) - y, x0, lb, ub, lambda th: JACOBIANS[name](th, t, t0))


def _lopo_rmse(d: pd.DataFrame, fit, predict) -> float:
    err = []
    for p in d.pid.unique():
        th = fit(d[d.pid != p])
        if th is None:
            raise RuntimeError(f"Leave-one-plot-out fit did not converge (plot {p})")
        held = d[d.pid == p]
        err.extend(predict(th, held))
    return float(np.sqrt(np.mean(np.square(err))))


def _retreat_lopo(d: pd.DataFrame, name: str) -> float:
    f = RETREAT_MODELS[name][0]
    return _lopo_rmse(d, lambda tr: _retreat_fit(tr, name), lambda th, h: (f(th, h.t.values) - f(th, h.t0.values)) - h.inc.values)


def _retreat_curve(d: pd.DataFrame, key: str, rng) -> Curve:
    rmse = {m: _retreat_lopo(d, m) for m in RETREAT_MODELS}
    name = "M1" if rmse["M1"] < rmse["M0"] else "M0"
    f = RETREAT_MODELS[name][0]
    th = _retreat_fit(d, name)
    if th is None:
        raise RuntimeError(f"Retreat fit did not converge for {key}")
    o, last = decimal_year(ORIGIN), float(d.t.max())
    tg = np.linspace(0.0, last, 90)
    draws, curves, failed = [], [], 0
    boot_d = _resampler(d)
    for _ in range(N_BOOT):
        b = _retreat_fit(boot_d(rng), name)
        if b is None:
            failed += 1
            continue
        draws.append(b)
        curves.append(f(b, tg))
    draws, curves = np.array(draws), np.array(curves)
    lo, hi = _pct(curves)
    names = {"M0": [("b, long-run rate", "m/yr")], "M1": [("b, long-run rate", "m/yr"), ("A, excess retreat", "m"), ("tau, excess time constant", "yr")]}[name]
    plo, phi = _pct(draws)
    params = tuple(Param(n, float(v), float(a), float(c), "estimated", "Zengel et al. 2022 GRIIDC field positions (this group's plots)", u)
                   for (n, u), v, a, c in zip(names, th, plo, phi))
    at_bound = int(np.sum(np.isclose(draws[:, 2], RETREAT_MODELS["M1"][3][2]) | np.isclose(draws[:, 2], RETREAT_MODELS["M1"][2][2]))) if name == "M1" else 0
    n_plots = d.pid.nunique()
    if name == "M1":
        summary = (f"{RV.LABELS[key]}: long-run rate {th[0]:.2f} m/yr (90% {plo[0]:.2f} to {phi[0]:.2f}) plus a fading excess of "
                   f"{th[1]:.1f} m (90% {plo[1]:.1f} to {phi[1]:.1f}), time constant {th[2]:.1f} years; {last:.1f} years of surveys.")
    else:
        summary = f"{RV.LABELS[key]}: constant rate {th[0]:.2f} m/yr (90% {plo[0]:.2f} to {phi[0]:.2f}); a fading excess term did not improve held-out fit."
    return Curve(key, RV.LABELS[key], FIT, tuple(o + tg), tuple(f(th, tg)), tuple(lo), tuple(hi), RETREAT_EQ[name], params,
                 f"90% plot-resampling bootstrap interval of the group-mean curve ({len(draws)} of {N_BOOT} refits converged)",
                 "between-year weather (for example the 2016 rise shared with the reference plots), choice of model form, GPS and staking "
                 "error, and the spread of single plots (not a prediction interval for a new plot)",
                 n_plots, len(d), summary,
                 (("model chosen", name), ("leave-one-plot-out RMSE, constant rate (m)", round(rmse["M0"], 3)),
                  ("leave-one-plot-out RMSE, fading excess (m)", round(rmse["M1"], 3)), ("bootstrap refits with tau at a bound", at_bound),
                  ("bootstrap refits not converged", failed)))


def retreat_panel(rng) -> TrajectoryPanel:
    p = TrajectoryPanel("retreat", "Shoreline retreat", "m", "cumulative marsh-edge retreat since 4 December 2010",
                        note=("Cumulative retreat is the integral of the erosion rate, so the slope of each curve is the rate. Retreat before the "
                              "first survey (oiling began in mid-2010) is not included, and the date of the largest excess is not identified: "
                              "the fading-excess form puts it at the first survey by construction."))
    d = field_positions()
    for key in (RV.UNTREATED, RV.MANUAL, REF_PLOTS):
        g = d[(d.key == key) & np.isclose(d.t0, 0.0)]
        rows = [(decimal_year(dt),) + _t90(v.inc.values) + (len(v),) for dt, v in g.groupby("date")]
        x, m, lo, hi, n = map(tuple, zip(*rows))
        p.observed.append(Observed(key, RV.LABELS[key], x, m, lo, hi, n, "Field surveys 4 Dec 2010 to 5 Oct 2016 (exact GPS dates)",
                                   "Zengel et al. 2022, GRIIDC doi:10.7266/VF524143, sheet GIS field erosion points (mean of two transects per plot)"))
        p.curves.append(_retreat_curve(g, key, rng))
    mech = d[d.key == RV.MECHANICAL]
    early = mech[mech.t0 < 1.5].pid.nunique()
    p.unavailable = [(RV.LABELS[RV.MECHANICAL], f"{early} plots surveyed from 13 Nov 2011 (after mechanical treatment in May-June 2011) and "
                      f"{mech.pid.nunique() - early} more only from 2014: no December 2010 origin and too few plots for a plot-resampling band. "
                      "Aerial period rates for mechanical plots remain in the recovery view"),
                     (RV.LABELS[RV.PLANTED], "the source has no field (GPS) shoreline positions for planted plots; aerial period rates only")]
    p.checks = [("Zengel et al. (2022) report 147 to 198% greater field erosion on oiled than reference plots over 2010-2012. Observed here to "
                 "17 Sep 2012: " + ", ".join(f"{o.label.lower()} {o.mean[2]:.1f} m" for o in p.observed) + ".")]
    return p


# ---------------------------------------------------------------------------------------------------------------
# Total vegetation cover (%): logistic recovery toward the mean cover of the reference plots

VEG_EQ = "C(t) = K / (1 + exp(-r (t - t50))),  K = mean total cover of the reference plots, 2011-2016"


@lru_cache(maxsize=1)
def vegetation_plots() -> pd.DataFrame:
    """Plot-year total cover of the Bay Jimmy plots (source "Zengel (B)") with the plot types of the erosion workbook."""
    v = pd.read_excel(VEG_DATA, sheet_name="Dataset", na_values=["NA"])
    v = v[v.Source == "Zengel (B)"].assign(pid=lambda x: x["Site ID"].astype(str).str.replace(" ", ""))
    types = pd.read_excel(te.EROSION_DATA, sheet_name="DSAS lumped")[["PLOT_ID", "PLOT_TYPE"]].drop_duplicates()
    types = types.assign(pid=types.PLOT_ID.astype(str).str.replace(" ", ""), key=types.PLOT_TYPE.str.strip().map(PLOT_TYPES))
    v = v.merge(types[["pid", "key"]], on="pid", how="left")
    if v.key.isna().any():
        raise ValueError(f"Vegetation plots without a plot type: {sorted(v[v.key.isna()].pid.unique())}")
    v = v.dropna(subset=["TotalCover"])
    return v.assign(x=v.Year + VEG_X, cover=v.TotalCover.astype(float))[["pid", "key", "Year", "x", "cover"]].reset_index(drop=True)


def _logistic(x, r, t50, k):
    return k / (1.0 + np.exp(-r * (x - t50)))


def _logistic_jac(x, r, t50, k):
    s = 1.0 / (1.0 + np.exp(-r * (x - t50)))
    g = k * s * (1.0 - s)
    return np.column_stack([g * (x - t50), -g * r])


def _veg_fit(d: pd.DataFrame, k: float, r: float | None = None) -> np.ndarray | None:
    x, y = d.x.values, d.cover.values
    if r is None:
        return _fit(lambda th: _logistic(x, th[0], th[1], k) - y, [1.0, 2013.5], [0.05, 2009.0], [10.0, 2025.0],
                    lambda th: _logistic_jac(x, th[0], th[1], k))
    th = _fit(lambda th: _logistic(x, r, th[0], k) - y, [2013.5], [2009.0], [2025.0], lambda th: _logistic_jac(x, r, th[0], k)[:, 1:])
    return None if th is None else np.array([r, th[0]])


def vegetation_panel(rng) -> TrajectoryPanel:
    p = TrajectoryPanel("cover", "Total vegetation cover", "%", "total vegetation cover (all species), plot visual estimate",
                        note=("Total cover of all species, not Spartina cover. Curves are bounded between 0 and the reference cover K. The 2016 "
                              "drop also appears on the reference plots and is not captured by a monotone curve."))
    v = vegetation_plots()
    ref = v[v.key == REF_PLOTS]
    k = float(ref.cover.mean())
    for key in (RV.UNTREATED, RV.MANUAL, RV.MECHANICAL, REF_PLOTS):
        g = v[v.key == key]
        rows = [(x,) + _t90(s.cover.values, 0.0, 100.0) + (len(s),) for x, s in g.groupby("x")]
        x, m, lo, hi, n = map(tuple, zip(*rows))
        p.observed.append(Observed(key, RV.LABELS[key], x, m, lo, hi, n, f"Surveys {int(g.Year.min())} to {int(g.Year.max())} (September; 2013-2016 month assumed)",
                                   "GRIIDC doi:10.7266/n7-cn03-z792, source Zengel (B) (Zengel et al. 2015 plots and later surveys)"))
    groups = {key: v[v.key == key] for key in (RV.UNTREATED, RV.MECHANICAL, RV.MANUAL)}
    fits = {key: _veg_fit(groups[key], k) for key in (RV.UNTREATED, RV.MECHANICAL)}
    if any(f is None for f in fits.values()):
        raise RuntimeError("Vegetation fit did not converge")
    fits[RV.MANUAL] = _veg_fit(groups[RV.MANUAL], k, r=fits[RV.UNTREATED][0])
    if fits[RV.MANUAL] is None:
        raise RuntimeError("Vegetation fit did not converge")
    boot = {key: [] for key in fits}
    ks, failed = [], 0
    draw = {key: _resampler(g) for key, g in {**groups, REF_PLOTS: ref}.items()}
    for _ in range(N_BOOT):
        kb = float(draw[REF_PLOTS](rng).cover.mean())
        u = _veg_fit(draw[RV.UNTREATED](rng), kb)
        mech = _veg_fit(draw[RV.MECHANICAL](rng), kb)
        man = _veg_fit(draw[RV.MANUAL](rng), kb, r=u[0]) if u is not None else None
        if u is None or mech is None or man is None:
            failed += 1
            continue
        ks.append(kb)
        for key, th in ((RV.UNTREATED, u), (RV.MECHANICAL, mech), (RV.MANUAL, man)):
            boot[key].append((th[0], th[1], kb))
    end = float(groups[RV.UNTREATED].x.max())
    k_lo, k_hi = _pct(np.array(ks))
    k_param = Param("K, reference cover", k, float(k_lo), float(k_hi), "estimated from reference plots",
                    "Reference plots 24-28, 2011-2016 (same source)", "%")
    for key in (RV.UNTREATED, RV.MECHANICAL, RV.MANUAL):
        g, th, b = groups[key], fits[key], np.array(boot[key])
        x0 = float(g.x.min())
        x1 = end if key == RV.MANUAL else float(g.x.max())
        xg = np.linspace(x0, x1, 80)
        curves = np.array([_logistic(xg, r, t50, kb) for r, t50, kb in b])
        lo, hi = _pct(curves)
        plo, phi = _pct(b[:, :2])
        y = _logistic(xg, th[0], th[1], k)
        lopo = _lopo_rmse(g, lambda tr: _veg_fit(tr, k) if key != RV.MANUAL else _veg_fit(tr, k, r=th[0]),
                          lambda t_, h: _logistic(h.x.values, t_[0], t_[1], k) - h.cover.values)
        const = _lopo_rmse(g, lambda tr: np.array([tr.cover.mean()]), lambda t_, h: t_[0] - h.cover.values)
        resid = g.assign(r=_logistic(g.x.values, th[0], th[1], k) - g.cover.values).groupby("Year").r.mean().round(1)
        if key == RV.MANUAL:
            r_param = Param("r, recovery rate", float(th[0]), float(plo[0]), float(phi[0]), "shared from untreated fit",
                            "Untreated plots (manual plots were surveyed only in 2011 and 2012)", "per yr")
            role, label = CONDITIONAL, RV.LABELS[key] + " (shared untreated rate)"
            summary = (f"{label}: half of reference cover reached about {th[1]:.1f} (90% {plo[1]:.1f} to {phi[1]:.1f}) IF the manual plots "
                       f"followed the untreated recovery rate after 2012; only the 2011-2012 surveys are observed.")
            interval = "90% bootstrap interval resampling untreated, manual and reference plots jointly; conditional on the shared rate"
        else:
            r_param = Param("r, recovery rate", float(th[0]), float(plo[0]), float(phi[0]), "estimated", "This group's plots", "per yr")
            role, label = FIT, RV.LABELS[key]
            summary = (f"{label}: half of reference cover reached about {th[1]:.1f} (90% {plo[1]:.1f} to {phi[1]:.1f}); "
                       f"rate {th[0]:.2f} per year (90% {plo[0]:.2f} to {phi[0]:.2f}).")
            interval = "90% plot-resampling bootstrap interval of the group-mean curve (group and reference plots resampled)"
        params = (r_param, Param("t50, year of half reference cover", float(th[1]), float(plo[1]), float(phi[1]),
                                 "estimated (given the shared rate)" if key == RV.MANUAL else "estimated", "This group's plots", "year"), k_param)
        p.curves.append(Curve(key, label, role, tuple(xg), tuple(y), tuple(lo), tuple(hi), VEG_EQ, params, interval,
                              "between-year variation (the 2016 drop), choice of a logistic form, visual cover-estimation error, the spread of "
                              "single plots" + (", and any difference between the manual and untreated rates after 2012" if key == RV.MANUAL else ""),
                              g.pid.nunique(), len(g), summary,
                              (("leave-one-plot-out RMSE, logistic (cover %)", round(lopo, 1)), ("leave-one-plot-out RMSE, no-trend mean (cover %)", round(const, 1)),
                               ("mean residual by survey year (fit minus observed)", "; ".join(f"{yr}: {r:+.1f}" for yr, r in resid.items())),
                               ("bootstrap refits not converged", failed))))
    mech_plots = groups[RV.MECHANICAL].groupby("pid").Year.min()
    unt_last = groups[RV.UNTREATED].groupby("pid").Year.max()
    p.checks = ["Plot means for 2011 and 2012 equal the Zengel et al. (2015) S1 Table group means (checked in the tests).",
                f"Untreated plots: {len(unt_last)} surveyed in 2011-2012, {int((unt_last >= 2016).sum())} of them followed to 2016; "
                "later means are of the smaller set.",
                f"Mechanical plots change between years: {int((mech_plots <= 2011).sum())} plots from 2011 (one followed to 2016) and "
                f"{int((mech_plots >= 2013).sum())} more from 2013; the fit treats them as one population."]
    p.unavailable = [(RV.LABELS[RV.PLANTED], "no plot-level total cover for planted plots; Zengel et al. (2015) report Spartina cover only (July 2012)")]
    return p


# ---------------------------------------------------------------------------------------------------------------
# Soil tPAH (mg/kg): conditional first-order scenario with the DIVER heavy-class rate

PAH_EQ = "C(t) = C_a exp(-k (t - t_a)),  C_a = first-survey group mean, k = DIVER heavy-class decline rate of the PAH sum"


def heavy_class_rate() -> tuple:
    d = pd.read_csv(PAH_CLASS_TABLE)
    r = d[(d.outcome == "PAH sum") & (d.stratum_type == "oiling_class") & (d.stratum == "heavy")].iloc[0]
    return float(r.k_per_year), float(r.k_lo90), float(r.k_hi90)


def pah_panel(rng) -> TrajectoryPanel:
    p = TrajectoryPanel("tpah", "Soil tPAH", "mg/kg", "total PAH in subsurface soil cores (0-10 cm, surface oil scraped aside)",
                        note=("All curves are conditional: the treatment plots have one or two samples, so their own decline rate is not "
                              "identified. The borrowed rate is for the DIVER PAH sum (mostly 0-2 cm grabs, 58 compounds) in heavily oiled marsh "
                              "across the northern Gulf, with no treatment variable; the plots' tPAH is 43 to 45 compounds in 0-10 cm cores. "
                              "The class rate is the decline of the PAH sum, which includes physical removal and dilution; the PAH/hopane ratio did not "
                              "decline, so the rate is not evidence of biodegradation."))
    k, k_lo, k_hi = heavy_class_rate()
    sd = (k_hi - k_lo) / (2 * Z90)
    support = RV._pah_support("Heavy")
    if support is None:
        p.unavailable = [("All groups", "DIVER campaign table missing: the support period of the decline rate is unknown")]
        return p
    end = RV.SPILL_YEAR + support[1]
    raw = te.load()
    kdraw = rng.normal(k, sd, N_MC)
    k_param = Param("k, decline rate", k, k_lo, k_hi, "external model coefficient",
                    "pah_decline_v1 heavy class (results/pah_decline/by_oiling_class.csv); DIVER, 36 stations with 2+ campaigns", "per yr")
    for name, key in RV.FIELD_NAMES.items():
        r = raw[(raw.study == "main") & (raw.metric == "tPAH (mg/kg)") & (raw.treatment == name)].dropna(subset=["mean"]).sort_values("year")
        if r.empty:
            continue
        xs, ms, los, his, ns = [], [], [], [], []
        for _, q in r.iterrows():
            lo, hi = RV._t90(float(q["mean"]), float(q.se), int(q.n))
            xs.append(PAH_X[int(q.year)]); ms.append(float(q["mean"])); los.append(lo); his.append(hi); ns.append(int(q.n))
        p.observed.append(Observed(key, RV.LABELS[key], tuple(xs), tuple(ms), tuple(los), tuple(his), tuple(ns),
                                   "Cores July-August 2011 and September 2012", "zengel2015_group_means.csv (Zengel et al. 2015, S1 Table)"))
        a = r.iloc[0]
        mean, se, xa = float(a["mean"]), float(a.se), PAH_X[int(a.year)]
        s2 = math.log(1.0 + (se / mean) ** 2)
        anchor = rng.lognormal(math.log(mean) - s2 / 2, math.sqrt(s2), N_MC)
        xg = np.linspace(xa, end, 60)
        draws = anchor[:, None] * np.exp(-kdraw[:, None] * (xg[None, :] - xa))
        lo, hi = _pct(draws)
        y = mean * np.exp(-k * (xg - xa))
        check = ""
        if len(r) > 1:
            later = r.iloc[1]
            xb = PAH_X[int(later.year)]
            at = anchor * np.exp(-kdraw * (xb - xa))
            blo, bhi = np.percentile(at, [5, 95])
            inside = blo <= float(later["mean"]) <= bhi
            check = (f"{RV.LABELS[key]}: observed {int(later.year)} mean {float(later['mean']):.0f} mg/kg is "
                     f"{'inside' if inside else 'outside'} the scenario's 90% range {blo:.0f} to {bhi:.0f} (not fitted; a weak check).")
            p.checks.append(check)
        p.curves.append(Curve(key, RV.LABELS[key] + " (shared class rate)", CONDITIONAL, tuple(xg), tuple(y), tuple(lo), tuple(hi), PAH_EQ,
                              (Param("C_a, first-survey mean", mean, *RV._t90(mean, se, int(a.n)), "estimated",
                                     f"Zengel et al. 2015 S1 Table, {int(a.year)} ({int(a.n)} plots)", "mg/kg"), k_param),
                              f"90% Monte Carlo range: first-survey mean (lognormal with its standard error) times the class rate (normal, from its 90% interval)",
                              "any treatment-specific rate, the depth and analyte mismatch, plot-to-plot spread, and decline before the first sample",
                              int(a.n), len(r), f"{RV.LABELS[key]}: {mean:.0f} mg/kg in {int(a.year)} declining at the shared class rate "
                              f"({k:.2f} per year, half-life {math.log(2) / k:.1f} years) to {y[-1]:.0f} mg/kg by the end of the DIVER campaigns ({end:.1f}).",
                              (("anchor date", round(xa, 2)), ("end of decline-rate support", round(end, 2)))))
    p.unavailable = [(RV.LABELS[RV.PLANTED], "no tPAH for planted plots"),
                     ("Treatment-specific decline rates", "PAH on treated and untreated plots at three or more dates, or a PAH model with a treatment variable")]
    return p


@lru_cache(maxsize=1)
def _heavy_panels() -> tuple:
    rng = np.random.default_rng(SEED)
    return (retreat_panel(rng), vegetation_panel(rng), pah_panel(rng))


def build(site_row: dict | None) -> Trajectories | None:
    """Trajectories for ONE in-scope mapped marsh cell, or None. Fitted to the heavily oiled Bay Jimmy plots only: other oiling classes
    get an explicit unavailable note rather than a borrowed curve."""
    if not site_row or site_row.get("status") != "in_scope":
        return None
    oiling = str(site_row.get("max_oiling", ""))
    out = Trajectories(str(site_row.get("cell", "")), oiling)
    if oiling != "Heavy":
        out.unavailable = (f"Continuous trajectories are fitted to heavily oiled Bay Jimmy plots only; none is shown for {oiling or 'unknown'} oiling, "
                           "because the plots' recovery is not evidence for other oiling classes.")
        return out
    out.panels = list(_heavy_panels())
    return out


def _num(v: float) -> str:
    return f"{v:.1f}" if abs(v) >= 1000 else f"{v:.3g}"


def parameter_frame(tr: Trajectories) -> pd.DataFrame:
    rows = []
    for p in tr.panels:
        for c in p.curves:
            for q in c.params:
                rows.append({"Outcome": p.title, "Series": c.label, "Role": ROLE_TEXT[c.role], "Parameter": q.name,
                             "Value": round(q.value, 3), "90% interval": "" if q.lo is None else f"{_num(q.lo)} to {_num(q.hi)}",
                             "Unit": q.unit, "Type": q.kind, "Source": q.source})
    return pd.DataFrame(rows)


def diagnostics_frame(tr: Trajectories) -> pd.DataFrame:
    return pd.DataFrame([{"Outcome": p.title, "Series": c.label, "Equation": c.equation, "Plots": c.n_plots, "Plot-dates": c.n_obs,
                          "Diagnostic": n, "Value": str(v)} for p in tr.panels for c in p.curves for n, v in c.diagnostics])
