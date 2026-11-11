"""Recovery analysis for a satellite time series of an oiled site and a nearby reference site.

Design: before-after-control-impact (BACI). The analysed quantity is the difference between the oiled site
and the reference site, which removes weather and season effects the two sites share. After the spill the
difference is modelled as a sudden drop that decays back towards the pre-spill level:

    d(t) = level + seasonal(t) + [t >= spill] * ( -drop * exp(-(t - spill) / tau) ) + noise

    drop   size of the initial impact (same units as the series, e.g. NDVI)
    tau    recovery time constant in years; 90% of the drop is recovered after tau * ln(10) years

With persistent=True a lasting step is added after the spill, for marsh that never comes back (for
example an oiled edge that eroded into open water):

    d(t) = ... + [t >= spill] * ( -loss - drop * exp(-(t - spill) / tau) )

    loss   the part of the impact still present at the end of the record

Recovery is then measured towards the new, lower level. Persistent loss and slow recovery look alike in a
short record, so use this option only with several years of post-spill data.

Uncertainty comes from a moving-block bootstrap of the residuals, which keeps their month-to-month
correlation. A placebo test repeats the fit with false spill dates inside the pre-spill period: if those
"find" impacts as large as the real one, the real estimate should not be trusted.

Input: a table with columns date, oiled, reference (see scripts/gee_export_ndvi.py). Months with no clear
image are simply absent. This module has been tested on simulated series only, not yet on real imagery.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

LN10 = float(np.log(10.0))
MAX_TAU_YEARS = 50.0


@dataclass
class RecoveryEstimate:
    drop: float
    tau_years: float
    years_to_90pct_recovery: float
    drop_interval: tuple[float, float]  # 90% bootstrap interval
    years_to_90pct_interval: tuple[float, float]
    drop_in_noise_sd: float  # drop divided by the residual standard deviation
    n_observations: int
    n_pre_spill: int
    persistent_loss: float | None = None  # only with persistent=True
    persistent_loss_interval: tuple[float, float] | None = None


def _years(dates: pd.Series) -> np.ndarray:
    dates = pd.to_datetime(dates)
    return (dates.dt.year + (dates.dt.dayofyear - 1) / 365.25).to_numpy(float)


def _prepare(series: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    clean = series.dropna(subset=["oiled", "reference"]).sort_values("date")
    return _years(clean["date"]), (clean["oiled"] - clean["reference"]).to_numpy(float)


def _design(t: np.ndarray) -> np.ndarray:
    return np.column_stack([np.ones_like(t), np.sin(2 * np.pi * t), np.cos(2 * np.pi * t)])


def _fit(t: np.ndarray, d: np.ndarray, spill: float, persistent: bool = False) -> tuple[float, float, np.ndarray, float]:
    """Return drop, tau, fitted values and persistent loss (0 unless persistent=True). Level, season, drop
    and loss are linear and solved exactly for each tau."""
    base = _design(t)
    after = t >= spill
    if persistent:
        base = np.column_stack([base, -after.astype(float)])

    def solve(log_tau: float):
        decay = np.where(after, -np.exp(-(t - spill) / np.exp(log_tau)), 0.0)
        matrix = np.column_stack([base, decay])
        coef, *_ = np.linalg.lstsq(matrix, d, rcond=None)
        return coef, matrix @ coef

    best = min(
        (least_squares(lambda p: solve(p[0])[1] - d, [start], bounds=(np.log(0.05), np.log(MAX_TAU_YEARS)))
         for start in np.log([0.5, 2.0, 8.0])),
        key=lambda result: result.cost,
    )
    coef, fitted = solve(best.x[0])
    return float(coef[-1]), float(np.exp(best.x[0])), fitted, float(coef[-2]) if persistent else 0.0


def fit_recovery(series: pd.DataFrame, spill_date: str, n_boot: int = 300, block: int = 6, seed: int = 0,
                 persistent: bool = False) -> RecoveryEstimate:
    """Estimate the impact and recovery time. `block` is the bootstrap block length in observations."""
    t, d = _prepare(series)
    spill = float(_years(pd.Series([spill_date]))[0])
    n_pre = int((t < spill).sum())
    if n_pre < 24 or (t >= spill).sum() < 12:
        raise ValueError("Need at least 24 observations before the spill and 12 after it.")
    drop, tau, fitted, loss = _fit(t, d, spill, persistent)
    residual = d - fitted
    rng = np.random.default_rng(seed)
    starts = np.arange(len(residual) - block + 1)
    drops, times, losses = [], [], []
    for _ in range(n_boot):
        picks = rng.choice(starts, size=int(np.ceil(len(residual) / block)))
        resampled = np.concatenate([residual[s:s + block] for s in picks])[:len(residual)]
        boot_drop, boot_tau, _, boot_loss = _fit(t, fitted + resampled, spill, persistent)
        drops.append(boot_drop)
        times.append(boot_tau * LN10)
        losses.append(boot_loss)
    interval = lambda values: (float(np.percentile(values, 5)), float(np.percentile(values, 95)))  # noqa: E731
    n_params = 5 + int(persistent)
    return RecoveryEstimate(drop, tau, tau * LN10, interval(drops), interval(times),
                            drop / float(residual.std(ddof=n_params)), len(d), n_pre,
                            loss if persistent else None, interval(losses) if persistent else None)


def placebo_test(series: pd.DataFrame, spill_date: str, n_placebos: int = 8) -> pd.DataFrame:
    """Fit the same model to pre-spill data only, with false spill dates. Returns one row per false date
    plus the real estimate. A real impact should stand well outside the false ones.

    Compare `impact_2yr`, the impact accumulated over the first two years (drop * tau * (1 - exp(-2 / tau)),
    in NDVI-years), not `drop`. A false date can fit a single noisy month as a large drop that vanishes
    within weeks; its accumulated impact stays small."""
    t, d = _prepare(series)
    spill = float(_years(pd.Series([spill_date]))[0])
    before = t < spill
    t_pre, d_pre = t[before], d[before]
    candidates = np.linspace(t_pre[0] + 2.0, t_pre[-1] - 1.0, n_placebos)
    def row(kind: str, times: np.ndarray, values: np.ndarray, date: float) -> dict:
        drop, tau, _, _ = _fit(times, values, date)  # plain model: a lasting step is not identifiable in 1-2 years
        return {"spill_year": round(date, 2), "kind": kind, "drop": round(drop, 4), "tau_years": round(tau, 3),
                "impact_2yr": round(drop * tau * (1.0 - np.exp(-2.0 / tau)), 4)}

    rows = [row("placebo", t_pre, d_pre, float(fake)) for fake in candidates]
    rows.append(row("real", t, d, spill))
    return pd.DataFrame(rows)


def monthly_medians(observations: pd.DataFrame, min_pixels: int = 20) -> pd.DataFrame:
    """Turn per-image values (columns date, site, ndvi, pixels) into the monthly table fit_recovery needs.
    Images with fewer than `min_pixels` clear pixels are dropped."""
    usable = observations[observations["pixels"] >= min_pixels].copy()
    usable["date"] = pd.to_datetime(usable["date"]).dt.to_period("M").dt.to_timestamp()
    table = usable.pivot_table(index="date", columns="site", values="ndvi", aggfunc="median")
    return table.dropna(subset=["oiled", "reference"]).reset_index()[["date", "oiled", "reference"]]
