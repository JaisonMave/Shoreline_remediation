"""P2 hold-out machinery on simulated basins: a real oil effect transfers; noise does not beat the baseline."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from validation import p2_basin_holdout as p2  # noqa: E402


def simulate(oil_effect, exposure_effect, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for b in p2.BASINS:
        shift = rng.normal(0, 0.1)
        for k in range(600):
            cls = rng.choice(["NOO", "Light", "Heavy"], p=[0.7, 0.15, 0.15])
            w1, w250, lf, pre = rng.uniform(0.2, 0.9), rng.uniform(0.1, 0.9), rng.normal(6.5, 0.8), rng.normal(0.5, 0.4)
            rate = 0.3 + shift + exposure_effect * w250 + 0.5 * pre + (oil_effect if cls == "Heavy" else 0) + rng.normal(0, 0.6)
            rows.append({"cell": f"{b}{k}", "basin": b, "cell_2km": f"{b}{k // 20}", "max_oiling": cls,
                         "water_1km_2010": w1, "water_250m_2010": w250, "log_fetch": lf, "pre_rate": pre, "rate": rate})
    return pd.DataFrame(rows)


def test_real_effect_transfers():
    res = p2.run(simulate(oil_effect=1.0, exposure_effect=1.5))
    assert res["pooled"]["MAE_M2"] < res["pooled"]["MAE_M1"] < res["pooled"]["MAE_M0"]
    assert 0.85 <= res["pooled"]["coverage_90"] <= 0.95
    t = res["transfer"]
    assert ((t.train_heavy_coef - 1.0).abs() < 0.25).all()
    assert p2.judge(res).startswith("Transfers")


def test_pure_noise_does_not_transfer():
    d = simulate(oil_effect=0.0, exposure_effect=0.0)
    d["rate"] = np.random.default_rng(9).normal(1.0, 0.6, len(d))
    res = p2.run(d)
    assert res["pooled"]["skill_M2"] < 0.02
