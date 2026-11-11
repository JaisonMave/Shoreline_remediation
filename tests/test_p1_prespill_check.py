"""P1 analysis recovers a known pre-existing trend and a known oil effect from simulated cells."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from validation import p1_prespill_check as p1  # noqa: E402


def simulate(tmp_path, pre_gap, oil_effect, seed=0):
    rng = np.random.default_rng(seed)
    cells, land, ls = [], [], []
    for b in range(50):
        shift, water = rng.normal(0, 0.5), rng.uniform(0.2, 0.8)
        for i in range(25):
            cls = rng.choice(["NOO", "Heavy", "Moderate"], p=[0.6, 0.25, 0.15])
            heavy = cls == "Heavy"
            base = 0.5 + shift + water
            r_ab = base + (pre_gap if heavy else 0) + rng.normal(0, 0.4)
            r_bc = base + (pre_gap if heavy else 0) + (oil_effect if heavy else 0) + rng.normal(0, 0.4)
            fa = rng.uniform(0.5, 0.8); fb = fa - r_ab * 9 / 100; fc = fb - r_bc * 7 / 100
            cid = f"{b}_{i}"
            cells.append({"cell": cid, "max_oiling": cls, "cell_2km": str(b), "water_1km_2010": water})
            land.append({"cell": cid, "year": 2010, "land_fraction": 0.5, "valid_fraction": 1.0})
            for e, f in zip("ABC", (fa, fb, fc)):
                ls.append({"cell": cid, "epoch": e, "land_fraction": f, "valid_fraction": 1.0})
    naip = tmp_path / "naip"; naip.mkdir()
    pd.DataFrame(cells).to_csv(naip / "cells_10A.csv", index=False)
    pd.DataFrame(land).to_csv(naip / "cell_land_by_year.csv", index=False)
    pd.DataFrame(ls).to_csv(tmp_path / "landsat_cell_fraction.csv", index=False)
    return naip


def test_recovers_pre_trend_and_oil_effect(tmp_path):
    naip = simulate(tmp_path, pre_gap=0.6, oil_effect=1.0)
    d = p1.landsat_panel(tmp_path, naip)
    c1 = p1.heavy_row("1", d.assign(rate=d.rate_BC))
    c2 = p1.heavy_row("2", d.assign(rate=d.rate_AB))
    c3 = p1.heavy_row("3", d.assign(rate=d.rate_BC - d.rate_AB))
    assert abs(c1["heavy_effect"] - 1.6) < 0.25
    assert abs(c2["heavy_effect"] - 0.6) < 0.25 and c2["excludes_zero"]
    assert abs(c3["heavy_effect"] - 1.0) < 0.3 and c3["lo"] < 1.0 < c3["hi"]


def test_judge_rules():
    ok = {"excludes_zero": True, "heavy_effect": 1.0}
    flat = {"excludes_zero": False, "heavy_effect": 0.1}
    assert p1.judge(ok, flat, ok).startswith("Holds")
    assert p1.judge(ok, {"excludes_zero": True, "heavy_effect": 0.6}, ok).startswith("Revised: part")
    assert p1.judge(flat, flat, ok).startswith("Inconclusive")
