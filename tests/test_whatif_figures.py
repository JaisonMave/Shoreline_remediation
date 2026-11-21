"""R8: difference plots and PNG/SVG export of the three Bay Jimmy what-ifs, drawn from the CSV the dashboard downloads."""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.shoreline_remediation.projections import cover as CV, evidence as EV, figure as FG, pah as PH, runner, spec as S, \
    whatif as W

ROOT = Path(__file__).resolve().parents[1]
D = dt.date
OK = SimpleNamespace(what_if_allowed=True, what_if_reason="", endpoint="")


def _csv(outcome: str, change) -> str:
    """The CSV text each explorer downloads, built with the same calculation (screening row allowed)."""
    if outcome == "retreat":
        raw = json.loads((ROOT / "examples/projections/bay_jimmy_retreat_2030.json").read_text(encoding="utf-8"))
        raw.update(end_date="2050-01-01")
        sp = S.from_dict(raw)
        eff = None if change is None else W.RetreatEffect("manual_removal", D(2030, 1, 1), D(2040, 1, 1), change)
        row = SimpleNamespace(**{**vars(OK), "endpoint": "cumulative_shoreline_retreat"})
        return W.csv_text(W.compute(sp, runner.observed_record(sp), eff, row).rows)
    if outcome == "cover":
        obs = EV.vegetation_observed(CV.observation_spec())
        eff = None if change is None else CV.CoverEffect("manual_removal", D(2030, 1, 1), D(2032, 1, 1), D(2034, 1, 1), change)
        sp = SimpleNamespace(end=D(2040, 1, 1), cadence="annual", technique="manual_removal", as_of=CV.AS_OF)
        row = SimpleNamespace(**{**vars(OK), "endpoint": CV.ENDPOINT})
        return W.csv_text(CV.compute(sp, obs, eff, row).rows)
    obs = EV.tpah_observed(PH.observation_spec())
    eff = None if change is None else PH.PahEffect("manual_removal", D(2020, 1, 1), change)
    sp = SimpleNamespace(end=D(2030, 1, 1), cadence="annual", technique="manual_removal", as_of=PH.AS_OF)
    row = SimpleNamespace(**{**vars(OK), "endpoint": PH.ENDPOINT})
    return W.csv_text(PH.compute(sp, obs, 4.0, eff, row).rows)


CHANGES = {"retreat": -0.5, "cover": 10.0, "tpah": 20.0}


@pytest.mark.parametrize("outcome", ["retreat", "cover", "tpah"])
def test_plotted_differences_match_the_csv(outcome):
    text = _csv(outcome, CHANGES[outcome])
    m = FG.WHATIF_OUTCOMES[outcome]
    rows = [r for r in csv.DictReader(io.StringIO(text)) if r["arm"] == "treatment_what_if"]
    diff = FG.difference_rows(text, outcome)
    assert diff.x.tolist() == [r[m["x"]] for r in rows]
    assert [f"{v:.6f}" for v in diff.difference] == [r[m["diff"]] for r in rows]
    if outcome == "retreat":
        assert dict(zip(diff.x, diff.difference))["2050-01-01"] == pytest.approx(-5.0)
    if outcome == "cover":
        assert dict(zip(diff.x, diff.difference))["2032-01-01"] == pytest.approx(10.0)
    if outcome == "tpah":                                       # both rows on the intervention date, in order: a vertical step
        step = diff[diff.x == "2020-01-01"]
        assert step["sample"].tolist() == ["intervention_before", "intervention_after"]
        assert step.difference.iloc[0] == 0.0 and step.difference.iloc[1] < 0


@pytest.mark.parametrize("outcome", ["retreat", "cover", "tpah"])
def test_zero_is_a_flat_line_and_blank_hides_the_plot(outcome):
    zero = FG.difference_rows(_csv(outcome, 0.0), outcome)
    assert not zero.empty and (zero.difference == 0.0).all()
    assert FG.difference_rows(_csv(outcome, None), outcome).empty


@pytest.mark.parametrize("outcome", ["retreat", "cover", "tpah"])
def test_png_and_svg_open_and_carry_the_required_labels(outcome):
    from PIL import Image
    out = FG.whatif_figure(_csv(outcome, CHANGES[outcome]), outcome, technique="Manual removal", baseline="BASELINE RULE",
                           last_observation="LAST OBS DATE")
    img = Image.open(io.BytesIO(out["png"]))
    img.verify()
    assert img.format == "PNG" and img.size[0] >= 1000
    root = ET.fromstring(out["svg"])
    text = " ".join(t for t in root.itertext())
    for needed in ("Bay Jimmy", "Manual removal", "BASELINE RULE", FG.WHATIF_OUTCOMES[outcome]["unit"], "LAST OBS DATE",
                   "User-defined what-if", "Treatment minus natural"):
        assert needed in text, needed
    blank = FG.whatif_figure(_csv(outcome, None), outcome, technique="natural recovery only", baseline="B", last_observation="L")
    assert "Treatment minus natural" not in " ".join(ET.fromstring(blank["svg"]).itertext())


def test_panel_shows_difference_plot_and_image_buttons_for_each_outcome():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / "src/shoreline_remediation/dashboard.py"), default_timeout=300)
    at.run()
    at.button(key="home_use_bay_jimmy").click().run()
    at.button(key="home_run").click().run()
    at.session_state["bj_future_panel"] = True
    at.run()
    at.selectbox(key="bj_future_option").set_value("manual_removal").run()
    for outcome, key in (("retreat", "bj_whatif_delta"), ("cover", "bj_cover_delta"), ("tpah", "bj_pah_reduction")):
        at.segmented_control(key="bj_future_outcome").set_value(outcome).run()
        keys = {b.proto.id.split("-")[-1] for b in at.get("download_button")} | {getattr(b, "key", "") for b in at.get("download_button")}
        assert {f"bj_{outcome}_png", f"bj_{outcome}_svg"} <= keys, keys
        captions = " ".join(str(c.value) for c in at.caption)
        assert FG.WHATIF_OUTCOMES[outcome]["sign"] not in captions              # blank: no difference plot
        if outcome == "retreat":
            at.date_input(key="bj_future_end").set_value(D(2050, 1, 1)).run()
            at.date_input(key="bj_whatif_start").set_value(D(2030, 1, 1)).run()
            at.date_input(key="bj_whatif_end").set_value(D(2040, 1, 1)).run()
        at.number_input(key=key).set_value(0.0).run()
        assert not at.exception, at.exception
        assert FG.WHATIF_OUTCOMES[outcome]["sign"] in " ".join(str(c.value) for c in at.caption)
