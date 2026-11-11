"""Tests for the satellite recovery analysis, on simulated series with a known impact.

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

from src.shoreline_remediation.recovery_timeseries import fit_recovery, monthly_medians, placebo_test  # noqa: E402


def simulate(drop: float, tau: float, seed: int = 0, noise: float = 0.02, loss: float = 0.0) -> pd.DataFrame:
    """Monthly NDVI for an oiled and a reference site, 2003-2016, spill in April 2010. Both sites share a
    seasonal cycle and weather; the difference has correlated noise; about 30% of months are lost to cloud."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2003-01-01", "2016-12-01", freq="MS")
    t = dates.year + (dates.dayofyear - 1) / 365.25
    shared = 0.55 + 0.15 * np.sin(2 * np.pi * (t - 0.3)) + rng.normal(0, 0.03, len(t))
    errors = np.zeros(len(t))
    for i in range(1, len(t)):
        errors[i] = 0.5 * errors[i - 1] + rng.normal(0, noise)
    spill = 2010 + 110 / 365.25
    impact = np.where(t >= spill, -loss - drop * np.exp(-(t - spill) / tau), 0.0)
    frame = pd.DataFrame({"date": dates, "reference": shared, "oiled": shared - 0.03 + impact + errors})
    return frame[rng.random(len(frame)) > 0.3].reset_index(drop=True)


def test_known_impact_is_recovered():
    estimate = fit_recovery(simulate(drop=0.20, tau=1.0), "2010-04-20", n_boot=100)
    assert estimate.drop == pytest.approx(0.20, abs=0.05)
    assert estimate.years_to_90pct_recovery == pytest.approx(2.3, abs=0.8)
    assert estimate.drop_interval[0] < 0.20 < estimate.drop_interval[1]
    assert estimate.drop_in_noise_sd > 3


def test_no_impact_gives_no_clear_signal():
    estimate = fit_recovery(simulate(drop=0.0, tau=1.0, seed=4), "2010-04-20", n_boot=100)
    assert abs(estimate.drop) < 0.05
    assert estimate.drop_interval[0] < 0 < estimate.drop_interval[1] or abs(estimate.drop_in_noise_sd) < 2


def test_real_impact_stands_out_from_placebos():
    table = placebo_test(simulate(drop=0.20, tau=1.0), "2010-04-20")
    real = table.loc[table["kind"] == "real", "impact_2yr"].iloc[0]
    assert real > 2 * table.loc[table["kind"] == "placebo", "impact_2yr"].abs().max()


def test_monthly_medians_drops_sparse_images():
    observations = pd.DataFrame({
        "date": ["2010-05-03", "2010-05-19", "2010-05-03", "2010-06-04", "2010-06-04"],
        "site": ["oiled", "oiled", "reference", "oiled", "reference"],
        "ndvi": [0.40, 0.50, 0.60, 0.45, 0.62],
        "pixels": [40, 40, 40, 5, 40],
    })
    table = monthly_medians(observations)
    assert len(table) == 1 and table["oiled"].iloc[0] == pytest.approx(0.45)


def test_persistent_loss_is_separated_from_recovery():
    """Part of the impact never recovers. The plain model has to absorb it as a very slow recovery; the
    persistent model returns both parts."""
    series = simulate(drop=0.15, tau=0.8, loss=0.08, seed=2)
    plain = fit_recovery(series, "2010-04-20", n_boot=50)
    lasting = fit_recovery(series, "2010-04-20", n_boot=100, persistent=True)
    assert plain.years_to_90pct_recovery > 10
    assert lasting.persistent_loss == pytest.approx(0.08, abs=0.03)
    assert lasting.persistent_loss_interval[0] > 0
    assert lasting.drop == pytest.approx(0.15, abs=0.05)
    assert lasting.years_to_90pct_recovery < 4


def test_persistent_model_finds_no_loss_when_recovery_is_complete():
    lasting = fit_recovery(simulate(drop=0.20, tau=1.0), "2010-04-20", n_boot=100, persistent=True)
    assert abs(lasting.persistent_loss) < 0.03
    assert lasting.persistent_loss_interval[0] < 0.02
