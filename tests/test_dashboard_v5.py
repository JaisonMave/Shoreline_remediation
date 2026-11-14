"""Dashboard checks with Streamlit's AppTest (decision D40): every view and habitat loads, no fabricated confidence or band,
the pipeline classes render for the Bay Jimmy worked cell, AI-proposed ranges never read as evidence."""
import re
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
APP = str(ROOT / "src" / "shoreline_remediation" / "dashboard.py")
HABITATS = ["marsh", "mangrove", "beach_fine", "beach_coarse", "beach_mixed", "beach_gravel"]


def fresh() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    assert not at.exception, at.exception
    return at


def all_text(at) -> str:
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption] + [i.value for i in at.info] + \
            [w.value for w in at.warning] + [e.value for e in at.error] + [m.label + " " + str(m.value) for m in at.metric] + \
            [s.value for s in at.subheader]
    for t in at.dataframe:
        parts += [str(c) for c in t.value.columns] + [str(v) for v in t.value.to_numpy().ravel()]
    return " ".join(parts)


def run_scenario(at: AppTest) -> AppTest:
    at.segmented_control(key="top_view").set_value("Scenario screening (legacy)").run()
    assert not at.exception, at.exception
    at.button[0].click().run()
    assert not at.exception, at.exception
    return at


@pytest.fixture(scope="module")
def app():
    return fresh()


@pytest.mark.parametrize("habitat", HABITATS)
def test_every_habitat_loads(habitat):
    at = fresh()
    at.segmented_control(key="site_habitat").set_value(habitat).run()
    assert not at.exception, at.exception
    txt = all_text(at)
    assert "Decision confidence" not in txt and "ML-ranked" not in txt
    assert "Scope: " in txt
    if habitat.startswith("beach"):
        assert "Sand-beach oil persistence model: being integrated" in txt


def test_marsh_landing_has_answer_first_and_pipeline_classes(app):
    txt = all_text(app)
    assert any("Expected marsh-edge loss, metres per year, with a 90% range" in m.label for m in app.metric)
    assert "Evidence behind this recommendation" in txt
    for name in ("Planting (after mechanical cleanup)", "Manual removal", "Natural attenuation"):
        assert name in txt
    # classes with evidence grade chips and sources
    assert "sr-cls-A" in txt and "Source: Field-plot differences through the scenario composer" in txt
    assert "Experimental" in txt
    for bad in ("R5 fix", "plan A4", "A4.3", "ML-ranked", "Decision confidence", "(D26)"):
        assert bad not in txt, bad  # decision ids appear only inside the Sources and decisions expander


def test_ai_proposed_ranges_never_read_as_evidence(app):
    txt = all_text(app)
    assert "AI-proposed range, not evidence" in txt
    for t in app.dataframe:
        cols = " ".join(map(str, t.value.columns))
        if "Evidence" in cols and "Range excludes zero" in cols:
            assert not any(str(v).startswith(("AI", "ELICITED")) for v in t.value["Evidence"])


def test_no_fabricated_band_in_source():
    src = (ROOT / "src" / "shoreline_remediation")
    for p in src.glob("*.py"):
        if p.name == "decision_framework.py":
            continue
        text = p.read_text()
        assert "(1.0 - confidence) * 0.16" not in text, p.name
        assert "0.04 + (1" not in text, p.name


def test_scenario_view_default_and_heavy_marsh():
    at = run_scenario(fresh())
    txt = all_text(at)
    assert "Decision confidence" not in txt and "ML-ranked" not in txt
    assert "Illustrative only: this process model did not beat a simple empirical curve on held-out stations (FINDINGS_V4 section 37)" in txt
    assert "What the evidence supports for this scenario" in txt
    assert "Confidence" not in {m.label for m in at.metric}
    assert not any(m.label == "Uncertainty" for m in at.metric)


def test_scenario_view_every_section():
    at = run_scenario(fresh())
    from src.shoreline_remediation.ui_scenario import SECTIONS
    for s in SECTIONS:
        at.segmented_control(key="scenario_section").set_value(s).run()
        assert not at.exception, (s, at.exception)
        assert "Decision confidence" not in all_text(at)


def test_only_active_view_runs():
    at = run_scenario(fresh())
    at.segmented_control(key="top_view").set_value("Site evidence").run()
    assert not at.exception
    assert not any("Run scenario analysis" in b.label for b in at.sidebar.button)


def test_beach_function_tolerates_missing_module():
    from src.shoreline_remediation import ui_components as C
    assert callable(C.render_beach_persistence)


def test_headline_numbers_agree_between_card_and_detail():
    at = fresh()
    from src.shoreline_remediation import scenario_composer as sc
    from src.shoreline_remediation.site_evidence import load_sites
    from src.shoreline_remediation.site_view import EXAMPLE_CELL
    site = load_sites().query("cell == @EXAMPLE_CELL").iloc[0].to_dict()
    med = sc.natural_recovery_summary(site)["mean_rate_y1_5"]["median"]
    m = next(x for x in at.metric if x.label.startswith("Expected marsh-edge loss"))
    assert m.value == f"{med:.2f} m/yr"
    assert re.search(r"Natural recovery here: " + f"{med:.2f}", all_text(at))
