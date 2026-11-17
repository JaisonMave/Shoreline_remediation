"""Treatment comparison layer (V5.4 plot-first assessment). No Streamlit, no plotting, no decision authority.

What it does
------------
Prepares ONE set of values that the Assessment figure, the response-options table and the downloadable report all read:
treatment contrasts against untreated oiled plots, each tagged with its outcome, unit, time, comparator, evidence basis and the
screening status the decision pipeline already assigned. It then decides which rows may enter a provisional performance order.

What it does not do
-------------------
It never changes a screening status, harm flag, abstention or recommendation: those are read from the DecisionReport that
decision_pipeline.run_decision() returned. A high estimate is not a recommendation; the order and the recommendation are shown
separately.

Sources of the runtime estimates (verified against the source tables, see docs/V5_4_PLOT_FIRST_HANDOFF.md)
- Vegetation: Zengel et al. (2015) S1 Table, group means and standard errors (treatment_effects.effect_table). The contrast is
  DERIVED from published group means (5 treated plots, 9 untreated), not computed from plot-level values.
- Erosion: Zengel et al. (2022) GRIIDC plot-level erosion rates (treatment_effects.erosion_effects), change from 2005-2010.
Both are 90% Welch t intervals: sampling uncertainty of a difference of group means. Plots were not randomly assigned to cleanup
method, so the contrasts are observational. Only the planting contrast of Zengel et al. (2015) was randomised, and it is an
incremental contrast on a mechanically treated baseline (Spartina cover), so it cannot enter a ranking against untreated plots.

Ranking rules (docs/V5_4_PLOT_FIRST_HANDOFF.md section 4)
- A row is compared only if its habitat, oiling scenario, outcome, unit, time and comparator equal the target's. No conversion
  between units or outcomes is applied anywhere in this module.
- Excluded options are never ranked. Conditional options are ranked only when the report shows their conditions are met; unknown
  is not met. A sequence (planting after mechanical cleanup) needs its prerequisite to be allowed.
- A model estimate (field-calibrated or scenario model) is ranked only with a complete ModelAdmission. No registered model
  qualifies today (NEAREST_CANDIDATE); the path is exercised by a synthetic test and never fed synthetic values at runtime.
- Eligible rows are sorted by the benefit-oriented point estimate; exact ties share a rank; fewer than two eligible rows give no
  rank at all. The order is labelled provisional: no order-stability probability is reported because no meaningful effect
  threshold has a scientific basis here.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from functools import lru_cache

FIELD = "Field comparison"
FIELD_MODEL = "Field-calibrated model"
SCENARIO_MODEL = "Scenario model"
BASES = (FIELD, FIELD_MODEL, SCENARIO_MODEL)
NO_DATA = "No comparative data"
REFERENCE_OPTION = "natural_attenuation"
PROVISIONAL_NOTE = ("Provisional order by point estimate. Pairwise differences between methods were not tested, so overlapping or "
                    "separate intervals do not show that one method is better than another.")
SINGLE_NOTE = "One eligible method has a comparable estimate, so no rank is assigned."
ZENGEL_2015 = "Zengel et al. 2015, PLoS ONE 10(7): e0132324, S1 Table"
ZENGEL_2022 = "Zengel et al. 2022, GRIIDC doi:10.7266/VF524143"
OBSERVATIONAL = "observational: plots were not randomly assigned to cleanup method"


# ---------------------------------------------------------------------------------------------------------------
# Contract

@dataclass(frozen=True)
class Target:
    """The question a ranking answers. Two estimates are comparable only if they answer the same one."""
    key: str
    habitat: str                 # "salt_marsh"
    scenario: str                # SCAT oiling class the evidence covers, e.g. "Heavy"
    outcome: str
    unit: str
    time: str
    comparator: str
    higher_is_better: bool
    title: str                   # plot title stem
    axis: str                    # x-axis title: quantity, unit and direction of benefit
    digits: int = 1
    unit_short: str = ""
    axis_short: str = ""         # short x-axis title that fits a narrow screen
    scenario_label: str = "heavily oiled salt marsh"

    @property
    def benefit_label(self) -> str:
        return "Right of zero is better" if self.higher_is_better else "Left of zero is better"


@dataclass(frozen=True)
class ModelAdmission:
    """The five checks a theory-based estimate must pass before it may be ranked beside a field estimate."""
    same_target: bool                 # 1. same outcome, unit, time and counterfactual for the assessed scenario
    explicit_pathway: bool            # 2. the path from treatment to this outcome is modelled explicitly
    discrepancy_documented: bool      # 3. parameter ranges and model discrepancy documented and inside the interval
    evaluation_independent: bool      # 4. evaluated on data that did not calibrate it
    gates_respected: bool             # 5. failed gates and scope limits do not cover this use
    shared_sources: tuple = ()        # source keys that also inform a field estimate (not independent support)
    note: str = ""

    def failed(self) -> list:
        names = {"same_target": "same outcome, unit, time and counterfactual", "explicit_pathway": "explicit treatment-to-outcome pathway",
                 "discrepancy_documented": "documented parameter ranges and model discrepancy",
                 "evaluation_independent": "evaluation independent of calibration", "gates_respected": "no failed gate or scope limit on this use"}
        return [text for key, text in names.items() if not getattr(self, key)]

    @property
    def ok(self) -> bool:
        return not self.failed()


@dataclass(frozen=True)
class Estimate:
    """One contrast as its source reports it, before any screening."""
    option: str                       # decision-pipeline option code
    label: str
    group: str                        # plain phrase for the treated group, e.g. "manually treated plots"
    habitat: str
    scenario: str
    outcome: str
    unit: str
    time: str
    comparator: str
    estimate: float | None
    lo: float | None
    hi: float | None
    interval_level: float | None
    interval_type: str
    basis: str                        # one of BASES
    design: str
    derivation: str                   # how the number was obtained from the source
    source: str
    source_keys: tuple = ()
    interpretation: str = "treatment"   # "treatment", "sequence" (several steps against untreated) or "incremental"
    prerequisite: str | None = None     # option code that must be allowed for a sequence
    admission: ModelAdmission | None = None
    n_treated: int | None = None
    n_comparator: int | None = None
    synthetic: bool = False

    @property
    def has_value(self) -> bool:
        return _finite(self.estimate)


@dataclass(frozen=True)
class Row:
    """An Estimate with the screening status of the report and the ranking decision."""
    est: Estimate
    screening: str                    # report recommendation_category, or "" when the report has no row
    screening_label: str
    applicability: str
    conditions: str                   # "met", "unmet", "unknown", "not_required" or "n/a"
    eligible: bool
    reason: str                       # why the row is not ranked; empty when eligible
    on_target: bool                   # same question as the target (it may still be ineligible)
    shown: bool = False               # drawn in the primary figure: a value on target, applicable, allowed by screening
    benefit: float | None = None      # estimate oriented so that larger is better
    rank: int | None = None
    tied: bool = False

    @property
    def option(self) -> str:
        return self.est.option


@dataclass
class Comparison:
    target: Target
    rows: list = field(default_factory=list)
    applicable: bool = True           # the run's habitat and oiling class are the ones the evidence covers
    applicability: str = ""
    shared_sources: list = field(default_factory=list)   # (model option, field option, source key)

    @property
    def eligible(self) -> list:
        return sorted((r for r in self.rows if r.eligible), key=lambda r: (-r.benefit, r.est.label))

    @property
    def mode(self) -> str:
        """'ranking' (two or more eligible), 'single' (one) or 'none'."""
        n = len(self.eligible)
        return "ranking" if n >= 2 else "single" if n == 1 else "none"

    @property
    def title(self) -> str:
        t = self.target
        if self.mode == "ranking":
            return f"{t.title}: provisional order of eligible methods"
        return f"{t.title}: comparison with natural recovery"

    @property
    def order_note(self) -> str:
        return PROVISIONAL_NOTE if self.mode == "ranking" else SINGLE_NOTE if self.mode == "single" else ""

    def row_for(self, option: str) -> Row | None:
        """The on-target row of an option (the one the options table quotes), or None."""
        return next((r for r in self.rows if r.option == option and r.on_target), None)

    @property
    def shown(self) -> list:
        """Rows drawn in the primary figure, best first. Eligible rows plus allowed rows whose conditions are not established
        (those are drawn and labelled, never ranked). Excluded options and off-target contrasts are not drawn."""
        return sorted((r for r in self.rows if r.shown), key=lambda r: (-r.benefit, r.est.label))

    @property
    def historical(self) -> list:
        """Rows with a value that are not ranked: context for the evidence detail, never part of the order."""
        return [r for r in self.rows if not r.eligible and r.est.has_value]


def _finite(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))


# ---------------------------------------------------------------------------------------------------------------
# Targets

VEG_YEAR2 = Target(
    key="veg_cover_year2", habitat="salt_marsh", scenario="Heavy", outcome="total vegetation cover", unit="percentage points",
    time="year 2 after oiling (2012 survey)", comparator="untreated oiled plots", higher_is_better=True,
    title="Total vegetation cover at year 2",
    axis="Difference in total vegetation cover from untreated oiled plots, percentage points (right of zero = more cover)",
    digits=1, unit_short="points", axis_short="Percentage points (right of zero = more cover)")
EROSION_2010_2012 = Target(
    key="erosion_2010_2012", habitat="salt_marsh", scenario="Heavy", outcome="marsh-edge erosion rate, change from 2005-2010",
    unit="m/yr", time="2010-2012", comparator="untreated oiled plots", higher_is_better=False,
    title="Marsh-edge erosion rate, 2010 to 2012",
    axis="Difference in erosion-rate change from untreated oiled plots, m/yr (left of zero = less erosion)", digits=2, unit_short="m/yr",
    axis_short="m/yr (left of zero = less erosion)")
EROSION_2012_2018 = replace(EROSION_2010_2012, key="erosion_2012_2018", time="2012-2018", title="Marsh-edge erosion rate, 2012 to 2018")
TARGETS = {t.key: t for t in (VEG_YEAR2, EROSION_2010_2012, EROSION_2012_2018)}
TARGET_LABELS = {"veg_cover_year2": "Vegetation cover, year 2", "erosion_2010_2012": "Edge erosion, 2010 to 2012",
                 "erosion_2012_2018": "Edge erosion, 2012 to 2018"}


# ---------------------------------------------------------------------------------------------------------------
# Runtime estimates: read from the source tables through the existing treatment-effect helpers. Nothing is typed in here.

_VEG_GROUPS = (("manual_removal", "Manual removal", "manually treated plots", "Manual Treatment"),
               ("mechanical_removal", "Mechanical removal", "mechanically treated plots", "Mechanical Treatment"))
PLANTING = "planting (after mechanical cleanup)"
_ERO_GROUPS = (("manual_removal", "Manual removal", "manually treated plots", "manual", "treatment", None),
               ("mechanical_removal", "Mechanical removal", "mechanically treated plots", "mechanical", "treatment", None),
               (PLANTING, "Mechanical removal, then planting", "mechanically treated and planted plots", "mechanical+planting", "sequence",
                "mechanical_removal"))


@lru_cache(maxsize=1)
def _effect_table():
    from src.shoreline_remediation import treatment_effects as te
    return te.effect_table(), te.load()


@lru_cache(maxsize=4)
def _erosion_table(period: str):
    from src.shoreline_remediation import treatment_effects as te
    return te.erosion_effects(period)


def vegetation_year2_estimates() -> list:
    """Zengel et al. (2015), 2012 survey. Manual and mechanical against untreated oiled plots (total vegetation cover), and the
    planting contrast exactly as the source reports it: Spartina cover, planted against unplanted, both mechanically treated."""
    table, raw = _effect_table()
    n = raw[(raw.study == "main") & (raw.year == 2012) & (raw.metric == "Total Vegetation Cover (%)")].set_index("treatment")["n"]
    out = []
    for option, label, group, name in _VEG_GROUPS:
        r = table[(table.comparison == f"{name} vs No Treatment") & (table.year == 2012) & (table.metric == "Total Vegetation Cover (%)")]
        if r.empty:
            continue
        r = r.iloc[0]
        out.append(Estimate(option, label, group, "salt_marsh", "Heavy", VEG_YEAR2.outcome, VEG_YEAR2.unit, VEG_YEAR2.time,
                            VEG_YEAR2.comparator, float(r.effect), float(r.lo), float(r.hi), 0.90,
                            "Welch t interval (sampling uncertainty of a difference of group means)", FIELD, OBSERVATIONAL,
                            "derived from published group means and standard errors, not from plot-level values",
                            ZENGEL_2015 + "; Bay Jimmy, northern Barataria Bay", ("zengel2015",), "treatment", None, None,
                            int(n.get(name, 0)) or None, int(n.get("No Treatment", 0)) or None))
    p = table[(table.comparison == "Planting vs no planting (after mechanical)") & (table.metric == "Spartina alterniflora Cover (%)")]
    if not p.empty:
        p = p.iloc[0]
        out.append(Estimate(PLANTING, "Planting after mechanical removal", "planted plots", "salt_marsh", "Heavy",
                            "Spartina alterniflora cover", "percentage points", VEG_YEAR2.time, "mechanically treated, unplanted plots",
                            float(p.effect), float(p.lo), float(p.hi), 0.90,
                            "Welch t interval (sampling uncertainty of a difference of group means)", FIELD,
                            "randomised: planting assigned at random within mechanically treated areas",
                            "derived from published group means and standard errors, not from plot-level values",
                            ZENGEL_2015 + "; Bay Jimmy, northern Barataria Bay", ("zengel2015",), "incremental", "mechanical_removal",
                            None, 5, 5))
    return out


def erosion_estimates(period: str) -> list:
    """Zengel et al. (2022) plot-level erosion rates: change from 2005-2010 to `period`, each group minus untreated oiled plots."""
    target = TARGETS[f"erosion_{period.replace('-', '_')}"]
    table = _erosion_table(period).set_index("treatment")
    out = []
    for option, label, group, name, interpretation, prerequisite in _ERO_GROUPS:
        if name not in table.index:
            continue
        r = table.loc[name]
        out.append(Estimate(option, label, group, "salt_marsh", "Heavy", target.outcome, target.unit, target.time, target.comparator,
                            float(r.extra_erosion_vs_untreated), float(r.lo), float(r.hi), 0.90,
                            "Welch t interval (sampling uncertainty of a difference of group means)", FIELD, OBSERVATIONAL,
                            "computed from plot-level aerial-photograph erosion rates",
                            ZENGEL_2022 + "; Bay Jimmy, northern Barataria Bay", ("zengel2022",), interpretation, prerequisite, None,
                            int(r.n), int(r.n_untreated)))
    return out


def runtime_estimates(target_key: str) -> list:
    """Every estimate the platform holds for a target. Field comparisons only: no registered model is admitted (NEAREST_CANDIDATE)."""
    if target_key == VEG_YEAR2.key:
        rows = vegetation_year2_estimates()
    elif target_key in (EROSION_2010_2012.key, EROSION_2012_2018.key):
        rows = erosion_estimates(TARGETS[target_key].time)
    else:
        raise KeyError(target_key)
    if any(r.synthetic for r in rows):      # defensive: synthetic values exist only in tests
        raise ValueError("synthetic estimate in runtime results")
    return rows


# ---------------------------------------------------------------------------------------------------------------
# Screening status of the report (read only)

_FAVOURABLE = ("helps", "may help", "less harm")
_ADVERSE = ("harms", "no benefit")


def _get(obj, key, default=None):
    value = obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)
    return default if value is None else value


def report_options(report) -> dict:
    return {str(r.get("option")): r for r in (_get(report, "options", []) or []) if isinstance(r, dict)}


def conditions_state(row: dict) -> tuple:
    """(state, detail) for one report option row. State: 'not_required' (the pipeline recommends it, or the screening rule is
    'eligible' and it is not conditional), 'met', 'unmet' or 'unknown'. Condition strings are the pipeline's own
    'text -> effect [status]' lines; a line that cannot be read counts as unknown. Unknown is never treated as met."""
    category = str(row.get("recommendation_category") or "")
    if category == "recommended" or (category != "conditional" and str(row.get("rule_verdict") or "") == "eligible"):
        return "not_required", ""
    lines = [str(c) for c in row.get("conditions") or []]
    if not lines:
        return "unknown", str(row.get("recommendation_category_reason") or "conditions are not stated for this scenario")
    state, detail = "met", ""
    for line in lines:
        body, _, status = line.rpartition("[")
        status = status.rstrip("] ").lower()
        text, _, effect = body.rpartition("->")
        effect = effect.strip().lower()
        favourable = any(effect.startswith(x) for x in _FAVOURABLE)
        adverse = any(effect.startswith(x) for x in _ADVERSE)
        if status.startswith("unknown") or not (favourable or adverse) or not (status.startswith("met") or status.startswith("not met")):
            if state != "unmet":
                state, detail = "unknown", text.strip() or line
            continue
        is_met = status.startswith("met")
        if (favourable and not is_met) or (adverse and is_met):
            state, detail = "unmet", text.strip()
    return state, detail


def _exclusion_text(row: dict) -> str:
    for x in row.get("exclusion_reasons") or []:
        return str(x.get("detail", x)) if isinstance(x, dict) else str(x)
    return str(row.get("rule_reason") or "")


def _mismatch(est: Estimate, target: Target) -> str:
    if est.habitat != target.habitat:
        return f"Different habitat ({est.habitat.replace('_', ' ')})"
    if est.scenario != target.scenario:
        return f"Different oiling scenario ({est.scenario})"
    if est.outcome != target.outcome:
        return f"Different outcome ({est.outcome}, not {target.outcome})"
    if est.unit != target.unit:
        return f"Different unit ({est.unit}, not {target.unit})"
    if est.time != target.time:
        return f"Different time ({est.time}, not {target.time})"
    if est.comparator != target.comparator or est.interpretation == "incremental":
        return f"Different comparator ({est.comparator}): an incremental contrast cannot stand in for a contrast with {target.comparator}"
    return ""


def compare(target: Target, estimates: list, report, habitat: str, oiling: str | None, applicability: str = "") -> Comparison:
    """Screen `estimates` against the report and order the eligible ones. `habitat` and `oiling` describe the assessed scenario
    ("salt_marsh", SCAT class). The report is read, never changed."""
    opts = report_options(report)
    applicable = habitat == target.habitat and oiling == target.scenario
    why_not = "" if applicable else (f"The field evidence covers {target.scenario_label} only; this scenario is "
                                     f"{habitat.replace('_', ' ')}" + (f", {str(oiling).replace('_', ' ').lower()} oiling" if oiling else "") + ".")
    rows = []
    for est in estimates:
        if est.basis not in BASES:
            raise ValueError(f"unknown evidence basis: {est.basis}")
        rep = opts.get(est.option)
        category = str(rep.get("recommendation_category") or "") if rep else ""
        label = str(rep.get("recommendation_category_label") or category.replace("_", " ")) if rep else "No screening status"
        mismatch = _mismatch(est, target)
        cond, cond_detail = conditions_state(rep) if rep else ("n/a", "")
        reason = ""
        if est.option == REFERENCE_OPTION:
            reason = "Reference: the zero of the effect scale"
        elif not est.has_value:
            reason = NO_DATA
        elif mismatch:
            reason = mismatch
        elif not applicable:
            reason = why_not
        elif est.basis != FIELD and (est.admission is None or not est.admission.ok):
            failed = est.admission.failed() if est.admission else ["a model admission record"]
            reason = "Model estimate not admitted: lacks " + "; ".join(failed)
        elif rep is None:
            reason = "The assessment lists no screening status for this option"
        elif category == "excluded":
            reason = "Excluded by screening: " + (_exclusion_text(rep) or "see the exclusion reason")
        elif est.prerequisite and (opts.get(est.prerequisite) is None
                                   or str(opts[est.prerequisite].get("recommendation_category")) == "excluded"):
            reason = f"Requires {est.prerequisite.replace('_', ' ')}, which is excluded for this scenario"
        elif cond == "unmet":
            reason = "Condition not met: " + cond_detail
        elif cond == "unknown":
            reason = "Conditions not established for this scenario: " + cond_detail
        benefit = None
        if est.has_value:
            benefit = float(est.estimate) if target.higher_is_better else -float(est.estimate)
        blocked = reason.startswith(("Reference", NO_DATA, "Model estimate", "The assessment lists", "Excluded by screening", "Requires "))
        shown = est.has_value and not mismatch and applicable and not blocked
        rows.append(Row(est, category, label, applicability or (why_not if not applicable else ""), cond, not reason, reason,
                        not mismatch, shown, benefit))
    comp = Comparison(target, _ranked(rows), applicable, applicability or why_not)
    fields = [r for r in comp.rows if r.eligible and r.est.basis == FIELD]
    for r in comp.rows:
        if r.eligible and r.est.basis != FIELD and r.est.admission:
            for key in r.est.admission.shared_sources:
                comp.shared_sources += [(r.option, f.option, key) for f in fields if key in f.est.source_keys]
    return comp


def _ranked(rows: list) -> list:
    """Assign ranks to eligible rows: sorted by benefit, exact ties share a rank (1, 1, 3). No rank with fewer than two rows."""
    eligible = sorted((r for r in rows if r.eligible), key=lambda r: -r.benefit)
    if len(eligible) < 2:
        return rows
    ranks, values = {}, [r.benefit for r in eligible]
    for i, r in enumerate(eligible):
        rank = i + 1 if i == 0 or r.benefit != eligible[i - 1].benefit else ranks[id(eligible[i - 1])][0]
        ranks[id(r)] = (rank, values.count(r.benefit) > 1)
    return [replace(r, rank=ranks[id(r)][0], tied=ranks[id(r)][1]) if id(r) in ranks else r for r in rows]


def independent_source_count(comp: Comparison) -> int:
    """Number of independent sources behind the eligible rows: a model that shares a source with a field row adds nothing."""
    keys = set()
    for r in comp.eligible:
        own = set(r.est.source_keys) | set(r.est.admission.shared_sources if r.est.admission else ())
        keys |= own or {r.option}
    return len(keys)


# ---------------------------------------------------------------------------------------------------------------
# Text shared by the figure, the table and the report

def fmt_value(row: Row | None, target: Target) -> str:
    """'+34.0 points (90% interval +19.0 to +49.0)' or 'No comparative data'. A missing value is never shown as zero."""
    if row is None or not row.est.has_value:
        return NO_DATA
    e, d = row.est, target.digits
    text = f"{e.estimate:+.{d}f} {target.unit_short or target.unit}"
    if _finite(e.lo) and _finite(e.hi) and e.interval_level:
        text += f" ({e.interval_level:.0%} interval {e.lo:+.{d}f} to {e.hi:+.{d}f})"
    return text


def cell_text(comp: Comparison, option: str) -> str:
    """Options-table cell for one option. A value is quoted only where it applies to the assessed scenario and answers the target."""
    row = comp.row_for(option)
    if option == REFERENCE_OPTION:
        return "Reference (0)"
    if row is None or not row.est.has_value or not comp.applicable:
        return NO_DATA
    if not row.shown:
        return "Not compared here (historical value in Methods and sources)"
    return fmt_value(row, comp.target)


def finding(comp: Comparison) -> str:
    """One literal sentence for the leading eligible row: quantity, direction, unit, comparator, time, interval and design."""
    rows = comp.eligible or comp.shown
    if not rows:
        return ""
    r, t = rows[0], comp.target
    e = r.est
    direction = "higher" if e.estimate > 0 else "lower"
    size = f"{abs(e.estimate):.{0 if t.unit == 'percentage points' else t.digits}f} {t.unit}"
    verb = "was" if e.basis == FIELD else "is estimated to be"
    if t.key == VEG_YEAR2.key:
        lead = f"Total vegetation cover {verb} {size} {direction} in {e.group} than in {t.comparator} at year 2"
    else:
        lead = (f"The change in marsh-edge erosion rate from 2005-2010 to {t.time} {verb} {size} {direction} in {e.group} than in "
                f"{t.comparator}")
    d = 0 if t.unit == "percentage points" else t.digits
    interval = f"{e.interval_level:.0%} interval {e.lo:+.{d}f} to {e.hi:+.{d}f}" if _finite(e.lo) and _finite(e.hi) else "no interval"
    crosses = _finite(e.lo) and _finite(e.hi) and e.lo <= 0.0 <= e.hi
    n = f"; {e.n_treated} treated and {e.n_comparator} untreated plots" if e.n_treated and e.n_comparator else ""
    return f"{lead} ({interval}{', which includes zero' if crosses else ''}{n})."


def design_limit(comp: Comparison) -> str:
    rows = comp.eligible or comp.shown
    if not rows:
        return ""
    e = rows[0].est
    if not rows[0].eligible:
        return ("These are the Bay Jimmy field plots, not this scenario: " + rows[0].reason[:1].lower() + rows[0].reason[1:]
                + ". Observational comparison at one site and one spill.")
    if e.basis != FIELD:
        return f"{e.basis}: not a field measurement."
    return ("Observational comparison at one site and one spill (Bay Jimmy, Deepwater Horizon): plots were not randomly assigned to "
            "cleanup method, so the difference is an association, not a proven effect.")


def source_caption(comp: Comparison) -> str:
    """Compact caption under the figure: interval level and type, basis, design, derivation and source."""
    rows = comp.eligible or comp.shown or [r for r in comp.rows if r.est.has_value and r.on_target]
    if not rows:
        return ""
    e = rows[0].est
    return (f"Dot: point estimate. Bar: {e.interval_level:.0%} {e.interval_type}. Dashed line: zero, no difference from "
            f"{comp.target.comparator}. {comp.target.benefit_label}. Basis: {e.basis.lower()}, {e.design}; {e.derivation}. "
            f"Source: {e.source}.")


def table_records(comp: Comparison) -> list:
    """Plain records of every row (for the evidence detail and the downloadable report): the same values the figure uses."""
    out = []
    for r in comp.rows:
        e = r.est
        out.append({"Method": e.label, "Outcome": e.outcome, "Time": e.time, "Comparator": e.comparator,
                    "Estimate": fmt_value(r, replace(comp.target, unit_short=e.unit if not r.on_target else comp.target.unit_short)),
                    "Evidence basis": e.basis, "Design": e.design, "Source": e.source, "Screening status": r.screening_label,
                    "In the order": ("Rank " + str(r.rank) + (" (tied)" if r.tied else "")) if r.rank else ("Yes, not ranked (single method)" if r.eligible else "No"),
                    "Why not ranked": r.reason})
    return out


def assessment_comparisons(report, habitat: str, oiling: str | None, applicability: str = "") -> dict:
    """{target key: Comparison} for a salt-marsh assessment, built from the runtime estimates. Empty for other habitats: they have
    no comparable treatment contrast, so the screening table is their result."""
    if habitat != "salt_marsh":
        return {}
    return {key: compare(TARGETS[key], runtime_estimates(key), report, habitat, oiling, applicability) for key in TARGETS}


# ---------------------------------------------------------------------------------------------------------------
# Theory-based candidates: audit record (documentation that the UI and the handoff quote; it admits nothing)

@dataclass(frozen=True)
class CandidateAudit:
    model_id: str
    name: str
    admitted: bool
    checks: tuple                    # (check, passed, evidence)
    missing: str


NEAREST_CANDIDATE = CandidateAudit(
    "composer_natural_recovery_v1", "Scenario composer: year-2 vegetation difference for manual removal", False,
    (("Same outcome, unit, time and counterfactual", False,
      "It reports vegetation cover as a ratio to reference-marsh cover (0.35 at year 2), not total cover in percentage points."),
     ("Explicit treatment-to-outcome pathway", False,
      "It has no mechanism: the Zengel et al. (2015) field contrast is divided by the reference cover (95%) and added to the "
      "vegetation curve, then held and decayed by an assumed rule."),
     ("Parameter ranges and model discrepancy documented", False,
      "The 90% field interval is read as a normal distribution (assumed); the vegetation curve it sits on (veg_recovery_v1) is "
      "worse than a no-trend baseline for heavy oiling."),
     ("Calibration and evaluation distinguished", False,
      "Its only input for this outcome is the same Zengel et al. (2015) plots as the field comparison. It is the field estimate in "
      "another unit, not independent support, and no held-out treated plots evaluate it."),
     ("Failed gates and scope limits respected", False,
      "Registry state experimental: the heavy-cell bias gates (R3, D32, V5-0.1) failed for the edge-loss part; the treatment "
      "differences are one site applied unchanged to every heavily oiled cell.")),
    "An independent prediction of total vegetation cover at year 2, in percentage points against untreated oiled plots, from a "
    "model whose treatment-to-cover pathway is evaluated on treated and untreated plots that did not calibrate it (a second site "
    "or spill with both groups). The process model (process_model_v2) is further away: it predicts residual oil, failed its F5 "
    "gate, and has no supported link from residual oil to vegetation cover.")


def plot_records(comp: Comparison) -> list:
    """Records for the dot-and-interval figure, best first: only rows with a finite value that are drawn (Comparison.shown).
    A missing value never becomes a zero: such rows are simply not in this list."""
    out = []
    for r in comp.shown:
        e = r.est
        if not (_finite(e.estimate) and _finite(e.lo) and _finite(e.hi)):
            continue
        name = (f"{r.rank}. " if r.rank else "") + e.label
        status = "" if r.eligible else "not ranked: conditions not established"
        out.append({"option": r.option, "label": name, "basis": e.basis, "status": status,
                    "row": "|".join(x for x in (name, e.basis, status) if x), "estimate": float(e.estimate), "lo": float(e.lo),
                    "hi": float(e.hi), "value_text": f"{e.estimate:+.{comp.target.digits}f} ({e.lo:+.{comp.target.digits}f} to {e.hi:+.{comp.target.digits}f})",
                    "rank": r.rank, "eligible": r.eligible})
    return out
