"""User-defined treatment what-if for cumulative shoreline retreat (remediation scenarios plan, section 3).

Two arms describe the SAME hypothetical shoreline from the same observed anchor (the last survey of the untreated Bay Jimmy
plots). The natural-recovery arm follows the stated baseline rate schedule (rate_continuation/1). The treatment arm follows the
same schedule plus a user-entered signed change in m/yr, applied only between the intervention start and the end of its effect:

    treatment(t) = natural(t) + delta * max(0, min(t, e) - max(s, a))

with a = anchor, s = intervention start, e = end of effect, all in calendar decimal years (recovery_trajectories.decimal_year).
After e the baseline rate resumes and the distance gained or lost during treatment is kept; the arms are identical before s.
Values depend on the date only, so the output cadence cannot change them.

Nothing here is a measured treatment effect, a forecast or a recommendation. The change is a `user_assumption`; a blank change
draws no treatment curve and an explicit zero draws two coinciding curves.
"""
from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass

import pandas as pd

from src.shoreline_remediation.projections import catalogue as C, projection as P
from src.shoreline_remediation.recovery_trajectories import decimal_year

WHATIF_LABEL = "User-defined what-if"
WHATIF_VERSION = "retreat-treatment-what-if/1"
NATURAL_ARM, TREATMENT_ARM = "natural_recovery", "treatment_what_if"


@dataclass(frozen=True)
class RetreatEffect:
    """The user's assumption for one technique. delta_rate None means 'not entered' (no treatment curve)."""
    option: str
    start: dt.date
    end: dt.date
    delta_rate: float | None
    source: str = "Bay Jimmy Assessment what-if controls"

    def as_dict(self) -> dict:
        return {"technique": self.option, "label": WHATIF_LABEL, "origin": "user_assumption", "source": self.source,
                "intervention_start": self.start.isoformat(), "effect_end": self.end.isoformat(),
                "rate_change_m_per_yr": self.delta_rate, "unit": "m/yr",
                "sign": "negative = slower retreat (less land lost); positive = faster retreat",
                "measured": False}


@dataclass
class WhatIf:
    frame: pd.DataFrame            # one row per sample date: both arms side by side
    segments: list                 # baseline RateSegments
    effect: RetreatEffect | None
    has_treatment: bool
    message: str                   # why there is no treatment curve, or ''

    @property
    def last(self) -> pd.Series:
        return self.frame.iloc[-1]


def problem(effect: RetreatEffect, anchor: dt.date, scenario_end: dt.date, segments: list) -> str:
    """A plain-language reason the assumption cannot be applied, or ''."""
    if effect.delta_rate is None:
        return ""
    if not (isinstance(effect.delta_rate, (int, float)) and math.isfinite(effect.delta_rate)):
        return "Enter a finite rate change in m/year."
    if effect.start <= anchor:
        return f"The intervention must start after the last survey ({anchor:%d %b %Y})."
    if effect.end <= effect.start:
        return "The end of the effect must be after the intervention start."
    if effect.start >= scenario_end:
        return "The intervention starts on or after the scenario end date. Move the end date later or the start earlier."
    for s in segments:
        if s.starts < effect.end and s.ends > effect.start and s.rate + effect.delta_rate < 0:
            return (f"During the intervention the treated rate would be {s.rate + effect.delta_rate:.2f} m/year "
                    f"({s.rate:.2f} {effect.delta_rate:+.2f}). A negative rate means the shoreline advances seaward, which this "
                    "what-if does not represent. Choose a change no more negative than the baseline rate.")
    return ""


def two_arms(spec, anchor: dt.date, anchor_value: float, effect: RetreatEffect | None) -> WhatIf:
    """Both arms on one sample grid (the spec's cadence plus the rate-change, intervention-start and effect-end dates)."""
    if not math.isfinite(anchor_value):
        raise ValueError("anchor value must be finite")
    segs = P.rate_segments(spec, anchor)
    a = decimal_year(anchor)
    seg_t = [(decimal_year(s.starts), decimal_year(s.ends), s.rate) for s in segs]
    why = "" if effect is None else problem(effect, anchor, spec.end, segs)
    active = effect is not None and effect.delta_rate is not None and not why
    if effect is None or effect.delta_rate is None:
        why = why or "No treatment curve: enter an assumed rate change to draw one."
    extra = tuple(s.starts for s in segs[1:])
    if active:
        extra += tuple(d for d in (effect.start, effect.end) if anchor < d < spec.end)
        s_t, e_t, delta = decimal_year(effect.start), decimal_year(effect.end), float(effect.delta_rate)
    rows = []
    for d in P.sample_dates(anchor, spec.end, spec.cadence, extra):
        t = decimal_year(d)
        base = 0.0 if d == anchor else P.additional_retreat(t, a, seg_t)
        rate = next((s.rate for s in segs if s.starts < d <= s.ends), None)
        row = {"date": d.isoformat(), "decimal_year": t, "years_since_anchor": t - a,
               "natural_recovery_m": anchor_value + base, "natural_rate_m_per_yr": rate,
               "sample": ("anchor" if d == anchor else "end_date" if d == spec.end else
                          "rate_change" if d in extra[:len(segs) - 1] else
                          "intervention_start" if active and d == effect.start else
                          "effect_end" if active and d == effect.end else "regular")}
        if active:
            gained = delta * max(0.0, min(t, e_t) - max(s_t, a)) + 0.0      # + 0.0 turns -0.0 into 0.0 before export
            in_effect = effect.start < d <= effect.end
            row.update(treatment_m=anchor_value + base + gained, difference_m=gained,
                       treatment_rate_m_per_yr=None if rate is None else rate + (delta if in_effect else 0.0),
                       effect_in_force=in_effect)
            if not math.isfinite(row["treatment_m"]):
                raise ValueError("Projected retreat exceeds the numeric range. Choose a smaller rate or a shorter horizon.")
        if not math.isfinite(row["natural_recovery_m"]):
            raise ValueError("Projected retreat exceeds the numeric range. Choose a smaller rate or a shorter horizon.")
        rows.append(row)
    return WhatIf(pd.DataFrame(rows), segs, effect, active, "" if active else why)


def summary_text(w: WhatIf, end: dt.date) -> str:
    """Plain-language comparison at the scenario end date."""
    last = w.last
    head = f"By {end:%d %b %Y}: natural recovery {last.natural_recovery_m:.2f} m"
    if not w.has_treatment:
        return head + " of cumulative retreat since December 2010."
    diff = float(last.difference_m)
    if abs(diff) < 0.005:
        tail = "The two curves coincide (0.00 m difference)."
    else:
        tail = f"{abs(diff):.2f} m {'less' if diff < 0 else 'more'} cumulative retreat under your assumption."
    return f"{head}; treatment scenario {last.treatment_m:.2f} m. {tail}"


def export_rows(observations: pd.DataFrame, w: WhatIf, n_plots: int, option_label: str) -> pd.DataFrame:
    """Tidy rows for the chart and the downloads: observed surveys on their actual dates, then each scenario arm by date."""
    rows = []
    for _, o in observations.iterrows():
        rows.append({"date": o["date"], "series": "Observed (untreated plots)", "arm": "observed",
                     "cumulative_retreat_m": float(o["value"]), "difference_from_natural_m": None,
                     "rate_in_effect_m_per_yr": None, "n_plots": int(o["n_plots"]), "record_type": "observed_group_mean",
                     "record_class": "observation", "origin": "derived", "status_label": "field survey (Zengel et al. 2022)",
                     "evidence_id": "zengel2022_griidc_field_positions"})
    for _, r in w.frame.iterrows():
        anchor = r["sample"] == "anchor"
        kind = ({"record_type": "observed_anchor", "record_class": "observation"} if anchor else
                {"record_type": "conditional_projection", "record_class": "conditional_projection"})
        rows.append({"date": r["date"], "series": "Natural recovery (assumed rate)", "arm": NATURAL_ARM,
                     "cumulative_retreat_m": r["natural_recovery_m"], "difference_from_natural_m": 0.0 if w.has_treatment else None,
                     "rate_in_effect_m_per_yr": r["natural_rate_m_per_yr"], "n_plots": n_plots, **kind,
                     "origin": ";".join(dict.fromkeys(s.origin for s in w.segments)),
                     "status_label": "observed anchor" if anchor else C.CONDITIONAL_LABEL,
                     "evidence_id": "zengel2022_griidc_field_positions"})
        if w.has_treatment:
            rows.append({"date": r["date"], "series": f"{WHATIF_LABEL}: {option_label}", "arm": TREATMENT_ARM,
                         "cumulative_retreat_m": r["treatment_m"], "difference_from_natural_m": r["difference_m"],
                         "rate_in_effect_m_per_yr": r["treatment_rate_m_per_yr"], "n_plots": n_plots, **kind,
                         "origin": "user_assumption",
                         "status_label": "observed anchor (shared by both arms)" if anchor else WHATIF_LABEL,
                         "evidence_id": "zengel2022_griidc_field_positions"})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------------
# One calculation and one export for the dashboard and the CLI (spec version 2)

CSV_FLOAT_FORMAT = "%.6f"          # the declared export precision of what-if CSV files (dashboard download and CLI run)
CSV_NAME = "whatif.csv"


def technique_label(option: str) -> str:
    return option.replace("_", " ").capitalize()


def csv_text(rows: pd.DataFrame) -> str:
    """The what-if CSV exactly as both the dashboard download and the CLI write it."""
    return rows.to_csv(index=False, float_format=CSV_FLOAT_FORMAT, lineterminator="\n")


def effect_from_spec(spec) -> RetreatEffect | None:
    """The user's effect from a version-2 spec, or None (no treatment curve)."""
    e = getattr(spec, "treatment_effect", None)
    if e is None:
        return None
    return RetreatEffect(spec.technique, dt.date.fromisoformat(e["intervention_start"]), dt.date.fromisoformat(e["effect_end"]),
                         float(e["rate_change"]), e.get("source") or "user-defined what-if")


@dataclass
class Computed:
    what: WhatIf
    rows: pd.DataFrame
    anchor: pd.Series
    applied: bool                  # a treatment curve was drawn
    screening_allows: bool
    screening_reason: str          # the inventory's what_if_reason for this technique and endpoint, or why it is unknown
    label: str


def compute(spec, observations: pd.DataFrame, effect: RetreatEffect | None, screening_row) -> Computed:
    """Both arms and their export rows. The effect is applied only when the live screening row allows a what-if for this
    technique; any eligibility text carried in a download is never consulted. `observations` is runner.observed_record(spec)."""
    obs = observations.loc[observations.available_at_as_of].sort_values("date")
    if obs.empty:
        raise ValueError("A dated observation on or before as_of is needed to start the scenario.")
    anchor = obs.iloc[-1]
    allows = bool(screening_row is not None and getattr(screening_row, "what_if_allowed", False)
                  and getattr(screening_row, "endpoint", "") == "cumulative_shoreline_retreat")
    reason = (getattr(screening_row, "what_if_reason", "") if screening_row is not None
              else "the technique could not be screened for this assessment")
    what = two_arms(spec, dt.date.fromisoformat(anchor.date), float(anchor.value), effect if allows else None)
    label = technique_label(getattr(spec, "technique", "") or (effect.option if effect else ""))
    rows = export_rows(obs, what, int(anchor.n_plots), label)
    return Computed(what, rows, anchor, what.has_treatment, allows, reason, label)


def spec_dict_v2(base: dict, technique: str, context: dict, effect: RetreatEffect | None) -> dict:
    """A version-2 scenario (inputs only) from the dashboard's version-1 retreat scenario dict."""
    d = {k: v for k, v in base.items() if k != "comparator_group_id"}
    d.update(schema_version=C.SCHEMA_VERSION_2, model_version=C.WHATIF_MODEL, scenario_id="bay_jimmy_dashboard_whatif",
             description=f"{WHATIF_LABEL} for {technique_label(technique).lower()}: conditional retreat of one hypothetical "
                         "shoreline under natural recovery and under a user-entered rate change. Not a forecast.",
             technique=technique, assessment_context=dict(context),
             treatment_effect=None if effect is None or effect.delta_rate is None else {
                 "intervention_start": effect.start.isoformat(), "effect_end": effect.end.isoformat(),
                 "rate_change": effect.delta_rate, "unit": "m/yr", "origin": "user_assumption", "source": effect.source})
    return d


def check_exported(exported: dict | None, computed: Computed) -> dict:
    """Compare the outputs saved with a download against the replay. The replay always wins: outputs are never inputs."""
    if not exported or not exported.get("rows"):
        return {"status": "no_exported_rows"}
    saved = pd.DataFrame(exported["rows"])
    cols = [c for c in computed.rows.columns if c in saved.columns]
    mine = csv_text(computed.rows[cols]).splitlines()
    theirs = csv_text(saved[cols]).splitlines()
    diffs = [{"line": i + 1, "download": a, "replay": b} for i, (a, b) in enumerate(zip(theirs, mine)) if a != b]
    if len(mine) != len(theirs):
        diffs.append({"line": None, "download": f"{len(theirs) - 1} rows", "replay": f"{len(mine) - 1} rows"})
    out = {"status": "matches" if not diffs else "differs", "rows_compared": max(len(mine), len(theirs)) - 1,
           "precision": CSV_FLOAT_FORMAT, "differences": diffs[:20]}
    summary = exported.get("summary") or {}
    if computed.applied and summary:
        last = computed.what.last
        recomputed = {"natural_recovery_m": float(last.natural_recovery_m), "treatment_m": float(last.treatment_m),
                      "difference_m": float(last.difference_m)}
        bad = {k: {"download": summary.get(k), "replay": v} for k, v in recomputed.items()
               if not isinstance(summary.get(k), (int, float)) or CSV_FLOAT_FORMAT % summary[k] != CSV_FLOAT_FORMAT % v}
        if bad:
            out["status"] = "differs"
            out["summary_differences"] = bad
    return out


@dataclass(frozen=True)
class Screening:
    """A technique's what-if eligibility for retreat, read from the inventory of a reproduced assessment report."""
    row: object | None             # inventory.InventoryRow for (technique, cumulative_shoreline_retreat), or None
    reason: str
    assessment_status: str
    pipeline: dict

    @property
    def allows(self) -> bool:
        return bool(self.row is not None and self.row.what_if_allowed)

    def as_dict(self) -> dict:
        r = self.row
        return {"assessment_status": self.assessment_status, "pipeline": self.pipeline,
                "technique": getattr(r, "option", None), "category": getattr(r, "category", None),
                "what_if_allowed": self.allows, "reason": self.reason,
                "unresolved_conditions": list(getattr(r, "unresolved_conditions", ()) or ()),
                "source": "re-derived on this run from the assessment; eligibility text saved in the input is not used"}


def screen(assessment, technique: str, endpoint: str = "cumulative_shoreline_retreat") -> Screening:
    """Eligibility for one endpoint from a reproduced assessment (assessment_screening.Assessment) through the inventory."""
    from src.shoreline_remediation.projections.inventory import build_inventory
    if assessment.report is None:
        return Screening(None, assessment.reason, assessment.status, assessment.pipeline)
    inv = build_inventory(assessment.report)
    if not inv.in_scope:
        return Screening(None, inv.scope_reason, assessment.status, assessment.pipeline)
    if technique not in inv.options:
        return Screening(None, f"'{technique}' is not an option in this assessment.", assessment.status, assessment.pipeline)
    row = inv.cell(technique, endpoint)
    return Screening(row, row.what_if_reason, assessment.status, assessment.pipeline)
