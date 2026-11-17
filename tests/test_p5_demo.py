"""P5: deployed edge-loss model, site flags, treatment evidence and the dashboard (plan: docs/P5_DEMO_PLAN.md)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from src.shoreline_remediation.site_evidence import (FEATURES, STATUS_TEXT, load_model, load_sites,  # noqa: E402
                                                     predict_edge_loss, site_flags, site_scenario,
                                                     treatment_evidence)
from src.shoreline_remediation.site_view import EXAMPLE_CELL  # noqa: E402
from src.shoreline_remediation.treatment_effects import erosion_prior  # noqa: E402

MODEL = load_model()
SITES = load_sites()
IN = SITES[SITES.status == "in_scope"]


def values(row) -> dict:
    return {f: float(row[f]) for f in FEATURES}


def test_artefact_reproduces_p2_heldout_predictions():
    # same model (M1), same training basins -> identical held-out predictions to P2's predictions.csv
    both = SITES.dropna(subset=["lobo_pred", "p2_heldout_M1"])
    assert len(both) > 8000
    assert np.allclose(both.lobo_pred, both.p2_heldout_M1, atol=1e-3)


def test_scope_status_matches_training_set():
    assert (SITES.status == "in_scope").sum() == MODEL["training_cells"]
    assert set(SITES.status) <= set(STATUS_TEXT)
    assert IN[FEATURES + ["observed_rate"]].notna().all().all()
    assert (SITES.loc[(SITES.basin == "birdfoot") & (SITES.esi_main == "10A"), "status"] == "river_delta").all()
    assert (SITES.loc[SITES.esi_main != "10A", "status"] == "not_salt_marsh").all()


def test_prediction_is_linear_model_with_interval():
    row = IN.iloc[0]
    v = values(row)
    x = np.array([1, v["water_1km_2010"], v["water_250m_2010"], np.log(v["fetch_mean_m"] + 16), v["pre_rate"]])
    p = predict_edge_loss(v)
    assert p["rate"] == pytest.approx(float(x @ np.array(MODEL["coefficients"])))
    lo, hi = MODEL["interval_offsets"]
    assert p["lo"] == pytest.approx(p["rate"] + lo) and p["hi"] == pytest.approx(p["rate"] + hi)
    assert lo < 0 < hi and MODEL["interval_level"] == 0.90
    assert MODEL["lobo_mae"] < MODEL["lobo_mae_no_predictor"]  # beats the no-predictor baseline held out
    with pytest.raises(ValueError):
        predict_edge_loss({**v, "pre_rate": None})


def test_flags():
    row = IN[IN.max_oiling == "Heavy"].iloc[0]
    f = site_flags(values(row), "in_scope", "10A", "Heavy", row.lat, row.lon)
    assert f.in_scope and not f.extrapolation and not f.evidence_scope
    delta = SITES[SITES.status == "river_delta"].iloc[0]
    assert not site_flags(values(delta), delta.status, delta.esi_main, delta.max_oiling).in_scope
    beach = site_flags(values(row), "in_scope", "3A", "Heavy")
    assert not beach.in_scope and "salt marsh" in beach.out_of_scope[0]
    far = site_flags({**values(row), "pre_rate": 50.0}, "in_scope", "10A", "Light", 40.0, -70.0)
    assert far.in_scope and len(far.extrapolation) == 2 and far.evidence_scope
    assert not site_flags({**values(row), "fetch_mean_m": None}).in_scope


def test_treatment_evidence_uses_priors_and_says_when_there_is_none():
    ev = treatment_evidence(["manual_removal", "mechanical_removal", "natural_attenuation", "solidifiers"]).set_index("treatment")
    a = erosion_prior("manual", "2010-2012")
    assert ev.at["manual_removal", "erosion_0_2"].startswith(f"{a['effect']:+.2f}")
    assert ev.at["natural_attenuation", "erosion_0_2"].startswith("baseline")
    assert ev.at["solidifiers", "erosion_0_2"] == "no outcome evidence"
    assert "planting (after mechanical cleanup)" in ev.index
    assert "confounded" in ev.at["mechanical_removal", "note"]


def test_worked_example_follows_the_fixed_rule():
    import build_p5_demo as b  # noqa: E402
    assert b.example_cell(SITES).cell == EXAMPLE_CELL
    assert EXAMPLE_CELL in (ROOT / "docs" / "P5_WORKED_EXAMPLE.md").read_text()


def test_site_scenario_is_salt_marsh():
    s = site_scenario(IN[IN.max_oiling == "Heavy"].iloc[0].to_dict())
    assert s.shoreline_type == "marsh" and s.habitat_type == "salt_marsh" and s.oil_coverage == 80.0


def test_model_card_has_provenance():
    m = json.loads((ROOT / "models" / "p5_edge_loss_v1.json").read_text())
    for key in ("target", "algorithm", "training_cells", "interval_method", "validation", "training_files_sha256",
                "measurement_note", "built"):
        assert m[key]
    import hashlib
    for rel, digest in m["training_files_sha256"].items():
        assert hashlib.sha256((ROOT / "data" / "external" / "p2" / rel).read_bytes()).hexdigest() == digest


@pytest.fixture(scope="module")
def app():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / "src" / "shoreline_remediation" / "dashboard.py"), default_timeout=180)
    at.run()
    at.segmented_control(key="page").set_value("site").run()   # the default page is now the landing page
    return at


def _all_text(at) -> str:
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption] + [i.value for i in at.info] + [w.value for w in at.warning]
    parts += [str(t.value.to_numpy().ravel().tolist()) + " ".join(map(str, t.value.columns)) for t in at.dataframe]
    return " ".join(parts)


def _fresh_app():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / "src" / "shoreline_remediation" / "dashboard.py"), default_timeout=300)
    at.run()
    at.segmented_control(key="page").set_value("site").run()   # the default page is now the landing page
    return at


def test_dashboard_site_view_runs_on_worked_example(app):
    assert not app.exception, app.exception
    assert app.segmented_control(key="page").value == "site"
    metrics = {m.label: m.value for m in app.metric}
    assert any(l.startswith("Expected marsh-edge loss") and v.endswith("m/yr") for l, v in metrics.items())
    assert any("Extra erosion vs natural recovery, years 0 to 2" in t.value.columns for t in app.dataframe)


def test_dashboard_new_site_gets_no_site_model(app):
    """A typed site has no row in the site table: it is never treated as an in-scope model cell (V5.4 plot-first)."""
    app.radio(key="site_mode").set_value("New site (enter values)").run()
    assert not app.exception, app.exception
    assert not any(n.key == "new_pre" for n in app.number_input)           # no typed model inputs
    assert not any(m.label.startswith("Expected marsh-edge loss") for m in app.metric)
    assert not any("extrapolation" in w.value.lower() for w in app.warning)


def test_dashboard_out_of_scope_cell_has_no_prediction(app):
    app.radio(key="site_mode").set_value("Pick a Louisiana edge cell").run()
    app.selectbox(key="pick_basin").set_value("birdfoot").run()
    app.checkbox(key="pick_scope").uncheck().run()
    assert not app.exception, app.exception
    assert any("river delta" in e.value.lower() for e in app.error)
    assert not any(m.label.startswith("Expected marsh-edge loss") for m in app.metric)


def test_dashboard_scenario_view_still_runs():
    at = _fresh_app()
    at.segmented_control(key="page").set_value("legacy").run()
    at.sidebar.button[0].click().run()
    assert not at.exception, at.exception
    at.segmented_control(key="scenario_section").set_value("Method test (synthetic data)").run()
    assert not at.exception, at.exception
    assert "synthetic" in _all_text(at)


def test_compare_options_detail_tables_for_worked_example():
    at = _fresh_app()
    assert not at.exception, at.exception
    cols = [set(t.value.columns) for t in at.dataframe]
    assert any("Range excludes zero, edge loss (yr 2 / 5 / 8)" in c and "Evidence" in c for c in cols)
    assert any("Marsh area lost vs natural recovery, year 8 (ha)" in c for c in cols)
    assert any("Condition to check" in c for c in cols)
    cell_table = next(t.value for t in at.dataframe if "Range excludes zero, edge loss (yr 2 / 5 / 8)" in t.value.columns)
    assert not any(str(v).startswith(("AI", "ELICITED")) for v in cell_table.Evidence)
    assert "AI-proposed range, not evidence" in _all_text(at)


def test_site_headline_is_clean_baseline_for_worked_example():
    from src.shoreline_remediation import scenario_composer as sc
    at = _fresh_app()
    headline = next(m.value for m in at.metric if m.label.startswith("Expected marsh-edge loss"))
    site = SITES[SITES.cell == EXAMPLE_CELL].iloc[0].to_dict()
    assert headline == f"{sc.natural_recovery_summary(site)['baseline']['rate']:.2f} m/yr"


def test_compare_options_out_of_scope_site_says_no_prediction_not_error():
    at = _fresh_app()
    at.radio(key="site_mode").set_value("Pick a Louisiana edge cell").run()
    at.selectbox(key="pick_basin").set_value("birdfoot").run()
    at.checkbox(key="pick_scope").uncheck().run()
    assert not at.exception, at.exception
    assert any("No prediction for this site" in i.value for i in at.info)
    assert not any("Range excludes zero, edge loss (yr 2 / 5 / 8)" in t.value.columns for t in at.dataframe)


def test_mangrove_mode_renders_with_no_marsh_model():
    at = _fresh_app()
    at.segmented_control(key="site_habitat").set_value("mangrove").run()
    assert not at.exception, at.exception
    assert any(s.value == "Oiling effect by year since the spill" for s in at.subheader)
    assert not any(m.label.startswith("Expected marsh-edge loss") for m in at.metric)
    assert any({"Verdict", "Reason", "Conditions", "Source", "Evidence class"} <= set(t.value.columns) for t in at.dataframe)


def test_marsh_mode_is_default_and_unchanged_after_switching_back():
    at = _fresh_app()
    assert at.segmented_control(key="site_habitat").value == "marsh"
    base = {m.label: m.value for m in at.metric}
    at.segmented_control(key="site_habitat").set_value("mangrove").run()
    at.segmented_control(key="site_habitat").set_value("marsh").run()
    assert not at.exception, at.exception
    assert {m.label: m.value for m in at.metric} == base
