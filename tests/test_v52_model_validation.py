"""V5.2 Model validation data layer: the registry stays authoritative, results come from real files, missing files say unavailable.

Run from the repository root:  python -m pytest tests/test_v52_model_validation.py
"""
import re
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.shoreline_remediation import model_validation_data as MV  # noqa: E402
from src.shoreline_remediation import registry  # noqa: E402


def test_inventory_is_the_registry_unchanged():
    table = registry.governance_table()
    inv = MV.inventory()
    assert [m["model_id"] for m in inv] == [m["model_id"] for m in table]
    for a, b in zip(inv, table):
        assert a["state"] == b["state"] and a["declared_state"] == b["declared_state"] and a["gates"] == b["gates"]
    assert set(m["state"] for m in inv) <= {"validated", "experimental"}
    assert MV.state_counts() == {"validated": 2, "experimental": 7} and sum(MV.state_counts().values()) == len(inv)


def test_only_the_two_narrow_models_are_validated_and_sorted_first():
    validated = [m["model_id"] for m in MV.inventory() if m["state"] == "validated"]
    assert sorted(validated) == ["edge_loss_v1", "pah_decline_v1"]
    ordered = MV.sorted_inventory()
    assert [m["state"] for m in ordered[:2]] == ["validated", "validated"] and len(ordered) == len(MV.inventory())


def test_failed_gates_are_never_dropped_even_for_validated_models():
    edge = next(m for m in MV.inventory() if m["model_id"] == "edge_loss_v1")
    assert edge["state"] == "validated" and "V5-0.2" in [g["gate_id"] for g in edge["gates"] if not g["passed"]]
    for m in MV.inventory():
        assert m["n_gates_failed"] == sum(1 for g in m["gates"] if not g["passed"])
    experimental_failed = {m["model_id"]: [g["gate_id"] for g in m["gates"] if not g["passed"]] for m in MV.inventory() if m["state"] == "experimental"}
    assert "F5" in experimental_failed["process_model_v2"] and "D32-heavy-bias" in experimental_failed["composer_natural_recovery_v1"]
    assert all(experimental_failed[k] for k in experimental_failed)               # every experimental model has at least one failed gate


def test_f5_numbers_come_from_the_summary_file_and_the_gate_failed():
    r = MV.f5_comparison()
    assert r["available"] and r["gate_failed"] and not r["beats_empirical"]
    assert (round(r["calibrated"], 3), round(r["empirical"], 3)) == (0.775, 0.750) and r["calibrated"] > r["empirical"]
    text = (ROOT / "results/f5_process/summary.txt").read_text()
    for key in ("prior", "empirical", "calibrated"):
        assert f"{r[key]:.4f}" in text
    f5 = next(g for m in MV.inventory() for g in m["gates"] if g["gate_id"] == "F5")
    assert f5["passed"] is False and f5["blocks_promotion"] is True


def test_d32_and_r3_bias_gates_fail_and_match_the_cited_summary_files():
    r = MV.bias_gates()
    assert r["available"]
    by = {x["gate_id"]: x for x in r["rows"]}
    assert by["D32-heavy-bias"]["observed"] == 0.330 and by["R3-heavy-bias"]["observed"] == 0.549
    assert all(x["limit"] == 0.25 and x["passed"] is False and x["observed"] > x["limit"] for x in r["rows"])
    assert by["D32-heavy-bias"]["observed"] < by["R3-heavy-bias"]["observed"]            # reduced, but still outside the gate
    assert "heavy_bias=+0.330" in (ROOT / "results/scenario_composer/summary_d32.txt").read_text()
    assert "heavy bias +0.549" in (ROOT / "results/scenario_composer/summary_v4_r3.txt").read_text()


def test_edge_loss_results_equal_the_files_and_untested_basins_are_not_shown_as_zero():
    r = MV.edge_loss_holdout()
    per = pd.read_csv(ROOT / "results/p2_basin_holdout/per_basin.csv")
    assert r["available"] and r["not_tested"] == list(per[per.tested == False].basin)  # noqa: E712
    shown = [x["basin"] for x in r["rows"]]
    assert "terrebonne" not in shown and shown[-1] == "pooled"
    for x in r["rows"][:-1]:
        row = per[per.basin == x["basin"]].iloc[0]
        assert (x["MAE_M0"], x["MAE_M1"], x["MAE_M2"], x["coverage_90"]) == (row.MAE_M0, row.MAE_M1, row.MAE_M2, row.coverage_90)
    pooled = pd.read_csv(ROOT / "results/p2_basin_holdout/pooled.csv").iloc[0]
    assert r["rows"][-1]["MAE_M0"] == pooled.MAE_M0 and r["rows"][-1]["cells"] == int(pooled.cells)
    assert "M2 vs M1" in (ROOT / r["verdict_file"]).read_text()


def test_pah_results_equal_the_file():
    r = MV.pah_holdout()
    row = pd.read_csv(ROOT / "results/pah_decline/summary.csv").query("outcome == 'PAH sum'").iloc[0]
    assert r["available"] and r["MAE_M0"] == row.MAE_M0 and r["MAE_M1"] == row.MAE_M1 and r["heldout_stations"] == row.n_heldout_stations
    assert r["diff_lo90"] < r["diff"] < r["diff_hi90"] < 0


@pytest.mark.parametrize("reader", [MV.edge_loss_holdout, MV.pah_holdout, MV.f5_comparison])
def test_missing_result_files_say_unavailable_instead_of_raising(reader, tmp_path, monkeypatch):
    monkeypatch.setattr(MV, "ROOT", tmp_path)
    r = reader()
    assert r["available"] is False and r["reason"] and r["source"]


def test_unreadable_or_incomplete_files_say_unavailable(tmp_path, monkeypatch):
    (tmp_path / "results/pah_decline").mkdir(parents=True)
    (tmp_path / "results/pah_decline/summary.csv").write_text("outcome,MAE_M0\nPAH sum,0.6\n")
    (tmp_path / "results/f5_process").mkdir(parents=True)
    (tmp_path / "results/f5_process/summary.txt").write_text("empirical k 0.75\n")
    monkeypatch.setattr(MV, "ROOT", tmp_path)
    assert MV.pah_holdout()["available"] is False and "columns" in MV.pah_holdout()["reason"]
    assert MV.f5_comparison()["available"] is False and "prior" in MV.f5_comparison()["reason"]


def test_heuristic_confidence_is_not_described_as_a_calibrated_probability():
    note = MV.HEURISTIC_CONFIDENCE_NOTE
    assert "heuristic" in note and "not a calibrated probability" in note and "scenario_runner" in note
    for m in MV.inventory():
        assert "calibrated probability" not in (m["interval_status"] or "").lower() or "not" in m["interval_status"].lower()


def test_every_model_has_its_governance_fields_or_a_stated_gap():
    for m in MV.inventory():
        for field in ("intended_use", "habitat_scope", "geographic_scope", "training_data", "validation_data", "validation_design",
                      "baseline", "uncertainty_method", "interval_status", "limitations"):
            assert m[field].strip() or field in m["governance_gaps"], (m["model_id"], field)


def test_bias_gates_say_unavailable_when_the_registry_wording_has_no_numbers(monkeypatch):
    fake = tuple({**m, "gates": [{**g, "description": "Heavy-cell bias within +/-0.25 m/yr"} for g in m["gates"]]}
                 for m in MV.inventory())
    monkeypatch.setattr(MV, "inventory", lambda: fake)
    r = MV.bias_gates()
    assert r["available"] is False and "not stated" in r["reason"]


def test_edge_loss_reader_rejects_a_file_without_the_expected_columns(tmp_path, monkeypatch):
    d = tmp_path / "results/p2_basin_holdout"
    d.mkdir(parents=True)
    (d / "per_basin.csv").write_text("basin,tested\nbarataria,True\n")
    (d / "pooled.csv").write_text("MAE_M0\n1.0\n")
    monkeypatch.setattr(MV, "ROOT", tmp_path)
    r = MV.edge_loss_holdout()
    assert r["available"] is False and "columns" in r["reason"]
