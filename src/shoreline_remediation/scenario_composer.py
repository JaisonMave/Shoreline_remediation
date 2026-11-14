"""Scenario composer for an oiled salt-marsh edge cell (plan: docs/SCENARIO_PROGRAMME_PLAN.md section A2). No new fitting.

For a site and a list of options it simulates yearly outcomes to `horizon_years` from `n_draws` Monte Carlo draws:

  Edge loss rate (m/yr, positive = land lost), year y = baseline + oil excess(y) + treatment shift(y)
    baseline        clean-edge model p5-edge-loss-clean-v1 prediction (R3 fix, docs/R3_OIL_DOUBLE_COUNT_PLAN.md:
                    M1 refitted on clean-edge cells only, NOO and Very_Light, so it does not itself absorb part of
                    the oil effect added below) + a draw from its leave-one-basin-out residuals (the residuals are
                    rebuilt from data/demo/p5_sites_clean_lobo.csv; their 5th/95th percentiles equal that model
                    card's interval offsets). One draw per site, shared by all options. site_evidence's own default
                    model (p5-edge-loss-v1, used by the dashboard) is unaffected.
    oil excess      Zengel et al. 2022, oiled-untreated minus reference, change from 2005-2010 (results/p3_treatment):
                    +1.88 m/yr years 1-2 (90% 1.57 to 2.20), +0.21 m/yr years 3-8 (90% -0.56 to 0.97); drawn as normal with
                    the 90% interval read as +/-1.645 sd (ASSUMED). Shared by all options. Heavy oiling only.
    treatment shift existing erosion_prior (Zengel et al. 2022, same two periods, same normal-from-interval rule). Heavy only.
  Cumulative edge loss = sum of the yearly rates.
  Vegetation cover relative to reference = exp(lnRR) from the A1 curve (models/veg_recovery_v1.json: bootstrap (A, tau)
    pairs plus leave-one-study-out residuals), used only if its verdict is "validated" or "suggestive". Treatment shift
    from Zengel et al. 2015 (treatment_prior, percentage points divided by the reference mean cover), held from year 2
    onward and decaying with each draw's own tau (R7a fix, ASSUMED: a one-year spike at year 2 only is implausible);
    no shift before year 2 (no evidence). For Heavy sites the curve itself is flagged `veg_curve_scope` (R7b / D28:
    worse than a no-trend baseline there, FINDINGS 14) and still shown, not dropped.

Options are labelled by evidence: MEASURED (Zengel evidence for edge loss and/or vegetation), AI-proposed range, not
human-reviewed (R6 fix: A3 hook, a dict {option: (lo, hi)} of multipliers on tau; no edge-loss effect; 90% range read
as a log-normal, ASSUMED) or NO EVIDENCE (no shift of any kind). No prior value is invented here: the A3 ranges are
supplied by the caller.

Inputs : site dict with the four edge-loss features (water_1km_2010, water_250m_2010, fetch_mean_m, pre_rate), optional
         max_oiling ("Heavy" gets evidence-based shifts; any other value gets none), optional pred_rate (m/yr) overriding the
         deployed prediction (used by the C1 check to supply held-out predictions).
Outputs: compose() -> (tidy DataFrame [option, year, outcome, median, lo90, hi90, ...], summary DataFrame).
         natural_recovery_summary() -> dict (R4 fix): the one absolute edge-loss number per site, decomposed into
         baseline, oil excess and mean rate years 1-5, used by both Site evidence and Compare options so they agree.
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
OIL_EXCESS_D32_PATH = ROOT / "models" / "oil_excess_d32.json"
# R3 fix (docs/R3_OIL_DOUBLE_COUNT_PLAN.md): the composer baseline is the clean-edge refit of M1 (max_oiling in
# NOO, Very_Light only), not the deployed p5-edge-loss-v1 card (which was fitted on all cells, including Heavy,
# and so partly absorbed the oil effect that the Zengel excess below then added a second time). site_evidence's
# own default model (used by the dashboard) is unchanged; only the composer's baseline is swapped, via the
# `model=` argument of site_evidence.predict_edge_loss.
BASELINE_MODEL_PATH = ROOT / "models" / "p5_edge_loss_clean_v1.json"
BASELINE_LOBO_PATH = ROOT / "data" / "demo" / "p5_sites_clean_lobo.csv"
Z90 = 1.6448536269514722
USABLE_VEG = ("validated", "suggestive")
NATURAL = "natural_attenuation"
OUTCOMES = ("edge_loss_rate_m_per_yr", "cumulative_edge_loss_m", "veg_cover_ratio_to_reference")
SUMMARY_YEARS = (2, 5, 8)
# R6 fix (docs/V4_PROGRAMME_PLAN.md R6): these ranges were written by the AI orchestrator acting as an expert, not
# elicited from a human, so the label says so rather than implying a human elicitation process.
EVIDENCE_MEASURED, EVIDENCE_ELICITED, EVIDENCE_NONE = "MEASURED", "AI-proposed range (not human-reviewed)", "NO EVIDENCE: no shift applied"
PLANTING = "planting (after mechanical cleanup)"
# option name -> evidence group (site_evidence mapping; the planting add-on is also accepted as "planting")
GROUPS = {**se.TREATMENT_EVIDENCE, PLANTING: "mechanical+planting", "planting": "mechanical+planting"}
HEAVY = "Heavy"
# R7b / D28 (docs/V4_PROGRAMME_PLAN.md, FINDINGS 14): the A1 vegetation curve is worse than a no-trend baseline for
# heavily oiled sites. It is not dropped (still shown for transparency), but flagged wherever it is used for Heavy sites.
VEG_CURVE_SCOPE_HEAVY = "worse than no-trend baseline for heavy oiling (FINDINGS 14); shown for transparency only"
# R4 fix (docs/V4_PROGRAMME_PLAN.md R4): held-out check of the oil-excess component against NAIP heavy-cell observations.
NATURAL_RECOVERY_BIAS_NOTE = ("In held-out checks the oil-excess component over-predicted NAIP heavy-cell loss by about "
                              "0.5 m/yr (B1b +0.59, C1b +0.55; results/scenario_composer/summary_v4_r3.txt).")


@lru_cache(maxsize=1)
def _veg_model() -> dict:
    with open(VEG_MODEL) as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _baseline_model() -> dict:
    """The composer's own baseline model (R3 fix): clean-edge M1, not site_evidence's default p5-edge-loss-v1."""
    with open(BASELINE_MODEL_PATH) as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _baseline_lobo() -> pd.DataFrame:
    """Per-cell leave-one-basin-out predictions from the clean-edge baseline (data/demo/p5_sites_clean_lobo.csv),
    built by scripts/build_clean_baseline.py. Every in-scope cell, any oiling class; data/demo/p5_sites.csv (the
    v1 table) is not touched."""
    return pd.read_csv(BASELINE_LOBO_PATH, dtype={"cell": str, "cell_2km": str})


@lru_cache(maxsize=1)
def _lobo_residuals() -> np.ndarray:
    s = _baseline_lobo()
    s = s[s.observed_rate.notna() & s.lobo_pred_clean.notna()]
    return (s.observed_rate - s.lobo_pred_clean).to_numpy()


@lru_cache(maxsize=1)
def _oil_excess() -> dict:
    """period -> (effect, lo, hi) of oiled-untreated minus reference, from the P3 pre-spill-adjusted table."""
    adj = _oil_excess_d32_adjustment()
    scale = float(adj["scale"])
    pooled_sd_total = float(adj["pooled_sd_total"])
    d = pd.read_csv(P3_A)
    d = d[d.contrast == "Oiled, untreated minus Reference (unoiled)"]
    out = {}
    for _, r in d.iterrows():
        period = "2010-2012" if r.analysis.startswith("A 2010-2012") else "2012-2018"
        effect = float(r["difference"])
        lo = float(r.lo90)
        hi = float(r.hi90)
        if scale == 1.0 and pooled_sd_total == 0.0:
            out[period] = (effect, lo, hi)
            continue
        effect_scaled = scale * effect
        scaled_sd = abs(scale) * ((hi - lo) / (2 * Z90))
        sd_total = scaled_sd + pooled_sd_total
        half90 = Z90 * sd_total
        out[period] = (effect_scaled, effect_scaled - half90, effect_scaled + half90)
    return out


@lru_cache(maxsize=1)
def _oil_excess_d32_adjustment() -> dict:
    """Optional D32 oil-excess scaling from models/oil_excess_d32.json. Missing/invalid file -> identity."""
    out = {"scale": 1.0, "pooled_sd_total": 0.0, "interval_inflation_90": 0.0}
    if not OIL_EXCESS_D32_PATH.exists():
        return out
    try:
        with open(OIL_EXCESS_D32_PATH) as f:
            data = json.load(f)
        scale = float(data.get("scale", 1.0))
        pooled_sd_total = float(data.get("pooled_sd_total", 0.0))
        interval_inflation_90 = float(data.get("interval_inflation_90", 0.0))
        if pooled_sd_total == 0.0 and interval_inflation_90 > 0:
            pooled_sd_total = interval_inflation_90 / Z90
        if not np.isfinite(scale):
            scale = 1.0
        if not np.isfinite(pooled_sd_total) or pooled_sd_total < 0:
            pooled_sd_total = 0.0
        if not np.isfinite(interval_inflation_90) or interval_inflation_90 < 0:
            interval_inflation_90 = Z90 * pooled_sd_total
        out.update({"scale": scale, "pooled_sd_total": pooled_sd_total, "interval_inflation_90": interval_inflation_90})
        return out
    except Exception:
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
    year 2, and cannot_be_distinguished flags (90% ranges overlap natural recovery: the old rule, kept for transparency).
    Plan A4.1: paired differences (option minus natural, same draw) at years 2, 5, 8 for cumulative edge loss
    (paired_diff_cum_edge_loss_y{y}_*) and, where a shift or elicited range exists, vegetation ratio (paired_diff_veg_ratio_y{y}_*),
    with edge_distinguished_y{y} / veg_distinguished_y{y} true when the 90% interval of the paired difference excludes zero.
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
        base_rate = se.predict_edge_loss({k: site[k] for k in se.FEATURES}, model=_baseline_model())["rate"]
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
        if shift_y2 is not None:
            # R7a fix (ASSUMED, docs/V4_PROGRAMME_PLAN.md R7a): the year-2 Zengel treatment shift used to be added at
            # year 2 only, so the trajectory jumped up and back down at year 3. It now holds from year 2 onward,
            # decaying as shift * exp(-(t - t2) / tau) with each draw's own tau (t2 = 2.5 in the A1 time convention),
            # so the treatment effect fades as the untreated curve itself recovers. Year-2 values are unchanged
            # (decay = 1 at t = t2); later years change.
            t2 = 2.5
            decay = np.where(t >= t2, np.exp(-(t - t2) / tau[:, None]), 0.0)
            r = r + shift_y2[:, None] * decay
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
        for y in SUMMARY_YEARS:      # A4.1: paired difference from natural recovery (same draw), excludes zero -> distinguished
            if y > horizon_years:
                continue
            pm, plo, phi = _q(m["cum"][:, y - 1] - nat["cum"][:, y - 1])
            row.update({f"paired_diff_cum_edge_loss_y{y}_median": pm, f"paired_diff_cum_edge_loss_y{y}_lo90": plo,
                        f"paired_diff_cum_edge_loss_y{y}_hi90": phi,
                        f"edge_distinguished_y{y}": np.nan if opt == NATURAL else bool(plo > 0 or phi < 0)})
            if m["veg"] is not None:
                vm_, vlo_, vhi_ = _q(m["veg"][:, y - 1] - nat["veg"][:, y - 1])
                row.update({f"paired_diff_veg_ratio_y{y}_median": vm_, f"paired_diff_veg_ratio_y{y}_lo90": vlo_,
                            f"paired_diff_veg_ratio_y{y}_hi90": vhi_,
                            f"veg_distinguished_y{y}": np.nan if opt == NATURAL else bool(m["has_veg_shift"] and (vlo_ > 0 or vhi_ < 0))})
                if not m["has_veg_shift"]:     # no shift and no elicited range: no vegetation difference to report
                    for k_ in ("median", "lo90", "hi90"):
                        row[f"paired_diff_veg_ratio_y{y}_{k_}"] = np.nan
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
            if heavy:                 # R7b / D28: flag the curve as out of scope for heavy oiling, not dropped
                row["veg_curve_scope"] = VEG_CURVE_SCOPE_HEAVY
        else:
            row["veg_curve_verdict"] = veg["verdict"] + " (curve not used)"
        srows.append(row)
    return tidy, pd.DataFrame(srows)


def natural_recovery_summary(site: dict, n_draws: int = 5000, seed: int = 20261112, residual_pool: np.ndarray | None = None) -> dict:
    """One absolute edge-loss number per site (R4 fix, docs/V4_PROGRAMME_PLAN.md R4), decomposed rather than hidden.

    Both "Site evidence" (the per-site headline) and "Compare options" (the natural-recovery row) must call this
    function so the same cell never shows two different absolute forecasts. It is built entirely from compose(),
    so it always agrees with the option comparison by construction.

    Returns a dict:
      baseline       clean-edge model point prediction with its 90% interval (model p5-edge-loss-clean-v1; no oil
                     term). None for lo90/hi90 if the caller supplied `pred_rate` directly (no model interval).
      oil_excess     {period: {effect, lo90, hi90}} for "2010-2012" and "2012-2018" (Zengel et al. 2022 untreated-plot
                     excess over reference), or None if the site is not heavily oiled (evidence covers Heavy only).
      mean_rate_y1_5 {median, lo90, hi90}: natural recovery's own composed mean edge-loss rate over years 1-5 (the
                     cumulative edge loss at year 5, divided by 5; dividing by a positive constant preserves quantiles).
      heavy          bool, whether the oil-excess term applies here.
      bias_note      str: held-out evidence that the oil-excess component over-predicts heavy-cell loss (R3/R4).
    """
    heavy = site.get("max_oiling", HEAVY) == HEAVY
    if site.get("pred_rate") is not None:
        base_rate, base_lo, base_hi = float(site["pred_rate"]), None, None
    else:
        pred = se.predict_edge_loss({k: site[k] for k in se.FEATURES}, model=_baseline_model())
        base_rate, base_lo, base_hi = pred["rate"], pred["lo"], pred["hi"]
    oil_excess = None
    if heavy:
        oil = _oil_excess()
        oil_excess = {p: {"effect": oil[p][0], "lo90": oil[p][1], "hi90": oil[p][2]} for p in ("2010-2012", "2012-2018")}
    tidy, _ = compose(site, [], horizon_years=5, n_draws=n_draws, seed=seed, residual_pool=residual_pool)
    cum5 = tidy[(tidy.option == NATURAL) & (tidy.outcome == "cumulative_edge_loss_m") & (tidy.year == 5)].iloc[0]
    mean_rate_y1_5 = {"median": cum5["median"] / 5, "lo90": cum5.lo90 / 5, "hi90": cum5.hi90 / 5}
    return {
        "baseline": {"rate": base_rate, "lo90": base_lo, "hi90": base_hi},
        "oil_excess": oil_excess,
        "mean_rate_y1_5": mean_rate_y1_5,
        "heavy": heavy,
        "bias_note": NATURAL_RECOVERY_BIAS_NOTE,
    }


# ---------------------------------------------------------------------------------------------------------------------
# Plan A4.2: block-level composer
CELL_LENGTH_M = 100.0   # ASSUMED: one cell holds 100 m of marsh edge (known to be an underestimate)
MIN_BLOCK_CELLS = 5     # ASSUMED: blocks with fewer valid cells are not used to build the block/within-block residual pools
BLOCK_OUTCOMES = ("mean_edge_loss_rate_m_per_yr", "mean_cumulative_edge_loss_m", "cumulative_area_lost_m2", "cumulative_area_lost_ha")


@lru_cache(maxsize=1)
def _block_pools() -> tuple[np.ndarray, np.ndarray]:
    """(block mean residuals, within-block residuals) of the clean-edge baseline's held-out (leave-one-basin-out)
    residuals, from blocks (2 km cells) with at least MIN_BLOCK_CELLS valid cells."""
    s = _baseline_lobo()
    s = s[s.observed_rate.notna() & s.lobo_pred_clean.notna()]
    return split_block_residuals(s.cell_2km, (s.observed_rate - s.lobo_pred_clean))


def split_block_residuals(block_ids, residuals, min_cells: int = MIN_BLOCK_CELLS) -> tuple[np.ndarray, np.ndarray]:
    """Split residuals into block means (one per block with >= min_cells cells) and within-block deviations (cell minus block mean)."""
    d = pd.DataFrame({"b": np.asarray(block_ids), "r": np.asarray(residuals, float)}).dropna()
    d = d[d.groupby("b").r.transform("size") >= min_cells]
    mean = d.groupby("b").r.transform("mean")
    return d.groupby("b").r.mean().to_numpy(), (d.r - mean).to_numpy()


def compose_block(cells: pd.DataFrame, options: list[str], horizon_years: int = 8, n_draws: int = 2000, seed: int = 20261112,
                  elicited: dict | None = None, residual_pools: tuple[np.ndarray, np.ndarray] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compose a set of edge cells (a 2 km block or any selection). Plan A4.2.

    cells: one row per cell with either `pred_rate` (m/yr baseline prediction) or the four edge-loss features, and optionally
    `max_oiling` (default Heavy; only Heavy cells get the oil excess and treatment shifts, as in compose()).
    Noise: per draw ONE block residual (resampled from the empirical block-mean residuals) shared by all cells plus an
    independent within-block residual per cell (resampled from the empirical within-block deviations). Oil excess and
    treatment shifts are drawn once per draw and shared by all cells. Natural recovery is always included.
    Outcomes per option and year: mean edge loss rate over cells (m/yr), mean cumulative edge loss (m), cumulative area lost
    (sum over cells of cumulative retreat x CELL_LENGTH_M, m2 and ha). Returns (tidy, summary); summary holds the paired
    differences from natural recovery at years 2, 5, 8 for cumulative area (m2 and ha) and `area_distinguished_y{y}`.
    """
    elicited = elicited or {}
    options = list(dict.fromkeys([NATURAL] + list(options)))
    cells = cells.reset_index(drop=True)
    n = len(cells)
    if n == 0:
        raise ValueError("compose_block needs at least one cell")
    years = np.arange(1, horizon_years + 1)
    heavy = (cells["max_oiling"].to_numpy() == HEAVY) if "max_oiling" in cells else np.ones(n, bool)
    if "pred_rate" in cells and cells["pred_rate"].notna().all():
        base = cells["pred_rate"].to_numpy(float)
    else:
        base = np.array([se.predict_edge_loss({k: float(r[k]) for k in se.FEATURES}, model=_baseline_model())["rate"]
                        for _, r in cells.iterrows()])
    bpool, wpool = _block_pools() if residual_pools is None else (np.asarray(residual_pools[0], float), np.asarray(residual_pools[1], float))

    shared = _rng(seed, "block-shared")
    block_res = shared.choice(bpool, n_draws)                    # (n_draws,) one per draw, shared by all cells
    within = shared.choice(wpool, (n_draws, n))                  # (n_draws, n_cells) independent
    baseline = base[None, :] + block_res[:, None] + within       # (n_draws, n_cells)
    oil = _oil_excess()
    oil_by_period = {p: _normal_from_interval(shared, oil[p][1], oil[p][2], n_draws, effect=oil[p][0]) for p in ("2010-2012", "2012-2018")}
    hv = heavy.astype(float)[None, :]

    mats, labels = {}, {}
    for opt in options:
        g = GROUPS.get(opt)
        r = _rng(seed, "block-option", opt)
        shift, label = None, EVIDENCE_NONE
        if opt in elicited:
            label = EVIDENCE_ELICITED
        elif g == "none":
            label = EVIDENCE_MEASURED + " (comparison group)"
        elif g is not None and heavy.any():
            shift = {}
            for p in ("2010-2012", "2012-2018"):
                e = _erosion(g, p)
                shift[p] = _normal_from_interval(r, e["lo"], e["hi"], n_draws, effect=e["effect"])
            label = EVIDENCE_MEASURED
        cum = np.zeros((n_draws, n))
        cols_rate, cols_cum, cols_area = [], [], []
        for y in years:
            p = "2010-2012" if y <= 2 else "2012-2018"
            rate = baseline + hv * (oil_by_period[p][:, None] + (shift[p][:, None] if shift else 0.0))
            cum = cum + rate
            cols_rate.append(rate.mean(1))
            cols_cum.append(cum.mean(1))
            cols_area.append(cum.sum(1) * CELL_LENGTH_M)
        mats[opt] = {"rate": np.column_stack(cols_rate), "cum": np.column_stack(cols_cum), "area": np.column_stack(cols_area)}
        labels[opt] = label

    rows = []
    for opt in options:
        m = mats[opt]
        arrays = {BLOCK_OUTCOMES[0]: m["rate"], BLOCK_OUTCOMES[1]: m["cum"], BLOCK_OUTCOMES[2]: m["area"], BLOCK_OUTCOMES[3]: m["area"] / 1e4}
        for name, arr in arrays.items():
            for j, y in enumerate(years):
                med, lo, hi = _q(arr[:, j])
                rows.append({"option": opt, "year": int(y), "outcome": name, "median": med, "lo90": lo, "hi90": hi, "evidence": labels[opt]})
    tidy = pd.DataFrame(rows)

    nat = mats[NATURAL]
    srows = []
    for opt in options:
        m = mats[opt]
        row = {"option": opt, "evidence": labels[opt], "n_cells": n, "n_heavy_cells": int(heavy.sum())}
        for y in SUMMARY_YEARS:
            if y > horizon_years:
                continue
            j = y - 1
            for tag, key, scale in (("area_m2", "area", 1.0), ("area_ha", "area", 1e-4), ("mean_rate", "rate", 1.0)):
                pm, plo, phi = _q((m[key][:, j] - nat[key][:, j]) * scale)
                row.update({f"paired_diff_{tag}_y{y}_median": pm, f"paired_diff_{tag}_y{y}_lo90": plo, f"paired_diff_{tag}_y{y}_hi90": phi})
            row[f"area_distinguished_y{y}"] = np.nan if opt == NATURAL else bool(row[f"paired_diff_area_m2_y{y}_lo90"] > 0 or row[f"paired_diff_area_m2_y{y}_hi90"] < 0)
        srows.append(row)
    return tidy, pd.DataFrame(srows)


# ---------------------------------------------------------------------------------------------------------------------
# Plan B1: forecast wrapper
FORECAST_MAX_YEARS = 8
EXTRAPOLATION_MESSAGE = ("extrapolation: no outcome data beyond 2018 (the longest outcome held is 8 years after the 2010 oiling); "
                         "horizons beyond 8 years are refused")


def forecast(site_or_cells, option: str = NATURAL, horizons: tuple = (1, 3, 5, 8), n_draws: int = 2000, seed: int = 20261112,
             elicited: dict | None = None, residual_pool=None, residual_pools=None) -> pd.DataFrame:
    """Cumulative edge loss with 90% ranges at each horizon (plan B1). Refuses any horizon beyond 8 years (ValueError).

    site_or_cells: a site dict (as compose(); outputs cumulative edge loss in m) or a DataFrame of cells (as compose_block();
    outputs mean cumulative edge loss in m and cumulative area lost in m2 and ha, one cell ASSUMED = 100 m of edge).
    Inputs are only what is known at forecast time (oiling class, exposure features or pred_rate, pre-spill trend, option).
    Returns DataFrame [option, horizon_years, outcome, median, lo90, hi90, evidence]. Deterministic for a given seed.
    """
    hs = sorted({int(h) for h in horizons})
    if not hs or hs[0] < 1:
        raise ValueError("horizons must be whole years >= 1")
    if hs[-1] > FORECAST_MAX_YEARS:
        raise ValueError(f"horizon {hs[-1]} years refused: {EXTRAPOLATION_MESSAGE}")
    top = hs[-1]
    if isinstance(site_or_cells, pd.DataFrame):
        tidy, _ = compose_block(site_or_cells, [option], horizon_years=top, n_draws=n_draws, seed=seed, elicited=elicited,
                                residual_pools=residual_pools)
        keep = ("mean_cumulative_edge_loss_m", "cumulative_area_lost_m2", "cumulative_area_lost_ha")
    else:
        tidy, _ = compose(site_or_cells, [option], horizon_years=top, n_draws=n_draws, seed=seed, elicited=elicited,
                          residual_pool=residual_pool)
        keep = ("cumulative_edge_loss_m",)
    t = tidy[(tidy.option == option) & tidy.outcome.isin(keep) & tidy.year.isin(hs)]
    return t.rename(columns={"year": "horizon_years"}).reset_index(drop=True)[
        ["option", "horizon_years", "outcome", "median", "lo90", "hi90", "evidence"]]
