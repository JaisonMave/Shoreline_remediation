"""Simulated checks of validation/veg_recovery_curve.py (written and run before the real data were fitted)."""
import numpy as np
import pandas as pd

from validation import veg_recovery_curve as vr


def simulate_units(seed, n_studies=10, A=1.2, tau=3.0, study_sd=0.15, noise_sd=0.15, planted=True, n_zones=2, null_level=-0.5):
    """Units as build_units returns them. lnRR = -A exp(-t/tau) (if planted) + study offset + noise."""
    rng = np.random.default_rng(seed)
    rows = []
    for s in range(n_studies):
        years = np.sort(rng.choice(np.arange(2010, 2018), size=rng.integers(1, 5), replace=False))
        off = rng.normal(0, study_sd)
        for y in years:
            for z in range(1, n_zones + 1):
                t = y - 2010 + 0.5
                mu = -A * np.exp(-t / tau) if planted else null_level
                rows.append({"study": f"S{s}", "year": int(y), "zone": z, "t": t, "lnRR": mu + off + rng.normal(0, noise_sd)})
    return pd.DataFrame(rows)


def test_planted_exponential_is_recovered_and_beats_m0():
    u = simulate_units(1)
    f = vr.fit_m2(u)
    assert abs(f.params["A"] - 1.2) < 0.25
    assert abs(f.params["tau"] - 3.0) < 1.5
    R = vr.run_subset(u, ["M0", "M1", "M2", "M3"], n_boot=300, seed=7)
    assert R["avg"]["M2"] < R["avg"]["M0"]
    assert R["verdict"] == "validated"
    assert R["diffs"]["M2"]["hi"] < 0


def test_pure_noise_does_not_beat_m0():
    # No time trend: lnRR is a constant level (-0.5, oiled cover below reference at every time) plus study offsets and noise.
    # (A null at exactly 0 is not used: M2 has no intercept, so it contains that truth exactly and beats a fitted constant by
    # construction; that is a property of the pre-specified models, not evidence of recovery.)
    for seed in (2, 3, 4, 5, 6, 7):
        u = simulate_units(seed, planted=False, study_sd=0.3, noise_sd=0.3)
        R = vr.run_subset(u, ["M0", "M1", "M2", "M3"], n_boot=300, seed=7)
        assert R["verdict"] != "validated", (seed, R["diffs"]["M2"])


def test_study_never_split_between_training_and_test():
    u = simulate_units(5)
    seen = []

    def spy(train):
        seen.append(set(train.study))
        c = float(train.lnRR.mean())
        return lambda d: np.full(len(d), c)

    pred = vr.loso(u, {"M0": spy})
    assert len(seen) == u.study.nunique()
    for s, train_studies in zip(sorted(u.study.unique()), seen):
        assert s not in train_studies and len(train_studies) == u.study.nunique() - 1
    assert len(pred) == len(u) and set(pred.unit) == set(u.index)   # every unit predicted exactly once
    assert pred.unit.is_unique


def test_t_to_fraction_hand_cases():
    # -A exp(-t/tau) = ln 0.8 at t = tau ln(A / -ln 0.8)
    assert abs(vr.t_to_fraction(1.0, 2.0) - 2.0 * np.log(1.0 / -np.log(0.8))) < 1e-12
    assert vr.t_to_fraction(0.1, 2.0) == 0.0
    assert vr.t_to_fraction(0.0, 2.0) == 0.0


def test_build_units_filters_and_lnrr():
    raw = pd.DataFrame({
        "Source": ["a", "a", "a", "a", "b", "b", "c"], "Site ID": list("abcdefg"),
        "Site type": ["Oiled", "Reference", "Oiled", "Reference", "Oiled", "Oiled", "Reference"],
        "Site type (HO)": [None, None, "Oiled", "Reference", None, None, None],
        "Marsh Zone": [1, 1, 1, 1, 1, 1, 1], "Year": [2011] * 7,
        "TotalCover": [20.0, 40.0, np.nan, 60.0, 10.0, 10.0, 50.0]})
    u, c = vr.build_units(raw, "type")
    assert c["rows"] == 7 and c["rows_with_cover_year_zone"] == 6
    assert list(u.study) == ["a"]                      # b has no reference, c has no oiled
    assert abs(u.lnRR[0] - np.log(21 / 51)) < 1e-12 and abs(u.t[0] - 1.5) < 1e-12
    assert u.n_oiled[0] == 1 and u.n_reference[0] == 2
    uh, ch = vr.build_units(raw, "type_ho")
    assert uh.empty and ch["units"] == 0               # the HO oiled site has no cover value


def test_verdict_reading_table():
    assert vr.verdict({"diff": -0.1, "lo": -0.2, "hi": -0.01}) == "validated"
    assert vr.verdict({"diff": -0.1, "lo": -0.2, "hi": 0.05}) == "suggestive"
    assert vr.verdict({"diff": 0.1, "lo": -0.2, "hi": 0.3}) == "not usable"
