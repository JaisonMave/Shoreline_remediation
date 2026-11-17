"""Continuous recovery trajectories (experimental): provenance, constraints, fit selection, conditional labelling, chart scales and
app visibility. These are wiring and numerical checks, not validation of the curves. Run from the repository root:
python -m pytest tests/test_recovery_trajectories.py
"""
import math
import sys
from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
APP = str(ROOT / "src" / "shoreline_remediation" / "dashboard.py")

from src.shoreline_remediation import recovery_trajectories as RT, recovery_view as RV, treatment_effects as te, ui_plots  # noqa: E402
from src.shoreline_remediation.site_evidence import load_sites  # noqa: E402

CELL = "8018_32612"
TITLE = "Continuous trajectories: experimental fits and conditional scenarios"


@pytest.fixture(scope="module")
def row():
    s = load_sites()
    return s[s.cell == CELL].iloc[0].to_dict()


@pytest.fixture(scope="module")
def tr(row):
    return RT.build(row)


def curve(tr, panel, key):
    return next(c for c in tr.panel(panel).curves if c.key == key)


def test_source_plots_reproduce_the_published_group_means_and_plot_counts():
    v, raw = RT.vegetation_plots(), te.load()
    for key, name in ((RV.UNTREATED, "No Treatment"), (RV.MANUAL, "Manual Treatment"), (RV.MECHANICAL, "Mechanical Treatment")):
        for year in (2011, 2012):
            pub = raw[(raw.study == "main") & (raw.year == year) & (raw.metric == "Total Vegetation Cover (%)") & (raw.treatment == name)].iloc[0]
            got = v[(v.key == key) & (v.Year == year)].cover
            assert len(got) == pub.n and got.mean() == pytest.approx(pub["mean"], abs=0.6)
    d = RT.field_positions()
    base = d[np.isclose(d.t0, 0.0)].groupby("key").pid.nunique().to_dict()
    assert base == {RV.UNTREATED: 9, RV.MANUAL: 5, RT.REF_PLOTS: 5}           # mechanical plots have no December 2010 survey


def test_retreat_curves_start_at_zero_stay_inside_their_data_and_bands(tr):
    p = tr.panel("retreat")
    assert p.unit == "m" and {c.key for c in p.curves} == {RV.UNTREATED, RV.MANUAL, RT.REF_PLOTS}
    for c in p.curves:
        obs = next(o for o in p.observed if o.key == c.key)
        assert c.role == RT.FIT and c.y[0] == 0.0 and c.x[0] == pytest.approx(obs.x[0]) and c.x[-1] == pytest.approx(obs.x[-1])
        y, lo, hi = map(np.array, (c.y, c.lo, c.hi))
        assert np.all(np.isfinite(y)) and np.all(lo <= y + 1e-9) and np.all(y <= hi + 1e-9) and np.all(np.diff(y) > 0)
        assert dict(c.diagnostics)["bootstrap refits not converged"] == 0
    assert {c.key: dict(c.diagnostics)["model chosen"] for c in p.curves} == {RV.UNTREATED: "M1", RV.MANUAL: "M1", RT.REF_PLOTS: "M0"}
    b_ref = curve(tr, "retreat", RT.REF_PLOTS).params[0]
    assert 0.9 < b_ref.value < 1.6 and b_ref.lo < b_ref.value < b_ref.hi
    assert {u[0] for u in p.unavailable} == {RV.LABELS[RV.MECHANICAL], RV.LABELS[RV.PLANTED]}


def test_model_selection_follows_held_out_error():
    d = RT.field_positions()
    g = d[(d.key == RV.UNTREATED) & np.isclose(d.t0, 0.0)]
    m0, m1 = RT._retreat_lopo(g, "M0"), RT._retreat_lopo(g, "M1")
    assert m1 < m0 and math.isfinite(m0)
    th = RT._retreat_fit(g, "M1")
    assert th is not None and RT.RETREAT_MODELS["M1"][2][2] < th[2] < RT.RETREAT_MODELS["M1"][3][2]   # tau not at a bound


def test_vegetation_is_bounded_and_manual_is_conditional_on_the_shared_rate(tr):
    p = tr.panel("cover")
    for c in p.curves:
        y, lo, hi = map(np.array, (c.y, c.lo, c.hi))
        assert np.all(lo >= 0) and np.all(hi <= 100) and np.all(lo <= y + 1e-9) and np.all(y <= hi + 1e-9)
    man, unt = curve(tr, "cover", RV.MANUAL), curve(tr, "cover", RV.UNTREATED)
    assert unt.role == RT.FIT and curve(tr, "cover", RV.MECHANICAL).role == RT.FIT
    assert man.role == RT.CONDITIONAL and man.params[0].kind == "shared from untreated fit" and man.params[0].value == unt.params[0].value
    assert "IF" in man.summary and man.x[-1] == pytest.approx(unt.x[-1])
    assert unt.x[-1] == pytest.approx(2016.70)                      # no extension past the last survey
    assert RV.LABELS[RV.PLANTED] in {u[0] for u in p.unavailable}


def test_pah_scenarios_are_conditional_nonnegative_and_end_at_the_rate_support(tr):
    p = tr.panel("tpah")
    k, k_lo, k_hi = RT.heavy_class_rate()
    end = RV.SPILL_YEAR + RV._pah_support("Heavy")[1]
    assert {c.key for c in p.curves} == {RV.UNTREATED, RV.MANUAL, RV.MECHANICAL}
    for c in p.curves:
        assert c.role == RT.CONDITIONAL and c.params[1].kind == "external model coefficient" and c.params[1].value == k
        assert min(c.lo) >= 0 and c.x[-1] == pytest.approx(end)
        assert c.y[-1] == pytest.approx(c.y[0] * math.exp(-k * (c.x[-1] - c.x[0])))
    assert curve(tr, "tpah", RV.MECHANICAL).x[0] == pytest.approx(2012.70)       # first sampled September 2012
    assert any("Treatment-specific" in u[0] for u in p.unavailable)


def test_nonconverged_vegetation_fit_has_explicit_error(monkeypatch):
    monkeypatch.setattr(RT, "_veg_fit", lambda *args, **kwargs: None)
    with pytest.raises(RuntimeError, match="Vegetation fit did not converge"):
        RT.vegetation_panel(np.random.default_rng(1))


def test_other_classes_and_out_of_scope_cells_get_no_curves(row):
    assert RT.build(None) is None and RT.build({**row, "status": "out_of_scope"}) is None
    other = RT.build({**row, "max_oiling": "Moderate"})
    assert other.panels == [] and "heavily oiled" in other.unavailable


def test_parameter_table_marks_how_every_value_was_obtained(tr):
    f = RT.parameter_frame(tr)
    assert set(f.Type) <= {"estimated", "estimated from reference plots", "shared from untreated fit", "external model coefficient",
                           "estimated (given the shared rate)"}
    assert f.Source.str.len().min() > 0 and not f["90% interval"].str.contains("e+", regex=False).any()


def test_trajectory_charts_use_explicit_nonzero_scales_and_dash_only_conditional(tr):
    for p in tr.panels:
        spec = ui_plots.trajectory_chart(p, RV.COLOURS).to_dict()
        assert "vconcat" not in spec and spec["autosize"] == {"contains": "padding", "type": "fit"}
        for layer in spec["layer"]:
            for ch in ("x", "y"):
                scale = layer["encoding"][ch]["scale"]
                assert scale["zero"] is False and len(scale["domain"]) == 2
        d = ui_plots.trajectory_records(p)["curve"]
        assert set(d.role) == {c.role for c in p.curves}
    dash = [l["encoding"]["strokeDash"]["scale"] for l in ui_plots.trajectory_chart(tr.panel("tpah"), RV.COLOURS).to_dict()["layer"]
            if "strokeDash" in l["encoding"]][0]
    assert dict(zip(dash["domain"], map(tuple, dash["range"])))[RT.CONDITIONAL] == (7, 5)


def test_decision_modules_do_not_read_the_trajectories():
    for name in ("decision_pipeline.py", "comparison.py", "recovery_view.py"):
        assert "recovery_trajectories" not in (ROOT / "src" / "shoreline_remediation" / name).read_text(encoding="utf-8")


def test_bay_jimmy_run_retains_only_the_continuous_recovery_section():
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    at.button(key="home_use_bay_jimmy").click().run()
    at.button(key="home_run").click().run()
    assert not at.exception, at.exception
    section = next(e for e in at.expander if e.label == TITLE)
    assert section.proto.expanded is False
    assert [t.label for t in section.tabs] == ["Shoreline retreat", "Vegetation cover", "Soil tPAH", "Parameters and sources"]
    assert len(section.get("arrow_vega_lite_chart")) + len(section.get("vega_lite_chart")) == 3
    assert any("Experimental" in w.value for w in section.warning)
    assert not any(e.label.startswith(("Recovery view", "Synthetic demonstration")) for e in at.expander)
    assert any("sr-opttable" in m.value for m in at.markdown)
