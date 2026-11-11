"""Event study of the 2010 Deepwater Horizon oiling on Louisiana CRMS marsh vegetation.

Specification (fixed on 2026-11-11 before the model was run; run once):
  Sites      data/external/scat_dwh/crms_scat_match.csv (scripts/match_crms_scat.py).
             exposed = 'oiled' (SCAT zone with max oiling Light or worse within 1,000 m)
             comparison = 'unoiled' (SCAT-surveyed shoreline within 1,000 m, no oil within 5,000 m)
             All other sites are left out. Distance thresholds are ASSUMED.
  Timing     first_post = 2010 if the site's 2010 survey was on or after oil arrival, else 2011.
             Oil arrival = first SCAT survey recording oil within 1,000 m (oiled sites);
             2010-06-15 for comparison sites (ASSUMED; median arrival at oiled sites was mid-June).
  Model      event_study(..., group="marsh_type_base", leads=3, lags=4): site effects, year effects per
             marsh type, so oiled sites are only compared with unoiled sites of the same marsh type.
             Gustav/Ike (2008) fall in the pre-period; Isaac (2012) at about event time 2 hits both groups.
  Outcomes   cover_total (primary, field survey), ndvi_gs_mean (secondary, MODIS 250 m).
  Baseline   zero effect: b[k] is measured against the unoiled sites, with the last pre-oil survey as k = -1.

Caveat known before running: CRMS plots are mostly hundreds of metres from the marsh edge, while
Deepwater Horizon oil sat in a band of roughly the first 10-20 m. A null here does not mean oil had no
effect at the edge; it means these monitoring stations could not detect one.

Run:  python -m validation.oil_event_study      Writes results/oil_event_study/{effects,summary}.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.shoreline_remediation.event_study import event_study  # noqa: E402

MATCH = ROOT / "data" / "external" / "scat_dwh" / "crms_scat_match.csv"
PANEL = ROOT / "data" / "external" / "crms" / "crms_marsh_site_year.csv"
RESULTS = ROOT / "results" / "oil_event_study"
CONTROL_ARRIVAL = pd.Timestamp("2010-06-15")  # ASSUMED
OUTCOMES = {"cover_total": "primary", "ndvi_gs_mean": "secondary"}


def build_panel() -> pd.DataFrame:
    match = pd.read_csv(MATCH)
    match = match[match["group"].isin(["oiled", "unoiled"])].copy()
    match["exposed"] = match["group"] == "oiled"
    match["arrival"] = pd.to_datetime(match["first_oil_date"]).where(match["exposed"], CONTROL_ARRIVAL)
    panel = pd.read_csv(PANEL).merge(match[["site", "exposed", "arrival", "d_surveyed_m"]], on="site")
    s2010 = panel[panel["year"] == 2010].set_index("site")["survey_date"].pipe(pd.to_datetime)
    arrival = match.set_index("site")["arrival"]
    after = (s2010 >= arrival.reindex(s2010.index))
    panel["first_post"] = panel["site"].map(lambda s: 2010 if bool(after.get(s, False)) else 2011)
    return panel


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    panel = build_panel()
    tables, rows = [], []
    for outcome, role in OUTCOMES.items():
        r = event_study(panel, outcome, "exposed", "first_post", group="marsh_type_base", leads=3, lags=4)
        tables.append(r.effects.assign(outcome=outcome, role=role))
        post = r.effects[r.effects["event_time"] >= 0]
        peak = post.loc[post["estimate"].abs().idxmax()]
        rows.append({"outcome": outcome, "role": role, "oiled_sites": r.n_exposed_sites,
                     "unoiled_sites": r.n_control_sites, "observations": r.n_observations,
                     "pretrend_p_value": round(r.pretrend_p_value, 3),
                     "pretrend_check": "passed" if r.pretrend_p_value >= 0.10 else "FAILED",
                     "largest_effect": round(float(peak["estimate"]), 3), "at_event_time": int(peak["event_time"]),
                     "largest_effect_90ci": f"{peak['ci_low']:.3f} to {peak['ci_high']:.3f}",
                     "recovery_lag_surveys": r.recovery_lag()})
    effects = pd.concat(tables, ignore_index=True).round(4)
    summary = pd.DataFrame(rows)
    effects.to_csv(RESULTS / "effects.csv", index=False)
    summary.to_csv(RESULTS / "summary.csv", index=False)
    pd.set_option("display.width", 220)
    print(summary.to_string(index=False))
    print()
    print(effects.pivot_table(index="event_time", columns="outcome", values=["estimate", "ci_low", "ci_high"]).round(3).to_string())
    first = panel.drop_duplicates("site").groupby("exposed")["first_post"].value_counts().unstack(fill_value=0)
    print("\nfirst post-oil survey year by group:\n", first.to_string())


if __name__ == "__main__":
    main()
