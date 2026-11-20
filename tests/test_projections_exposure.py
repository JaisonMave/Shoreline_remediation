"""Session 5 of docs/CLAUDE_SCENARIO_PREDICTION_PLAN.md: offline release-and-exposure feasibility (data-gap outcome).

Software checks of the request, the inventory record and the survey export; no transport engine exists or is imported.
    python -m pytest -q tests/test_projections_exposure.py
"""
import ast
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.shoreline_remediation.projections import SpecError, check_scope, from_dict, run  # noqa: E402
from src.shoreline_remediation.projections import catalogue as C  # noqa: E402
from src.shoreline_remediation.projections.__main__ import main  # noqa: E402

EX = ROOT / "examples" / "projections" / "dwh_mobile_exposure_hindcast.json"
MISSING = ["release_location", "release_timing", "release_amount_or_rate", "oil_type", "wind_fields", "current_fields",
           "shoreline_geometry"]


def req(**changes) -> dict:
    d = json.loads(EX.read_text(encoding="utf-8"))
    d.update(changes)
    return d


@pytest.fixture(scope="module")
def gap_run(tmp_path_factory):
    out = tmp_path_factory.mktemp("x") / "exposure"
    code = main(["run", "--scenario", str(EX), "--output", str(out)])
    return code, out, json.loads((out / "manifest.json").read_text()), pd.read_csv(out / "survey_contact.csv")


def test_request_returns_a_specific_reason_recorded_in_the_manifest(gap_run):
    code, out, m, _ = gap_run
    assert code == 3
    assert sorted(p.name for p in out.iterdir()) == ["input.json", "manifest.json", "survey_contact.csv"]
    assert m["status"] == "unsupported" and m["outcome"]["code"] == "exposure_inputs_unavailable"
    for name in MISSING:
        assert name in m["outcome"]["reason"]
    assert m["exposure"]["missing_essential"] == MISSING and m["exposure"]["simulation_attempted"] is False
    assert m["outcome"]["historical_records_exported"] == ["survey_contact.csv"]
    assert m["exposure"]["data_gap_record"] == "docs/PROJECTION_EXPOSURE_DATA_GAP.md"
    status = {i["name"]: i["status"] for i in m["exposure"]["inputs"]}
    assert status["dated_shoreline_surveys"] == "present" and status["wind_fields"] == "absent" and status["oil_type"] == "proxy"
    assert all(i["found"] and i["variables_units"] and i["coverage"] for i in m["exposure"]["inputs"])
    srcs = {s["evidence_id"]: s for s in m["sources"]}
    assert set(srcs) == {"noaa_scat_mobile_visits", "noaa_scat_mobile_segments"}
    assert all(s["present"] and len(s["sha256"]) == 64 for s in srcs.values())


def test_no_contact_is_never_emitted_without_a_completed_simulation(gap_run):
    _, _, m, d = gap_run
    assert m["outcome"]["code"] != "no_contact"
    assert set(d.survey_class) == {"clear_then_oiled", "oiled_at_first_visit", "no_oil_observed", "not_visited_in_window"}
    assert "no_contact" in C.EXPOSURE_OUTCOMES and "completed" in C.EXPOSURE_OUTCOMES["no_contact"]
    assert "no_contact" not in (ROOT / "src" / "shoreline_remediation" / "projections" / "exposure.py").read_text(encoding="utf-8") \
        .split('"""', 2)[2]                                          # code (not the docstring) never writes it


def test_survey_classes_follow_the_visit_table(gap_run):
    _, _, m, d = gap_run
    v = pd.read_csv(ROOT / C.EVIDENCE["noaa_scat_mobile_visits"].path, parse_dates=["date"])
    s = m["exposure"]["survey_summary"]
    assert len(d) == d.segment.nunique() == s["segments_in_layer"] == 3007
    assert d.survey_class.value_counts().to_dict() == {k: c for k, c in s["survey_class_counts"].items() if c}
    assert (d.record_type == "observed_survey_contact").all() and (d.record_class == "observation").all()
    assert d.role.str.startswith("evaluation_observation").all()
    w = v[(v.date > "2010-04-20") & (v.date <= "2010-08-31")]
    cto = d[d.survey_class == "clear_then_oiled"].sample(50, random_state=1)
    for r in cto.itertuples():
        seg = w[w.segment == r.segment].set_index("date").status
        assert seg[pd.Timestamp(r.window_start)] == "clear" and seg[pd.Timestamp(r.window_end)] == "oiled"
        assert (seg[seg.index < pd.Timestamp(r.window_end)] != "oiled").all()      # the first oiled visit
        between = seg[(seg.index > pd.Timestamp(r.window_start)) & (seg.index < pd.Timestamp(r.window_end))]
        assert (between != "clear").all()                                         # the last clear visit before it
    ofv = d[d.survey_class == "oiled_at_first_visit"]
    assert (ofv.window_start == "2010-04-20").all() and (ofv.window_end == ofv.first_visit).all()
    nv = d[d.survey_class == "not_visited_in_window"]
    assert (nv.n_visits == 0).all() and not w.segment.isin(nv.segment).any()
    noo = d[d.survey_class == "no_oil_observed"]
    assert not w[(w.status == "oiled")].segment.isin(noo.segment).any()
    assert s["no_oil_observed_but_oiled_after_window"] + s["no_oil_observed_never_oiled_in_record"] == len(noo)
    ever = set(v[v.status == "oiled"].segment)
    assert s["candidate_false_alarm_denominator"] == int(((noo.n_clear_visits >= 2) & ~noo.segment.isin(ever)).sum()) > 0
    assert s["first_oiled_observation"] == "2010-05-17"


@pytest.mark.parametrize("changes, field", [
    ({"unit": "m"}, "unit"),
    ({"plot_group_id": "untreated_heavy"}, "plot_group_id"),
    ({"oiling_class": "Heavy"}, "oiling_class"),
    ({"arm": "intervention"}, "arm"),
    ({"evidence_ids": []}, "evidence_ids"),
    ({"habitat": "salt_marsh"}, "habitat"),
    ({"model_version": "observed_record/1"}, "model_version"),
])
def test_exposure_input_errors(changes, field):
    with pytest.raises(SpecError) as e:
        check_scope(from_dict(req(**changes)))
    assert field in dict(e.value.problems)


def test_unknown_case_and_window_outside_the_case(tmp_path):
    assert check_scope(from_dict(req(site_id="exxon_valdez_1989"))).code == "unknown_exposure_case"
    res = run(req(end_date="2010-12-31"), tmp_path / "late")
    assert res.status == "unsupported" and res.unsupported.code == "outside_domain"
    assert sorted(p.name for p in res.output_dir.iterdir()) == ["input.json", "manifest.json"]


def test_no_transport_engine_is_imported_by_the_package():
    for p in (ROOT / "src" / "shoreline_remediation" / "projections").glob("*.py"):
        tree = ast.parse(p.read_text(encoding="utf-8-sig"))
        names = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        names |= {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        assert not [n for n in names if "gnome" in n.lower() or "opendrift" in n.lower()], p.name


def test_data_gap_record_names_the_missing_inputs_and_usable_observations():
    text = (ROOT / "docs" / "PROJECTION_EXPOSURE_DATA_GAP.md").read_text(encoding="utf-8")
    for words in ("Release location", "Release amount or rate", "Wind fields", "Current fields", "Shoreline geometry",
                  "20 April 2010", "31 August 2010", "beach_visits.csv", "731", "944", "no_contact"):
        assert words in text, words
