"""Scientific values and admission checks for the historical two-arm comparison."""
import json
from pathlib import Path

import pytest

from src.shoreline_remediation.projections import catalogue as C
from src.shoreline_remediation.projections.inventory import build_inventory
from src.shoreline_remediation.projections.slice import COVER, PAH, RETREAT, manual_vs_natural
from src.shoreline_remediation.projections.spec import Unsupported


def report(name):
    path = Path(__file__).resolve().parents[1] / "results" / "projection_baseline" / f"{name}.report.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def history():
    source = report("bay_jimmy_mapped")
    before = json.dumps(source)
    result = manual_vs_natural(build_inventory(source))
    assert json.dumps(source) == before
    return result


def test_cover_keeps_plot_means_and_published_inputs_distinct(history):
    panel = history["endpoints"][COVER]
    raw = [r for r in panel["observations"] if r["role"] == "intervention"]
    assert [r["value"] for r in raw] == pytest.approx([21.8, 51.8])
    assert [r["n_plots"] for r in raw] == [5, 5]
    manual, untreated, contrast = panel["published_year_two"]
    assert (manual["value"], untreated["value"]) == (52, 18)
    assert (contrast["value"], contrast["interval_lo"], contrast["interval_hi"]) == pytest.approx(
        (34, 18.962854, 49.037146), abs=1e-6)
    assert (contrast["n_plots"], contrast["n_comparator"], contrast["interval_level"]) == (5, 9, .9)
    assert "Welch" in contrast["interval_method"] and contrast["date"] == "2012-09"


def test_pah_keeps_observations_on_gap_path_and_class_reference_separate(history):
    panel = history["endpoints"][PAH]
    assert [(r["role"], r["n_plots"], r["value"]) for r in panel["observations"]] == [
        ("reference", 9, 260), ("reference", 9, 112), ("intervention", 5, 220), ("intervention", 5, 101)]
    assert {r["unit"] for r in panel["observations"]} == {"mg/kg"}
    assert C.PAH_TREATMENT_GAP in panel["future_rate_or_effect_gap"]
    region = panel["regional_reference"]
    assert region["metadata"]["n_stations_2plus_campaigns"] == 36
    assert len(region["records"]) == 15 and region["records"][0]["value"] == pytest.approx(100)
    assert all(r["unit"] != "mg/kg" and r["record_class"] == "model_reference" for r in region["records"])
    assert set(region["sources_consulted"]) == {"pah_decline_v1_card", "pah_decline_v1_campaigns", "pah_decline_v1_heavy_class"}


def test_retreat_shares_origin_and_preserves_separate_aerial_periods(history):
    panel = history["endpoints"][RETREAT]
    for role, n, final in (("reference", 9, 12.125645), ("intervention", 5, 11.441917)):
        rows = [r for r in panel["observations"] if r["role"] == role]
        assert len(rows) == 7 and all(r["n_plots"] == n and r["unit"] == "m" for r in rows)
        assert (rows[0]["date"], rows[0]["value"], rows[0]["interval_lo"]) == ("2010-12-04", 0, None)
        assert rows[-1]["date"] == "2016-10-05" and rows[-1]["value"] == pytest.approx(final, abs=1e-6)
    rates = panel["aerial_rate_contrasts"]
    assert [r["date"] for r in rates] == ["2010-2012", "2012-2018"]
    assert [r["value"] for r in rates] == pytest.approx([-.634733, -.129711], abs=1e-6)
    assert all(r["unit"] == "m/yr" and "DSAS lumped" in C.EVIDENCE[r["evidence_id"]].locator for r in rates)


def test_history_is_json_native_with_one_overlap_note_and_no_future_treatment(history):
    assert json.dumps(history, allow_nan=False).count(C.SHARED_PLOTS_NOTE) == 1
    assert history["historical_manual_treatment"]["date"] == "2010-12"
    assert history["future_intervention_date"] is None and history["unresolved_conditions"]
    for panel in history["endpoints"].values():
        for r in panel["observations"]:
            assert r["date"] >= "2010" and r["record_class"] == "observation" and r["evidence_id"] in C.EVIDENCE


@pytest.mark.parametrize("case,option", [
    ("bay_jimmy_mapped", "mechanical_removal"), ("bay_jimmy_mapped", "planting (after mechanical cleanup)"),
    ("rocky_esi_1A", "manual_removal"), ("mangrove", "manual_removal"), ("typed_marsh", "manual_removal"),
])
def test_other_requests_abstain(case, option):
    result = manual_vs_natural(build_inventory(report(case)), option)
    assert isinstance(result, Unsupported) and result.reason


def test_missing_reference_cell_abstains():
    inv = build_inventory(report("bay_jimmy_mapped"))
    inv.rows.remove(inv.reference(PAH))
    assert manual_vs_natural(inv).code == "missing_arm"
