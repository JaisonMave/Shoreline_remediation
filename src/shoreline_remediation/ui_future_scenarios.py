"""Bay Jimmy Assessment panel: historical technique comparisons and conditional retreat of the field plots.

Presentation only. The technique list, statuses and conditions come from the report through projections.inventory; the
manual-removal values come from the tested projections.slice.manual_vs_natural contract. Nothing here changes a recommendation.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from src.shoreline_remediation import assessment_screening as AS
from types import SimpleNamespace

from src.shoreline_remediation.projections import cover as CV, evidence as EV, figure as FG, inventory as I, pah as PH, \
    projection, runner, slice as SL, spec, whatif as W

EXAMPLE = Path(__file__).resolve().parents[2] / "examples/projections/bay_jimmy_retreat_2030.json"

# Palette (CLAUDE.md section 6): reference arm in the pale highlight, treatment in teal, conditional scenario in blue.
REF_COLOUR, TREAT_COLOUR, SCENARIO_COLOUR = "#B6D9CF", "#28B8A5", "#4E9BE8"
REF_SERIES, TREAT_SERIES = "Natural recovery (untreated)", "Manual removal"
ARM_DESCRIPTION = {REF_SERIES: "untreated, heavily oiled plots", TREAT_SERIES: "manually treated, heavily oiled plots"}
OFFSET_DAYS = 25      # horizontal separation of the two arms at a shared survey, display only
AVAILABILITY_TEXT = {
    "observed_and_contrast": "Measurements and a matched field difference",
    "observed": "Measurements only (no matched difference)",
    "context_only": "Context only (different outcome, unit or comparator)",
    "evidence_gap": "No site evidence",
    "out_of_scope": "Outside the evidence scope",
}


@st.cache_data(show_spinner=False)
def _plot_record():
    return runner.observed_record(spec.load(EXAMPLE))


def _assumption(name, value, unit):
    return dict(assumption_id=name, value=value, unit=unit, origin="user_assumption",
                source="Bay Jimmy Assessment scenario controls")


def option_name(option: str) -> str:
    return "Natural recovery only (reference)" if option == I.REFERENCE else W.technique_label(option)


# ---------------------------------------------------------------------------------------------------------------
# Pure helpers (tested without rendering)

def _when(decimal_year: float) -> pd.Timestamp:
    year = int(decimal_year)
    start = pd.Timestamp(year=year, month=1, day=1)
    return start + (pd.Timestamp(year=year + 1, month=1, day=1) - start) * (decimal_year - year)


def arm_frame(observations: list) -> pd.DataFrame:
    """Tidy chart rows for the two arms of one endpoint: one row per survey and arm, with n and interval provenance."""
    rows = []
    for r in observations:
        ref = r["role"] == "reference"
        when = _when(float(r["decimal_year"]))
        rows.append({
            "series": REF_SERIES if ref else TREAT_SERIES, "plots": ARM_DESCRIPTION[REF_SERIES if ref else TREAT_SERIES],
            "plot_date": when + pd.Timedelta(days=-OFFSET_DAYS if ref else OFFSET_DAYS),
            "survey": r.get("survey_period") or r["date"], "value": float(r["value"]), "unit": r["unit"],
            "lo": r.get("interval_lo"), "hi": r.get("interval_hi"), "n_plots": int(r["n_plots"]),
            "interval": r.get("interval_method") or "no interval",
        })
    return pd.DataFrame(rows)


def cover_contrast_text(panel: dict) -> str:
    rows = panel.get("published_year_two") or []
    c = next((r for r in rows if r["record_type"] == "field_contrast"), None)
    if c is None:
        return "No year-two difference is shown: " + str(panel.get("contrast_unavailable_reason") or "not admitted.")
    means = {r["plot_group_id"]: r["value"] for r in rows if r["record_type"] == "observed_group_mean"}
    return (f"**{c['value']:+.1f} percentage points** more total cover on manually treated plots in September 2012 "
            f"({int(c['interval_level'] * 100)}% Welch interval {c['interval_lo']:+.1f} to {c['interval_hi']:+.1f}; "
            f"{int(c['n_plots'])} manual vs {int(c['n_comparator'])} untreated plots; published group means "
            f"{means.get('manual_removal_heavy', float('nan')):.0f}% vs {means.get('untreated_heavy', float('nan')):.0f}%). "
            "Observational: plots were not randomly assigned.")


def retreat_summary_text(panel: dict) -> str:
    last = {}
    for r in panel["observations"]:
        if r["role"] not in last or r["date"] > last[r["role"]]["date"]:
            last[r["role"]] = r
    m, u = last["intervention"], last["reference"]
    return (f"By {dt.date.fromisoformat(m['date']):%d %b %Y}: **{m['value']:.2f} m** (manual, n = {m['n_plots']}) and "
            f"**{u['value']:.2f} m** (untreated, n = {u['n_plots']}) of cumulative retreat since "
            f"{dt.date.fromisoformat(panel['origin_date']):%d %b %Y}.")


def aerial_table(panel: dict) -> pd.DataFrame:
    return pd.DataFrame([{
        "Period": r["date"], "Manual − untreated (m/yr)": f"{r['value']:+.2f}",
        f"{int(r['interval_level'] * 100)}% interval": f"{r['interval_lo']:+.2f} to {r['interval_hi']:+.2f}",
        "Plots (manual / untreated)": f"{r['n_plots']} / {r['n_comparator']}",
    } for r in panel.get("aerial_rate_contrasts") or []]).set_index("Period")


def tidy_rows(history: dict) -> pd.DataFrame:
    """One flat table of every value the comparison shows, for the tabular alternative and the CSV download."""
    keep = ("endpoint", "option", "role", "record_type", "record_class", "plot_group_id", "comparator_group_id", "date",
            "survey_period", "value", "unit", "interval_lo", "interval_hi", "interval_method", "n_plots", "n_comparator",
            "evidence_id")
    rows = []
    for endpoint, panel in history["endpoints"].items():
        for group in ("observations", "published_year_two", "aerial_rate_contrasts"):
            for r in panel.get(group) or []:
                rows.append({k: r.get(k) for k in keep} | {"endpoint": r.get("endpoint") or endpoint, "table": group})
    out = pd.DataFrame(rows)
    out.insert(0, "site_id", history["site_id"])
    out["status"] = "historical field record (not a forecast)"
    return out


# ---------------------------------------------------------------------------------------------------------------
# Charts

def _arm_chart(frame: pd.DataFrame, y_title: str, fmt: str) -> alt.Chart:
    colour = alt.Color("series:N", title=None, scale=alt.Scale(domain=[REF_SERIES, TREAT_SERIES],
                                                              range=[REF_COLOUR, TREAT_COLOUR]),
                       legend=alt.Legend(orient="bottom", direction="vertical", labelLimit=260))
    shape = alt.Shape("series:N", scale=alt.Scale(domain=[REF_SERIES, TREAT_SERIES], range=["circle", "square"]), legend=None)
    x = alt.X("plot_date:T", title="Survey date", scale=alt.Scale(nice="year"),
              axis=alt.Axis(format="%Y", tickCount="year", grid=False))
    tooltip = ["series:N", alt.Tooltip("plots:N", title="Plots"), alt.Tooltip("survey:N", title="Survey"), alt.Tooltip("value:Q", title=f"Mean ({y_title})", format=fmt),
               alt.Tooltip("lo:Q", title="90% low", format=fmt), alt.Tooltip("hi:Q", title="90% high", format=fmt),
               alt.Tooltip("n_plots:Q", title="Plots (n)"), alt.Tooltip("interval:N", title="Interval method")]
    base = alt.Chart(frame)
    bars = base.transform_filter("isValid(datum.lo) && isValid(datum.hi)").mark_rule(strokeWidth=2).encode(
        x=x, y=alt.Y("lo:Q"), y2="hi:Q", color=colour)
    points = base.mark_point(filled=True, size=75, opacity=1).encode(
        x=x, y=alt.Y("value:Q", title=y_title, axis=alt.Axis(gridOpacity=0.15)), color=colour, shape=shape, tooltip=tooltip)
    return (bars + points).properties(height=240)


def _diver_chart(records: list) -> alt.Chart:
    d = pd.DataFrame([{"date": _when(float(r["decimal_year"])), "value": r["value"], "lo": r["interval_lo"],
                       "hi": r["interval_hi"]} for r in records])
    x = alt.X("date:T", title="Date", axis=alt.Axis(format="%Y", grid=False))
    band = alt.Chart(d).mark_area(opacity=0.25, color=SCENARIO_COLOUR).encode(x=x, y="lo:Q", y2="hi:Q")
    line = alt.Chart(d).mark_line(color=SCENARIO_COLOUR).encode(
        x=x, y=alt.Y("value:Q", title="Index (first campaign = 100)"),
        tooltip=[alt.Tooltip("date:T", format="%b %Y"), alt.Tooltip("value:Q", format=".1f"),
                 alt.Tooltip("lo:Q", title="90% low", format=".1f"), alt.Tooltip("hi:Q", title="90% high", format=".1f")])
    return (band + line).properties(height=200)


# ---------------------------------------------------------------------------------------------------------------
# Sections

def _manual_comparison(inventory: I.Inventory) -> None:
    history = SL.manual_vs_natural(inventory)
    if not isinstance(history, dict):
        st.info(history.reason, icon=":material/info:")
        return
    ep = history["endpoints"]
    st.caption("Historical field records from the Bay Jimmy plots: manual cleanup in December 2010, measured afterwards. "
               "Points are group means with 90% interval bars; the two arms are drawn a few days apart so both stay "
               "visible (tooltips give the survey). No future treatment effect is calculated here.")
    cover, pah, retreat = st.columns(3, gap="medium")
    with cover:
        st.markdown("**Total vegetation cover (%)**")
        st.altair_chart(_arm_chart(arm_frame(ep[SL.COVER]["observations"]), "Cover (%)", ".1f"), width="stretch",
                        alt="Total vegetation cover of manual-removal and untreated plots at each September survey, 2011 to 2016.")
        st.markdown(cover_contrast_text(ep[SL.COVER]))
        st.caption(ep[SL.COVER]["limitation"] + " Manual plots were surveyed in 2011 and 2012 only.")
    with pah:
        st.markdown("**Soil total PAH (mg/kg)**")
        st.altair_chart(_arm_chart(arm_frame(ep[SL.PAH]["observations"]), "tPAH (mg/kg)", ".0f"), width="stretch",
                        alt="Soil tPAH of manual-removal and untreated plots in July-August 2011 and September 2012.")
        st.markdown("Measured in 0–10 cm cores in Jul–Aug 2011 and Sep 2012. **No treatment-specific future decline rate** "
                    "can be estimated from two dates.")
        st.caption(ep[SL.PAH]["limitation"])
        regional = ep[SL.PAH].get("regional_reference") or {}
        if regional.get("records") and st.toggle("Show regional PAH index (separate scale)", key="bj_hist_diver"):
            st.altair_chart(_diver_chart(regional["records"]), width="stretch",
                            alt="Regional DIVER heavy-oiling PAH index with its 90% band, first campaign equals 100.")
            st.caption(f"Model reference, not a plot measurement: {regional['records'][0]['status']}. "
                       f"{regional['records'][0]['analyte']}. Support {regional['records'][0]['campaign_support']}.")
    with retreat:
        st.markdown("**Cumulative shoreline retreat since 4 Dec 2010 (m)**")
        st.altair_chart(_arm_chart(arm_frame(ep[SL.RETREAT]["observations"]), "Retreat (m)", ".2f"),
                        width="stretch", alt="Cumulative marsh-edge retreat of manual-removal and untreated plots, 2010 to 2016.")
        st.markdown(retreat_summary_text(ep[SL.RETREAT]))
        st.caption("Aerial-photo erosion rates on a separate scale: change in m/yr from the 2005–2010 pre-spill rate.")
        st.table(aerial_table(ep[SL.RETREAT]))
        st.caption(ep[SL.RETREAT]["limitation"])

    notes = [history["shared_plots_note"]]
    if history["unresolved_conditions"]:
        notes.append("Condition not established for this site: " + "; ".join(history["unresolved_conditions"]) + ".")
    st.caption(" ".join(notes))
    rows = tidy_rows(history)
    if st.toggle("Show the values as a table", key="bj_hist_table"):
        st.dataframe(rows, hide_index=True, width="stretch")
    left, right = st.columns(2)
    left.download_button("Download comparison JSON", json.dumps(history, indent=2, default=str),
                         file_name="bay_jimmy_manual_vs_natural.json", mime="application/json", on_click="ignore",
                         icon=":material/download:", width="stretch")
    right.download_button("Download comparison CSV", rows.to_csv(index=False), file_name="bay_jimmy_manual_vs_natural.csv",
                          mime="text/csv", on_click="ignore", icon=":material/download:", width="stretch")


def _technique_status(inventory: I.Inventory, option: str) -> None:
    first = inventory.cell(option, I.ENDPOINT_ORDER[0])
    st.markdown(f"**{option_name(option)}**: {first.category_label}. {first.category_reason}")
    if first.prerequisites:
        st.caption(f"Presupposes {', '.join(p.replace('_', ' ') for p in first.prerequisites)}, which is "
                   f"{first.prerequisite_state} here.")
    if first.conditions:
        st.caption("Conditions from the screening rules: " + "; ".join(first.conditions))
    table = pd.DataFrame([{
        "Outcome": e.replace("_", " ").capitalize() + f" ({inventory.cell(option, e).endpoint_unit})",
        "What exists at Bay Jimmy": AVAILABILITY_TEXT[inventory.cell(option, e).availability],
        "Why no comparison is drawn": inventory.cell(option, e).unavailable_reason,
    } for e in I.ENDPOINT_ORDER])
    st.dataframe(table, hide_index=True, width="stretch")
    if option != SL.MANUAL:
        st.caption("Only manual removal has a historical comparison with natural recovery at these plots. "
                   + ("Excluded methods are not offered as future interventions." if first.category == "excluded" else ""))


WHATIF_DEFAULTS = {"bj_whatif_start": dt.date(2027, 1, 1), "bj_whatif_end": dt.date(2030, 1, 1), "bj_whatif_delta": None,
                   "bj_cover_start": dt.date(2027, 1, 1), "bj_cover_peak": dt.date(2029, 1, 1),
                   "bj_cover_stop": dt.date(2032, 1, 1), "bj_cover_delta": None,
                   "bj_pah_date": dt.date(2027, 1, 1), "bj_pah_reduction": None, "bj_pah_basis": PH.DEFAULT_BASIS}
OUTCOMES = {"retreat": "Shoreline retreat", "cover": "Vegetation cover", "tpah": "Soil tPAH"}
PAH_BASELINES = {PH.HOLD: "Hold concentration at the last observation", PH.HALF_LIFE: "Assume a decline half-life"}
RETREAT = "cumulative_shoreline_retreat"


def _clear_whatif() -> None:
    """A what-if belongs to one technique: changing the technique resets it instead of silently carrying it over. The
    defaults are assigned (not deleted) so the browser's widgets are reset too; a deleted key lets a widget resend its value."""
    for key, value in WHATIF_DEFAULTS.items():
        st.session_state[key] = value


def _technique_section(report) -> tuple:
    """Draw the selector and the historical view. Returns (inventory, choice), or (None, None) when out of scope."""
    inventory = I.build_inventory(report)
    if not inventory.in_scope:
        st.info(inventory.scope_reason, icon=":material/info:")
        return None, None
    options = [I.REFERENCE] + [o for o in inventory.options if o != I.REFERENCE]
    labels = {o: option_name(o) + ("" if o == I.REFERENCE else f" · {inventory.cell(o, I.ENDPOINT_ORDER[0]).category_label}")
              for o in options}
    choice = st.selectbox("Technique to compare with natural recovery", options, format_func=labels.__getitem__,
                          key="bj_future_option", on_change=_clear_whatif,
                          help="Statuses come from this assessment's screening. Changing the technique never changes them "
                               "and clears any what-if entered for the previous technique.")
    if choice == I.REFERENCE:
        st.caption("Choose a technique to see its historical comparison with natural recovery or the evidence it lacks.")
    elif choice == SL.MANUAL:
        _manual_comparison(inventory)
    else:
        _technique_status(inventory, choice)
    return inventory, choice


def evidence_statement(row: I.InventoryRow) -> str:
    """What the repository does and does not hold for this technique's retreat effect (shown beside the what-if inputs)."""
    name = option_name(row.option).lower()
    if any(s.on_endpoint and s.record_type == "field_contrast" for s in row.support):
        return f"A matched field difference exists for {name}; it is shown above and is not applied to this future curve."
    if row.availability == "evidence_gap":
        return (f"The repository has no measured treatment effect of {name} on shoreline retreat. Any change you enter is "
                "your own assumption.")
    return (f"No measured future retreat effect exists for {name}. The historical treated plots and the aerial erosion-rate "
            "differences above describe past plots on their own scales and are not applied here. Any change you enter is your "
            "own assumption for a hypothetical shoreline that starts from the untreated plots' last survey.")


def _whatif_controls(inventory, choice) -> W.RetreatEffect | None:
    st.markdown("**Treatment what-if (user-defined)**")
    if inventory is None or choice in (None, I.REFERENCE):
        st.caption("Choose a technique at the top of this panel to add a user-defined treatment curve.")
        return None
    row = inventory.cell(choice, RETREAT)
    if not row.what_if_allowed:
        st.info(f"No what-if for {option_name(choice).lower()}. {row.what_if_reason}", icon=":material/block:")
        return None
    st.caption(evidence_statement(row))
    if row.unresolved_conditions:
        st.caption("Condition not established for this site, carried with this technique: "
                   + "; ".join(row.unresolved_conditions) + ".")
    for key, value in WHATIF_DEFAULTS.items():      # one place for the defaults, so a reset reaches the browser widgets
        st.session_state.setdefault(key, value)
    left, middle, right = st.columns(3)
    start = left.date_input("Intervention starts", min_value=dt.date(2016, 10, 6), max_value=dt.date(2100, 12, 30),
                            key="bj_whatif_start")
    stop = middle.date_input("Effect ends", min_value=dt.date(2016, 10, 7), max_value=dt.date(2100, 12, 31),
                             key="bj_whatif_end")
    delta = right.number_input("Change from the natural-recovery rate (m/year)", value=None, step=0.1, format="%.2f",
                               key="bj_whatif_delta", placeholder="Blank: no treatment curve",
                               help="Negative = slower retreat (less land lost). Positive = faster retreat. 0 = no change.")
    right.caption("Negative = slower retreat. Positive = faster retreat.")
    st.caption("Applied only between the two dates, on top of the natural-recovery rate schedule above; afterwards that "
               "schedule resumes and the distance gained or lost is kept. Changing the technique clears these entries.")
    if start is None or stop is None:
        st.info("Choose both dates to apply the assumed change.")
        return None
    return W.RetreatEffect(choice, start, stop, delta)


def _retreat_explorer(inventory=None, choice=None, context=None) -> None:
    st.markdown("**Conditional future retreat: untreated plots**")
    st.caption("Bay Jimmy · Nine untreated, heavily oiled marsh plots. Choose a retreat rate to see how far "
               "their edge would move if that rate held after the final survey. Historical tests on these nine "
               "plots covered lead times up to about four years. Neither candidate improved on the constant-rate "
               "baseline enough to meet the study criteria. Longer projections depend on the rates you choose.")
    end = st.date_input("Scenario end date", dt.date(2030, 1, 1), min_value=dt.date(2017, 1, 1),
                        max_value=dt.date(2100, 12, 31), key="bj_future_end")
    rate = st.number_input("Assumed annual retreat (m/year)", min_value=0.0, value=1.43, step=0.1,
                           key="bj_future_rate", help="1.43 is the rounded long-run rate fitted to the historical plots.")
    if end is None or rate is None:
        st.info("Choose an end date and enter a retreat rate to calculate the scenario.")
        return
    assumptions = [_assumption("retreat_rate", rate, "m/yr")]
    if st.checkbox("Change the rate on a second date", key="bj_future_change"):
        change = st.date_input("Rate change date", min(dt.date(2030, 1, 1), end - dt.timedelta(days=1)),
                               min_value=dt.date(2016, 10, 6), max_value=end - dt.timedelta(days=1),
                               key="bj_future_change_date")
        second = st.number_input("Annual retreat after the change (m/year)", min_value=0.0, value=2.19,
                                 step=0.1, key="bj_future_second")
        if change is None or second is None:
            st.info("Choose the change date and enter the second rate.")
            return
        assumptions.extend([_assumption("rate_change_date", change.isoformat(), "date"),
                            _assumption("changed_retreat_rate", second, "m/yr")])

    effect = _whatif_controls(inventory, choice)

    try:
        raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        raw.update(scenario_id="bay_jimmy_dashboard_retreat", description="Conditional retreat under the selected rates.",
                   end_date=end.isoformat(), assumptions=assumptions)
        scenario = spec.from_dict(raw)
        unsupported = spec.check_scope(scenario)
        if unsupported:
            st.info(unsupported.reason)
            return
        observations = _plot_record()
        observations = observations.loc[observations.available_at_as_of].sort_values("date")
        if observations.empty:
            st.info("A dated Bay Jimmy observation is needed to start the projection.")
            return
        anchor = observations.iloc[-1]
        series, _ = projection.project(scenario, dt.date.fromisoformat(anchor.date), float(anchor.value),
                                       int(anchor.n_plots))
        row = inventory.cell(choice, RETREAT) if inventory is not None and choice not in (None, I.REFERENCE) else None
        computed = W.compute(scenario, observations, effect, row)       # the same calculation the CLI replays
        what = computed.what
    except (OSError, ValueError, RuntimeError) as exc:
        st.error(f"Could not build this retreat scenario. {exc}")
        return

    last = series.iloc[-1]
    st.markdown(f"**{last.additional_retreat_since_anchor_m:.2f} m additional retreat** by {end:%d %b %Y} "
                f"under these assumptions ({last.cumulative_retreat_since_origin_m:.2f} m since December 2010).")
    label = option_name(choice) if choice else ""
    if effect is not None and effect.delta_rate is not None and not what.has_treatment:
        st.warning(what.message, icon=":material/warning:")
    if what.has_treatment:
        st.markdown(f"**{W.WHATIF_LABEL}, {label.lower()}.** " + W.summary_text(what, end))
        if effect.end > end:
            st.caption(f"The assumed effect continues past the scenario end date; only the part up to {end:%d %b %Y} is shown.")
    rows = computed.rows
    st.altair_chart(retreat_chart(rows, anchor.date, what, label, end), width="stretch",
                    alt="Observed Bay Jimmy retreat through October 2016 and conditional retreat at the selected rates"
                        + (", with a user-defined treatment what-if." if what.has_treatment else "."))
    st.caption("Dots show measured group means (Zengel et al., 2022). The dashed line starts at the final "
               "survey on 5 October 2016. Future storms, changes in marsh geometry and treatment effects "
               "are outside this calculation.")
    if what.has_treatment:
        st.caption("The dotted teal line applies only the change you entered, during the shaded period. It is a "
                   "user-defined what-if, not a measured treatment effect, and it does not change any recommendation."
                   + (" The historical manual plots above are a different set of plots and are not part of this calculation."
                      if choice == SL.MANUAL else ""))
    st.download_button("Download scenario inputs", scenario.to_json(), file_name="bay_jimmy_scenario.json",
                       mime="application/json", on_click="ignore")
    st.download_button("Download projection CSV", series.to_csv(index=False), file_name="bay_jimmy_retreat.csv",
                       mime="text/csv", on_click="ignore")
    if what.has_treatment:
        if context is not None:
            payload = whatif_payload(scenario, computed, inventory.cell(choice, RETREAT), effect, context, end)
            st.download_button("Download what-if JSON", json.dumps(payload, indent=2, allow_nan=False),
                               file_name="bay_jimmy_retreat_whatif.json", mime="application/json", on_click="ignore",
                               icon=":material/download:",
                               help="A replayable scenario (spec version 2): python -m src.shoreline_remediation.projections "
                                    "run --scenario <this file> --output <new folder>")
        st.download_button("Download what-if CSV", W.csv_text(rows), file_name="bay_jimmy_retreat_whatif.csv",
                           mime="text/csv", on_click="ignore", icon=":material/download:")
    figure_section(W.csv_text(rows), "retreat", **FG.whatif_labels("retreat", computed, label))


def whatif_payload(scenario, computed: W.Computed, row: I.InventoryRow, effect: W.RetreatEffect, context: dict,
                   end: dt.date) -> dict:
    """The what-if download: a version-2 scenario the projections CLI replays (inputs), plus what this page showed under
    `exported_outputs`. Replay recomputes everything from the inputs and re-screens the technique; the outputs are only
    compared."""
    last = computed.what.last
    payload = W.spec_dict_v2(scenario.to_dict(), row.option, context, effect)
    payload["exported_outputs"] = {
        "note": "Outputs shown in the dashboard when this file was saved. Never used as inputs on replay.",
        "label": W.WHATIF_LABEL, "screening_category_at_export": row.category, "eligibility_at_export": row.what_if_reason,
        "evidence_statement": evidence_statement(row), "unresolved_conditions": list(row.unresolved_conditions),
        "summary": {"end_date": end.isoformat(), "natural_recovery_m": float(last.natural_recovery_m),
                    "treatment_m": float(last.treatment_m), "difference_m": float(last.difference_m),
                    "text": W.summary_text(computed.what, end)},
        "csv_float_format": W.CSV_FLOAT_FORMAT,
        "not": "not a measured treatment effect, not a forecast, not used for ranking or recommendations",
        "rows": computed.rows.astype(object).where(computed.rows.notna(), None).to_dict("records"),
    }
    return payload


OBS_SERIES, SCEN_SERIES = "Observed (untreated plots)", "Natural recovery (assumed rate)"
END_TAGS = {W.NATURAL_ARM: ("Natural recovery", -10), W.TREATMENT_ARM: ("What-if", 14)}
CHART_HEIGHT = 340


def retreat_chart(rows: pd.DataFrame, anchor_date: str, what: W.WhatIf, option_label: str, end: dt.date) -> alt.LayerChart:
    """Built from the same rows as the CSV download. Observations are points; the natural-recovery scenario is a pale dashed
    line; a user-defined what-if is a teal dotted line. Both lines carry direct end labels, the last survey is a rule and the
    intervention period is shaded."""
    treat = f"{W.WHATIF_LABEL}: {option_label}" if what.has_treatment else None
    domain = [OBS_SERIES, SCEN_SERIES] + ([treat] if treat else [])
    colour = alt.Color("series:N", title=None,
                       scale=alt.Scale(domain=domain, range=[REF_COLOUR, REF_COLOUR, TREAT_COLOUR][:len(domain)]),
                       legend=None)       # every series is labelled directly, so the plot keeps its height on mobile
    dash = alt.StrokeDash("series:N", scale=alt.Scale(domain=domain[1:], range=[[6, 4], [2, 3]][:len(domain) - 1]), legend=None)
    x = alt.X("date:T", title="Year", axis=alt.Axis(format="%Y"))
    y = alt.Y("cumulative_retreat_m:Q", title="Retreat since Dec 2010 (m)")
    tip = ["series:N", alt.Tooltip("date:T", title="Date"),
           alt.Tooltip("cumulative_retreat_m:Q", title="Cumulative (m)", format=".2f"),
           alt.Tooltip("difference_from_natural_m:Q", title="Difference from natural (m)", format="+.2f"),
           alt.Tooltip("status_label:N", title="Status")]
    base = alt.Chart(rows)
    lines = base.transform_filter("datum.arm != 'observed'").mark_line(strokeWidth=2.5).encode(
        x=x, y=y, color=colour, strokeDash=dash, tooltip=tip)
    points = base.transform_filter("datum.arm == 'observed'").mark_point(filled=True, size=60, opacity=1).encode(
        x=x, y=y, color=colour, tooltip=tip + [alt.Tooltip("n_plots:Q", title="Plots (n)")])
    ends = rows[rows.arm != "observed"].groupby("arm").tail(1)
    labels = []
    for arm, (tag, dy) in END_TAGS.items():
        one = ends[ends.arm == arm].assign(tag=tag)
        if not one.empty:
            labels.append(alt.Chart(one).mark_text(align="right", dx=-2, dy=dy, fontSize=12, fontWeight="bold",
                                                   color=REF_COLOUR if arm == W.NATURAL_ARM else TREAT_COLOUR).encode(
                x=x, y=y, text="tag:N"))
    last_obs = rows[rows.arm == "observed"].tail(1).assign(tag="Surveys")
    labels.append(alt.Chart(last_obs).mark_text(align="right", dx=-8, dy=-12, fontSize=12, color=REF_COLOUR).encode(
        x=x, y=y, text="tag:N"))
    survey = pd.DataFrame({"date": [anchor_date], "label": ["Last survey"]})
    layers = [alt.Chart(survey).mark_rule(color="#A6B2C2", strokeDash=[2, 2]).encode(x="date:T", tooltip=["label:N", "date:T"]),
              alt.Chart(survey).mark_text(align="left", baseline="top", dx=4, dy=4, fontSize=11, color="#A6B2C2").encode(
                  x="date:T", y=alt.value(0), text="label:N")]
    if what.has_treatment:
        e = what.effect
        period = pd.DataFrame({"start": [e.start.isoformat()], "stop": [min(e.end, end).isoformat()],
                               "label": ["Assumed intervention period"]})
        layers.insert(0, alt.Chart(period).mark_rect(color=TREAT_COLOUR, opacity=0.12).encode(
            x="start:T", x2="stop:T",
            tooltip=["label:N", alt.Tooltip("start:T", title="From"), alt.Tooltip("stop:T", title="To")]))
        layers.append(alt.Chart(period).mark_text(align="left", baseline="top", dx=3, dy=4, fontSize=11,
                                                  color=TREAT_COLOUR).encode(x="start:T", y=alt.value(0),
                                                                             text=alt.value("Intervention")))
        title = f"{W.WHATIF_LABEL}: {option_label.lower()}"
    else:
        title = "Conditional scenario, not a forecast"
    return alt.layer(*layers, lines, points, *labels).properties(
        height=CHART_HEIGHT, title=alt.TitleParams(title, anchor="start", color="#F4F7FA", fontSize=13))


def render(report=None, run_spec=None) -> None:
    panel = st.expander("Explore future scenarios", key="bj_future_panel", icon=":material/show_chart:",
                        on_change="rerun")
    if not panel.open:
        return
    with panel:
        inventory, choice = (None, None)
        if report is not None:
            inventory, choice = _technique_section(report)
            st.divider()
        context = AS.context_from_run_spec(run_spec)
        outcome = st.segmented_control("Future outcome", list(OUTCOMES), format_func=OUTCOMES.__getitem__, default="retreat",
                                       required=True, key="bj_future_outcome")
        if outcome == "cover":
            _cover_explorer(inventory, choice, context)
        elif outcome == "tpah":
            _tpah_explorer(inventory, choice, context)
        else:
            _retreat_explorer(inventory, choice, context)


# ---------------------------------------------------------------------------------------------------------------
# Vegetation cover what-if (cover_whatif/1)

@st.cache_data(show_spinner=False)
def _cover_record() -> pd.DataFrame:
    return EV.vegetation_observed(CV.observation_spec())


def cover_evidence_statement(inventory: I.Inventory, row: I.InventoryRow) -> str:
    """The field evidence for this technique's cover effect at Bay Jimmy, kept beside the (blank) future effect."""
    name = option_name(row.option).lower()
    if row.option == SL.MANUAL and row.comparison_status == "":
        history = SL.manual_vs_natural(inventory)
        if isinstance(history, dict):
            return ("Field evidence, kept for reference and not applied to the future curve: "
                    + cover_contrast_text(history["endpoints"][SL.COVER]))
    if row.availability == "evidence_gap":
        return (f"There is no measured Bay Jimmy cover effect for {name}. Any change you enter is your own assumption.")
    return (f"No measured future cover effect exists for {name}. Historical measurements are shown above on their own dates "
            "and are not applied here. Any change you enter is your own assumption.")


def _cover_controls(inventory, choice, anchor: CV.Anchor) -> CV.CoverEffect | None:
    st.markdown("**Treatment what-if (user-defined)**")
    if inventory is None or choice in (None, I.REFERENCE):
        st.caption("Choose a technique at the top of this panel to add a user-defined treatment curve.")
        return None
    row = inventory.cell(choice, CV.ENDPOINT)
    if not row.what_if_allowed:
        st.info(f"No what-if for {option_name(choice).lower()}. {row.what_if_reason}", icon=":material/block:")
        return None
    st.caption(cover_evidence_statement(inventory, row))
    if row.unresolved_conditions:
        st.caption("Condition not established for this site, carried with this technique: "
                   + "; ".join(row.unresolved_conditions) + ".")
    for key, value in WHATIF_DEFAULTS.items():
        st.session_state.setdefault(key, value)
    first, second, third = st.columns(3)
    start = first.date_input("Intervention starts", min_value=dt.date(2016, 10, 1), max_value=dt.date(2100, 12, 29),
                             key="bj_cover_start")
    peak = second.date_input("Effect peaks", min_value=dt.date(2016, 10, 2), max_value=dt.date(2100, 12, 30),
                             key="bj_cover_peak")
    stop = third.date_input("Effect ends", min_value=dt.date(2016, 10, 3), max_value=dt.date(2100, 12, 31),
                            key="bj_cover_stop")
    lo, hi = CV.allowed_range(anchor.value)
    delta = st.number_input("Peak change from the natural-recovery scenario (percentage points)", value=None, step=1.0,
                            format="%.1f", key="bj_cover_delta", placeholder="Blank: no treatment curve",
                            help="Positive = more cover than natural recovery; negative = damage (less cover). 0 = no change.")
    st.caption(f"Positive = more cover; negative = damage. Allowed: {lo:+.1f} to {hi:+.1f} percentage points, which keeps "
               f"total cover within 0–100% (baseline {anchor.value:.1f}%). {CV.TEMPORARY_NOTE} Changing the technique clears "
               "these entries.")
    if start is None or peak is None or stop is None:
        st.info("Choose all three dates to apply the assumed change.")
        return None
    return CV.CoverEffect(choice, start, peak, stop, delta)


def _cover_explorer(inventory=None, choice=None, context=None) -> None:
    st.markdown("**Conditional future cover: untreated plots**")
    observations = _cover_record()
    anchor = CV.anchor_from(observations)
    if anchor is None:
        st.info(CV.no_anchor_reason(SimpleNamespace(as_of=CV.AS_OF)), icon=":material/info:")
        return
    month = dt.date.fromisoformat(anchor.survey + "-01")
    st.markdown(f"Last untreated, heavily oiled survey: **{month:%B %Y}** (date precision: {anchor.date_precision}; "
                f"{anchor.date_basis}) · mean total cover **{anchor.value:.1f}%** · **{anchor.n_plots} plots**.")
    st.caption(f"{CV.BASELINE_LABEL} ({anchor.value:.1f}% from {anchor.starts:%d %b %Y}, the end of the survey month). This is an "
               "assumption, not a recovery forecast: cover on these plots fell from 92.0% in 2015 to 70.0% in 2016, and no "
               "later survey tests any future rule.")
    end = st.date_input("Scenario end date", dt.date(2040, 1, 1), min_value=dt.date(2017, 1, 1), max_value=dt.date(2100, 12, 31),
                        key="bj_cover_end")
    if end is None:
        st.info("Choose an end date to draw the scenario.")
        return
    effect = _cover_controls(inventory, choice, anchor)
    row = inventory.cell(choice, CV.ENDPOINT) if inventory is not None and choice not in (None, I.REFERENCE) else None
    sp = SimpleNamespace(end=end, cadence="annual", technique=choice or "", as_of=CV.AS_OF)
    computed = CV.compute(sp, observations, effect, row)          # the same calculation the CLI replays
    what, rows, label = computed.what, computed.rows, computed.label
    if effect is not None and effect.peak_change is not None and not what.has_treatment:
        st.warning(what.message, icon=":material/warning:")
    if what.has_treatment:
        st.markdown(f"**{CV.WHATIF_LABEL}, {label.lower()}.** " + CV.peak_text(what))
    else:
        st.markdown(CV.peak_text(what))
    st.altair_chart(cover_chart(rows, anchor, what, label, end), width="stretch",
                    alt="Measured total cover of the untreated Bay Jimmy plots, 2011 to 2016, the natural-recovery scenario held "
                        "at the last observed value" + (", and a user-defined temporary treatment change." if what.has_treatment
                                                        else "."))
    st.caption("Points are survey means of the untreated, heavily oiled plots with 90% intervals (Zengel et al. GRIIDC dataset). "
               "Surveys are dated to the month and drawn at the end of the survey month. The lines are conditional scenarios, "
               "not forecasts.")
    if what.has_treatment:
        st.caption("The dotted teal line applies only the peak change you entered, rising during the shaded period to the peak "
                   "and returning to zero by its end. It is a user-defined what-if, not a measured treatment effect, and it does "
                   "not change any recommendation.")
    left, right = st.columns(2)
    if context is not None:
        technique = choice if choice not in (None, I.REFERENCE) else I.REFERENCE
        payload = cover_payload(computed, technique, context, effect if what.has_treatment else None, end, inventory)
        left.download_button("Download cover JSON", json.dumps(payload, indent=2, allow_nan=False),
                             file_name="bay_jimmy_cover_whatif.json", mime="application/json", on_click="ignore",
                             icon=":material/download:", width="stretch",
                             help="A replayable scenario (spec version 2): python -m src.shoreline_remediation.projections "
                                  "run --scenario <this file> --output <new folder>")
    right.download_button("Download cover CSV", W.csv_text(rows), file_name="bay_jimmy_cover_whatif.csv", mime="text/csv",
                          on_click="ignore", icon=":material/download:", width="stretch")
    figure_section(W.csv_text(rows), "cover", **FG.whatif_labels("cover", computed, label))


def cover_payload(computed: CV.Computed, technique: str, context: dict, effect, end: dt.date, inventory) -> dict:
    """The cover download: a version-2 scenario the projections CLI replays (inputs) plus what this page showed (outputs)."""
    payload = CV.spec_dict(CV.AS_OF, end, "annual", technique, context, effect)
    w = computed.what
    peak = w.at(w.effect.peak) if computed.applied else None
    row = inventory.cell(technique, CV.ENDPOINT) if inventory is not None else None
    payload["exported_outputs"] = {
        "note": "Outputs shown in the dashboard when this file was saved. Never used as inputs on replay.",
        "label": CV.WHATIF_LABEL, "baseline": CV.BASELINE_LABEL,
        "eligibility_at_export": getattr(row, "what_if_reason", None),
        "summary": {"peak_date": None if peak is None else w.effect.peak.isoformat(),
                    "natural_recovery_pct": w.anchor.value if peak is None else float(peak.natural_recovery_pct),
                    "treatment_pct": None if peak is None else float(peak.treatment_pct),
                    "difference_pp": None if peak is None else float(peak.difference_pp), "text": CV.peak_text(w)},
        "csv_float_format": W.CSV_FLOAT_FORMAT,
        "rows": computed.rows.astype(object).where(computed.rows.notna(), None).to_dict("records"),
    }
    return payload


COVER_TAGS = {CV.NATURAL_ARM: ("Natural recovery", -10), CV.TREATMENT_ARM: ("What-if", 14)}


def cover_chart(rows: pd.DataFrame, anchor: CV.Anchor, what: CV.CoverWhatIf, option_label: str, end: dt.date) -> alt.LayerChart:
    """Built from the same rows as the CSV download: survey means with 90% interval bars, the last untreated survey, the
    natural-recovery scenario (pale dashed) and the what-if (teal dotted) with direct labels, the effect period and its peak."""
    treat = f"{CV.WHATIF_LABEL}: {option_label}" if what.has_treatment else None
    domain = ["Observed (untreated plots)", CV.BASELINE_LABEL] + ([treat] if treat else [])
    colour = alt.Color("series:N", scale=alt.Scale(domain=domain, range=[REF_COLOUR, REF_COLOUR, TREAT_COLOUR][:len(domain)]),
                       legend=None)
    dash = alt.StrokeDash("series:N", scale=alt.Scale(domain=domain[1:], range=[[6, 4], [2, 3]][:len(domain) - 1]), legend=None)
    x = alt.X("plot_date:T", title="Year", axis=alt.Axis(format="%Y"))
    y = alt.Y("total_cover:Q", title="Total vegetation cover (%)", scale=alt.Scale(domain=[0, 100]))
    tip = ["series:N", alt.Tooltip("date:N", title="Date"), alt.Tooltip("date_precision:N", title="Date precision"),
           alt.Tooltip("total_cover:Q", title="Cover (%)", format=".1f"),
           alt.Tooltip("difference_from_natural:Q", title="Difference (percentage points)", format="+.1f"),
           alt.Tooltip("status_label:N", title="Status")]
    base = alt.Chart(rows)
    observed = base.transform_filter("datum.arm == 'observed'")
    bars = observed.mark_rule(strokeWidth=2, color=REF_COLOUR).encode(x=x, y="interval_lo:Q", y2="interval_hi:Q")
    points = observed.mark_point(filled=True, size=60, opacity=1).encode(
        x=x, y=y, color=colour, tooltip=tip + [alt.Tooltip("n_plots:Q", title="Plots (n)"),
                                               alt.Tooltip("interval_method:N", title="Interval")])
    lines = base.transform_filter("datum.arm != 'observed'").mark_line(strokeWidth=2.5).encode(
        x=x, y=y, color=colour, strokeDash=dash, tooltip=tip)
    labels = []
    ends = rows[rows.arm != "observed"].groupby("arm").tail(1)
    # The arms meet again after the effect, so their end labels sit on opposite sides of the line: the natural-recovery label
    # away from the side the effect moves towards (below for a gain, above for damage), so neither crosses the peak.
    gain = not what.has_treatment or what.effect.peak_change >= 0
    offsets = {CV.NATURAL_ARM: 14 if gain else -10, CV.TREATMENT_ARM: -10 if gain else 14}
    for arm, (tag, _) in COVER_TAGS.items():
        dy = offsets[arm]
        one = ends[ends.arm == arm].assign(tag=tag)
        if not one.empty:
            labels.append(alt.Chart(one).mark_text(align="right", dx=-2, dy=dy, fontSize=12, fontWeight="bold",
                                                   color=REF_COLOUR if arm == CV.NATURAL_ARM else TREAT_COLOUR).encode(
                x=x, y=y, text="tag:N"))
    survey = pd.DataFrame({"plot_date": [anchor.starts.isoformat()], "label": [f"Last survey ({anchor.survey})"]})
    layers = [alt.Chart(survey).mark_rule(color="#A6B2C2", strokeDash=[2, 2]).encode(x="plot_date:T", tooltip=["label:N"]),
              alt.Chart(survey).mark_text(align="left", baseline="top", dx=4, dy=4, fontSize=11, color="#A6B2C2").encode(
                  x="plot_date:T", y=alt.value(0), text=alt.value("Last survey"))]
    if what.has_treatment:
        e = what.effect
        period = pd.DataFrame({"start": [e.start.isoformat()], "stop": [min(e.end, end).isoformat()],
                               "label": ["Assumed effect period"]})
        layers.insert(0, alt.Chart(period).mark_rect(color=TREAT_COLOUR, opacity=0.12).encode(
            x="start:T", x2="stop:T", tooltip=["label:N", alt.Tooltip("start:T", title="From"), alt.Tooltip("stop:T", title="To")]))
        layers.append(alt.Chart(period).mark_text(align="left", baseline="top", dx=3, dy=4, fontSize=11, color=TREAT_COLOUR)
                      .encode(x="start:T", y=alt.value(0), text=alt.value("Intervention")))
        peak = rows[(rows.arm == CV.TREATMENT_ARM) & (rows["sample"] == "effect_peak")].assign(tag="Peak")
        labels.append(alt.Chart(peak).mark_point(shape="diamond", size=90, filled=True, color=TREAT_COLOUR).encode(
            x=x, y=y, tooltip=tip))
        labels.append(alt.Chart(peak).mark_text(dy=-14 if e.peak_change >= 0 else 16, fontSize=11, color=TREAT_COLOUR).encode(
            x=x, y=y, text="tag:N"))
        title = f"{CV.WHATIF_LABEL}: {option_label.lower()}"
    else:
        title = "Conditional scenario, not a forecast"
    return alt.layer(*layers, bars, lines, points, *labels).properties(
        height=CHART_HEIGHT, title=alt.TitleParams(title, anchor="start", color="#F4F7FA", fontSize=13))


# ---------------------------------------------------------------------------------------------------------------
# Soil tPAH what-if (tpah_whatif/1)

@st.cache_data(show_spinner=False)
def _tpah_record(group_id: str = "untreated_heavy") -> pd.DataFrame:
    return EV.tpah_observed(PH.observation_spec(group_id))


def tpah_evidence_table(untreated: pd.DataFrame, manual: pd.DataFrame) -> pd.DataFrame:
    """Both groups' measured soil tPAH on their survey periods: reference only, never used to fill the treatment assumption."""
    rows = []
    for label, frame in (("Untreated, heavily oiled", untreated), ("Manual removal, heavily oiled", manual)):
        for _, r in frame.iterrows():
            rows.append({"Plots": label, "Survey": r.survey_period, "Mean tPAH (mg/kg)": f"{r['value']:.0f}",
                         "90% interval (mg/kg)": f"{r.interval_lo:.0f} to {r.interval_hi:.0f}", "n": int(r.n_plots)})
    return pd.DataFrame(rows).set_index("Plots")


def tpah_evidence_statement(row: I.InventoryRow) -> str:
    name = option_name(row.option).lower()
    if row.option == SL.MANUAL:
        return ("Measured on the manually treated plots: 220 mg/kg (July-August 2011) and 101 mg/kg (September 2012), against 260 "
                "and 112 mg/kg on the untreated plots (table above). Two dates identify no treatment-specific tPAH effect, and "
                "these differences are not used to fill the reduction. Any reduction you enter is your own assumption.")
    if row.availability == "evidence_gap":
        return f"There is no measured Bay Jimmy soil tPAH effect for {name}. Any reduction you enter is your own assumption."
    return (f"No measured soil tPAH effect exists for {name}. Any reduction you enter is your own assumption.")


def _tpah_controls(inventory, choice) -> PH.PahEffect | None:
    st.markdown("**Treatment what-if (user-defined)**")
    if inventory is None or choice in (None, I.REFERENCE):
        st.caption("Choose a technique at the top of this panel to add a user-defined treatment curve.")
        return None
    row = inventory.cell(choice, PH.ENDPOINT)
    if not row.what_if_allowed:
        st.info(f"No what-if for {option_name(choice).lower()}. {row.what_if_reason}", icon=":material/block:")
        return None
    st.caption(tpah_evidence_statement(row))
    if row.unresolved_conditions:
        st.caption("Condition not established for this site, carried with this technique: "
                   + "; ".join(row.unresolved_conditions) + ".")
    for key, value in WHATIF_DEFAULTS.items():
        st.session_state.setdefault(key, value)
    left, right = st.columns(2)
    date = left.date_input("Intervention date", min_value=dt.date(2012, 10, 1), max_value=dt.date(2100, 12, 31),
                           key="bj_pah_date")
    reduction = right.number_input("One-time reduction in soil tPAH (%)", value=None, step=5.0, format="%.1f",
                                   key="bj_pah_reduction", placeholder="Blank: no treatment curve",
                                   help="Percent of the measured 0-10 cm soil tPAH concentration removed on the intervention "
                                        "date. 0 = no change; 100 = all of it.")
    basis = st.text_input("Basis for the reduction", key="bj_pah_basis",
                          help="Where the percentage comes from. Keep 'user-defined sensitivity assumption' when no field "
                               "estimate exists.")
    st.caption(f"Accepts 0–100%. {PH.SOIL_NOTE} The reduction is applied to the concentration on the intervention date; both "
               "curves then follow the same natural-recovery rule. Changing the technique clears these entries.")
    if date is None:
        st.info("Choose the intervention date to apply the assumed reduction.")
        return None
    return PH.PahEffect(choice, date, reduction, basis or "")


def _tpah_explorer(inventory=None, choice=None, context=None) -> None:
    st.markdown("**Conditional future soil tPAH: untreated plots**")
    observations, manual = _tpah_record("untreated_heavy"), _tpah_record("manual_removal_heavy")
    anchor = PH.anchor_from(observations)
    if anchor is None:
        st.info(PH.no_anchor_reason(PH.AS_OF), icon=":material/info:")
        return
    st.markdown(f"Last untreated, heavily oiled measurement: **{anchor.survey_period}** (date precision: "
                f"{anchor.date_precision}) · **{anchor.value:.1f} mg/kg** · **{anchor.n_plots} plots** · {anchor.depth}.")
    st.caption(f"Analyte: {anchor.analyte}. The curves start at the end of the survey month ({anchor.starts:%d %b %Y}).")
    st.table(tpah_evidence_table(observations, manual))
    st.caption("Field measurements for reference (Zengel et al. 2015, S1 Table). The regional DIVER PAH index uses different "
               "sampling (mostly 0–2 cm sediment grabs, 58 compounds) and stays on its own scale in the manual-removal "
               "comparison above; it is not used here.")
    choice_key = st.segmented_control("Natural-recovery scenario", list(PAH_BASELINES), format_func=PAH_BASELINES.__getitem__,
                                      default=PH.HOLD, required=True, key="bj_pah_baseline")
    half_life = None
    if choice_key == PH.HALF_LIFE:
        half_life = st.number_input("Assumed decline half-life (years)", value=None, step=0.5, format="%.2f",
                                    key="bj_pah_half_life", placeholder="Enter a positive number of years",
                                    help="C(t) = C0 × 2^(−t/h), with t in years since the last measurement.")
        st.caption(f"C(t) = C₀ × 2^(−t/h). {PH.BACKGROUND_NOTE} The half-life is your assumption: two measurement dates "
                   "identify no decline rate for these plots.")
        if half_life is None:
            st.info("Enter a positive half-life in years to draw the scenario, or hold the concentration.",
                    icon=":material/info:")
            return
        bad = PH.baseline_problem(half_life)
        if bad:
            st.warning(bad, icon=":material/warning:")
            return
    end = st.date_input("Scenario end date", dt.date(2030, 1, 1), min_value=dt.date(2013, 1, 1), max_value=dt.date(2100, 12, 31),
                        key="bj_pah_end")
    if end is None:
        st.info("Choose an end date to draw the scenario.")
        return
    effect = _tpah_controls(inventory, choice)
    row = inventory.cell(choice, PH.ENDPOINT) if inventory is not None and choice not in (None, I.REFERENCE) else None
    sp = SimpleNamespace(end=end, cadence="annual", technique=choice or "", as_of=PH.AS_OF)
    computed = PH.compute(sp, observations, half_life, effect, row)        # the same calculation the CLI replays
    what, rows, label = computed.what, computed.rows, computed.label
    if effect is not None and effect.reduction_percent is not None and not what.has_treatment:
        st.warning(what.message, icon=":material/warning:")
    st.markdown((f"**{PH.WHATIF_LABEL}, {label.lower()}.** " if what.has_treatment else "") + PH.summary_text(what, end))
    st.altair_chart(tpah_chart(rows, anchor, what, label, end), width="stretch",
                    alt="Measured soil tPAH of the untreated Bay Jimmy plots in 2011 and 2012 and conditional future "
                        "concentrations" + (", with a user-defined one-time reduction." if what.has_treatment else "."))
    st.caption("Points are group means of the untreated plots with 90% intervals, drawn at the end of the survey month. Both "
               f"lines are conditional scenarios, not forecasts. {PH.baseline_label(half_life)}.")
    if what.has_treatment:
        st.caption("At the intervention the dotted teal line drops on one date (before and after are both plotted); it then "
                   "follows the same rule as natural recovery. It is a user-defined what-if, not a measured treatment effect, "
                   "and it does not change any recommendation.")
    left, right = st.columns(2)
    if context is not None:
        technique = choice if choice not in (None, I.REFERENCE) else I.REFERENCE
        payload = tpah_payload(computed, technique, context, half_life, effect if what.has_treatment else None, end, inventory)
        left.download_button("Download tPAH JSON", json.dumps(payload, indent=2, allow_nan=False),
                             file_name="bay_jimmy_tpah_whatif.json", mime="application/json", on_click="ignore",
                             icon=":material/download:", width="stretch",
                             help="A replayable scenario (spec version 2): python -m src.shoreline_remediation.projections "
                                  "run --scenario <this file> --output <new folder>")
    right.download_button("Download tPAH CSV", W.csv_text(rows), file_name="bay_jimmy_tpah_whatif.csv", mime="text/csv",
                          on_click="ignore", icon=":material/download:", width="stretch")
    figure_section(W.csv_text(rows), "tpah", **FG.whatif_labels("tpah", computed, label))


def tpah_payload(computed: PH.Computed, technique: str, context: dict, half_life, effect, end: dt.date, inventory) -> dict:
    """The tPAH download: a version-2 scenario the projections CLI replays (inputs) plus what this page showed (outputs)."""
    payload = PH.spec_dict(PH.AS_OF, end, "annual", technique, context, half_life, effect)
    w, last = computed.what, computed.what.frame.iloc[-1]
    a = w.anchor
    row = inventory.cell(technique, PH.ENDPOINT) if inventory is not None else None
    at = None
    if computed.applied:
        before = w.row(w.effect.date, "intervention_before")
        after = w.frame[w.frame.date == w.effect.date.isoformat()].iloc[-1]
        at = {"date": w.effect.date.isoformat(), "before_mgkg": float(before.treatment_mgkg),
              "after_mgkg": float(after.treatment_mgkg)}
    payload["exported_outputs"] = {
        "note": "Outputs shown in the dashboard when this file was saved. Never used as inputs on replay.",
        "label": PH.WHATIF_LABEL, "baseline": PH.baseline_label(half_life),
        "anchor": {"survey_period": a.survey_period, "date_precision": a.date_precision, "tpah_mgkg": a.value,
                   "n_plots": a.n_plots, "sampling_depth": a.depth, "analyte": a.analyte},
        "eligibility_at_export": getattr(row, "what_if_reason", None),
        "summary": {"end_date": end.isoformat(), "natural_mgkg": float(last.natural_mgkg),
                    "treatment_mgkg": float(last.treatment_mgkg) if computed.applied else None,
                    "difference_mgkg": float(last.difference_mgkg) if computed.applied else None,
                    "at_intervention": at, "text": PH.summary_text(w, end)},
        "csv_float_format": W.CSV_FLOAT_FORMAT,
        "rows": computed.rows.astype(object).where(computed.rows.notna(), None).to_dict("records"),
    }
    return payload


def tpah_chart(rows: pd.DataFrame, anchor: PH.Anchor, what: PH.PahWhatIf, option_label: str, end: dt.date) -> alt.LayerChart:
    """Built from the same rows as the CSV download: measured means with 90% interval bars, the last measurement, the natural-
    recovery scenario (pale dashed) and the what-if (teal dotted). Lines follow the export order, so the treated arm drops
    vertically at the intervention, with labelled before and after points."""
    treat = f"{PH.WHATIF_LABEL}: {option_label}" if what.has_treatment else None
    natural = PH.baseline_label(what.half_life)
    domain = ["Observed (untreated plots)", natural] + ([treat] if treat else [])
    colour = alt.Color("series:N", scale=alt.Scale(domain=domain, range=[REF_COLOUR, REF_COLOUR, TREAT_COLOUR][:len(domain)]),
                       legend=None)
    dash = alt.StrokeDash("series:N", scale=alt.Scale(domain=domain[1:], range=[[6, 4], [2, 3]][:len(domain) - 1]), legend=None)
    x = alt.X("plot_date:T", title="Year", axis=alt.Axis(format="%Y"))
    y = alt.Y("soil_tpah:Q", title="Soil tPAH, 0–10 cm (mg/kg)", scale=alt.Scale(domainMin=0))
    tip = ["series:N", alt.Tooltip("date:N", title="Date"), alt.Tooltip("sample:N", title="Point"),
           alt.Tooltip("soil_tpah:Q", title="tPAH (mg/kg)", format=".1f"),
           alt.Tooltip("difference_from_natural:Q", title="Difference (mg/kg)", format="+.1f"),
           alt.Tooltip("status_label:N", title="Status")]
    base = alt.Chart(rows)
    observed = base.transform_filter("datum.arm == 'observed'")
    bars = observed.mark_rule(strokeWidth=2, color=REF_COLOUR).encode(x=x, y="interval_lo:Q", y2="interval_hi:Q")
    points = observed.mark_point(filled=True, size=60, opacity=1).encode(
        x=x, y=y, color=colour, tooltip=tip + [alt.Tooltip("survey_period:N", title="Survey"),
                                               alt.Tooltip("n_plots:Q", title="Plots (n)"),
                                               alt.Tooltip("interval_method:N", title="Interval")])
    lines = base.transform_filter("datum.arm != 'observed'").mark_line(strokeWidth=2.5).encode(
        x=x, y=y, color=colour, strokeDash=dash, order="order:Q", tooltip=tip)
    labels = []
    ends = rows[rows.arm != "observed"].groupby("arm").tail(1)
    offsets = {PH.NATURAL_ARM: -10, PH.TREATMENT_ARM: 14}
    for arm, tag in ((PH.NATURAL_ARM, "Natural recovery"), (PH.TREATMENT_ARM, "What-if")):
        one = ends[ends.arm == arm].assign(tag=tag)
        if not one.empty:
            labels.append(alt.Chart(one).mark_text(align="right", dx=-2, dy=offsets[arm], fontSize=12, fontWeight="bold",
                                                   color=REF_COLOUR if arm == PH.NATURAL_ARM else TREAT_COLOUR).encode(
                x=x, y=y, text="tag:N"))
    last = pd.DataFrame({"plot_date": [anchor.starts.isoformat()], "label": [f"Last measurement ({anchor.survey_period})"]})
    layers = [alt.Chart(last).mark_rule(color="#A6B2C2", strokeDash=[2, 2]).encode(x="plot_date:T", tooltip=["label:N"]),
              alt.Chart(last).mark_text(align="left", baseline="top", dx=4, dy=4, fontSize=11, color="#A6B2C2").encode(
                  x="plot_date:T", y=alt.value(0), text=alt.value("Last measurement"))]
    if what.has_treatment:
        e = what.effect
        mark = pd.DataFrame({"plot_date": [e.date.isoformat()], "label": [f"Assumed intervention: {e.reduction_percent:g}% "
                                                                          "one-time reduction"]})
        layers.append(alt.Chart(mark).mark_rule(color=TREAT_COLOUR, strokeDash=[4, 3], opacity=0.7).encode(
            x="plot_date:T", tooltip=["label:N"]))
        layers.append(alt.Chart(mark).mark_text(align="left", baseline="top", dx=4, dy=4, fontSize=11, color=TREAT_COLOUR).encode(
            x="plot_date:T", y=alt.value(0), text=alt.value("Intervention")))
        step = rows[(rows.arm == PH.TREATMENT_ARM) & rows["sample"].isin(["intervention_before", "intervention_after"])].assign(
            tag=lambda d: d["sample"].map({"intervention_before": "before", "intervention_after": "after"})
            + " " + d.soil_tpah.map(lambda v: f"{v:.1f}"))
        labels.append(alt.Chart(step).mark_point(filled=True, size=55, shape="diamond", color=TREAT_COLOUR).encode(
            x=x, y=y, tooltip=tip))
        # The values are written beside the step (before above, after below) so the drop stays legible at any y scale.
        for sample, dy in (("intervention_before", -10), ("intervention_after", 12)):
            labels.append(alt.Chart(step[step["sample"] == sample]).mark_text(
                align="left", dx=7, dy=dy, fontSize=11, color=TREAT_COLOUR).encode(x=x, y=y, text="tag:N"))
        title = f"{PH.WHATIF_LABEL}: {option_label.lower()}"
    else:
        title = "Conditional scenario, not a forecast"
    return alt.layer(*layers, bars, lines, points, *labels).properties(
        height=CHART_HEIGHT, title=alt.TitleParams(title, anchor="start", color="#F4F7FA", fontSize=13))


# ---------------------------------------------------------------------------------------------------------------
# Difference plot and PNG/SVG export (R8). Both read the CSV text the CSV button downloads.

@st.cache_data(show_spinner=False, max_entries=24)
def _figure_bytes(csv_text: str, outcome: str, technique: str, baseline: str, last_observation: str) -> dict:
    return FG.whatif_figure(csv_text, outcome, technique=technique, baseline=baseline, last_observation=last_observation)


def difference_chart(csv_text: str, outcome: str) -> alt.LayerChart | None:
    """Treatment minus natural recovery from the CSV rows, with a zero line; None when no treatment arm was exported."""
    d = FG.difference_rows(csv_text, outcome)
    if d.empty:
        return None
    m = FG.WHATIF_OUTCOMES[outcome]
    d = d.assign(seq=range(len(d)), when=d.x.str.slice(0, 10))
    x = alt.X("when:T", title="Year", axis=alt.Axis(format="%Y"))
    zero = alt.Chart(pd.DataFrame({"y": [0.0]})).mark_rule(color="#A6B2C2").encode(y="y:Q")
    line = alt.Chart(d).mark_line(color=TREAT_COLOUR, strokeWidth=2.5).encode(
        x=x, y=alt.Y("difference:Q", title=f"Difference ({m['unit']})"), order="seq:Q",
        tooltip=[alt.Tooltip("x:N", title="Date"), alt.Tooltip("difference:Q", title=f"Difference ({m['unit']})", format="+.2f")])
    return (zero + line).properties(height=200, title=alt.TitleParams("Treatment minus natural recovery", anchor="start",
                                                                      color="#F4F7FA", fontSize=12))


def figure_section(csv_text: str, outcome: str, technique: str, baseline: str, last_observation: str) -> None:
    chart = difference_chart(csv_text, outcome)
    if chart is not None:
        st.altair_chart(chart, width="stretch", alt="Difference between the user-defined what-if and natural recovery over time, "
                                                   f"in {FG.WHATIF_OUTCOMES[outcome]['unit']}, with a zero line.")
        st.caption(FG.WHATIF_OUTCOMES[outcome]["sign"] + " A flat line at zero means the two arms coincide.")
    images = _figure_bytes(csv_text, outcome, technique, baseline, last_observation)
    left, right = st.columns(2)
    left.download_button("Download PNG", images["png"], file_name=f"bay_jimmy_{outcome}_whatif.png", mime="image/png",
                         on_click="ignore", icon=":material/image:", width="stretch", key=f"bj_{outcome}_png")
    right.download_button("Download SVG", images["svg"], file_name=f"bay_jimmy_{outcome}_whatif.svg", mime="image/svg+xml",
                          on_click="ignore", icon=":material/image:", width="stretch", key=f"bj_{outcome}_svg")
