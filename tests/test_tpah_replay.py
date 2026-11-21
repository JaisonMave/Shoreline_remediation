"""Bay Jimmy soil tPAH what-if in the Assessment panel and its replay through the projections CLI (tpah_whatif/1).

The dashboard is driven with Streamlit AppTest; the exact bytes its download buttons serve are replayed with the CLI into a
fresh directory and compared row by row at the declared export precision, including the before/after rows at intervention."""
from __future__ import annotations

import copy
import csv
import datetime as dt
import io
import json
from pathlib import Path

import pytest

from src.shoreline_remediation.projections import pah as PH, whatif as W
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
    at.segmented_control(key="bj_future_outcome").set_value("tpah").run()
    assert not at.exception, at.exception
    return at


def _enter(at, reduction, date=D(2020, 1, 1), half_life=4.0, end=D(2030, 1, 1)):
    if half_life is not None:
        at.segmented_control(key="bj_pah_baseline").set_value(PH.HALF_LIFE).run()
        at.number_input(key="bj_pah_half_life").set_value(half_life).run()
    at.date_input(key="bj_pah_end").set_value(end).run()
    at.date_input(key="bj_pah_date").set_value(date).run()
    at.number_input(key="bj_pah_reduction").set_value(reduction).run()
    assert not at.exception, at.exception


def text(at) -> str:
    return " ".join(str(e.value) for g in (at.markdown, at.caption, at.info, at.warning) for e in g)


# ---- panel ------------------------------------------------------------------------------------------------------------

def test_tpah_panel_shows_the_anchor_and_both_groups_measurements():
    at = _panel()
    t = text(at)
    assert "September 2012" in t and "112.0 mg/kg" in t and "9 plots" in t and "date precision: month" in t
    assert "0-10 cm cores, surface oil scraped aside" in t and "dry or wet basis not recorded" in t
    table = next(tb.value for tb in at.table if "Mean tPAH (mg/kg)" in tb.value.columns)
    assert table["Mean tPAH (mg/kg)"].tolist() == ["260", "112", "220", "101"]
    assert table["Survey"].tolist() == ["July-August 2011", "September 2012"] * 2
    assert "DIVER" in t and "own scale" in t
    assert at.segmented_control(key="bj_pah_baseline").value == PH.HOLD
    assert at.number_input(key="bj_pah_reduction").value is None                  # never prefilled from the field difference
    assert at.text_input(key="bj_pah_basis").value == PH.DEFAULT_BASIS
    assert "A percentage of visible surface oil collected does not establish that value" in t
    assert "concentration held at the last observation" in t


def test_half_life_is_blank_by_default_and_must_be_positive():
    at = _panel()
    at.segmented_control(key="bj_pah_baseline").set_value(PH.HALF_LIFE).run()
    assert at.number_input(key="bj_pah_half_life").value is None
    t = text(at)
    assert "Enter a positive half-life" in t and "zero long-term background" in t
    assert not any(c.key == "bj_pah_reduction" for c in at.number_input)       # no future curve without a valid baseline
    at.number_input(key="bj_pah_half_life").set_value(-2.0).run()
    assert "positive, finite number of years" in text(at)
    at.number_input(key="bj_pah_half_life").set_value(4.0).run()
    assert "decline with an assumed half-life of 4 years" in text(at)


def test_tpah_whatif_values_bounds_and_zero():
    at = _panel()
    _enter(at, 20.0, half_life=None)
    t = text(at)
    assert "At the intervention (01 Jan 2020): 112.0 mg/kg before, 89.6 mg/kg after a 20% reduction." in t
    assert "22.4 mg/kg lower under your assumption." in t
    at.number_input(key="bj_pah_reduction").set_value(120.0).run()
    assert "between 0% and 100%" in text(at)
    at.number_input(key="bj_pah_reduction").set_value(0.0).run()
    assert "identical (0.0 mg/kg difference)" in text(at)
    at.number_input(key="bj_pah_reduction").set_value(20.0).run()
    at.text_input(key="bj_pah_basis").set_value("").run()
    assert "Record the basis" in text(at)


def test_passive_sorbents_has_no_measured_effect_planting_is_blocked_and_switching_clears():
    at = _panel()
    _enter(at, 30.0, half_life=None)
    at.selectbox(key="bj_future_option").set_value("passive_sorbents").run()
    t = text(at)
    assert "There is no measured Bay Jimmy soil tPAH effect for passive sorbents" in t
    assert at.number_input(key="bj_pah_reduction").value is None and at.date_input(key="bj_pah_date").value == D(2027, 1, 1)
    at.selectbox(key="bj_future_option").set_value("planting (after mechanical cleanup)").run()
    t = text(at)
    assert "No what-if for planting (after mechanical cleanup)." in t and not any(c.key == "bj_pah_reduction" for c in at.number_input)


# ---- replay of the actual download ------------------------------------------------------------------------------------

def _download(served, tmp_path, reduction=20.0, **kw):
    at = _panel()
    _enter(at, reduction, **kw)
    path = tmp_path / "bay_jimmy_tpah_whatif.json"
    path.write_bytes(served["bay_jimmy_tpah_whatif.json"][-1])
    return path, served["bay_jimmy_tpah_whatif.csv"][-1].decode("utf-8")


def _replay(scenario, out):
    code = cli(["run", "--scenario", str(scenario), "--output", str(out)])
    return code, json.loads((out / "manifest.json").read_text(encoding="utf-8"))


def test_tpah_download_replays_row_for_row_including_the_step(served, tmp_path):
    scenario, dashboard_csv = _download(served, tmp_path)                   # half-life 4 years, 20% on 1 Jan 2020
    figures = tmp_path / "figures"
    assert cli(["run", "--scenario", str(scenario), "--output", str(figures), "--figures"]) == 0
    assert (figures / "whatif.png").read_bytes() == served["bay_jimmy_tpah_whatif.png"][-1]
    assert (figures / "whatif.svg").read_bytes() == served["bay_jimmy_tpah_whatif.svg"][-1]
    data = json.loads(scenario.read_text(encoding="utf-8"))
    assert data["model_version"] == PH.TPAH_MODEL and data["unit"] == "mg/kg" and data["technique"] == "manual_removal"
    assert data["assumptions"] == [{"assumption_id": "tpah_half_life", "value": 4.0, "unit": "yr", "origin": "user_assumption",
                                    "source": "Bay Jimmy Assessment tPAH controls (zero long-term background assumed)"}]
    assert data["treatment_effect"] == {"intervention_date": "2020-01-01", "reduction_percent": 20.0,
                                        "unit": "percent of soil tPAH concentration", "basis": PH.DEFAULT_BASIS,
                                        "origin": "user_assumption", "source": "Bay Jimmy Assessment what-if controls"}
    assert data["exported_outputs"]["anchor"]["tpah_mgkg"] == 112.0
    code, manifest = _replay(scenario, tmp_path / "replay")
    assert code == 0 and manifest["status"] == "completed"
    replay_csv = (tmp_path / "replay" / W.CSV_NAME).read_text(encoding="utf-8")
    assert replay_csv.splitlines() == dashboard_csv.splitlines()
    rows = list(csv.DictReader(io.StringIO(replay_csv)))
    assert [(r["date"], r["survey_period"]) for r in rows if r["arm"] == "observed"] == \
        [("2011-07/08", "July-August 2011"), ("2012-09", "September 2012")]
    step = [r for r in rows if r["date"] == "2020-01-01" and r["arm"] == PH.TREATMENT_ARM]
    assert [r["sample"] for r in step] == ["intervention_before", "intervention_after"]
    before, after = float(step[0]["soil_tpah"]), float(step[1]["soil_tpah"])
    assert f"{after:.6f}" == f"{0.8 * before:.6f}" and int(step[0]["order"]) < int(step[1]["order"])
    assert len([r for r in rows if r["date"] == "2020-01-01" and r["arm"] == PH.NATURAL_ARM]) == 1
    b = manifest["whatif"]["baseline"]
    assert (b["choice"], b["half_life_years"], b["background"], b["survey_period"], b["tpah_mgkg"], b["n_plots"]) == \
        ("half_life", 4.0, "zero (assumed)", "September 2012", 112.0, 9)
    assert manifest["whatif"]["summary"]["at_intervention"]["after_mgkg"] == pytest.approx(0.8 * before, abs=1e-5)
    assert manifest["whatif"]["exported_outputs_check"]["status"] == "matches"
    assert cli(["run", "--scenario", str(scenario), "--output", str(tmp_path / "replay")]) == 4


def test_tpah_blank_zero_off_grid_and_held_downloads_replay(served, tmp_path):
    for name, kw in (("zero", dict(reduction=0.0)), ("offgrid", dict(reduction=35.0, date=D(2019, 7, 15))),
                     ("held", dict(reduction=100.0, half_life=None))):
        sub = tmp_path / name
        sub.mkdir()
        scenario, dashboard_csv = _download(served, sub, **kw)
        code, manifest = _replay(scenario, sub / "replay")
        assert code == 0 and (sub / "replay" / W.CSV_NAME).read_text(encoding="utf-8").splitlines() == dashboard_csv.splitlines()
        if name == "zero":
            assert manifest["whatif"]["summary"]["difference_mgkg"] == 0.0
        if name == "held":
            assert manifest["whatif"]["baseline"]["choice"] == "hold" and manifest["whatif"]["summary"]["treatment_mgkg"] == 0.0
        if name == "offgrid":
            assert "2019-07-15" in dashboard_csv
    blank = json.loads(scenario.read_text(encoding="utf-8"))
    blank["treatment_effect"] = None
    (tmp_path / "blank.json").write_text(json.dumps(blank), encoding="utf-8")
    code, manifest = _replay(tmp_path / "blank.json", tmp_path / "blank")
    assert code == 0 and not manifest["whatif"]["treatment_applied"]
    assert PH.TREATMENT_ARM not in (tmp_path / "blank" / W.CSV_NAME).read_text(encoding="utf-8")


def test_tpah_replay_rescreens_and_ignores_edited_outputs(served, tmp_path):
    scenario, _ = _download(served, tmp_path)
    data = json.loads(scenario.read_text(encoding="utf-8"))
    code, manifest = _replay(scenario, tmp_path / "original")
    edited = copy.deepcopy(data)
    edited["exported_outputs"]["summary"]["treatment_mgkg"] = 1.0
    edited["exported_outputs"]["rows"][-1]["soil_tpah"] = 1.0
    (tmp_path / "edited.json").write_text(json.dumps(edited), encoding="utf-8")
    code, m2 = _replay(tmp_path / "edited.json", tmp_path / "edited")
    assert code == 0 and m2["whatif"]["summary"]["treatment_mgkg"] == manifest["whatif"]["summary"]["treatment_mgkg"]
    assert m2["whatif"]["exported_outputs_check"]["status"] == "differs" and m2["run_id"] == manifest["run_id"]
    blocked = {**data, "technique": "planting (after mechanical cleanup)"}
    (tmp_path / "blocked.json").write_text(json.dumps(blocked), encoding="utf-8")
    assert cli(["validate", "--scenario", str(tmp_path / "blocked.json")]) == 3
    code, m3 = _replay(tmp_path / "blocked.json", tmp_path / "blocked")
    assert code == 3 and m3["outcome"]["code"] == "technique_blocked_by_screening"
    assert PH.TREATMENT_ARM not in (tmp_path / "blocked" / W.CSV_NAME).read_text(encoding="utf-8")


@pytest.mark.parametrize("change,where", [
    ({"treatment_effect": {"reduction_percent": 120.0}}, "treatment_effect"),
    ({"treatment_effect": {"reduction_percent": -5.0}}, "treatment_effect"),
    ({"treatment_effect": {"basis": ""}}, "treatment_effect.basis"),
    ({"treatment_effect": {"unit": "percent of surface oil"}}, "treatment_effect.unit"),
    ({"treatment_effect": {"intervention_date": "2011-01-01"}}, "treatment_effect"),
    ({"assumptions": [{"assumption_id": "tpah_half_life", "value": 0.0, "unit": "yr", "origin": "user_assumption",
                       "source": "x"}]}, "assumptions"),
    ({"assumptions": [{"assumption_id": "tpah_half_life", "value": 4.0, "unit": "d", "origin": "user_assumption",
                       "source": "x"}]}, "assumptions[0].unit"),
])
def test_invalid_tpah_inputs_are_refused_before_writing(served, tmp_path, change, where):
    from src.shoreline_remediation.projections import spec as S
    scenario, _ = _download(served, tmp_path)
    data = json.loads(scenario.read_text(encoding="utf-8"))
    for k, v in change.items():
        data[k] = {**data[k], **v} if k == "treatment_effect" else v
    with pytest.raises(S.SpecError) as err:
        S.check_scope(S.from_dict(data))
    assert any(p.startswith(where) for p, _ in err.value.problems)
    (tmp_path / "bad.json").write_text(json.dumps(data), encoding="utf-8")
    assert cli(["run", "--scenario", str(tmp_path / "bad.json"), "--output", str(tmp_path / "bad")]) == 2
    assert not (tmp_path / "bad").exists()
