"""Bay Jimmy vegetation-cover what-if in the Assessment panel and its replay through the projections CLI (cover_whatif/1).

The dashboard is driven with Streamlit AppTest; the exact bytes its download buttons serve are replayed with the CLI into a
fresh directory and compared row by row at the declared export precision."""
from __future__ import annotations

import copy
import csv
import datetime as dt
import io
import json
from pathlib import Path

import pytest

from src.shoreline_remediation.projections import cover as CV, whatif as W
from src.shoreline_remediation.projections.__main__ import main as cli

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "src" / "shoreline_remediation" / "dashboard.py")
D = dt.date


@pytest.fixture()
def served(monkeypatch):
    from streamlit.runtime.memory_media_file_storage import MemoryMediaFileStorage
    files: dict = {}
    original = MemoryMediaFileStorage.load_and_get_id

    def record(self, path_or_data, mimetype, kind, filename=None):
        data = path_or_data if isinstance(path_or_data, bytes) else (
            path_or_data.encode("utf-8") if isinstance(path_or_data, str) else Path(path_or_data).read_bytes())
        files.setdefault(filename, []).append(data)
        return original(self, path_or_data, mimetype, kind, filename)

    monkeypatch.setattr(MemoryMediaFileStorage, "load_and_get_id", record)
    return files


def _panel(technique="manual_removal"):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    at.button(key="home_use_bay_jimmy").click().run()
    at.button(key="home_run").click().run()
    at.session_state["bj_future_panel"] = True
    at.run()
    if technique:
        at.selectbox(key="bj_future_option").set_value(technique).run()
    at.segmented_control(key="bj_future_outcome").set_value("cover").run()
    assert not at.exception, at.exception
    return at


def _enter(at, delta, start=D(2030, 1, 1), peak=D(2032, 1, 1), stop=D(2034, 1, 1), end=D(2040, 1, 1)):
    at.date_input(key="bj_cover_end").set_value(end).run()
    at.date_input(key="bj_cover_start").set_value(start).run()
    at.date_input(key="bj_cover_peak").set_value(peak).run()
    at.date_input(key="bj_cover_stop").set_value(stop).run()
    at.number_input(key="bj_cover_delta").set_value(delta).run()
    assert not at.exception, at.exception


def text(at) -> str:
    return " ".join(str(e.value) for g in (at.markdown, at.caption, at.info, at.warning) for e in g)


# ---- panel ------------------------------------------------------------------------------------------------------------

def test_cover_panel_anchors_on_the_last_untreated_survey_and_keeps_field_evidence():
    at = _panel()
    t = text(at)
    assert "September 2016" in t and "date precision: month" in t and "70.0%" in t and "5 plots" in t
    assert "Natural recovery scenario: cover held at the last observed value" in t
    assert "+34.0 percentage points" in t and "52% vs 18%" in t and "Observational" in t and "+19.0 to +49.0" in t
    assert at.number_input(key="bj_cover_delta").value is None                   # future effect blank
    assert "Allowed: -70.0 to +30.0 percentage points" in t and "temporary" in t
    assert "User-defined what-if, manual removal" not in t


def test_cover_whatif_peak_values_bounds_and_zero():
    at = _panel()
    _enter(at, 10.0)
    t = text(at)
    assert ("At the peak (01 Jan 2032): natural recovery 70.0%; treatment scenario 80.0%; difference +10.0 percentage "
            "points.") in t
    at.number_input(key="bj_cover_delta").set_value(35.0).run()
    t = text(at)
    assert "would be 105.0%" in t and "between -70.0 and +30.0 percentage points" in t and "treatment scenario" not in t
    at.number_input(key="bj_cover_delta").set_value(0.0).run()
    assert "coincide (0.0 percentage points)" in text(at)
    at.number_input(key="bj_cover_delta").set_value(-25.0).run()
    assert "treatment scenario 45.0%; difference -25.0 percentage points" in text(at)


def test_passive_sorbents_has_no_measured_cover_effect_and_planting_is_blocked():
    at = _panel("passive_sorbents")
    assert "There is no measured Bay Jimmy cover effect for passive sorbents" in text(at)
    assert at.number_input(key="bj_cover_delta").value is None
    at.selectbox(key="bj_future_option").set_value("planting (after mechanical cleanup)").run()
    t = text(at)
    assert "No what-if for planting (after mechanical cleanup)." in t and "Presupposes mechanical_removal" in t
    assert not any(n.key == "bj_cover_delta" for n in at.number_input)


def test_switching_technique_clears_the_cover_assumption():
    at = _panel()
    _enter(at, 10.0, start=D(2031, 3, 1))
    assert "User-defined what-if, manual removal." in text(at)
    at.selectbox(key="bj_future_option").set_value("passive_sorbents").run()
    assert at.number_input(key="bj_cover_delta").value is None and at.date_input(key="bj_cover_start").value == D(2027, 1, 1)
    assert "User-defined what-if" not in " ".join(str(m.value) for m in at.markdown)


def test_retreat_remains_the_default_outcome():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    at.button(key="home_use_bay_jimmy").click().run()
    at.button(key="home_run").click().run()
    at.session_state["bj_future_panel"] = True
    at.run()
    assert at.segmented_control(key="bj_future_outcome").value == "retreat"
    assert "31.06 m since December 2010" in text(at) and not any(d.key == "bj_cover_end" for d in at.date_input)


# ---- replay of the actual download ------------------------------------------------------------------------------------

def _download(served, tmp_path, delta=10.0, **kw):
    at = _panel()
    _enter(at, delta, **kw)
    path = tmp_path / "bay_jimmy_cover_whatif.json"
    path.write_bytes(served["bay_jimmy_cover_whatif.json"][-1])
    return path, served["bay_jimmy_cover_whatif.csv"][-1].decode("utf-8")


def _replay(scenario, out):
    code = cli(["run", "--scenario", str(scenario), "--output", str(out)])
    return code, json.loads((out / "manifest.json").read_text(encoding="utf-8"))


def test_cover_download_replays_row_for_row(served, tmp_path):
    scenario, dashboard_csv = _download(served, tmp_path)
    data = json.loads(scenario.read_text(encoding="utf-8"))
    assert data["model_version"] == CV.COVER_MODEL and data["endpoint"] == "total_vegetation_cover"
    assert data["treatment_effect"] == {"intervention_start": "2030-01-01", "effect_peak": "2032-01-01",
                                        "effect_end": "2034-01-01", "peak_change": 10.0, "unit": "percentage points",
                                        "origin": "user_assumption", "source": "Bay Jimmy Assessment what-if controls"}
    assert data["exported_outputs"]["baseline"] == CV.BASELINE_LABEL and data["technique"] == "manual_removal"
    code, manifest = _replay(scenario, tmp_path / "replay")
    assert code == 0 and manifest["status"] == "completed"
    replay_csv = (tmp_path / "replay" / W.CSV_NAME).read_text(encoding="utf-8")
    assert replay_csv.splitlines() == dashboard_csv.splitlines()
    rows = list(csv.DictReader(io.StringIO(replay_csv)))
    assert [r["date"] for r in rows if r["arm"] == "observed"] == ["2011-09", "2012-09", "2013-09", "2014-09", "2015-09", "2016-09"]
    by = {(r["date"], r["arm"]): r for r in rows}
    for date, value in (("2030-01-01", "70.000000"), ("2031-01-01", "75.000000"), ("2032-01-01", "80.000000"),
                        ("2033-01-01", "75.000000"), ("2034-01-01", "70.000000")):
        assert by[(date, CV.TREATMENT_ARM)]["total_cover"] == value
        assert by[(date, CV.NATURAL_ARM)]["total_cover"] == "70.000000"
    assert by[("2032-01-01", CV.TREATMENT_ARM)]["sample"] == "effect_peak"
    assert {r["unit"] for r in rows} == {"percent"}
    w = manifest["whatif"]
    assert w["baseline"]["survey"] == "2016-09" and w["baseline"]["date_precision"] == "month"
    assert w["summary"]["difference_pp"] == 10.0 and w["exported_outputs_check"]["status"] == "matches"
    assert w["screening"]["what_if_allowed"] and "trampling" in " ".join(w["screening"]["unresolved_conditions"])
    assert cli(["run", "--scenario", str(scenario), "--output", str(tmp_path / "replay")]) == 4


def test_cover_replay_rescreens_and_ignores_edited_outputs(served, tmp_path):
    scenario, dashboard_csv = _download(served, tmp_path, delta=-20.0, start=D(2030, 3, 15), peak=D(2031, 8, 20),
                                        stop=D(2033, 2, 10))
    data = json.loads(scenario.read_text(encoding="utf-8"))
    code, manifest = _replay(scenario, tmp_path / "offgrid")
    assert code == 0 and (tmp_path / "offgrid" / W.CSV_NAME).read_text(encoding="utf-8").splitlines() == dashboard_csv.splitlines()
    assert manifest["whatif"]["summary"]["treatment_pct"] == 50.0 and manifest["whatif"]["summary"]["peak_date"] == "2031-08-20"
    edited = copy.deepcopy(data)
    edited["exported_outputs"]["summary"]["treatment_pct"] = 95.0
    next(r for r in edited["exported_outputs"]["rows"] if r["sample"] == "effect_peak" and r["arm"] == CV.TREATMENT_ARM
         )["total_cover"] = 95.0
    (tmp_path / "edited.json").write_text(json.dumps(edited), encoding="utf-8")
    code, m2 = _replay(tmp_path / "edited.json", tmp_path / "edited")
    assert code == 0 and m2["whatif"]["summary"]["treatment_pct"] == 50.0
    assert m2["whatif"]["exported_outputs_check"]["status"] == "differs" and m2["run_id"] == manifest["run_id"]
    blocked = {**data, "technique": "planting (after mechanical cleanup)"}
    (tmp_path / "blocked.json").write_text(json.dumps(blocked), encoding="utf-8")
    assert cli(["validate", "--scenario", str(tmp_path / "blocked.json")]) == 3
    code, m3 = _replay(tmp_path / "blocked.json", tmp_path / "blocked")
    assert code == 3 and m3["outcome"]["code"] == "technique_blocked_by_screening"
    assert CV.TREATMENT_ARM not in (tmp_path / "blocked" / W.CSV_NAME).read_text(encoding="utf-8")


def test_cover_zero_and_blank_downloads_replay(served, tmp_path):
    scenario, dashboard_csv = _download(served, tmp_path, delta=0.0)
    code, manifest = _replay(scenario, tmp_path / "zero")
    assert code == 0 and (tmp_path / "zero" / W.CSV_NAME).read_text(encoding="utf-8").splitlines() == dashboard_csv.splitlines()
    assert manifest["whatif"]["treatment_applied"] and manifest["whatif"]["summary"]["difference_pp"] == 0.0
    blank = json.loads(scenario.read_text(encoding="utf-8"))
    blank["treatment_effect"] = None
    (tmp_path / "blank.json").write_text(json.dumps(blank), encoding="utf-8")
    code, m2 = _replay(tmp_path / "blank.json", tmp_path / "blank")
    assert code == 0 and not m2["whatif"]["treatment_applied"]
    assert CV.TREATMENT_ARM not in (tmp_path / "blank" / W.CSV_NAME).read_text(encoding="utf-8")


@pytest.mark.parametrize("change,where", [
    ({"peak_change": 35.0}, "treatment_effect"),                               # 105% at the peak
    ({"peak_change": -71.0}, "treatment_effect"),                              # below 0%
    ({"effect_peak": "2035-01-01"}, "treatment_effect"),                       # out of order
    ({"unit": "percent"}, "treatment_effect.unit"),
    ({"rate_change": -0.5}, "treatment_effect.rate_change"),                   # a retreat key in a cover effect
])
def test_invalid_cover_inputs_are_refused_before_writing(served, tmp_path, change, where):
    from src.shoreline_remediation.projections import spec as S
    scenario, _ = _download(served, tmp_path)
    data = json.loads(scenario.read_text(encoding="utf-8"))
    data["treatment_effect"] = {**data["treatment_effect"], **change}
    with pytest.raises(S.SpecError) as err:
        S.check_scope(S.from_dict(data))
    assert any(p.startswith(where) for p, _ in err.value.problems)
    (tmp_path / "bad.json").write_text(json.dumps(data), encoding="utf-8")
    assert cli(["run", "--scenario", str(tmp_path / "bad.json"), "--output", str(tmp_path / "bad")]) == 2
    assert not (tmp_path / "bad").exists()
