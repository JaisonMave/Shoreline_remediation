"""Replay of the dashboard's what-if download through the projections CLI (shoreline-projection-spec/2, Session R5).

The acceptance tests drive the real dashboard with Streamlit AppTest, keep the exact bytes its download buttons serve, and replay
the JSON with the CLI into a fresh directory. Screening and arithmetic are recomputed from inputs; outputs saved in the file are
only compared.
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.shoreline_remediation.projections import catalogue as C, runner, spec as S, whatif as W
from src.shoreline_remediation.projections.__main__ import main as cli

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "projections"
APP = str(ROOT / "src" / "shoreline_remediation" / "dashboard.py")
RETREAT = "cumulative_shoreline_retreat"

# Run IDs of every version-1 example, recorded before spec version 2 was added (21 Nov 2026). They must never change.
V1_RUN_IDS = {
    "bay_jimmy_observed": "a10afcdc134a1a08", "bay_jimmy_retreat_2030": "8dd6de47e97a8527",
    "bay_jimmy_retreat_2050_changed_rate": "c40c06ac3aec2bfe", "bay_jimmy_tpah_manual_future_unsupported": "41de4fc939fa68fa",
    "bay_jimmy_tpah_observed": "fde8109d673e2e41", "bay_jimmy_veg_contrast_year2": "1c3e23fab97e18f4",
    "bay_jimmy_veg_manual_fit": "78ec0ada1f2b30ae", "dwh_mobile_exposure_hindcast": "4f39be155fd5d57f",
    "rocky_retreat_unsupported": "70d70f5f3d326524",
}


# ---- dashboard downloads ---------------------------------------------------------------------------------------------

@pytest.fixture()
def served(monkeypatch):
    """Every file the dashboard's download buttons serve during the test, by download file name (latest last)."""
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


def _dashboard(end=dt.date(2050, 1, 1), start=dt.date(2030, 1, 1), stop=dt.date(2040, 1, 1), delta=-0.5, change=None):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    at.button(key="home_use_bay_jimmy").click().run()
    at.button(key="home_run").click().run()
    at.session_state["bj_future_panel"] = True
    at.run()
    at.selectbox(key="bj_future_option").set_value("manual_removal").run()
    at.date_input(key="bj_future_end").set_value(end).run()
    if change is not None:
        at.checkbox(key="bj_future_change").check().run()
        at.date_input(key="bj_future_change_date").set_value(change[0]).run()
        at.number_input(key="bj_future_second").set_value(change[1]).run()
    at.date_input(key="bj_whatif_start").set_value(start).run()
    at.date_input(key="bj_whatif_end").set_value(stop).run()
    at.number_input(key="bj_whatif_delta").set_value(delta).run()
    assert not at.exception, at.exception
    return at


def _download(served, tmp_path, **kw):
    at = _dashboard(**kw)
    text = " ".join(str(m.value) for m in at.markdown)
    raw_json, raw_csv = served["bay_jimmy_retreat_whatif.json"][-1], served["bay_jimmy_retreat_whatif.csv"][-1]
    path = tmp_path / "bay_jimmy_retreat_whatif.json"
    path.write_bytes(raw_json)
    return path, raw_csv.decode("utf-8"), text


def _replay(scenario: Path, out: Path) -> tuple:
    code = cli(["run", "--scenario", str(scenario), "--output", str(out)])
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8")) if (out / "manifest.json").exists() else None
    return code, manifest


def _rows(csv_text: str) -> list:
    return csv_text.splitlines()


# ---- acceptance: the actual dashboard download replays exactly ------------------------------------------------------

def test_dashboard_download_replays_row_for_row(served, tmp_path):
    scenario, dashboard_csv, page = _download(served, tmp_path)
    assert "5.00 m less cumulative retreat under your assumption." in page
    out = tmp_path / "replay"
    code, manifest = _replay(scenario, out)
    assert code == 0 and manifest["status"] == "completed"
    replay_csv = (out / W.CSV_NAME).read_text(encoding="utf-8")
    assert _rows(replay_csv) == _rows(dashboard_csv)                 # every row: dates, arm labels, units of record, values
    header = _rows(replay_csv)[0].split(",")
    assert header[:4] == ["date", "series", "arm", "cumulative_retreat_m"]
    import csv, io
    rows = list(csv.DictReader(io.StringIO(replay_csv)))
    observed = [r["date"] for r in rows if r["arm"] == "observed"]
    assert observed == ["2010-12-04", "2011-11-13", "2012-09-17", "2013-09-08", "2014-09-26", "2015-09-30", "2016-10-05"]
    assert {r["series"] for r in rows if r["arm"] == W.TREATMENT_ARM} == {"User-defined what-if: Manual removal"}
    by = {(r["date"], r["arm"]): r for r in rows}
    for year in ("2030-01-01", "2040-01-01", "2050-01-01"):
        nat, trt = by[(year, W.NATURAL_ARM)], by[(year, W.TREATMENT_ARM)]
        expected = "0.000000" if year == "2030-01-01" else "-5.000000"
        assert trt["difference_from_natural_m"] == expected
        assert f"{float(nat['cumulative_retreat_m']) - float(trt['cumulative_retreat_m']):.2f}" == \
            ("0.00" if year == "2030-01-01" else "5.00")
    w = manifest["whatif"]
    assert w["treatment_applied"] and w["screening"]["what_if_allowed"] and w["screening"]["assessment_status"] == "reproduced"
    assert w["summary"]["difference_m"] == pytest.approx(-5.0, abs=1e-9)
    assert w["exported_outputs_check"]["status"] == "matches" and w["exported_outputs_check"]["rows_compared"] == len(rows)
    assert "trampling" in " ".join(w["screening"]["unresolved_conditions"])
    assert cli(["run", "--scenario", str(scenario), "--output", str(out)]) == 4       # output folder protection kept


def test_zero_and_baseline_rate_change_downloads_replay(served, tmp_path):
    scenario, dashboard_csv, page = _download(served, tmp_path, delta=0.0)
    assert "The two curves coincide (0.00 m difference)." in page
    code, manifest = _replay(scenario, tmp_path / "zero")
    assert code == 0 and _rows((tmp_path / "zero" / W.CSV_NAME).read_text(encoding="utf-8")) == _rows(dashboard_csv)
    import csv, io
    rows = list(csv.DictReader(io.StringIO(dashboard_csv)))
    trt = [r for r in rows if r["arm"] == W.TREATMENT_ARM]
    nat = {r["date"]: r["cumulative_retreat_m"] for r in rows if r["arm"] == W.NATURAL_ARM}
    assert trt and all(r["cumulative_retreat_m"] == nat[r["date"]] and r["difference_from_natural_m"] == "0.000000" for r in trt)

    sub = tmp_path / "change"
    sub.mkdir()
    scenario, dashboard_csv, page = _download(served, sub, change=(dt.date(2035, 1, 1), 2.19))
    code, manifest = _replay(scenario, sub / "replay")
    assert code == 0 and _rows((sub / "replay" / W.CSV_NAME).read_text(encoding="utf-8")) == _rows(dashboard_csv)
    by = {(r["date"], r["arm"]): r for r in csv.DictReader(io.StringIO(dashboard_csv))}
    assert by[("2035-01-01", W.TREATMENT_ARM)]["difference_from_natural_m"] == "-2.500000"
    assert by[("2040-01-01", W.TREATMENT_ARM)]["difference_from_natural_m"] == "-5.000000"
    assert by[("2037-01-01", W.TREATMENT_ARM)]["rate_in_effect_m_per_yr"] == "1.690000"
    assert [r["assumption_id"] for r in manifest["whatif"]["rates"]] == ["retreat_rate", "changed_retreat_rate"]


# ---- outputs are never inputs ----------------------------------------------------------------------------------------

def test_an_edited_saved_result_cannot_be_reproduced(served, tmp_path):
    scenario, dashboard_csv, _ = _download(served, tmp_path)
    data = json.loads(scenario.read_text(encoding="utf-8"))
    edited = copy.deepcopy(data)
    edited["exported_outputs"]["summary"]["treatment_m"] = 50.0
    edited["exported_outputs"]["summary"]["difference_m"] = -9.66
    row = next(r for r in edited["exported_outputs"]["rows"] if r["date"] == "2050-01-01" and r["arm"] == W.TREATMENT_ARM)
    row["cumulative_retreat_m"] = 50.0
    path = tmp_path / "edited.json"
    path.write_text(json.dumps(edited), encoding="utf-8")
    code, manifest = _replay(path, tmp_path / "edited_run")
    assert code == 0
    replay = (tmp_path / "edited_run" / W.CSV_NAME).read_text(encoding="utf-8")
    assert _rows(replay) == _rows(dashboard_csv)                       # recomputed from the unchanged inputs
    assert "50.000000" not in replay and manifest["whatif"]["summary"]["treatment_m"] == pytest.approx(54.659470, abs=1e-6)
    check = manifest["whatif"]["exported_outputs_check"]
    assert check["status"] == "differs" and len(check["differences"]) == 1
    assert "50.000000" in check["differences"][0]["download"] and "54.659470" in check["differences"][0]["replay"]
    assert set(check["summary_differences"]) == {"treatment_m", "difference_m"}
    original_run = _replay(scenario, tmp_path / "original_run")[1]
    assert manifest["run_id"] == original_run["run_id"]                # outputs are not part of the run's identity


# ---- screening is re-derived on replay -------------------------------------------------------------------------------

def test_switching_the_technique_to_blocked_planting_draws_no_treatment_curve(served, tmp_path):
    scenario, _, _ = _download(served, tmp_path)
    data = json.loads(scenario.read_text(encoding="utf-8"))
    assert "permit" in data["exported_outputs"]["eligibility_at_export"]          # the stale text still says 'allowed'
    for technique in ("planting (after mechanical cleanup)", "bioremediation"):
        data["technique"] = technique
        path = tmp_path / f"{technique[:8]}.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        assert cli(["validate", "--scenario", str(path)]) == 3
        code, manifest = _replay(path, tmp_path / f"run_{technique[:8]}")
        assert code == 3 and manifest["status"] == "unsupported"
        assert manifest["outcome"]["code"] == "technique_blocked_by_screening"
        assert not manifest["whatif"]["treatment_applied"] and not manifest["whatif"]["screening"]["what_if_allowed"]
        rows = (tmp_path / f"run_{technique[:8]}" / W.CSV_NAME).read_text(encoding="utf-8")
        assert W.TREATMENT_ARM not in rows and W.NATURAL_ARM in rows
    assert "Presupposes mechanical_removal" in json.dumps(manifest) or "Conditions not established" in json.dumps(manifest)


def test_a_changed_site_table_or_unknown_technique_is_not_screened_as_allowed(served, tmp_path):
    scenario, _, _ = _download(served, tmp_path)
    data = json.loads(scenario.read_text(encoding="utf-8"))
    for name, change in (("sha", {"assessment_context": {**data["assessment_context"], "site_sha256": "0" * 64}}),
                         ("unknown", {"technique": "teleportation"})):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps({**data, **change}), encoding="utf-8")
        code, manifest = _replay(path, tmp_path / f"run_{name}")
        assert code == 3 and not manifest["whatif"]["treatment_applied"]


# ---- spec version 2: inputs, blank and zero ---------------------------------------------------------------------------

def _v2(**overrides) -> dict:
    from src.shoreline_remediation import assessment_screening as AS
    base = json.loads((EXAMPLES / "bay_jimmy_retreat_2030.json").read_text(encoding="utf-8"))
    base.update(end_date="2050-01-01")
    ctx = AS.context_from_run_spec(("site", AS.site_items("8018_32612"), "light", None, 3000))
    eff = W.RetreatEffect("manual_removal", dt.date(2030, 1, 1), dt.date(2040, 1, 1), -0.5, "test")
    d = W.spec_dict_v2(base, "manual_removal", ctx, eff)
    d.update(overrides)
    return d


def test_missing_effect_is_baseline_only_and_zero_is_two_identical_arms(tmp_path):
    from src.shoreline_remediation import assessment_screening as AS
    for name, effect in (("none", None), ("omitted", "omit")):
        d = _v2(treatment_effect=None)
        if effect == "omit":
            d.pop("treatment_effect")
        res = runner.run(d, tmp_path / name, screening=AS.reproduce)
        assert res.status == "completed" and not res.manifest["whatif"]["treatment_applied"]
        text = (tmp_path / name / W.CSV_NAME).read_text(encoding="utf-8")
        assert W.TREATMENT_ARM not in text and "2050-01-01" in text
    zero = _v2()
    zero["treatment_effect"] = {**zero["treatment_effect"], "rate_change": 0}
    res = runner.run(zero, tmp_path / "zero", screening=AS.reproduce)
    assert res.manifest["whatif"]["treatment_applied"] and res.manifest["whatif"]["summary"]["difference_m"] == 0.0


@pytest.mark.parametrize("change,where", [
    ({"treatment_effect": {"intervention_start": "2030-01-01", "effect_end": "2040-01-01", "rate_change": None, "unit": "m/yr",
                           "origin": "user_assumption"}}, "treatment_effect.rate_change"),
    ({"treatment_effect": {"intervention_start": "2030-01-01", "effect_end": "2040-01-01", "rate_change": -0.5, "unit": "cm/yr",
                           "origin": "user_assumption"}}, "treatment_effect.unit"),
    ({"treatment_effect": {"intervention_start": "2030-01-01", "effect_end": "2040-01-01", "rate_change": -0.5, "unit": "m/yr",
                           "origin": "literature"}}, "treatment_effect.origin"),
    ({"treatment_effect": {"intervention_start": "2030-01-01", "effect_end": "2040-01-01", "rate_change": -2.0, "unit": "m/yr",
                           "origin": "user_assumption"}}, "treatment_effect"),
    ({"assessment_context": {"entry": "typed_marsh"}}, "assessment_context"),
    ({"model_version": "rate_continuation/1"}, "model_version"),
])
def test_invalid_version_2_inputs_are_refused_before_writing(tmp_path, change, where):
    with pytest.raises(S.SpecError) as err:
        spec = S.from_dict(_v2(**change))
        S.check_scope(spec)
    assert any(p.startswith(where) for p, _ in err.value.problems)


def test_version_2_fields_are_refused_in_version_1_files():
    raw = json.loads((EXAMPLES / "bay_jimmy_retreat_2030.json").read_text(encoding="utf-8"))
    with pytest.raises(S.SpecError, match="version-2 field"):
        S.from_dict({**raw, "technique": "manual_removal"})
    with pytest.raises(S.SpecError, match="needs schema_version"):
        S.from_dict({**raw, "model_version": C.WHATIF_MODEL})


def test_version_2_needs_a_screening_resolver(tmp_path):
    with pytest.raises(S.SpecError, match="re-screened"):
        runner.run(_v2(), tmp_path / "no_resolver")
    assert not (tmp_path / "no_resolver").exists()


# ---- version 1 is unchanged -----------------------------------------------------------------------------------------

def test_version_1_examples_keep_their_run_ids():
    import hashlib
    for path in sorted(EXAMPLES.glob("*.json")):
        spec = S.load(path)
        canonical = json.dumps(spec.to_dict(), sort_keys=True, allow_nan=False)
        assert hashlib.sha256(canonical.encode()).hexdigest()[:16] == V1_RUN_IDS[path.stem], path.name
        assert "technique" not in spec.to_dict() and "exported_outputs" not in spec.to_dict()


def test_version_1_example_still_replays_through_the_cli(tmp_path):
    code, manifest = _replay(EXAMPLES / "bay_jimmy_retreat_2030.json", tmp_path / "v1")
    assert code == 0 and manifest["run_id"] == V1_RUN_IDS["bay_jimmy_retreat_2030"] and "whatif" not in manifest
    assert manifest["projection"]["end"]["cumulative_retreat_since_origin_m"] == pytest.approx(31.06, abs=0.005)


# ---- boundaries -----------------------------------------------------------------------------------------------------

def test_replay_never_imports_streamlit_and_version_1_never_loads_the_decision_engine(tmp_path):
    v2 = tmp_path / "v2.json"
    v2.write_text(json.dumps(_v2()), encoding="utf-8")
    probe = ("import sys; from src.shoreline_remediation.projections.__main__ import main; "
             "code = main(['run', '--scenario', sys.argv[1], '--output', sys.argv[2]]); "
             "print(code, any(m == 'streamlit' or m.startswith('streamlit.') for m in sys.modules), "
             "'src.shoreline_remediation.decision_pipeline' in sys.modules)")
    for scenario, out, loads_engine in ((v2, tmp_path / "o2", "True"),
                                        (EXAMPLES / "bay_jimmy_retreat_2030.json", tmp_path / "o1", "False")):
        res = subprocess.run([sys.executable, "-W", "ignore", "-c", probe, str(scenario), str(out)], cwd=ROOT,
                             capture_output=True, text=True, timeout=300)
        assert res.returncode == 0, res.stderr
        assert res.stdout.strip().splitlines()[-1] == f"0 False {loads_engine}"


def test_screening_adapter_matches_the_dashboard_pipeline_call():
    from src.shoreline_remediation import assessment_screening as AS, ui_pipeline as P
    assert AS.site_keys() == P.SITE_KEYS and AS.DASHBOARD_DRAWS == P.UI_DRAWS
    import pandas as pd
    from src.shoreline_remediation import site_evidence as se
    sites = se.load_sites()
    assert AS.site_items("8018_32612") == P.site_items(sites[sites.cell == "8018_32612"].iloc[0].to_dict())
