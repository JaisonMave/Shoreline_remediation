"""Session 2 of docs/CLAUDE_SCENARIO_PREDICTION_PLAN.md: scenario spec, offline runner, CLI, manifest and isolation.

Software checks only; none of this is scientific validation. Run from the repository root:
    python -m pytest -q tests/test_projections.py
"""
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.shoreline_remediation.projections import (  # noqa: E402
    OutputExistsError, SpecError, Unsupported, check_scope, from_dict, load, normalized, run)
from src.shoreline_remediation.projections import runner as R  # noqa: E402
from src.shoreline_remediation.projections.__main__ import main  # noqa: E402

EXAMPLE = ROOT / "examples" / "projections" / "bay_jimmy_observed.json"
ROCKY = ROOT / "examples" / "projections" / "rocky_retreat_unsupported.json"
PKG = ROOT / "src" / "shoreline_remediation"


def base() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def with_(**changes) -> dict:
    d = base()
    d.update(changes)
    return d


def rate(value, **kw) -> dict:
    return {"assumption_id": "retreat_rate", "value": value, "unit": "m/yr", "origin": "user_assumption", "source": "owner", **kw}


def problems_of(raw) -> dict:
    with pytest.raises(SpecError) as e:
        from_dict(raw)
    return dict(e.value.problems)


# ---- spec: round trip, zero versus missing --------------------------------------------------------------------------

def test_spec_round_trips_through_json():
    spec = load(EXAMPLE)
    again = from_dict(json.loads(spec.to_json()))
    assert again == spec
    assert again.to_dict() == spec.to_dict()


def test_a_measured_zero_survives_round_trip_and_is_not_missing():
    spec = from_dict(with_(assumptions=[rate(0)]))
    text = spec.to_json()
    a = from_dict(json.loads(text)).assumption("retreat_rate")
    assert a.value == 0.0 and a.value is not None and a.missing_reason == ""
    assert '"value": 0.0' in text


def test_missing_value_needs_a_reason_and_stays_null():
    spec = from_dict(with_(assumptions=[rate(None, missing_reason="no defensible rate for this period")]))
    assert spec.assumption("retreat_rate").value is None
    assert "assumptions[0].missing_reason" in problems_of(with_(assumptions=[rate(None)]))
    assert "assumptions[0].missing_reason" in problems_of(with_(assumptions=[rate(1.0, missing_reason="x")]))


# ---- spec: invalid input gives actionable messages ------------------------------------------------------------------

@pytest.mark.parametrize("changes, field, words", [
    ({"as_of": "2016-13-01"}, "as_of", "ISO date"),
    ({"end_date": "2016-10-05"}, "end_date", "must be after"),
    ({"cadence": "weekly"}, "cadence", "annual"),
    ({"seed": -1}, "seed", "non-negative"),
    ({"seed": True}, "seed", "non-negative"),
    ({"arm": "treated"}, "arm", "intervention"),
    ({"model_version": "magic/9"}, "model_version", "observed_record/1"),
    ({"schema_version": "shoreline-projection-spec/0"}, "schema_version", "expected"),
    ({"site_name": "x"}, "site_name", "unknown field"),
    ({"evidence_ids": ["nope"]}, "evidence_ids", "unknown evidence ID"),
    ({"assumptions": [rate(1.2, unit="m")]}, "assumptions[0].unit", "m/yr"),
    ({"assumptions": [rate("fast")]}, "assumptions[0].value", "expected a number"),
    ({"assumptions": [rate(True)]}, "assumptions[0].value", "expected a number"),
    ({"assumptions": [rate(1.0, origin="guess")]}, "assumptions[0].origin", "user_assumption"),
    ({"assumptions": [rate(1.0, origin="literature", source="")]}, "assumptions[0].source", "needs a source"),
    ({"assumptions": [{**rate(1.0), "assumption_id": "storm_factor"}]}, "assumptions[0].assumption_id", "retreat_rate"),
    ({"assumptions": [rate(1.0), rate(2.0)]}, "assumptions", "more than once"),
    ({"assumptions": [{"assumption_id": "rate_change_date", "value": "2020-02-30", "unit": "date", "origin": "user_assumption",
                       "source": "owner"}]}, "assumptions[0].value", "ISO date"),
    ({"assumptions": [rate(1.0, origin="synthetic_fixture")]}, "demonstration", "synthetic_fixture"),
])
def test_invalid_input_names_the_field_and_the_fix(changes, field, words):
    p = problems_of(with_(**changes))
    assert field in p, p
    assert words in p[field], p[field]


def test_missing_required_fields_are_all_listed():
    d = base()
    for k in ("unit", "as_of", "seed"):
        d.pop(k)
    p = problems_of(d)
    assert {"unit", "as_of", "seed"} <= set(p)


def test_non_finite_numbers_are_rejected_from_files(tmp_path):
    f = tmp_path / "nan.json"
    f.write_text(EXAMPLE.read_text(encoding="utf-8").replace('"assumptions": []',
                 '"assumptions": [{"assumption_id": "retreat_rate", "value": NaN, "unit": "m/yr", "origin": "user_assumption"}]'))
    with pytest.raises(SpecError, match="NaN"):
        load(f)
    with pytest.raises(SpecError, match="not found"):
        load(tmp_path / "absent.json")


def test_synthetic_values_are_allowed_only_in_an_identified_demonstration():
    spec = from_dict(with_(demonstration=True, assumptions=[rate(1.0, origin="synthetic_fixture")]))
    assert spec.demonstration
    for p in (ROOT / "examples" / "projections").glob("*.json"):
        assert "synthetic_fixture" not in p.read_text(encoding="utf-8"), p


# ---- scope: structured reasons ------------------------------------------------------------------------------------

@pytest.mark.parametrize("changes, code", [
    ({"habitat": "rocky_shore"}, "habitat_unsupported"),
    ({"habitat": "mangrove"}, "habitat_unsupported"),
    ({"site_id": "galveston_bay"}, "unknown_site"),
    ({"site_id": "bay_jimmy_cell_8018_32612"}, "spatial_unit_mismatch"),
    ({"plot_group_id": "mechanical_removal_heavy", "arm": "intervention"}, "plot_group_ineligible"),
    ({"plot_group_id": "planted"}, "unknown_plot_group"),
    ({"endpoint": "total_vegetation_cover", "unit": "percent", "model_version": "field_contrast/1",
      "evidence_ids": ["zengel2015_s1_group_means"], "comparator_group_id": "unoiled_reference"}, "no_field_contrast"),
    ({"endpoint": "species_richness"}, "unknown_endpoint"),
    ({"oiling_class": "Moderate"}, "oiling_class_unsupported"),
])
def test_unsupported_requests_return_a_reason_not_a_number(changes, code):
    u = check_scope(from_dict(with_(**changes)))
    assert isinstance(u, Unsupported) and u.code == code and len(u.reason) > 40


def test_mangrove_and_rocky_reasons_point_to_the_dashboard_outcome():
    assert "screening" in check_scope(from_dict(with_(habitat="rocky_shore"))).reason
    assert "insufficient evidence" in check_scope(from_dict(with_(habitat="mangrove"))).reason


@pytest.mark.parametrize("changes, field", [
    ({"unit": "ft"}, "unit"),
    ({"arm": "intervention"}, "arm"),
    ({"evidence_ids": []}, "evidence_ids"),
])
def test_fixable_inconsistencies_are_input_errors(changes, field):
    with pytest.raises(SpecError) as e:
        check_scope(from_dict(with_(**changes)))
    assert field in dict(e.value.problems)


def test_supported_groups_pass_scope():
    assert check_scope(load(EXAMPLE)) is None
    assert check_scope(from_dict(with_(plot_group_id="manual_removal_heavy", arm="intervention"))) is None
    assert check_scope(from_dict(with_(plot_group_id="unoiled_reference", oiling_class="NOO"))) is None


# ---- runner -------------------------------------------------------------------------------------------------------

def _tree(d: Path) -> dict:
    return {p.relative_to(d).as_posix(): p.read_bytes() for p in sorted(d.rglob("*")) if p.is_file()}


def test_two_offline_runs_reproduce_the_same_normalized_record(tmp_path):
    a, b = run(EXAMPLE, tmp_path / "a"), run(EXAMPLE, tmp_path / "b")
    assert a.status == b.status == "completed"
    assert normalized(a.manifest) == normalized(b.manifest)
    ta, tb = _tree(a.output_dir), _tree(b.output_dir)
    assert ta.keys() == tb.keys() == {"input.json", "manifest.json", "observed.csv"}
    assert ta["observed.csv"] == tb["observed.csv"] and ta["input.json"] == EXAMPLE.read_bytes()
    m = a.manifest
    assert m["seed"] == 20261120 and m["spec"]["seed"] == 20261120
    assert m["sources"][0]["evidence_id"] == "zengel2022_griidc_field_positions" and len(m["sources"][0]["sha256"]) == 64
    assert {"python", "numpy", "pandas", "scipy", "openpyxl"} <= set(m["dependencies"])
    assert len(m["code"]["code_sha256"]) == 64 and "recovery_trajectories.py" in m["code"]["code_files"]
    assert m["outputs"][0]["sha256"] == hashlib.sha256(ta["observed.csv"]).hexdigest()
    assert json.loads((a.output_dir / "manifest.json").read_text())["status"] == "completed"


def test_observed_record_reproduces_the_field_series(tmp_path):
    import pandas as pd
    res = run(EXAMPLE, tmp_path / "r")
    d = pd.read_csv(res.output_dir / "observed.csv")
    assert list(d.date) == ["2010-12-04", "2011-11-13", "2012-09-17", "2013-09-08", "2014-09-26", "2015-09-30", "2016-10-05"]
    assert (d.n_plots == 9).all() and (d.unit == "m").all() and (d.record_type == "observed_group_mean").all()
    assert d.value.iloc[0] == 0.0 and d.value.iloc[-1] == pytest.approx(12.126, abs=1e-3)
    assert d.value.is_monotonic_increasing                  # positive = land lost
    assert pd.isna(d.interval_lo.iloc[0]) and (d.interval_lo.iloc[1:] < d.value.iloc[1:]).all()
    assert res.manifest["outcome"]["final_survey"] == "2016-10-05"


def test_as_of_withholds_later_observations_from_the_anchor(tmp_path):
    import pandas as pd
    res = run(with_(as_of="2013-09-08"), tmp_path / "r")
    d = pd.read_csv(res.output_dir / "observed.csv")
    assert d.available_at_as_of.tolist() == [True] * 4 + [False] * 3
    assert res.manifest["outcome"]["last_observation_at_as_of"] == "2013-09-08"


def test_an_existing_output_directory_is_left_untouched(tmp_path):
    out = tmp_path / "taken"
    out.mkdir()
    (out / "keep.txt").write_text("user data")
    with pytest.raises(OutputExistsError, match="left untouched"):
        run(EXAMPLE, out)
    assert _tree(out) == {"keep.txt": b"user data"}
    assert main(["run", "--scenario", str(EXAMPLE), "--output", str(out)]) == 4
    assert _tree(out) == {"keep.txt": b"user data"}


def test_invalid_input_writes_nothing(tmp_path):
    with pytest.raises(SpecError):
        run(with_(cadence="weekly"), tmp_path / "x")
    with pytest.raises(SpecError):
        run(with_(unit="ft"), tmp_path / "y")
    assert not (tmp_path / "x").exists() and not (tmp_path / "y").exists()


def test_unsupported_run_records_the_reason_and_no_numbers(tmp_path):
    res = run(ROCKY, tmp_path / "rocky")
    assert res.status == "unsupported" and res.unsupported.code == "habitat_unsupported"
    files = _tree(res.output_dir)
    assert set(files) == {"input.json", "manifest.json"}
    m = json.loads(files["manifest.json"])
    assert m["status"] == "unsupported" and m["outcome"]["code"] == "habitat_unsupported" and m["outputs"] == []


def test_running_status_is_written_first_and_failures_are_recorded(tmp_path, monkeypatch):
    seen = {}

    def boom(spec):
        seen["status"] = json.loads((tmp_path / "f" / "manifest.json").read_text())["status"]
        raise RuntimeError("simulated interruption")

    monkeypatch.setattr(R, "observed_record", boom)
    with pytest.raises(RuntimeError):
        run(EXAMPLE, tmp_path / "f")
    assert seen["status"] == "running"
    m = json.loads((tmp_path / "f" / "manifest.json").read_text())
    assert m["status"] == "failed" and "simulated interruption" in m["outcome"]["error"]
    assert not (tmp_path / "f" / "observed.csv").exists()


def test_cli_exit_codes(tmp_path, capsys):
    assert main(["validate", "--scenario", str(EXAMPLE)]) == 0
    assert main(["validate", "--scenario", str(ROCKY)]) == 3
    assert main(["run", "--scenario", str(EXAMPLE), "--output", str(tmp_path / "ok")]) == 0
    assert main(["run", "--scenario", str(ROCKY), "--output", str(tmp_path / "rocky")]) == 3
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(with_(end_date="2000-01-01")))
    assert main(["run", "--scenario", str(bad), "--output", str(tmp_path / "bad")]) == 2
    assert "end_date" in capsys.readouterr().err and not (tmp_path / "bad").exists()


# ---- isolation from the production pathway ------------------------------------------------------------------------

def _imports(path: Path) -> set:
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):     # some modules start with a BOM
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
            names |= {f"{node.module}.{a.name}" for a in node.names}
    return names


def test_only_the_scenario_panel_imports_the_research_package():
    offenders = [p.name for p in PKG.glob("*.py") if any("projections" in n for n in _imports(p))]
    assert offenders == ["ui_future_scenarios.py"]


def test_research_package_does_not_import_dashboard_or_legacy_decision_code():
    banned = ("streamlit", "scenario_runner", "decision_framework", "decision_pipeline", "dashboard", "site_view", "ui_")
    for p in (PKG / "projections").glob("*.py"):
        bad = [n for n in _imports(p) if any(b in n for b in banned)]
        assert bad == [], (p.name, bad)
    # The parent package __init__ eagerly imports the legacy HybridDecisionModel for every submodule (pre-existing, not changed
    # here). Check only what importing the research package adds on top of the parent package.
    code = ("import sys; import src.shoreline_remediation; before = set(sys.modules); "
            "import src.shoreline_remediation.projections, src.shoreline_remediation.projections.__main__; "
            "added = set(sys.modules) - before; "
            "print(sorted(m for m in added if m.split('.')[-1] in ('scenario_runner', 'decision_framework', 'decision_pipeline', "
            "'dashboard', 'site_view') or m.startswith('streamlit') or m.split('.')[-1].startswith('ui_')))")
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "[]"


# ---- Session 1 regression references are read-only ----------------------------------------------------------------

BASELINE_SHA256 = {   # line-ending-normalized SHA-256, recorded 20 Nov 2026 (docs/PROJECTION_HANDOFF.md)
    "bay_jimmy_mapped.report.json": "4da6fa96b77da55c235d81cbc6f9e2b397251a92967f4783db40fb11e2e895ce",
    "mangrove.report.json": "658ec33839a03cb61e3a75261c27740f48e9ff4315f00568e1af81041b5558e5",
    "rocky_esi_1A.report.json": "d6d10541523e57bb5bdbac9edc414219f35592082a14a76044c61993e7f03406",
    "summary.json": "026d5d359d724612da49909947fcba24a705d5b6eca4f584922048e372e286e7",
    "typed_marsh.report.json": "32926391d3c2d5baa238c46b54fb4f9101351ec1f3896fe1637cd185984de119",
}


def test_session1_baseline_files_are_unchanged():
    d = ROOT / "results" / "projection_baseline"
    for name, digest in BASELINE_SHA256.items():
        assert hashlib.sha256((d / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() == digest, name


def test_capture_script_refuses_to_overwrite_a_capture(tmp_path):
    out = subprocess.run([sys.executable, "scripts/capture_projection_baseline.py", "--out", "results/projection_baseline"],
                         cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert out.returncode != 0 and "Refusing" in out.stderr
