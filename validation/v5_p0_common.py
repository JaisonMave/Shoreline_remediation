"""Shared helpers for the V5 Phase 0 checks (plan: docs/V5_P0_PLAN.md). No analysis runs on import.

Used by validation/v5_p0_oil_excess.py (Part 0.1) and validation/v5_p0_intervals.py (Part 0.2).
Reads committed tables only:
    data/demo/p5_sites_clean_lobo.csv  clean-edge baseline leave-one-basin-out predictions (lobo_pred_clean)
    data/demo/p5_sites.csv             deployed p5-edge-loss-v1 inputs and leave-one-basin-out predictions (lobo_pred)
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN_LOBO = ROOT / "data" / "demo" / "p5_sites_clean_lobo.csv"
SITES = ROOT / "data" / "demo" / "p5_sites.csv"
RESULTS = ROOT / "results" / "v5_p0"
BASINS = ("terrebonne", "barataria", "breton")
CLASSES = ("NOO", "Very_Light", "Light", "Moderate", "Heavy")
EXCESS_CLASSES = ("Heavy", "Moderate", "Light")     # plan 0.1 choice 5
CLEAN_CLASSES = ("NOO", "Very_Light")               # clean-edge baseline training classes
FEATURES = ["water_1km_2010", "water_250m_2010", "fetch_mean_m", "pre_rate"]
FETCH_OFFSET = 16.0
SEED = 20261114
N_BOOT = 2000
ALPHA = 0.10
MIN_CAL_CELLS = 100


def load_cells() -> pd.DataFrame:
    """All 12,696 in-scope cells: basin, block, class, observed rate, both LOBO predictions and the four inputs."""
    c = pd.read_csv(CLEAN_LOBO, dtype={"cell": str, "cell_2km": str})
    s = pd.read_csv(SITES, dtype={"cell": str, "segment": str, "cell_2km": str})
    s = s[s.status == "in_scope"][["cell", "lobo_pred", *FEATURES]]
    d = c.merge(s, on="cell", how="left", validate="one_to_one")
    if len(d) != len(c) or d[["lobo_pred", *FEATURES]].isna().any().any():
        raise RuntimeError("p5_sites.csv and p5_sites_clean_lobo.csv do not describe the same in-scope cells")
    # plan: a block is (basin, cell_2km), so no block is split between training and test
    d["block"] = d.basin + "|" + d.cell_2km
    return d


# ---------------------------------------------------------------------------------------------------------------
# Part 0.1: within-block excess
def block_table(d: pd.DataFrame, cls: str) -> pd.DataFrame:
    """Per contributing block: basin, block, n_c, n_noo, mean difference (class cls minus NOO), weight."""
    sub = d[d.max_oiling.isin([cls, "NOO"])]
    g = sub.groupby(["basin", "block", "max_oiling"]).observed_rate.agg(["mean", "size"]).unstack("max_oiling")
    if cls not in g["size"].columns or "NOO" not in g["size"].columns:
        return pd.DataFrame(columns=["basin", "block", "n_c", "n_noo", "diff", "w"])
    t = pd.DataFrame({"n_c": g["size"][cls], "n_noo": g["size"]["NOO"],
                      "diff": g["mean"][cls] - g["mean"]["NOO"]}).dropna().reset_index()
    t["w"] = t.n_c * t.n_noo / (t.n_c + t.n_noo)
    return t


def weighted_excess(t: pd.DataFrame) -> float:
    """Block-fixed-effects estimate: weighted mean of block differences; 0.0 if no block contributes (plan 0.1.4)."""
    if len(t) == 0:
        return 0.0
    return float(np.sum(t.w * t["diff"]) / np.sum(t.w))


def bootstrap_excess(t: pd.DataFrame, rng: np.random.Generator, n_boot: int = N_BOOT) -> np.ndarray:
    """Resample contributing blocks with replacement within each basin (stratified), recompute the excess."""
    if len(t) == 0:
        return np.zeros(n_boot)
    parts = [g[["diff", "w"]].to_numpy() for _, g in t.groupby("basin")]
    out = np.empty(n_boot)
    for i in range(n_boot):
        num = den = 0.0
        for p in parts:
            k = rng.integers(0, len(p), len(p))
            num += float(np.sum(p[k, 0] * p[k, 1]))
            den += float(np.sum(p[k, 1]))
        out[i] = num / den
    return out


def class_excess(train: pd.DataFrame, classes=EXCESS_CLASSES) -> dict:
    """{class: excess} from the given (training) cells."""
    return {c: weighted_excess(block_table(train, c)) for c in classes}


def add_excess(d: pd.DataFrame, excess: dict) -> np.ndarray:
    return d.max_oiling.map(lambda c: excess.get(c, 0.0)).to_numpy(float)


# ---------------------------------------------------------------------------------------------------------------
# Part 0.2: OLS refits, conformal offsets, Winkler score
def design(d: pd.DataFrame) -> np.ndarray:
    return np.column_stack([np.ones(len(d)), d.water_1km_2010, d.water_250m_2010,
                            np.log(d.fetch_mean_m + FETCH_OFFSET), d.pre_rate]).astype(float)


def fit_ols(d: pd.DataFrame) -> np.ndarray:
    beta, *_ = np.linalg.lstsq(design(d), d.observed_rate.to_numpy(float), rcond=None)
    return beta


def predict_ols(beta: np.ndarray, d: pd.DataFrame) -> np.ndarray:
    return design(d) @ beta


def conformal_offsets(resid, alpha: float = ALPHA) -> tuple[float, float]:
    """Split-conformal offsets with the finite-sample rank correction (plan 0.2.3), each tail alpha/2."""
    r = np.sort(np.asarray(resid, float))
    n = len(r)
    k_lo = math.floor((alpha / 2) * (n + 1))
    k_hi = math.ceil((1 - alpha / 2) * (n + 1))
    lo = -np.inf if k_lo < 1 else float(r[k_lo - 1])
    hi = np.inf if k_hi > n else float(r[k_hi - 1])
    return lo, hi


def class_offsets(resid: np.ndarray, classes: np.ndarray, min_cells: int = MIN_CAL_CELLS) -> dict:
    """{class: (lo, hi, n_cal, fallback)} plus key '__all__'. Classes with < min_cells use the all-class offsets."""
    resid, classes = np.asarray(resid, float), np.asarray(classes)
    lo_all, hi_all = conformal_offsets(resid)
    out = {"__all__": (lo_all, hi_all, int(len(resid)), False)}
    for c in CLASSES:
        r = resid[classes == c]
        if len(r) >= min_cells:
            lo, hi = conformal_offsets(r)
            out[c] = (lo, hi, int(len(r)), False)
        else:
            out[c] = (lo_all, hi_all, int(len(r)), True)
    return out


def winkler(lo, hi, y, alpha: float = ALPHA) -> np.ndarray:
    lo, hi, y = (np.asarray(v, float) for v in (lo, hi, y))
    return (hi - lo) + (2 / alpha) * np.clip(lo - y, 0, None) + (2 / alpha) * np.clip(y - hi, 0, None)
