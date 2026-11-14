"""Sand-beach (ESI 3A) persistence of visible oil, Deepwater Horizon SCAT (D39; plan docs/V5_BEACH_SAND_PLAN.md).

What it predicts: for a sand-beach segment first seen oiled, the probability that visible oil is still recorded
(no "No Oil Observed" survey yet) 90, 180, 365 and 730 days after that first oiled survey.

What it is NOT: natural recovery (most oiled beach was treated, and treatment is not in the data), chemical or
ecological recovery, or buried oil. It cannot rank treatments.

Two layers in this file:
1. The statistics shared with validation/v5_beach_sand.py: the design matrix, a piecewise-exponential
   proportional-hazards model fitted to interval-censored times, and the Turnbull estimator (the
   Kaplan-Meier-type curve for interval-censored data) used as the baseline.
2. Packaged use: `persistence_curve(site)` reads models/beach_sand_persistence_v1.json and returns the median
   and 90% interval at the four horizons, scope flags and a one-line explanation; `BeachSandPersistenceAdapter`
   wraps it behind the standard interface in model_interface.py.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np

from . import model_interface as mi
from .model_interface import (Prediction, ScenarioRequest, SiteRecord, SCOPE_IN_RANGE, SCOPE_NEW_REGION,
                              SCOPE_OUTSIDE, STATE_EXPERIMENTAL)

ROOT = Path(__file__).resolve().parents[2]
CARD_PATH = ROOT / "models" / "beach_sand_persistence_v1.json"

HORIZONS = (90, 180, 365, 730)
CUTS = np.array([0.0, 30.0, 90.0, 180.0, 365.0, 730.0])  # piece starts (days); last piece is open-ended
CAT_LEVELS = ("surface_light", "surface_mod_heavy", "tb_neg_light", "tb_mod_heavy")  # first = reference
CAT_OF_CODE = {"Neg_TB": "tb_neg_light", "Light_TB": "tb_neg_light", "Mod_TB": "tb_mod_heavy",
               "Heavy_TB": "tb_mod_heavy", "Very_Light": "surface_light", "Light": "surface_light",
               "Moderate": "surface_mod_heavy", "Heavy": "surface_mod_heavy"}
CONT = ("sodistro", "log_tb", "log_days", "exposure")
TERMS = ("cat_surface_mod_heavy", "cat_tb_neg_light", "cat_tb_mod_heavy", "tz_SU", "tz_MI_LI",
         "thick_thick", "thick_thin") + CONT
TRAINED_STATES = ("AL", "MS", "FL")
RIDGE = 0.01  # ASSUMED, numerical stability only


# ---------------------------------------------------------------------------------------------------------------
# Design matrix

def raw_terms(rows) -> np.ndarray:
    """rows: iterable of dicts with keys first_cat_group, first_tidal_zone, first_thickness,
    first_sodistro_pct, first_tb_count, days_spill_to_first_oiled, exposure_open_frac. Unstandardised."""
    out = []
    for r in rows:
        cat = r["first_cat_group"]
        tz = r.get("first_tidal_zone") or "UI"
        th = r.get("first_thickness") or "none"
        out.append([cat == "surface_mod_heavy", cat == "tb_neg_light", cat == "tb_mod_heavy",
                    tz == "SU", tz in ("MI", "LI"), th == "thick", th == "thin",
                    float(r.get("first_sodistro_pct") or 0.0) / 100.0,
                    math.log1p(float(r.get("first_tb_count") or 0.0)),
                    math.log(max(float(r["days_spill_to_first_oiled"]), 1.0)),
                    float(r.get("exposure_open_frac") if r.get("exposure_open_frac") is not None else 1.0)])
    return np.asarray(out, dtype=float)


def standardise(X: np.ndarray, mean=None, sd=None):
    X = X.copy()
    k = len(TERMS) - len(CONT)
    if mean is None:
        mean = X[:, k:].mean(axis=0)
        sd = X[:, k:].std(axis=0)
        sd = np.where(sd > 0, sd, 1.0)
    X[:, k:] = (X[:, k:] - mean) / sd
    return X, np.asarray(mean), np.asarray(sd)


# ---------------------------------------------------------------------------------------------------------------
# Piecewise-exponential proportional hazards with interval censoring

def exposure(t) -> np.ndarray:
    """Time spent in each hazard piece up to t (t may be inf). Shape (n, n_pieces)."""
    t = np.atleast_1d(np.asarray(t, dtype=float))
    ends = np.append(CUTS[1:], np.inf)
    return np.clip(t[:, None] - CUTS[None, :], 0.0, ends - CUTS)


def _nll(theta, X, EL, ER, interval):
    p = len(CUTS)
    a, b = theta[:p], theta[p:]
    eta = np.exp(np.clip(X @ b, -30, 30))
    lam = np.exp(a)
    HL = eta * (EL @ lam)
    D = eta * (ER @ lam) - HL  # only used where interval
    ll = -HL.copy()
    gHL_a = eta[:, None] * EL * lam[None, :]
    # contributions
    gb = -(HL[:, None] * X)
    ga = -gHL_a
    if interval.any():
        Di = np.maximum(D[interval], 1e-12)
        w = np.exp(-Di) / (-np.expm1(-Di))  # e^-D / (1 - e^-D)
        ll[interval] += np.log(-np.expm1(-Di))
        dD_a = eta[interval, None] * (ER[interval] - EL[interval]) * lam[None, :]
        ga[interval] += w[:, None] * dD_a
        gb[interval] += (w * Di)[:, None] * X[interval]
    nll = -ll.sum() + RIDGE * (b @ b)
    grad = np.concatenate([-ga.sum(axis=0), -gb.sum(axis=0) + 2 * RIDGE * b])
    return nll, grad


def fit_pe(X: np.ndarray, L: np.ndarray, R: np.ndarray, theta0=None) -> np.ndarray:
    """Fit; L, R in days (R = inf for right-censored). Returns theta = [alpha (6), beta (n_terms)]."""
    from scipy.optimize import minimize
    interval = np.isfinite(R)
    EL, ER = exposure(L), exposure(np.where(interval, R, 0.0))
    if theta0 is None:
        theta0 = np.concatenate([np.full(len(CUTS), math.log(1 / 200.0)), np.zeros(X.shape[1])])
    res = minimize(_nll, theta0, args=(X, EL, ER, interval), jac=True, method="L-BFGS-B",
                   options={"maxiter": 2000, "gtol": 1e-7})
    return res.x


def surv_pe(theta, X, times=HORIZONS) -> np.ndarray:
    """S(t|x), shape (n, len(times))."""
    p = len(CUTS)
    eta = np.exp(np.clip(X @ theta[p:], -30, 30))
    H0 = exposure(np.asarray(times, dtype=float)) @ np.exp(theta[:p])
    return np.exp(-eta[:, None] * H0[None, :])


# ---------------------------------------------------------------------------------------------------------------
# Turnbull estimator (Kaplan-Meier-type curve for interval-censored data)

def turnbull(L, R, tol=1e-9, max_iter=10000):
    """Self-consistency EM on the grid of observed endpoints. Returns (grid, p): mass p_j on (grid[j], grid[j+1]],
    last interval (grid[-1], inf)."""
    L = np.asarray(L, float)
    R = np.asarray(R, float)
    grid = np.unique(np.concatenate([[0.0], L, R[np.isfinite(R)]]))
    lo = grid
    hi = np.append(grid[1:], np.inf)
    A = (L[:, None] <= lo[None, :]) & (hi[None, :] <= np.where(np.isfinite(R), R, np.inf)[:, None])
    A = A.astype(float)
    keep = A.sum(axis=0) > 0
    A, lo, hi = A[:, keep], lo[keep], hi[keep]
    p = np.full(A.shape[1], 1.0 / A.shape[1])
    for _ in range(max_iter):
        denom = A @ p
        new = p * (A / denom[:, None]).mean(axis=0)
        if np.abs(new - p).max() < tol:
            p = new
            break
        p = new
    return np.column_stack([lo, hi]), p


def turnbull_surv(fit, times=HORIZONS) -> np.ndarray:
    """S(t) with mass spread uniformly inside each finite interval; mass beyond the last point stays above t."""
    iv, p = fit
    out = []
    for t in times:
        s = 0.0
        for (a, b), m in zip(iv, p):
            if a >= t:
                s += m
            elif np.isfinite(b) and b > t:
                s += m * (b - t) / (b - a)
            elif not np.isfinite(b):
                s += m
        out.append(min(1.0, max(0.0, s)))
    return np.array(out)


# ---------------------------------------------------------------------------------------------------------------
# Packaged use

@lru_cache(maxsize=4)
def load_card(path: str | None = None) -> dict:
    with open(path or CARD_PATH) as f:
        return json.load(f)


def _site_row(site: dict) -> dict:
    """Accept either the predictor names of beach_series.csv or a raw SCAT category code."""
    row = dict(site)
    if "first_cat_group" not in row:
        code = row.get("first_cat") or row.get("oiling_category")
        if code not in CAT_OF_CODE:
            raise ValueError(f"unknown first oiling category {code!r}; expected one of {sorted(CAT_OF_CODE)}")
        row["first_cat_group"] = CAT_OF_CODE[code]
    if row["first_cat_group"] not in CAT_LEVELS:
        raise ValueError(f"unknown category group {row['first_cat_group']!r}")
    if "days_spill_to_first_oiled" not in row:
        raise ValueError("days_spill_to_first_oiled is required (days from 20 April 2010 to first oiled survey)")
    return row


def scope_flags(row: dict, card: dict) -> list:
    flags = []
    esi = str(row.get("esi", "3A")).upper()
    if esi != "3A":
        flags.append(f"ESI not 3A (got {esi}): the model was trained on fine-to-medium sand beaches only")
    state = row.get("state")
    if state is not None and state not in card["training_range"]["states"]:
        flags.append(f"state unseen ({state}): trained on Alabama, Mississippi and Florida (one spill)")
    rng = card["training_range"]["continuous"]
    vals = {"days_spill_to_first_oiled": row["days_spill_to_first_oiled"],
            "first_sodistro_pct": row.get("first_sodistro_pct") or 0.0,
            "first_tb_count": row.get("first_tb_count") or 0.0,
            "exposure_open_frac": row.get("exposure_open_frac", 1.0)}
    for k, v in vals.items():
        lo, hi = rng[k]
        if v is not None and not (lo <= float(v) <= hi):
            flags.append(f"outside training range: {k}={v} (trained {lo} to {hi})")
    return flags


def persistence_curve(site: dict, card: dict | None = None) -> dict:
    """Return {'horizons_days', 'median', 'lo90', 'hi90', 'source', 'scope_flags', 'warnings', 'explanation',
    'state'}.
    `site` uses the predictor names of beach_series.csv (see the card's 'predictors')."""
    card = card or load_card()
    row = _site_row(site)
    flags = scope_flags(row, card)
    if card["packaged_prediction"] == "model":
        X = raw_terms([row])
        X, _, _ = standardise(X, np.array(card["standardisation"]["mean"]), np.array(card["standardisation"]["sd"]))
        boot = np.array(card["bootstrap_theta"])
        curves = np.vstack([surv_pe(th, X)[0] for th in boot])
        med = np.median(curves, axis=0)
        lo, hi = np.percentile(curves, 5, axis=0), np.percentile(curves, 95, axis=0)
        source = "model (piecewise-exponential hazards, all three states)"
    else:
        b = card["baseline_curves_all_states"][row["first_cat_group"]]
        med, lo, hi = np.array(b["median"]), np.array(b["lo90"]), np.array(b["hi90"])
        source = ("baseline fallback: Turnbull persistence curve by first oiling category (the model did not beat "
                  "the baseline, gate B-1)")
    lo, hi = np.minimum(lo, med), np.maximum(hi, med)
    i365 = HORIZONS.index(365)
    expl = (f"About {med[i365]*100:.0f}% (90% interval {lo[i365]*100:.0f}-{hi[i365]*100:.0f}%) of DWH sand-beach "
            f"segments like this still had visible oil one year after first being seen oiled, under the cleanup "
            f"as it was done in 2010-2013 ({source.split(':')[0]}).")
    key = "pred_model_365" if card["packaged_prediction"] == "model" else "pred_base_365"
    miss = [abs(r[key] - r["obs_persist_365"]) for s, r in card["per_state_results"].items() if s in TRAINED_STATES]
    warnings = []
    if miss:
        warnings = [f"held-out-state test: this curve missed observed 365-day state persistence by up to "
                         f"{max(miss)*100:.0f} percentage points; the 90% interval does not include that state-to-state "
                         f"shift"]
    return {"horizons_days": list(HORIZONS), "median": [float(x) for x in med], "lo90": [float(x) for x in lo],
            "hi90": [float(x) for x in hi], "source": source, "scope_flags": flags, "explanation": expl,
            "warnings": warnings, "state": card["declared_state"]}


class BeachSandPersistenceAdapter(mi.BaseModel):
    """Registry adapter (same constructor as registry._Adapter: takes the registry.json entry dict).

    SiteRecord.fields: the predictors named in the card (first_cat or first_cat_group, days_spill_to_first_oiled,
    first_tidal_zone, first_thickness, first_sodistro_pct, first_tb_count, exposure_open_frac); optional
    'horizon_days' (90, 180, 365 or 730; default 365). SiteRecord.habitat is read as the ESI code and
    SiteRecord.region as the state. SiteRecord.oiling may carry the SCAT category code.
    Prediction.value = probability that visible oil persists at the horizon (median of the bootstrap)."""

    def __init__(self, entry: dict | None = None):
        entry = entry or {"model_id": "beach_sand_persistence_v1",
                          "card": "models/beach_sand_persistence_v1.json"}
        self.model_id = entry["model_id"]
        self.title = entry.get("title", self.model_id)
        self.card_path = entry["card"]
        self.card = load_card(str(ROOT / entry["card"]))
        self.declared_state = STATE_EXPERIMENTAL  # never validated (D39)
        self.evidence_grade = entry.get("evidence_grade", self.card["declared_state"])
        self.state = STATE_EXPERIMENTAL
        self.model_version = self.card.get("name", self.model_id)

    def predict(self, site: SiteRecord, scenario: ScenarioRequest) -> Prediction:
        fields = dict(site.fields)
        if "first_cat_group" not in fields and "first_cat" not in fields and site.oiling:
            fields["first_cat"] = site.oiling
        if site.habitat:
            fields.setdefault("esi", site.habitat)
        if site.region:
            fields.setdefault("state", site.region)
        horizon = int(fields.pop("horizon_days", 365))
        reasons = []
        if horizon not in HORIZONS:
            nearest = min(HORIZONS, key=lambda h: abs(h - horizon))
            reasons.append(f"horizon {horizon} d not modelled; nearest modelled horizon {nearest} d used")
            horizon = nearest
        if scenario.treatment:
            reasons.append(f"treatment '{scenario.treatment}' ignored: the data record no treatment per segment; "
                           "the curve is persistence under the 2010-2013 response as carried out")
        cur = persistence_curve(fields, self.card)
        i = HORIZONS.index(horizon)
        flags = cur["scope_flags"]
        if any(f.startswith("state unseen") for f in flags):
            scope = SCOPE_NEW_REGION
        elif flags:
            scope = SCOPE_OUTSIDE
        else:
            scope = SCOPE_IN_RANGE
        reasons = flags + reasons + cur["warnings"] + list(self.card["caveats_short"])
        return Prediction(
            value=cur["median"][i], unit=f"probability visible oil still recorded {horizon} days after first oiled survey",
            interval_lo=cur["lo90"][i], interval_hi=cur["hi90"][i], interval_level=0.9,
            interval_method=(self.card["interval_method"] if self.card["packaged_prediction"] == "model" else
                             "5th-95th percentile of the Turnbull curve over bootstrap resamples of whole segments "
                             "within the first-oiling category group (baseline fallback)"), scope=scope, scope_reasons=reasons,
            explanation={"source": cur["source"], "curve": cur, "note": cur["explanation"]},
            evidence_grade=self.evidence_grade, model_id=self.model_id, model_version=self.model_version,
            state=self.state)
