"""Model validation page (V5.2). Presentation only.

Authority: registry.governance_table() (through model_validation_data) for every model's state, scope, data, baseline, uncertainty and
gates; genuine result files for the charts. The page never promotes, demotes or recomputes a state or a metric. A value that cannot be
read is shown as unavailable. A validated model with a failed gate shows that gate; a failed gate is never dropped.

Entry point: render_models(). Widget keys are listed in STATE_KEYS so the dashboard can keep them when the page changes.
"""
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from . import model_validation_data as MV
from . import ui_components as C
from . import ui_theme as T

STATE_KEYS = ("mv_model",)

INTRO = ("What each model has actually demonstrated, taken from the model registry and from result files in this repository. "
         "This is not a performance showcase: failed promotion gates are shown as failed, and 'validated' always means validated within the "
         "stated scope only.")
SCOPE_NOTE = ("Numerical validation is narrow: heavily oiled northern Gulf salt-marsh edge loss (whole Louisiana basins held out) and "
              "Deepwater Horizon soil PAH-sum decline (whole stations held out), each from one spill. Everything else is experimental, "
              "screening-only or literature-only.")

_BASELINE_COLOUR = T.NEUTRAL
_MODEL_COLOUR = T.PALETTE["teal"]
_FAIL_COLOUR = "#E0A83A"


def _state_chip(state: str) -> str:
    return T.grade_html("validated" if state == "validated" else "experimental", "Validated (within scope)" if state == "validated" else "Experimental")


def _inventory_table() -> pd.DataFrame:
    rows = []
    for m in MV.sorted_inventory():
        rows.append({"Model": m["title"], "State (registry)": m["state"], "Habitat scope": m["habitat_scope"] or MV.UNAVAILABLE,
                     "Gates passed": f"{m['n_gates'] - m['n_gates_failed']} of {m['n_gates']}",
                     "Failed gates": ", ".join(g["gate_id"] for g in m["gates"] if not g.get("passed")) or "none"})
    return pd.DataFrame(rows)


def _gate_table(m: dict) -> pd.DataFrame:
    return pd.DataFrame([{"Gate": g["gate_id"], "Result": "passed" if g.get("passed") else "FAILED",
                          "Blocks promotion": "yes" if g.get("blocks_promotion") else "no",
                          "What it tests": g.get("description", MV.UNAVAILABLE), "Source": g.get("source", MV.UNAVAILABLE)} for g in m["gates"]])


def _model_detail(m: dict) -> None:
    with st.container(border=True):
        st.markdown(f"{_state_chip(m['state'])}", unsafe_allow_html=True)
        st.markdown(f"#### {m['title']}  \n`{m['model_id']}` version {m['model_version'] or MV.UNAVAILABLE}")
        if m["state"] != m["declared_state"]:
            st.warning(f"Declared as {m['declared_state']} but held at {m['state']} by the registry.")
        st.markdown(f"**Intended use.** {m['intended_use'] or MV.UNAVAILABLE}")
        a, b = st.columns(2)
        with a:
            st.markdown(f"**Habitat scope.** {m['habitat_scope'] or MV.UNAVAILABLE}")
            st.markdown(f"**Geographic scope.** {m['geographic_scope'] or MV.UNAVAILABLE}")
            st.markdown(f"**Training data.** {m['training_data'] or MV.UNAVAILABLE}")
        with b:
            st.markdown(f"**Validation data.** {m['validation_data'] or MV.UNAVAILABLE}")
            st.markdown(f"**Hold-out design.** {m['validation_design'] or MV.UNAVAILABLE}")
            st.markdown(f"**Baseline comparison.** {m['baseline'] or MV.UNAVAILABLE}")
        st.markdown(f"**Uncertainty method.** {m['uncertainty_method'] or MV.UNAVAILABLE}")
        st.markdown(f"**Interval status.** {m['interval_status'] or MV.UNAVAILABLE}")
        st.markdown(f"**Known limitations.** {m['limitations'] or MV.UNAVAILABLE}")
        failed = [g for g in m["gates"] if not g.get("passed")]
        if failed:
            st.error("**Failed gates** (shown for every model, including validated ones): "
                     + "; ".join(f"{g['gate_id']}{' (blocks promotion)' if g.get('blocks_promotion') else ' (does not block promotion)'}" for g in failed))
        if m["reasons_not_validated"]:
            with st.expander("Why this model is not validated"):
                for r in m["reasons_not_validated"]:
                    st.markdown(f"- {r}")
        if m["governance_gaps"]:
            st.warning("Governance fields missing in the registry: " + ", ".join(map(str, m["governance_gaps"])))
        if m["gates"]:
            st.markdown("**Promotion gates**")
            st.dataframe(_gate_table(m), hide_index=True, width="stretch")
        st.caption(f"Registry entry: models/registry.json; model card: {m['card'] or MV.UNAVAILABLE}. "
                   f"{'Wrapped by a registry adapter.' if m['has_adapter'] else 'Card only: no adapter, not wired into the decision engine.'}")


def _inventory_tab() -> None:
    counts = MV.state_counts()
    st.markdown(f"**{counts.get('validated', 0)}** validated within a narrow scope, **{counts.get('experimental', 0)}** experimental "
                f"(registry states; no other state exists).")
    st.info(SCOPE_NOTE)
    st.dataframe(_inventory_table(), hide_index=True, width="stretch")
    st.caption("Intended use, geographic scope, data, baseline and uncertainty for each model are in the detail view below.")
    models = MV.sorted_inventory()
    ids = [m["model_id"] for m in models]
    if st.session_state.get("mv_model") not in ids:
        st.session_state.pop("mv_model", None)
    title = {m["model_id"]: f"{m['title']} ({m['state']})" for m in models}
    pick = st.selectbox("Inspect a model", ids, format_func=title.get, key="mv_model", index=0)
    _model_detail(next(m for m in models if m["model_id"] == pick))


def _unavailable(res: dict, what: str) -> bool:
    if res.get("available"):
        return False
    st.warning(f"{what}: unavailable. {res.get('reason', '')} (expected in {res.get('source', 'the repository')}).")
    return True


def _bar(df: pd.DataFrame, x: str, y: str, colour: str, order: list, title: str, domain: list | None = None) -> alt.Chart:
    base = alt.Chart(df).encode(
        x=alt.X(f"{x}:N", sort=order, title=None, axis=alt.Axis(labelAngle=0, labelLimit=140)),
        y=alt.Y(f"{y}:Q", title=title),
        color=alt.Color(f"{colour}:N", legend=alt.Legend(orient="bottom", title=None, direction="vertical"), scale=alt.Scale(domain=domain) if domain else alt.Undefined),
        tooltip=list(df.columns))
    return base.mark_bar().properties(height=240)


def _edge_loss_block() -> None:
    res = MV.edge_loss_holdout()
    st.markdown("#### Marsh-edge loss: whole-basin hold-out")
    if _unavailable(res, "Edge-loss hold-out results"):
        return
    long = []
    for r in res["rows"]:
        for key, label in (("MAE_M0", "M0 baseline"), ("MAE_M1", "M1 exposure only"), ("MAE_M2", "M2 exposure + oiling")):
            long.append({"Basin": str(r["basin"]).capitalize(), "Model": label, "MAE": round(float(r[key]), 3)})
    df = pd.DataFrame(long)
    chart = _bar(df, "Basin", "MAE", "Model", ["Barataria", "Breton", "Pooled"], "Error, m/yr (MAE)",
                 ["M0 baseline", "M1 exposure only", "M2 exposure + oiling"]).encode(xOffset="Model:N")
    st.altair_chart(chart, theme="streamlit", width="stretch")
    pooled = next(r for r in res["rows"] if r["basin"] == "pooled")
    st.caption(f"Lower is better. Pooled over the two held-out basins ({int(pooled['cells'])} cells): baseline {float(pooled['MAE_M0']):.3f}, "
               f"exposure only {float(pooled['MAE_M1']):.3f}, exposure + oiling {float(pooled['MAE_M2']):.3f}; 90% interval coverage "
               f"{float(pooled['coverage_90']):.3f}. Barataria and Breton are the only basins held out; {', '.join(b.capitalize() for b in res['not_tested'])} "
               f"was used for training only (not tested). Models: " + "; ".join(f"{k} = {v}" for k, v in res["definitions"].items()) + ".")
    verdict = _verdict_line(res["verdict_file"])
    if verdict:
        st.caption(f"Recorded verdict ({res['verdict_file']}): {verdict}")
    per_basin = "; ".join(f"{str(r['basin']).capitalize()}: baseline {float(r['MAE_M0']):.3f}, exposure only {float(r['MAE_M1']):.3f}, "
                          f"exposure + oiling {float(r['MAE_M2']):.3f}, {int(r['heavy'])} heavily oiled cells" for r in res["rows"] if r["basin"] != "pooled")
    st.caption(f"By basin: {per_basin}. Source: {res['source']}. {res['scope']}")
    st.divider()
    _scatter_block()


def _scatter_block() -> None:
    """Leave-one-basin-out predicted vs observed edge loss (lobo_pred only). Descriptive; not a new validation."""
    res = MV.edge_loss_scatter()
    st.markdown("#### Marsh-edge loss: predicted against observed (leave-one-basin-out)")
    if _unavailable(res, "Predicted-versus-observed edge loss"):
        return
    lo, hi = res["axis_min"], res["axis_max"]
    dom = alt.Scale(domain=[lo, hi], nice=False)
    pts = alt.Chart(res["points"]).mark_circle(size=14, opacity=0.35).encode(
        x=alt.X("observed_rate:Q", title="Observed edge loss, m/yr", scale=dom),
        y=alt.Y("lobo_pred:Q", title="Leave-one-basin-out prediction, m/yr", scale=dom),
        color=alt.Color("basin:N", title="Basin", legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["basin", alt.Tooltip("observed_rate:Q", format=".2f"), alt.Tooltip("lobo_pred:Q", format=".2f")])
    line = alt.Chart(pd.DataFrame({"v": [lo, hi]})).mark_line(strokeDash=[5, 4], color=T.NEUTRAL).encode(x="v:Q", y="v:Q")
    st.altair_chart((pts + line).properties(height=320), theme="streamlit", width="stretch")
    per = "; ".join(f"{r['basin'].capitalize()}: n={r['n']}, MAE {r['MAE']:.3f}" for r in res["per_basin"])
    pct = (f"Mean absolute percentage error {res['MAPE_pct']:.0f}% over the {res['n_nonzero_observed']} cells whose observed rate is not zero "
           f"(percentage error is undefined where the observation is 0)." if res["MAPE_pct"] is not None else "")
    st.caption(f"Dashed line: 1:1 (perfect agreement). n = {res['n']} cells with both a prediction and an observation; mean absolute error "
               f"{res['MAE']:.3f} m/yr on all {res['n']} cells. {per}. {pct} The plot shows a fixed random subset of {res['n_plotted']} points "
               f"for speed; the numbers use all rows. This all-cell error is not comparable with the P2 table above (different cell set, "
               f"Terrebonne included). Source: {res['source']}.")
    st.caption(res["caption"])


def _verdict_line(rel: str) -> str:
    try:
        return (MV.ROOT / rel).read_text(encoding="utf-8").strip().splitlines()[0]
    except (OSError, IndexError):
        return ""


def _pah_block() -> None:
    res = MV.pah_holdout()
    st.markdown("#### Soil PAH-sum decline: whole-station hold-out")
    if _unavailable(res, "PAH hold-out results"):
        return
    a, b, c = st.columns(3)
    a.metric("Baseline error (M0, no change)", f"{res['MAE_M0']:.3f}", border=True)
    b.metric("Model error (M1)", f"{res['MAE_M1']:.3f}", border=True)
    c.metric("Model minus baseline", f"{res['diff']:+.3f}", delta=f"90% interval {res['diff_lo90']:+.3f} to {res['diff_hi90']:+.3f}",
             delta_color="off", delta_arrow="off", border=True)
    st.caption(f"Error is the mean absolute error in {res['unit'].split('(')[0].strip()}; lower is better. {res['heldout_stations']} held-out stations. "
               f"The 90% prediction interval covered {res['pi90_coverage']:.2f} of held-out cells (reported in the plan's validation, one spill). "
               f"Source: {res['source']}. {res['scope']}")


def _f5_block() -> None:
    res = MV.f5_comparison()
    st.markdown("#### F5 process model: promotion gate failed")
    if _unavailable(res, "F5 comparison"):
        return
    df = pd.DataFrame([{"Model": "Prior (uncalibrated)", "MAE": res["prior"]}, {"Model": "Empirical decline curve", "MAE": res["empirical"]},
                       {"Model": "Calibrated process model", "MAE": res["calibrated"]}])
    bars = alt.Chart(df).mark_bar().encode(
        y=alt.Y("Model:N", sort=None, title=None, axis=alt.Axis(labelLimit=220)),
        x=alt.X("MAE:Q", title="Held-out error (MAE, lower is better)", scale=alt.Scale(domain=[0, 1])),
        color=alt.Color("Model:N", legend=None, scale=alt.Scale(domain=list(df.Model), range=[_BASELINE_COLOUR, _MODEL_COLOUR, _FAIL_COLOUR])),
        tooltip=["Model", "MAE"])
    labels = alt.Chart(df).mark_text(align="left", dx=4, color="#F4F7FA").encode(y=alt.Y("Model:N", sort=None), x="MAE:Q",
                                                                                  text=alt.Text("MAE:Q", format=".3f"))
    chart = (bars + labels).properties(height=150)
    st.altair_chart(chart, theme="streamlit", width="stretch")
    st.error(f"Held-out error {res['calibrated']:.3f} for the calibrated process model against {res['empirical']:.3f} for the empirical comparison: "
             f"it does not beat the empirical curve, so the gate failed. The process model is illustrative and does not enter the decision path.")
    st.caption(f"{res['stations']} held-out stations, {res['cells']} cells; {res['unit']}. The axis starts at zero, so the differences are small; read the labels. "
               f"Source: {res['source']}.")


def _bias_block() -> None:
    res = MV.bias_gates()
    st.markdown("#### Scenario composer: heavy-cell bias gate failed")
    if _unavailable(res, "Bias gates"):
        return
    by = {r["gate_id"]: r for r in res["rows"]}
    stages = (("R3-heavy-bias", "Before literature scaling (R3)"), ("D32-heavy-bias", "After D32 literature scaling"))
    if any(g not in by for g, _ in stages):
        st.warning("Bias gates: unavailable. The registry does not hold both the R3 and D32 heavy-bias gates.")
        return
    df = pd.DataFrame([{"Stage": label, "Pooled heavy-cell bias": by[g]["observed"], "Limit": by[g]["limit"],
                        "Result": "FAILED" if not by[g]["passed"] else "passed"} for g, label in stages])
    limit = float(df.Limit.iloc[0])
    bars = alt.Chart(df).mark_bar(color=_FAIL_COLOUR).encode(x=alt.X("Stage:N", sort=None, title=None, axis=alt.Axis(labelAngle=0, labelLimit=200)),
                                                              y=alt.Y("Pooled heavy-cell bias:Q", title="Bias, m per year"),
                                                              tooltip=list(df.columns)).properties(height=220)
    rule = alt.Chart(pd.DataFrame({"y": [limit]})).mark_rule(strokeDash=[5, 4], color=T.NEUTRAL).encode(y="y:Q")
    st.altair_chart(bars + rule, theme="streamlit", width="stretch")
    before, after = float(df["Pooled heavy-cell bias"].iloc[0]), float(df["Pooled heavy-cell bias"].iloc[1])
    verb = "reduced" if after < before else "did not reduce"
    outcome = "failed" if (df.Result == "FAILED").any() else "passed"
    st.error(f"D32 scaling {verb} the heavy-cell bias from {before:+.3f} to {after:+.3f} m/yr; the pre-specified gate is within +/-{limit:.2f} m/yr and "
             f"the D32 gate {outcome}" + (", so the composer stays experimental." if outcome == "failed" else "."))
    st.caption(f"The dashed line marks the +{limit:.2f} limit. Values and gate wording are the registry's gate records ({res['source']}); each gate cites its "
               f"findings section and summary file in the gate table of the model detail.")


def _results_tab() -> None:
    st.markdown("Charts below use result files that exist in this repository. Where a file cannot be read the block says unavailable instead "
                "of showing a substitute.")
    _edge_loss_block()
    st.divider()
    _pah_block()
    st.divider()
    _f5_block()
    st.divider()
    _bias_block()


def _uncertainty_tab() -> None:
    st.warning(MV.HEURISTIC_CONFIDENCE_NOTE)
    st.markdown("The uncertainty method and interval status recorded in the registry for each model are listed here. "
                "An interval whose status says 'not validated' must not be read as a coverage guarantee.")
    rows = [{"Model": m["title"], "Uncertainty method": m["uncertainty_method"] or MV.UNAVAILABLE,
             "Interval status": m["interval_status"] or MV.UNAVAILABLE, "Scope": m["habitat_scope"] or MV.UNAVAILABLE}
            for m in MV.sorted_inventory()]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.markdown("**Appropriate use.** A validated model may be used as a reference number inside its stated scope. An experimental model "
                "is shown with its Experimental label and does not by itself support a recommendation. Nothing on this page validates a "
                "model for another habitat, coast or spill, and no expert review has been carried out.")


def render_models() -> None:
    C.section_header("Model validation", kicker="What has been demonstrated", anchor="models", description=INTRO,
                     meta="Sources: model registry, results files")
    try:
        MV.inventory()
    except Exception as exc:   # noqa: BLE001 - report an unreadable registry instead of an empty page
        st.error(f"The model registry could not be read ({type(exc).__name__}: {exc}). No validation information is shown.")
        return
    t1, t2, t3 = st.tabs(["Model inventory", "Held-out results", "Uncertainty and appropriate use"])
    with t1:
        _inventory_tab()
    with t2:
        _results_tab()
    with t3:
        _uncertainty_tab()
