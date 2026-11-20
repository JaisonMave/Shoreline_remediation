"""rate_continuation/1: conditional continuation of cumulative retreat from the last observation.

Time convention (docs/PROJECTION_RETREAT_PROTOCOL.md section 2): elapsed time is the difference of calendar decimal years from
recovery_trajectories.decimal_year, computed from actual dates, so the output cadence cannot change any value.

With anchor date a, anchor value R_a, first rate r1, optional change date c and second rate r2 (all in decimal years and m/yr):

    additional(t) = r1 * (min(t, c) - a) + r2 * max(t - c, 0)        (c = +infinity when there is no change)
    cumulative(t) = R_a + additional(t)

Both pieces join continuously at c. At the anchor, additional is exactly 0.0 and cumulative equals R_a exactly.
This is arithmetic on stated assumptions, not a forecast. It assigns no recommendation.
"""
from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass

import pandas as pd

from src.shoreline_remediation.projections import catalogue as C
from src.shoreline_remediation.recovery_trajectories import decimal_year


@dataclass(frozen=True)
class RateSegment:
    assumption_id: str
    rate: float                 # m/yr, positive = land lost
    unit: str
    origin: str
    source: str
    starts: dt.date
    ends: dt.date

    def as_dict(self) -> dict:
        return {"assumption_id": self.assumption_id, "rate": self.rate, "unit": self.unit, "origin": self.origin,
                "source": self.source, "applies_from": self.starts.isoformat(), "applies_to": self.ends.isoformat()}


def rate_segments(spec, anchor: dt.date) -> list:
    """The rate schedule from the spec's assumptions, from the anchor to end_date."""
    first = spec.assumption("retreat_rate")
    change = spec.assumption("rate_change_date")
    end = spec.end
    if change is None:
        return [RateSegment("retreat_rate", first.value, first.unit, first.origin, first.source, anchor, end)]
    c = dt.date.fromisoformat(change.value)
    second = spec.assumption("changed_retreat_rate")
    return [RateSegment("retreat_rate", first.value, first.unit, first.origin, first.source, anchor, c),
            RateSegment("changed_retreat_rate", second.value, second.unit, second.origin, second.source, c, end)]


def additional_retreat(t: float, anchor_t: float, segments_t: list) -> float:
    """Integral of a piecewise-constant rate from anchor_t to t. segments_t: [(start_t, end_t, rate), ...] contiguous."""
    total = 0.0
    for s, e, r in segments_t:
        lo, hi = max(s, anchor_t), min(e, t)
        if hi > lo:
            total += r * (hi - lo)
    return total


def sample_dates(anchor: dt.date, end: dt.date, cadence: str, extra: tuple = ()) -> list:
    """Anchor, regular dates strictly between anchor and end, any extra dates (rate change), and the exact end date.
    Regular dates are the first day of each month (monthly), of Jan/Apr/Jul/Oct (quarterly) or of January (annual), so annual
    dates are a subset of quarterly and monthly ones."""
    step = 12 // C.CADENCES[cadence]
    dates = {anchor, end, *extra}
    y, m = anchor.year, anchor.month
    while True:
        m += 1
        if m > 12:
            y, m = y + 1, 1
        d = dt.date(y, m, 1)
        if d >= end:
            break
        if (m - 1) % step == 0 and d > anchor:
            dates.add(d)
    return sorted(dates)


def project(spec, anchor: dt.date, anchor_value: float, n_plots: int) -> tuple:
    """Return (table, segments). One row per sample date; the anchor row is the observed value itself."""
    if not math.isfinite(anchor_value):
        raise ValueError("anchor value must be finite")
    segs = rate_segments(spec, anchor)
    a = decimal_year(anchor)
    seg_t = [(decimal_year(s.starts), decimal_year(s.ends), s.rate) for s in segs]
    change = tuple(s.starts for s in segs[1:])
    label = describe_rates(segs)
    rows = []
    for d in sample_dates(anchor, spec.end, spec.cadence, change):
        t = decimal_year(d)
        add = 0.0 if d == anchor else additional_retreat(t, a, seg_t)
        in_effect = next((s for s in segs if s.starts < d <= s.ends), None)
        kind = ("anchor" if d == anchor else "end_date" if d == spec.end else "rate_change" if d in change else "regular")
        rows.append({
            "scenario_id": spec.scenario_id, "site_id": spec.site_id, "plot_group_id": spec.plot_group_id,
            "endpoint": spec.endpoint, "unit": spec.unit, "date": d.isoformat(), "decimal_year": t,
            "years_since_anchor": t - a, "additional_retreat_since_anchor_m": add, "cumulative_retreat_since_origin_m": anchor_value + add,
            "rate_in_effect_m_per_yr": None if in_effect is None else in_effect.rate,
            "rate_assumption_id": None if in_effect is None else in_effect.assumption_id,
            "rate_origin": None if in_effect is None else in_effect.origin,
            "sample": kind,
            "record_type": "observed_anchor" if d == anchor else "conditional_projection",
            "record_class": "observation" if d == anchor else "conditional_projection",
            "status_label": f"observed group mean (n = {n_plots} plots)" if d == anchor else C.CONDITIONAL_LABEL,
            "scenario_rates": label,
        })
    return pd.DataFrame(rows), segs


def describe_rates(segs: list) -> str:
    if len(segs) == 1:
        return f"{segs[0].rate:.2f} m/yr ({segs[0].origin.replace('_', ' ')})"
    a, b = segs
    return (f"{a.rate:.2f} m/yr ({a.origin.replace('_', ' ')}) to {b.starts.isoformat()}, then {b.rate:.2f} m/yr "
            f"({b.origin.replace('_', ' ')})")
