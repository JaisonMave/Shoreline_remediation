"""Bay Jimmy Assessment panel for conditional retreat of the historical field plots."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import altair as alt
import streamlit as st

from src.shoreline_remediation.projections import projection, runner, spec

EXAMPLE = Path(__file__).resolve().parents[2] / "examples/projections/bay_jimmy_retreat_2030.json"


@st.cache_data(show_spinner=False)
def _plot_record():
    return runner.observed_record(spec.load(EXAMPLE))


def _assumption(name, value, unit):
    return dict(assumption_id=name, value=value, unit=unit, origin="user_assumption",
                source="Bay Jimmy Assessment scenario controls")


def render() -> None:
    panel = st.expander("Explore future scenarios", key="bj_future_panel", icon=":material/show_chart:",
                        on_change="rerun")
    if not panel.open:
        return
    with panel:
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
        except (OSError, ValueError, RuntimeError) as exc:
            st.error(f"Could not build this retreat scenario. {exc}")
            return

        last = series.iloc[-1]
        st.markdown(f"**{last.additional_retreat_since_anchor_m:.2f} m additional retreat** by {end:%d %b %Y} "
                    f"under these assumptions ({last.cumulative_retreat_since_origin_m:.2f} m since December 2010).")
        x = alt.X("date:T", title="Year", axis=alt.Axis(format="%Y"))
        y = alt.Y("value:Q", title="Cumulative retreat (m)")
        observed = alt.Chart(observations).mark_point(filled=True, color="#28B8A5", size=55).encode(
            x=x, y=y, tooltip=["date:T", alt.Tooltip("value:Q", title="Observed (m)", format=".2f")])
        future = alt.Chart(series.rename(columns={"cumulative_retreat_since_origin_m": "value"})).mark_line(
            strokeDash=[6, 4], color="#4E9BE8").encode(
                x=x, y=y, tooltip=["date:T", alt.Tooltip("value:Q", title="Scenario (m)", format=".2f")])
        st.altair_chart((future + observed).properties(height=270), width="stretch",
                        alt="Observed Bay Jimmy retreat through October 2016 and conditional retreat at the selected rates.")
        st.caption("Dots show measured group means (Zengel et al., 2022). The dashed line starts at the final "
                   "survey on 5 October 2016. Future storms, changes in marsh geometry and treatment effects "
                   "are outside this calculation.")
        st.download_button("Download scenario inputs", scenario.to_json(), file_name="bay_jimmy_scenario.json",
                           mime="application/json", on_click="ignore")
        st.download_button("Download projection CSV", series.to_csv(index=False), file_name="bay_jimmy_retreat.csv",
                           mime="text/csv", on_click="ignore")
