"""Provenance of the DIVER reference index (follow-up to the review fixes). Written before the change; the first two tests failed
because the PAH model card and station-campaign table had no evidence IDs and were not recorded in manifests.

Three paths: (1) heavy-class run that exports the index; (2) early as_of run that withholds it after checking campaign support;
(3) treatment-specific future request that returns evidence_gap and exports the historical tPAH measurements.
    python -m pytest -q tests/test_projections_pah_sources.py
"""
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.shoreline_remediation.projections import run  # noqa: E402
from src.shoreline_remediation.projections import catalogue as C  # noqa: E402

EX = ROOT / "examples" / "projections"
CITED = {"zengel2015_s1_group_means", "pah_decline_v1_heavy_class"}


def ex(name: str, **changes) -> dict:
    d = json.loads((EX / name).read_text(encoding="utf-8"))
    d.update(changes)
    return d


def sources(res) -> dict:
    out = {s["evidence_id"]: s for s in res.manifest["sources"]}
    for eid, s in out.items():
        assert s["present"] and s["sha256"] == hashlib.sha256((ROOT / C.EVIDENCE[eid].path).read_bytes()).hexdigest(), eid
        assert s["cited_in_spec"] == (eid in CITED), eid
        assert s["used_in_calculation"] == bool(s["roles"]), eid
    return out


def test_new_evidence_ids_point_at_the_files_recovery_view_reads():
    from src.shoreline_remediation import recovery_view as RV
    assert ROOT / C.EVIDENCE["pah_decline_v1_card"].path == RV.PAH_CARD
    assert ROOT / C.EVIDENCE["pah_decline_v1_campaigns"].path == RV.CAMPAIGNS


def test_heavy_run_exports_the_index_and_records_every_source_used(tmp_path):
    res = run(EX / "bay_jimmy_tpah_observed.json", tmp_path / "heavy")
    assert res.status == "completed" and res.manifest["run_id"] == "fde8109d673e2e41"          # spec and run ID unchanged
    s = sources(res)
    assert set(s) == CITED | {"pah_decline_v1_card", "pah_decline_v1_campaigns"}
    assert all(s[e]["used_in_calculation"] for e in s)
    assert any("support" in r for r in s["pah_decline_v1_campaigns"]["roles"])
    assert any("decline rate" in r for r in s["pah_decline_v1_card"]["roles"])
    assert any("tPAH" in r for r in s["zengel2015_s1_group_means"]["roles"])
    # index values and dates as exported before this change (Session 4 replay, scratchpad s4)
    i = pd.read_csv(res.output_dir / "reference_index.csv")
    assert len(i) == 15 and i.value.iloc[0] == 100.0
    assert i.decimal_year.iloc[0] == pytest.approx(2011.343121, abs=1e-6) and i.decimal_year.iloc[-1] == pytest.approx(2013.777070, abs=1e-6)
    assert (i.value.iloc[-1], i.interval_lo.iloc[-1], i.interval_hi.iloc[-1]) == pytest.approx((35.09593, 25.932632, 49.220534), abs=1e-5)
    o = pd.read_csv(res.output_dir / "observed.csv")
    assert o.value.tolist() == [260.0, 112.0] and o.date.tolist() == ["2011-07/08", "2012-09"]


def test_early_as_of_withholds_the_index_after_checking_campaign_support(tmp_path):
    res = run(ex("bay_jimmy_tpah_observed.json", as_of="2012-10-15", end_date="2013-01-01"), tmp_path / "early")
    assert not (res.output_dir / "reference_index.csv").exists()
    assert "withheld" in res.manifest["reference_index"]["reason"]
    s = sources(res)
    assert s["pah_decline_v1_campaigns"]["used_in_calculation"] and not s["pah_decline_v1_campaigns"]["cited_in_spec"]
    assert any("withheld" in r or "as_of" in r for r in s["pah_decline_v1_campaigns"]["roles"])
    assert "pah_decline_v1_card" not in s                      # not consulted: the index is withheld before the card is read
    assert s["pah_decline_v1_heavy_class"]["cited_in_spec"] and not s["pah_decline_v1_heavy_class"]["used_in_calculation"]
    assert s["zengel2015_s1_group_means"]["used_in_calculation"]
    o = pd.read_csv(res.output_dir / "observed.csv")
    assert o.value.tolist() == [260.0, 112.0] and o.available_at_as_of.tolist() == [True, True]


def test_treatment_specific_request_is_an_evidence_gap_with_measurements_and_honest_sources(tmp_path):
    res = run(EX / "bay_jimmy_tpah_manual_future_unsupported.json", tmp_path / "gap")
    assert res.status == "unsupported" and res.unsupported.code == "evidence_gap"
    assert res.manifest["run_id"] == "41de4fc939fa68fa"
    assert sorted(p.name for p in res.output_dir.iterdir()) == ["input.json", "manifest.json", "observed.csv"]
    s = sources(res)
    assert set(s) == CITED                                     # the index path is not entered: no card or campaign read
    assert s["zengel2015_s1_group_means"]["used_in_calculation"]
    assert not s["pah_decline_v1_heavy_class"]["used_in_calculation"]
    o = pd.read_csv(res.output_dir / "observed.csv")
    assert o.value.tolist() == [220.0, 101.0] and o.date.tolist() == ["2011-07/08", "2012-09"] and (o.n_plots == 5).all()


def test_other_runs_mark_the_sources_they_use(tmp_path):
    r = run(EX / "bay_jimmy_retreat_2030.json", tmp_path / "r")
    s = {x["evidence_id"]: x for x in r.manifest["sources"]}
    assert s["zengel2022_griidc_field_positions"]["used_in_calculation"] and r.manifest["run_id"] == "8dd6de47e97a8527"
    c = run(EX / "bay_jimmy_veg_contrast_year2.json", tmp_path / "c")
    assert all(x["used_in_calculation"] for x in c.manifest["sources"]) and c.manifest["run_id"] == "1c3e23fab97e18f4"
