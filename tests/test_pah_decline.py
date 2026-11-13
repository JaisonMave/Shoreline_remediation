"""Simulated checks of src/shoreline_remediation/diver_soil.py and validation/pah_decline.py (written and run before the
real DIVER data were fitted)."""
import numpy as np
import pandas as pd

from src.shoreline_remediation import diver_soil as ds
from validation import pah_decline as pd_


# ---------------------------------------------------------------- replicate rule
def test_replicate_rule_picks_the_right_value():
    assert ds.pick_value([100.0], 50.0) == (100.0, "single")
    v, r = ds.pick_value([100.0, 102.0], 500.0)                  # RPD 2 %: mean, reference ignored
    assert (v, r) == (101.0, "mean")
    assert ds.pick_value([100.0, 300.0], 110.0) == (100.0, "closer_to_median")   # RPD 100 %: closer to reference 110
    assert ds.pick_value([100.0, 300.0], 280.0) == (300.0, "closer_to_median")
    v, r = ds.pick_value([100.0, 102.0, 400.0], 0.0)             # three: drop the one farthest from their median
    assert (v, r) == (101.0, "drop_farthest")
    assert ds.pick_value([100.0, 101.0, 103.0], 0.0)[1] == "mean"
    assert ds.pick_value([100.0, 149.0], 0.0)[1] == "mean"        # RPD 39 % is within 50 %


def test_resolve_replicates_end_to_end_and_detect_outranks_nondetect():
    smp = pd.DataFrame({"sample": ["a", "b", "c"], "station": ["S1"] * 3, "campaign": ["Fall2011"] * 3})
    rows = pd.DataFrame({"Sample_ID": ["a", "a", "b", "c", "c", "c"], "Analysis": ["X"] * 6,
                         "value": [10.0, 90.0, 12.0, 11.0, 5.0, 5.0],
                         "Detection_Extent": ["Above Reporting Limit"] * 5 + [ds.ND_EXTENT]})
    rows.loc[4, "Detection_Extent"] = ds.ND_EXTENT
    log = ds.Log()
    r = ds.resolve_replicates(rows, smp, log).set_index("sample")
    # sample a: 10 vs 90 differ by 160 %; reference = median of the other samples (b = 12, c = 11) = 11.5 -> keep 10
    assert r.loc["a", "value"] == 10.0
    assert r.loc["b", "value"] == 12.0
    assert r.loc["c", "value"] == 11.0 and not r.loc["c", "nd"]      # the detect outranks the two non-detects


# ---------------------------------------------------------------- Tobit
def _simulate_censored(n=4000, seed=0, slope=0.8, sd=0.5, limit=1.0):
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 1, n)
    y = 1.0 + slope * x + rng.normal(0, sd, n)
    cens = y < limit
    return x, y, cens, np.full(n, limit)


def test_tobit_recovers_planted_relation_and_beats_naive():
    x, y, cens, c = _simulate_censored()
    assert 0.2 < cens.mean() < 0.6
    X = np.column_stack([np.ones_like(x), x])
    beta, sig = ds.tobit_fit(X, np.where(cens, np.nan, y), cens, c)
    assert abs(beta[1] - 0.8) < 0.08 and abs(beta[0] - 1.0) < 0.08 and abs(sig - 0.5) < 0.08
    naive = np.linalg.lstsq(X[~cens], y[~cens], rcond=None)[0]
    assert abs(naive[1] - 0.8) > abs(beta[1] - 0.8)                   # ignoring the censoring flattens the slope


def test_imputed_value_never_exceeds_limit():
    rng = np.random.default_rng(1)
    mu = rng.normal(0, 3, 500); c = rng.normal(0, 1, 500)
    for sig in (0.1, 1.0, 3.0):
        e = ds.tobit_expected(mu, sig, c)
        assert np.all(e <= np.exp(c) + 1e-12) and np.all(e > 0)


def test_impute_pipeline_respects_proxy_limit_and_uses_tobit_and_fallback():
    rng = np.random.default_rng(2)
    n = 900
    camps = np.array(["Spring2011", "Fall2011", "Fall2012", "Fall2013"])[rng.integers(0, 4, n)]
    toc = np.exp(rng.normal(0.5, 0.6, n))
    val = np.exp(3 + 0.9 * np.log(toc) + rng.normal(0, 0.8, n))
    lim = np.quantile(val, 0.25)
    nd = val < lim
    rows = []
    for comp in ("big", "tiny"):
        for i in range(n):
            if comp == "tiny" and i > 40:
                break
            rows.append((f"s{i}", comp, val[i], bool(nd[i] or (comp == "tiny" and i % 2 == 0)), camps[i], f"st{i % 50}"))
    res = pd.DataFrame(rows, columns=["sample", "compound", "value", "nd", "campaign", "station"])
    smp = pd.DataFrame({"sample": [f"s{i}" for i in range(n)], "depth_class": "0-2cm"})
    tocdf = pd.DataFrame({"sample": [f"s{i}" for i in range(n)], "toc": toc})
    p = ds.impute(res, ["big", "tiny"], smp, tocdf, "tobit", None)
    nds = p[p.nd]
    assert (nds.filled <= nds.proxy + 1e-9).all() and (nds.filled > 0).all()
    assert (p[p.compound == "big"].query("nd").method == "tobit").all()          # >= 30 detects: Tobit
    assert (p[p.compound == "tiny"].query("nd").method == "half_proxy").all()    # < 30 detects: half the proxy limit
    for mode, f in (("zero", 0.0), ("proxy", 1.0), ("half", 0.5)):
        q = ds.impute(res, ["big", "tiny"], smp, tocdf, mode, None)
        qn = q[q.nd]
        assert np.allclose(qn.filled, f * qn.proxy)


# ---------------------------------------------------------------- decline model
TIMES = np.array([1.0, 1.6, 2.6, 3.6])


def simulate_cells(seed, k=None, n_st=60, station_sd=1.0, noise_sd=0.3, classes=("none", "heavy")):
    """k: dict class -> first-order rate (per year); None = constant series."""
    rng = np.random.default_rng(seed)
    rows = []
    for s in range(n_st):
        cl = classes[s % len(classes)]
        lvl = 8 + rng.normal(0, station_sd) + (1.5 if cl == "heavy" else 0)
        for o, t in enumerate(TIMES):
            kk = 0.0 if k is None else k[cl]
            rows.append({"station": f"S{s}", "campaign": f"C{o}", "order": o, "t": t + rng.normal(0, 0.05),
                         "y": lvl - kk * t + rng.normal(0, noise_sd), "deep": 0.0, "oil_class": cl, "state": "LA", "depth_class": "0-2cm"})
    return pd.DataFrame(rows)


def test_planted_first_order_decline_is_recovered_with_half_life():
    hl = {"none": 2.0, "heavy": 4.0}
    k = {c: np.log(2) / h for c, h in hl.items()}
    cells = simulate_cells(3, k, n_st=80)
    m = pd_.fit_m1(cells)
    for c in hl:
        assert abs(pd_.half_life(m["k"][c]) - hl[c]) / hl[c] < 0.2, (c, m["k"])
    v = pd_.validate(cells)
    assert v["MAE_M1"] < v["MAE_M0"] and v["boot"]["verdict"] == "validated"
    tab = pd_.half_life_table(cells, n_boot=60, seed=5)
    h = tab.set_index("oil_class").loc["none"]
    assert h.half_life_lo90 < 2.0 * 1.3 and h.half_life_hi90 > 2.0 * 0.7


def test_constant_series_does_not_beat_m0():
    for seed in (11, 12, 13, 14, 15):
        cells = simulate_cells(seed, None, n_st=60)
        v = pd_.validate(cells)
        assert v["boot"]["verdict"] != "validated", (seed, v["boot"])
        assert v["MAE_M1"] >= v["MAE_M0"] - 0.02


def test_no_station_is_split_between_folds():
    cells = simulate_cells(4, None, n_st=47)
    fold = pd_.station_folds(cells.station)
    assert set(fold) == set(cells.station) and set(fold.values()) == set(range(pd_.N_FOLDS))
    sizes = pd.Series(fold).value_counts()
    assert sizes.max() - sizes.min() <= 1
    pred = pd_.cross_validate(cells)                       # asserts inside that train and test stations are disjoint
    assert pred.groupby("station").fold.nunique().max() == 1
    assert set(pred.station) == set(cells.station)


def test_depth_class_targets_use_same_depth_anchor():
    c = simulate_cells(5, None, n_st=3)
    deep = c[c.order.isin([1, 2])].assign(deep=1.0, depth_class="deeper", y=c.y + 5)
    a = pd_.anchors(pd.concat([c, deep], ignore_index=True))
    d = a[a.depth_class == "deeper"]
    assert (d.order == 2).all()                              # first deeper cell (order 1) is its own anchor
    assert (d.a_y > c.y.max()).all()
