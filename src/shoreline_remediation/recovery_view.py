"""Bay Jimmy recovery view (data layer; no Streamlit, no drawing). Replaces the synthetic recovery display with values that can be
traced to a source. Every series carries its outcome, unit, time support, comparator or identity, source, evidence status and
interval type, so the figure, its captions and the tests read the same records.

What is shown, and why only that (audit in docs/V5_4_RECOVERY_VIEW.md)
- Erosion rate, m/yr: the scenario composer's absolute rates (clean-edge baseline + oil excess + treatment shift; EXPERIMENTAL, heavy-cell
  bias gates failed) drawn as period steps 2010-2012 and 2012-2018, the supported horizon; Zengel et al. (2022) absolute plot-group
  means at the same periods (field observations); and the deployed edge_loss_v1 reference and the cell's observed rate, kept apart
  because the deployed model has no oiling term. No published treatment contrast is added to it.
- Total vegetation cover, %: Zengel et al. (2015) absolute group means at the 2011 and 2012 surveys, with 90% t intervals of the
  group mean. The composer's cover ratio (to reference marsh) is NOT converted: its untreated year-2 value, applied to the Bay Jimmy
  reference cover, gives about 81% against 18% observed on untreated oiled plots.
- Soil PAH: Zengel et al. (2015) tPAH in mg/kg for untreated and treated plots (2011 and 2012), and, in a separate chart because
  the unit differs, the DIVER soil PAH-sum decline reference by oiling class as an index (100 at the first sampling campaign).
  The decline model has no treatment variable and is not called untreated.
Nothing is extrapolated past the supported period, and no synthetic value is used here.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from src.shoreline_remediation import treatment_effects as te

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGNS = ROOT / "results" / "pah_decline" / "station_campaign.csv"
PAH_CARD = ROOT / "models" / "pah_decline_v1.json"
SPILL_YEAR = 2010.30            # 20 April 2010; the PAH model's origin ("years since April 2010")
BAY_JIMMY = "Bay Jimmy, northern Barataria Bay"
BAY_JIMMY_SCOPE = "Heavily oiled salt marsh, Bay Jimmy; Deepwater Horizon (2010); one site, 5 to 9 plots per group"
N_DRAWS = 3000
PLANTING = "planting (after mechanical cleanup)"

# Series keys, labels and the colours shared by every panel and by the legend.
UNTREATED, MANUAL, MECHANICAL, PLANTED = "untreated", "manual", "mechanical", "planted"
DEPLOYED, OBSERVED, PAH_CLASS = "deployed", "observed_cell", "pah_class"
LABELS = {UNTREATED: "Untreated baseline", MANUAL: "Manual removal", MECHANICAL: "Mechanical removal",
          PLANTED: "Mechanical removal, then planting", DEPLOYED: "Deployed model (no oiling term)", OBSERVED: "Observed at this cell",
          PAH_CLASS: "Class decline reference (all management)"}
COLOURS = {UNTREATED: "#A6B2C2", MANUAL: "#28B8A5", MECHANICAL: "#E0A83A", PLANTED: "#D07BA8", DEPLOYED: "#4E9BE8", OBSERVED: "#F4F7FA",
           PAH_CLASS: "#B6D9CF"}
OPTION_OF = {MANUAL: "manual_removal", MECHANICAL: "mechanical_removal", PLANTED: PLANTING}
# kinds: how the values were obtained. They decide the mark in the figure.
FIELD, SCENARIO, REFERENCE, OBSERVATION, DECLINE = "field", "scenario", "reference", "observation", "decline"
KIND_TEXT = {FIELD: "Field observation (plot-group mean)", SCENARIO: "Experimental scenario (model)",
             REFERENCE: "Fitted reference (model)", OBSERVATION: "Field observation (one cell)", DECLINE: "Fitted decline reference (model)"}
COMPOSER_GATE = ("Experimental scenario: the composer's heavy-cell bias gates failed (R3 +0.55 m/yr, D32 +0.33 m/yr over-prediction against "
                 "observed aerial-image loss); treat the levels as scenario values, not forecasts.")
SHARED_SOURCE = ("The field points and the composer's treatment terms come from the same Zengel et al. plots, so the field points are not "
                 "independent evaluation of the scenario values.")


@dataclass(frozen=True)
class Point:
    x0: float                        # start of the supported time (calendar year, decimal)
    x1: float                        # end; equal to x0 for a survey date
    value: float
    lo: float | None = None
    hi: float | None = None


@dataclass(frozen=True)
class Series:
    panel: str
    key: str                         # colour key
    label: str
    kind: str
    outcome: str
    unit: str
    points: tuple
    time_support: str
    comparator: str                  # identity of the series: untreated, treatment sequence, reference
    interval: str                    # "" when no interval is drawn; else its type and level
    source: str
    evidence: str                    # evidence status in one phrase
    scope: str
    screening: str = ""              # decision-report category label of the treatment option, where there is one

    @property
    def is_period(self) -> bool:
        return any(p.x1 > p.x0 for p in self.points)


@dataclass
class Panel:
    key: str
    title: str
    unit: str
    series: list = field(default_factory=list)
    note: str = ""                   # limitation line under the panel
    unavailable: str = ""            # shown instead of a chart when nothing is supported
    missing: list = field(default_factory=list)   # (series, evidence needed)
    sub: str = ""                    # "pah_index" for the separate PAH decline chart


@dataclass
class RecoveryView:
    cell: str
    oiling: str
    panels: list
    notes: list = field(default_factory=list)
    statuses: dict = field(default_factory=dict)  # option code -> screening category label

    def panel(self, key: str) -> Panel:
        return next(p for p in self.panels if p.key == key)

    def all_series(self) -> list:
        return [s for p in self.panels for s in p.series]


def _finite(x) -> bool:
    return isinstance(x, (int, float, np.floating)) and not isinstance(x, bool) and math.isfinite(float(x))


def _t90(mean: float, se: float, n: int, floor0: bool = True) -> tuple:
    """90% t interval of a group mean from its standard error and n. Cover and concentration cannot be negative: the lower limit is
    cut at 0 (the cut is stated in the panel note)."""
    h = float(stats.t.ppf(0.95, n - 1)) * se
    return (max(0.0, mean - h) if floor0 else mean - h), mean + h


# ---------------------------------------------------------------------------------------------------------------
# Erosion

@lru_cache(maxsize=8)
def _compose_cached(site_items: tuple, heavy: bool) -> pd.DataFrame:
    from src.shoreline_remediation import scenario_composer as sc
    tidy, _ = sc.compose(dict(site_items), ["manual_removal", "mechanical_removal", PLANTING] if heavy else [], horizon_years=8, n_draws=N_DRAWS)
    return tidy[tidy.outcome == "edge_loss_rate_m_per_yr"].reset_index(drop=True)


@lru_cache(maxsize=1)
def _erosion_plot_table() -> pd.DataFrame:
    d = pd.read_excel(te.EROSION_DATA, sheet_name="DSAS lumped")
    d["group"] = d.PLOT_TYPE.str.strip().map(te.EROSION_GROUPS)
    return d.pivot_table(index=["PLOT_ID", "group"], columns="TIME_PERIOD", values="EROSION_RATE").reset_index()


COMPOSER_KEYS = {"natural_attenuation": UNTREATED, "manual_removal": MANUAL, "mechanical_removal": MECHANICAL, PLANTING: PLANTED}
FIELD_GROUPS = {"none": UNTREATED, "manual": MANUAL, "mechanical": MECHANICAL, "mechanical+planting": PLANTED}
PERIODS = {"2010-2012": (2010.0, 2012.0, 1), "2012-2018": (2012.0, 2018.0, 3)}     # period -> (x0, x1, composer year inside it)
COMPARATORS = {UNTREATED: "untreated oiled recovery", MANUAL: "manual removal", MECHANICAL: "mechanical removal",
               PLANTED: "mechanical removal followed by planting (a historical sequence)"}


def erosion_panel(site: dict, heavy: bool, statuses: dict, deployed: dict | None, observed: float | None) -> Panel:
    p = Panel("erosion", "Marsh-edge erosion rate", "m/yr",
              note="Positive = land lost. Steps cover the period the source reports (2010-2012, 2012-2018); nothing is drawn after 2018.")
    items = tuple(sorted((k, v) for k, v in site.items() if k in ("water_1km_2010", "water_250m_2010", "fetch_mean_m", "pre_rate", "max_oiling")))
    tidy = _compose_cached(items, heavy)
    for opt, key in COMPOSER_KEYS.items():
        t = tidy[tidy.option == opt]
        if t.empty:
            continue
        pts = []
        for per, (x0, x1, y) in PERIODS.items():
            r = t[t.year == y].iloc[0]
            pts.append(Point(x0, x1, float(r["median"]), float(r.lo90), float(r.hi90)))
        p.series.append(Series("erosion", key, LABELS[key], SCENARIO, "marsh-edge erosion rate", "m/yr", tuple(pts), "2010-2012 and 2012-2018 (model horizon 8 years)",
                               COMPARATORS[key], "90% simulation interval (5th to 95th percentile of the composer's joint draws: baseline residual, oil excess, "
                               "treatment shift) of the absolute rate; not an interval for a difference between methods",
                               "Scenario composer (scenario_composer.compose; clean-edge baseline p5-edge-loss-clean-v1 + Zengel 2022 oil excess + treatment shift)",
                               "Experimental (composer_natural_recovery_v1; heavy-cell bias gates failed)", "Model cell " + str(site.get("cell", "")),
                               statuses.get(OPTION_OF.get(key, ""), "")))
    if heavy:
        w = _erosion_plot_table()
        for group, key in FIELD_GROUPS.items():
            g = w[w.group == group]
            pts = []
            for per, (x0, x1, _) in PERIODS.items():
                v = g[per].dropna()
                if len(v) < 2:
                    continue
                m, se = float(v.mean()), float(v.std(ddof=1) / math.sqrt(len(v)))
                lo, hi = _t90(m, se, len(v), floor0=False)
                pts.append(Point(x0, x1, m, lo, hi))
            if pts:
                p.series.append(Series("erosion", key, LABELS[key] + " (field plots)", FIELD, "marsh-edge erosion rate", "m/yr", tuple(pts),
                                       "Plotted at the middle of each period; each value is the period's mean rate", COMPARATORS[key],
                                       "90% t interval of the group mean (5 to 9 plots)", te.EROSION_DATA.name + " (Zengel et al. 2022, GRIIDC doi:10.7266/VF524143), aerial-photograph rates",
                                       "Field observation, observational comparison", BAY_JIMMY_SCOPE, statuses.get(OPTION_OF.get(key, ""), "")))
    if deployed and _finite(deployed.get("value")):
        p.series.append(Series("erosion", DEPLOYED, LABELS[DEPLOYED], REFERENCE, "marsh-edge erosion rate", "m/yr",
                               (Point(2010.0, 2015.0, float(deployed["value"]), deployed.get("lo90"), deployed.get("hi90")),),
                               "2010-2015 (NAIP land change)", "natural (no oiling term); not the untreated oiled rate", "90% interval for one 100 m cell (pooled leave-one-basin-out residuals)",
                               "edge_loss_v1 (deployed all-cell fit), value from the assessment report", "Validated reference within three Louisiana basins; interval not independently validated",
                               "Model cell " + str(site.get("cell", ""))))
    if _finite(observed):
        p.series.append(Series("erosion", OBSERVED, LABELS[OBSERVED], OBSERVATION, "marsh-edge erosion rate", "m/yr",
                               (Point(2010.0, 2015.0, float(observed)),), "2010-2015 (NAIP aerial images)", "this 100 m cell; includes any oiling effect", "",
                               "data/demo/p5_sites.csv observed_rate", "Field observation (aerial images read about 1.2 m/yr below field erosion measurements)",
                               "Model cell " + str(site.get("cell", ""))))
    p.missing = [("Treatment series beyond 2018", "a published treated-and-untreated comparison with later surveys, or a validated erosion model with a treatment term"),
                 ("Composer levels as validated forecasts", "pass the heavy-cell bias gates (R3 and D32) on held-out basins")]
    return p


# ---------------------------------------------------------------------------------------------------------------
# Vegetation and PAH field summaries (Zengel et al. 2015, absolute group means)

FIELD_NAMES = {"No Treatment": UNTREATED, "Manual Treatment": MANUAL, "Mechanical Treatment": MECHANICAL}
YEAR_OF_SURVEY = {2011: 2011.0, 2012: 2012.0}


def _group_series(panel: str, metric: str, outcome: str, unit: str, statuses: dict) -> list:
    raw = te.load()
    out = []
    for name, key in FIELD_NAMES.items():
        pts = []
        for year, x in YEAR_OF_SURVEY.items():
            r = raw[(raw.study == "main") & (raw.year == year) & (raw.metric == metric) & (raw.treatment == name)]
            if r.empty or not _finite(r.iloc[0]["mean"]) or not _finite(r.iloc[0]["se"]) or not _finite(r.iloc[0]["n"]):
                continue
            r = r.iloc[0]
            lo, hi = _t90(float(r["mean"]), float(r.se), int(r.n))
            pts.append(Point(x, x, float(r["mean"]), lo, hi))
        if pts:
            out.append(Series(panel, key, LABELS[key], FIELD, outcome, unit, tuple(pts), "Survey years 2011 and 2012 (about 1 and 2 years after oiling began in 2010)",
                              COMPARATORS[key], "90% t interval of the group mean (n = 5 to 9 plots; lower limit cut at 0)",
                              "zengel2015_group_means.csv (Zengel et al. 2015, PLoS ONE 10(7): e0132324, S1 Table)", "Field observation, observational comparison",
                              BAY_JIMMY_SCOPE, statuses.get(OPTION_OF.get(key, ""), "")))
    return out


def vegetation_panel(statuses: dict) -> Panel:
    p = Panel("vegetation", "Total vegetation cover", "%",
              note="Two survey years only, so points rather than curves. Lower interval limits are cut at 0%. Reference marsh (unoiled) cover was 96% in 2011 and 95% in 2012.")
    p.series = _group_series("vegetation", "Total Vegetation Cover (%)", "total vegetation cover", "%", statuses)
    p.missing = [("Planting, total cover", "total cover of planted plots: the source reports Spartina cover only (69% planted against 0% unplanted, an incremental contrast)"),
                 ("Absolute cover from the composer or vegetation curve", "a vegetation model validated for heavy oiling whose ratio denominator is the same reference cover; the curve's untreated year-2 ratio of 0.86 would give about 81% against the 18% observed"),
                 ("Treatments after 2012", "a later survey of the same plots")]
    return p


def pah_field_panel(statuses: dict) -> Panel:
    p = Panel("pah", "Soil PAH, concentration", "mg/kg",
              note="Total PAH (tPAH) as reported in the source table; the dry or wet basis is not recorded in the repository table. Group means vary widely between plots; lower limits are cut at 0. Mechanical removal was not sampled in 2011.")
    p.series = _group_series("pah", "tPAH (mg/kg)", "soil tPAH concentration", "mg/kg", statuses)
    return p


@lru_cache(maxsize=4)
def _pah_support(oiling_class: str) -> tuple | None:
    if not CAMPAIGNS.exists():
        return None
    d = pd.read_csv(CAMPAIGNS)
    d = d[d.oil_class == oiling_class.lower()]
    if d.empty:
        return None
    med = d.groupby("campaign").t.median()
    return float(med.min()), float(med.max())


def pah_decline_panel(oiling: str) -> Panel:
    """DIVER soil PAH-sum decline reference for the cell's SCAT class: index 100 at the first sampling campaign, first-order decline
    with the class decline rate k and its 90% interval. No treatment variable; supported only between the first and last campaign."""
    p = Panel("pah_index", "Soil PAH sum, decline reference", "index",
              note="Index 100 = first sampling campaign. The interval is the 90% interval of the class decline rate, not a prediction interval for a station. The sum falls by physical loss as well as degradation.",
              sub="pah_index")
    card = json.loads(PAH_CARD.read_text(encoding="utf-8"))
    row = card["half_life_years_by_class"].get(str(oiling).lower().replace("very light", "very_light"))
    support = _pah_support(str(oiling))
    if not row or support is None or not _finite(row.get("half_life")) or not _finite(row.get("hi90")) or not _finite(row.get("lo90")):
        p.unavailable = (f"No supported PAH decline for {oiling} oiling: the class decline rate is not distinguished from zero or its interval is open.")
        return p
    k, k_lo, k_hi = float(row["k_per_year"]), math.log(2) / float(row["hi90"]), math.log(2) / float(row["lo90"])
    t0, t1 = support
    pts = []
    for t in np.linspace(t0, t1, 15):
        dt = float(t - t0)
        x = SPILL_YEAR + float(t)
        pts.append(Point(x, x, 100.0 * math.exp(-k * dt), 100.0 * math.exp(-k_hi * dt), 100.0 * math.exp(-k_lo * dt)))
    p.series.append(Series("pah_index", PAH_CLASS, LABELS[PAH_CLASS], DECLINE, "soil PAH-sum, relative to the first campaign", "index (first campaign = 100)", tuple(pts),
                           f"First to last sampling campaign (years since April 2010: {t0:.1f} to {t1:.1f}; spring 2011 to fall 2013)",
                           "all management and natural loss at DIVER stations of this SCAT class; no treatment variable, so not labelled untreated",
                           "90% interval of the class decline rate k (half-life 90% interval), applied to the index",
                           "pah_decline_v1 (results/pah_decline/by_oiling_class.csv; models/pah_decline_v1.json)",
                           "Validated within Deepwater Horizon only (held-out stations); a decline of the sum, not shown degradation",
                           f"{oiling} oiling class, northern Gulf marsh, one spill"))
    return p


def build(site_row: dict | None, report, statuses: dict | None = None, deployed: dict | None = None) -> RecoveryView | None:
    """The recovery view for ONE in-scope mapped cell, or None (typed site, habitat-level run, out-of-scope cell). Treatment series and the
    Bay Jimmy field summaries are used only for heavily oiled cells; any other class gets the untreated composer scenario only."""
    if not site_row or site_row.get("status") != "in_scope":
        return None
    site = {k: v for k, v in site_row.items() if v == v and v is not None}
    oiling = str(site.get("max_oiling", ""))
    heavy = oiling == "Heavy"
    statuses = dict(statuses or {})
    observed = site.get("observed_rate")
    panels = [erosion_panel(site, heavy, statuses, deployed, float(observed) if _finite(observed) else None)]
    if heavy:
        panels += [vegetation_panel(statuses), pah_field_panel(statuses)]
    else:
        panels += [Panel("vegetation", "Total vegetation cover", "%", unavailable="Treatment-specific vegetation cover is unavailable: the field plots are heavily oiled marsh only."),
                   Panel("pah", "Soil PAH, concentration", "mg/kg", unavailable="Treatment-specific PAH estimates are unavailable: the field plots are heavily oiled marsh only.")]
    panels.append(pah_decline_panel(oiling.replace("_", " ")))
    pah = panels[2]
    if heavy and pah.series:
        pah.missing = [("Treatment-specific PAH decline curve", "PAH measured on treated and untreated plots at three or more times, or a PAH model with a treatment variable"),
                       ("Starting concentration for the decline reference", "an absolute PAH-sum concentration at the first campaign for this class in the same units as the sum")]
    return RecoveryView(str(site.get("cell", "")), oiling, panels, [COMPOSER_GATE, SHARED_SOURCE], statuses)
