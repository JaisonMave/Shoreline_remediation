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
    # R3 fix: the composer's baseline is the clean-edge model (docs/R3_OIL_DOUBLE_COUNT_PLAN.md), not site_evidence's
    # default (p5-edge-loss-v1, used elsewhere e.g. the dashboard).
    base = se.predict_edge_loss({k: SITE[k] for k in se.FEATURES}, model=sc._baseline_model())["rate"]
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


# ---- R7a: year-2 treatment shift now held and decaying, not a one-year spike --------------------------------------
def test_vegetation_year2_shift_held_and_decaying_not_a_spike():
    t, _ = sc.compose(SITE, ["manual_removal"], n_draws=4000, seed=15)
    man = t[(t.option == "manual_removal") & (t.outcome == "veg_cover_ratio_to_reference")].set_index("year")["median"]
    nat = t[(t.option == "natural_attenuation") & (t.outcome == "veg_cover_ratio_to_reference")].set_index("year")["median"]
    # year 1 (before the shift) is identical to natural recovery
    assert man[1] == pytest.approx(nat[1], abs=1e-9)
    # year 2 is unchanged by the fix (decay = 1 exactly at t2): still the old spike size
    assert man[2] - nat[2] > 0.1
    # later years keep a positive, decaying effect rather than snapping back to zero at year 3
    assert man[3] - nat[3] > 0.0
    assert man[8] - nat[8] > 0.0
    assert (man[3] - nat[3]) < (man[2] - nat[2])     # the gap shrinks after year 2 instead of vanishing
    assert (man[8] - nat[8]) < (man[3] - nat[3])     # and keeps shrinking


# ---- R7b / D28: heavy-oiling scope flag on the vegetation curve, shown not dropped ----------------------------------
def test_veg_curve_scope_flag_on_heavy_sites_only():
    _, s_heavy = sc.compose(SITE, ["manual_removal"], n_draws=500, seed=16)          # SITE is Heavy
    assert (s_heavy.veg_curve_scope == sc.VEG_CURVE_SCOPE_HEAVY).all()
    _, s_light = sc.compose({**SITE, "max_oiling": "Light"}, ["manual_removal"], n_draws=500, seed=16)
    assert "veg_curve_scope" not in s_light.columns or s_light.veg_curve_scope.isna().all()
    # not dropped: the vegetation outcome is still produced for heavy sites
    t, _ = sc.compose(SITE, ["manual_removal"], n_draws=500, seed=16)
    assert "veg_cover_ratio_to_reference" in set(t.outcome)


# ---- R4: one absolute edge-loss number per site, decomposed -------------------------------------------------------
def test_natural_recovery_summary_decomposes_and_matches_compose():
    nrs = sc.natural_recovery_summary(SITE, n_draws=5000, seed=20261112)
    assert nrs["heavy"] is True
    assert nrs["oil_excess"]["2010-2012"]["effect"] == pytest.approx(sc._oil_excess()["2010-2012"][0])
    assert "over-predicted NAIP heavy-cell loss" in nrs["bias_note"]
    base = se.predict_edge_loss({k: SITE[k] for k in se.FEATURES}, model=sc._baseline_model())
    assert nrs["baseline"]["rate"] == pytest.approx(base["rate"])
    assert nrs["baseline"]["lo90"] == pytest.approx(base["lo"]) and nrs["baseline"]["hi90"] == pytest.approx(base["hi"])
    # mean_rate_y1_5 must come from the same compose() output used everywhere else (R4: one number, one function)
    tidy, _ = sc.compose(SITE, [], horizon_years=5, n_draws=5000, seed=20261112)
    cum5 = tidy[(tidy.option == sc.NATURAL) & (tidy.outcome == "cumulative_edge_loss_m") & (tidy.year == 5)].iloc[0]
    assert nrs["mean_rate_y1_5"]["median"] == pytest.approx(cum5["median"] / 5)
    assert nrs["mean_rate_y1_5"]["lo90"] == pytest.approx(cum5.lo90 / 5)
    # a non-heavy site gets no oil-excess component
    light = sc.natural_recovery_summary({**SITE, "max_oiling": "Light"}, n_draws=500, seed=1)
    assert light["heavy"] is False and light["oil_excess"] is None


def test_elicited_option_acts_on_tau_only_and_is_labelled():
    t, s = sc.compose(SITE, ["natural_attenuation", "bioremediation"], n_draws=2000, seed=7, elicited={"bioremediation": (0.6, 1.0)})
    r = s.set_index("option").loc["bioremediation"]
    assert r.evidence == sc.EVIDENCE_ELICITED and "not human-reviewed" in r.evidence   # R6 fix: AI-proposed, not elicited from a human
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


# ---- Plan B1: forecast()
def test_forecast_returns_ranges_at_each_horizon_for_site_and_cells():
    f = sc.forecast(SITE, horizons=(1, 3, 5, 8), n_draws=500, seed=1)
    assert sorted(f.horizon_years.unique()) == [1, 3, 5, 8]
    assert (f.lo90 <= f["median"]).all() and (f["median"] <= f.hi90).all() and (f.hi90 > f.lo90).all()
    fb = sc.forecast(SIM_CELLS, n_draws=500, seed=1, residual_pools=(WIDE, WIDE))
    assert set(fb.outcome) == {"mean_cumulative_edge_loss_m", "cumulative_area_lost_m2", "cumulative_area_lost_ha"}
    assert sorted(fb.horizon_years.unique()) == [1, 3, 5, 8] and (fb.hi90 > fb.lo90).all()


def test_forecast_refuses_horizon_beyond_8_with_clear_message():
    with pytest.raises(ValueError, match="extrapolation: no outcome data beyond 2018"):
        sc.forecast(SITE, horizons=(1, 10), n_draws=100)
    with pytest.raises(ValueError, match="extrapolation"):
        sc.forecast(SIM_CELLS, horizons=(9,), n_draws=100, residual_pools=(WIDE, WIDE))


def test_forecast_deterministic_with_seed():
    a = sc.forecast(SITE, n_draws=500, seed=7)
    b = sc.forecast(SITE, n_draws=500, seed=7)
    c = sc.forecast(SITE, n_draws=500, seed=8)
    assert a.equals(b) and not a["median"].equals(c["median"])


# ---- R3 fix: composer baseline is the clean-edge model (docs/R3_OIL_DOUBLE_COUNT_PLAN.md) ----------------------------
def test_composer_baseline_uses_clean_card_not_site_evidence_default():
    v1_rate = se.predict_edge_loss({k: SITE[k] for k in se.FEATURES})["rate"]            # site_evidence default (v1)
    clean_rate = se.predict_edge_loss({k: SITE[k] for k in se.FEATURES}, model=sc._baseline_model())["rate"]
    assert sc._baseline_model()["name"] == "p5-edge-loss-clean-v1"
    assert clean_rate != pytest.approx(v1_rate)          # different coefficients -> different prediction
    pool = np.zeros(1)
    tidy, _ = sc.compose(SITE, ["natural_attenuation"], n_draws=20000, seed=4, residual_pool=pool)
    rate_y1 = tidy[(tidy.outcome == "edge_loss_rate_m_per_yr") & (tidy.year == 1)]["median"].iloc[0]
    oil = sc._oil_excess()["2010-2012"][0]
    assert rate_y1 == pytest.approx(clean_rate + oil, abs=0.03)
    assert rate_y1 != pytest.approx(v1_rate + oil, abs=1e-3)   # would be wrong if the v1 (all-cells) baseline leaked back in


def test_clean_card_training_cells_exclude_light_moderate_heavy():
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    from validation.p2_basin_holdout import BASINS, load_basin
    panel = pd.concat([load_basin(root / "data" / "external" / "p2" / b, b) for b in BASINS])
    model = sc._baseline_model()
    kept = set(model["clean_training_filter"]["kept_oiling_classes"])
    assert kept == {"NOO", "Very_Light"}
    clean = panel[panel.max_oiling.isin(kept)]
    assert len(clean) == model["training_cells"]
    assert not (set(clean.max_oiling.unique()) & {"Light", "Moderate", "Heavy"})
    assert set(clean.max_oiling.unique()) <= kept
