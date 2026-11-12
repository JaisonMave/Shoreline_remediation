"""Scenario composer for an oiled salt-marsh edge cell (plan: docs/SCENARIO_PROGRAMME_PLAN.md section A2). No new fitting.

For a site and a list of options it simulates yearly outcomes to `horizon_years` from `n_draws` Monte Carlo draws:

  Edge loss rate (m/yr, positive = land lost), year y = baseline + oil excess(y) + treatment shift(y)
    baseline        deployed model p5-edge-loss-v1 prediction + a draw from its leave-one-basin-out residuals (the
                    residuals are rebuilt from data/demo/p5_sites.csv; their 5th/95th percentiles equal the model card's
                    interval offsets). One draw per site, shared by all options.
    oil excess      Zengel et al. 2022, oiled-untreated minus reference, change from 2005-2010 (results/p3_treatment):
                    +1.88 m/yr years 1-2 (90% 1.57 to 2.20), +0.21 m/yr years 3-8 (90% -0.56 to 0.97); drawn as normal with
                    the 90% interval read as +/-1.645 sd (ASSUMED). Shared by all options. Heavy oiling only.
    treatment shift existing erosion_prior (Zengel et al. 2022, same two periods, same normal-from-interval rule). Heavy only.
  Cumulative edge loss = sum of the yearly rates.
  Vegetation cover relative to reference = exp(lnRR) from the A1 curve (models/veg_recovery_v1.json: bootstrap (A, tau)
    pairs plus leave-one-study-out residuals), used only if its verdict is "validated" or "suggestive". Treatment shift
    at year 2 only, from Zengel et al. 2015 (treatment_prior, percentage points divided by the reference mean cover);
    no shift is applied at other years (no evidence).

Options are labelled by evidence: MEASURED (Zengel evidence for edge loss and/or vegetation), ELICITED (A3 hook: a dict
{option: (lo, hi)} of multipliers on tau; no edge-loss effect; 90% range read as a log-normal, ASSUMED) or NO EVIDENCE
(no shift of any kind). No prior value is invented here: the A3 ranges are supplied by the caller.

Inputs : site dict with the four edge-loss features (water_1km_2010, water_250m_2010, fetch_mean_m, pre_rate), optional
         max_oiling ("Heavy" gets evidence-based shifts; any other value gets none), optional pred_rate (m/yr) overriding the
         deployed prediction (used by the C1 check to supply held-out predictions).
Outputs: compose() -> (tidy DataFrame [option, year, outcome, median, lo90, hi90, ...], summary DataFrame).
"""
from __future__ import annotations

import json
import zlib
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from src.shoreline_remediation import site_evidence as se
from src.shoreline_remediation import treatment_effects as te

ROOT = Path(__file__).resolve().parents[2]
VEG_MODEL = ROOT / "models" / "veg_recovery_v1.json"
P3_A = ROOT / "results" / "p3_treatment" / "A_prespill_adjusted.csv"
Z90 = 1.6448536269514722
USABLE_VEG = ("validated", "suggestive")
NATURAL = "natural_attenuation"
OUTCOMES = ("edge_loss_rate_m_per_yr", "cumulative_edge_loss_m", "veg_cover_ratio_to_reference")
SUMMARY_YEARS = (2, 5, 8)
EVIDENCE_MEASURED, EVIDENCE_ELICITED, EVIDENCE_NONE = "MEASURED", "ELICITED, not measured", "NO EVIDENCE: no shift applied"
PLANTING = "planting (after mechanical cleanup)"
# option name -> evidence group (site_evidence mapping; the planting add-on is also accepted as "planting")
GROUPS = {**se.TREATMENT_EVIDENCE, PLANTING: "mechanical+planting", "planting": "mechanical+planting"}
HEAVY = "Heavy"


@lru_cache(maxsize=1)
def _veg_model() -> dict:
    with open(VEG_MODEL) as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _lobo_residuals() -> np.ndarray:
    s = se.load_sites()
    s = s[(s.status == "in_scope") & s.observed_rate.notna() & s.lobo_pred.notna()]
    return (s.observed_rate - s.lobo_pred).to_numpy()


@lru_cache(maxsize=1)
def _oil_excess() -> dict:
    """period -> (effect, lo, hi) of oiled-untreated minus reference, from the P3 pre-spill-adjusted table."""
    d = pd.read_csv(P3_A)
    d = d[d.contrast == "Oiled, untreated minus Reference (unoiled)"]
    out = {}
    for _, r in d.iterrows():
        period = "2010-2012" if r.analysis.startswith("A 2010-2012") else "2012-2018"
        out[period] = (float(r["difference"]), float(r.lo90), float(r.hi90))
    return out


@lru_cache(maxsize=1)
def _reference_cover_year2() -> float:
    df = te.load()
    m = df[(df.study == "main") & (df.metric == "Total Vegetation Cover (%)") & (df.treatment == "Reference") & (df.year == 2012)]
    return float(m["mean"].iloc[0])


@lru_cache(maxsize=None)
def _erosion(group: str, period: str) -> dict:
    return te.erosion_prior(group, period, oiling="heavy")


@lru_cache(maxsize=None)
def _veg_prior(group: str):
    return te.treatment_prior(group, 2, oiling="heavy")


def _normal_from_interval(rng, lo, hi, n, effect=None):
    mean = (lo + hi) / 2 if effect is None else effect
    return rng.normal(mean, (hi - lo) / (2 * Z90), n)


def _q(x: np.ndarray) -> tuple[float, float, float]:
    return tuple(float(v) for v in np.percentile(x, [50, 5, 95]))


def _rng(seed: int, *keys) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence([seed] + [zlib.crc32(str(k).encode()) for k in keys]))


def compose(site: dict, options: list[str], horizon_years: int = 8, n_draws: int = 5000, seed: int = 20261112,
            elicited: dict | None = None, residual_pool: np.ndarray | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Simulate yearly outcomes for `options` at `site`. See the module docstring. Returns (tidy, summary).

    tidy columns: option, year, outcome, median, lo90, hi90, evidence. Natural recovery is always included.
    summary: one row per option, with cumulative edge loss at years 2, 5, 8 (median, lo90, hi90), probability that
    the option has less cumulative edge loss than natural recovery, the paired difference at year 8, vegetation at
    year 2, and cannot_be_distinguished flags (90% ranges overlap natural recovery).
    """
    elicited = elicited or {}
    options = list(dict.fromkeys([NATURAL] + list(options)))
    years = np.arange(1, horizon_years + 1)
    heavy = site.get("max_oiling", HEAVY) == HEAVY
    pool = _lobo_residuals() if residual_pool is None else np.asarray(residual_pool, float)

    # shared draws (common random numbers across options, so comparisons are paired)
    shared = _rng(seed, "shared")
    if site.get("pred_rate") is not None:
        base_rate = float(site["pred_rate"])
    else:
        base_rate = se.predict_edge_loss({k: site[k] for k in se.FEATURES})["rate"]
    baseline = base_rate + shared.choice(pool, n_draws)
    oil = _oil_excess()
    oil_by_period = {p: _normal_from_interval(shared, oil[p][1], oil[p][2], n_draws, effect=oil[p][0]) for p in ("2010-2012", "2012-2018")}
    veg = _veg_model()
    veg_ok = veg["verdict"] in USABLE_VEG
    if veg_ok:
        bA, bT = np.array(veg["bootstrap_draws"]["A"]), np.array(veg["bootstrap_draws"]["tau"])
        k = shared.integers(0, len(bA), n_draws)
        A, tau = bA[k], bT[k]
        resid = shared.choice(np.array(veg["loso_residuals"]), n_draws)

    def rate_matrix(shift):            # (n_draws, years)
        cols = []
        for y in years:
            p = "2010-2012" if y <= 2 else "2012-2018"
            cols.append(baseline + (oil_by_period[p] if heavy else 0.0) + (shift[p] if shift else 0.0))
        return np.column_stack(cols)

    def veg_ratio(tau_mult, shift_y2):   # (n_draws, years)
        t = years[None, :] + 0.5      # A1 convention t = Year - 2010 + 0.5; year y after oiling (2010) is t = y + 0.5
        ln = -A[:, None] * np.exp(-t / (tau[:, None] * tau_mult[:, None])) + resid[:, None]
        r = np.exp(ln)
        if shift_y2 is not None and horizon_years >= 2:
            r[:, 1] = r[:, 1] + shift_y2
        return r

    results, labels, mats = {}, {}, {}
    for opt in options:
        g = GROUPS.get(opt)
        r = _rng(seed, "option", opt)
        shift, shift_y2, mult, label = None, None, np.ones(n_draws), EVIDENCE_NONE
        if opt in elicited:
            lo, hi = elicited[opt]
            mult = np.exp(r.normal((np.log(lo) + np.log(hi)) / 2, (np.log(hi) - np.log(lo)) / (2 * Z90), n_draws))
            label = EVIDENCE_ELICITED
        elif g == "none":
            label = EVIDENCE_MEASURED + " (comparison group)"
        elif g is not None and heavy:
            shift = {}
            for p in ("2010-2012", "2012-2018"):
                e = _erosion(g, p)
                shift[p] = _normal_from_interval(r, e["lo"], e["hi"], n_draws, effect=e["effect"])
            label = EVIDENCE_MEASURED
            if g in ("manual", "mechanical"):
                v = _veg_prior(g)
                shift_y2 = _normal_from_interval(r, v.veg_cover_lo, v.veg_cover_hi, n_draws, effect=v.veg_cover_effect) / _reference_cover_year2()
        rates = rate_matrix(shift)
        mats[opt] = {"rate": rates, "cum": rates.cumsum(1), "veg": veg_ratio(mult, shift_y2) if veg_ok else None,
                     "has_veg_shift": shift_y2 is not None or opt in elicited,
                     "has_edge_shift": shift is not None}
        labels[opt] = label

    rows = []
    for opt in options:
        m = mats[opt]
        series = {OUTCOMES[0]: m["rate"], OUTCOMES[1]: m["cum"]}
        if m["veg"] is not None:
            series[OUTCOMES[2]] = m["veg"]
        for name, arr in series.items():
            for j, y in enumerate(years):
                med, lo, hi = _q(arr[:, j])
                rows.append({"option": opt, "year": int(y), "outcome": name, "median": med, "lo90": lo, "hi90": hi,
                             "evidence": labels[opt]})
    tidy = pd.DataFrame(rows)

    nat = mats[NATURAL]
    srows = []
    for opt in options:
        m = mats[opt]
        row = {"option": opt, "evidence": labels[opt], "evidence_scope_heavy_only": not heavy}
        for y in SUMMARY_YEARS:
            if y > horizon_years:
                continue
            j = y - 1
            med, lo, hi = _q(m["cum"][:, j])
            nmed, nlo, nhi = _q(nat["cum"][:, j])
            row.update({f"cum_edge_loss_y{y}_median": med, f"cum_edge_loss_y{y}_lo90": lo, f"cum_edge_loss_y{y}_hi90": hi,
                        f"p_less_edge_loss_than_natural_y{y}": float(np.mean(m["cum"][:, j] < nat["cum"][:, j])) if m["has_edge_shift"] else np.nan,
                        f"edge_cannot_be_distinguished_y{y}": (np.nan if opt == NATURAL else bool(lo <= nhi and hi >= nlo))})
        jl = min(8, horizon_years) - 1
        d = m["cum"][:, jl] - nat["cum"][:, jl]
        dm, dlo, dhi = _q(d)
        row.update({"paired_diff_cum_edge_loss_median": dm, "paired_diff_cum_edge_loss_lo90": dlo, "paired_diff_cum_edge_loss_hi90": dhi})
        if m["veg"] is not None and horizon_years >= 2:
            vm, vlo, vhi = _q(m["veg"][:, 1])
            nvm, nvlo, nvhi = _q(nat["veg"][:, 1])
            row.update({"veg_ratio_y2_median": vm, "veg_ratio_y2_lo90": vlo, "veg_ratio_y2_hi90": vhi})
            if opt != NATURAL and m["has_veg_shift"]:
                row["p_more_vegetation_than_natural_y2"] = float(np.mean(m["veg"][:, 1] > nat["veg"][:, 1]))
            else:
                row["p_more_vegetation_than_natural_y2"] = np.nan
            row["veg_cannot_be_distinguished_y2"] = np.nan if opt == NATURAL else bool(vlo <= nvhi and vhi >= nvlo)
            row["veg_curve_verdict"] = veg["verdict"]
        else:
            row["veg_curve_verdict"] = veg["verdict"] + " (curve not used)"
        srows.append(row)
    return tidy, pd.DataFrame(srows)
