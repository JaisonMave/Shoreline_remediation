"""Tests for the panel event study, on simulated panels with a known effect.

Run from the repository root:  python -m pytest tests
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.shoreline_remediation.event_study import event_study  # noqa: E402

TRUE_EFFECT = {0: -10.0, 1: -5.0, 2: -2.5}  # effect by years since the event; zero afterwards


def simulate(seed: int = 0, n_sites: int = 240, diverging: float = 0.0) -> pd.DataFrame:
    """Sites surveyed yearly 2004-2016, event before the 2010 survey. Each site has its own level and its
    own year-to-year persistence; all sites share year shocks. `diverging` adds a trend to exposed sites
    only, which breaks the parallel-trends assumption."""
    rng = np.random.default_rng(seed)
    rows = []
    year_shock = dict(zip(range(2004, 2017), rng.normal(0, 4, 13)))
    for site in range(n_sites):
        exposed = site % 2 == 0
        level, noise = rng.normal(70, 10), 0.0
        for year in range(2004, 2017):
            noise = 0.4 * noise + rng.normal(0, 5)
            effect = TRUE_EFFECT.get(year - 2010, 0.0) if exposed else 0.0
            rows.append({"site": f"S{site}", "year": year, "exposed": exposed, "first_post": 2010,
                         "cover": level + year_shock[year] + effect + noise + (diverging * (year - 2004) if exposed else 0.0)})
    return pd.DataFrame(rows)


def test_known_effects_are_recovered():
    result = event_study(simulate(), "cover", "exposed", "first_post", leads=4, lags=5)
    effects = result.effects.set_index("event_time")
    for k, truth in TRUE_EFFECT.items():
        assert effects.loc[k, "estimate"] == pytest.approx(truth, abs=2.5)
        assert effects.loc[k, "ci_low"] < truth < effects.loc[k, "ci_high"]
    assert abs(effects.loc[4, "estimate"]) < 2.5
    assert result.pretrend_p_value > 0.01
    assert result.n_exposed_sites == 120 and result.n_control_sites == 120
    assert result.recovery_lag() in (2, 3)


def test_intervals_have_the_stated_coverage():
    """Across repeated simulations the 90% interval should contain the truth about 90% of the time."""
    hits = [r.loc[0, "ci_low"] < TRUE_EFFECT[0] < r.loc[0, "ci_high"]
            for r in (event_study(simulate(seed), "cover", "exposed", "first_post").effects.set_index("event_time")
                      for seed in range(60))]
    assert 0.80 <= np.mean(hits) <= 0.98


def test_diverging_sites_fail_the_pretrend_check():
    result = event_study(simulate(diverging=1.5), "cover", "exposed", "first_post", leads=4, lags=5)
    assert result.pretrend_p_value < 0.01


def test_no_effect_gives_no_recovery_lag():
    data = simulate(seed=3)
    data["exposed"] = data["site"].str[1:].astype(int) % 4 < 2  # exposure unrelated to the simulated effect
    data["cover"] = data["cover"] - data.apply(lambda r: TRUE_EFFECT.get(r["year"] - 2010, 0.0) if int(r["site"][1:]) % 2 == 0 else 0.0, axis=1)
    result = event_study(data, "cover", "exposed", "first_post")
    assert result.recovery_lag() is None
