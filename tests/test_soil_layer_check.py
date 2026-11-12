"""Simulated checks of validation/soil_layer_check.py (written and run before the real comparison was run)."""
import numpy as np
import pandas as pd

from validation import soil_layer_check as sl


def test_lin_ccc_hand_cases():
    x = np.array([1.0, 2.0, 3.0])
    assert abs(sl.lin_ccc(x, x) - 1.0) < 1e-12
    # y = x + 1: cov 2/3, variances 2/3 each, mean difference 1 -> 2(2/3) / (4/3 + 1) = 4/7
    assert abs(sl.lin_ccc(x, x + 1) - 4 / 7) < 1e-12
    # perfectly anti-correlated with equal means -> -1
    assert abs(sl.lin_ccc(x, 4 - x) + 1.0) < 1e-12


def test_spearman_hand_cases():
    x = np.array([1.0, 2.0, 3.0, 4.0])
    assert abs(sl.spearman(x, x ** 3) - 1.0) < 1e-12           # monotone, not linear
    assert abs(sl.spearman(x, -x) + 1.0) < 1e-12
    assert np.isnan(sl.spearman(x, np.ones(4)))                  # constant side


def test_ssurgo_horizon_clipping_and_component_weighting():
    # 0-10 cm value 10, 10-30 cm value 40: clipped to 0-15 -> (10*10 + 5*40)/15 = 20
    assert abs(sl.clipped_weighted_mean([0, 10], [10, 30], [10, 40]) - 20.0) < 1e-12
    # a horizon wholly below 15 cm and a horizon without a value are ignored
    assert abs(sl.clipped_weighted_mean([0, 10, 20], [10, 20, 30], [10, np.nan, 99]) - 10.0) < 1e-12
    assert np.isnan(sl.clipped_weighted_mean([20], [30], [5.0]))
    hz = pd.DataFrame({"cokey": ["a", "a", "b", "c"], "comppct_r": [60, 60, 30, 10], "hzdept_r": [0, 10, 0, 0],
                       "hzdepb_r": [10, 30, 40, 40], "om_r": [10, 40, 30, np.nan]})
    # comp a = 20 (60%), comp b = 30 (30%), comp c has no value and is dropped -> (60*20 + 30*30)/90 = 23.333
    assert abs(sl.ssurgo_value(hz, "om_r") - (60 * 20 + 30 * 30) / 90) < 1e-12


def test_ssurgo_site_values_reasons():
    sites = pd.DataFrame({"site": ["s1", "s2", "s3"], "mukey": ["1", "2", np.nan]})
    h = pd.DataFrame({"mukey": ["1", "1", "2"], "cokey": ["a", "a", "b"], "comppct_r": [100, 100, 100],
                      "hzdept_r": [0, 10, 0], "hzdepb_r": [10, 30, 30], "om_r": [10, 40, np.nan],
                      "dbthirdbar_r": [0.2, 0.4, np.nan], "ec_r": [1, 1, np.nan], "ph1to1h2o_r": [6, 7, np.nan]})
    v, why = sl.ssurgo_site_values(sites, h)
    assert abs(v.loc[0, "om_r"] - 20.0) < 1e-12
    assert list(why.om_r) == ["ok", "no_value", "no_unit"]


def test_soilgrids_conversion_and_1_to_2_weighting():
    rows = []
    for stat, a, b in [("mean", 100, 130), ("Q0.05", 40, 40), ("Q0.95", 160, 160)]:
        for depth, v in [("0-5cm", a), ("5-15cm", b)]:
            rows.append(dict(site="s", prop="bdod", depth=depth, stat=stat, raw=v))
    for depth, v in [("0-5cm", 600), ("5-15cm", 900)]:
        rows.append(dict(site="s", prop="soc", depth=depth, stat="mean", raw=v))
    for depth, v in [("0-5cm", 50), ("5-15cm", ""), ]:
        rows.append(dict(site="t", prop="phh2o", depth=depth, stat="mean", raw=v))
    w = sl.soilgrids_site_values(pd.DataFrame(rows)).set_index("site")
    # bdod mean: (1.00*5 + 1.30*10)/15 = 1.2 g/cm3
    assert abs(w.loc["s", "bdod_mean"] - 1.2) < 1e-12
    # soc: (60*5 + 90*10)/15 = 80 g/kg; OM % = 80 * 1.724 / 10
    assert abs(w.loc["s", "soc_mean"] - 80.0) < 1e-12 and abs(w.loc["s", "om_mean"] - 80 * 1.724 / 10) < 1e-12
    assert np.isnan(w.loc["t", "phh2o_mean"])  # one layer missing -> missing


def test_site_table_depth_rule_unit_and_drops():
    c = sl.COLS
    raw = pd.DataFrame({
        c["station"]: ["CRMS0001-S01", "CRMS0001-S01", "CRMS0001-S02", "CRMS0002-S01", "CRMS0003-S01"],
        c["depth"]: ["0 to 4", "16 to 20", "8 to 16", "20 to 24", "0 to 4"],
        c["bd"]: [0.2, 9.0, 0.4, 5.0, 0.3], c["om"]: [10, 90, 30, 50, 17.24], c["ph"]: [6.0, 9, 7.0, 5, np.nan],
        c["cond"]: [2000, 9000, 4000, 1, np.nan],
        c["lat"]: [29.0, 29.0, 29.2, 29.5, np.nan], c["lon"]: [-90.0, -90.0, -90.2, -90.5, np.nan]})
    s, n = sl.build_sites(raw)
    assert n["sites_all"] == 3 and n["dropped_no_slice_shallower_than_16cm"] == 1 and n["dropped_no_coordinates"] == 1
    assert list(s.site) == ["CRMS0001"]
    r = s.iloc[0]
    # the 16-20 slice is excluded; the site is the mean of slices (0.2, 0.4), not of cores or deeper slices
    assert abs(r.bd - 0.3) < 1e-12 and abs(r.om - 20.0) < 1e-12 and abs(r.ph - 6.5) < 1e-12
    assert abs(r.sal - 3.0) < 1e-12            # uS/cm / 1000 = dS/m
    assert abs(r.lat - 29.1) < 1e-12 and abs(r.lon + 90.1) < 1e-12  # mean of the two cores' positions
    assert abs(r.soc - 20.0 / 1.724 * 10) < 1e-9


def test_p5_box():
    d = pd.DataFrame({"lat": [29.5, 29.0, 29.5], "lon": [-90.0, -90.0, -88.0]})
    assert list(sl.in_p5_box(d)) == [True, False, False]


def sim(n=300, seed=3):
    rng = np.random.default_rng(seed)
    truth = rng.lognormal(0, 0.5, n)
    return truth, rng


def test_map_that_tracks_truth_is_judged_usable():
    truth, rng = sim()
    r = sl.compare(truth, truth + rng.normal(0, 0.1, len(truth)), n_boot=300, seed=1)
    assert r["spearman"] > 0.8 and r["spearman_lo"] > 0.3 and r["mae_diff_vs_baseline_hi"] < 0
    assert r["verdict"].startswith("Usable")


def test_random_noise_map_is_judged_not_usable():
    truth, rng = sim()
    r = sl.compare(truth, rng.permutation(truth), n_boot=300, seed=1)
    assert abs(r["spearman"]) < 0.2 and r["verdict"] == "Not usable in marsh"


def test_ranking_only_map_is_weak():
    truth, rng = sim()
    r = sl.compare(truth, 5 * truth + 50, n_boot=300, seed=1)   # perfect ranks, values far off
    assert r["spearman"] > 0.99 and r["mae_diff_vs_baseline_lo"] > 0 and r["verdict"].startswith("Weak")


def test_rank_only_reports_no_error_statistics():
    truth, rng = sim()
    r = sl.compare(truth, truth + rng.normal(0, 0.2, len(truth)), rank_only=True, n_boot=200, seed=1)
    assert "spearman" in r and "mae" not in r and "bias" not in r and "no verdict" in r["verdict"]


def test_baseline_bias_and_coverage_hand_case():
    x = np.array([1.0, 2.0, 3.0, 4.0, 10.0]); y = x + 1
    s = sl.stat_arrays(x[None], y[None], np.array([[1, 1, 1, 1, 0]], float))
    assert abs(s["baseline_mae"][0] - np.abs(x - 3).mean()) < 1e-12 and abs(s["bias"][0] - 1.0) < 1e-12
    assert abs(s["rmse"][0] - 1.0) < 1e-12 and abs(s["coverage_q05_q95"][0] - 0.8) < 1e-12
    assert abs(s["mae_diff_vs_baseline"][0] - (1.0 - 2.2)) < 1e-12


def test_bootstrap_is_reproducible_and_brackets_estimate():
    truth, rng = sim()
    y = truth + rng.normal(0, 0.3, len(truth))
    a = sl.bootstrap_stats(truth, y, n_boot=200, seed=5); b = sl.bootstrap_stats(truth, y, n_boot=200, seed=5)
    assert a == b
    for k, (e, lo, hi) in a.items():
        assert lo <= e <= hi or k == "ccc"  # estimate lies inside its own 90% interval for these simulated data
    assert a["spearman"][1] < a["spearman"][0] < a["spearman"][2]


def test_run_end_to_end_on_simulated_sites():
    truth, rng = sim(150)
    n = len(truth)
    sites = pd.DataFrame({"site": [f"S{i}" for i in range(n)], "lat": rng.uniform(29.0, 30.4, n), "lon": rng.uniform(-93, -89.2, n),
                          "n_slices": 6, "bd": truth, "om": truth * 10, "ph": truth + 5, "sal": truth, "soc": truth * 10 / 1.724 * 10})
    sv = pd.DataFrame({"site": sites.site, "om_r": truth * 10, "dbthirdbar_r": rng.permutation(truth), "ec_r": truth * 2, "ph1to1h2o_r": truth + 5})
    why = pd.DataFrame({"site": sites.site, **{c: "ok" for c in ["om_r", "dbthirdbar_r", "ec_r", "ph1to1h2o_r"]}})
    sg = pd.DataFrame({"site": sites.site, "bdod_mean": truth, "bdod_Q0.05": truth - 1, "bdod_Q0.95": truth + 1,
                       "phh2o_mean": truth + 5, "phh2o_Q0.05": truth + 4, "phh2o_Q0.95": truth + 6,
                       "soc_mean": truth * 10 / 1.724 * 10, "soc_Q0.05": truth * 50, "soc_Q0.95": truth * 70,
                       "om_mean": truth * 10, "om_Q0.05": truth * 9, "om_Q0.95": truth * 11})
    res, _ = sl.run(sites, sv, why, sg, n_boot=100, seed=1)
    g = lambda v, p, s="all_sites": res[(res.variable == v) & (res["product"] == p) & (res.scope == s)].iloc[0]
    assert g("om_pct", "ssurgo").verdict.startswith("Usable")
    assert g("bulk_density_g_cm3", "ssurgo").verdict == "Not usable in marsh"
    assert g("bulk_density_g_cm3", "soilgrids").coverage_q05_q95 == 1.0
    assert "no verdict" in g("salinity_dS_m", "ssurgo").verdict and pd.isna(g("salinity_dS_m", "ssurgo").mae)
    assert len(res) == 16 and g("ph", "ssurgo", "P5_box").n < g("ph", "ssurgo").n
