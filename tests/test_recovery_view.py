"""Bay Jimmy recovery view (V5.4): series identity, units, horizons, missing treatments and visibility. Data and wiring checks only; the
view is not scientific validation of the composer. Run from the repository root:  python -m pytest tests/test_recovery_view.py
"""
import math
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
APP = str(ROOT / "src" / "shoreline_remediation" / "dashboard.py")

from src.shoreline_remediation import recovery_view as RV, treatment_effects as te, ui_plots  # noqa: E402
from src.shoreline_remediation.site_evidence import load_sites  # noqa: E402

CELL = "8018_32612"
KEYS = ("water_1km_2010", "water_250m_2010", "fetch_mean_m", "pre_rate", "max_oiling")


@pytest.fixture(scope="module")
def row():
    s = load_sites()
    return s[s.cell == CELL].iloc[0].to_dict()


@pytest.fixture(scope="module")
def view(row):
    return RV.build(row, None, {"manual_removal": "Recommended", "mechanical_removal": "Excluded"},
                    {"value": 1.418, "lo90": -1.74, "hi90": 4.30})


def get(view, panel, key, kind=None):
    return next((s for s in view.panel(panel).series if s.key == key and (kind is None or s.kind == kind)), None)


def test_all_panels_exist_with_units_identity_and_sources(view):
    assert [p.key for p in view.panels] == ["erosion", "vegetation", "pah", "pah_index"]
    assert {p.unit for p in view.panels} == {"m/yr", "%", "mg/kg", "index"}
    for s in view.all_series():
        assert s.unit and s.outcome and s.comparator and s.source and s.evidence and s.scope and s.time_support
        assert all(math.isfinite(q.value) for q in s.points)
    assert RV.LABELS[RV.UNTREATED] == "Untreated baseline"
    decline = get(view, "pah_index", RV.PAH_CLASS)
    assert decline.label != "Untreated baseline" and "no treatment variable" in decline.comparator


def test_vegetation_points_equal_the_source_group_means_with_group_level_intervals(view):
    raw = te.load()
    for key, name in ((RV.UNTREATED, "No Treatment"), (RV.MANUAL, "Manual Treatment"), (RV.MECHANICAL, "Mechanical Treatment")):
        s = get(view, "vegetation", key)
        assert s.kind == RV.FIELD and [q.x0 for q in s.points] == [2011.0, 2012.0] and all(q.x0 == q.x1 for q in s.points)
        for q in s.points:
            r = raw[(raw.study == "main") & (raw.year == int(q.x0)) & (raw.metric == "Total Vegetation Cover (%)") & (raw.treatment == name)].iloc[0]
            assert q.value == pytest.approx(r["mean"]) and 0 <= q.lo <= q.value <= q.hi
        assert "90% t interval of the group mean" in s.interval
    assert get(view, "vegetation", RV.MANUAL).points[1].value == 52.0 and get(view, "vegetation", RV.UNTREATED).points[1].value == 18.0
    assert get(view, "vegetation", RV.PLANTED) is None                      # source has Spartina cover only for planting: not total cover
    assert any("Spartina" in need for _, need in view.panel("vegetation").missing)
    assert all(s.kind != RV.SCENARIO for s in view.panel("vegetation").series)   # the composer's ratio is not converted to cover


def test_erosion_scenario_is_composer_steps_within_the_supported_horizon(view):
    for key in (RV.UNTREATED, RV.MANUAL, RV.MECHANICAL, RV.PLANTED):
        s = get(view, "erosion", key, RV.SCENARIO)
        assert [(q.x0, q.x1) for q in s.points] == [(2010.0, 2012.0), (2012.0, 2018.0)] and "bias gates failed" in s.evidence
        assert all(q.lo < q.value < q.hi for q in s.points)
        assert "absolute rate" in s.interval and "not an interval for a difference" in s.interval
    assert max(q.x1 for s in view.all_series() if s.kind == RV.SCENARIO for q in s.points) == 2018.0     # no extension to 2030
    assert not [s for s in view.all_series() if any(q.x1 > 2018.0 for q in s.points)]
    assert get(view, "erosion", RV.PLANTED, RV.SCENARIO).comparator.endswith("(a historical sequence)")
    assert get(view, "erosion", RV.MECHANICAL, RV.SCENARIO).screening == "Excluded"      # carried from the report, never decided here


def test_composer_years_inside_a_period_are_identical_so_steps_are_faithful(row):
    tidy = RV._compose_cached(tuple(sorted((k, v) for k, v in row.items() if k in KEYS)), True)
    for opt, g in tidy.groupby("option"):
        g = g.set_index("year")
        assert g.loc[1, "median"] == g.loc[2, "median"], opt
        assert len({round(float(g.loc[y, "median"]), 9) for y in range(3, 9)}) == 1, opt


def test_field_erosion_points_equal_plot_level_means_and_differ_in_kind_from_the_scenario(view):
    s = get(view, "erosion", RV.UNTREATED, RV.FIELD)
    w = RV._erosion_plot_table()
    assert s.points[0].value == pytest.approx(w[w.group == "none"]["2010-2012"].mean())
    assert s.points[0].x0 == 2011.0 and s.points[1].x0 == 2015.0
    scenario = get(view, "erosion", RV.UNTREATED, RV.SCENARIO)
    assert s.kind != scenario.kind and "Experimental" in scenario.evidence and "Field observation" in s.evidence


def test_deployed_model_and_observed_cell_stay_separate_references(view, row):
    d, o = get(view, "erosion", RV.DEPLOYED), get(view, "erosion", RV.OBSERVED)
    assert d.kind == RV.REFERENCE and d.points[0].value == pytest.approx(1.418) and "no oiling term" in d.label and "natural" in d.comparator
    assert o.kind == RV.OBSERVATION and o.points[0].value == pytest.approx(row["observed_rate"]) and o.points[0].lo is None
    assert d.points[0].value != get(view, "erosion", RV.UNTREATED, RV.SCENARIO).points[0].value     # no treatment term added to it


def test_pah_decline_reference_is_an_index_inside_the_sampled_period(view):
    s = get(view, "pah_index", RV.PAH_CLASS)
    assert s.kind == RV.DECLINE and s.unit.startswith("index") and s.points[0].value == 100.0 and s.points[0].lo == s.points[0].hi == 100.0
    xs = [q.x0 for q in s.points]
    assert xs == sorted(xs) and xs[0] == pytest.approx(2010.30 + 1.04, abs=0.02) and xs[-1] == pytest.approx(2010.30 + 3.48, abs=0.02)
    assert all(q.lo <= q.value <= q.hi for q in s.points) and s.points[-1].value < s.points[0].value
    assert s.points[-1].value == pytest.approx(100 * math.exp(-0.43016 * (xs[-1] - xs[0])), rel=1e-3)
    assert "decline rate" in s.interval and "Deepwater Horizon only" in s.evidence
    assert view.panel("pah").unit == "mg/kg" and {x.unit for x in view.panel("pah").series} == {"mg/kg"}    # concentration and index never share an axis


def test_pah_concentration_has_only_the_sampled_cells_and_no_decline_curve_for_treatments(view):
    mech = get(view, "pah", RV.MECHANICAL)
    assert len(mech.points) == 1 and mech.points[0].x0 == 2012.0                  # not sampled in 2011
    assert get(view, "pah", RV.UNTREATED).points[0].value == 260.0 and all(s.kind == RV.FIELD for s in view.panel("pah").series)
    assert any("treatment variable" in need or "treated and untreated" in need for _, need in view.panel("pah").missing)


def test_other_oiling_class_gets_no_treatment_series_and_a_compact_note(row):
    v = RV.build({**row, "max_oiling": "Moderate"}, None)
    assert [s.key for s in v.panel("erosion").series if s.kind == RV.SCENARIO] == [RV.UNTREATED]
    assert v.panel("vegetation").unavailable.startswith("Treatment-specific vegetation cover is unavailable")
    assert v.panel("pah").unavailable.startswith("Treatment-specific PAH estimates are unavailable")
    assert ui_plots.recovery_panel_chart(v.panel("vegetation"), RV.COLOURS) is None          # no empty axes


def test_no_view_for_typed_sites_out_of_scope_cells_or_missing_rows(row):
    assert RV.build(None, None) is None and RV.build({**row, "status": "out_of_scope"}, None) is None
    assert RV.build({**row, "status": "no_site_record"}, None) is None


def test_charts_serialise_and_use_no_dotted_lines(view):
    for p in view.panels:
        spec = ui_plots.recovery_panel_chart(p, RV.COLOURS).to_dict()
        assert spec["layer"] and "strokeDash" not in str(spec)          # nothing here is a forward projection


def test_recovery_module_uses_no_synthetic_values():
    src = Path(RV.__file__).read_text(encoding="utf-8").split('"""', 2)[2]
    assert "illustrative_recovery_data" not in src and "_SHAPES_SYNTHETIC" not in src and "ui_plots" not in src


# ---- app behaviour ---------------------------------------------------------------------------------------------------

def run(habitat=None):
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    if habitat is None:
        at.button(key="home_use_bay_jimmy").click().run()
    else:
        at.selectbox(key="home_habitat").set_value(habitat).run()
    at.button(key="home_run").click().run()
    assert not at.exception, at.exception
    return at


def test_bay_jimmy_assessment_shows_the_collapsed_recovery_view_with_all_headings():
    at = run()
    section = next(e for e in at.expander if e.label == "Recovery view: erosion, vegetation and soil PAH")
    assert section.proto.expanded is False
    md = " ".join(m.value for m in section.markdown)
    for heading in ("Marsh-edge erosion rate (m/yr)", "Total vegetation cover (%)", "Soil PAH, concentration (field plots)",
                    "Soil PAH sum, decline reference (index)"):
        assert heading in md
    assert len(section.get("arrow_vega_lite_chart")) + len(section.get("vega_lite_chart")) == 4
    assert any("bias gates failed" in w.value for w in section.warning)
    synthetic = next(e for e in at.expander if e.label == "Synthetic demonstration curves (not data)")
    assert synthetic.proto.expanded is False


@pytest.mark.parametrize("kind", ["marsh", "esi_1A"])
def test_generic_marsh_and_rocky_runs_get_no_recovery_view(kind):
    at = run(habitat=kind)
    assert not any(e.label.startswith("Recovery view") or e.label.startswith("Synthetic demonstration") for e in at.expander)
