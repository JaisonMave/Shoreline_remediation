"""User-defined vegetation-cover what-if for the Bay Jimmy plots (remediation scenarios plan, section 3; model cover_whatif/1).

Baseline. The natural-recovery arm starts from the last measured mean total cover of the untreated, heavily oiled plots that is
available at the scenario's as_of date (evidence.vegetation_observed) and holds it constant:
    "Natural recovery scenario: cover held at the last observed value."
This is a stated assumption, not a recovery forecast. Surveys are dated to the month; the curve starts at the end of the survey
month, the date from which the loader treats that survey as available.

Treatment. A user-entered, signed peak change P (percentage points) with three ordered dates, start s < peak p < end e:

    difference(t) = 0                          t <= s
                  = P * (t - s) / (p - s)      s < t <= p
                  = P * (e - t) / (e - p)      p < t < e
                  = 0                          t >= e
    treatment(t)  = natural(t) + difference(t)

Calendar convention: t is the calendar decimal year (recovery_trajectories.decimal_year), as in the retreat what-if. 1 January
dates are whole years, so a 2030-2032-2034 effect is exactly halfway on 1 January 2031 and 2033. The user is assuming a temporary
effect that returns to zero by e. Total cover must stay within 0-100% at every date; because the baseline is flat and the
difference peaks at p, the bound is checked exactly at the peak. A blank change draws no treatment curve; an entered zero draws
two coincident arms. Nothing here is a measured treatment effect, a forecast or a recommendation.
"""
from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass

import pandas as pd

from src.shoreline_remediation.projections import projection as P
from src.shoreline_remediation.recovery_trajectories import decimal_year

COVER_MODEL = "cover_whatif/1"
ENDPOINT = "total_vegetation_cover"
UNIT = "percent"
DIFF_UNIT = "percentage points"
BASELINE_LABEL = "Natural recovery scenario: cover held at the last observed value"
WHATIF_LABEL = "User-defined what-if"
NATURAL_ARM, TREATMENT_ARM = "natural_recovery", "treatment_what_if"
TEMPORARY_NOTE = ("You are assuming the effect is temporary: it rises or falls linearly to your peak, then returns linearly to "
                  "zero by the end date.")


@dataclass(frozen=True)
class CoverEffect:
    option: str
    start: dt.date
    peak: dt.date
    end: dt.date
    peak_change: float | None          # percentage points; None = not entered (no treatment curve)
    source: str = "Bay Jimmy Assessment what-if controls"

    def as_dict(self) -> dict:
        return {"technique": self.option, "label": WHATIF_LABEL, "origin": "user_assumption", "source": self.source,
                "intervention_start": self.start.isoformat(), "effect_peak": self.peak.isoformat(),
                "effect_end": self.end.isoformat(), "peak_change": self.peak_change, "unit": DIFF_UNIT,
                "shape": "linear rise to the peak, linear return to zero by the end", "measured": False}


@dataclass(frozen=True)
class Anchor:
    survey: str                # survey date as the source records it, e.g. "2016-09"
    date_precision: str
    date_basis: str
    starts: dt.date            # the date the baseline curve starts (end of the survey month)
    value: float               # mean total cover, percent
    n_plots: int


def anchor_from(observations: pd.DataFrame) -> Anchor | None:
    """The last untreated survey available at as_of (evidence.vegetation_observed rows), or None."""
    obs = observations.loc[observations.available_at_as_of] if len(observations) else observations
    if obs.empty:
        return None
    last = obs.sort_values("decimal_year").iloc[-1]
    return Anchor(str(last.date), str(last.date_precision), str(last.date_basis), dt.date.fromisoformat(last.available_from),
                  float(last.value), int(last.n_plots))


def allowed_range(baseline: float) -> tuple:
    """Peak changes that keep total cover within 0-100% when the baseline is `baseline` percent."""
    return -baseline, 100.0 - baseline


def problem(effect: CoverEffect, anchor: Anchor, scenario_end: dt.date) -> str:
    """A plain-language reason the assumption cannot be applied, or ''."""
    if effect.peak_change is None:
        return ""
    if not (isinstance(effect.peak_change, (int, float)) and math.isfinite(effect.peak_change)):
        return "Enter a finite peak change in percentage points."
    if effect.start <= anchor.starts:
        return f"The intervention must start after the last survey ({anchor.survey}, curve from {anchor.starts:%d %b %Y})."
    if not (effect.start < effect.peak < effect.end):
        return "The dates must be in order: start, then peak, then end."
    if effect.peak > scenario_end:
        return "The peak falls after the scenario end date. Move the end date later or the peak earlier."
    lo, hi = allowed_range(anchor.value)
    if not (lo <= effect.peak_change <= hi):
        return (f"With the baseline at {anchor.value:.1f}%, total cover would be {anchor.value + effect.peak_change:.1f}% at the "
                f"peak. Total cover must stay within 0-100%, so the peak change must be between {lo:+.1f} and {hi:+.1f} "
                "percentage points.")
    return ""


def difference(t: float, s: float, p: float, e: float, peak: float) -> float:
    if t <= s or t >= e:
        return 0.0
    if t <= p:
        return peak * (t - s) / (p - s) + 0.0          # + 0.0 turns -0.0 into 0.0 before export
    return peak * (e - t) / (e - p) + 0.0


@dataclass
class CoverWhatIf:
    frame: pd.DataFrame
    anchor: Anchor
    effect: CoverEffect | None
    has_treatment: bool
    message: str

    def at(self, date: dt.date) -> pd.Series:
        return self.frame.set_index("date").loc[date.isoformat()]


def two_arms(anchor: Anchor, end: dt.date, cadence: str, effect: CoverEffect | None) -> CoverWhatIf:
    """Both arms on one grid: the cadence plus the exact start, peak and end dates (so the peak is always a sample)."""
    why = "" if effect is None else problem(effect, anchor, end)
    active = effect is not None and effect.peak_change is not None and not why
    if effect is None or effect.peak_change is None:
        why = why or "No treatment curve: enter an assumed peak change to draw one."
    extra = tuple(d for d in (effect.start, effect.peak, effect.end) if anchor.starts < d < end) if active else ()
    if active:
        s, p, e, peak = (decimal_year(effect.start), decimal_year(effect.peak), decimal_year(effect.end),
                         float(effect.peak_change))
    rows = []
    for d in P.sample_dates(anchor.starts, end, cadence, extra):
        t = decimal_year(d)
        kind = ("anchor" if d == anchor.starts else "end_date" if d == end else
                "intervention_start" if active and d == effect.start else "effect_peak" if active and d == effect.peak else
                "effect_end" if active and d == effect.end else "regular")
        row = {"date": d.isoformat(), "decimal_year": t, "sample": kind, "natural_recovery_pct": anchor.value}
        if active:
            diff = difference(t, s, p, e, peak)
            row.update(treatment_pct=anchor.value + diff, difference_pp=diff)
        rows.append(row)
    return CoverWhatIf(pd.DataFrame(rows), anchor, effect, active, "" if active else why)


def peak_text(w: CoverWhatIf) -> str:
    """Both values and the difference at the exact peak date."""
    if not w.has_treatment:
        return f"Natural recovery scenario: {w.anchor.value:.1f}% total cover, held from the {w.anchor.survey} survey."
    r = w.at(w.effect.peak)
    diff = float(r.difference_pp)
    sign = "coincide (0.0 percentage points)" if abs(diff) < 0.05 else f"{diff:+.1f} percentage points"
    return (f"At the peak ({w.effect.peak:%d %b %Y}): natural recovery {r.natural_recovery_pct:.1f}%; treatment scenario "
            f"{r.treatment_pct:.1f}%; difference {sign}. The difference returns to zero by {w.effect.end:%d %b %Y}.")


def export_rows(observations: pd.DataFrame, w: CoverWhatIf, option_label: str) -> pd.DataFrame:
    """Observed surveys on their recorded dates (month precision), then each arm by date. Shared by the chart and both CSVs."""
    rows = []
    obs = observations.loc[observations.available_at_as_of].sort_values("decimal_year")
    for _, o in obs.iterrows():
        rows.append({"date": o.date, "date_precision": o.date_precision, "plot_date": o.available_from,
                     "series": "Observed (untreated plots)", "arm": "observed", "total_cover": float(o.value), "unit": UNIT,
                     "difference_from_natural": None, "difference_unit": None, "interval_lo": o.interval_lo,
                     "interval_hi": o.interval_hi, "interval_method": o.interval_method, "n_plots": int(o.n_plots),
                     "sample": "survey", "record_type": "observed_group_mean", "record_class": "observation", "origin": "derived",
                     "status_label": "field survey mean (" + str(o.date_basis) + ")", "evidence_id": o.evidence_id})
    for _, r in w.frame.iterrows():
        anchor = r["sample"] == "anchor"
        kind = ({"record_type": "observed_anchor", "record_class": "observation"} if anchor else
                {"record_type": "conditional_projection", "record_class": "conditional_projection"})
        common = {"date": r["date"], "date_precision": "day", "plot_date": r["date"], "unit": UNIT, "interval_lo": None,
                  "interval_hi": None, "interval_method": None, "n_plots": w.anchor.n_plots, "sample": r["sample"], **kind,
                  "evidence_id": "zengel2022_griidc_vegetation"}
        rows.append({**common, "series": BASELINE_LABEL, "arm": NATURAL_ARM, "total_cover": r["natural_recovery_pct"],
                     "difference_from_natural": 0.0 if w.has_treatment else None,
                     "difference_unit": DIFF_UNIT if w.has_treatment else None, "origin": "derived",
                     "status_label": "observed anchor" if anchor else BASELINE_LABEL})
        if w.has_treatment:
            rows.append({**common, "series": f"{WHATIF_LABEL}: {option_label}", "arm": TREATMENT_ARM,
                         "total_cover": r["treatment_pct"], "difference_from_natural": r["difference_pp"],
                         "difference_unit": DIFF_UNIT, "origin": "user_assumption",
                         "status_label": "observed anchor (shared by both arms)" if anchor else WHATIF_LABEL})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------------
# Spec version 2 (shared by the dashboard download and the CLI replay)

def effect_from_spec(spec) -> CoverEffect | None:
    e = getattr(spec, "treatment_effect", None)
    if e is None:
        return None
    return CoverEffect(spec.technique, dt.date.fromisoformat(e["intervention_start"]), dt.date.fromisoformat(e["effect_peak"]),
                       dt.date.fromisoformat(e["effect_end"]), float(e["peak_change"]), e.get("source") or WHATIF_LABEL)


@dataclass
class Computed:
    what: CoverWhatIf
    rows: pd.DataFrame
    applied: bool
    screening_allows: bool
    screening_reason: str
    label: str


def compute(spec, observations: pd.DataFrame, effect: CoverEffect | None, screening_row) -> Computed:
    """Both arms and their export rows. The effect is applied only when the live screening row allows a what-if."""
    from src.shoreline_remediation.projections.whatif import technique_label
    anchor = anchor_from(observations)
    if anchor is None:
        raise ValueError(no_anchor_reason(spec))
    allows = bool(screening_row is not None and getattr(screening_row, "what_if_allowed", False)
                  and getattr(screening_row, "endpoint", "") == ENDPOINT)
    reason = (getattr(screening_row, "what_if_reason", "") if screening_row is not None
              else "the technique could not be screened for this assessment")
    what = two_arms(anchor, spec.end, spec.cadence, effect if allows else None)
    label = technique_label(getattr(spec, "technique", "") or (effect.option if effect else ""))
    return Computed(what, export_rows(observations, what, label), what.has_treatment, allows, reason, label)


def no_anchor_reason(spec) -> str:
    return (f"No untreated survey of total cover is available on or before as_of {spec.as_of}; the first survey is September "
            "2011. A cover scenario must start from a measured value, so no future curve is drawn.")


def spec_dict(as_of: str, end: dt.date, cadence: str, technique: str, context: dict, effect: CoverEffect | None) -> dict:
    """A version-2 cover scenario (inputs only)."""
    from src.shoreline_remediation.projections import catalogue as C
    from src.shoreline_remediation.projections.whatif import technique_label
    return {
        "schema_version": C.SCHEMA_VERSION_2, "scenario_id": "bay_jimmy_dashboard_cover_whatif",
        "description": (f"{WHATIF_LABEL} for {technique_label(technique).lower()}: total vegetation cover of one hypothetical "
                        f"shoreline. Baseline: {BASELINE_LABEL.split(': ')[1]}. Treatment: a user-entered temporary change. "
                        "Not a forecast."),
        "site_id": "bay_jimmy_zengel_plots", "plot_group_id": "untreated_heavy", "habitat": "salt_marsh", "oiling_class": "Heavy",
        "endpoint": ENDPOINT, "unit": UNIT, "arm": "reference", "as_of": as_of, "end_date": end.isoformat(), "cadence": cadence,
        "model_version": COVER_MODEL, "seed": 20261120,
        "evidence_ids": list(C.SUPPORTED[("observed_record/1", ENDPOINT)]), "assumptions": [],
        "technique": technique, "assessment_context": dict(context),
        "treatment_effect": None if effect is None or effect.peak_change is None else {
            "intervention_start": effect.start.isoformat(), "effect_peak": effect.peak.isoformat(),
            "effect_end": effect.end.isoformat(), "peak_change": effect.peak_change, "unit": DIFF_UNIT,
            "origin": "user_assumption", "source": effect.source},
    }


def check_exported(exported: dict | None, computed: Computed) -> dict:
    """Compare outputs saved with a download against the replay. The replay always wins."""
    from src.shoreline_remediation.projections.whatif import CSV_FLOAT_FORMAT, csv_text
    if not exported or not exported.get("rows"):
        return {"status": "no_exported_rows"}
    saved = pd.DataFrame(exported["rows"])
    cols = [c for c in computed.rows.columns if c in saved.columns]
    mine, theirs = csv_text(computed.rows[cols]).splitlines(), csv_text(saved[cols]).splitlines()
    diffs = [{"line": i + 1, "download": a, "replay": b} for i, (a, b) in enumerate(zip(theirs, mine)) if a != b]
    if len(mine) != len(theirs):
        diffs.append({"line": None, "download": f"{len(theirs) - 1} rows", "replay": f"{len(mine) - 1} rows"})
    out = {"status": "matches" if not diffs else "differs", "rows_compared": max(len(mine), len(theirs)) - 1,
           "precision": CSV_FLOAT_FORMAT, "differences": diffs[:20]}
    summary = exported.get("summary") or {}
    if computed.applied and summary:
        r = computed.what.at(computed.what.effect.peak)
        recomputed = {"natural_recovery_pct": float(r.natural_recovery_pct), "treatment_pct": float(r.treatment_pct),
                      "difference_pp": float(r.difference_pp)}
        bad = {k: {"download": summary.get(k), "replay": v} for k, v in recomputed.items()
               if not isinstance(summary.get(k), (int, float)) or CSV_FLOAT_FORMAT % summary[k] != CSV_FLOAT_FORMAT % v}
        if bad:
            out["status"], out["summary_differences"] = "differs", bad
    return out


AS_OF = "2016-12-31"       # the dashboard's evidence cutoff: every Bay Jimmy cover survey (2011-2016) is available


def observation_spec(as_of: str = AS_OF):
    """A version-1 observed_record/1 spec for the untreated, heavily oiled plots' total cover (input to the existing loader)."""
    from src.shoreline_remediation.projections import catalogue as C, spec as S
    return S.from_dict({
        "schema_version": C.SCHEMA_VERSION, "scenario_id": "bay_jimmy_untreated_cover", "site_id": "bay_jimmy_zengel_plots",
        "plot_group_id": "untreated_heavy", "habitat": "salt_marsh", "oiling_class": "Heavy", "endpoint": ENDPOINT, "unit": UNIT,
        "arm": "reference", "as_of": as_of, "end_date": "2100-01-01", "cadence": "annual", "model_version": "observed_record/1",
        "seed": 20261120, "evidence_ids": list(C.SUPPORTED[("observed_record/1", ENDPOINT)]), "assumptions": []})
