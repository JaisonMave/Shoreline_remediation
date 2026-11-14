"""Tests for V5 Phase 0.1/0.2 (docs/V5_P0_PLAN.md): results files reproduce the summaries, defaults are unchanged,
and the new options work. Reads committed files only; does not rerun the gated analyses."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.shoreline_remediation import scenario_composer as sc  # noqa: E402
from src.shoreline_remediation import site_evidence as se  # noqa: E402
from validation.v5_p0_common import conformal_offsets, winkler  # noqa: E402

R = ROOT / "results" / "v5_p0"
SITE = {"water_1km_2010": 0.6, "water_250m_2010": 0.5, "fetch_mean_m": 900.0, "pre_rate": 0.5, "max_oiling": "Heavy"}


@pytest.fixture(scope="module")
def ox():
    return pd.read_csv(R / "oil_excess_cells.csv", dtype={"cell": str})


@pytest.fixture(scope="module")
def iv():
    return pd.read_csv(R / "interval_cells.csv", dtype={"cell": str})


def test_known_baseline_numbers(ox):
    h = ox[ox.basin.isin(["barataria", "breton"]) & (ox.max_oiling == "Heavy")]
    e = h.pred_clean - h.observed_rate
    assert len(h) == 532
    assert abs(e.abs().mean() - 1.044) < 1e-3 and abs(e.mean() + 0.475) < 1e-3


def test_oil_excess_gate_reproduces(ox):
    gate = pd.read_csv(R / "oil_excess_gate.csv")
    for g in gate.itertuples():
        c = ox[ox.basin == g.basin]
        h, n = c[c.max_oiling == "Heavy"], c[c.max_oiling == "NOO"]
        assert np.isclose((h.pred_oos - h.observed_rate).abs().mean(), g.mae_oos)
        assert np.isclose((h.pred_clean - h.observed_rate).abs().mean(), g.mae_clean)
        rel = (h.pred_oos - h.observed_rate).mean() - (n.pred_oos - n.observed_rate).mean()
        assert np.isclose(rel, g.heavy_minus_noo_bias_oos)
    gp = gate[gate.gated]
    passed = bool((gp.mae_below & gp.bias_within).all())
    assert ("GATE 0.1: PASSED" if passed else "GATE 0.1: FAILED") in (R / "summary.txt").read_text()
    assert set(gp.basin) == {"barataria", "breton"}


def test_excess_values_in_cells_match_estimates(ox):
    est = pd.read_csv(R / "oil_excess_estimates.csv")
    for r in est[est.held_out_basin != "all_basins_deployable"].itertuples():
        v = ox[(ox.basin == r.held_out_basin) & (ox.max_oiling == r.oiling_class)].excess.unique()
        assert np.allclose(v, r.excess_m_per_yr)
    assert (ox[ox.max_oiling.isin(["NOO", "Very_Light"])].excess == 0).all()


def test_interval_gate_reproduces(iv):
    cov = pd.read_csv(R / "interval_coverage_gate.csv")
    y = iv.observed_rate
    iv = iv.assign(cov=(iv.m1_class_oos_lo <= y) & (y <= iv.m1_class_oos_hi))
    for r in cov.itertuples():
        g = iv[(iv.basin == r.basin) & (iv.max_oiling == r.oiling_class)]
        assert len(g) == r.n_cells >= 100 and np.isclose(g["cov"].mean(), r.m1_class_oos_coverage)
    by_b = pd.read_csv(R / "interval_by_basin.csv").set_index("basin")
    ok = cov.passes.all()
    for b, g in iv.groupby("basin"):
        w = winkler(g.m1_class_oos_lo, g.m1_class_oos_hi, g.observed_rate).mean()
        w0 = winkler(g.m0_lo, g.m0_hi, g.observed_rate).mean()
        assert np.isclose(w, by_b.loc[b, "m1_class_oos_winkler"]) and np.isclose(w0, by_b.loc[b, "m0_winkler"])
        ok = ok and w < w0
    assert ("GATE 0.2: PASSED" if ok else "GATE 0.2: FAILED") in (R / "summary.txt").read_text()


def test_conformal_offsets_rank_rule():
    r = np.arange(1, 100, dtype=float)                 # n = 99: k_lo = floor(5) = 5, k_hi = ceil(95) = 95
    assert conformal_offsets(r) == (5.0, 95.0)
    assert conformal_offsets(np.arange(10.0)) == (-np.inf, np.inf)


def test_cards_state_not_validated():
    for name in ("oil_excess_oos_v1.json", "p5_edge_loss_v2.json"):
        c = json.loads((ROOT / "models" / name).read_text())
        assert c["state"].startswith("experimental") and "validated" not in c["state"]
    reg = (ROOT / "models" / "registry.json").read_text()
    assert "oil_excess_oos_v1" not in reg and "p5_edge_loss_v2" not in reg


def test_v1_card_keeps_history_and_has_note():
    c = json.loads((ROOT / "models" / "p5_edge_loss_v1.json").read_text())
    assert "90% intervals covered 89% of held-out cells." in c["validation"]
    assert "M2" in c["validation"] and "calibrated in sample" in c["interval_calibration_note"]


# ---------------------------------------------------------------------------------------------------------------
# defaults unchanged
def test_site_evidence_default_unchanged():
    m = se.load_model()
    p = se.predict_edge_loss(SITE)
    x = np.array([1, 0.6, 0.5, np.log(900 + 16), 0.5])
    assert set(p) == {"rate", "lo", "hi", "level"} and np.isclose(p["rate"], x @ np.array(m["coefficients"]))
    assert np.isclose(p["hi"] - p["rate"], m["interval_offsets"][1])
    assert se.predict_edge_loss(SITE, oiling="Heavy") == p      # v1 card has no class offsets: option ignored


def test_composer_default_unchanged():
    a, sa = sc.compose(SITE, ["manual_removal"], n_draws=500, seed=7)
    b, sb = sc.compose(SITE, ["manual_removal"], n_draws=500, seed=7, oil_excess_source="default")
    pd.testing.assert_frame_equal(a, b)
    pd.testing.assert_frame_equal(sa, sb)
    n = sc.natural_recovery_summary(SITE, n_draws=500, seed=7)
    assert "oil_excess_source" not in n and n["oil_excess"]["2010-2012"]["effect"] == sc._oil_excess()["2010-2012"][0]


# ---------------------------------------------------------------------------------------------------------------
# options work
def test_site_evidence_class_offsets_option():
    m2 = se.load_model_v2()
    p = se.predict_edge_loss(SITE, model=m2, oiling="Heavy")
    lo, hi = m2["interval_offsets_by_class"]["Heavy"]
    assert p["offsets_class"] == "Heavy" and np.isclose(p["lo"], p["rate"] + lo) and np.isclose(p["hi"], p["rate"] + hi)
    assert np.isclose(p["rate"], se.predict_edge_loss(SITE)["rate"])     # same point model as v1


def test_composer_oos_excess_option():
    card = json.loads((ROOT / "models" / "oil_excess_oos_v1.json").read_text())
    e = card["excess_by_class_deployable"]["Heavy"]["excess_m_per_yr"]
    o = sc.oil_excess_oos("Heavy")
    assert np.isclose((2 * o["2010-2012"][0] + 3 * o["2012-2018"][0]) / 5, e)       # years 1-5 mean = level
    assert sc.oil_excess_oos("NOO") is None
    site = {"max_oiling": "Heavy", "pred_rate": 0.0}
    pool = np.zeros(10)
    t, _ = sc.compose(site, [], horizon_years=5, n_draws=20000, seed=3, residual_pool=pool, oil_excess_source="oos_v1")
    c5 = t[(t.outcome == "cumulative_edge_loss_m") & (t.year == 5)].iloc[0]
    assert abs(c5["median"] / 5 - e) < 0.02
    tm, _ = sc.compose({"max_oiling": "Moderate", "pred_rate": 0.0}, [], horizon_years=5, n_draws=2000, seed=3,
                       residual_pool=pool, oil_excess_source="oos_v1")
    assert tm[(tm.outcome == "cumulative_edge_loss_m") & (tm.year == 5)].iloc[0]["median"] > 0
    n = sc.natural_recovery_summary(site, n_draws=500, seed=3, residual_pool=pool, oil_excess_source="oos_v1")
    assert n["oil_excess_source"] == "oos_v1" and np.isclose(n["oil_excess"]["2010-2012"]["effect"], o["2010-2012"][0])
    with pytest.raises(ValueError):
        sc.compose(site, [], oil_excess_source="zengel")


def test_class_residual_pool_option(ox):
    pool = sc.oos_class_residual_pool("Heavy")
    assert len(pool) == int((ox.max_oiling == "Heavy").sum())
    assert len(sc.oos_class_residual_pool("unknown")) == len(ox)


def test_docstrings_say_gate_failed():
    s = (ROOT / "results" / "v5_p0" / "summary.txt").read_text()
    if re.search(r"GATE 0\.1: FAILED", s):
        assert "FAILED" in (sc.oil_excess_oos.__doc__ or "")
    if re.search(r"GATE 0\.2: FAILED", s):
        assert "FAILED" in (se.load_model_v2.__doc__ or "")
