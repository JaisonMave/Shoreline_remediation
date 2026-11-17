"""Session 3: ESI 1A/8A headline wording and the five-part answer card (presentation only).

Run from the repository root:  python -m pytest tests/test_session3_answer_card.py
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.shoreline_remediation import decision_pipeline as dp  # noqa: E402
from src.shoreline_remediation import ui_evidence as E  # noqa: E402


@pytest.fixture(scope="module")
def rocky():
    return {esi: dp.run_decision({}, habitat=esi, oiling_class="moderate") for esi in ("1A", "8A")}
from tests._nav import open_habitat  # noqa: E402


def _cls(report, option):
    return next(r for r in report.options if r["option"] == option)


# ---- headline wording (pipeline) ------------------------------------------------------------------------------
@pytest.mark.parametrize("esi", ["1A", "8A"])
def test_headline_no_longer_says_best_allowed_options(rocky, esi):
    h = rocky[esi].headline
    assert "Best allowed options" not in h and "class B" not in h
    assert h.startswith("Insufficient evidence to compare with natural recovery")


@pytest.mark.parametrize("esi", ["1A", "8A"])
def test_headline_separates_screening_eligibility_from_effectiveness(rocky, esi):
    h = rocky[esi].headline
    assert "Eligible under screening rules, but effectiveness relative to natural recovery has not been established" in h
    assert "not demonstrated remediation effectiveness" in h
    assert "not a performance ranking" in h
    for r in rocky[esi].options:
        if r["recommendation_class"] == "B":
            assert r["option"] in h


def test_class_b_options_keep_classification_and_evidence_state(rocky):
    for esi, expected in (("1A", {"passive_sorbents", "vacuum_removal", "high_pressure_washing", "low_pressure_flushing"}),
                          ("8A", {"passive_sorbents", "bioremediation", "vacuum_removal", "low_pressure_flushing"})):
        b = [r for r in rocky[esi].options if r["recommendation_class"] == "B"]
        assert {r["option"] for r in b} == expected
        assert all(r["evidence_state"] == dp.STATE_INSUFFICIENT and r["recommendation_category"] == dp.CAT_INSUFFICIENT for r in b)
        assert rocky[esi].evidence_state == dp.STATE_INSUFFICIENT


def test_manual_removal_stays_excluded_on_1a_and_conditional_on_8a(rocky):
    assert _cls(rocky["1A"], "manual_removal")["recommendation_class"] == "E"
    assert _cls(rocky["1A"], "manual_removal")["recommendation_category"] == "excluded"
    assert _cls(rocky["8A"], "manual_removal")["recommendation_class"] == "D"
    assert _cls(rocky["8A"], "manual_removal")["recommendation_category"] == "conditional"


# ---- answer-card sections (view model) -------------------------------------------------------------------------
def _sections(report):
    return E.answer_sections(E.report_view(report))


def test_insufficient_evidence_card_does_not_equate_eligibility_with_effectiveness_or_failure(rocky):
    s = _sections(rocky["1A"])
    assert "not demonstrated remediation effectiveness" in s.eligibility
    assert "is not established for: " in s.benefit and "not a finding that they do not work" in s.benefit
    assert "Manual removal" in s.excluded_names and "Manual removal" not in s.eligible_names
    assert len(s.eligible_names) == 4


def test_rocky_card_discloses_unverified_ratings_and_missing_numerical_validation(rocky):
    for esi in ("1A", "8A"):
        s = _sections(rocky[esi])
        text = " ".join(s.uncertainty)
        assert E.PROPOSED_RATINGS_TEXT in s.uncertainty and "not yet human-verified" in text
        assert E.NO_NUMERIC_TEXT in s.uncertainty
        assert E.UNCALIBRATED_TEXT in s.uncertainty and "heuristic" in text


def test_conditional_option_reason_is_shown_on_8a(rocky):
    s = _sections(rocky["8A"])
    assert any(c.startswith("Manual removal:") for c in s.conditions)
    assert "conditional" in rocky["8A"].decision_outcome


def _fake(summary, label="x", options=(), tier="rules_and_literature", out=False):
    return E.ReportView(headline="h", tier=tier, tier_grade="rules_literature", tier_text="Rules", scope_message="",
                        options=list(options), reference=[], headline_grade="rules_literature", headline_grade_text="g",
                        out_of_scope=out, decision_outcome="o", decision_outcome_label=label, recommendation_summary=summary)


def test_no_difference_and_recommended_semantics_come_from_the_summary_only():
    base = {c: [] for c in dp.CATEGORY_ORDER}
    nd = E.answer_sections(_fake({**base, "no_demonstrated_benefit": ["passive_sorbents"], "excluded": ["solidifiers"]}))
    assert "shows no clear difference from natural recovery for: Passive sorbents" in nd.benefit and "not proof" in nd.benefit
    assert "not established" not in nd.benefit
    rec = E.answer_sections(_fake({**base, "recommended": ["planting (after mechanical cleanup)"]}))
    assert rec.benefit == "h" and rec.benefit_names                       # the pipeline's own headline, not UI wording
    none = E.answer_sections(_fake({**base, "natural_recovery_monitoring": ["natural_attenuation"]}))
    assert none.eligible_names == [] and none.benefit == "No eligible option to compare with natural recovery."


def test_abstention_and_missing_summary_read_as_unavailable_not_zero():
    out = E.answer_sections(_fake({}, label="Outside the scope", tier="out_of_scope", out=True))
    assert out.eligibility.startswith("Not assessed") and out.benefit == "Not assessed."
    miss = E.answer_sections(_fake({}))
    assert miss.eligibility == "Eligibility summary unavailable for this assessment."


# ---- literal-wording guards (a change to the constants must not pass silently) ---------------------------------
def test_wording_is_pinned_literally(rocky):
    s = _sections(rocky["1A"])
    assert "No eligible evidence compares them with natural recovery" in s.benefit
    text = " ".join(s.uncertainty)
    assert "transcribed by AI from NOAA tables" in text and "not yet human-verified" in text and "not authoritative" in text
    assert "not numerically validated" in text and "No calibrated probability" in text
    assert "habitat-impact screening, not demonstrated remediation effectiveness" in s.eligibility
    assert "not a finding that they do not work" in s.benefit and "demonstrated benefit" not in s.benefit


def test_8a_conditional_reason_text_and_outcome_are_shown(rocky):
    s = _sections(rocky["8A"])
    reason = _cls(rocky["8A"], "manual_removal")["recommendation_category_reason"]
    assert reason and any(c.startswith("Manual removal: allowed") for c in s.conditions)
    assert not any("harm_flags" in c for c in s.conditions)
    assert rocky["8A"].decision_outcome == "conditional_only"


def test_category_keys_used_by_the_card_exist_in_the_pipeline():
    assert set(E.ELIGIBLE_CATEGORIES) <= set(dp.CATEGORY_ORDER)
    assert {"conditional", "excluded", "recommended", "no_demonstrated_benefit"} <= set(dp.CATEGORY_ORDER)


# ---- option-card wording (_verdict_text) -----------------------------------------------------------------------
def test_option_card_text_distinguishes_no_evidence_from_no_clear_difference(rocky):
    insuff = E.option_view(_cls(rocky["1A"], "vacuum_removal"))
    assert "no eligible evidence is available" in insuff.verdict_text and "either way" not in insuff.verdict_text
    assert "not a finding that it does not work" in insuff.verdict_text
    nd_row = next(r for r in dp.run_decision({}, habitat="3A", oiling_class="moderate").options
                  if r["recommendation_category"] == "no_demonstrated_benefit")
    nd = E.option_view(nd_row)
    assert nd.verdict_text.startswith("Evidence exists but shows no clear difference from natural recovery")
    assert "not a demonstrated benefit" in nd.verdict_text and "either way" not in nd.verdict_text


def test_excluded_and_conditional_option_text_unchanged_in_meaning(rocky):
    assert E.option_view(_cls(rocky["1A"], "manual_removal")).verdict_text.startswith("Excluded:")
    assert E.option_view(_cls(rocky["8A"], "manual_removal")).verdict_text.startswith("Allowed, but")


def test_report_level_no_difference_does_not_contradict_per_option_text():
    """Regression for a rendered contradiction: ESI 1A (medium oil) has evidence for one conditional option only. The card must
    name that option under 'no clear difference' and the evidence-free ones under 'not established'."""
    r = dp.run_decision({}, habitat="1A", oiling_class="moderate", oil="medium")
    s = _sections(r)
    assert r.evidence_state == dp.STATE_NO_DIFFERENCE
    assert "shows no clear difference from natural recovery for: High pressure heated washing" in s.benefit
    assert "is not established for: " in s.benefit and "Passive sorbents" in s.benefit.split("is not established for: ")[1]
    assert "High pressure heated washing" not in s.benefit.split("is not established for: ")[1]


def test_acronym_in_condition_text_is_not_lowercased_and_class_b_group_header_is_not_misleading():
    s = _sections(dp.run_decision({}, habitat="1A", oiling_class="moderate", oil="medium"))
    assert any("allowed, but NOAA Characteristic" in c for c in s.conditions) and not any("nOAA" in c for c in s.conditions)
    from src.shoreline_remediation import ui_theme as T
    b = T.class_style("B")
    assert "either way" not in b["name"] + b["plain"]
    assert "no eligible evidence exists yet" in b["plain"] and "benefit not established" in b["name"]


def test_marsh_worked_cell_card_keeps_headline_numbers_and_explains_conditional_planting():
    from src.shoreline_remediation import site_evidence as se
    sites = se.load_sites()
    cell = sites[sites.cell == "8018_32612"].iloc[0].to_dict()
    r = dp.run_decision(cell, label="worked cell")
    view = E.report_view(r)
    s = E.answer_sections(view)
    assert s.benefit.startswith(r.headline)                              # numbers and design come from the pipeline's headline
    assert "edge loss avoided" in s.benefit and "90%" in s.benefit
    assert any(c.startswith("Planting (after mechanical cleanup):") and "presupposes" in c for c in s.conditions)
    assert not any("treatment-specific rule applies" in c for c in s.conditions)


def test_option_card_text_keeps_noaa_acronym(rocky):
    r = dp.run_decision({}, habitat="1A", oiling_class="moderate", oil="medium")
    row = next(x for x in r.options if x["recommendation_category"] == "conditional")
    assert E.option_view(row).verdict_text.startswith("Allowed, but NOAA ")


# ---- headline: insufficient vs no-difference states (approved correction) ---------------------------------------
CAVEAT = ("Eligibility reflects habitat-impact screening, not demonstrated remediation effectiveness. "
          "The order shown is not a performance ranking.")
ELIGIBLE_LEAD = "Eligible under screening rules, but effectiveness relative to natural recovery has not been established: "


@pytest.fixture(scope="module")
def no_difference():
    return {"1A medium oil": dp.run_decision({}, habitat="1A", oiling_class="moderate", oil="medium"),
            "3A": dp.run_decision({}, habitat="3A", oiling_class="moderate")}


def test_insufficient_state_headline_lists_all_eligible_options_with_caveat(rocky):
    for esi, r in rocky.items():
        h = r.headline
        assert r.evidence_state == dp.STATE_INSUFFICIENT
        assert h.startswith("Insufficient evidence to compare with natural recovery")
        assert "Natural recovery with monitoring is the default" in h and "not a finding that treatment gives no benefit" in h
        listed = h.split(ELIGIBLE_LEAD)[1].split(". Eligibility reflects")[0].split(", ")
        assert set(listed) == {x["option"] for x in r.options if x["recommendation_class"] == "B"}
        assert h.endswith(CAVEAT)


def test_no_difference_state_headline_has_caveat_only_and_no_second_option_list(no_difference):
    for name, r in no_difference.items():
        h = r.headline
        assert r.evidence_state == dp.STATE_NO_DIFFERENCE, name
        assert ELIGIBLE_LEAD not in h and "has not been established" not in h, name
        assert h.endswith(CAVEAT) and h.count(CAVEAT) == 1, name
        assert "continue with natural recovery and monitoring" in h                       # existing wording preserved
        with_ev = h.split("shows no clear difference for: ")[1].split(". ")[0].split(", ")
        assert set(with_ev) == {x["option"] for x in r.options
                                if x["recommendation_class"] in ("B", "D") and x["evidence_state"] != dp.STATE_INSUFFICIENT}
        assert "Insufficient evidence to compare with natural recovery for: " in h, name   # both cases have evidence-free options
        without = h.split("Insufficient evidence to compare with natural recovery for: ")[1].split(". ")[0].split(", ")
        assert without and not set(with_ev) & set(without), name                       # each option is named under one verdict only


def test_class_a_headline_branch_is_unchanged_by_the_wording_fix():
    from src.shoreline_remediation import site_evidence as se
    sites = se.load_sites()
    r = dp.run_decision(sites[sites.cell == "8018_32612"].iloc[0].to_dict())
    assert r.headline.startswith("Field evidence of benefit over natural recovery:")
    assert "Eligible under screening" not in r.headline and "Eligibility reflects" not in r.headline


def test_manual_removal_classes_are_pinned_to_the_pre_change_values():
    """Values recorded from HEAD 29aba8d (before the wording fixes). Manual removal depends on the oil setting through the NOAA
    oil category; the default oil setting gives 1A excluded / 8A conditional, medium oil gives class B on both."""
    expected = {("1A", None): ("E", "excluded"), ("1A", "medium"): ("B", "insufficient_evidence"),
                ("1A", "heavy"): ("B", "insufficient_evidence"), ("8A", None): ("D", "conditional"),
                ("8A", "medium"): ("B", "insufficient_evidence"), ("8A", "heavy"): ("D", "conditional")}
    for (esi, oil), (cls, cat) in expected.items():
        row = _cls(dp.run_decision({}, habitat=esi, oiling_class="moderate", oil=oil), "manual_removal")
        assert (row["recommendation_class"], row["recommendation_category"]) == (cls, cat), (esi, oil)


def test_expander_is_renamed_in_the_rendered_card():
    from streamlit.testing.v1 import AppTest
    app = str(Path(__file__).resolve().parent.parent / "src" / "shoreline_remediation" / "dashboard.py")
    at = AppTest.from_file(app, default_timeout=300)
    at.run()
    open_habitat(at, f"hab_esi_1a")
    assert not at.exception, at.exception
    labels = [e.label for e in at.expander]
    assert "Pipeline's full text statement (technical wording)" in labels
    assert not any(l == "Full pipeline statement" for l in labels)


def test_option_codes_in_condition_text_are_shown_as_plain_names():
    """Rendered-QA finding: the planting condition quoted the internal code 'mechanical_removal'."""
    from src.shoreline_remediation import site_evidence as se, ui_components as C
    sites = se.load_sites()
    view = E.report_view(dp.run_decision(sites[sites.cell == "8018_32612"].iloc[0].to_dict()))
    cond = next(c for c in E.answer_sections(view).conditions if c.startswith("Planting"))
    assert "mechanical_removal" in cond                                     # the pipeline's own reason carries the code
    shown = C.humanise(cond, view.options)
    assert "mechanical_removal" not in shown and "mechanical removal" in shown


def test_rendered_marsh_card_shows_no_raw_option_code_in_conditions():
    from tests.test_dashboard_v5 import fresh, all_text
    txt = all_text(fresh())
    assert "4. Conditions and restrictions" in txt
    assert "presupposes 'mechanical_removal'" not in txt and "presupposes 'mechanical removal'" in txt
