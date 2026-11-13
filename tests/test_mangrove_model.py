"""Mangrove oiling-effect model on SIMULATED sites (not Galeta data)."""
import numpy as np
import pandas as pd

from src.shoreline_remediation import mangrove_model as mm


def simulate(effect=0.3, n_per=10, years=(1987, 1988, 1989), seed=1, site_sd=0.3, noise=0.1):
    rng = np.random.default_rng(seed)
    rows = []
    for g, oiled in (("o", 1), ("u", 0)):
        for i in range(n_per):
            a = rng.normal(0, site_sd)
            for y in years:
                rows.append({"site": f"{g}{i}", "oiled": oiled, "year": y, "ys": y - mm.SPILL_YEAR,
                             "value": 1 + a + 0.1 * (y - 1987) + effect * oiled + rng.normal(0, noise)})
    return pd.DataFrame(rows)


def test_planted_effect_recovered_and_beats_m0():
    r = mm.run_outcome(simulate(0.5), n_boot=300)
    assert (r["effects"].effect > 0.3).all() and (r["effects"].effect < 0.7).all()
    assert (r["effects"].lo90 > 0).all()
    assert r["diff"]["diff"] < 0 and r["verdict"] == "validated"


def test_no_effect_is_not_validated():
    r = mm.run_outcome(simulate(0.0, seed=2), n_boot=300)
    assert r["verdict"] != "validated"
    assert (r["effects"].lo90 < 0).any()


def test_site_never_split():
    df = simulate(0.2, n_per=4, seed=3)
    p = mm.loso(df)
    assert len(p) == len(df)
    for s, g in p.groupby("site"):
        assert len(g) == (df.site == s).sum()
    train_sites = [set(df.site) - {s} for s in df.site.unique()]
    assert all(s not in t for s, t in zip(df.site.unique(), train_sites))


def test_verdict_rule_and_determinism():
    assert mm.verdict({"diff": -1, "hi": -0.1}) == "validated"
    assert mm.verdict({"diff": -1, "hi": 0.1}) == "suggestive"
    assert mm.verdict({"diff": 0.2, "hi": 0.5}) == "not usable"
    df = simulate(0.3, n_per=5, seed=4)
    assert mm.run_outcome(df, 200)["diff"] == mm.run_outcome(df, 200)["diff"]
