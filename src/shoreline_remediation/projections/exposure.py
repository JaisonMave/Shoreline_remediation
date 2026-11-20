"""What the SCAT surveys can verify for a release-and-exposure hindcast (Session 5). No transport engine is used.

Per shoreline segment and the request window (as_of = scenario start, end_date), the visit table supports six survey classes:

- oiled_before_window   oil was already observed on or before the scenario start (`prior_oiled_observation`). Contact happened
                        before the window, so no first-arrival window is set; in-window visits are still counted and reported.
- clear_then_oiled      oil first observed at `window_end` (in the window); the last clear visit before it in the whole record
                        (`window_start`, which may precede as_of) recorded no oil. Arrival lies in (window_start, window_end] IF the
                        clear visit did not miss oil.
- oiled_at_first_visit  no oil observed before the scenario start and no clear visit anywhere before the first oiled visit; arrival
                        lies in (release start, window_end], so the window starts at the case's release start, not at as_of.
- no_oil_observed       at least one clear visit and no oiled visit in the window. A survey result, not 'no_contact': oil may have
                        arrived and gone between visits, or been missed.
- inconclusive_partial_clear  the window has visits but none is clear or oiled (partial_clear only: NOO zones cover less than half
                        the segment). Counted in n_visits; excluded from clear-segment and false-alarm counts.
- not_visited_in_window the segment is in the SCAT layer but had no visit in the window. Shoreline that SCAT never segmented is
                        not in the files at all and cannot be counted.

In-window rows are evaluation observations dated after as_of: reserved for scoring a hindcast, never simulation inputs.
`prior_oiled_observation` is dated on or before as_of and is information available at the scenario start.
"""
from __future__ import annotations

import pandas as pd

from src.shoreline_remediation.projections import catalogue as C

SURVEY_LIMITATIONS = (
    "A 'clear' visit is the derived status of scripts/build_beach_series.py: all zones NOO and NOO zones covering at least 50% of "
    "the segment length (ASSUMED threshold). 'partial_clear' visits (NOO covering less) are treated as uninformative.",
    "Survey dates are days; visit frequency is uneven between segments, so arrival windows differ in width and are not arrival "
    "times. Oil can be missed by a survey or arrive and leave between visits.",
    "The layer is the Mobile ICP cumulative SCAT layer of 27 Sep 2014 (Mississippi, Alabama, Florida panhandle): only segments "
    "SCAT defined and surveyed are present. Louisiana shorelines are not in this checkout's visit table.",
    "Zone IDs are unrelated between dates (layer metadata); classes are built at segment level only.",
)


SURVEY_CLASSES = ("oiled_before_window", "clear_then_oiled", "oiled_at_first_visit", "no_oil_observed",
                  "inconclusive_partial_clear", "not_visited_in_window")


def survey_contact(spec, root) -> tuple:
    """Rows (one per segment of the case) and a summary block."""
    v = pd.read_csv(root / C.EVIDENCE["noaa_scat_mobile_visits"].path, parse_dates=["date"])
    s = pd.read_csv(root / C.EVIDENCE["noaa_scat_mobile_segments"].path)
    start, end = pd.Timestamp(spec.as_of), pd.Timestamp(spec.end_date)
    w = v[(v.date > start) & (v.date <= end)].sort_values("date")
    ever_oiled = set(v[v.status == "oiled"].segment)
    later_oiled = set(v[(v.date > end) & (v.status == "oiled")].segment) - set(w[w.status == "oiled"].segment)
    prior_oiled = v[(v.date <= start) & (v.status == "oiled")].sort_values("date").groupby("segment").date.first()
    clear_dates = {k: g.date for k, g in v[(v.status == "clear") & (v.date <= end)].groupby("segment")}
    release_start = pd.Timestamp(C.EXPOSURE_CASES[spec.site_id].window[0])
    by_seg = dict(tuple(w.groupby("segment")))
    no_window = {"window_start": None, "window_end": None, "window_days": None}
    rows = []
    for seg in s.sort_values("segment").itertuples():
        r = by_seg.get(seg.segment)
        prior = prior_oiled.get(seg.segment)
        base = {"scenario_id": spec.scenario_id, "site_id": spec.site_id, "endpoint": spec.endpoint,
                "record_type": "observed_survey_contact", "record_class": C.RECORD_TYPES["observed_survey_contact"],
                "evidence_id": "noaa_scat_mobile_visits", "role": "evaluation_observation (dated after as_of; never a simulation input)",
                "segment": seg.segment, "state": seg.state, "esi_class": seg.esi_class, "seg_length_m": seg.seg_length_m,
                "lon": seg.lon, "lat": seg.lat,
                "prior_oiled_observation": None if prior is None else prior.date().isoformat()}
        if r is None:
            common = {"n_visits": 0, "n_clear_visits": 0, "first_visit": None, "last_visit": None}
        else:
            common = {"n_visits": int(len(r)), "n_clear_visits": int((r.status == "clear").sum()),
                      "first_visit": r.date.iloc[0].date().isoformat(), "last_visit": r.date.iloc[-1].date().isoformat()}
        in_oiled = None if r is None else r[r.status == "oiled"]
        first_cat = None if in_oiled is None or in_oiled.empty else in_oiled.top_cat.iloc[0]
        if prior is not None:
            rows.append({**base, **common, **no_window, "survey_class": "oiled_before_window", "first_oiled_category": first_cat})
            continue
        if r is None:
            rows.append({**base, **common, **no_window, "survey_class": "not_visited_in_window", "first_oiled_category": None})
            continue
        oiled = in_oiled
        if oiled.empty:
            cls = "no_oil_observed" if common["n_clear_visits"] else "inconclusive_partial_clear"
            rows.append({**base, **common, **no_window, "survey_class": cls, "first_oiled_category": None})
            continue
        t1 = oiled.date.iloc[0]
        # last clear visit before the first oil, from the whole record (it may precede as_of; no oil was seen before as_of)
        clear_before = clear_dates.get(seg.segment)
        clear_before = None if clear_before is None else clear_before[clear_before < t1]
        if clear_before is not None and len(clear_before):
            t0, cls = clear_before.max(), "clear_then_oiled"
        else:
            t0, cls = release_start, "oiled_at_first_visit"     # never seen clear before: arrival bounded by the release start
        rows.append({**base, **common, "survey_class": cls, "window_start": t0.date().isoformat(), "window_end": t1.date().isoformat(),
                     "window_days": int((t1 - t0).days), "first_oiled_category": oiled.top_cat.iloc[0]})
    df = pd.DataFrame(rows)
    counts = df.survey_class.value_counts().to_dict()
    cto = df[df.survey_class == "clear_then_oiled"].window_days
    noo = df[df.survey_class == "no_oil_observed"]
    summary = {
        "window": [spec.as_of, spec.end_date], "segments_in_layer": int(len(df)),
        "survey_class_counts": {k: int(counts.get(k, 0)) for k in SURVEY_CLASSES},
        "first_oiled_observation": None if w[w.status == "oiled"].empty else w[w.status == "oiled"].date.min().date().isoformat(),
        "first_visit_in_window": None if w.empty else w.date.min().date().isoformat(),
        "clear_then_oiled_window_days": ({"median": float(cto.median()), "p25": float(cto.quantile(0.25)),
                                          "p75": float(cto.quantile(0.75)), "max": int(cto.max())} if len(cto) else None),
        "no_oil_observed_with_2plus_clear_visits": int((noo.n_clear_visits >= 2).sum()),
        "no_oil_observed_but_oiled_after_window": int(noo.segment.isin(later_oiled).sum()),
        "no_oil_observed_never_oiled_in_record": int((~noo.segment.isin(ever_oiled)).sum()),
        "candidate_false_alarm_denominator": int(((noo.n_clear_visits >= 2) & ~noo.segment.isin(ever_oiled)).sum()),
        "false_alarm_metric": ("Possible with care: the layer includes surveyed segments where no oil was ever recorded (2010-2013). "
                               "Proposed denominator: segments with at least two clear visits in the window and no oiled visit in the "
                               "whole record (candidate_false_alarm_denominator). A simulated contact there is a candidate false "
                               "alarm, not a proven one, because surveys can miss transient oil."),
        "limitations": list(SURVEY_LIMITATIONS),
    }
    return df, summary
