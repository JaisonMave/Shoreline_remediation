"""Data layer for the Model validation page (V5.2). No Streamlit, no scientific calculation.

Authority: `registry.governance_table()` is the only source of a model's state, scope, data, baseline, uncertainty and gates.
This module re-shapes that table and reads a few genuine result files that already exist in the repository. Every reader
returns {"available": False, "reason": ...} when its file is missing or unreadable, so the page says "unavailable" instead of
inventing a value. Nothing here promotes, demotes or recomputes a model state or a metric.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

from . import registry

ROOT = Path(__file__).resolve().parents[2]
UNAVAILABLE = "unavailable"
STATE_ORDER = ("validated", "experimental")

HEURISTIC_CONFIDENCE_NOTE = ("The confidence or uncertainty score produced by scenario_runner.py is a heuristic. It is not a calibrated "
                             "probability and must not be read as one. Only intervals whose method, level and validation status are "
                             "shown beside them (below) carry that information.")

# Definitions of the P2 hold-out models, copied from docs/P2_BASIN_HOLDOUT_PLAN.md (the plan that defines them).
P2_MODEL_DEFINITIONS = {"M0": "no-predictor baseline (mean rate of the training basins)",
                        "M1": "exposure only (water 1 km and 250 m, log fetch, pre-spill rate)",
                        "M2": "M1 plus oiling class"}


def _read_csv(rel: str):
    path = ROOT / rel
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        return None, f"{rel} could not be read ({type(exc).__name__})"
    return (df, "") if len(df) else (None, f"{rel} is empty")


def _missing(reason: str, source: str) -> dict:
    return {"available": False, "reason": reason, "source": source}


# ---------------------------------------------------------------------------------------------------------------
# Inventory (registry is authoritative)

@lru_cache(maxsize=1)
def inventory() -> tuple:
    """One dict per registered model or card, in registry order, with the registry's own state. Adds counts only."""
    out = []
    for row in registry.governance_table():
        gates = row["gates"]
        out.append({**row, "n_gates": len(gates), "n_gates_failed": sum(1 for g in gates if not g.get("passed")),
                    "gap_count": len(row["governance_gaps"])})
    return tuple(out)


def state_counts() -> dict:
    counts: dict = {}
    for m in inventory():
        counts[m["state"]] = counts.get(m["state"], 0) + 1
    return counts


def sorted_inventory() -> list:
    """Validated models first, then experimental; stable within a state."""
    rank = {s: i for i, s in enumerate(STATE_ORDER)}
    return sorted(inventory(), key=lambda m: rank.get(m["state"], len(rank)))


# ---------------------------------------------------------------------------------------------------------------
# Result files

def edge_loss_holdout() -> dict:
    """Marsh-edge loss, whole-basin hold-out (P2): MAE of M0, M1, M2 on the held-out basins and pooled, 90% interval coverage."""
    src = "results/p2_basin_holdout/per_basin.csv and pooled.csv"
    per, why = _read_csv("results/p2_basin_holdout/per_basin.csv")
    pooled, why2 = _read_csv("results/p2_basin_holdout/pooled.csv")
    if per is None or pooled is None:
        return _missing(why or why2, src)
    need = {"basin", "tested", "cells", "heavy", "MAE_M0", "MAE_M1", "MAE_M2", "coverage_90"}
    if not need <= set(per.columns) or not {"MAE_M0", "MAE_M1", "MAE_M2", "cells", "coverage_90"} <= set(pooled.columns):
        return _missing("expected columns are missing", src)
    held = per[per["tested"].astype(str).str.lower() == "true"]
    rows = [{"basin": str(r["basin"]), "cells": int(r["cells"]), "heavy": int(r["heavy"]), "MAE_M0": float(r["MAE_M0"]),
             "MAE_M1": float(r["MAE_M1"]), "MAE_M2": float(r["MAE_M2"]), "coverage_90": float(r["coverage_90"])} for _, r in held.iterrows()]
    p = pooled.iloc[0]
    rows.append({"basin": "pooled", "cells": int(p["cells"]), "heavy": None, "MAE_M0": float(p["MAE_M0"]), "MAE_M1": float(p["MAE_M1"]),
                 "MAE_M2": float(p["MAE_M2"]), "coverage_90": float(p["coverage_90"])})
    return {"available": True, "rows": rows, "source": src, "unit": "m per year (mean absolute error)",
            "definitions": P2_MODEL_DEFINITIONS,
            "not_tested": [str(b) for b in per[per["tested"].astype(str).str.lower() != "true"]["basin"]],
            "scope": "Louisiana basins, 2010 to 2015, one spill. Basins listed as not tested were used for training only.",
            "verdict_file": "results/p2_basin_holdout/verdict.txt"}


def pah_holdout() -> dict:
    """Soil PAH-sum decline, whole stations held out: MAE (ln units) of M0 and M1, the difference and its 90% interval."""
    src = "results/pah_decline/summary.csv"
    df, why = _read_csv(src)
    if df is None:
        return _missing(why, src)
    need = {"outcome", "n_heldout_stations", "MAE_M0", "MAE_M1", "diff_M1_minus_M0", "diff_lo90", "diff_hi90", "pi90_coverage"}
    if not need <= set(df.columns):
        return _missing("expected columns are missing", src)
    hit = df[df["outcome"] == "PAH sum"]
    if hit.empty:
        return _missing("no 'PAH sum' row", src)
    r = hit.iloc[0]
    return {"available": True, "source": src, "unit": "ln units (mean absolute error)",
            "heldout_stations": int(r["n_heldout_stations"]), "MAE_M0": float(r["MAE_M0"]), "MAE_M1": float(r["MAE_M1"]),
            "diff": float(r["diff_M1_minus_M0"]), "diff_lo90": float(r["diff_lo90"]), "diff_hi90": float(r["diff_hi90"]),
            "pi90_coverage": float(r["pi90_coverage"]),
            "scope": "Deepwater Horizon marsh soil, 2011 to 2013, one spill. M0 is the no-change baseline."}


_F5_PATTERNS = {"prior": r"^\s*prior\s+([0-9.]+)", "empirical": r"^\s*empirical k\s+([0-9.]+)", "calibrated": r"^\s*calibrated\s+([0-9.]+)"}


def f5_comparison() -> dict:
    """F5 process model against the empirical PAH decline curve, from the numbers printed in results/f5_process/summary.txt."""
    src = "results/f5_process/summary.txt"
    try:
        text = (ROOT / src).read_text(encoding="utf-8")
    except OSError as exc:
        return _missing(f"{src} could not be read ({type(exc).__name__})", src)
    vals = {}
    for name, pat in _F5_PATTERNS.items():
        m = re.search(pat, text, flags=re.M)
        if not m:
            return _missing(f"could not find the '{name}' value", src)
        vals[name] = float(m.group(1))
    stations = re.search(r"stations\s+(\d+),\s*cells\s+(\d+)", text)
    gate_failed = "GATE: FAIL" in text
    return {"available": True, "source": src, "unit": "ln relative PAH (mean absolute error), held-out stations", **vals,
            "stations": int(stations.group(1)) if stations else None, "cells": int(stations.group(2)) if stations else None,
            "gate_failed": gate_failed, "beats_empirical": vals["calibrated"] < vals["empirical"]}


def _gate_number(description: str, pattern: str):
    m = re.search(pattern, description)
    return float(m.group(1)) if m else None


def bias_gates() -> dict:
    """Heavy-cell bias against the +/-0.25 m/yr gate, read from the registry gate descriptions (R3 and D32). Values the registry
    does not state in that wording come back as None and are shown as unavailable."""
    rows = []
    for m in inventory():
        for g in m["gates"]:
            if g["gate_id"] in ("R3-heavy-bias", "D32-heavy-bias"):
                desc = g.get("description", "")
                rows.append({"gate_id": g["gate_id"], "model_id": m["model_id"], "passed": bool(g.get("passed")),
                             "observed": _gate_number(desc, r"observed pooled ([+-]?\d+(?:\.\d+)?)"),
                             "limit": _gate_number(desc, r"\+/-(\d+(?:\.\d+)?)"), "description": desc, "source": g.get("source", "")})
    if not rows or any(r["observed"] is None or r["limit"] is None for r in rows):
        return _missing("bias gate values are not stated in the registry gate descriptions", "models/registry.json")
    return {"available": True, "rows": rows, "unit": "m per year", "source": "models/registry.json (gate descriptions)"}


# ---------------------------------------------------------------------------------------------------------------
# Edge-loss leave-one-basin-out predicted vs observed (V5.3)

SCATTER_MAX_POINTS = 4000
SCATTER_SOURCE = "data/demo/p5_sites.csv (columns lobo_pred and observed_rate; built by scripts/build_p5_demo.py)"
SCATTER_CAPTION = ("Each point is one in-scope marsh-edge cell. The prediction is leave-one-basin-out (trained on the other two basins): "
                   "no cell was predicted by a model that saw its own basin. Unit: m/yr of edge loss, 2010 to 2015. Scope: one spill, "
                   "northern Gulf salt marsh. Terrebonne is out-of-sample here but was not a P2 gate basin (too few heavily oiled cells). "
                   "The deployed model (models/p5_edge_loss_v1.json) is an all-cells refit and is NOT what is plotted. This chart is a "
                   "descriptive check of the hold-out predictions; it is not a new validation and does not change the model's registry state.")


def edge_loss_scatter(path: str = "data/demo/p5_sites.csv") -> dict:
    """Leave-one-basin-out M1 prediction (lobo_pred) against observed_rate, for rows where both are present. Reads only those columns
    (no other prediction column). MAE and n use every such row; `points` is a deterministic downsample for plotting only."""
    df, why = _read_csv(path)
    if df is None:
        return _missing(why, path)
    need = {"basin", "observed_rate", "lobo_pred"}
    if not need <= set(df.columns):
        return _missing("expected columns are missing", path)
    d = df[["basin", "observed_rate", "lobo_pred"]].copy()
    d["observed_rate"] = pd.to_numeric(d["observed_rate"], errors="coerce")
    d["lobo_pred"] = pd.to_numeric(d["lobo_pred"], errors="coerce")
    d = d.dropna(subset=["observed_rate", "lobo_pred"]).reset_index(drop=True)
    if d.empty:
        return _missing("no rows with both a prediction and an observation", path)
    d["abs_error"] = (d["lobo_pred"] - d["observed_rate"]).abs()
    nz = d[d["observed_rate"] != 0]
    pct = (nz["abs_error"] / nz["observed_rate"].abs() * 100.0) if len(nz) else None
    per = [{"basin": str(b), "n": int(len(g)), "MAE": float(g["abs_error"].mean())} for b, g in d.groupby("basin", sort=True)]
    pts = d if len(d) <= SCATTER_MAX_POINTS else d.sample(n=SCATTER_MAX_POINTS, random_state=0)
    lo = min(0.0, float(d[["observed_rate", "lobo_pred"]].min().min()))
    hi = float(d[["observed_rate", "lobo_pred"]].max().max())
    return {"available": True, "source": SCATTER_SOURCE, "unit": "m per year", "n": int(len(d)), "MAE": float(d["abs_error"].mean()),
            "n_nonzero_observed": int(len(nz)), "MAPE_pct": None if pct is None else float(pct.mean()),
            "per_basin": per, "points": pts[["basin", "observed_rate", "lobo_pred"]].reset_index(drop=True),
            "n_plotted": int(len(pts)), "axis_min": lo, "axis_max": hi, "caption": SCATTER_CAPTION}
