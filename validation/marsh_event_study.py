"""Real-data run of the event study: hurricane effects on Louisiana marsh vegetation (CRMS, 2006-2025).

Purpose:
  1. Exercise event_study.py on real field and satellite data with real event dates.
  2. Measure how strongly, and for how long, a hurricane changes marsh cover and NDVI. Hurricane Isaac
     (August 2012) struck the marshes oiled in 2010, so its effect is the main confounder for any estimate
     of Deepwater Horizon recovery.

Comparison: sites inside the storm's 64-knot wind radius against the least exposed sites in the same
season (inside only the 34-knot radius for Isaac; outside it for Ida), within the same marsh type.
Sites in the middle exposure classes are left out.

This says nothing about oil. The data hold no oiling information.

Run:  python -m validation.marsh_event_study
Writes results/marsh_events/{effects,summary}.csv and effects.png
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.shoreline_remediation.event_study import event_study  # noqa: E402

DATA_DIR = ROOT / "data" / "external" / "crms"
RESULTS_DIR = ROOT / "results" / "marsh_events"
EVENTS = {  # season: (label, exposed class, comparison class, lags available before the record ends or the next storm season)
    2012: ("Isaac 2012", "kt64", "kt34", 5),
    2021: ("Ida 2021", "kt64", "lt34", 3),
}
OUTCOMES = {"cover_total": "Vegetation cover (points)", "ndvi_gs_mean": "Growing-season NDVI"}


def build_panel(season: int, exposed_class: str, control_class: str) -> pd.DataFrame:
    sites = pd.read_csv(DATA_DIR / "crms_marsh_site_year.csv")
    events = pd.read_csv(DATA_DIR / "hurricane_site_events.csv")
    events = events[(events["event"] == season) & events["exposure"].isin([exposed_class, control_class])].copy()
    events["first_post"] = pd.to_datetime(events["post_date"]).dt.year
    events["exposed"] = events["exposure"] == exposed_class
    return sites.merge(events[["site", "first_post", "exposed"]], on="site")


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    effect_tables, summaries = [], []
    for season, (label, exposed_class, control_class, lags) in EVENTS.items():
        panel = build_panel(season, exposed_class, control_class)
        for outcome, outcome_label in OUTCOMES.items():
            result = event_study(panel, outcome, "exposed", "first_post", group="marsh_type_base", leads=3, lags=lags)
            table = result.effects.assign(event=label, outcome=outcome)
            effect_tables.append(table)
            post = table[table["event_time"] >= 0]
            peak = post.loc[post["estimate"].abs().idxmax()]
            summaries.append({
                "event": label, "outcome": outcome, "exposed_sites": result.n_exposed_sites,
                "comparison_sites": result.n_control_sites, "observations": result.n_observations,
                "pretrend_p_value": round(result.pretrend_p_value, 3),
                "largest_effect": round(float(peak["estimate"]), 3), "largest_effect_at": int(peak["event_time"]),
                "largest_effect_ci": f"{peak['ci_low']:.3f} to {peak['ci_high']:.3f}",
                "recovery_lag_surveys": result.recovery_lag(),
            })
    effects = pd.concat(effect_tables, ignore_index=True).round(4)
    summary = pd.DataFrame(summaries)
    effects.to_csv(RESULTS_DIR / "effects.csv", index=False)
    summary.to_csv(RESULTS_DIR / "summary.csv", index=False)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(len(OUTCOMES), len(EVENTS), figsize=(9, 6), sharex="col")
    for column, (label, *_rest) in enumerate(EVENTS.values()):
        for row, (outcome, outcome_label) in enumerate(OUTCOMES.items()):
            table = effects[(effects["event"] == label) & (effects["outcome"] == outcome)]
            axis = axes[row][column]
            axis.axhline(0, color="#999999", lw=0.8)
            axis.axvline(-0.5, color="#E45756", lw=0.8, ls=":")
            axis.errorbar(table["event_time"], table["estimate"],
                          yerr=[table["estimate"] - table["ci_low"], table["ci_high"] - table["estimate"]],
                          fmt="o-", color="#333333", lw=1, ms=4, capsize=2)
            axis.spines[["top", "right"]].set_visible(False)
            if row == 0:
                axis.set_title(f"{label}: 64 kt sites vs least exposed", fontsize=10, loc="left")
            if column == 0:
                axis.set_ylabel(outcome_label)
            if row == len(OUTCOMES) - 1:
                axis.set_xlabel("Surveys since the storm (0 = first survey after)")
    figure.tight_layout()
    figure.savefig(RESULTS_DIR / "effects.png", dpi=150)

    pd.set_option("display.width", 220)
    print(summary.to_string(index=False))
    print()
    print(effects.pivot_table(index="event_time", columns=["event", "outcome"], values="estimate").round(3).to_string())


if __name__ == "__main__":
    main()
