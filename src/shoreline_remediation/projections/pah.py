"""User-defined soil tPAH what-if for the Bay Jimmy plots (remediation scenarios plan, section 3; model tpah_whatif/1).

Anchor. The last untreated, heavily oiled soil tPAH group mean available at the scenario's as_of date (evidence.tpah_observed):
0-10 cm cores with surface oil scraped aside, tPAH as reported in the Zengel et al. 2015 S1 Table (43 to 45 compounds), dry or wet
basis not recorded. For the full record this is September 2012, 112 mg/kg, nine plots. Surveys are dated to the month; the curve
starts at the end of the survey month, when the loader treats the measurement as available.

Baseline (the user's choice; both are assumptions, not forecasts):
    hold:       C(t) = C0
    half-life:  C(t) = C0 * 2 ** (-(t - t0) / h)        h > 0 years; assumes a zero long-term background concentration

Treatment. A one-time reduction r (percent of the measured 0-10 cm soil tPAH concentration) applied on the intervention date d:
the concentration drops from C(d) to C(d) * (1 - r/100) on d, and both arms then follow the same baseline rule, so
    treatment(t) = natural(t)                     t < d (and the 'before' row at d)
    treatment(t) = natural(t) * (1 - r/100)       t >= d ('after' row at d onward)
Two rows are written at d (before and after), so a chart shows the drop on one date instead of a gradual decline. Time is in
calendar decimal years (recovery_trajectories.decimal_year), as in the other what-ifs. A blank reduction draws the baseline only;
0% draws two identical arms; 0-100% is accepted. The percentage applies to soil concentration: a percentage of visible surface
oil collected does not establish it. Nothing here is a measured treatment effect, a forecast or a recommendation.
"""
from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass

import pandas as pd

from src.shoreline_remediation.projections import projection as P
from src.shoreline_remediation.recovery_trajectories import decimal_year

TPAH_MODEL = "tpah_whatif/1"
ENDPOINT = "soil_tpah"
UNIT = "mg/kg"
REDUCTION_UNIT = "percent of soil tPAH concentration"
WHATIF_LABEL = "User-defined what-if"
NATURAL_ARM, TREATMENT_ARM = "natural_recovery", "treatment_what_if"
HOLD, HALF_LIFE = "hold", "half_life"
DEFAULT_BASIS = "user-defined sensitivity assumption"
SOIL_NOTE = ("The percentage applies to the measured 0-10 cm soil tPAH concentration. A percentage of visible surface oil "
             "collected does not establish that value.")
BACKGROUND_NOTE = "This simple scenario assumes a zero long-term background concentration."
AS_OF = "2016-12-31"       # the dashboard's evidence cutoff: both Bay Jimmy tPAH surveys (2011, 2012) are available


def baseline_label(half_life: float | None) -> str:
    if half_life is None:
        return "Natural recovery scenario: concentration held at the last observation"
    return f"Natural recovery scenario: decline with an assumed half-life of {half_life:g} years (zero long-term background)"


@dataclass(frozen=True)
class PahEffect:
    option: str
    date: dt.date
    reduction_percent: float | None     # None = not entered (no treatment curve)
    basis: str = DEFAULT_BASIS
    source: str = "Bay Jimmy Assessment what-if controls"

    def as_dict(self) -> dict:
        return {"technique": self.option, "label": WHATIF_LABEL, "origin": "user_assumption", "source": self.source,
                "intervention_date": self.date.isoformat(), "reduction_percent": self.reduction_percent,
                "unit": REDUCTION_UNIT, "basis": self.basis, "measured": False}


@dataclass(frozen=True)
class Anchor:
    survey: str                # as the source records it, e.g. "2012-09"
    survey_period: str         # e.g. "September 2012"
    date_precision: str
    starts: dt.date            # the curve starts at the end of the survey month
    value: float               # mg/kg
    n_plots: int
    depth: str
    analyte: str


def anchor_from(observations: pd.DataFrame) -> Anchor | None:
    obs = observations.loc[observations.available_at_as_of] if len(observations) else observations
    if obs.empty:
        return None
    last = obs.sort_values("decimal_year").iloc[-1]
    return Anchor(str(last.date), str(last.survey_period), str(last.date_precision),
                  dt.date.fromisoformat(last.available_from), float(last["value"]), int(last.n_plots), str(last.sampling_depth),
                  str(last.analyte))


def no_anchor_reason(as_of: str) -> str:
    return (f"No untreated soil tPAH measurement is available on or before {as_of}; the first cores were taken in July-August "
            "2011. A tPAH scenario must start from a compatible measurement, so no future curve is drawn.")


def baseline_problem(half_life) -> str:
    if half_life is None:
        return ""
    if isinstance(half_life, bool) or not isinstance(half_life, (int, float)) or not math.isfinite(half_life) or half_life <= 0:
        return "The half-life must be a positive, finite number of years. Enter one, or hold the concentration."
    return ""


def problem(effect: PahEffect, anchor: Anchor, scenario_end: dt.date) -> str:
    """A plain-language reason the treatment assumption cannot be applied, or ''."""
    r = effect.reduction_percent
    if r is None:
        return ""
    if isinstance(r, bool) or not isinstance(r, (int, float)) or not math.isfinite(r) or not (0.0 <= r <= 100.0):
        return "The reduction must be between 0% and 100% of the soil tPAH concentration."
    if effect.date <= anchor.starts:
        return f"The intervention must be after the last measurement ({anchor.survey_period}, curve from {anchor.starts:%d %b %Y})."
    if effect.date > scenario_end:
        return "The intervention falls after the scenario end date. Move the end date later or the intervention earlier."
    if not (effect.basis or "").strip():
        return f"Record the basis for the reduction (for example '{DEFAULT_BASIS}')."
    return ""


def concentration(t: float, t0: float, c0: float, half_life: float | None) -> float:
    return c0 if half_life is None else c0 * 2.0 ** (-(t - t0) / half_life)


@dataclass
class PahWhatIf:
    frame: pd.DataFrame
    anchor: Anchor
    half_life: float | None
    effect: PahEffect | None
    has_treatment: bool
    message: str

    def row(self, date: dt.date, sample: str | None = None) -> pd.Series:
        f = self.frame[self.frame.date == date.isoformat()]
        if sample:
            f = f[f["sample"] == sample]
        return f.iloc[-1]


def two_arms(anchor: Anchor, end: dt.date, cadence: str, half_life: float | None, effect: PahEffect | None) -> PahWhatIf:
    """Both arms on one grid: the cadence plus the exact intervention date, which carries a 'before' and an 'after' row."""
    bad = baseline_problem(half_life)
    if bad:
        raise ValueError(bad)
    why = "" if effect is None else problem(effect, anchor, end)
    active = effect is not None and effect.reduction_percent is not None and not why
    if effect is None or effect.reduction_percent is None:
        why = why or "No treatment curve: enter an assumed reduction to draw one."
    t0 = decimal_year(anchor.starts)
    keep = 1.0 - float(effect.reduction_percent) / 100.0 if active else 1.0
    rows = []
    extra = (effect.date,) if active and anchor.starts < effect.date < end else ()
    for d in P.sample_dates(anchor.starts, end, cadence, extra):
        t = decimal_year(d)
        nat = concentration(t, t0, anchor.value, half_life)
        kind = "anchor" if d == anchor.starts else "end_date" if d == end else "regular"
        if active and d == effect.date:
            rows.append({"date": d.isoformat(), "decimal_year": t, "sample": "intervention_before", "natural_mgkg": nat,
                         "treatment_mgkg": nat, "difference_mgkg": 0.0})
            kind = "intervention_after"
        row = {"date": d.isoformat(), "decimal_year": t, "sample": kind, "natural_mgkg": nat}
        if active:
            treated = nat * keep if d >= effect.date else nat
            row.update(treatment_mgkg=treated, difference_mgkg=treated - nat + 0.0)    # + 0.0 turns -0.0 into 0.0
        rows.append(row)
    return PahWhatIf(pd.DataFrame(rows), anchor, half_life, effect, active, "" if active else why)


def summary_text(w: PahWhatIf, end: dt.date) -> str:
    last = w.frame.iloc[-1]
    rule = "held" if w.half_life is None else f"half-life {w.half_life:g} years"
    if not w.has_treatment:
        return (f"Natural recovery scenario ({rule}): {last.natural_mgkg:.1f} mg/kg by {end:%d %b %Y}, from "
                f"{w.anchor.value:.1f} mg/kg measured in {w.anchor.survey_period}.")
    b, a = w.row(w.effect.date, "intervention_before"), w.frame[w.frame.date == w.effect.date.isoformat()].iloc[-1]
    diff = float(last.difference_mgkg)
    tail = ("The two arms are identical (0.0 mg/kg difference)." if abs(diff) < 0.05 else
            f"{abs(diff):.1f} mg/kg {'lower' if diff < 0 else 'higher'} under your assumption.")
    return (f"At the intervention ({w.effect.date:%d %b %Y}): {b.treatment_mgkg:.1f} mg/kg before, {a.treatment_mgkg:.1f} mg/kg "
            f"after a {w.effect.reduction_percent:g}% reduction. By {end:%d %b %Y}: natural recovery {last.natural_mgkg:.1f} mg/kg; "
            f"treatment scenario {last.treatment_mgkg:.1f} mg/kg. {tail}")


def export_rows(observations: pd.DataFrame, w: PahWhatIf, option_label: str) -> pd.DataFrame:
    """Observed surveys on their recorded dates, then each arm by date, with a running order so a chart keeps the before/after
    rows at the intervention in sequence. Shared by the chart and both CSV writers."""
    rows, seq = [], 0
    obs = observations.loc[observations.available_at_as_of].sort_values("decimal_year")
    for _, o in obs.iterrows():
        seq += 1
        rows.append({"order": seq, "date": o.date, "date_precision": o.date_precision, "plot_date": o.available_from,
                     "survey_period": o.survey_period, "series": "Observed (untreated plots)", "arm": "observed",
                     "soil_tpah": float(o["value"]), "unit": UNIT, "difference_from_natural": None, "interval_lo": o.interval_lo,
                     "interval_hi": o.interval_hi, "interval_method": o.interval_method, "n_plots": int(o.n_plots),
                     "sampling_depth": o.sampling_depth, "analyte": o.analyte, "sample": "survey",
                     "record_type": "observed_group_mean", "record_class": "observation", "origin": "derived",
                     "status_label": "field measurement (published group mean)", "evidence_id": o.evidence_id})
    label = baseline_label(w.half_life)
    for _, r in w.frame.iterrows():
        seq += 1
        anchor = r["sample"] == "anchor"
        kind = ({"record_type": "observed_anchor", "record_class": "observation"} if anchor else
                {"record_type": "conditional_projection", "record_class": "conditional_projection"})
        common = {"order": seq, "date": r["date"], "date_precision": "day", "plot_date": r["date"], "survey_period": None,
                  "unit": UNIT, "interval_lo": None, "interval_hi": None, "interval_method": None, "n_plots": w.anchor.n_plots,
                  "sampling_depth": w.anchor.depth, "analyte": w.anchor.analyte, "sample": r["sample"], **kind,
                  "evidence_id": "zengel2015_s1_group_means"}
        if r["sample"] != "intervention_after":       # the natural arm has one value per date
            rows.append({**common, "series": label, "arm": NATURAL_ARM, "soil_tpah": r["natural_mgkg"],
                         "difference_from_natural": 0.0 if w.has_treatment else None, "origin": "derived",
                         "status_label": "observed anchor" if anchor else label})
        if w.has_treatment:
            rows.append({**common, "series": f"{WHATIF_LABEL}: {option_label}", "arm": TREATMENT_ARM,
                         "soil_tpah": r["treatment_mgkg"], "difference_from_natural": r["difference_mgkg"],
                         "origin": "user_assumption",
                         "status_label": "observed anchor (shared by both arms)" if anchor else WHATIF_LABEL})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------------
# Spec version 2 (shared by the dashboard download and the CLI replay)

def half_life_from_spec(spec) -> float | None:
    a = spec.assumption("tpah_half_life") if hasattr(spec, "assumption") else None
    return None if a is None else a.value


def effect_from_spec(spec) -> PahEffect | None:
    e = getattr(spec, "treatment_effect", None)
    if e is None:
        return None
    return PahEffect(spec.technique, dt.date.fromisoformat(e["intervention_date"]), float(e["reduction_percent"]),
                     e.get("basis", ""), e.get("source") or WHATIF_LABEL)


@dataclass
class Computed:
    what: PahWhatIf
    rows: pd.DataFrame
    applied: bool
    screening_allows: bool
    screening_reason: str
    label: str


def compute(spec, observations: pd.DataFrame, half_life: float | None, effect: PahEffect | None, screening_row) -> Computed:
    """Both arms and their export rows. The effect is applied only when the live screening row allows a what-if."""
    from src.shoreline_remediation.projections.whatif import technique_label
    anchor = anchor_from(observations)
    if anchor is None:
        raise ValueError(no_anchor_reason(spec.as_of))
    allows = bool(screening_row is not None and getattr(screening_row, "what_if_allowed", False)
                  and getattr(screening_row, "endpoint", "") == ENDPOINT)
    reason = (getattr(screening_row, "what_if_reason", "") if screening_row is not None
              else "the technique could not be screened for this assessment")
    what = two_arms(anchor, spec.end, spec.cadence, half_life, effect if allows else None)
    label = technique_label(getattr(spec, "technique", "") or (effect.option if effect else ""))
    return Computed(what, export_rows(observations, what, label), what.has_treatment, allows, reason, label)


def observation_spec(group_id: str = "untreated_heavy", as_of: str = AS_OF):
    """A version-1 observed_record/1 spec for a plot group's soil tPAH (input to the existing loader)."""
    from src.shoreline_remediation.projections import catalogue as C, spec as S
    group = C.SITES["bay_jimmy_zengel_plots"].plot_groups[group_id]
    return S.from_dict({
        "schema_version": C.SCHEMA_VERSION, "scenario_id": f"bay_jimmy_{group_id}_tpah", "site_id": "bay_jimmy_zengel_plots",
        "plot_group_id": group_id, "habitat": "salt_marsh", "oiling_class": "Heavy", "endpoint": ENDPOINT, "unit": UNIT,
        "arm": group.arm, "as_of": as_of, "end_date": "2100-01-01", "cadence": "annual", "model_version": "observed_record/1",
        "seed": 20261120, "evidence_ids": list(C.SUPPORTED[("observed_record/1", ENDPOINT)]), "assumptions": []})


def spec_dict(as_of: str, end: dt.date, cadence: str, technique: str, context: dict, half_life: float | None,
              effect: PahEffect | None) -> dict:
    """A version-2 tPAH scenario (inputs only)."""
    from src.shoreline_remediation.projections import catalogue as C
    from src.shoreline_remediation.projections.whatif import technique_label
    return {
        "schema_version": C.SCHEMA_VERSION_2, "scenario_id": "bay_jimmy_dashboard_tpah_whatif",
        "description": (f"{WHATIF_LABEL} for {technique_label(technique).lower()}: soil tPAH (0-10 cm cores) of one hypothetical "
                        f"shoreline. Baseline: {baseline_label(half_life).split(': ')[1]}. Treatment: a user-entered one-time "
                        "reduction in soil concentration. Not a forecast."),
        "site_id": "bay_jimmy_zengel_plots", "plot_group_id": "untreated_heavy", "habitat": "salt_marsh", "oiling_class": "Heavy",
        "endpoint": ENDPOINT, "unit": UNIT, "arm": "reference", "as_of": as_of, "end_date": end.isoformat(), "cadence": cadence,
        "model_version": TPAH_MODEL, "seed": 20261120, "evidence_ids": list(C.SUPPORTED[(TPAH_MODEL, ENDPOINT)]),
        "assumptions": [] if half_life is None else [{
            "assumption_id": "tpah_half_life", "value": half_life, "unit": "yr", "origin": "user_assumption",
            "source": "Bay Jimmy Assessment tPAH controls (zero long-term background assumed)"}],
        "technique": technique, "assessment_context": dict(context),
        "treatment_effect": None if effect is None or effect.reduction_percent is None else {
            "intervention_date": effect.date.isoformat(), "reduction_percent": effect.reduction_percent,
            "unit": REDUCTION_UNIT, "basis": effect.basis, "origin": "user_assumption", "source": effect.source},
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
    if summary:
        last = computed.what.frame.iloc[-1]
        recomputed = {"natural_mgkg": float(last.natural_mgkg)}
        if computed.applied:
            recomputed.update(treatment_mgkg=float(last.treatment_mgkg), difference_mgkg=float(last.difference_mgkg))
        bad = {k: {"download": summary.get(k), "replay": v} for k, v in recomputed.items()
               if not isinstance(summary.get(k), (int, float)) or CSV_FLOAT_FORMAT % summary[k] != CSV_FLOAT_FORMAT % v}
        if bad:
            out["status"], out["summary_differences"] = "differs", bad
    return out
