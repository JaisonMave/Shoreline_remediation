"""Decision board (V5.1 Stage 2): presenter membership, flags, abstention and the Site assessment run button.

Run from the repository root:  python -m pytest tests/test_decision_board.py
Dashboard-presentation checks only. They do not validate any model: the board must show exactly what decision_pipeline returned.
"""
import re
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
APP = str(ROOT / "src" / "shoreline_remediation" / "dashboard.py")

from src.shoreline_remediation import site_evidence as se, ui_decision_board as B, ui_pipeline as P  # noqa: E402
from src.shoreline_remediation.data_model import Scenario  # noqa: E402
from src.shoreline_remediation.decision_pipeline import CAT_NATURAL, CATEGORY_ORDER  # noqa: E402

EXAMPLE_CELL = "8018_32612"
N = 200


def _scenario_report(shoreline_type: str, habitat: str, oiling: str = "Moderate"):
    scen = Scenario(shoreline_type=shoreline_type, wave_exposure="moderate", oil_category="medium")
    report, err = P.decision_for_scenario(P.scenario_items(scen), oiling, "medium", None, habitat, N)
    assert err is None, err
    return report


@pytest.fixture(scope="module")
def marsh():
    site = se.load_sites().query("cell == @EXAMPLE_CELL").iloc[0].to_dict()
    report, err = P.decision_for_site(P.site_items(site), "light", None, N)
    assert err is None, err
    flags = se.site_flags({f: site.get(f) for f in se.FEATURES}, site["status"], site["esi_main"], site["max_oiling"],
                          site.get("lat"), site.get("lon"))
    return report, flags


@pytest.fixture(scope="module", params=["1A", "8A"])
def rocky(request):
    return _scenario_report("rocky_shore", request.param)


@pytest.fixture(scope="module")
def unsupported():
    return _scenario_report("rocky_shore", "coral reef")


def _members(model):
    return {c.category: c.options for c in model.cards}


def _expected(report):
    return {c: list(report.recommendation_summary[c]) for c in CATEGORY_ORDER if report.recommendation_summary.get(c)}


def test_marsh_cards_equal_the_recommendation_summary(marsh):
    report, flags = marsh
    model = B.board_model(report, flags)
    got, want = _members(model), _expected(report)
    want.setdefault(CAT_NATURAL, [])
    assert got == want
    assert [c.category for c in model.cards] == [c for c in CATEGORY_ORDER if c in got]      # CATEGORY_ORDER, nothing re-sorted
    assert "no_demonstrated_benefit" in got                                                  # the "Allowed, no demonstrated benefit" card
    assert model.outcome_label == report.decision_outcome_label and model.scope_message == report.scope_message
    for card in model.cards:                                                                 # rows are the report's own rows, unchanged
        for name, row in card.rows.items():
            assert row is next(r for r in report.options if r["option"] == name)


def test_rocky_cards_equal_the_recommendation_summary(rocky):
    model = B.board_model(rocky)
    want = _expected(rocky)
    assert _members(model) == want
    assert not model.refused and model.scope_tier == rocky.scope_tier


def test_unsupported_habitat_abstains_with_no_technology_cards(unsupported):
    model = B.board_model(unsupported)
    assert model.refused and model.cards == []
    assert all(not v for v in unsupported.recommendation_summary.values())
    assert [f.text for f in model.flags] == [a["text"] for a in unsupported.abstentions]
    assert model.outcome_label == unsupported.decision_outcome_label


def test_flags_equal_abstentions_advisories_and_site_flags_verbatim(marsh, rocky):
    report, flags = marsh
    model = B.board_model(report, flags)
    site_texts = flags.out_of_scope + flags.extrapolation + flags.evidence_scope
    assert [f.text for f in model.flags] == [a["text"] for a in report.abstentions] + list(report.advisories) + site_texts
    assert [f.kind for f in model.flags[:len(report.abstentions)]] == [a["kind"] for a in report.abstentions]
    model = B.board_model(rocky)
    assert [f.text for f in model.flags] == [a["text"] for a in rocky.abstentions] + list(rocky.advisories)


def test_natural_recovery_card_is_always_present_and_carries_its_reference_rows(marsh, rocky):
    for report in (marsh[0], rocky):
        model = B.board_model(report)
        nat = [c for c in model.cards if c.is_natural]
        assert len(nat) == 1 and nat[0].category == CAT_NATURAL
        assert nat[0].reference == list(report.natural_recovery["reference"])
    quantities = {r["quantity"]: r for r in B.board_model(marsh[0]).cards[2].reference}
    edge = next(r for q, r in quantities.items() if q.startswith("edge-loss rate"))
    assert edge["model_id"] == "edge_loss_v1" and edge["state"]                                # model id and registry state come with the row


def test_summary_empty_means_no_cards():
    from src.shoreline_remediation.decision_pipeline import DecisionReport
    empty = DecisionReport(headline="", scope_tier="rules_and_literature", scope_message="m", options=[], natural_recovery={}, plots={},
                           trace=[], version={}, recommendation_summary={c: [] for c in CATEGORY_ORDER})
    assert B.board_model(empty).cards == []


# ---------------------------------------------------------------------------------------------------------------
# Rendering through the app

def _text(at) -> str:
    raw = " ".join(str(e.value) for group in (at.markdown, at.caption, at.info, at.warning, at.error, at.subheader) for e in group)
    return re.sub(r"<[^>]+>", " ", re.sub(r"<style.*?</style>", " ", raw, flags=re.S))


def _open(habitat_key: str) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    at.button(key=f"sr_open_site_{habitat_key}").click().run()
    assert not at.exception, at.exception
    return at


def test_site_page_shows_no_board_until_run_is_pressed_then_marsh_board():
    at = _open("marsh")
    assert "Nothing has been run yet" in _text(at)
    at.button(key="run_marsh").click().run()
    assert not at.exception, at.exception
    text = _text(at)
    assert "Remediation assessment" in text and "Natural recovery with monitoring (reference option)" in text
    assert "Allowed, no demonstrated benefit over natural recovery" in text
    assert not re.search(r"confidence[^.]{0,40}\d", text, flags=re.I)
    assert any(e.label.startswith("Technical trace") for e in at.expander)
    at.selectbox(key="site_oil").set_value("heavy").run()                       # an edited scenario is flagged, not silently re-run
    assert "changed since this run" in _text(at)


def test_site_page_rocky_runs_through_the_scenario_path():
    at = _open("hab_esi_1a")
    at.button(key="run_esi_1A").click().run()
    assert not at.exception, at.exception
    text = _text(at)
    assert "Rules and literature" in text and "Natural recovery with monitoring (reference option)" in text
    assert "Excluded" in text


def test_new_site_goes_through_the_scenario_path_and_is_not_called_in_scope():
    at = _open("marsh")
    at.radio(key="site_mode").set_value("New site (enter values)").run()
    at.button(key="run_marsh").click().run()
    assert not at.exception, at.exception
    text = _text(at)
    assert "no edge cell given: generic marsh scenario" in text            # the pipeline's own abstention text
    assert "Experimental" in text                                          # the tier the pipeline returned
    assert "no model scope status is assigned" in text


def test_mangrove_run_and_named_oil_search_work():
    at = _open("mangrove")
    at.button(key="run_mangrove").click().run()
    assert not at.exception, at.exception
    assert "Remediation assessment" in _text(at)
    at = _open("marsh")
    at.text_input(key="site_named_q").set_value("South Louisiana").run()
    assert not at.exception, at.exception
    assert at.selectbox(key="site_named_id").options
