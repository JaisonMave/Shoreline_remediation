"""What the research projection runner supports, and the explicit reasons for what it does not.

Every identifier a scenario file may use is defined here: sites, plot groups, endpoints, evidence sources, assumption IDs, model
versions, the (model, endpoint) pairs that can run and the evidence gaps of those that cannot. Anything else is either invalid
input (spec.SpecError) or a structured unsupported outcome (spec.Unsupported).

Scope follows docs/PROJECTION_RETREAT_PROTOCOL.md and docs/V5_4_RECOVERY_VIEW.md. Identifiers and scope only; no data are read here.
"""
from __future__ import annotations

from dataclasses import dataclass, field

SCHEMA_VERSION = "shoreline-projection-spec/1"
# Version 2 adds a user-defined treatment what-if for retreat (technique, assessment context, treatment effect). Version 1
# files keep their meaning, run IDs and outputs; the two versions are parsed by the same validator.
SCHEMA_VERSION_2 = "shoreline-projection-spec/2"
SCHEMA_VERSIONS = (SCHEMA_VERSION, SCHEMA_VERSION_2)
WHATIF_MODEL = "retreat_whatif/1"
COVER_WHATIF_MODEL = "cover_whatif/1"
TPAH_WHATIF_MODEL = "tpah_whatif/1"
WHATIF_MODELS = {WHATIF_MODEL: "cumulative_shoreline_retreat", COVER_WHATIF_MODEL: "total_vegetation_cover",
                 TPAH_WHATIF_MODEL: "soil_tpah"}

# Origin of every value a scenario carries (CLAUDE.md section 4: keep these separate).
ORIGINS = ("observation", "derived", "literature", "fitted_parameter", "user_assumption", "synthetic_fixture")

ARMS = ("reference", "intervention")
CADENCES = {"monthly": 12, "quarterly": 4, "annual": 1}

# One vocabulary for every exported row. record_type is the specific kind; record_class is the reader-facing class.
RECORD_TYPES = {
    "observed_group_mean": "observation",           # mean of measured plot values at a survey
    "observed_anchor": "observation",               # the observed value a projection starts from
    "field_contrast": "derived_field_contrast",     # difference of observed group means with its sampling interval
    "experimental_fit": "experimental_fit",         # model fitted to the group's own observations, inside their time span
    "conditional_projection": "conditional_projection",  # any value that depends on a stated or borrowed assumption
    "model_reference_index": "model_reference",     # a registered model's relative reference curve (not a plot observation)
    "observed_survey_contact": "observation",       # SCAT survey record of oil / no oil observed on a shoreline segment
}
RECORD_CLASS_MEANING = {
    "observation": "measured in the field (group mean of plot values)",
    "derived_field_contrast": "difference between observed group means; observational unless stated otherwise",
    "experimental_fit": "experimental model fitted to observations; describes the surveyed period only",
    "conditional_projection": "depends on an assumption (stated rate or borrowed parameter); not a forecast",
    "model_reference": "relative reference curve from a registered model, within its stated support",
}
SHARED_PLOTS_NOTE = ("Bay Jimmy plots are shared across sources: Zengel et al. 2015 (S1 Table) and Zengel et al. 2022 (GRIIDC "
                     "erosion and the compiled vegetation dataset) report the same plots, and these plots also calibrate the scenario "
                     "composer's treatment terms. They are not independent evidence for one another.")


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    citation: str
    locator: str
    path: str            # repository-relative path of the source file


EVIDENCE = {
    "zengel2022_griidc_aerial_rates": Evidence(
        "zengel2022_griidc_aerial_rates",
        "Zengel et al. 2022, Sci. Rep. 12:13802",
        "GRIIDC doi:10.7266/VF524143, sheet 'DSAS lumped', aerial-photo erosion rates by plot and period",
        "data/external/zengel2022/zengel2022_griidc_erosion.xlsx"),
    "zengel2022_griidc_field_positions": Evidence(
        "zengel2022_griidc_field_positions",
        "Zengel et al. 2022, Sci. Rep. 12:13802 (PMC9376092)",
        "GRIIDC doi:10.7266/VF524143 (CC0), sheets 'GIS field erosion points' and 'GIS field erosion'",
        "data/external/zengel2022/zengel2022_griidc_erosion.xlsx"),
    "zengel2022_griidc_vegetation": Evidence(
        "zengel2022_griidc_vegetation",
        "Zengel et al. 2022 meta-analysis compiled dataset (Ecol. Appl.), source 'Zengel (B)'",
        "GRIIDC doi:10.7266/n7-cn03-z792, sheet 'Dataset' (plot types from the erosion workbook sheet 'DSAS lumped')",
        "data/external/zengel2022_meta/dataset_compiled_for_GRIIDC.xlsx"),
    "zengel2015_s1_group_means": Evidence(
        "zengel2015_s1_group_means",
        "Zengel et al. 2015, PLoS ONE 10(7): e0132324 (PMC4511762)",
        "S1 Table group means, standard errors and n (transcribed)",
        "data/external/zengel2015/zengel2015_group_means.csv"),
    "noaa_scat_mobile_visits": Evidence(
        "noaa_scat_mobile_visits",
        "NOAA NCEI Accession 0163818 v1.1 (DOI 10.7289/v53t9ffx), DWH SCAT layer 18613 'SCAT All zones, Mobile'",
        "derived visit table (one row per segment x survey date) built by scripts/build_beach_series.py; clear = all zones NOO "
        "covering >= 50% of SegLength (ASSUMED); see data/external/scat_dwh_mobile/SOURCE.md",
        "data/external/scat_dwh_mobile/beach_visits.csv"),
    "noaa_scat_mobile_segments": Evidence(
        "noaa_scat_mobile_segments",
        "NOAA NCEI Accession 0163818 v1.1, SCAT layer 18613 (Mobile ICP: Alabama, Mississippi, Florida panhandle)",
        "derived segment table: state, segment length, ESI class, midpoint lon/lat (EPSG:4326) by scripts/build_beach_series.py",
        "data/external/scat_dwh_mobile/beach_series.csv"),
    "pah_decline_v1_card": Evidence(
        "pah_decline_v1_card",
        "pah_decline_v1 model card (DIVER soil PAH, Deepwater Horizon)",
        "half_life_years_by_class: decline rate k and the 90% half-life interval by SCAT oiling class (recovery_view.PAH_CARD)",
        "models/pah_decline_v1.json"),
    "pah_decline_v1_campaigns": Evidence(
        "pah_decline_v1_campaigns",
        "pah_decline_v1 station-campaign table (DIVER soil PAH, Deepwater Horizon)",
        "campaign times by station and oiling class; median campaign times give the index support (recovery_view.CAMPAIGNS)",
        "results/pah_decline/station_campaign.csv"),
    "pah_decline_v1_heavy_class": Evidence(
        "pah_decline_v1_heavy_class",
        "pah_decline_v1 (DIVER soil PAH, Deepwater Horizon), heavy oiling class",
        "results/pah_decline/by_oiling_class.csv (rate) and results/pah_decline/station_campaign.csv (campaign support)",
        "results/pah_decline/by_oiling_class.csv"),
}


@dataclass(frozen=True)
class PlotGroup:
    group_id: str
    loader_key: str          # recovery_trajectories key (field positions and vegetation plots)
    oiling_class: str        # the oiling class this group represents; a spec must state the same
    arm: str
    plots: str
    zengel2015_name: str = ""                            # treatment name in the S1 Table
    ineligible: dict = field(default_factory=dict)       # endpoint -> reason this group cannot be used for it
    label: str = ""


@dataclass(frozen=True)
class Site:
    site_id: str
    label: str
    habitat: str
    spatial_unit: str
    plot_groups: dict


BAY_JIMMY_PLOTS = Site(
    "bay_jimmy_zengel_plots",
    "Bay Jimmy field plots (northern Barataria Bay, Louisiana), Deepwater Horizon",
    "salt_marsh",
    "Field plots with two staked transects each (Zengel et al. 2015, 2022); not a mapped NAIP edge cell",
    {
        "untreated_heavy": PlotGroup("untreated_heavy", "untreated", "Heavy", "reference", "3, 8, 12, 13, 15, 16, 18, 19, 23",
                                     "No Treatment", label="untreated, heavily oiled plots"),
        "manual_removal_heavy": PlotGroup("manual_removal_heavy", "manual", "Heavy", "intervention", "11, 17, 20, 21, 22",
                                          "Manual Treatment", label="manual-removal, heavily oiled plots"),
        "unoiled_reference": PlotGroup("unoiled_reference", "reference_plots", "NOO", "reference", "24, 25, 26, 27, 28",
                                       "Reference", label="unoiled reference plots"),
        "mechanical_removal_heavy": PlotGroup(
            "mechanical_removal_heavy", "mechanical", "Heavy", "intervention", "1-2, 7-8, 8-9, 9-10, 16-17, 17-18, 19-20, 20-21, 22-23",
            "Mechanical Treatment", label="mechanical-removal, heavily oiled plots",
            ineligible={"cumulative_shoreline_retreat": (
                "No mechanical plot has a 4 December 2010 origin: 2 plots were first surveyed on 13 Nov 2011 (after treatment in "
                "May-June 2011) and 4 only from 2014, so cumulative retreat since the common origin is not observed. Aerial period "
                "rates remain in the dashboard recovery view.")}),
    },
)

SITES = {BAY_JIMMY_PLOTS.site_id: BAY_JIMMY_PLOTS}

# Known places that are deliberately not projection sites; each returns its own reason rather than "unknown site".
KNOWN_NON_PROJECTION_SITES = {
    "bay_jimmy_cell_8018_32612": (
        "spatial_unit_mismatch",
        "The mapped worked-example cell 8018_32612 is a 100 m NAIP edge cell. Retreat projections are built on the Bay Jimmy field "
        "plots (site_id 'bay_jimmy_zengel_plots'), a different spatial unit; the cell has its own validated edge_loss_v1 reference "
        "rate (2010-2015) in the dashboard. Plots and cell are not pooled or used to calibrate each other."),
}

# Habitats with no projection evidence: the dashboard screening remains the supported output for them.
UNSUPPORTED_HABITATS = {
    "rocky_shore": ("No habitat-specific shoreline-position series or validated recovery model exists for rocky shores in this "
                    "repository. The dashboard's rules-and-literature screening (for example ESI 1A) is the supported output; no "
                    "numerical recovery forecast is made."),
    "mangrove": ("Mangrove evidence in this repository describes an oiling effect at one site (Galeta) and is not a shoreline-retreat "
                 "series. The dashboard reports insufficient evidence for mangrove treatment comparison; no projection is made."),
    "sand_beach": ("Sand-beach evidence is surface-oil persistence (experimental), not shoreline position. No retreat projection."),
}


@dataclass(frozen=True)
class Endpoint:
    endpoint_id: str
    unit: str
    description: str
    habitats: tuple
    implemented: bool = True
    not_implemented_reason: str = ""


ENDPOINTS = {
    "cumulative_shoreline_retreat": Endpoint(
        "cumulative_shoreline_retreat", "m",
        "Group mean of plot cumulative landward marsh-edge movement since 4 December 2010; positive = land lost", ("salt_marsh",)),
    "total_vegetation_cover": Endpoint(
        "total_vegetation_cover", "percent", "Total vegetation cover of all species (plot visual estimate), not Spartina cover",
        ("salt_marsh",)),
    "soil_tpah": Endpoint(
        "soil_tpah", "mg/kg", "Soil total PAH in 0-10 cm cores (surface oil scraped aside), as reported in Zengel et al. 2015",
        ("salt_marsh",)),
}


@dataclass(frozen=True)
class AssumptionDef:
    assumption_id: str
    unit: str            # "date" for ISO date values
    description: str


ASSUMPTIONS = {
    "retreat_rate": AssumptionDef("retreat_rate", "m/yr", "Annual retreat rate applied after the as-of date (positive = land lost)"),
    "rate_change_date": AssumptionDef("rate_change_date", "date", "Date after which 'changed_retreat_rate' applies"),
    "changed_retreat_rate": AssumptionDef("changed_retreat_rate", "m/yr", "Annual retreat rate applied after 'rate_change_date'"),
    "tpah_half_life": AssumptionDef("tpah_half_life", "yr", "Assumed half-life of soil tPAH decline for the natural-recovery "
                                    "scenario of tpah_whatif/1 (zero long-term background); omitted = concentration held"),
}

# Model versions the runner can execute, and the assumptions each one uses (anything else is an input error).
MODELS = {
    "observed_record/1": "Observed group means at survey dates; no values after the as-of date",
    "rate_continuation/1": ("Conditional projection: cumulative retreat continues from the last observation on or before as_of at "
                            "the stated annual rate, optionally changing to a second rate on a stated date"),
    "field_contrast/1": ("Historical field contrast: difference of observed group means between a treated group and its comparator "
                         "at the source's survey, with the source's interval, sample sizes and design"),
    "recovery_fit/1": ("Experimental within-record fit of the group's observations available at as_of; a group with too few surveys "
                       "borrows a parameter from another group and is labelled conditional"),
    "transport_hindcast/1": ("Release-and-exposure hindcast through an optional transport adapter (contract only; no engine is "
                             "installed or evaluated). Runs only when every essential input of the case is present"),
    "retreat_whatif/1": ("Spec version 2 only. Two arms of one hypothetical shoreline from the same observed anchor: natural "
                         "recovery at the stated rate schedule (as rate_continuation/1) and a user-defined what-if that adds a "
                         "signed rate change between two dates. The technique is re-screened through the assessment on replay"),
    "cover_whatif/1": ("Spec version 2 only. Two arms of one hypothetical shoreline's total vegetation cover from the last untreated "
                       "survey available at as_of: natural recovery held at that observed value, and a user-defined temporary "
                       "change that rises linearly to a peak and returns linearly to zero. The technique is re-screened on replay"),
    "tpah_whatif/1": ("Spec version 2 only. Two arms of one hypothetical shoreline's soil tPAH (0-10 cm cores) from the last "
                      "untreated measurement available at as_of: natural recovery held, or declining with an assumed half-life "
                      "(zero long-term background), and a user-defined one-time percentage reduction on an intervention date, "
                      "after which both arms follow the same rule. The technique is re-screened on replay"),
}
MODEL_ASSUMPTIONS = {
    "observed_record/1": {"required": (), "optional": ()},
    "rate_continuation/1": {"required": ("retreat_rate",), "optional": ("rate_change_date", "changed_retreat_rate")},
    "field_contrast/1": {"required": (), "optional": ()},
    "recovery_fit/1": {"required": (), "optional": ()},
    "transport_hindcast/1": {"required": (), "optional": ()},
    "retreat_whatif/1": {"required": ("retreat_rate",), "optional": ("rate_change_date", "changed_retreat_rate")},
    "cover_whatif/1": {"required": (), "optional": ()},
    "tpah_whatif/1": {"required": (), "optional": ("tpah_half_life",)},
}
CONDITIONAL_LABEL = "Conditional projection: holds only IF the stated rate(s) apply. Not a forecast; not validated."

# (model, endpoint) pairs that run, with the evidence each one must cite.
SUPPORTED = {
    ("observed_record/1", "cumulative_shoreline_retreat"): ("zengel2022_griidc_field_positions",),
    ("rate_continuation/1", "cumulative_shoreline_retreat"): ("zengel2022_griidc_field_positions",),
    ("retreat_whatif/1", "cumulative_shoreline_retreat"): ("zengel2022_griidc_field_positions",),
    ("cover_whatif/1", "total_vegetation_cover"): ("zengel2022_griidc_vegetation", "zengel2022_griidc_field_positions"),
    ("tpah_whatif/1", "soil_tpah"): ("zengel2015_s1_group_means",),
    ("observed_record/1", "total_vegetation_cover"): ("zengel2022_griidc_vegetation", "zengel2022_griidc_field_positions"),
    ("recovery_fit/1", "total_vegetation_cover"): ("zengel2022_griidc_vegetation", "zengel2022_griidc_field_positions"),
    ("field_contrast/1", "total_vegetation_cover"): ("zengel2015_s1_group_means",),
    ("observed_record/1", "soil_tpah"): ("zengel2015_s1_group_means", "pah_decline_v1_heavy_class"),
}

PAH_TREATMENT_GAP = (
    "Treatment-specific future PAH decline is not supported by the evidence. The Bay Jimmy plots have tPAH at only two dates "
    "(July-August 2011 and September 2012; mechanical plots 2012 only), so no plot or treatment decline rate is identified, and the "
    "DIVER decline model (pah_decline_v1) has no treatment variable and describes the PAH sum (physical loss as well as degradation). "
    "Evidence needed: PAH on treated and untreated plots at three or more dates, or a PAH model with a treatment variable. The "
    "historical tPAH measurements are exported with this record (observed.csv), and the DIVER class index is available from "
    "observed_record/1.")
VEG_FUTURE_GAP = (
    "Future vegetation cover is not projected. Plot surveys end in September 2016 (manual plots in September 2012); the logistic fit "
    "already misses the 2016 decline that the reference plots share, and no later surveys or independent site test the rate. The "
    "historical cover is exported with this record (observed.csv); the within-record fit is available from recovery_fit/1.")

# (model, endpoint) pairs that do not run. "evidence_gap" also exports the historical observations of the endpoint.
GAPS = {
    ("rate_continuation/1", "soil_tpah"): ("evidence_gap", PAH_TREATMENT_GAP),
    ("recovery_fit/1", "soil_tpah"): ("evidence_gap", PAH_TREATMENT_GAP),
    ("rate_continuation/1", "total_vegetation_cover"): ("evidence_gap", VEG_FUTURE_GAP),
    ("field_contrast/1", "cumulative_shoreline_retreat"): (
        "evidence_gap", "No field contrast of cumulative retreat since December 2010 is defined: the available treatment contrasts are "
        "changes in aerial-photograph erosion rates (2010-2012 and 2012-2018 against 2005-2010), a different endpoint, shown in the "
        "dashboard comparison layer. The observed cumulative retreat of each group is exported with this record."),
    ("field_contrast/1", "soil_tpah"): (
        "evidence_gap", "No tPAH treatment contrast is defined in the comparison layer. Group means differ by an order of magnitude "
        "between plots within a group and cores were taken on two dates only. The measurements are exported with this record."),
    ("recovery_fit/1", "cumulative_shoreline_retreat"): (
        "model_not_available_for_endpoint", "Retreat fits (M0/M1) are shown in the dashboard; for projections from the observed "
        "record use rate_continuation/1."),
}

# Sources a (model, endpoint) run reads beyond those the scenario must cite. The runner adds them to the manifest (with checksums)
# itself, so existing scenario files stay valid and replayable. evidence_id -> what it is read for.
DEPENDENCIES = {
    ("field_contrast/1", "total_vegetation_cover"): {
        "zengel2022_griidc_vegetation": "plot membership: plot-level total-cover records of each group at the 2012 survey",
        "zengel2022_griidc_field_positions": "plot types (sheet 'DSAS lumped') that assign the vegetation plots to groups",
    },
}

# Historical contrasts available through the comparison layer: (endpoint, treated group, comparator) -> comparison option code.
CONTRASTS = {
    ("total_vegetation_cover", "manual_removal_heavy", "untreated_heavy"): "manual_removal",
    ("total_vegetation_cover", "mechanical_removal_heavy", "untreated_heavy"): "mechanical_removal",
}

# (model, group) pairs that do not apply, with the reason.
GROUP_MODEL_GAPS = {
    ("recovery_fit/1", "unoiled_reference"): (
        "The reference plots define the ceiling K of the recovery curve (their mean cover); they have no recovery curve of their own. "
        "Their observed cover is available from observed_record/1."),
}


# ---------------------------------------------------------------------------------------------------------------
# Release-and-exposure scenarios (Session 5). Contract and inventory only: no transport engine is installed or imported.

EXPOSURE_ENDPOINT = "shoreline_oil_contact"
ENDPOINTS[EXPOSURE_ENDPOINT] = Endpoint(
    EXPOSURE_ENDPOINT, "contact",
    "Whether and when oil reaches a shoreline segment: per segment, contact (yes/no), arrival window, estimated exposure",
    ("gulf_shoreline_mixed_esi",))

# Outcome codes of an exposure request. 'no_contact' is reserved for a transport simulation that COMPLETED and placed no oil
# on the segment; it is never used for missing inputs, a failed run, a domain problem or a survey that observed no oil.
EXPOSURE_OUTCOMES = {
    "contact": "completed simulation: oil reached the segment (arrival window and exposure reported)",
    "no_contact": "completed simulation: no simulated oil reached the segment within the window (reserved; requires a completed run)",
    "exposure_inputs_unavailable": "essential release or forcing inputs are missing; no simulation was attempted",
    "model_failed": "the transport adapter raised or returned an invalid result",
    "outside_domain": "the release or shoreline lies outside the forcing grid or the adapter's domain",
}


@dataclass(frozen=True)
class ExposureInput:
    name: str
    essential: bool
    status: str          # present | partial | proxy | absent
    found: str           # what exists in this checkout (path and provenance), or "none"
    variables_units: str
    dates: str
    coverage: str
    case_overlap: str    # does it overlap the case's time window and region


@dataclass(frozen=True)
class ExposureCase:
    case_id: str
    label: str
    habitat: str
    region: str
    bbox_lon_lat: tuple          # (lon_min, lon_max, lat_min, lat_max) of the surveyed segment midpoints
    window: tuple                # (scenario start = release start, end) as ISO dates
    inputs: tuple

    def missing_essential(self) -> list:
        return [i for i in self.inputs if i.essential and i.status in ("absent", "partial", "proxy")]


DWH_MOBILE_2010 = ExposureCase(
    "dwh_mobile_sector_2010",
    "Deepwater Horizon (MC252) release, 2010; shorelines of the Mobile ICP sector (Mississippi, Alabama, Florida panhandle)",
    "gulf_shoreline_mixed_esi",
    "SCAT segments of the Mobile Incident Command Post: MS, AL and FL panhandle; ESI 3A sand beach dominant, plus marsh and "
    "armoured shore",
    (-89.5287, -84.1790, 29.5874, 30.5217),
    ("2010-04-20", "2010-08-31"),
    (
        ExposureInput("release_location", True, "absent", "none (MC252 well position appears only in literature text, not as data)",
                      "lon/lat, depth (m)", "-", "-", "cannot be checked"),
        ExposureInput("release_timing", True, "partial",
                      "start date 2010-04-20 only, as code constants (scripts/build_beach_series.py SPILL_START; recovery_view.SPILL_YEAR); "
                      "no dated release or capping record", "datetime", "start only; end of release not recorded", "-",
                      "start matches the window; duration unknown"),
        ExposureInput("release_amount_or_rate", True, "absent", "none", "m3/day or bbl/day (time series)", "-", "-", "cannot be checked"),
        ExposureInput("oil_type", True, "proxy",
                      "data/oil_properties.csv (NOAA ADIOS export): no MC252 record; generic 'South Louisiana' crudes AD01025 (API 37.0, "
                      "1996), EC00696 (33.7, 2021), EC00698 (37.1, 2021) disagree", "API gravity, density kg/m3, viscosity cSt, pour point C",
                      "reference years 1996 and 2021", "not location-specific", "proxy only; weathering state at landfall not represented"),
        ExposureInput("wind_fields", True, "absent", "none (no NetCDF/GRIB or station file in the checkout)", "u, v (m/s), gridded or station",
                      "-", "-", "cannot be checked"),
        ExposureInput("current_fields", True, "absent", "none", "u, v (m/s), gridded ocean model or HF radar", "-", "-",
                      "cannot be checked"),
        ExposureInput("shoreline_geometry", True, "partial",
                      "data/external/scat_dwh_mobile/beach_series.csv: segment midpoints (lon/lat) and lengths for 3,007 segments; "
                      "the raw SCAT shapefile (data/raw/scat_mobile) is not in this checkout. Chandeleur shorelines 2012-2017 are "
                      "post-event and outside the region", "midpoint lon/lat (EPSG:4326), length m", "segments as of the 27 Sep 2014 layer",
                      "MS, AL, FL panhandle", "segments overlap the region; no line geometry for contact testing"),
        ExposureInput("dated_shoreline_surveys", True, "present",
                      "data/external/scat_dwh_mobile/beach_visits.csv (NCEI 0163818 v1.1, layer 18613; derived visit table)",
                      "status oiled / clear / partial_clear per segment and survey date; top oiling category", "2010-05-05 to 2013-06-18",
                      "3,007 segments, MS AL FL", "overlaps the window from 2010-05-05"),
    ),
)
EXPOSURE_CASES = {DWH_MOBILE_2010.case_id: DWH_MOBILE_2010}
EXPOSURE_GROUP = "all_surveyed_segments"
EXPOSURE_OILING = "not_applicable"
EXPOSURE_EVIDENCE = ("noaa_scat_mobile_visits", "noaa_scat_mobile_segments")
