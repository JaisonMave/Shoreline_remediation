"""Versioned scenario specification for research projections: parsing, validation and scope checks.

Two different failure kinds are kept apart:

- SpecError: the input itself is invalid (wrong type, unit, date order, unknown assumption, non-finite value). Every problem is
  listed with the field path and what to change. Nothing is run.
- Unsupported: the input is well formed but asks for something the evidence does not support (a rocky or mangrove habitat, an
  unknown site, an endpoint not implemented, an ineligible plot group). This is a legitimate outcome and is recorded as such.

A missing value (value null plus a missing_reason) is never the same as a measured zero (value 0.0).
"""
from __future__ import annotations

import datetime as dt
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

from src.shoreline_remediation.projections import catalogue as C


class SpecError(ValueError):
    """Invalid scenario input. `problems` lists (field path, message) pairs."""

    def __init__(self, problems: list):
        self.problems = list(problems)
        super().__init__("Invalid scenario specification:\n" + "\n".join(f"  - {p}: {m}" for p, m in self.problems))


@dataclass(frozen=True)
class Unsupported:
    """A well-formed request the platform declines to project, with a machine-readable code and a reason for people."""
    code: str
    reason: str
    field: str = ""


@dataclass(frozen=True)
class Assumption:
    assumption_id: str
    value: float | str | None          # number, ISO date string (unit "date"), or None when missing
    unit: str
    origin: str
    source: str = ""                   # where the value came from (evidence ID, document, or "owner" for a user choice)
    missing_reason: str = ""


@dataclass(frozen=True)
class ScenarioSpec:
    schema_version: str
    scenario_id: str
    site_id: str
    plot_group_id: str
    habitat: str
    oiling_class: str
    endpoint: str
    unit: str
    arm: str
    as_of: str                          # ISO date: last observation used (later observations are withheld from the anchor)
    end_date: str                       # ISO date: end of the scenario (a planning horizon, never a validated horizon)
    cadence: str
    model_version: str
    seed: int
    evidence_ids: tuple = ()
    assumptions: tuple = ()
    description: str = ""
    demonstration: bool = False         # must be true when any value has origin 'synthetic_fixture'
    comparator_group_id: str = ""       # field_contrast/1 only: the group the plot group is compared with
    # --- spec version 2 only (retreat_whatif/1) ---
    technique: str = ""                 # report option key the what-if is for, re-screened on every run
    assessment_context: dict | None = None   # how to re-run the assessment that screens the technique
    treatment_effect: dict | None = None     # None: no treatment curve (baseline only); rate_change 0: identical arms
    exported_outputs: dict | None = field(default=None, compare=False)   # results saved with a download: outputs, never inputs

    @property
    def version(self) -> int:
        return 2 if self.schema_version == C.SCHEMA_VERSION_2 else 1

    def to_dict(self) -> dict:
        """The canonical inputs (run ID basis). Exported outputs are never part of it."""
        d = asdict(self)
        d["evidence_ids"] = list(self.evidence_ids)
        d["assumptions"] = [asdict(a) for a in self.assumptions]
        d.pop("exported_outputs")
        if not self.comparator_group_id:       # optional field added in Session 4: omitted when unused, so earlier specs and
            d.pop("comparator_group_id")       # their run IDs are unchanged
        if self.version == 1:                  # version-1 dicts, and so their run IDs, are unchanged by version 2
            for k in V2_FIELDS:
                d.pop(k)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, allow_nan=False)

    def assumption(self, assumption_id: str) -> Assumption | None:
        return next((a for a in self.assumptions if a.assumption_id == assumption_id), None)

    @property
    def as_of_date(self) -> dt.date:
        return dt.date.fromisoformat(self.as_of)

    @property
    def end(self) -> dt.date:
        return dt.date.fromisoformat(self.end_date)


_REQUIRED = ("schema_version", "scenario_id", "site_id", "plot_group_id", "habitat", "oiling_class", "endpoint", "unit", "arm",
             "as_of", "end_date", "cadence", "model_version", "seed")
_OPTIONAL = ("evidence_ids", "assumptions", "description", "demonstration", "comparator_group_id")
V2_FIELDS = ("technique", "assessment_context", "treatment_effect")
_V2_OPTIONAL = V2_FIELDS + ("exported_outputs",)
CONTEXT_KEYS = {"entry": str, "cell": str, "habitat": str, "oil": (str, type(None)), "season": (str, type(None)),
                "n_draws": int, "site_sha256": str}
EFFECT_KEYS = ("intervention_start", "effect_end", "rate_change", "unit", "origin", "source")      # retreat_whatif/1
COVER_EFFECT_KEYS = ("intervention_start", "effect_peak", "effect_end", "peak_change", "unit", "origin", "source")  # cover_whatif/1
TPAH_EFFECT_KEYS = ("intervention_date", "reduction_percent", "unit", "basis", "origin", "source")                # tpah_whatif/1
# model -> (effect keys, date keys in order, value key, unit, what the value means)
_EFFECTS = {
    C.WHATIF_MODEL: (EFFECT_KEYS, ("intervention_start", "effect_end"), "rate_change", "m/yr",
                     "a finite number in m/yr (negative = slower retreat)"),
    C.COVER_WHATIF_MODEL: (COVER_EFFECT_KEYS, ("intervention_start", "effect_peak", "effect_end"), "peak_change",
                           "percentage points", "a finite number in percentage points (negative = less cover)"),
    C.TPAH_WHATIF_MODEL: (TPAH_EFFECT_KEYS, ("intervention_date",), "reduction_percent", "percent of soil tPAH concentration",
                          "a finite number from 0 to 100 (percent of the soil tPAH concentration removed)"),
}
_ASSUMPTION_KEYS = ("assumption_id", "value", "unit", "origin", "source", "missing_reason")


def _is_number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _date(problems: list, path: str, value) -> dt.date | None:
    if not isinstance(value, str):
        problems.append((path, f"expected an ISO date string 'YYYY-MM-DD', got {type(value).__name__}"))
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        problems.append((path, f"'{value}' is not an ISO date 'YYYY-MM-DD'"))
        return None


def _assumption(problems: list, i: int, raw) -> Assumption | None:
    path = f"assumptions[{i}]"
    if not isinstance(raw, dict):
        problems.append((path, "each assumption must be an object"))
        return None
    for k in sorted(set(raw) - set(_ASSUMPTION_KEYS)):
        problems.append((f"{path}.{k}", f"unknown key; allowed: {', '.join(_ASSUMPTION_KEYS)}"))
    aid = raw.get("assumption_id")
    if aid not in C.ASSUMPTIONS:
        problems.append((f"{path}.assumption_id", f"unknown assumption '{aid}'; known: {', '.join(sorted(C.ASSUMPTIONS))}"))
        return None
    adef = C.ASSUMPTIONS[aid]
    unit, origin, value = raw.get("unit"), raw.get("origin"), raw.get("value", None)
    if "value" not in raw:
        problems.append((f"{path}.value", "required; use null with a missing_reason if the value is not available (0 means zero)"))
    if unit != adef.unit:
        problems.append((f"{path}.unit", f"'{aid}' must be given in '{adef.unit}', got '{unit}' (no unit conversion is done)"))
    if origin not in C.ORIGINS:
        problems.append((f"{path}.origin", f"'{origin}' is not one of {', '.join(C.ORIGINS)}"))
    missing_reason = raw.get("missing_reason", "") or ""
    if value is None:
        if not missing_reason:
            problems.append((f"{path}.missing_reason", "a null value needs a missing_reason (a measured zero is written as 0)"))
    elif missing_reason:
        problems.append((f"{path}.missing_reason", "only allowed when value is null"))
    elif adef.unit == "date":
        _date(problems, f"{path}.value", value)
    elif not _is_number(value):
        problems.append((f"{path}.value", f"expected a number in {adef.unit}, got {type(value).__name__}"))
    elif not math.isfinite(value):
        problems.append((f"{path}.value", "must be finite"))
    if origin in ("observation", "literature", "fitted_parameter", "derived") and not raw.get("source"):
        problems.append((f"{path}.source", f"origin '{origin}' needs a source (evidence ID or document)"))
    return Assumption(aid, float(value) if _is_number(value) else value, unit, origin, raw.get("source", "") or "", missing_reason)


def from_dict(raw: dict) -> ScenarioSpec:
    """Parse and validate a scenario. Raises SpecError listing every problem found."""
    if not isinstance(raw, dict):
        raise SpecError([("(root)", "the scenario must be a JSON object")])
    problems: list = []
    for k in _REQUIRED:
        if k not in raw:
            problems.append((k, "required field is missing"))
    v2 = raw.get("schema_version") == C.SCHEMA_VERSION_2
    allowed = _REQUIRED + _OPTIONAL + (_V2_OPTIONAL if v2 else ())
    for k in sorted(set(raw) - set(allowed)):
        hint = " (a version-2 field: use schema_version 'shoreline-projection-spec/2')" if k in _V2_OPTIONAL else ""
        problems.append((k, "unknown field (check spelling); allowed: " + ", ".join(allowed) + hint))
    if raw.get("schema_version", C.SCHEMA_VERSION) not in C.SCHEMA_VERSIONS:
        problems.append(("schema_version", f"'{raw.get('schema_version')}' is not supported; expected one of "
                         + ", ".join(C.SCHEMA_VERSIONS)))
    for k in ("scenario_id", "site_id", "plot_group_id", "habitat", "oiling_class", "endpoint", "unit", "arm", "cadence",
              "model_version"):
        if k in raw and (not isinstance(raw[k], str) or not raw[k].strip()):
            problems.append((k, "must be a non-empty string"))
    if raw.get("arm") is not None and raw.get("arm") not in C.ARMS:
        problems.append(("arm", f"'{raw.get('arm')}' is not one of {', '.join(C.ARMS)}"))
    if "cadence" in raw and raw["cadence"] not in C.CADENCES:
        problems.append(("cadence", f"'{raw['cadence']}' is not one of {', '.join(C.CADENCES)}"))
    if "model_version" in raw and raw["model_version"] not in C.MODELS:
        problems.append(("model_version", f"'{raw['model_version']}' is not available; known: {', '.join(C.MODELS)}"))
    if "seed" in raw and not (isinstance(raw["seed"], int) and not isinstance(raw["seed"], bool) and raw["seed"] >= 0):
        problems.append(("seed", "must be a non-negative integer"))
    a = _date(problems, "as_of", raw["as_of"]) if "as_of" in raw else None
    e = _date(problems, "end_date", raw["end_date"]) if "end_date" in raw else None
    if a and e and e <= a:
        problems.append(("end_date", f"{e} must be after as_of {a}"))
    ev = raw.get("evidence_ids", [])
    if not isinstance(ev, list) or not all(isinstance(x, str) for x in ev):
        problems.append(("evidence_ids", "must be a list of evidence ID strings"))
        ev = []
    for x in ev:
        if x not in C.EVIDENCE:
            problems.append(("evidence_ids", f"unknown evidence ID '{x}'; known: {', '.join(sorted(C.EVIDENCE))}"))
    raw_as = raw.get("assumptions", [])
    if not isinstance(raw_as, list):
        problems.append(("assumptions", "must be a list"))
        raw_as = []
    assumptions = [_assumption(problems, i, r) for i, r in enumerate(raw_as)]
    ids = [x.assumption_id for x in assumptions if x]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        problems.append(("assumptions", f"'{dup}' is given more than once"))
    demo = raw.get("demonstration", False)
    if not isinstance(demo, bool):
        problems.append(("demonstration", "must be true or false"))
    if any(x and x.origin == "synthetic_fixture" for x in assumptions) and demo is not True:
        problems.append(("demonstration", "values with origin 'synthetic_fixture' are only allowed when demonstration is true"))
    comparator = raw.get("comparator_group_id", "")
    if not isinstance(comparator, str):
        problems.append(("comparator_group_id", "must be a plot group ID string"))
    model = raw.get("model_version")
    if v2:
        _v2_problems(problems, raw)
    elif model == C.WHATIF_MODEL:
        problems.append(("model_version", f"'{C.WHATIF_MODEL}' needs schema_version '{C.SCHEMA_VERSION_2}'"))
    elif model in (C.COVER_WHATIF_MODEL, C.TPAH_WHATIF_MODEL):
        problems.append(("model_version", f"'{model}' needs schema_version '{C.SCHEMA_VERSION_2}'"))
    if problems:
        raise SpecError(problems)
    exported = raw.get("exported_outputs")
    return ScenarioSpec(raw["schema_version"], raw["scenario_id"], raw["site_id"], raw["plot_group_id"], raw["habitat"],
                        raw["oiling_class"], raw["endpoint"], raw["unit"], raw["arm"], raw["as_of"], raw["end_date"], raw["cadence"],
                        raw["model_version"], raw["seed"], tuple(ev), tuple(assumptions), raw.get("description", ""), demo,
                        comparator, raw.get("technique", "") if v2 else "", raw.get("assessment_context") if v2 else None,
                        raw.get("treatment_effect") if v2 else None, exported if v2 else None)


def _v2_problems(problems: list, raw: dict) -> None:
    """Version-2 inputs: one technique, the assessment that screens it, and an optional user-defined treatment effect.
    A blank effect is written as null (or omitted): baseline only. An entered zero is rate_change 0: identical arms."""
    model = raw.get("model_version")
    if model not in C.WHATIF_MODELS:
        problems.append(("model_version", "spec version 2 is used only with " + ", ".join(f"'{m}'" for m in C.WHATIF_MODELS)))
    elif raw.get("endpoint") != C.WHATIF_MODELS[model]:
        problems.append(("endpoint", f"'{model}' is defined for {C.WHATIF_MODELS[model]} only"))
    for k in V2_FIELDS[:2]:
        if k not in raw:
            problems.append((k, "required in spec version 2"))
    t = raw.get("technique")
    if "technique" in raw and (not isinstance(t, str) or not t.strip()):
        problems.append(("technique", "must be the report option key, for example 'manual_removal'"))
    ctx = raw.get("assessment_context")
    if "assessment_context" in raw:
        if not isinstance(ctx, dict):
            problems.append(("assessment_context", "must be an object"))
        else:
            for k in sorted(set(ctx) - set(CONTEXT_KEYS)):
                problems.append((f"assessment_context.{k}", "unknown key; allowed: " + ", ".join(CONTEXT_KEYS)))
            for k, typ in CONTEXT_KEYS.items():
                if k not in ctx:
                    problems.append((f"assessment_context.{k}", "required"))
                elif not isinstance(ctx[k], typ) or isinstance(ctx[k], bool):
                    problems.append((f"assessment_context.{k}", "has the wrong type"))
            if ctx.get("entry") not in (None, "mapped_site"):
                problems.append(("assessment_context.entry", "only 'mapped_site' (a mapped marsh cell) can be replayed"))
            if isinstance(ctx.get("n_draws"), int) and ctx["n_draws"] <= 0:
                problems.append(("assessment_context.n_draws", "must be a positive integer"))
    eff = raw.get("treatment_effect")
    if eff is None:
        return
    if not isinstance(eff, dict):
        problems.append(("treatment_effect", "must be an object, or null for no treatment curve"))
        return
    if model not in _EFFECTS:
        return
    keys, date_keys, value_key, unit, meaning = _EFFECTS[model]
    for k in sorted(set(eff) - set(keys)):
        problems.append((f"treatment_effect.{k}", "unknown key; allowed: " + ", ".join(keys)))
    for k in date_keys:
        if k not in eff:
            problems.append((f"treatment_effect.{k}", "required"))
        else:
            _date(problems, f"treatment_effect.{k}", eff[k])
    rc = eff.get(value_key, None)
    if value_key not in eff or rc is None:
        problems.append((f"treatment_effect.{value_key}", "required; write null for the whole effect to mean 'no treatment "
                         "curve' (0 means an entered zero change)"))
    elif not _is_number(rc) or not math.isfinite(rc):
        problems.append((f"treatment_effect.{value_key}", f"must be {meaning}"))
    if eff.get("unit") != unit:
        problems.append(("treatment_effect.unit", f"must be '{unit}' (no unit conversion is done)"))
    if model == C.TPAH_WHATIF_MODEL and not (isinstance(eff.get("basis"), str) and eff["basis"].strip()):
        problems.append(("treatment_effect.basis", "record the basis of the reduction (for example 'user-defined sensitivity "
                         "assumption' when no field estimate exists)"))
    if eff.get("origin") != "user_assumption":
        problems.append(("treatment_effect.origin", "must be 'user_assumption': no measured treatment effect is available"))


def load(path: str | Path) -> ScenarioSpec:
    p = Path(path)
    try:
        raw = json.loads(p.read_text(encoding="utf-8"), parse_constant=_reject_constant)
    except FileNotFoundError:
        raise SpecError([("(file)", f"scenario file not found: {p}")]) from None
    except json.JSONDecodeError as exc:
        raise SpecError([("(file)", f"{p} is not valid JSON: {exc}")]) from None
    return from_dict(raw)


def _reject_constant(name: str):
    raise SpecError([("(file)", f"'{name}' is not allowed; values must be finite numbers or null")])


def _model_assumption_problems(spec: ScenarioSpec) -> list:
    """Assumptions must match what the model uses: nothing unused is carried silently, nothing required is missing."""
    rules = C.MODEL_ASSUMPTIONS[spec.model_version]
    allowed = set(rules["required"]) | set(rules["optional"])
    given = {a.assumption_id: a for a in spec.assumptions}
    problems = [("assumptions", f"'{k}' is not used by {spec.model_version}; remove it (used: {', '.join(sorted(allowed)) or 'none'})")
                for k in sorted(set(given) - allowed)]
    problems += [("assumptions", f"{spec.model_version} needs '{k}'") for k in rules["required"] if k not in given]
    change, second = given.get("rate_change_date"), given.get("changed_retreat_rate")
    if (change is None) != (second is None):
        problems.append(("assumptions", "'rate_change_date' and 'changed_retreat_rate' must be given together"))
    elif change is not None:
        if change.value is None or second.value is None:
            problems.append(("assumptions", "a rate change needs both a date and a rate; remove both to use one fixed rate"))
        else:
            c = dt.date.fromisoformat(change.value)
            if not (spec.as_of_date < c < spec.end):
                problems.append(("assumptions", f"rate_change_date {c} must lie after as_of {spec.as_of} and before end_date "
                                 f"{spec.end_date}"))
    return problems


def _exposure_scope(spec: ScenarioSpec) -> Unsupported | None:
    """Release-and-exposure requests. Input errors raise SpecError; a known case with missing essential inputs returns
    Unsupported('exposure_inputs_unavailable') naming them. No path here can produce 'no_contact'."""
    problems = []
    if spec.endpoint != C.EXPOSURE_ENDPOINT or spec.model_version != "transport_hindcast/1":
        problems.append(("model_version", f"exposure requests use endpoint '{C.EXPOSURE_ENDPOINT}' with model 'transport_hindcast/1'"))
    case = C.EXPOSURE_CASES.get(spec.site_id)
    if case is None and not problems:
        return Unsupported("unknown_exposure_case", f"No release-and-exposure case '{spec.site_id}' is defined; defined: "
                           + ", ".join(C.EXPOSURE_CASES) + ".", "site_id")
    ep = C.ENDPOINTS[C.EXPOSURE_ENDPOINT]
    if spec.unit != ep.unit:
        problems.append(("unit", f"'{C.EXPOSURE_ENDPOINT}' is reported as '{ep.unit}', not '{spec.unit}'"))
    if spec.plot_group_id != C.EXPOSURE_GROUP:
        problems.append(("plot_group_id", f"exposure cases use '{C.EXPOSURE_GROUP}'"))
    if spec.oiling_class != C.EXPOSURE_OILING:
        problems.append(("oiling_class", f"the oiling class is an outcome here, not an input; use '{C.EXPOSURE_OILING}'"))
    if spec.arm != "reference":
        problems.append(("arm", "a release hindcast has no treatment arm; use 'reference'"))
    if case is not None and spec.habitat != case.habitat:
        problems.append(("habitat", f"case '{case.case_id}' is '{case.habitat}'"))
    missing_ev = [x for x in C.EXPOSURE_EVIDENCE if x not in spec.evidence_ids]
    if missing_ev:
        problems.append(("evidence_ids", "add the survey evidence this case is checked against: " + ", ".join(missing_ev)))
    if spec.comparator_group_id:
        problems.append(("comparator_group_id", "only used by field_contrast/1"))
    problems += _model_assumption_problems(spec) if spec.model_version in C.MODEL_ASSUMPTIONS else []
    if problems:
        raise SpecError(problems)
    start, end = (dt.date.fromisoformat(x) for x in case.window)
    if spec.as_of_date < start or spec.end > end:
        return Unsupported("outside_domain", f"Case '{case.case_id}' covers {case.window[0]} to {case.window[1]}; requested "
                           f"{spec.as_of} to {spec.end_date}.", "as_of")
    missing = case.missing_essential()
    if missing:
        return Unsupported("exposure_inputs_unavailable",
                           "No transport simulation can be run for this case from the files in this checkout. Essential inputs "
                           "missing or incomplete: " + "; ".join(f"{i.name} ({i.status})" for i in missing)
                           + ". The dated SCAT surveys are present and are exported as evaluation observations "
                           "(survey_contact.csv); they are not simulation inputs. See docs/PROJECTION_EXPOSURE_DATA_GAP.md.",
                           "site_id")
    return Unsupported("model_not_installed", "All inputs are present but no transport adapter is installed in this environment.",
                       "model_version")


def check_scope(spec: ScenarioSpec) -> Unsupported | None:
    """Return a structured reason when a valid spec asks for something unsupported, else None. Order: habitat, site, group,
    endpoint, oiling class. Raises SpecError when a supported request is internally inconsistent (unit, arm, missing citation)."""
    if spec.endpoint == C.EXPOSURE_ENDPOINT or spec.model_version == "transport_hindcast/1":
        return _exposure_scope(spec)
    if spec.habitat in C.UNSUPPORTED_HABITATS:
        return Unsupported("habitat_unsupported", C.UNSUPPORTED_HABITATS[spec.habitat], "habitat")
    if spec.site_id in C.KNOWN_NON_PROJECTION_SITES:
        code, reason = C.KNOWN_NON_PROJECTION_SITES[spec.site_id]
        return Unsupported(code, reason, "site_id")
    site = C.SITES.get(spec.site_id)
    if site is None:
        return Unsupported("unknown_site", f"No projection evidence is held for site '{spec.site_id}'. Supported sites: "
                           + ", ".join(C.SITES) + ". A new location needs habitat-specific measurements and an independent "
                           "evaluation before any number is produced.", "site_id")
    if spec.habitat != site.habitat:
        return Unsupported("habitat_mismatch", f"Site '{site.site_id}' is {site.habitat}, not {spec.habitat}.", "habitat")
    group = site.plot_groups.get(spec.plot_group_id)
    if group is None:
        return Unsupported("unknown_plot_group", f"Site '{site.site_id}' has plot groups: {', '.join(site.plot_groups)}.",
                           "plot_group_id")
    ep = C.ENDPOINTS.get(spec.endpoint)
    if ep is None:
        return Unsupported("unknown_endpoint", f"Endpoint '{spec.endpoint}' is not defined; defined: {', '.join(C.ENDPOINTS)}.",
                           "endpoint")
    if not ep.implemented:
        return Unsupported("endpoint_not_implemented", ep.not_implemented_reason, "endpoint")
    if spec.endpoint in group.ineligible:
        return Unsupported("plot_group_ineligible", group.ineligible[spec.endpoint], "plot_group_id")
    if spec.habitat not in ep.habitats:
        return Unsupported("habitat_unsupported", f"Endpoint '{ep.endpoint_id}' is defined only for {', '.join(ep.habitats)}.",
                           "habitat")
    if spec.oiling_class != group.oiling_class:
        return Unsupported("oiling_class_unsupported", f"Plot group '{group.group_id}' represents oiling class "
                           f"{group.oiling_class}; these plots are not evidence for class {spec.oiling_class}.", "oiling_class")
    # Inconsistencies the user can fix in the file are input errors, not abstentions.
    problems = []
    if spec.unit != ep.unit:
        problems.append(("unit", f"endpoint '{ep.endpoint_id}' is reported in '{ep.unit}', not '{spec.unit}' (no conversion is done)"))
    if spec.arm != group.arm:
        problems.append(("arm", f"plot group '{group.group_id}' is the '{group.arm}' arm, not '{spec.arm}'"))
    pair = (spec.model_version, spec.endpoint)
    gap = C.GAPS.get(pair)
    # An evidence gap still exports the endpoint's historical observations, so it needs their evidence cited.
    cite = C.SUPPORTED.get(pair) or C.SUPPORTED.get(("observed_record/1", spec.endpoint), ())
    missing_ev = [x for x in cite if x not in spec.evidence_ids]
    if missing_ev:
        problems.append(("evidence_ids", "add the evidence this request is built on: " + ", ".join(missing_ev)))
    if spec.model_version == "field_contrast/1":
        if not spec.comparator_group_id:
            problems.append(("comparator_group_id", "field_contrast/1 needs the comparator plot group (for example 'untreated_heavy')"))
        elif spec.comparator_group_id not in site.plot_groups:
            problems.append(("comparator_group_id", f"unknown plot group '{spec.comparator_group_id}'; groups: "
                             + ", ".join(site.plot_groups)))
    elif spec.comparator_group_id:
        problems.append(("comparator_group_id", f"only used by field_contrast/1; remove it for {spec.model_version}"))
    if gap:
        if problems:
            raise SpecError(problems)
        code, reason = gap
        return Unsupported(code, reason, "model_version")
    problems += _model_assumption_problems(spec)
    if problems:
        raise SpecError(problems)
    rate = spec.assumption("retreat_rate")
    if rate is not None and rate.value is None:
        return Unsupported("rate_not_available", f"No retreat rate was supplied ({rate.missing_reason}); no projection is made "
                           "without a stated rate.", "assumptions")
    if spec.model_version == C.WHATIF_MODEL and spec.treatment_effect is not None:
        from src.shoreline_remediation.projections import projection as P, whatif as W
        effect = W.effect_from_spec(spec)
        problem = W.problem(effect, spec.as_of_date, spec.end, P.rate_segments(spec, spec.as_of_date))
        if problem:
            raise SpecError([("treatment_effect", problem)])
    if spec.model_version == C.TPAH_WHATIF_MODEL:
        from src.shoreline_remediation.projections import evidence as E, pah as PH
        hl = spec.assumption("tpah_half_life")
        if hl is not None:
            bad = PH.baseline_problem(hl.value) if hl.value is not None else (
                "omit 'tpah_half_life' to hold the concentration, or give a positive half-life in years")
            if bad:
                raise SpecError([("assumptions", bad)])
        anchor = PH.anchor_from(E.tpah_observed(spec))
        if anchor is None:
            return Unsupported("no_anchor_observation", PH.no_anchor_reason(spec.as_of), "as_of")
        if spec.treatment_effect is not None:
            problem = PH.problem(PH.effect_from_spec(spec), anchor, spec.end)
            if problem:
                raise SpecError([("treatment_effect", problem)])
    if spec.model_version == C.COVER_WHATIF_MODEL:
        from src.shoreline_remediation.projections import cover as CV, evidence as E
        anchor = CV.anchor_from(E.vegetation_observed(spec))
        if anchor is None:
            return Unsupported("no_anchor_observation", CV.no_anchor_reason(spec), "as_of")
        if spec.treatment_effect is not None:
            problem = CV.problem(CV.effect_from_spec(spec), anchor, spec.end)
            if problem:
                raise SpecError([("treatment_effect", problem)])
    if (spec.model_version, group.group_id) in C.GROUP_MODEL_GAPS:
        return Unsupported("model_not_applicable_to_group", C.GROUP_MODEL_GAPS[(spec.model_version, group.group_id)],
                           "plot_group_id")
    if spec.model_version == "field_contrast/1" and (spec.endpoint, group.group_id, spec.comparator_group_id) not in C.CONTRASTS:
        return Unsupported("no_field_contrast", f"No historical field contrast of {spec.endpoint} between '{group.group_id}' and "
                           f"'{spec.comparator_group_id}' exists in the comparison layer. Available: "
                           + "; ".join(f"{t} vs {c}" for e, t, c in C.CONTRASTS if e == spec.endpoint) + ".", "comparator_group_id")
    if pair not in C.SUPPORTED:
        return Unsupported("model_not_available_for_endpoint", f"{spec.model_version} is not available for {spec.endpoint}.",
                           "model_version")
    return None
