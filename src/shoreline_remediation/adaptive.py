from __future__ import annotations

import zlib
from typing import Iterable

import numpy as np
import pandas as pd

from src.shoreline_remediation import scenario_composer as sc

Z90 = 1.6448536269514722


def _rng(seed: int, *keys: Iterable[object]) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence([seed] + [zlib.crc32(str(k).encode()) for k in keys]))


def bayesian_block_posterior(prior_mean: float, prior_var: float, sample_mean: float, likelihood_var: float) -> tuple[float, float]:
    """Normal-normal conjugate posterior for a latent shared block residual."""
    pv = max(float(prior_var), 1e-12)
    lv = max(float(likelihood_var), 1e-12)
    post_var = 1.0 / ((1.0 / pv) + (1.0 / lv))
    post_mean = post_var * ((float(prior_mean) / pv) + (float(sample_mean) / lv))
    return float(post_mean), float(post_var)


def _mean_oil_excess_draws(max_oiling: pd.Series, horizon_years: int, n_draws: int, seed: int) -> np.ndarray:
    hv = (max_oiling.to_numpy() == sc.HEAVY).astype(float)
    if hv.sum() == 0:
        return np.zeros((n_draws, len(max_oiling)))
    y1 = min(horizon_years, 2)
    y2 = max(0, horizon_years - 2)
    oil = sc._oil_excess()
    r = _rng(seed, "oil")
    d1 = sc._normal_from_interval(r, oil["2010-2012"][1], oil["2010-2012"][2], n_draws, effect=oil["2010-2012"][0])
    d2 = sc._normal_from_interval(r, oil["2012-2018"][1], oil["2012-2018"][2], n_draws, effect=oil["2012-2018"][0])
    mean_draw = (y1 * d1 + y2 * d2) / float(horizon_years)
    return mean_draw[:, None] * hv[None, :]


def _mean_oil_effect(max_oiling: pd.Series, horizon_years: int) -> np.ndarray:
    oil = sc._oil_excess()
    y1 = min(horizon_years, 2)
    y2 = max(0, horizon_years - 2)
    mean_heavy = (y1 * oil["2010-2012"][0] + y2 * oil["2012-2018"][0]) / float(horizon_years)
    hv = (max_oiling.to_numpy() == sc.HEAVY).astype(float)
    return hv * mean_heavy


def _q(x: np.ndarray) -> tuple[float, float, float]:
    a = np.percentile(x, [50, 5, 95])
    return float(a[0]), float(a[1]), float(a[2])


def update_block(
    block_cells: pd.DataFrame,
    monitored_observations: pd.DataFrame,
    residual_pools: tuple[np.ndarray, np.ndarray],
    horizon_years: int = 5,
    n_draws: int = 2000,
    seed: int = 20261114,
    observation_col: str = "observed_rate",
) -> pd.DataFrame:
    """Update block-shared residual from monitored cells and forecast unmonitored cells."""
    required = {"cell", "pred_rate", "max_oiling"}
    miss = required - set(block_cells.columns)
    if miss:
        raise ValueError(f"block_cells missing columns: {sorted(miss)}")
    if n_draws < 10:
        raise ValueError("n_draws must be >= 10")

    cells = block_cells.copy()
    cells["cell"] = cells["cell"].astype(str)
    obs = monitored_observations.copy()
    obs["cell"] = obs["cell"].astype(str)
    if observation_col not in obs.columns:
        raise ValueError(f"monitored_observations missing observation column '{observation_col}'")

    monitored = cells.merge(obs[["cell", observation_col]], on="cell", how="inner", suffixes=("", "_mon"))
    monitored_ids = set(monitored["cell"].tolist()) if len(monitored) else set()

    target = cells[~cells["cell"].isin(monitored_ids)].copy()
    if target.empty:
        return pd.DataFrame(columns=[
            "cell", "max_oiling", "prior_median", "prior_lo90", "prior_hi90", "updated_median", "updated_lo90", "updated_hi90",
            "prior_width", "updated_width", "prior_covered", "updated_covered", "n_monitored", "posterior_mean", "posterior_sd",
            "prior_block_mean", "prior_block_sd"
        ])

    bpool = np.asarray(residual_pools[0], float)
    wpool = np.asarray(residual_pools[1], float)
    if len(bpool) == 0 or len(wpool) == 0:
        raise ValueError("residual pools must be non-empty")

    prior_mean = float(np.mean(bpool))
    prior_var = float(np.var(bpool, ddof=1)) if len(bpool) > 1 else 0.0
    within_var = float(np.var(wpool, ddof=1)) if len(wpool) > 1 else 0.0

    n_monitored = len(monitored)
    if n_monitored > 0:
        oil_det = _mean_oil_effect(monitored["max_oiling"], horizon_years)
        residuals = monitored[observation_col].to_numpy(float) - monitored["pred_rate"].to_numpy(float) - oil_det
        sample_mean = float(np.mean(residuals))
        post_mean, post_var = bayesian_block_posterior(prior_mean, prior_var, sample_mean, within_var / float(n_monitored))
    else:
        post_mean, post_var = prior_mean, max(prior_var, 0.0)

    r = _rng(seed, "adaptive-block")
    prior_block = r.choice(bpool, n_draws)
    if n_monitored == 0:
        updated_block = prior_block.copy()
    else:
        updated_block = r.normal(post_mean, np.sqrt(max(post_var, 1e-12)), n_draws)

    oil_draw = _mean_oil_excess_draws(target["max_oiling"], horizon_years, n_draws=n_draws, seed=seed)
    within = r.choice(wpool, (n_draws, len(target)))
    pred = target["pred_rate"].to_numpy(float)[None, :]

    prior_draws = pred + oil_draw + prior_block[:, None] + within
    updated_draws = pred + oil_draw + updated_block[:, None] + within

    rows = []
    obs_lookup = target.set_index("cell")["observed_rate"].to_dict() if "observed_rate" in target.columns else {}
    for j, row in enumerate(target.itertuples(index=False)):
        p50, plo, phi = _q(prior_draws[:, j])
        u50, ulo, uhi = _q(updated_draws[:, j])
        out = {
            "cell": row.cell,
            "max_oiling": row.max_oiling,
            "prior_median": p50,
            "prior_lo90": plo,
            "prior_hi90": phi,
            "updated_median": u50,
            "updated_lo90": ulo,
            "updated_hi90": uhi,
            "prior_width": phi - plo,
            "updated_width": uhi - ulo,
            "n_monitored": n_monitored,
            "posterior_mean": float(post_mean),
            "posterior_sd": float(np.sqrt(max(post_var, 0.0))),
            "prior_block_mean": prior_mean,
            "prior_block_sd": float(np.sqrt(max(prior_var, 0.0))),
        }
        obs_val = obs_lookup.get(str(row.cell), np.nan)
        out["observed_rate"] = float(obs_val) if pd.notna(obs_val) else np.nan
        out["prior_covered"] = bool(plo <= obs_val <= phi) if pd.notna(obs_val) else np.nan
        out["updated_covered"] = bool(ulo <= obs_val <= uhi) if pd.notna(obs_val) else np.nan
        rows.append(out)

    return pd.DataFrame(rows)
