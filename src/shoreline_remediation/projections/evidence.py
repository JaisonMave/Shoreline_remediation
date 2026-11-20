"""Historical evidence exports for the research runner: vegetation cover, soil tPAH, the DIVER decline index and field contrasts.

Each function returns tidy rows that answer, on their own: what was measured, at which plots and dates, compared with what, and
which values depend on an assumption. Values come from the existing loaders and comparison layer; nothing is typed in here.

- Vegetation observations: recovery_trajectories.vegetation_plots() (GRIIDC compiled dataset, plot-year total cover).
- Vegetation fits: recovery_trajectories._veg_fit (the dashboard's logistic form), refitted on the surveys available at as_of.
- Field contrasts: comparison.vegetation_year2_estimates() (Zengel et al. 2015 S1 Table, Welch interval).
- tPAH: treatment_effects.load() (S1 Table group means). DIVER index: recovery_view.pah_decline_panel().

Survey dates: vegetation September 2011 and 2012 and tPAH July-August 2011 / September 2012 are verified in the Zengel et al. 2015
full text; the September month of the 2013-2016 vegetation surveys is assumed (docs/V5_4_RECOVERY_VIEW.md). An observation is
available at as_of only after the last day of its survey period, because the day is not recorded.
"""
from __future__ import annotations

import calendar
import datetime as dt

import numpy as np
import pandas as pd

from src.shoreline_remediation.projections import catalogue as C

VEG_PERIOD = {2011: ("September 2011", "verified (Zengel et al. 2015 Methods)"), 2012: ("September 2012", "verified (Zengel et al. 2015 Methods)")}
PAH_PERIOD = {2011: ("July-August 2011", 7, 8), 2012: ("September 2012", 9, 9)}
TPAH_DEPTH = "0-10 cm cores, surface oil scraped aside"
TPAH_ANALYTE = "tPAH as reported in the Zengel et al. 2015 S1 Table (43 to 45 compounds); dry or wet basis not recorded in the repository table"
DIVER_ANALYTE = "PAH sum (58 compounds), mostly 0-2 cm sediment grabs, DIVER stations of the heavy SCAT oiling class across the northern Gulf"
NO_INTERVAL = "no interval: point fit on the surveys available at as_of (the dashboard's 400-refit bootstrap band uses all surveys)"


def month_end(year: int, month: int) -> dt.date:
    return dt.date(year, month, calendar.monthrange(year, month)[1])


def _common(spec, record_type: str, evidence_id: str) -> dict:
    return {"scenario_id": spec.scenario_id, "site_id": spec.site_id, "endpoint": spec.endpoint, "record_type": record_type,
            "record_class": C.RECORD_TYPES[record_type], "evidence_id": evidence_id, "shared_plots": C.SHARED_PLOTS_NOTE}


def _group(spec, group_id: str | None = None) -> C.PlotGroup:
    return C.SITES[spec.site_id].plot_groups[group_id or spec.plot_group_id]


# ---- vegetation ---------------------------------------------------------------------------------------------------

def _veg_plots() -> pd.DataFrame:
    from src.shoreline_remediation import recovery_trajectories as T
    v = T.vegetation_plots().copy()
    v["available_from"] = v.Year.map(lambda y: month_end(int(y), 9))
    return v


def vegetation_observed(spec) -> pd.DataFrame:
    """Group means of plot-level total cover at each survey of the requested group (90% t interval, cut to 0-100)."""
    from src.shoreline_remediation import recovery_trajectories as T
    g = _group(spec)
    v = _veg_plots()
    v = v[v.key == g.loader_key]
    rows = []
    for year, s in v.groupby("Year"):
        m, lo, hi = T._t90(s.cover.values, 0.0, 100.0)
        period, basis = VEG_PERIOD.get(int(year), (f"September {int(year)}", "assumed (survey month not recorded in the sources examined)"))
        rows.append({**_common(spec, "observed_group_mean", "zengel2022_griidc_vegetation"),
                     "plot_group_id": g.group_id, "plots": ", ".join(sorted(s.pid.unique(), key=_plot_sort)),
                     "plot_membership": f"GRIIDC compiled dataset plot-level records at the {int(year)} survey",
                     "n_plots": int(s.pid.nunique()),
                     "survey_period": period, "date": f"{int(year)}-09", "date_precision": "month", "date_basis": basis,
                     "decimal_year": float(s.x.iloc[0]), "available_from": month_end(int(year), 9).isoformat(),
                     "available_at_as_of": month_end(int(year), 9) <= spec.as_of_date,
                     "value": m, "unit": "percent", "interval_lo": lo, "interval_hi": hi,
                     "interval_method": "90% t interval of the mean of plot values, cut to 0-100" if len(s) > 1 else "",
                     "derivation": "mean of plot visual estimates of total cover (all species)",
                     "note": ("2011-2012 means reproduce the Zengel et al. 2015 S1 Table group means (same plots)" if year <= 2012 else
                              "later surveys may follow fewer plots of the group")})
    return pd.DataFrame(rows)


def plot_membership(group, endpoint: str, year: int, n: int) -> tuple:
    """(plot IDs, basis) for a published group summary of `n` plots at one survey. IDs are exported only where a source establishes
    which plots were measured for that survey and endpoint; otherwise the IDs are blank and the basis says why."""
    if endpoint == "total_vegetation_cover":
        v = _veg_plots()
        pids = sorted(v[(v.key == group.loader_key) & (v.Year == year)].pid.unique(), key=_plot_sort)
        if len(pids) == n:
            return ", ".join(pids), (f"GRIIDC compiled dataset has plot-level records for these {n} plots at the {year} survey "
                                     "(count matches the published n)")
        return None, (f"not established: the published n is {n}, the GRIIDC dataset has {len(pids)} plot records for {year}")
    members = [p for p in group.plots.split(", ") if p]
    if len(members) == n:
        return group.plots, f"n = {n} equals the whole group, so every plot of the group (Zengel et al. 2022 plot types)"
    return None, (f"not established by the source: the S1 Table gives n = {n} of the {len(members)} {group.group_id} plots and "
                  f"does not record which were sampled for {endpoint} in {year}")


def _plot_sort(p: str):
    head = p.split("-")[0]
    return (int(head) if head.isdigit() else 999, p)


def vegetation_fit(spec) -> tuple:
    """(rows, manifest block) or (None, Unsupported). Logistic C(t) = K / (1 + exp(-r (t - t50))) on surveys available at as_of.
    K = mean cover of the reference plots; the untreated and mechanical groups estimate r and t50; the manual group (two surveys)
    estimates t50 given the untreated r, and every value after its last survey is a conditional projection."""
    from src.shoreline_remediation import recovery_trajectories as T
    from src.shoreline_remediation.projections.spec import Unsupported
    g = _group(spec)
    v = _veg_plots()
    v = v[v.available_from <= spec.as_of_date]
    ref, unt, own = v[v.key == "reference_plots"], v[v.key == "untreated"], v[v.key == g.loader_key]
    if ref.empty or unt.Year.nunique() < 3 or own.empty:
        return None, Unsupported("insufficient_surveys_for_fit", f"At as_of {spec.as_of} the fit needs reference plots and at least "
                                 f"three untreated survey years; available: untreated {sorted(unt.Year.unique().tolist())}, "
                                 f"{g.group_id} {sorted(own.Year.unique().tolist())}.", "as_of")
    k = float(ref.cover.mean())
    th_u = T._veg_fit(unt, k)
    if th_u is None:
        raise RuntimeError("Untreated vegetation fit did not converge")
    borrowed = g.group_id != "untreated_heavy" and own.Year.nunique() < 3
    if g.group_id == "untreated_heavy":
        th = th_u
    elif borrowed:
        th = T._veg_fit(own, k, r=th_u[0])
    else:
        th = T._veg_fit(own, k)
    if th is None:
        raise RuntimeError(f"Vegetation fit did not converge for {g.group_id}")
    x_first, x_own_last, x_end = float(own.x.min()), float(own.x.max()), float(unt.x.max())
    x_stop = x_end if borrowed else x_own_last          # nothing beyond the last available untreated survey
    grid = sorted(set(np.round(np.arange(x_first, x_stop + 1e-9, 0.25), 4)) | set(own.x.unique()) | ({x_end} if borrowed else set()))
    status = ("Experimental fit of this group's surveys" if not borrowed else
              "Experimental fit (t50 fitted to this group's surveys given the borrowed rate r)")
    rows = []
    for x in grid:
        after = borrowed and x > x_own_last + 1e-9
        rt = "conditional_projection" if after else "experimental_fit"
        rows.append({**_common(spec, rt, "zengel2022_griidc_vegetation"), "plot_group_id": g.group_id, "decimal_year": float(x),
                     "value": float(T._logistic(np.array([x]), th[0], th[1], k)[0]), "unit": "percent",
                     "interval_lo": None, "interval_hi": None, "interval_method": NO_INTERVAL,
                     "equation": T.VEG_EQ, "r_per_yr": float(th[0]), "t50_year": float(th[1]), "K_percent": k,
                     "rate_origin": ("borrowed from untreated_heavy fit" if borrowed else "estimated from this group's plots"),
                     "borrowing_begins": (f"{_ym(x_own_last)} (last survey of this group)" if borrowed else ""),
                     "status_label": ("Conditional: IF this group followed the untreated recovery rate after its last survey. Not a "
                                      "forecast; not validated." if after else status + "; describes the surveyed period only.")})
    block = {
        "equation": T.VEG_EQ, "as_of": spec.as_of,
        "data_used": {"reference_plot_years": int(len(ref)), "untreated_survey_years": sorted(int(y) for y in unt.Year.unique()),
                      "group_survey_years": sorted(int(y) for y in own.Year.unique()), "group_plots": int(own.pid.nunique())},
        "parameters": [{"name": "K", "value": k, "unit": "percent", "origin": "fitted_parameter",
                        "source": "mean total cover of reference plots 24-28 at the surveys available at as_of"},
                       {"name": "r", "value": float(th[0]), "unit": "per yr", "origin": "fitted_parameter",
                        "source": "untreated_heavy plots" if (borrowed or g.group_id == "untreated_heavy") else f"{g.group_id} plots"},
                       {"name": "t50", "value": float(th[1]), "unit": "year", "origin": "fitted_parameter",
                        "source": f"{g.group_id} plots" + (" given the borrowed r" if borrowed else "")}],
        "borrowing": ({"parameter": "r", "from_group": "untreated_heavy", "value": float(th_u[0]),
                       "begins": f"{_ym(x_own_last)} (decimal {x_own_last:.2f}), after the last survey of {g.group_id}",
                       "ends": f"{_ym(x_end)} (last untreated survey available at as_of)",
                       "status": "conditional_projection"} if borrowed else None),
        "not_drawn": "No value after the last untreated survey available at as_of: " + C.VEG_FUTURE_GAP.split(". The historical")[0] + ".",
        "interval": NO_INTERVAL,
    }
    return pd.DataFrame(rows), block


def _ym(x: float) -> str:
    year = int(x)
    month = min(12, int(round((x - year) * 12 + 0.5)))
    return f"{year}-{month:02d}"


# ---- field contrast -----------------------------------------------------------------------------------------------

def vegetation_contrast(spec) -> tuple:
    """(rows, manifest block) or (None, Unsupported): the year-2 total-cover contrast from the comparison layer, with its inputs."""
    from src.shoreline_remediation import comparison as CMP, treatment_effects as te
    from src.shoreline_remediation.projections.spec import Unsupported
    treated, comp = _group(spec), _group(spec, spec.comparator_group_id)
    option = C.CONTRASTS[(spec.endpoint, treated.group_id, comp.group_id)]
    available = month_end(2012, 9)
    if spec.as_of_date < available:
        return None, Unsupported("not_available_at_as_of", f"The year-2 contrast uses the September 2012 survey, available from "
                                 f"{available}; as_of is {spec.as_of}.", "as_of")
    est = next(e for e in CMP.vegetation_year2_estimates() if e.option == option and e.outcome == CMP.VEG_YEAR2.outcome)
    raw = te.load()
    sel = raw[(raw.study == "main") & (raw.year == 2012) & (raw.metric == "Total Vegetation Cover (%)")].set_index("treatment")
    base = {"time": est.time, "survey_period": "September 2012", "date": "2012-09", "date_precision": "month",
            "date_basis": "verified (Zengel et al. 2015 Methods)", "decimal_year": 2012.70, "available_from": available.isoformat(),
            "design": est.design, "source": est.source}
    rows = []
    member = {}
    for g in (treated, comp):
        r = sel.loc[g.zengel2015_name]
        member[g.group_id] = plot_membership(g, spec.endpoint, 2012, int(r.n))
        rows.append({**_common(spec, "observed_group_mean", "zengel2015_s1_group_means"), **base, "plot_group_id": g.group_id,
                     "plots": member[g.group_id][0], "plot_membership": member[g.group_id][1],
                     "n_plots": int(r.n), "value": float(r["mean"]), "unit": "percent", "se": float(r.se),
                     "comparator_group_id": "", "interval_lo": None, "interval_hi": None, "interval_level": None,
                     "interval_method": "", "derivation": "published group mean and standard error (S1 Table)",
                     "applies_to": "this survey only"})
    rows.append({**_common(spec, "field_contrast", "zengel2015_s1_group_means"), **base, "plot_group_id": treated.group_id,
                 "plots": member[treated.group_id][0], "plot_membership": member[treated.group_id][1],
                 "n_plots": est.n_treated, "value": est.estimate, "unit": est.unit, "se": None,
                 "comparator_group_id": comp.group_id, "comparator_plots": member[comp.group_id][0],
                 "comparator_plot_membership": member[comp.group_id][1], "n_comparator": est.n_comparator,
                 "interval_lo": est.lo, "interval_hi": est.hi, "interval_level": est.interval_level,
                 "interval_method": est.interval_type + "; Welch-Satterthwaite df from SE x sqrt(n)",
                 "derivation": f"{treated.group_id} mean minus {comp.group_id} mean; {est.derivation}",
                 "applies_to": ("year 2 after oiling (September 2012) only; not an annual benefit, not a rate and not a projection "
                                "to any later year")})
    df = pd.DataFrame(rows)
    block = {"comparison_option": option, "target": CMP.VEG_YEAR2.key, "outcome": est.outcome, "unit": est.unit, "time": est.time,
             "comparator": comp.group_id, "n_treated": est.n_treated, "n_comparator": est.n_comparator,
             "treated_mean": float(sel.loc[treated.zengel2015_name]["mean"]), "comparator_mean": float(sel.loc[comp.zengel2015_name]["mean"]),
             "difference": est.estimate, "interval": [est.lo, est.hi], "interval_level": est.interval_level,
             "interval_method": est.interval_type, "design": est.design, "source": est.source,
             "reads": "comparison.vegetation_year2_estimates (the dashboard comparison layer)"}
    return df, block


# ---- soil tPAH and the DIVER index --------------------------------------------------------------------------------

def tpah_observed(spec) -> pd.DataFrame:
    from src.shoreline_remediation import recovery_view as RV, treatment_effects as te
    g = _group(spec)
    raw = te.load()
    r = raw[(raw.study == "main") & (raw.metric == "tPAH (mg/kg)") & (raw.treatment == g.zengel2015_name)].dropna(subset=["mean"])
    rows = []
    for _, q in r.sort_values("year").iterrows():
        period, m0, m1 = PAH_PERIOD[int(q.year)]
        lo, hi = RV._t90(float(q["mean"]), float(q.se), int(q.n))
        ids, basis = plot_membership(g, spec.endpoint, int(q.year), int(q.n))
        rows.append({**_common(spec, "observed_group_mean", "zengel2015_s1_group_means"), "plot_group_id": g.group_id, "plots": ids,
                     "plot_membership": basis, "n_plots": int(q.n), "survey_period": period, "date": f"{int(q.year)}-{m0:02d}" + (f"/{m1:02d}" if m1 != m0 else ""),
                     "date_precision": "month", "date_basis": "verified (Zengel et al. 2015 Methods)",
                     "decimal_year": RV.PAH_SURVEY_X[int(q.year)], "available_from": month_end(int(q.year), m1).isoformat(),
                     "available_at_as_of": month_end(int(q.year), m1) <= spec.as_of_date,
                     "value": float(q["mean"]), "unit": "mg/kg", "se": float(q.se), "interval_lo": lo, "interval_hi": hi,
                     "interval_method": "90% t interval of the group mean from its standard error, lower limit cut at 0",
                     "sampling_depth": TPAH_DEPTH, "analyte": TPAH_ANALYTE,
                     "derivation": "published group mean and standard error (S1 Table)"})
    return pd.DataFrame(rows)


def diver_index(spec) -> tuple:
    """(rows, block, uses) for the heavy-class DIVER decline index, or (None, reason text, uses) when it does not apply or is not
    yet known at as_of (its rate was estimated from campaigns to about 2013.78). `uses` lists (evidence_id, role) for every source
    consulted, in order: campaign support is checked first; the model card and rate table are read only if the index is exported."""
    from src.shoreline_remediation import recovery_view as RV
    uses = []
    g = _group(spec)
    if g.oiling_class != "Heavy":
        return None, f"The DIVER decline index is exported for the heavy class only; {g.group_id} is {g.oiling_class}.", uses
    support = RV._pah_support("Heavy")
    uses.append(("pah_decline_v1_campaigns", "campaign support of the heavy-class index (first and last median campaign time), "
                                             "checked against as_of before the index is exported or withheld"))
    if support is None:
        return None, "DIVER campaign table missing or without heavy-class campaigns: the index support is unknown", uses
    t0, t1 = support
    support_end = RV.SPILL_YEAR + t1
    end_date = dt.date(int(support_end), 1, 1) + dt.timedelta(days=int((support_end % 1) * 365.25))
    if spec.as_of_date < end_date:
        return None, (f"The DIVER heavy-class rate was estimated from campaigns up to about {end_date} (decimal {support_end:.2f}), "
                      f"after as_of {spec.as_of}; the index is withheld for this as_of."), uses
    panel = RV.pah_decline_panel("Heavy")
    uses.append(("pah_decline_v1_card", "heavy-class decline rate k and its 90% half-life interval, used to draw the index and "
                                        "its interval"))
    if panel.unavailable or not panel.series:
        return None, panel.unavailable or "DIVER decline reference unavailable", uses
    k_tab = pd.read_csv(RV.ROOT / "results" / "pah_decline" / "by_oiling_class.csv")
    uses.append(("pah_decline_v1_heavy_class", "heavy-class k, its 90% interval, half-life and station count reported in the "
                                               "manifest block"))
    row = k_tab[(k_tab.outcome == "PAH sum") & (k_tab.stratum_type == "oiling_class") & (k_tab.stratum == "heavy")].iloc[0]
    s = panel.series[0]
    rows = [{**_common(spec, "model_reference_index", "pah_decline_v1_heavy_class"), "plot_group_id": "",
             "oiling_class": "heavy (SCAT)", "years_since_spill": p.x0 - RV.SPILL_YEAR, "decimal_year": p.x0, "value": p.value,
             "unit": s.unit, "reference_value": 100.0,
             "reference": f"100 = first DIVER sampling campaign (median {t0:.2f} years after 20 April 2010)",
             "interval_lo": p.lo, "interval_hi": p.hi, "interval_method": s.interval, "analyte": DIVER_ANALYTE,
             "campaign_support": f"{RV.SPILL_YEAR + t0:.2f} to {support_end:.2f} (first to last campaign)",
             "model": "pah_decline_v1", "status": s.evidence, "comparator": s.comparator} for p in s.points]
    block = {"model": "pah_decline_v1", "oiling_class": "heavy", "k_per_year": float(row.k_per_year),
             "k_90": [float(row.k_lo90), float(row.k_hi90)], "half_life_years": float(row.half_life_years),
             "n_stations_2plus_campaigns": int(row.n_stations_2plus_campaigns), "reference_value": 100.0,
             "campaign_support_decimal_years": [RV.SPILL_YEAR + t0, support_end], "analyte": DIVER_ANALYTE,
             "not_a_plot_measurement": "a class-level relative index; not on the tPAH axis (different analyte set, depth and unit)",
             "status": s.evidence}
    return pd.DataFrame(rows), block, uses
