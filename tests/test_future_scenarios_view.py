"""Chart data and labels of the Bay Jimmy future-scenario panel, tested without rendering."""
import json
from pathlib import Path

import pandas as pd
import pytest

from src.shoreline_remediation import ui_future_scenarios as V
from src.shoreline_remediation.projections import inventory as I, slice as SL

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def history():
    report = json.loads((ROOT / "results/projection_baseline/bay_jimmy_mapped.report.json").read_text(encoding="utf-8"))
    return SL.manual_vs_natural(I.build_inventory(report))


def test_arm_frames_carry_n_dates_and_interval_method(history):
    cover = V.arm_frame(history["endpoints"][SL.COVER]["observations"])
    manual = cover[cover.series == V.TREAT_SERIES]
    assert list(manual.survey) == ["September 2011", "September 2012"] and list(manual.n_plots) == [5, 5]
    assert manual.value.tolist() == pytest.approx([21.8, 51.8]) and manual.interval.str.contains("90% t interval").all()
    pah = V.arm_frame(history["endpoints"][SL.PAH]["observations"])
    assert pah.unit.eq("mg/kg").all() and sorted(pah.value) == [101, 112, 220, 260]
    assert set(pah[pah.series == V.REF_SERIES].n_plots) == {9}


def test_display_offset_is_small_and_symmetric(history):
    ret = V.arm_frame(history["endpoints"][SL.RETREAT]["observations"])
    origin = ret[ret.value == 0]
    gap = (origin[origin.series == V.TREAT_SERIES].plot_date.iloc[0] - origin[origin.series == V.REF_SERIES].plot_date.iloc[0])
    assert gap == pd.Timedelta(days=2 * V.OFFSET_DAYS) and V.OFFSET_DAYS <= 31
    assert origin[["lo", "hi"]].isna().all().all()        # zero by definition: no interval bar is drawn


def test_summary_texts_state_units_n_and_uncertainty(history):
    c = V.cover_contrast_text(history["endpoints"][SL.COVER])
    assert "+34.0 percentage points" in c and "90% Welch interval +19.0 to +49.0" in c and "5 manual vs 9 untreated" in c
    assert "52% vs 18%" in c and "Observational" in c
    r = V.retreat_summary_text(history["endpoints"][SL.RETREAT])
    assert "11.44 m" in r and "n = 5" in r and "12.13 m" in r and "n = 9" in r and "04 Dec 2010" in r
    a = V.aerial_table(history["endpoints"][SL.RETREAT])
    assert list(a.index) == ["2010-2012", "2012-2018"] and a["Manual − untreated (m/yr)"].tolist() == ["-0.63", "-0.13"]
    assert a["90% interval"].tolist() == ["-1.25 to -0.02", "-0.62 to +0.36"]
    assert a["Plots (manual / untreated)"].eq("5 / 9").all()


def test_missing_contrast_is_explained_not_drawn():
    panel = {"published_year_two": [], "contrast_unavailable_reason": "Excluded by screening"}
    assert V.cover_contrast_text(panel) == "No year-two difference is shown: Excluded by screening"


def test_tidy_rows_cover_every_shown_value(history):
    rows = V.tidy_rows(history)
    n = sum(len(p.get(g) or []) for p in history["endpoints"].values()
            for g in ("observations", "published_year_two", "aerial_rate_contrasts"))
    assert len(rows) == n and rows.status.str.contains("not a forecast").all() and rows.unit.notna().all()
    assert set(rows.record_type) == {"observed_group_mean", "field_contrast"}


def _whatif(delta):
    import datetime as dt
    from src.shoreline_remediation.projections import runner, spec as S, whatif as W
    raw = json.loads(V.EXAMPLE.read_text(encoding="utf-8"))
    raw.update(end_date="2050-01-01")
    sp = S.from_dict(raw)
    obs = runner.observed_record(S.load(V.EXAMPLE))
    eff = None if delta == "none" else W.RetreatEffect("manual_removal", dt.date(2030, 1, 1), dt.date(2040, 1, 1), delta)
    w = W.two_arms(sp, dt.date(2016, 10, 5), float(obs.value.iloc[-1]), eff)
    return W.export_rows(obs, w, 9, "Manual removal"), w, dt.date(2050, 1, 1)


def _chart_rows(chart_dict):
    """The rows the Vega-Lite spec actually draws (Altair stores the layer data once, in datasets)."""
    sets = chart_dict["datasets"]
    return max(sets.values(), key=len)


def test_chart_draws_exactly_the_exported_rows():
    rows, w, end = _whatif(-0.5)
    spec = V.retreat_chart(rows, "2016-10-05", w, "Manual removal", end).to_dict()
    drawn = pd.DataFrame(_chart_rows(spec))
    assert len(drawn) == len(rows)
    assert drawn.cumulative_retreat_m.tolist() == pytest.approx(rows.cumulative_retreat_m.tolist(), abs=0)
    assert drawn.date.tolist() == rows.date.tolist()


def test_whatif_chart_is_labelled_and_distinct_from_observations():
    from src.shoreline_remediation.projections import whatif as W
    rows, w, end = _whatif(-0.5)
    spec = V.retreat_chart(rows, "2016-10-05", w, "Manual removal", end).to_dict()
    assert spec["title"]["text"] == "User-defined what-if: manual removal"
    layers = spec["layer"]
    kinds = [lay["mark"]["type"] for lay in layers]
    # band, last-survey rule and label, intervention label, lines, points, survey label and two direct end labels
    assert kinds[0] == "rect" and "rule" in kinds and "point" in kinds and kinds.count("text") == 5
    assert all(lay.get("encoding", {}).get("color", {}).get("legend", "none") is None
               for lay in layers if lay["mark"]["type"] in ("line", "point"))           # direct labels, no legend
    words = json.dumps(spec["datasets"])
    assert "What-if" in words and "Natural recovery" in words and "Last survey" in words and "Surveys" in words
    line = next(lay for lay in layers if lay["mark"]["type"] == "line")
    assert line["encoding"]["strokeDash"]["scale"]["range"] == [[6, 4], [2, 3]]
    assert line["encoding"]["color"]["scale"]["domain"] == [V.OBS_SERIES, V.SCEN_SERIES, f"{W.WHATIF_LABEL}: Manual removal"]
    texts = {lay["mark"].get("text") or str(lay["encoding"].get("text")) for lay in layers if lay["mark"]["type"] == "text"}
    assert any("Intervention" in t for t in texts)


def test_without_an_effect_the_chart_has_no_treatment_line():
    rows, w, end = _whatif("none")
    spec = V.retreat_chart(rows, "2016-10-05", w, "Manual removal", end).to_dict()
    assert spec["title"]["text"] == "Conditional scenario, not a forecast"
    assert "rect" not in [lay["mark"]["type"] for lay in spec["layer"]] and set(rows.arm) == {"observed", "natural_recovery"}


def test_selector_lists_every_report_option_from_the_inventory():
    report = json.loads((ROOT / "results/projection_baseline/bay_jimmy_mapped.report.json").read_text(encoding="utf-8"))
    inv = I.build_inventory(report)
    assert V.option_name(I.REFERENCE).startswith("Natural recovery only") and V.option_name("manual_removal") == "Manual removal"
    assert len(inv.options) == 16


def test_cover_chart_draws_the_exported_rows_with_labels_and_the_peak():
    import datetime as dt
    from src.shoreline_remediation.projections import cover as CV, evidence as EV
    obs = EV.vegetation_observed(CV.observation_spec())
    anchor = CV.anchor_from(obs)
    eff = CV.CoverEffect("manual_removal", dt.date(2030, 1, 1), dt.date(2031, 8, 20), dt.date(2034, 1, 1), 10.0)
    w = CV.two_arms(anchor, dt.date(2040, 1, 1), "annual", eff)
    rows = CV.export_rows(obs, w, "Manual removal")
    spec = V.cover_chart(rows, anchor, w, "Manual removal", dt.date(2040, 1, 1)).to_dict()
    drawn = pd.DataFrame(_chart_rows(spec))
    assert len(drawn) == len(rows) and drawn.total_cover.tolist() == pytest.approx(rows.total_cover.tolist(), abs=0)
    assert drawn.date.tolist()[:6] == ["2011-09", "2012-09", "2013-09", "2014-09", "2015-09", "2016-09"]
    assert spec["title"]["text"] == "User-defined what-if: manual removal"
    kinds = [lay["mark"]["type"] for lay in spec["layer"]]
    assert kinds[0] == "rect" and "rule" in kinds and kinds.count("point") == 2          # survey points and the peak marker
    words = json.dumps(spec["datasets"])
    assert "Peak" in words and "Last survey (2016-09)" in words and "What-if" in words and "Natural recovery" in words
    texts = [lay for lay in spec["layer"] if lay["mark"]["type"] == "text" and lay["mark"].get("fontWeight") == "bold"]
    assert sorted(lay["mark"]["dy"] for lay in texts) == [-10, 14]                        # end labels on opposite sides
    assert "2031-08-20" in words                                                       # the exact off-grid peak is plotted
    y = next(lay for lay in spec["layer"] if lay["mark"]["type"] == "line")["encoding"]["y"]
    assert y["scale"]["domain"] == [0, 100] and y["title"] == "Total vegetation cover (%)"


def test_tpah_chart_draws_the_exported_rows_and_a_vertical_step_at_intervention():
    import datetime as dt
    from src.shoreline_remediation.projections import evidence as EV, pah as PH
    obs = EV.tpah_observed(PH.observation_spec())
    anchor = PH.anchor_from(obs)
    w = PH.two_arms(anchor, dt.date(2030, 1, 1), "annual", 4.0, PH.PahEffect("manual_removal", dt.date(2019, 7, 15), 20.0))
    rows = PH.export_rows(obs, w, "Manual removal")
    spec = V.tpah_chart(rows, anchor, w, "Manual removal", dt.date(2030, 1, 1)).to_dict()
    drawn = pd.DataFrame(_chart_rows(spec))
    assert len(drawn) == len(rows) and drawn.soil_tpah.tolist() == pytest.approx(rows.soil_tpah.tolist(), abs=0)
    line = next(lay for lay in spec["layer"] if lay["mark"]["type"] == "line")
    assert line["encoding"]["order"]["field"] == "order"                       # before/after stay in sequence on one date
    assert line["encoding"]["y"]["title"] == "Soil tPAH, 0–10 cm (mg/kg)"
    words = json.dumps(spec["datasets"])
    step = rows[(rows.arm == PH.TREATMENT_ARM) & rows["sample"].str.startswith("intervention")].soil_tpah.tolist()
    assert f'"before {step[0]:.1f}"' in words and f'"after {step[1]:.1f}"' in words
    assert "2019-07-15" in words and "Last measurement (September 2012)" in words
    assert spec["title"]["text"] == "User-defined what-if: manual removal"
