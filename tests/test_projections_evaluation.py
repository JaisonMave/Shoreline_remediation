"""Session 6 of docs/CLAUDE_SCENARIO_PREDICTION_PLAN.md: protocol P-RET-1 scoring. Software checks of the scoring code against
hand calculations, leakage and the recorded verdicts. The verdicts themselves are scientific results recorded in the protocol.
    python -m pytest -q tests/test_projections_evaluation.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.shoreline_remediation.projections import evaluation as E  # noqa: E402
from src.shoreline_remediation.projections.__main__ import main  # noqa: E402


@pytest.fixture(scope="module")
def result():
    return E.evaluate(n_boot=0)


@pytest.fixture(scope="module")
def g():
    return E.untreated_plots()


def test_data_and_pairs_follow_the_protocol(result):
    p = result["pairs"]
    assert result["data"]["n_plots"] == 9 and len(result["data"]["survey_dates"]) == 7
    pairs = p[["cutoff", "target"]].drop_duplicates()
    assert len(pairs) == 10 and set(pairs.cutoff) == set(E.CUTOFFS)
    assert (pairs.target > pairs.cutoff).all()
    assert p.lead_years.min() == pytest.approx(0.9745, abs=1e-3) and p.lead_years.max() == pytest.approx(4.049, abs=1e-3)


def test_rates_match_hand_calculations(g, result):
    rates = result["rates"].set_index(["cutoff", "rule"]).rate_m_per_yr
    means = g.groupby(["d", "t"]).inc.mean().reset_index().set_index("d")
    for c in E.CUTOFFS:
        tr = g[(g.d <= c) & (g.t > 0)]
        assert rates[(c, "B1")] == pytest.approx(float((tr.t * tr.inc).sum() / (tr.t ** 2).sum()), abs=1e-6)  # LS through origin
        m = means[means.index <= c]
        assert rates[(c, "C1")] == pytest.approx(float((m.inc.iloc[-1] - m.inc.iloc[-2]) / (m.t.iloc[-1] - m.t.iloc[-2])), abs=1e-12)
        assert rates[(c, "B0")] == 0.0


def test_no_later_survey_can_change_a_rate(g):
    for c in E.CUTOFFS:
        full = E.rates_at(g, c)
        trimmed = E.rates_at(g[g.d <= c], c)
        for rule in E.RULES:
            assert full[rule] == trimmed[rule], (c, rule)


def test_errors_are_forecast_minus_observed_increments(result):
    p = result["pairs"]
    s = p[p.scored]
    assert np.allclose(s.forecast_increment_m, s.rate_m_per_yr * s.lead_years)
    assert np.allclose(s.error_m, s.forecast_increment_m - s.observed_increment_m)
    b0 = s[s.rule == "B0"]
    assert np.allclose(b0.error_m, -b0.observed_increment_m)


def test_candidates_are_compared_on_their_own_pairs(result):
    s = result["summary"]
    assert s["C1"]["n_pairs"] == 10 and s["C1"]["omitted_pairs"] == []
    assert s["C2"]["n_pairs"] == 6 and len(s["C2"]["omitted_pairs"]) == 4
    assert all(o["cutoff"] == "2012-09-17" and "three post-origin" in o["reason"] for o in s["C2"]["omitted_pairs"])
    p = result["pairs"]
    keys = p[(p.rule == "C2") & p.scored].set_index(["cutoff", "target"]).index
    b1 = p[p.rule == "B1"].set_index(["cutoff", "target"]).loc[keys]
    assert s["C2"]["mae_m"]["B1"] == pytest.approx(float(b1.abs_error_m.mean()))
    assert s["C1"]["longest_lead_scored_years"] == pytest.approx(4.049, abs=1e-3)
    assert s["C2"]["longest_lead_scored_years"] == pytest.approx(3.075, abs=1e-3)


def test_criteria_are_applied_as_written(result):
    for cand, v in result["summary"].items():
        m = v["mae_m"]
        crit = v["criteria"]
        assert (crit["1_mae_gain_at_least_delta"]["result"] == "pass") == (m[cand] <= m["B1"] - E.DELTA_M)
        assert (crit["4_B1_beats_B0"]["result"] == "pass") == (m["B1"] < m["B0"])
        b = v["bias_m"]
        assert (crit["3_bias_not_worse_than_B1_plus_0.25"]["result"] == "pass") == (abs(b[cand]) <= abs(b["B1"]) + 0.25)
        eligible = [x for x in v["by_lead_bin"] if x["n_pairs"] >= 2]
        expect2 = all(x[f"mae_{cand}_m"] <= x["mae_B1_m"] for x in eligible)
        assert (crit["2_no_worse_than_B1_in_bins_with_2plus_pairs"]["result"] == "pass") == expect2
        results = [c["result"] for c in crit.values()]
        assert (v["verdict"] == "pass") == all(r == "pass" for r in results)


def test_recorded_verdicts(result):
    """Regression on the Session 6 results recorded in docs/PROJECTION_RETREAT_PROTOCOL.md section 10."""
    c1, c2 = result["summary"]["C1"], result["summary"]["C2"]
    assert c1["verdict"] == "fail" and c2["verdict"] == "fail"
    assert c1["mae_m"]["C1"] == pytest.approx(2.2456, abs=1e-4) and c1["mae_m"]["B1"] == pytest.approx(2.7423, abs=1e-4)
    assert c1["mae_difference_candidate_minus_B1_m"] == pytest.approx(-0.4967, abs=1e-4)      # short of Delta by 0.003 m
    assert [k for k, x in c1["criteria"].items() if x["result"] == "fail"] == ["1_mae_gain_at_least_delta"]
    assert c2["mae_m"]["C2"] == pytest.approx(3.6964, abs=1e-4)
    diag = c2["identification_diagnostic"]
    assert diag["cutoffs_with_a_parameter_at_bound"] == ["2013-09-08", "2014-09-26", "2015-09-30"]
    assert all(f["params_at_bound"] == "A" and f["b"] < 0 for f in diag["fits"])
    sens = c1["sensitivity_without_2016_targets"]
    assert sens["n_pairs"] == 6 and sens["B1"]["mae_m"] - sens["C1"]["mae_m"] == pytest.approx(0.514, abs=1e-3)


def test_cli_evaluate_writes_a_record_and_refuses_existing_paths(tmp_path):
    out = tmp_path / "ev"
    assert main(["evaluate", "--output", str(out), "--n-boot", "20"]) == 0
    e = json.loads((out / "evaluation.json").read_text())
    assert e["status"] == "completed" and e["delta_m"] == 0.5 and "owner-confirmed" in e["delta_status"]
    assert e["seed"] == 20261120 and e["n_boot"] == 20 and len(e["source"]["sha256"]) == 64
    assert "2030 or 2050" in e["scope"] and "conditional scenario" in e["scope"]
    assert set(e["outputs"]) == {"pairs.csv", "rates.csv"}
    assert pd.read_csv(out / "pairs.csv").shape[0] == 40                   # 10 pairs x 4 rules
    assert main(["evaluate", "--output", str(out), "--n-boot", "0"]) == 4
