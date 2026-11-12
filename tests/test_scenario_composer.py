"""Checks of src/shoreline_remediation/scenario_composer.py (plan A2): determinism, natural recovery = baseline + oil
excess, no-evidence options get no shift and say so, elicited options act on tau only, outputs are ranges."""
import numpy as np
import pytest

from src.shoreline_remediation import scenario_composer as sc
from src.shoreline_remediation import site_evidence as se

SITE = dict(water_1km_2010=0.87, water_250m_2010=0.81, fetch_mean_m=3638.0, pre_rate=0.58, max_oiling="Heavy")
OPTS = ["natural_attenuation", "manual_removal", "mechanical_removal", "passive sorbents"]


def test_deterministic_with_seed_and_different_seed_differs():
    a, sa = sc.compose(SITE, OPTS, n_draws=500, seed=1)
    b, sb = sc.compose(SITE, OPTS, n_draws=500, seed=1)
    c, _ = sc.compose(SITE, OPTS, n_draws=500, seed=2)
    assert a.equals(b) and sa.equals(sb)
    assert not a["median"].equals(c["median"])


def test_option_order_does_not_change_results():
    a, _ = sc.compose(SITE, ["manual_removal", "mechanical_removal"], n_draws=400, seed=3)
    b, _ = sc.compose(SITE, ["mechanical_removal", "manual_removal"], n_draws=400, seed=3)
    key = ["option", "year", "outcome"]
    assert a.sort_values(key).reset_index(drop=True).equals(b.sort_values(key).reset_index(drop=True))


def test_natural_recovery_is_baseline_plus_oil_excess():
    pool = np.zeros(1)                       # no residual spread, so the baseline is the model prediction itself
    tidy, _ = sc.compose(SITE, ["natural_attenuation"], n_draws=20000, seed=4, residual_pool=pool)
    base = se.predict_edge_loss({k: SITE[k] for k in se.FEATURES})["rate"]
    oil = sc._oil_excess()
    rate = tidy[tidy.outcome == "edge_loss_rate_m_per_yr"].set_index("year")["median"]
    assert abs(rate[1] - (base + oil["2010-2012"][0])) < 0.03 and abs(rate[2] - rate[1]) < 0.03
    assert abs(rate[5] - (base + oil["2012-2018"][0])) < 0.05
    cum = tidy[tidy.outcome == "cumulative_edge_loss_m"].set_index("year")["median"]
    assert abs(cum[2] - 2 * (base + oil["2010-2012"][0])) < 0.06
    # a site that is not heavily oiled gets no oil excess (the evidence covers heavy oiling only)
    t2, s2 = sc.compose({**SITE, "max_oiling": "Light"}, ["natural_attenuation", "manual_removal"], n_draws=2000, seed=4, residual_pool=pool)
    r2 = t2[(t2.outcome == "edge_loss_rate_m_per_yr") & (t2.option == "natural_attenuation")].set_index("year")["median"]
    assert abs(r2[1] - base) < 1e-9 and bool(s2.evidence_scope_heavy_only.all())
    assert abs(t2[(t2.option == "manual_removal") & (t2.outcome == "cumulative_edge_loss_m") & (t2.year == 8)]["median"].iloc[0]
               - t2[(t2.option == "natural_attenuation") & (t2.outcome == "cumulative_edge_loss_m") & (t2.year == 8)]["median"].iloc[0]) < 1e-9


def test_option_without_evidence_has_no_shift_and_is_labelled():
    tidy, summ = sc.compose(SITE, OPTS, n_draws=1000, seed=5)
    nat = tidy[tidy.option == "natural_attenuation"].reset_index(drop=True)
    no = tidy[tidy.option == "passive sorbents"].reset_index(drop=True)
    assert np.allclose(nat[["median", "lo90", "hi90"]], no[["median", "lo90", "hi90"]])
    assert (no.evidence == sc.EVIDENCE_NONE).all()
    r = summ.set_index("option").loc["passive sorbents"]
    assert r.evidence == sc.EVIDENCE_NONE and np.isnan(r.p_less_edge_loss_than_natural_y8)
    assert r.paired_diff_cum_edge_loss_median == 0.0 and bool(r.edge_cannot_be_distinguished_y8)


def test_measured_option_is_shifted_and_labelled_measured():
    _, summ = sc.compose(SITE, OPTS, n_draws=3000, seed=6)
    s = summ.set_index("option")
    assert s.loc["manual_removal", "evidence"] == sc.EVIDENCE_MEASURED
    assert s.loc["manual_removal", "paired_diff_cum_edge_loss_median"] < 0   # Zengel 2022: manual -0.63 m/yr years 1-2
    assert 0.5 < s.loc["manual_removal", "p_less_edge_loss_than_natural_y2"] <= 1.0


def test_elicited_option_acts_on_tau_only_and_is_labelled():
    t, s = sc.compose(SITE, ["natural_attenuation", "bioremediation"], n_draws=2000, seed=7, elicited={"bioremediation": (0.6, 1.0)})
    r = s.set_index("option").loc["bioremediation"]
    assert r.evidence == sc.EVIDENCE_ELICITED and "not measured" in r.evidence
    assert r.paired_diff_cum_edge_loss_median == 0.0 and np.isnan(r.p_less_edge_loss_than_natural_y8)   # no edge-loss effect
    v = t[(t.option == "bioremediation") & (t.outcome == "veg_cover_ratio_to_reference")].set_index("year")["median"]
    vn = t[(t.option == "natural_attenuation") & (t.outcome == "veg_cover_ratio_to_reference")].set_index("year")["median"]
    assert v[3] > vn[3]                      # a smaller tau (faster recovery) raises cover at year 3


def test_outputs_are_always_ranges():
    tidy, summ = sc.compose(SITE, OPTS, n_draws=1000, seed=8)
    assert {"option", "year", "outcome", "median", "lo90", "hi90"} <= set(tidy.columns)
    assert (tidy.lo90 <= tidy["median"]).all() and (tidy["median"] <= tidy.hi90).all()
    assert (tidy.hi90 - tidy.lo90 > 0).all()
    assert tidy.year.min() == 1 and tidy.year.max() == 8
    assert (summ.cum_edge_loss_y8_lo90 < summ.cum_edge_loss_y8_hi90).all()


def test_veg_curve_not_used_when_verdict_not_usable(monkeypatch):
    m = dict(sc._veg_model()); m["verdict"] = "not usable"
    monkeypatch.setattr(sc, "_veg_model", lambda: m)
    tidy, summ = sc.compose(SITE, ["natural_attenuation"], n_draws=300, seed=9)
    assert "veg_cover_ratio_to_reference" not in set(tidy.outcome)
    assert "curve not used" in summ.veg_curve_verdict.iloc[0]


# ---- A4.1: paired-difference rule ------------------------------------------------------------------------------------
def test_paired_difference_flags_distinguish_measured_options_but_not_unshifted_ones():
    _, s = sc.compose(SITE, OPTS, n_draws=3000, seed=11)
    s = s.set_index("option")
    # old overlap flag kept; new flag added. Manual removal: Zengel 2022 shift is a clear negative paired difference at year 2
    assert "edge_cannot_be_distinguished_y2" in s.columns and "edge_distinguished_y2" in s.columns
    assert bool(s.loc["manual_removal", "edge_distinguished_y2"]) and bool(s.loc["manual_removal", "edge_cannot_be_distinguished_y2"])
    # no-evidence option: paired difference is exactly zero, never distinguished
    assert s.loc["passive sorbents", "paired_diff_cum_edge_loss_y5_lo90"] == 0.0 and not bool(s.loc["passive sorbents", "edge_distinguished_y5"])
    # natural recovery has no flag; the year-8 paired columns still equal the earlier summary columns
    assert np.isnan(s.loc["natural_attenuation", "edge_distinguished_y2"])
    assert s.loc["manual_removal", "paired_diff_cum_edge_loss_y8_median"] == s.loc["manual_removal", "paired_diff_cum_edge_loss_median"]


def test_vegetation_paired_difference_only_where_shift_or_elicited_range_exists():
    _, s = sc.compose(SITE, ["manual_removal", "passive sorbents", "bioremediation"], n_draws=2000, seed=12, elicited={"bioremediation": (0.6, 1.0)})
    s = s.set_index("option")
    assert np.isnan(s.loc["passive sorbents", "paired_diff_veg_ratio_y2_median"]) and not bool(s.loc["passive sorbents", "veg_distinguished_y2"])
    assert not np.isnan(s.loc["manual_removal", "paired_diff_veg_ratio_y2_median"])
    assert not np.isnan(s.loc["bioremediation", "paired_diff_veg_ratio_y5_median"])
    assert not bool(s.loc["bioremediation", "edge_distinguished_y8"])      # elicited: no edge-loss effect


# ---- A4.2: block composer on SIMULATED cells ---------------------------------------------------------------------------
import pandas as pd  # noqa: E402

SIM_CELLS = pd.DataFrame({"pred_rate": np.linspace(0.2, 1.0, 25), "max_oiling": "Heavy"})
RNG = np.random.default_rng(0)
WIDE, NARROW = RNG.normal(0, 2.0, 400), np.zeros(1)


def _rate_range(cells, pools, **kw):
    t, _ = sc.compose_block(cells, ["natural_attenuation"], n_draws=1500, seed=3, residual_pools=pools, **kw)
    r = t[(t.outcome == "mean_edge_loss_rate_m_per_yr") & (t.year == 5)].iloc[0]
    return r.hi90 - r.lo90


def test_block_range_narrower_than_cell_range_when_within_block_noise_dominates():
    one, many = SIM_CELLS.iloc[[0]], SIM_CELLS
    w1, w25 = _rate_range(one, (NARROW, WIDE)), _rate_range(many, (NARROW, WIDE))
    assert w25 < 0.5 * w1          # independent cell noise averages out (about 1/5 for 25 cells, plus shared oil excess)


def test_block_range_equals_cell_range_when_all_noise_is_block_level():
    # block residual shared by all cells; same pred_rate so the mean over cells equals one cell exactly
    same = pd.DataFrame({"pred_rate": [0.5] * 25, "max_oiling": "Heavy"})
    w1, w25 = _rate_range(same.iloc[[0]], (WIDE, np.zeros(1))), _rate_range(same, (WIDE, np.zeros(1)))
    assert w25 == pytest.approx(w1, rel=1e-9)


def test_block_composer_deterministic_and_units():
    a, sa = sc.compose_block(SIM_CELLS, ["manual_removal", "bioremediation"], n_draws=500, seed=9, residual_pools=(WIDE, WIDE),
                             elicited={"bioremediation": (0.6, 1.6)})
    b, sb = sc.compose_block(SIM_CELLS, ["manual_removal", "bioremediation"], n_draws=500, seed=9, residual_pools=(WIDE, WIDE),
                             elicited={"bioremediation": (0.6, 1.6)})
    assert a.equals(b) and sa.equals(sb)
    m2 = a[(a.outcome == "cumulative_area_lost_m2") & (a.year == 8)].set_index("option")
    ha = a[(a.outcome == "cumulative_area_lost_ha") & (a.year == 8)].set_index("option")
    mc = a[(a.outcome == "mean_cumulative_edge_loss_m") & (a.year == 8)].set_index("option")
    assert np.allclose(m2["median"] / 1e4, ha["median"])
    assert np.allclose(m2["median"], mc["median"] * 25 * sc.CELL_LENGTH_M, rtol=1e-6)   # sum x 100 m = mean x n x 100 m
    s = sa.set_index("option")
    assert s.loc["bioremediation", "paired_diff_area_m2_y8_median"] == 0.0 and not bool(s.loc["bioremediation", "area_distinguished_y8"])
    assert bool(s.loc["manual_removal", "area_distinguished_y2"])      # shared shift across 25 cells, paired draw: clearly negative


def test_block_composer_non_heavy_cells_get_no_oil_excess_or_shift():
    light = pd.DataFrame({"pred_rate": [0.3] * 6, "max_oiling": "Light"})
    t, s = sc.compose_block(light, ["manual_removal"], n_draws=400, seed=2, residual_pools=(np.zeros(1), np.zeros(1)))
    r = t[(t.option == "natural_attenuation") & (t.outcome == "mean_edge_loss_rate_m_per_yr") & (t.year == 1)].iloc[0]
    assert r["median"] == pytest.approx(0.3) and r.lo90 == pytest.approx(0.3)
    assert s.set_index("option").loc["manual_removal", "paired_diff_area_m2_y8_median"] == 0.0
