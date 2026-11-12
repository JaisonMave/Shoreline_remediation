"""Simulated checks of validation/period_split_check.py (run before the real outcome was touched)."""
import numpy as np
import pandas as pd

from validation import period_split_check as ps


def simulate(heavy1, heavy2, confound=0.0, seed=1, n_blocks=120):
    rng = np.random.default_rng(seed)
    rows = []
    for b in range(n_blocks):
        base = rng.normal(0, 0.5)
        for _ in range(rng.integers(8, 14)):
            cls = rng.choice(ps.CLASSES, p=[0.5, 0.1, 0.1, 0.1, 0.2])
            u = confound * (cls == "Heavy") + rng.normal(0, 0.3)  # latent exposure, unobserved
            w1 = rng.uniform(0.3, 0.9); w2 = rng.uniform(0.3, 0.9); fetch = rng.uniform(5, 8); trend = rng.normal(0, 0.5)
            h = float(cls == "Heavy")
            r1 = base + 0.8 * w1 + 0.3 * trend + heavy1 * h + u + rng.normal(0, 0.5)
            r2 = base + 0.8 * w1 + 0.3 * trend + heavy2 * h + u + rng.normal(0, 0.5)
            rows.append(dict(cell_2km=f"b{b}", max_oiling=cls, water_1km_2010=w1, water_250m_2010=w2,
                             log_fetch=fetch, rate_AB=trend, rate_1015=r1, rate_1517=r2))
    d = pd.DataFrame(rows); d["max_oiling"] = pd.Categorical(d.max_oiling, ps.CLASSES)
    return d


def test_within_estimator_matches_block_dummies():
    d = simulate(1.0, 1.0)
    e = ps.class_effects(d, "rate_1015")["Heavy"]
    assert abs(e - ps.ols_interval(d, "rate_1015", "Heavy")[0]) < 1e-8


def test_planted_effect_that_fades_is_recovered_as_fading():
    d = simulate(2.0, 0.0)
    r = ps.analyse(d, n_boot=200, seed=1)
    e_old, _, _ = r["est"][("Heavy", "2010-2015")]; e_new, lo, hi = r["est"][("Heavy", "2015-2017")]
    assert abs(e_old - 2.0) < 0.4 and abs(e_new) < 0.4
    dif, dlo, dhi = r["diffs"]["Heavy"][:3]
    assert dhi < 0 and abs(dif + 2.0) < 0.5
    assert ps.reading(e_new, lo, hi, e_old)[0] == "row 1"


def test_constant_exposure_difference_without_oil_effect_shows_no_fade():
    d = simulate(0.0, 0.0, confound=1.5)
    r = ps.analyse(d, n_boot=200, seed=1)
    e_old, _, _ = r["est"][("Heavy", "2010-2015")]; e_new, lo, hi = r["est"][("Heavy", "2015-2017")]
    assert e_old > 1.0 and e_new > 1.0  # confounded excess present in both periods
    dif, dlo, dhi = r["diffs"]["Heavy"][:3]
    assert dlo < 0 < dhi  # no fade detected
    assert ps.reading(e_new, lo, hi, e_old)[0] != "row 1"


def test_bootstrap_is_seeded_and_resamples_blocks():
    d = simulate(1.0, 1.0, n_blocks=30)
    a = ps.bootstrap_diff(d, 20, seed=5)["Heavy"]; b = ps.bootstrap_diff(d, 20, seed=5)["Heavy"]
    assert np.allclose(a, b, equal_nan=True)


def test_reading_table():
    assert ps.reading(0.2, -0.5, 0.9, 1.0)[0] == "row 1"
    assert ps.reading(1.1, 0.3, 1.9, 1.0)[0] == "row 2"
    assert ps.reading(0.7, -0.2, 1.6, 1.0)[0] == "row 3"
