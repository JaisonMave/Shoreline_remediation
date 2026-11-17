"""Treatment comparison layer (V5.4 plot-first): contract, eligibility and ordering. Logic tests only; not scientific validation.

Synthetic estimates appear ONLY in this file. They exercise the ordering rules; they are never runtime results.
Run from the repository root:  python -m pytest tests/test_comparison.py
"""
import copy
import math
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.shoreline_remediation import comparison as K  # noqa: E402
from src.shoreline_remediation import treatment_effects as te  # noqa: E402

T = K.VEG_YEAR2


def option(name, category="recommended", rule="eligible", conditions=(), reason="", exclusion=()):
    return {"option": name, "recommendation_category": category, "recommendation_category_label": category.replace("_", " ").capitalize(),
            "recommendation_category_reason": reason, "rule_verdict": rule, "conditions": list(conditions),
            "exclusion_reasons": [{"detail": x} for x in exclusion]}


def report(*options):
    return {"options": list(options), "recommendation_summary": {}}


def est(name, value, lo=None, hi=None, **kw):
    base = dict(option=name, label=name.replace("_", " ").capitalize(), group=f"{name} plots", habitat=T.habitat, scenario=T.scenario,
                outcome=T.outcome, unit=T.unit, time=T.time, comparator=T.comparator, estimate=value,
                lo=None if value is None else (value - 5 if lo is None else lo), hi=None if value is None else (value + 5 if hi is None else hi),
                interval_level=0.90, interval_type="synthetic interval", basis=K.FIELD, design="synthetic", derivation="synthetic",
                source="synthetic test value", source_keys=(name,), synthetic=True)
    base.update(kw)
    return K.Estimate(**base)


def run(estimates, rep, target=T, habitat="salt_marsh", oiling="Heavy"):
    return K.compare(target, estimates, rep, habitat, oiling)


ADMITTED = K.ModelAdmission(True, True, True, True, True)


@pytest.fixture(scope="module")
def bay_jimmy_report():
    from src.shoreline_remediation.decision_pipeline import run_decision
    from src.shoreline_remediation.site_evidence import load_sites
    s = load_sites()
    row = s[s.cell == "8018_32612"].iloc[0].to_dict()
    return run_decision({k: v for k, v in row.items() if v == v}, habitat="salt_marsh", oil="light", season=None, n_draws=500)


# ---- runtime estimates equal their source ---------------------------------------------------------------------------

def test_manual_removal_contrast_is_recomputed_from_the_published_group_means():
    raw = te.load()
    g = raw[(raw.study == "main") & (raw.year == 2012) & (raw.metric == "Total Vegetation Cover (%)")].set_index("treatment")
    m, u = g.loc["Manual Treatment"], g.loc["No Treatment"]
    assert (m["mean"], m.se, m.n, u["mean"], u.se, u.n) == (52.0, 7.0, 5, 18.0, 3.0, 9)
    c = te.welch_contrast(m["mean"], m.se, m.n, u["mean"], u.se, u.n, 0.90)
    e = next(x for x in K.vegetation_year2_estimates() if x.option == "manual_removal")
    assert e.estimate == pytest.approx(34.0) and e.estimate == pytest.approx(c["effect"])
    assert (e.lo, e.hi) == (pytest.approx(c["lo"]), pytest.approx(c["hi"])) and (round(e.lo, 2), round(e.hi, 2)) == (18.96, 49.04)
    assert e.interval_level == 0.90 and "Welch" in e.interval_type
    assert e.basis == K.FIELD and "not randomly assigned" in e.design and "published group means" in e.derivation
    assert (e.n_treated, e.n_comparator) == (5, 9) and e.outcome == "total vegetation cover" and e.comparator == "untreated oiled plots"


def test_runtime_rows_are_field_comparisons_and_never_synthetic():
    for key in K.TARGETS:
        rows = K.runtime_estimates(key)
        assert rows and all(r.basis == K.FIELD and not r.synthetic and r.admission is None for r in rows)
    assert not K.NEAREST_CANDIDATE.admitted and not any(ok for _, ok, _ in K.NEAREST_CANDIDATE.checks)


def test_erosion_rows_keep_period_units_and_the_planting_sequence():
    a, b = K.erosion_estimates("2010-2012"), K.erosion_estimates("2012-2018")
    assert {e.time for e in a} == {"2010-2012"} and {e.time for e in b} == {"2012-2018"} and {e.unit for e in a + b} == {"m/yr"}
    manual = next(e for e in a if e.option == "manual_removal")
    ref = te.erosion_effects("2010-2012").set_index("treatment").loc["manual"]
    assert manual.estimate == pytest.approx(ref.extra_erosion_vs_untreated) and round(manual.estimate, 2) == -0.63
    assert "plot-level" in manual.derivation
    seq = next(e for e in a if e.option == K.PLANTING)
    assert seq.interpretation == "sequence" and seq.prerequisite == "mechanical_removal" and seq.comparator == "untreated oiled plots"
    assert not K.EROSION_2010_2012.higher_is_better


# ---- Bay Jimmy through the real report ------------------------------------------------------------------------------

def test_bay_jimmy_vegetation_has_one_eligible_method_and_no_rank(bay_jimmy_report):
    comp = K.assessment_comparisons(bay_jimmy_report, "salt_marsh", "Heavy")[T.key]
    assert comp.mode == "single" and [r.option for r in comp.eligible] == ["manual_removal"]
    assert all(r.rank is None for r in comp.rows)
    assert comp.title.endswith("comparison with natural recovery") and "order" not in comp.title
    mech = comp.row_for("mechanical_removal")
    assert mech.screening == "excluded" and not mech.eligible and not mech.shown and mech.reason.startswith("Excluded by screening")
    assert mech.est.estimate == pytest.approx(5.0) and mech in comp.historical           # the historical value is kept, not ranked
    planting = next(r for r in comp.rows if r.option == K.PLANTING)
    assert not planting.on_target and "Spartina alterniflora cover" in planting.reason and comp.row_for(K.PLANTING) is None
    assert K.cell_text(comp, K.PLANTING) == K.NO_DATA and K.cell_text(comp, "bioremediation") == K.NO_DATA
    assert K.cell_text(comp, "manual_removal") == "+34.0 points (90% interval +19.0 to +49.0)"
    assert K.finding(comp).startswith("Total vegetation cover was 34 percentage points higher in manually treated plots than in "
                                      "untreated oiled plots at year 2")
    assert [p["option"] for p in K.plot_records(comp)] == ["manual_removal"]


def test_bay_jimmy_planting_sequence_is_not_ranked_for_erosion_while_mechanical_is_excluded(bay_jimmy_report):
    comp = K.assessment_comparisons(bay_jimmy_report, "salt_marsh", "Heavy")[K.EROSION_2010_2012.key]
    seq = comp.row_for(K.PLANTING)
    assert seq.on_target and not seq.eligible and "mechanical removal, which is excluded" in seq.reason
    assert comp.mode == "single" and comp.eligible[0].option == "manual_removal" and comp.eligible[0].benefit == pytest.approx(0.635, abs=0.01)


def test_comparison_does_not_change_the_report(bay_jimmy_report):
    before = copy.deepcopy(bay_jimmy_report.options), copy.deepcopy(bay_jimmy_report.recommendation_summary)
    K.assessment_comparisons(bay_jimmy_report, "salt_marsh", "Heavy")
    assert (bay_jimmy_report.options, bay_jimmy_report.recommendation_summary) == before


def test_no_comparison_outside_heavily_oiled_salt_marsh(bay_jimmy_report):
    assert K.assessment_comparisons(bay_jimmy_report, "rocky_shore", "Heavy") == {}
    comp = K.assessment_comparisons(bay_jimmy_report, "salt_marsh", "Moderate")[T.key]
    assert not comp.applicable and comp.mode == "none" and not K.plot_records(comp)
    assert K.cell_text(comp, "manual_removal") == K.NO_DATA and "heavily oiled salt marsh only" in comp.rows[0].reason


# ---- rules, with synthetic rows -------------------------------------------------------------------------------------

@pytest.mark.parametrize("change,word", [({"outcome": "Spartina alterniflora cover"}, "outcome"), ({"unit": "ratio to reference cover"}, "unit"),
                                         ({"time": "year 1 after oiling (2011 survey)"}, "time"),
                                         ({"comparator": "reference marsh"}, "comparator"), ({"habitat": "mangrove"}, "habitat"),
                                         ({"scenario": "Moderate"}, "oiling scenario"), ({"interpretation": "incremental"}, "comparator")])
def test_a_mismatch_on_any_target_field_keeps_a_row_out(change, word):
    comp = run([est("a", 10.0), est("b", 50.0, **change)], report(option("a"), option("b")))
    b = next(r for r in comp.rows if r.option == "b")
    assert not b.eligible and not b.on_target and word in b.reason.lower()
    assert [r.option for r in comp.eligible] == ["a"] and comp.mode == "single"


def test_sign_direction_follows_the_target():
    rep = report(option("a"), option("b"))
    up = run([est("a", 10.0), est("b", 30.0)], rep)
    assert [r.option for r in up.eligible] == ["b", "a"] and [r.rank for r in up.eligible] == [1, 2]
    ero = K.EROSION_2010_2012
    fields = dict(outcome=ero.outcome, unit=ero.unit, time=ero.time)
    down = run([est("a", -0.2, **fields), est("b", -0.9, **fields), est("c", 0.4, **fields)], report(option("a"), option("b"), option("c")), ero)
    assert [r.option for r in down.eligible] == ["b", "a", "c"]            # less erosion is better
    assert down.eligible[0].benefit == pytest.approx(0.9) and down.eligible[-1].benefit == pytest.approx(-0.4)


def test_missing_values_are_never_ranked_plotted_or_shown_as_zero():
    comp = run([est("a", 10.0), est("b", None), est("c", float("nan"))], report(option("a"), option("b"), option("c")))
    for name in ("b", "c"):
        r = comp.row_for(name)
        assert not r.eligible and r.reason == K.NO_DATA and r.benefit is None
        assert K.cell_text(comp, name) == K.NO_DATA and K.fmt_value(r, T) == K.NO_DATA
    assert [p["option"] for p in K.plot_records(comp)] == ["a"]
    assert all(math.isfinite(p["estimate"]) and p["estimate"] != 0.0 for p in K.plot_records(comp))
    assert K.cell_text(comp, "not_in_any_table") == K.NO_DATA


def test_excluded_options_are_visible_but_never_ranked_even_with_the_largest_effect():
    comp = run([est("a", 10.0), est("b", 12.0), est("x", 90.0)],
               report(option("a"), option("b"), option("x", "excluded", "ineligible", exclusion=["damages the habitat"])))
    x = comp.row_for("x")
    assert not x.eligible and not x.shown and x.rank is None and "damages the habitat" in x.reason and x in comp.historical
    assert [r.option for r in comp.eligible] == ["b", "a"] and "x" not in [p["option"] for p in K.plot_records(comp)]
    assert any(rec["Method"] == "X" and rec["In the order"] == "No" for rec in K.table_records(comp))


@pytest.mark.parametrize("conditions,state,eligible", [
    (["Applied early -> helps [met by input season]"], "met", True),
    (["Applied early -> helps [unknown (ask user)]"], "unknown", False),
    (["Applied early -> helps [not met by input season]"], "unmet", False),
    (["Growing season -> harms [met by input season]"], "unmet", False),
    (["Growing season -> harms [not met by input season]"], "met", True),
    (["Applied early -> helps [met by input season]", "Hard nozzles -> harms [unknown (ask user)]"], "unknown", False),
    ([], "unknown", False),
    (["free text with no status"], "unknown", False)])
def test_conditional_options_need_their_conditions_established(conditions, state, eligible):
    row = option("c", "conditional", "conditional", conditions, reason="transfer untested")
    assert K.conditions_state(row)[0] == state
    comp = run([est("a", 10.0), est("c", 40.0)], report(option("a"), row))
    c = comp.row_for("c")
    assert c.eligible is eligible and c.conditions == state
    if not eligible:
        assert c.reason.startswith(("Conditions not established", "Condition not met")) and c.rank is None
        assert c.shown                                    # drawn and labelled, never ranked


def test_rule_conditional_options_in_other_categories_also_need_conditions():
    row = option("c", "insufficient_evidence", "conditional", ["Fresh oil -> helps [unknown (ask user)]"])
    assert K.conditions_state(row)[0] == "unknown"
    assert K.conditions_state(option("d", "insufficient_evidence", "eligible"))[0] == "not_required"


def test_planting_needs_its_prerequisite_and_an_incremental_contrast_cannot_substitute():
    seq = est(K.PLANTING, 60.0, interpretation="sequence", prerequisite="mechanical_removal")
    planting = option(K.PLANTING, "conditional", "conditional", ["Elevation restored -> helps [met by input season]"])
    blocked = run([est("a", 10.0), seq], report(option("a"), planting, option("mechanical_removal", "excluded", "ineligible")))
    assert not blocked.row_for(K.PLANTING).eligible and "Requires mechanical removal" in blocked.row_for(K.PLANTING).reason
    missing = run([est("a", 10.0), seq], report(option("a"), planting))
    assert not missing.row_for(K.PLANTING).eligible
    allowed = run([est("a", 10.0), seq], report(option("a"), planting, option("mechanical_removal", "conditional", "conditional")))
    assert allowed.row_for(K.PLANTING).eligible and [r.option for r in allowed.eligible] == [K.PLANTING, "a"]
    inc = replace(seq, interpretation="incremental", comparator="mechanically treated, unplanted plots")
    comp = run([est("a", 10.0), inc], report(option("a"), planting, option("mechanical_removal", "conditional", "conditional")))
    assert not comp.rows[1].eligible and "incremental contrast cannot stand in" in comp.rows[1].reason


def test_exact_ties_share_a_rank_and_the_order_is_labelled_provisional():
    comp = run([est("a", 20.0), est("b", 20.0), est("c", 5.0), est("d", 30.0)], report(*(option(x) for x in "abcd")))
    ranks = {r.option: (r.rank, r.tied) for r in comp.eligible}
    assert ranks == {"d": (1, False), "a": (2, True), "b": (2, True), "c": (4, False)}
    assert comp.mode == "ranking" and "provisional order" in comp.title and comp.order_note == K.PROVISIONAL_NOTE
    assert "do not show that one method is better" in comp.order_note


def test_single_eligible_method_gets_no_rank_and_a_natural_recovery_title():
    comp = run([est("a", 20.0)], report(option("a")))
    assert comp.mode == "single" and comp.rows[0].rank is None and comp.order_note == K.SINGLE_NOTE
    assert "comparison with natural recovery" in comp.title
    assert K.plot_records(comp)[0]["label"] == "A"                         # no "1." prefix
    assert run([], report()).mode == "none"


def test_reference_option_is_the_zero_and_is_not_ranked():
    comp = run([est(K.REFERENCE_OPTION, 0.0), est("a", 5.0)], report(option(K.REFERENCE_OPTION, "natural_recovery_monitoring"), option("a")))
    assert not comp.rows[0].eligible and K.cell_text(comp, K.REFERENCE_OPTION) == "Reference (0)"


def test_a_synthetic_model_estimate_can_outrank_a_field_estimate_without_touching_the_recommendation():
    rep = report(option("manual_removal", "recommended"), option("modelled_option", "insufficient_evidence", "eligible"))
    frozen = copy.deepcopy(rep)
    model = est("modelled_option", 41.0, basis=K.SCENARIO_MODEL, admission=ADMITTED, interval_type="synthetic parameter uncertainty")
    comp = run([est("manual_removal", 34.0), model], rep)
    assert [(r.option, r.rank, r.est.basis) for r in comp.eligible] == [("modelled_option", 1, K.SCENARIO_MODEL), ("manual_removal", 2, K.FIELD)]
    assert rep == frozen                                                    # statuses untouched: the higher estimate is not recommended
    top = comp.eligible[0]
    assert top.screening == "insufficient_evidence" and comp.row_for("manual_removal").screening == "recommended"
    assert {p["basis"] for p in K.plot_records(comp)} == {K.SCENARIO_MODEL, K.FIELD}
    assert "is estimated to be" in K.finding(comp) and K.design_limit(comp).startswith(K.SCENARIO_MODEL)


@pytest.mark.parametrize("flag", ["same_target", "explicit_pathway", "discrepancy_documented", "evaluation_independent", "gates_respected"])
def test_a_model_estimate_without_a_complete_admission_is_not_ranked(flag):
    partial = replace(ADMITTED, **{flag: False})
    model = est("m", 99.0, basis=K.FIELD_MODEL, admission=partial)
    comp = run([est("a", 10.0), model], report(option("a"), option("m")))
    m = comp.row_for("m")
    assert not m.eligible and not m.shown and m.reason.startswith("Model estimate not admitted") and comp.mode == "single"
    assert not run([est("a", 10.0), replace(model, admission=None)], report(option("a"), option("m"))).row_for("m").eligible


def test_a_shared_source_is_recorded_and_not_counted_twice():
    field = est("a", 30.0, source_keys=("zengel2015",))
    model = est("m", 35.0, basis=K.FIELD_MODEL, admission=replace(ADMITTED, shared_sources=("zengel2015",)), source_keys=("model_card",))
    comp = run([field, model], report(option("a"), option("m")))
    assert comp.shared_sources == [("m", "a", "zengel2015")]
    assert K.independent_source_count(comp) == 2            # zengel2015 once, the model's own card once: not three
    assert K.independent_source_count(run([field], report(option("a")))) == 1


def test_unknown_basis_and_synthetic_runtime_rows_are_rejected(monkeypatch):
    with pytest.raises(ValueError):
        run([est("a", 1.0, basis="Expert guess")], report(option("a")))
    monkeypatch.setattr(K, "vegetation_year2_estimates", lambda: [est("a", 1.0)])
    with pytest.raises(ValueError):
        K.runtime_estimates(T.key)


def test_report_download_carries_the_same_values_as_the_dashboard(bay_jimmy_report):
    from src.shoreline_remediation import ui_evidence as E, ui_report
    comps = K.assessment_comparisons(bay_jimmy_report, "salt_marsh", "Heavy")
    html = ui_report.build_html(E.report_view(bay_jimmy_report), title="t", habitat="marsh", comparisons=list(comps.values()))
    assert "Field comparisons with untreated oiled plots" in html
    for comp in comps.values():
        for rec in K.table_records(comp):
            assert rec["Estimate"].replace("+", "&#x2B;") in html or rec["Estimate"] in html
    assert "+34.0 points (90% interval +19.0 to +49.0)" in html and "Zengel et al. 2015" in html
    assert "Excluded by screening" in html and "Field comparison" in html and "untreated oiled plots" in html
    assert "Field comparisons with untreated oiled plots" not in ui_report.build_html(E.report_view(bay_jimmy_report), title="t")
