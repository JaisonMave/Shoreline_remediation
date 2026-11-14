"""V4 R7 sensitivity B: PAH replicate rule (not a change to any default).

src/shoreline_remediation/diver_soil.py pick_value() keeps, when two replicates differ by more than
RPD_LIMIT (50%), the value nearer the station-campaign median (and drops the farthest of 3+). This
script reruns validation/pah_decline.py's primary analysis with an alternative replicate rule: the
plain mean of the replicates (unchanged: a detect still outranks a non-detect replicate -- that
logic lives outside pick_value() and is not touched). The alternative rule is applied via a
monkeypatch of diver_soil.pick_value for the duration of this script only; no default in
diver_soil.py or pah_decline.py is changed.

Needs the DIVER files under data/external/diver_dwh/ (git-ignored). If they are absent, this script
does not download them; it reports "not run" and exits cleanly (writes no CSV).

Run:    python -m validation.v4_r7_pah_replicate_sensitivity
Writes: results/v4_r7/pah_replicate_sensitivity.csv (only if the DIVER files are present)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

RESULTS = ROOT / "results" / "v4_r7"
DIVER_DIR = ROOT / "data" / "external" / "diver_dwh" / "extracted_csv"
SCAT_SHP = ROOT / "data" / "raw" / "scat" / "18611" / "SCAT_Max_OilZones_Louisiana_2014_09_30Sorted.shp"
NOT_RUN_MSG = "not run: DIVER files absent; fetch with scripts/download_diver.sh"


def mean_rule_pick_value(values, ref_median: float, limit: float = 50.0) -> tuple[float, str]:
    """Alternative replicate rule: plain mean of replicates, regardless of RPD. Detects-vs-non-detects
    are already resolved before pick_value() is called, so that part of the rule is unaffected."""
    v = np.asarray(values, float)
    return float(v.mean()), "mean"


def find_diver_files() -> Path | None:
    if not DIVER_DIR.is_dir():
        return None
    from src.shoreline_remediation.diver_soil import CAMPAIGN_FILES
    if not all((DIVER_DIR / fname).exists() for fname in CAMPAIGN_FILES.values()):
        return None
    if not SCAT_SHP.exists():
        return None
    return DIVER_DIR


def run_variant(diver_dir: Path, patch_pick_value: bool) -> dict:
    """Runs pah_decline's half-life + M0/M1 primary analysis once, optionally with the mean-rule patch."""
    from src.shoreline_remediation import diver_soil as ds
    from validation import pah_decline as pd_

    pick_value_impl = mean_rule_pick_value if patch_pick_value else ds.pick_value
    original = ds.pick_value
    ds.pick_value = pick_value_impl
    try:
        log = ds.Log()
        prep = ds.prepare(diver_dir, SCAT_SHP, log)
        _s, sc = ds.build(prep, "tobit", False, log)
        out = {}
        for col, label in pd_.OUTCOMES.items():
            cells = pd_.make_cells(sc, col)
            v = pd_.validate(cells)
            hl = pd_.half_life_table(cells)
            out[col] = {"label": label, "cells": cells, "v": v, "hl": hl}
        return out
    finally:
        ds.pick_value = original


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    diver_dir = find_diver_files()
    if diver_dir is None:
        print(NOT_RUN_MSG)
        return

    primary = run_variant(diver_dir, patch_pick_value=False)
    mean_rule = run_variant(diver_dir, patch_pick_value=True)

    rows = []
    for col, label in [("pah_sum", "PAH sum"), ("ratio", "PAH sum / hopane")]:
        for rule_name, res in [("primary (RPD>50% -> nearer median)", primary), ("alternative (plain mean)", mean_rule)]:
            v, hl = res[col]["v"], res[col]["hl"]
            b = v["boot"]
            for _, h in hl.iterrows():
                rows.append({
                    "outcome": label, "rule": rule_name, "oil_class": h.oil_class,
                    "n_stations": h.n_stations, "n_stations_2plus_campaigns": h.n_stations_2plus_campaigns,
                    "k_per_year": h.k_per_year, "k_lo90": h.k_lo90, "k_hi90": h.k_hi90,
                    "half_life_years": h.half_life_years, "half_life_lo90": h.half_life_lo90, "half_life_hi90": h.half_life_hi90,
                    "MAE_M0": v["MAE_M0"], "MAE_M1": v["MAE_M1"], "diff_M1_minus_M0": b["diff"],
                    "diff_lo90": b["lo"], "diff_hi90": b["hi"], "verdict": b["verdict"],
                })
    out = pd.DataFrame(rows)
    out.to_csv(RESULTS / "pah_replicate_sensitivity.csv", index=False)
    pd.set_option("display.width", 250)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
