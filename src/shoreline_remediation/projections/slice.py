"""Historical manual-removal comparison for the Bay Jimmy plots linked to an Assessment."""
from __future__ import annotations

from src.shoreline_remediation import comparison
from src.shoreline_remediation.projections import catalogue as C, evidence, inventory as I
from src.shoreline_remediation.projections.spec import Unsupported


COVER, PAH, RETREAT = I.ENDPOINT_ORDER
MANUAL = "manual_removal"


def _records(frame):
    """Preserve the loader's precision and provenance while making missing intervals JSON null."""
    frame = frame.drop(columns=["shared_plots", "scenario_id", "available_at_as_of"], errors="ignore")
    return frame.astype(object).where(frame.notna(), None).to_dict("records")


def _erosion_context():
    rows = []
    for target in (comparison.EROSION_2010_2012, comparison.EROSION_2012_2018):
        for est in comparison.runtime_estimates(target.key):
            if est.option == MANUAL and est.comparator == target.comparator and est.has_value:
                rows.append({
                    "endpoint": "erosion_rate_change_difference", "date": est.time,
                    "pre_spill_reference_period": "2005-2010", "outcome": est.outcome,
                    "plot_group_id": "manual_removal_heavy", "comparator_group_id": "untreated_heavy",
                    "n_plots": est.n_treated, "n_comparator": est.n_comparator,
                    "value": est.estimate, "unit": est.unit, "interval_lo": est.lo, "interval_hi": est.hi,
                    "interval_level": est.interval_level, "interval_method": est.interval_type,
                    "record_type": "field_contrast", "record_class": C.RECORD_TYPES["field_contrast"],
                    "evidence_id": "zengel2022_griidc_aerial_rates", "design": est.design,
                    "derivation": est.derivation, "source": est.source,
                })
    return rows


def manual_vs_natural(inventory: I.Inventory, option: str = MANUAL) -> dict | Unsupported:
    """Build a JSON-ready historical comparison. No UI, files written or hypothetical treatment date."""
    if not inventory.in_scope or inventory.site_id != "bay_jimmy_zengel_plots":
        return Unsupported("site_out_of_scope", inventory.scope_reason or "Requires the Bay Jimmy field plots.", "site_id")
    if option != MANUAL:
        return Unsupported("unsupported_option", "This field comparison covers manual removal only.", "option")

    # Check all six cells before loading measurements, including the scope of the reference arm.
    arms = {}
    for endpoint in I.ENDPOINT_ORDER:
        try:
            treated = inventory.cell(option, endpoint)
            reference = inventory.reference(endpoint)
        except (KeyError, ValueError):
            return Unsupported("missing_arm", f"Missing a unique treatment or reference for {endpoint}.", endpoint)
        if treated.category == "excluded" or treated.historical_context_only:
            return Unsupported("excluded_option", treated.what_if_reason, "option")
        if (reference.option != I.REFERENCE or
                any("observed_group_mean" not in arm.admissible_outputs for arm in (treated, reference))):
            return Unsupported("missing_observations", f"Both arms need observed support for {endpoint}.", endpoint)
        arms[endpoint] = (reference, treated)

    site = inventory.site_id
    groups = I.OPTION_PLOT_GROUPS[site]
    endpoints = {}
    for endpoint, pair in arms.items():
        observations = []
        for arm in pair:
            sp = I.historical_spec(site, groups[arm.option], endpoint)
            for row in _records(I.historical_observations(sp)):
                observations.append({**row, "option": arm.option, "role": arm.role})
        endpoints[endpoint] = {"observations": observations, "future_rate_or_effect_gap": pair[1].unavailable_reason}

    cover = endpoints[COVER]
    treated = arms[COVER][1]
    cover["limitation"] = ("Plot measurements and the published rounded means cover overlapping plots. "
                           "The observational difference applies to the September 2012 survey only.")
    cover["published_year_two"] = []
    if "field_contrast" in treated.admissible_outputs and treated.comparison_status == "":
        sp = I.historical_spec(site, groups[option], COVER, "field_contrast/1", groups[I.REFERENCE])
        frame, detail = evidence.vegetation_contrast(sp)
        if frame is None:
            cover["contrast_unavailable_reason"] = detail.reason
        else:
            # Keep the published rounded inputs beside their contrast, apart from the plot means.
            cover["published_year_two"] = _records(frame)
    else:
        cover["contrast_unavailable_reason"] = treated.comparison_status or "No admitted year-two contrast."

    pah = endpoints[PAH]
    pah["limitation"] = "Two soil sampling periods per arm. The regional DIVER stations use a different depth and analyte set."
    if "model_reference_index" in arms[PAH][0].admissible_outputs:
        index, detail, uses = evidence.diver_index(I.historical_spec(site, groups[I.REFERENCE], PAH))
        pah["regional_reference"] = {
            "records": [] if index is None else _records(index.assign(
                site_id=None, endpoint="regional_heavy_class_pah_index", geography="northern Gulf DIVER stations")),
            "metadata": None if index is None else detail,
            "unavailable_reason": detail if index is None else None,
            "sources_consulted": dict(uses),
        }
    endpoints[RETREAT]["origin_date"] = "2010-12-04"
    endpoints[RETREAT]["limitation"] = ("Field surveys measure retreat since the common origin. The aerial comparisons "
                                        "measure changes in erosion rates relative to 2005–2010 on a separate scale.")
    endpoints[RETREAT]["aerial_rate_contrasts"] = _erosion_context()
    return {
        "version": "manual-versus-natural-history/1", "site_id": site,
        "option": option, "comparator": I.REFERENCE,
        "historical_manual_treatment": {"date": "2010-12", "precision": "month",
                                        "source": "Zengel et al. 2015, Methods (docs/V5_4_RECOVERY_VIEW.md)"},
        "future_intervention_date": None, "unresolved_conditions": list(treated.unresolved_conditions),
        "shared_plots_note": inventory.shared_plots_note, "endpoints": endpoints,
    }
