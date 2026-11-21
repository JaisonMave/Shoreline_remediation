"""Technique-by-endpoint inventory for the future-scenario explorer (remediation scenarios plan, section 1).

What it does
------------
Reads a decision report (the dict or DecisionReport that decision_pipeline.run_decision() returned) and returns ONE row per report
option and scenario endpoint. The report's own natural-recovery option is the single reference row of each endpoint. Each row
records, unchanged, what the report says about the option (category, rule verdict, harm flags, condition lines, exclusion
reasons, source IDs), and then what the repository can show for that endpoint: observed plot records, a field contrast with a
matching comparator, off-endpoint context, or a specific evidence gap.

What it does not do
-------------------
It never changes a screening status, a recommendation or an order, and it computes no effect size. Options come from the report,
never from a list typed here, so a new report option appears as an explicit evidence-gap row without any code change. Conditions
are read with comparison.conditions_state (unknown is never treated as met), and field contrasts are admitted with
comparison.compare, the same rules the Assessment comparison uses. Observed support is read through the existing loaders.

`what_if_allowed` only says that screening and prerequisites would permit a user-defined assumption for that arm (plan section
3, not implemented here). A method whose conditions are unknown stays visible with its conditions and is not executable.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from functools import lru_cache

from src.shoreline_remediation import comparison as K
from src.shoreline_remediation.projections import catalogue as C

INVENTORY_VERSION = "technique-endpoint-inventory/1"
ENDPOINT_ORDER = ("total_vegetation_cover", "soil_tpah", "cumulative_shoreline_retreat")
REFERENCE = K.REFERENCE_OPTION

# Report option -> catalogue plot group whose field records describe that action at the site. Only actions the plots received.
OPTION_PLOT_GROUPS = {
    "bay_jimmy_zengel_plots": {
        REFERENCE: "untreated_heavy",
        "manual_removal": "manual_removal_heavy",
        "mechanical_removal": "mechanical_removal_heavy",
    },
}
# The worked-example report cell whose nearest field evidence is the Bay Jimmy plots (a different spatial unit, see
# catalogue.KNOWN_NON_PROJECTION_SITES). The Assessment shows plot evidence for this cell only.
REPORT_CELL_SITES = {"8018_32612": "bay_jimmy_zengel_plots"}
_HABITAT_CLASS_KEYS = {"rocky/hard": "rocky_shore", "mangrove": "mangrove", "sand": "sand_beach"}

# Contrast targets of the comparison layer and the scenario endpoint each one informs. Only the vegetation target has the same
# outcome and unit as a scenario endpoint; erosion-rate contrasts (m/yr change) are context for cumulative retreat (m).
_TARGET_ENDPOINT = {K.VEG_YEAR2.key: "total_vegetation_cover", K.EROSION_2010_2012.key: "cumulative_shoreline_retreat",
                    K.EROSION_2012_2018.key: "cumulative_shoreline_retreat"}
_ON_ENDPOINT_TARGETS = {K.VEG_YEAR2.key}

NEEDED = {
    "total_vegetation_cover": ("dated total vegetation cover (%, all species) on plots that received this action and on comparable "
                               "untreated oiled plots at the same surveys"),
    "soil_tpah": ("soil tPAH (mg/kg, stated depth, analyte set and dry/wet basis) on treated and comparable untreated plots at two "
                  "or more dates"),
    "cumulative_shoreline_retreat": ("dated shoreline positions (m) from a common origin on treated and comparable untreated plots, "
                                     "with treatment dates"),
}
NO_EFFECT_SIZE = "A lack of demonstrated benefit supplies no numerical effect size."
REFERENCE_COMPARATOR = "none: natural-recovery reference (oiled shoreline left to natural recovery)"


@dataclass(frozen=True)
class Support:
    """One body of repository evidence for an (option, endpoint) cell."""
    record_type: str            # catalogue.RECORD_TYPES key
    evidence_id: str
    on_endpoint: bool           # same outcome and unit as the endpoint (False: context only, never plotted on this endpoint)
    description: str
    dates: tuple = ()
    n_plots: tuple = ()
    comparator: str = ""
    note: str = ""


@dataclass(frozen=True)
class InventoryRow:
    option: str
    endpoint: str
    endpoint_unit: str
    role: str                    # "reference" or "intervention"
    # --- read unchanged from the report
    category: str
    category_label: str
    category_reason: str
    rule_verdict: str
    rule_id: str
    do_no_harm: str
    harm_flags: tuple
    conditions: tuple            # the pipeline's own 'text -> effect [status]' lines
    exclusion_reasons: tuple
    evidence_state: str
    report_evidence_basis: str
    report_source_ids: tuple
    # --- derived with the comparison layer's rules
    conditions_state: str        # comparison.conditions_state: not_required, met, unmet, unknown
    conditions_detail: str
    unresolved_conditions: tuple  # condition lines whose status is unknown, even where the state is 'not_required'
    prerequisites: tuple
    prerequisite_state: str      # "none", "allowed", "excluded" or "absent from report"
    # --- endpoint evidence
    comparator: str
    evidence_ids: tuple
    support: tuple               # Support records
    admissible_outputs: tuple    # record types this cell may display
    availability: str            # observed_and_contrast, observed, context_only, evidence_gap, out_of_scope
    comparison_status: str       # comparison.compare reason for the on-endpoint field contrast ('' = eligible, 'n/a' = none)
    unavailable_reason: str
    historical_context_only: bool
    what_if_allowed: bool
    what_if_reason: str

    def as_dict(self) -> dict:
        """JSON-native dict (tuples become lists)."""
        def native(x):
            return [native(v) for v in x] if isinstance(x, (list, tuple)) else {k: native(v) for k, v in x.items()} \
                if isinstance(x, dict) else x
        return native(asdict(self))


@dataclass
class Inventory:
    rows: list
    site_id: str | None
    in_scope: bool
    scope_reason: str
    version: str = INVENTORY_VERSION
    shared_plots_note: str = C.SHARED_PLOTS_NOTE
    endpoints: tuple = ENDPOINT_ORDER
    notes: list = field(default_factory=list)

    @property
    def options(self) -> list:
        return list(dict.fromkeys(r.option for r in self.rows))

    def cell(self, option: str, endpoint: str) -> InventoryRow:
        for r in self.rows:
            if r.option == option and r.endpoint == endpoint:
                return r
        raise KeyError((option, endpoint))

    def reference(self, endpoint: str) -> InventoryRow:
        refs = [r for r in self.rows if r.endpoint == endpoint and r.role == "reference"]
        if len(refs) != 1:
            raise ValueError(f"expected one natural-recovery reference for {endpoint}, found {len(refs)}")
        return refs[0]

    def coverage(self) -> list:
        """One dict per option: category plus the availability of each endpoint (the N-by-3 coverage table)."""
        out = []
        for o in self.options:
            first = self.cell(o, self.endpoints[0])
            out.append({"option": o, "category": first.category, "what_if_allowed": first.what_if_allowed,
                        **{e: self.cell(o, e).availability for e in self.endpoints}})
        return out

    def to_records(self) -> list:
        return [r.as_dict() for r in self.rows]


# ---------------------------------------------------------------------------------------------------------------
# Report access (read only)

def _report_dict(report) -> dict:
    if isinstance(report, dict):
        return report
    to_dict = getattr(report, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    raise TypeError("report must be a DecisionReport or its dict")


def site_for_report(report) -> str | None:
    """The catalogue site whose field evidence the Assessment shows for this report, or None. Only the worked-example cell maps."""
    ch = _report_dict(report).get("characterisation") or {}
    return REPORT_CELL_SITES.get(str(ch.get("cell") or ""))


def _scope(rep: dict, site_id: str | None) -> tuple:
    ch = rep.get("characterisation") or {}
    habitat, oiling = str(ch.get("habitat") or ""), str(ch.get("oiling_class") or "")
    hkey = habitat if habitat in C.UNSUPPORTED_HABITATS else _HABITAT_CLASS_KEYS.get(str(ch.get("habitat_class") or ""), "")
    if hkey in C.UNSUPPORTED_HABITATS:
        return False, C.UNSUPPORTED_HABITATS[hkey]
    if site_id is None:
        return False, ("No field site with dated endpoint records is linked to this assessment. Site evidence is shown for the "
                       "Bay Jimmy worked example only; screening results remain the supported output.")
    if site_id not in C.SITES:
        return False, f"Unknown evidence site '{site_id}'."
    site = C.SITES[site_id]
    groups = OPTION_PLOT_GROUPS.get(site_id, {})
    ref_group = site.plot_groups.get(groups.get(REFERENCE, ""))
    if habitat != site.habitat:
        return False, f"The {site.label} evidence covers {site.habitat.replace('_', ' ')}; this assessment is {habitat or 'unstated'}."
    if ref_group is None or oiling != ref_group.oiling_class:
        return False, (f"The {site.label} evidence covers {ref_group.oiling_class if ref_group else 'stated'} oiling; this assessment's "
                       f"oiling class is {oiling or 'unstated'}.")
    return True, ""


# ---------------------------------------------------------------------------------------------------------------
# Evidence (existing loaders; cached because the data files do not change within a process)

def historical_spec(site_id: str, group_id: str, endpoint: str, model="observed_record/1", comparator=""):
    """Validated loader input for the complete historical record, without a retrospective cutoff."""
    from src.shoreline_remediation.projections import spec as S
    group = C.SITES[site_id].plot_groups[group_id]
    raw = {"schema_version": C.SCHEMA_VERSION, "scenario_id": f"inventory_{group_id}_{endpoint}", "site_id": site_id,
           "plot_group_id": group_id, "habitat": C.SITES[site_id].habitat, "oiling_class": group.oiling_class,
           "endpoint": endpoint, "unit": C.ENDPOINTS[endpoint].unit, "arm": group.arm, "as_of": "2100-01-01",
           "end_date": "2100-01-02", "cadence": "annual", "model_version": model, "seed": 0,
           "evidence_ids": list(C.SUPPORTED[(model, endpoint)]), "assumptions": []}
    if comparator:
        raw["comparator_group_id"] = comparator
    return S.from_dict(raw)


def historical_observations(sp):
    from src.shoreline_remediation.projections import evidence as E, runner as R
    loader = {"total_vegetation_cover": E.vegetation_observed, "soil_tpah": E.tpah_observed,
              "cumulative_shoreline_retreat": R.observed_record}[sp.endpoint]
    return loader(sp)


@lru_cache(maxsize=32)
def observed_support(site_id: str, group_id: str, endpoint: str) -> Support | None:
    """Observed group means of a plot group for one endpoint, through the existing projection loaders. None if there are none."""
    from src.shoreline_remediation.projections import evidence as E
    group = C.SITES[site_id].plot_groups[group_id]
    if endpoint in group.ineligible:
        return None
    try:
        df = historical_observations(historical_spec(site_id, group_id, endpoint))
    except RuntimeError:
        return None
    if df.empty:
        return None
    eid = str(df.evidence_id.iloc[0])
    extra = {"soil_tpah": f"; {E.TPAH_DEPTH}", "cumulative_shoreline_retreat": "; cumulative since 4 Dec 2010"}.get(endpoint, "")
    return Support("observed_group_mean", eid, True,
                   f"Observed group means of {group.label} ({C.ENDPOINTS[endpoint].unit}{extra})",
                   tuple(str(d) for d in df.date), tuple(int(n) for n in df.n_plots))


@lru_cache(maxsize=1)
def _contrast_estimates() -> dict:
    return {key: tuple(K.runtime_estimates(key)) for key in _TARGET_ENDPOINT}


def prerequisites() -> dict:
    """option -> options it presupposes, as declared by the comparison layer's field estimates (sequences and increments)."""
    out = {}
    for ests in _contrast_estimates().values():
        for e in ests:
            if e.prerequisite:
                out.setdefault(e.option, set()).add(e.prerequisite)
    return {k: tuple(sorted(v)) for k, v in out.items()}


def _contrast_support(option: str, endpoint: str, rep: dict, habitat: str, oiling: str) -> tuple:
    """(support records, comparison status of the on-endpoint contrast or 'n/a') for one option and endpoint."""
    records, status = [], "n/a"
    for key, ests in _contrast_estimates().items():
        if _TARGET_ENDPOINT[key] != endpoint:
            continue
        target = K.TARGETS[key]
        mine = [e for e in ests if e.option == option]
        if not mine:
            continue
        comp = K.compare(target, list(ests), rep, habitat, oiling)
        for e in mine:
            mismatch = K._mismatch(e, target)
            on = key in _ON_ENDPOINT_TARGETS and not mismatch
            row = next((r for r in comp.rows if r.est is e), None)
            if on and row is not None:
                status = row.reason
            note = mismatch or ("" if on else f"different endpoint: {target.outcome} ({target.unit}), not {endpoint.replace('_', ' ')} "
                                                "(" + C.ENDPOINTS[endpoint].unit + ")")
            records.append(Support(
                "field_contrast", "zengel2015_s1_group_means" if "zengel2015" in e.source_keys else "zengel2022_griidc_aerial_rates",
                on, f"{e.label} minus {e.comparator}: {e.outcome}, {e.time}, {e.estimate:+.{target.digits}f} {e.unit} "
                    f"({int(e.interval_level * 100)}% {e.interval_type.split(' (')[0]} {e.lo:+.{target.digits}f} to {e.hi:+.{target.digits}f})",
                (e.time,), tuple(n for n in (e.n_treated, e.n_comparator) if n), e.comparator,
                "; ".join(x for x in (note, e.design, e.source) if x)))
    return tuple(records), status


# ---------------------------------------------------------------------------------------------------------------
# Rows

def _str_tuple(xs) -> tuple:
    return tuple(str(x) for x in (xs or []))


def _exclusions(row: dict) -> tuple:
    return tuple(str(x.get("detail", x)) if isinstance(x, dict) else str(x) for x in row.get("exclusion_reasons") or [])


def _prerequisite_state(option: str, opts: dict) -> tuple:
    pre = prerequisites().get(option, ())
    if not pre:
        return pre, "none"
    states = []
    for p in pre:
        r = opts.get(p)
        states.append("absent from report" if r is None else "excluded" if r.get("recommendation_category") == "excluded" else "allowed")
    worst = next((s for s in ("excluded", "absent from report") if s in states), "allowed")
    return pre, worst


def _what_if(role: str, row: dict, cond: str, cond_detail: str, pre: tuple, pre_state: str, in_scope: bool, scope: str) -> tuple:
    if role == "reference":
        return False, "Natural-recovery reference: the baseline arm, not an intervention."
    if not in_scope:
        return False, scope
    if row.get("recommendation_category") == "excluded":
        return False, "Excluded by screening: " + "; ".join(_exclusions(row) or (str(row.get("rule_reason") or ""),))
    if str(row.get("do_no_harm") or "") not in ("", "passed"):
        return False, f"Do-no-harm screening: {row.get('do_no_harm')}"
    if pre_state != "none" and pre_state != "allowed":
        return False, (f"Presupposes {', '.join(pre)}, which is {pre_state} for this assessment. An incremental comparison applies "
                       "only where that prior cleanup is independently documented and the comparator and outcome match.")
    if cond == "unmet":
        return False, f"Condition not met for this assessment: {cond_detail}"
    if cond == "unknown":
        return False, f"Conditions not established; confirm before exploring assumptions: {cond_detail}"
    return True, "Screening and prerequisites permit a user-defined assumption for this arm (plan section 3)."


def _row(option: str, rep_row: dict, endpoint: str, site_id: str | None, in_scope: bool, scope: str, opts: dict,
         rep: dict) -> InventoryRow:
    role = "reference" if option == REFERENCE else "intervention"
    category = str(rep_row.get("recommendation_category") or "")
    cond, cond_detail = K.conditions_state(rep_row)
    unresolved = tuple(c for c in _str_tuple(rep_row.get("conditions")) if "[unknown" in c.lower())
    pre, pre_state = _prerequisite_state(option, opts)
    ch = rep.get("characterisation") or {}

    support, status = (), "n/a"
    if in_scope:
        group = OPTION_PLOT_GROUPS.get(site_id, {}).get(option)
        obs = observed_support(site_id, group, endpoint) if group else None
        contrasts, status = _contrast_support(option, endpoint, rep, str(ch.get("habitat") or ""), str(ch.get("oiling_class") or ""))
        support = ((obs,) if obs else ()) + contrasts
        if group and obs is None and endpoint in C.SITES[site_id].plot_groups[group].ineligible:
            support += (Support("observed_group_mean", "", False, "not observed", note=C.SITES[site_id].plot_groups[group].ineligible[endpoint]),)

    on = [s for s in support if s.on_endpoint]
    has_obs = any(s.record_type == "observed_group_mean" for s in on)
    has_contrast = any(s.record_type == "field_contrast" for s in on)
    outputs = []
    if has_obs:
        outputs.append("observed_group_mean")
        if endpoint == "total_vegetation_cover":
            outputs.append("experimental_fit")
    if has_contrast:
        outputs.append("field_contrast")
    if role == "reference" and has_obs:
        if endpoint == "soil_tpah":
            outputs.append("model_reference_index")
        if endpoint == "cumulative_shoreline_retreat":
            outputs.append("conditional_projection")

    if not in_scope:
        availability = "out_of_scope"
    elif has_obs and has_contrast:
        availability = "observed_and_contrast"
    elif has_obs:
        availability = "observed"
    elif support:
        availability = "context_only"
    else:
        availability = "evidence_gap"

    excluded = category == "excluded"
    reason = _unavailable(role, endpoint, category, rep_row, availability, scope, support)
    if role == "reference":
        comparator = REFERENCE_COMPARATOR
    elif has_contrast:
        comparator = next(s.comparator for s in on if s.record_type == "field_contrast")
    elif has_obs:
        comparator = "no matched contrast; reference observations are untreated oiled plots at the same surveys"
    elif support:
        context = "; ".join(dict.fromkeys(s.comparator for s in support if s.comparator))
        comparator = "no matched comparator on this endpoint" + (f" (context evidence compares with: {context})" if context else "")
    else:
        comparator = "none available"
    what_if, why = _what_if(role, rep_row, cond, cond_detail, pre, pre_state, in_scope, scope)
    if what_if and unresolved:
        why += " Unresolved condition(s) carried with this arm: " + "; ".join(unresolved)
    evidence_ids = tuple(dict.fromkeys(s.evidence_id for s in support if s.evidence_id))
    return InventoryRow(
        option, endpoint, C.ENDPOINTS[endpoint].unit, role, category,
        str(rep_row.get("recommendation_category_label") or category.replace("_", " ")),
        str(rep_row.get("recommendation_category_reason") or ""), str(rep_row.get("rule_verdict") or ""),
        str(rep_row.get("rule_id") or ""), str(rep_row.get("do_no_harm") or ""), _str_tuple(rep_row.get("harm_flags")),
        _str_tuple(rep_row.get("conditions")), _exclusions(rep_row), str(rep_row.get("evidence_state") or ""),
        str(rep_row.get("evidence_basis") or ""), _str_tuple(rep_row.get("source_ids")),
        cond, cond_detail, unresolved, pre, pre_state, comparator, evidence_ids, support, tuple(outputs), availability, status,
        reason, excluded and bool(support), what_if, why)


def _unavailable(role, endpoint, category, rep_row, availability, scope, support) -> str:
    if availability == "out_of_scope":
        return scope
    parts = []
    if category == "excluded":
        parts.append("Excluded by screening (" + "; ".join(_exclusions(rep_row)) + "); historical records, if any, are context only "
                     "and the action is not a prospective control.")
    elif category == "no_demonstrated_benefit":
        parts.append(f"Screening rationale: {rep_row.get('recommendation_category_reason') or ''} ({rep_row.get('evidence_verdict') or ''}). "
                     + NO_EFFECT_SIZE)
    elif category == "insufficient_evidence":
        parts.append(f"Insufficient evidence: {rep_row.get('recommendation_category_reason') or ''}.")
    for s in support:
        if not s.on_endpoint and s.record_type == "observed_group_mean":
            parts.append(s.note)
    if availability in ("evidence_gap", "context_only"):
        if availability == "context_only":
            parts.append("Only off-endpoint or different-comparator evidence exists; nothing is plotted on this endpoint.")
        parts.append(f"Evidence needed for {endpoint.replace('_', ' ')}: {NEEDED[endpoint]}.")
    else:
        # observed records exist; say what remains unavailable (the future of a treated arm, or the reference's own limits)
        if endpoint == "soil_tpah":
            parts.append(C.PAH_TREATMENT_GAP)
        elif endpoint == "total_vegetation_cover":
            parts.append(C.VEG_FUTURE_GAP)
        elif role != "reference":
            parts.append("No treatment-specific retreat rate or cumulative-retreat contrast is identified; erosion-rate contrasts "
                         "(m/yr) are context on a separate scale. A future treated arm needs a stated what-if assumption.")
    return " ".join(p for p in parts if p).strip()


def build_inventory(report, site_id: str | None = "auto") -> Inventory:
    """The technique-by-endpoint inventory of `report`. `site_id` 'auto' uses site_for_report(); None means no site evidence."""
    rep = _report_dict(report)
    if site_id == "auto":
        site_id = site_for_report(rep)
    in_scope, scope = _scope(rep, site_id)
    raw_opts = [r for r in rep.get("options") or [] if isinstance(r, dict)]
    keys = [str(r.get("option")) for r in raw_opts]
    if len(set(keys)) != len(keys):
        raise ValueError("report lists an option more than once")
    opts = dict(zip(keys, raw_opts))
    notes = []
    if REFERENCE not in opts:
        nr = rep.get("natural_recovery") or {}
        opts = {REFERENCE: {"option": REFERENCE, "recommendation_category": "natural_recovery_monitoring",
                            "recommendation_category_label": str(nr.get("label") or "natural recovery"),
                            "recommendation_category_reason": "reference option (from the report's natural_recovery block)",
                            "evidence_basis": str(nr.get("evidence_basis") or "")}, **opts}
        notes.append("The report lists no natural_attenuation option; the reference row is taken from its natural_recovery block.")
    rows = [_row(o, r, e, site_id, in_scope, scope, opts, rep) for o, r in opts.items() for e in ENDPOINT_ORDER]
    return Inventory(rows, site_id, in_scope, scope, notes=notes)
