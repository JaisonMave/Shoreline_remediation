"""Tests for the sand-beach persistence model (D39): statistics on simulated data, card contract, packaged use."""
import math

import numpy as np
import pytest

from src.shoreline_remediation import beach_model as bm
from src.shoreline_remediation import model_interface as mi
from src.shoreline_remediation.model_interface import ScenarioRequest, SiteRecord


def _sim(n=600, seed=1, beta=0.5):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=n)
    T = rng.exponential(200.0, n) * np.exp(-beta * x)
    L = np.floor(T / 30) * 30
    R = L + 30
    C = rng.uniform(100, 1000, n)  # independent censoring at a visit
    cens = C < R
    L = np.where(cens, np.floor(C / 30) * 30, L)
    R = np.where(cens, np.inf, R)
    return x, T, L, R


def test_gradient_matches_numeric():
    from scipy.optimize import approx_fprime
    x, _, L, R = _sim(200)
    X = np.column_stack([x, x ** 2])
    iv = np.isfinite(R)
    EL, ER = bm.exposure(L), bm.exposure(np.where(iv, R, 0))
    th = np.concatenate([np.full(len(bm.CUTS), -5.0), [0.2, -0.1]])
    f = lambda t: bm._nll(t, X, EL, ER, iv)[0]
    g = bm._nll(th, X, EL, ER, iv)[1]
    assert np.allclose(approx_fprime(th, f, 1e-6), g, atol=1e-2)


def test_fit_recovers_hazard_ratio():
    x, _, L, R = _sim(1500, seed=3)
    th = bm.fit_pe(x[:, None], L, R)
    assert abs(th[len(bm.CUTS)] - 0.5) < 0.12


def test_turnbull_close_to_truth_and_monotone():
    _, T, L, R = _sim(1500, seed=4, beta=0.0)
    s = bm.turnbull_surv(bm.turnbull(L, R))
    true = np.array([np.mean(T > h) for h in bm.HORIZONS])
    assert np.all(np.diff(s) <= 1e-12)
    assert np.max(np.abs(s - true)) < 0.06


def test_exposure_sums_to_time():
    e = bm.exposure([0, 45, 1000, np.inf])
    assert e[0].sum() == 0 and e[1].sum() == 45 and e[2].sum() == 1000 and math.isinf(e[3].sum())


def test_card_contract():
    c = bm.load_card()
    assert "validated" != c["declared_state"] and c["declared_state"].startswith("experimental")
    assert c["packaged_prediction"] == ("model" if c["gates"]["B-1"]["pass"] else "baseline")
    assert set(c["baseline_curves_all_states"]) == set(bm.CAT_LEVELS)
    assert len(c["theta_all_states"]) == len(bm.CUTS) + len(bm.TERMS)
    for k in ("plan", "caveats", "training_range", "per_state_results", "gates"):
        assert k in c


def test_curve_shape_and_flags():
    out = bm.persistence_curve({"first_cat": "Light", "days_spill_to_first_oiled": 60, "esi": "3A", "state": "AL"})
    assert out["horizons_days"] == [90, 180, 365, 730]
    for lo, m, hi in zip(out["lo90"], out["median"], out["hi90"]):
        assert 0 <= lo <= m <= hi <= 1
    assert out["scope_flags"] == []
    assert np.all(np.diff(out["median"]) <= 1e-9)
    bad = bm.persistence_curve({"first_cat": "Light", "days_spill_to_first_oiled": 2000, "esi": "6B", "state": "TX"})
    text = " ".join(bad["scope_flags"])
    assert "ESI not 3A" in text and "state unseen" in text and "outside training range" in text


def test_unknown_category_raises():
    with pytest.raises(ValueError):
        bm.persistence_curve({"first_cat": "Gasoline", "days_spill_to_first_oiled": 60})


def test_adapter_follows_interface():
    a = bm.BeachSandPersistenceAdapter({"model_id": "beach_sand_persistence_v1",
                                        "card": "models/beach_sand_persistence_v1.json"})
    assert isinstance(a, mi.Model) and a.state == mi.STATE_EXPERIMENTAL
    p = a.predict(SiteRecord("s1", habitat="3A", region="FL", oiling="Light_TB",
                             fields={"days_spill_to_first_oiled": 70, "horizon_days": 180}), ScenarioRequest())
    assert p.scope == mi.SCOPE_IN_RANGE and 0 <= p.interval_lo <= p.value <= p.interval_hi <= 1
    q = a.predict(SiteRecord("s2", habitat="3A", region="TX", oiling="Heavy",
                             fields={"days_spill_to_first_oiled": 70}), ScenarioRequest(treatment="tilling"))
    assert q.scope == mi.SCOPE_NEW_REGION
    assert any("treatment 'tilling' ignored" in r for r in q.scope_reasons)
