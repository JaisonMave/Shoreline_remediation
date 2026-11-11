"""The edge-loss analysis recovers a known effect from simulated cells."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from validation.naip_edge_loss import cell_rates, fit  # noqa: E402


def simulate(tmp_path, heavy_extra=1.5, seed=0):
    rng = np.random.default_rng(seed)
    n_blocks, per = 40, 30
    cells, land = [], []
    for b in range(n_blocks):
        block_shift = rng.normal(0, 0.8)           # some blocks erode faster
        water = rng.uniform(0.2, 0.8)
        for i in range(per):
            cls = rng.choice(["NOO", "Heavy", "Light"], p=[0.6, 0.25, 0.15])
            rate = 1.0 + block_shift + 1.0 * water + (heavy_extra if cls == "Heavy" else 0) + rng.normal(0, 0.5)
            f10 = rng.uniform(0.3, 0.7); yrs = 4.8
            cid = f"{b}_{i}"
            cells.append({"cell": cid, "max_oiling": cls, "cell_2km": str(b), "water_1km_2010": water})
            for y, f, date in [(2010, f10, "2010-06-15"), (2015, f10 - rate * yrs / 100, "2015-04-01")]:
                land.append({"cell": cid, "year": y, "land_fraction": f, "valid_fraction": 1.0, "flight_date": date,
                             "block": str(b), "block_land_fraction": 0.4})
    pd.DataFrame(cells).to_csv(tmp_path / "cells_10A.csv", index=False)
    pd.DataFrame(land).to_csv(tmp_path / "cell_land_by_year.csv", index=False)


def test_recovers_known_heavy_effect(tmp_path):
    simulate(tmp_path, heavy_extra=1.5)
    d = cell_rates(tmp_path, 2015)
    m = fit(d, "rate ~ C(max_oiling, Treatment('NOO')) + water_1km_2010 + C(cell_2km)")
    est = m.params["C(max_oiling, Treatment('NOO'))[T.Heavy]"]
    lo, hi = m.conf_int(alpha=0.10).loc["C(max_oiling, Treatment('NOO'))[T.Heavy]"]
    assert abs(est - 1.5) < 0.2 and lo < 1.5 < hi


def test_null_effect_interval_covers_zero(tmp_path):
    simulate(tmp_path, heavy_extra=0.0, seed=3)
    d = cell_rates(tmp_path, 2015)
    m = fit(d, "rate ~ C(max_oiling, Treatment('NOO')) + water_1km_2010 + C(cell_2km)")
    lo, hi = m.conf_int(alpha=0.10).loc["C(max_oiling, Treatment('NOO'))[T.Heavy]"]
    assert lo < 0 < hi
