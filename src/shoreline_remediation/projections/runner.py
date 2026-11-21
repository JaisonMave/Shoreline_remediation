"""Offline runner for research projections. Writes one self-describing run directory per run.

Run directory contents:
    manifest.json   status, exact input, code and source checksums, dependency versions, seed, outcome, outputs
    input.json      the exact input bytes (the scenario file as given, or the canonical spec when run from Python)
    observed.csv    observed group means at survey dates, when the request is supported (both models)
    projection.csv  rate_continuation/1 only: anchor row plus conditional projection to end_date
    projection.png, projection.svg   rate_continuation/1 only: standalone figure
    whatif.csv      retreat_whatif/1, cover_whatif/1 and tpah_whatif/1 (spec version 2): observed surveys, natural-recovery arm and, where
                    screening allows it, the user-defined what-if arm; written by the same code and at the same precision as
                    the dashboard download
    whatif.png, whatif.svg   optional images of a completed version-2 replay (run --figures)
    contrast.csv    field_contrast/1: the historical contrast and the two group means it is computed from
    fit.csv         recovery_fit/1: experimental within-record fit; conditional rows where a parameter is borrowed
    reference_index.csv   soil_tpah observed_record/1, heavy class: DIVER relative decline index within campaign support
Every CSV row carries record_type and record_class from catalogue.RECORD_TYPES. An evidence gap still writes observed.csv.

Status values: 'running' is written first and replaced at the end, so an interrupted run is never mistaken for a completed one.
'completed' and 'unsupported' are both finished outcomes; 'failed' records an exception. An existing output path is never
written into.

The Assessment scenario panel and the CLI reuse the scenario calculations. The decision pipeline assigns recommendations.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import platform
import subprocess
from dataclasses import asdict, dataclass
from importlib import metadata
from pathlib import Path

import numpy as np
import pandas as pd

from src.shoreline_remediation.projections import catalogue as C
from src.shoreline_remediation.projections.spec import ScenarioSpec, SpecError, Unsupported, check_scope, from_dict

ROOT = Path(__file__).resolve().parents[3]
MANIFEST_VERSION = "shoreline-projection-run/1"
VOLATILE_KEYS = ("started_at", "finished_at", "git_commit", "git_dirty")
DEPENDENCIES = ("numpy", "pandas", "scipy", "openpyxl")
PKG = Path(__file__).resolve().parent
# Code whose behaviour determines the outputs: this package and the reused scientific loaders.
CODE_FILES = tuple(sorted(PKG.glob("*.py"))) + tuple(PKG.parent / f for f in ("recovery_trajectories.py", "recovery_view.py",
                                                                                "treatment_effects.py", "comparison.py",
                                                                                "assessment_screening.py"))
INTERVAL_METHOD = "90% t interval of the mean of plot values (between-plot variation only)"
LIMITATIONS = (
    "Observed group means of one site's plots (Bay Jimmy, Deepwater Horizon); not a forecast and not validated for other places.",
    "Retreat before the 4 December 2010 origin (oiling began mid-2010) is not observed in this series.",
    "Intervals describe between-plot variation of the mean at each survey; they exclude GPS and staking error and between-year "
    "weather, and are not prediction intervals for a new plot.",
    "The plots also calibrate the scenario composer's treatment terms and are shared by Zengel et al. 2015 and 2022, so they are "
    "not independent evaluation data for those models.",
)


class OutputExistsError(FileExistsError):
    pass


@dataclass(frozen=True)
class RunResult:
    status: str
    output_dir: Path
    manifest: dict
    unsupported: Unsupported | None = None


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _text_sha256(p: Path) -> str:
    """Line-ending-independent hash of a text file (Windows checkouts convert LF to CRLF)."""
    return _sha256_bytes(p.read_bytes().replace(b"\r\n", b"\n"))


def code_sha256() -> str:
    h = hashlib.sha256()
    for p in CODE_FILES:
        h.update(p.name.encode() + b"\0" + _text_sha256(p).encode())
    return h.hexdigest()


def _git(*args) -> str | None:
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=20)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _versions() -> dict:
    out = {"python": platform.python_version()}
    for name in DEPENDENCIES:
        try:
            out[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            out[name] = None
    return out


def _sources(spec: ScenarioSpec) -> list:
    """Every source the run reads: those cited in the scenario, then the endpoint's dependencies resolved here (catalogue
    DEPENDENCIES), each with its checksum. A dependency the scenario did not cite is marked cited_in_spec False."""
    deps = C.DEPENDENCIES.get((spec.model_version, spec.endpoint), {})
    ids = list(spec.evidence_ids) + [e for e in deps if e not in spec.evidence_ids]
    return [_source_entry(eid, eid in spec.evidence_ids, deps.get(eid, "cited in the scenario")) for eid in ids]


def _source_entry(eid: str, cited: bool, read_for: str) -> dict:
    ev = C.EVIDENCE[eid]
    p = ROOT / ev.path
    return {"evidence_id": eid, "citation": ev.citation, "locator": ev.locator, "path": ev.path,
            "sha256": _sha256_bytes(p.read_bytes()) if p.exists() else None, "present": p.exists(),
            "cited_in_spec": cited, "read_for": read_for, "used_in_calculation": False, "roles": []}


def _use(manifest: dict, eid: str, role: str) -> None:
    """Record that the calculation consulted `eid` for `role`. A source the scenario did not cite is added with its checksum."""
    entry = next((s for s in manifest["sources"] if s["evidence_id"] == eid), None)
    if entry is None:
        entry = _source_entry(eid, False, role)
        manifest["sources"].append(entry)
    entry["used_in_calculation"] = True
    if role not in entry["roles"]:
        entry["roles"].append(role)


def _write_json(path: Path, obj) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def observed_record(spec: ScenarioSpec) -> pd.DataFrame:
    """Observed group means of cumulative retreat at each survey, from the existing loader (recovery_trajectories)."""
    from src.shoreline_remediation import recovery_trajectories as T
    group = C.SITES[spec.site_id].plot_groups[spec.plot_group_id]
    d = T.field_positions()
    g = d[(d.key == group.loader_key) & np.isclose(d.t0, 0.0)]
    if g.empty:
        raise RuntimeError(f"No field positions with the common origin for plot group '{group.group_id}'")
    origin = T.decimal_year(T.ORIGIN)
    rows = []
    for date, v in g.groupby("date"):
        m, lo, hi = T._t90(v.inc.values)
        rows.append({"scenario_id": spec.scenario_id, "site_id": spec.site_id, "plot_group_id": spec.plot_group_id,
                     "endpoint": spec.endpoint, "unit": spec.unit, "date": pd.Timestamp(date).date().isoformat(),
                     "decimal_year": round(T.decimal_year(date), 6), "elapsed_years": round(T.decimal_year(date) - origin, 6),
                     "value": m, "interval_lo": lo, "interval_hi": hi, "interval_method": INTERVAL_METHOD if len(v) > 1 else "",
                     "n_plots": int(v.pid.nunique()), "record_type": "observed_group_mean", "record_class": "observation",
                     "origin": "derived", "derivation": "mean over plots of (first minus current back-stake distance), two transects per plot",
                     "evidence_id": "zengel2022_griidc_field_positions",
                     "available_at_as_of": pd.Timestamp(date).date() <= spec.as_of_date})
    out = pd.DataFrame(rows)
    # the origin survey is zero by definition (every plot's increment from itself): keep it, with no interval
    zero = np.isclose(out.elapsed_years, 0.0)
    out.loc[zero, ["interval_lo", "interval_hi"]] = np.nan
    out.loc[zero, "interval_method"] = "origin: zero by definition"
    return out


PROJECTION_LIMITATIONS = (
    C.CONDITIONAL_LABEL,
    "The rate(s) are assumptions stated in the input. Nothing here estimates storms, sea-level rise, subsidence, marsh geometry "
    "change or management after the last survey.",
    "No interval is drawn. Runs with different rates are a sensitivity comparison of separate assumptions, not a probability band; "
    "the plot bootstrap of the dashboard's fits describes historical fit uncertainty only.",
    "Forecast skill of any rate rule is untested here (protocol P-RET-1, scoring session). Even a passed test would cover lead "
    "times of about 4 years at most; a 2030 or 2050 end date is a planning horizon, not a validated horizon.",
    "No recommendation is assigned. The dashboard's decision pipeline is unaffected.",
)


def _write_csv(out: Path, manifest: dict, name: str, df: pd.DataFrame, description: str) -> None:
    df.to_csv(out / name, index=False, float_format="%.6f", lineterminator="\n")
    manifest["outputs"].append({"path": name, "sha256": _sha256_bytes((out / name).read_bytes()), "rows": len(df),
                                "description": description})


def arithmetic(anchor_value: float, anchor_t: float, segs_t: list, end_t: float) -> str:
    """Hand-checkable statement of the endpoint arithmetic, with the numbers actually used."""
    parts, total = [], 0.0
    for s, e, r in segs_t:
        lo, hi = max(s, anchor_t), min(e, end_t)
        if hi > lo:
            parts.append(f"{r:g} m/yr x ({hi:.6f} - {lo:.6f}) yr = {r * (hi - lo):.6f} m")
            total += r * (hi - lo)
    summed = f" = {total:.6f} m" if len(parts) > 1 else ""
    return (f"additional = {' + '.join(parts)}{summed}; cumulative = {anchor_value:.6f} + {total:.6f} = "
            f"{anchor_value + total:.6f} m")


def _project(spec: ScenarioSpec, out: Path, manifest: dict, obs: pd.DataFrame, anchor_row) -> None:
    from src.shoreline_remediation.projections import figure, projection as P
    from src.shoreline_remediation.recovery_trajectories import decimal_year
    anchor = dt.date.fromisoformat(anchor_row.date)
    table, segs = P.project(spec, anchor, float(anchor_row.value), int(anchor_row.n_plots))
    _write_csv(out, manifest, "projection.csv", table, "Conditional projection from the anchor observation to end_date")
    _record_types(manifest, table)
    end = table.iloc[-1]
    segs_t = [(decimal_year(s.starts), decimal_year(s.ends), s.rate) for s in segs]
    ev = C.EVIDENCE["zengel2022_griidc_field_positions"]
    footer = (f"Observations: {ev.citation}; {ev.locator.split(',')[0]}. Scenario '{spec.scenario_id}', run {manifest['run_id']}, "
              f"model {spec.model_version}. Rates: " + "; ".join(f"{s.assumption_id} {s.rate:g} m/yr from {s.starts} "
                                                                   f"({s.origin.replace('_', ' ')}: {s.source})" for s in segs))
    for p in figure.draw(obs, [{"table": table, "label": P.describe_rates(segs)}], spec, out / "projection", footer=footer):
        manifest["outputs"].append({"path": p.name, "sha256": _sha256_bytes(p.read_bytes()), "rows": None,
                                    "description": "Standalone figure: observations and the conditional projection"})
    manifest["projection"] = {
        "status_label": C.CONDITIONAL_LABEL,
        "anchor": {"date": anchor.isoformat(), "cumulative_retreat_m": float(anchor_row.value), "n_plots": int(anchor_row.n_plots),
                   "record": "observed group mean (observed.csv row at this date)"},
        "rates": [s.as_dict() for s in segs],
        "end": {"date": end.date, "years_since_anchor": float(end.years_since_anchor),
                "additional_retreat_since_anchor_m": float(end.additional_retreat_since_anchor_m),
                "cumulative_retreat_since_origin_m": float(end.cumulative_retreat_since_origin_m)},
        "arithmetic": arithmetic(float(anchor_row.value), decimal_year(anchor), segs_t, decimal_year(spec.end)),
        "time_convention": "calendar decimal years (recovery_trajectories.decimal_year), actual dates",
    }
    manifest["limitations"] = list(LIMITATIONS) + list(PROJECTION_LIMITATIONS)


def _write_whatif_figures(out, manifest, text, outcome, computed):
    from . import figure
    technique = computed.label
    if outcome == "retreat" and manifest["spec"]["technique"] == "natural_attenuation":
        technique = "Natural recovery only (reference)"
    images = figure.whatif_figure(text, outcome, **figure.whatif_labels(outcome, computed, technique))
    for fmt, image in images.items():
        name = f"whatif.{fmt}"
        (out / name).write_bytes(image)
        manifest["outputs"].append({"path": name, "sha256": _sha256_bytes(image), "rows": None,
                                    "description": "Scenario figure rendered from the replayed whatif.csv"})


def _whatif(spec: ScenarioSpec, out: Path, manifest: dict, obs: pd.DataFrame, screening, figures=False) -> Unsupported | None:
    """retreat_whatif/1: re-screen the technique, recompute both arms from the inputs and the source observations, and write
    whatif.csv with the dashboard's export code. Saved outputs in the file are compared, never used."""
    from src.shoreline_remediation.projections import whatif as W
    result = W.screen(screening(spec), spec.technique)
    effect = W.effect_from_spec(spec)
    computed = W.compute(spec, obs, effect, result.row)
    text = W.csv_text(computed.rows)
    (out / W.CSV_NAME).write_bytes(text.encode("utf-8"))
    manifest["outputs"].append({"path": W.CSV_NAME, "sha256": _sha256_bytes(text.encode("utf-8")), "rows": len(computed.rows),
                                "description": "Observed surveys and the scenario arms (dashboard what-if CSV format)",
                                "float_format": W.CSV_FLOAT_FORMAT})
    _record_types(manifest, computed.rows)
    last = computed.what.last
    manifest["whatif"] = {
        "label": W.WHATIF_LABEL, "technique": spec.technique, "screening": result.as_dict(),
        "treatment_effect": spec.treatment_effect, "treatment_applied": computed.applied,
        "anchor": {"date": computed.anchor.date, "cumulative_retreat_m": float(computed.anchor.value),
                   "n_plots": int(computed.anchor.n_plots)},
        "rates": [seg.as_dict() for seg in computed.what.segments],
        "summary": {"end_date": spec.end_date, "natural_recovery_m": float(last.natural_recovery_m),
                    "treatment_m": float(last.treatment_m) if computed.applied else None,
                    "difference_m": float(last.difference_m) if computed.applied else None,
                    "text": W.summary_text(computed.what, spec.end)},
        "exported_outputs_check": W.check_exported(spec.exported_outputs, computed),
        "not": "not a measured treatment effect, not a forecast, not used for ranking or recommendations",
    }
    manifest["limitations"] = list(LIMITATIONS) + list(PROJECTION_LIMITATIONS)
    if effect is not None and not computed.screening_allows:
        return Unsupported("technique_blocked_by_screening",
                           f"No treatment curve for '{spec.technique}': {computed.screening_reason} The natural-recovery arm and "
                           "the observations are exported.", "technique")
    if figures:
        _write_whatif_figures(out, manifest, text, "retreat", computed)
    return None


def _cover(spec: ScenarioSpec, out: Path, manifest: dict, screening, figures=False) -> Unsupported | None:
    """cover_whatif/1: re-screen the technique, recompute both arms from the inputs and the untreated surveys, and write
    observed.csv and whatif.csv with the dashboard's export code. Saved outputs in the file are compared, never used."""
    from src.shoreline_remediation.projections import cover as CV, evidence as E, whatif as W
    obs = E.vegetation_observed(spec)
    _use(manifest, "zengel2022_griidc_vegetation", "plot-level total cover of the untreated, heavily oiled plots")
    _write_csv(out, manifest, "observed.csv", obs, "Observed group means of total cover at each survey")
    result = W.screen(screening(spec), spec.technique, CV.ENDPOINT)
    effect = CV.effect_from_spec(spec)
    computed = CV.compute(spec, obs, effect, result.row)
    text = W.csv_text(computed.rows)
    (out / W.CSV_NAME).write_bytes(text.encode("utf-8"))
    manifest["outputs"].append({"path": W.CSV_NAME, "sha256": _sha256_bytes(text.encode("utf-8")), "rows": len(computed.rows),
                                "description": "Observed surveys and the scenario arms (dashboard cover what-if CSV format)",
                                "float_format": W.CSV_FLOAT_FORMAT})
    _record_types(manifest, computed.rows)
    a, w = computed.what.anchor, computed.what
    peak = w.at(w.effect.peak) if computed.applied else None
    manifest["whatif"] = {
        "label": CV.WHATIF_LABEL, "endpoint": CV.ENDPOINT, "unit": CV.UNIT, "technique": spec.technique,
        "screening": result.as_dict(), "treatment_effect": spec.treatment_effect, "treatment_applied": computed.applied,
        "baseline": {"rule": CV.BASELINE_LABEL, "survey": a.survey, "date_precision": a.date_precision,
                     "date_basis": a.date_basis, "curve_starts": a.starts.isoformat(), "mean_total_cover_percent": a.value,
                     "n_plots": a.n_plots},
        "summary": {"peak_date": None if peak is None else w.effect.peak.isoformat(),
                    "natural_recovery_pct": a.value if peak is None else float(peak.natural_recovery_pct),
                    "treatment_pct": None if peak is None else float(peak.treatment_pct),
                    "difference_pp": None if peak is None else float(peak.difference_pp),
                    "text": CV.peak_text(w)},
        "exported_outputs_check": CV.check_exported(spec.exported_outputs, computed),
        "not": "not a measured treatment effect, not a forecast, not used for ranking or recommendations",
    }
    manifest["limitations"] = [
        "Observed group means of one site's plots (Bay Jimmy, Deepwater Horizon); not a forecast and not validated elsewhere.",
        "The baseline holds the last observed mean constant. Cover fell from 92.0% (2015) to 70.0% (2016) on the five plots still "
        "surveyed, and no later survey or independent site tests any future cover rule.",
        CV.TEMPORARY_NOTE, "No recommendation is assigned. The dashboard's decision pipeline is unaffected."]
    if effect is not None and not computed.screening_allows:
        return Unsupported("technique_blocked_by_screening",
                           f"No treatment curve for '{spec.technique}': {computed.screening_reason} The natural-recovery arm and "
                           "the observations are exported.", "technique")
    if figures:
        _write_whatif_figures(out, manifest, text, "cover", computed)
    return None


def _tpah(spec: ScenarioSpec, out: Path, manifest: dict, screening, figures=False) -> Unsupported | None:
    """tpah_whatif/1: re-screen the technique, recompute both arms from the inputs and the untreated measurements, and write
    observed.csv and whatif.csv with the dashboard's export code. Saved outputs in the file are compared, never used."""
    from src.shoreline_remediation.projections import evidence as E, pah as PH, whatif as W
    obs = E.tpah_observed(spec)
    _use(manifest, "zengel2015_s1_group_means", "untreated soil tPAH group means (0-10 cm cores, S1 Table)")
    _write_csv(out, manifest, "observed.csv", obs, "Observed soil tPAH group means at each survey")
    result = W.screen(screening(spec), spec.technique, PH.ENDPOINT)
    half_life, effect = PH.half_life_from_spec(spec), PH.effect_from_spec(spec)
    computed = PH.compute(spec, obs, half_life, effect, result.row)
    text = W.csv_text(computed.rows)
    (out / W.CSV_NAME).write_bytes(text.encode("utf-8"))
    manifest["outputs"].append({"path": W.CSV_NAME, "sha256": _sha256_bytes(text.encode("utf-8")), "rows": len(computed.rows),
                                "description": "Observed measurements and the scenario arms (dashboard tPAH what-if CSV format)",
                                "float_format": W.CSV_FLOAT_FORMAT})
    _record_types(manifest, computed.rows)
    a, w = computed.what.anchor, computed.what
    last = w.frame.iloc[-1]
    at = None
    if computed.applied:
        before = w.row(w.effect.date, "intervention_before")
        after = w.frame[w.frame.date == w.effect.date.isoformat()].iloc[-1]
        at = {"date": w.effect.date.isoformat(), "before_mgkg": float(before.treatment_mgkg),
              "after_mgkg": float(after.treatment_mgkg)}
    manifest["whatif"] = {
        "label": PH.WHATIF_LABEL, "endpoint": PH.ENDPOINT, "unit": PH.UNIT, "technique": spec.technique,
        "screening": result.as_dict(), "treatment_effect": spec.treatment_effect, "treatment_applied": computed.applied,
        "baseline": {"rule": PH.baseline_label(half_life), "choice": PH.HOLD if half_life is None else PH.HALF_LIFE,
                     "half_life_years": half_life, "background": "zero (assumed)" if half_life is not None else None,
                     "survey": a.survey, "survey_period": a.survey_period, "date_precision": a.date_precision,
                     "curve_starts": a.starts.isoformat(), "tpah_mgkg": a.value, "n_plots": a.n_plots,
                     "sampling_depth": a.depth, "analyte": a.analyte},
        "summary": {"end_date": spec.end_date, "natural_mgkg": float(last.natural_mgkg),
                    "treatment_mgkg": float(last.treatment_mgkg) if computed.applied else None,
                    "difference_mgkg": float(last.difference_mgkg) if computed.applied else None,
                    "at_intervention": at, "text": PH.summary_text(w, spec.end)},
        "exported_outputs_check": PH.check_exported(spec.exported_outputs, computed),
        "not": "not a measured treatment effect, not a forecast, not used for ranking or recommendations",
    }
    manifest["limitations"] = [
        "Two measurement dates per group (July-August 2011, September 2012); no plot or treatment decline rate is identified "
        "from them, so any half-life is the user's assumption.",
        PH.BACKGROUND_NOTE if half_life is not None else "The natural-recovery scenario holds the last measured concentration.",
        PH.SOIL_NOTE, "The regional DIVER index (different depth and analyte set) is not used.",
        "No recommendation is assigned. The dashboard's decision pipeline is unaffected."]
    if effect is not None and not computed.screening_allows:
        return Unsupported("technique_blocked_by_screening",
                           f"No treatment curve for '{spec.technique}': {computed.screening_reason} The natural-recovery arm and "
                           "the measurements are exported.", "technique")
    if figures:
        _write_whatif_figures(out, manifest, text, "tpah", computed)
    return None


def compare(run_dirs: list, out_stem: str | Path) -> list:
    """Overlay completed rate_continuation runs that share site, plot group and anchor (a sensitivity figure)."""
    from src.shoreline_remediation.projections import figure
    runs = []
    for d in map(Path, run_dirs):
        m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
        if m.get("status") != "completed" or "projection" not in m:
            raise ValueError(f"{d} is not a completed projection run (status {m.get('status')})")
        runs.append((d, m))
    keys = {(m["spec"]["site_id"], m["spec"]["plot_group_id"], m["projection"]["anchor"]["date"]) for _, m in runs}
    if len(keys) != 1:
        raise ValueError(f"Runs differ in site, plot group or anchor and cannot share one figure: {sorted(keys)}")
    if len(runs) > 2:
        raise ValueError("At most two runs per comparison figure (two categorical slots with line-style encoding)")
    stem = Path(out_stem)
    targets = [stem.with_suffix(".png"), stem.with_suffix(".svg")]
    if any(p.exists() for p in targets):
        raise OutputExistsError(f"Figure already exists and was left untouched: {[str(p) for p in targets if p.exists()]}")
    stem.parent.mkdir(parents=True, exist_ok=True)
    from src.shoreline_remediation.projections.projection import describe_rates, rate_segments
    curves = []
    for d, m in runs:
        s = from_dict(m["spec"])
        segs = rate_segments(s, dt.date.fromisoformat(m["projection"]["anchor"]["date"]))
        curves.append({"table": pd.read_csv(d / "projection.csv"), "label": f"{s.scenario_id}: {describe_rates(segs)}"})
    first = from_dict(runs[0][1]["spec"])
    footer = ("Sensitivity comparison of runs " + ", ".join(m["run_id"] for _, m in runs) + ". Observations: "
              + C.EVIDENCE["zengel2022_griidc_field_positions"].citation + ".")
    return figure.draw(pd.read_csv(runs[0][0] / "observed.csv"), curves, first, stem, footer=footer, comparison=True)


EVIDENCE_LIMITATIONS = (
    C.SHARED_PLOTS_NOTE,
    "One site (Bay Jimmy, Deepwater Horizon), 5 to 9 plots per group. Treatment groups were not randomly assigned (observational), "
    "except the planting contrast, which is not exported here.",
    "Field contrasts describe the survey they come from; they are not annual benefits, rates or projections to later years.",
    "Experimental fits describe the surveyed period only and carry no interval in this export. Borrowed-parameter values are "
    "conditional projections.",
    "No recommendation is assigned. The dashboard's decision pipeline is unaffected.",
)


# Unsupported outcomes that still export the historical observations of the request.
EXPORTING_CODES = ("evidence_gap", "exposure_inputs_unavailable")


def _check_sources(manifest: dict) -> None:
    missing = [s["path"] for s in manifest["sources"] if not s["present"]]
    if missing:
        raise FileNotFoundError(f"Evidence source files missing: {missing}")


def _record_types(manifest: dict, df: pd.DataFrame) -> None:
    if "record_type" in df:
        seen = manifest.setdefault("record_types", {})
        for rt in df.record_type.unique():
            seen[rt] = C.RECORD_TYPES[rt]
        manifest["record_class_meaning"] = {c: C.RECORD_CLASS_MEANING[c] for c in sorted(set(seen.values()))}


def _evidence_exports(spec: ScenarioSpec, out: Path, manifest: dict, gap: Unsupported | None) -> Unsupported | None:
    """Historical evidence for vegetation and tPAH (and the observed record for a retreat evidence gap). Returns the Unsupported
    outcome to record (the gap, or a fit that cannot be made at as_of), else None."""
    from src.shoreline_remediation.projections import evidence as E

    def write(name, df, description):
        _write_csv(out, manifest, name, df, description)
        _record_types(manifest, df)

    manifest["limitations"] = list(EVIDENCE_LIMITATIONS)
    if spec.endpoint == C.EXPOSURE_ENDPOINT:
        from src.shoreline_remediation.projections import exposure as X
        case = C.EXPOSURE_CASES[spec.site_id]
        df, summary = X.survey_contact(spec, ROOT)
        _use(manifest, "noaa_scat_mobile_visits", "segment visit status and dates (survey classes, arrival windows)")
        _use(manifest, "noaa_scat_mobile_segments", "segment list, state, ESI class, length and midpoint")
        write("survey_contact.csv", df, "SCAT survey classes per segment in the window: evaluation observations, not simulation inputs")
        manifest["exposure"] = {
            "case": {"case_id": case.case_id, "label": case.label, "region": case.region, "bbox_lon_lat": list(case.bbox_lon_lat),
                     "window": list(case.window)},
            "inputs": [asdict(i) for i in case.inputs],
            "missing_essential": [i.name for i in case.missing_essential()],
            "simulation_attempted": False,
            "outcome_codes": C.EXPOSURE_OUTCOMES,
            "survey_summary": summary,
            "data_gap_record": "docs/PROJECTION_EXPOSURE_DATA_GAP.md",
        }
        manifest["limitations"] = list(X.SURVEY_LIMITATIONS) + [
            "No transport simulation was attempted, so no 'contact' or 'no_contact' result exists for any segment.",
            "No recommendation is assigned. The dashboard's decision pipeline is unaffected."]
        return gap
    if spec.endpoint == "cumulative_shoreline_retreat":
        write("observed.csv", observed_record(spec), "Observed group means at survey dates")
        _use(manifest, "zengel2022_griidc_field_positions", "plot transect positions: cumulative retreat of each plot since 4 Dec 2010")
        manifest["limitations"] = list(LIMITATIONS)
        return gap
    if spec.endpoint == "total_vegetation_cover" and spec.model_version == "field_contrast/1":
        df, block = E.vegetation_contrast(spec)
        if df is None:
            return block
        write("contrast.csv", df, "Year-2 field contrast with the two group means it is computed from")
        _use(manifest, "zengel2015_s1_group_means", "2012 total-cover group means, standard errors and n (contrast and its inputs)")
        _use(manifest, "zengel2022_griidc_vegetation", "plot membership: plot-level total-cover records of each group at the 2012 survey")
        _use(manifest, "zengel2022_griidc_field_positions", "plot types (sheet 'DSAS lumped') that assign the vegetation plots to groups")
        manifest["contrast"] = block
        return None
    if spec.endpoint == "total_vegetation_cover":
        write("observed.csv", E.vegetation_observed(spec), "Observed total cover, group means at survey dates")
        _use(manifest, "zengel2022_griidc_vegetation", "plot-year total cover of the group (plot-level records)")
        _use(manifest, "zengel2022_griidc_field_positions", "plot types (sheet 'DSAS lumped') assigning vegetation plots to groups")
        if gap is None and spec.model_version == "recovery_fit/1":
            df, block = E.vegetation_fit(spec)
            if df is None:
                return block
            write("fit.csv", df, "Experimental within-record fit; conditional rows where a parameter is borrowed")
            manifest["fit"] = block
        return gap
    if spec.endpoint == "soil_tpah":
        write("observed.csv", E.tpah_observed(spec), "Observed soil tPAH, group means at sampling dates")
        _use(manifest, "zengel2015_s1_group_means", "tPAH group means, standard errors and n at the 2011 and 2012 samplings")
        if gap is None:
            idx, block, uses = E.diver_index(spec)
            for eid, role in uses:
                _use(manifest, eid, role)
            if idx is None:
                manifest["reference_index"] = {"exported": False, "reason": block}
            else:
                write("reference_index.csv", idx, "DIVER heavy-class relative decline index (pah_decline_v1), within campaign support")
                manifest["reference_index"] = {"exported": True, **block}
        return gap
    raise ValueError(f"No evidence export for {spec.endpoint}")


EVALUATION_SCOPE = (
    "Applies only to the heavily oiled untreated Bay Jimmy plots (n = 9), the cutoffs 2012-09-17 to 2015-09-30 and the lead times "
    "actually scored (at most about 4.05 years, 2016-10-05 targets). The pairs share plots and overlapping periods and are not "
    "independent tests. No result here is evidence about 2030 or 2050: those outputs remain conditional scenario projections. No "
    "cross-site skill is evaluated (one eligible site). The historical decision-replay records (legacy 5/6; integrated F11 2/6 against "
    "an always-active baseline of 5/6) evaluate different decision rules and are unaffected.")


def write_evaluation(output_dir: str | Path, n_boot: int = 2000) -> Path:
    """Score protocol P-RET-1 into a new directory: pairs.csv, rates.csv, evaluation.json."""
    from src.shoreline_remediation.projections import evaluation as E
    out = Path(output_dir)
    if out.exists():
        raise OutputExistsError(f"Output path already exists and was left untouched: {out}. Choose a new directory for each run.")
    out.mkdir(parents=True)
    src = ROOT / C.EVIDENCE["zengel2022_griidc_field_positions"].path
    record = {"protocol": E.PROTOCOL, "status": "running", "started_at": _now(),
              "protocol_document": "docs/PROJECTION_RETREAT_PROTOCOL.md",
              "delta_m": E.DELTA_M, "delta_status": "owner-confirmed 20 November 2026 before scoring (research criterion)",
              "bias_margin_m": E.BIAS_MARGIN_M, "cutoffs": list(E.CUTOFFS), "lead_bins": [b[2] for b in E.BINS],
              "rules": E.RULE_TEXT, "seed": E.SEED, "n_boot": n_boot,
              "source": {"evidence_id": "zengel2022_griidc_field_positions", "path": C.EVIDENCE["zengel2022_griidc_field_positions"].path,
                         "sha256": _sha256_bytes(src.read_bytes())},
              "code": {"code_sha256": code_sha256(), "evaluation_sha256": _text_sha256(PKG / "evaluation.py"),
                       "git_commit": _git("rev-parse", "HEAD"), "git_dirty": bool(_git("status", "--porcelain", "--", "src"))},
              "dependencies": _versions(), "scope": EVALUATION_SCOPE}
    _write_json(out / "evaluation.json", record)
    try:
        res = E.evaluate(n_boot=n_boot)
        res["pairs"].to_csv(out / "pairs.csv", index=False, float_format="%.6f", lineterminator="\n")
        res["rates"].to_csv(out / "rates.csv", index=False, float_format="%.6f", lineterminator="\n")
        record.update({"data": res["data"], "candidates": res["summary"], "bootstrap": res["bootstrap"],
                       "outputs": {n: _sha256_bytes((out / n).read_bytes()) for n in ("pairs.csv", "rates.csv")},
                       "status": "completed", "finished_at": _now()})
    except Exception as exc:
        record.update({"status": "failed", "error": f"{type(exc).__name__}: {exc}", "finished_at": _now()})
        _write_json(out / "evaluation.json", record)
        raise
    _write_json(out / "evaluation.json", record)
    return out


def normalized(manifest: dict) -> dict:
    """Manifest with only the genuinely volatile fields removed (times, git commit and working-tree state)."""
    m = json.loads(json.dumps(manifest))
    for k in VOLATILE_KEYS:
        m.pop(k, None)
        m.get("code", {}).pop(k, None)
    return m


def run(spec: ScenarioSpec | dict | str | Path, output_dir: str | Path, *, input_bytes: bytes | None = None,
        screening=None, figures=False) -> RunResult:
    """Validate, check scope, and write a new run directory. Raises SpecError (nothing written) or OutputExistsError.
    A version-2 what-if needs `screening` (assessment_screening.reproduce): the assessment is re-run and the technique
    re-screened through the inventory on every run."""
    if isinstance(spec, (str, Path)):
        path = Path(spec)
        try:
            input_bytes = path.read_bytes()
        except FileNotFoundError:
            raise SpecError([("(file)", f"scenario file not found: {path}")]) from None
        from src.shoreline_remediation.projections.spec import load
        spec = load(path)
    elif isinstance(spec, dict):
        spec = from_dict(spec)
    unsupported = check_scope(spec)              # may raise SpecError before anything is written
    if figures and spec.model_version not in C.WHATIF_MODELS:
        raise SpecError([("figures", "--figures is available for version-2 what-if scenarios")])
    if spec.model_version in C.WHATIF_MODELS and screening is None:
        raise SpecError([("technique", "a version-2 what-if is re-screened on every run; pass a screening resolver "
                                       "(the CLI uses assessment_screening.reproduce)")])
    out = Path(output_dir)
    if out.exists():
        raise OutputExistsError(f"Output path already exists and was left untouched: {out}. Choose a new directory for each run.")
    out.mkdir(parents=True)
    if input_bytes is None:
        input_bytes = (spec.to_json() + "\n").encode("utf-8")
    (out / "input.json").write_bytes(input_bytes)
    canonical = json.dumps(spec.to_dict(), sort_keys=True, allow_nan=False)
    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "run_id": _sha256_bytes(canonical.encode())[:16],
        "status": "running",
        "started_at": _now(),
        "spec": spec.to_dict(),
        "spec_sha256": _sha256_bytes(canonical.encode()),
        "input_sha256": _sha256_bytes(input_bytes.replace(b"\r\n", b"\n")),
        "demonstration": spec.demonstration,
        "seed": spec.seed,
        "code": {"package": "src.shoreline_remediation.projections", "code_sha256": code_sha256(),
                 "code_files": [p.name for p in CODE_FILES], "git_commit": _git("rev-parse", "HEAD"),
                 "git_dirty": bool(_git("status", "--porcelain", "--", "src"))},
        "dependencies": _versions(),
        "sources": _sources(spec),
        "model": {"model_version": spec.model_version, "description": C.MODELS[spec.model_version]},
        "outcome": None,
        "outputs": [],
        "limitations": [],
    }
    _write_json(out / "manifest.json", manifest)
    try:
        if figures:
            manifest["dependencies"]["matplotlib"] = metadata.version("matplotlib")
        if unsupported is not None and unsupported.code not in EXPORTING_CODES:
            manifest["status"] = "unsupported"
            manifest["outcome"] = {"status": "unsupported", **asdict(unsupported)}
        elif spec.model_version in (C.COVER_WHATIF_MODEL, C.TPAH_WHATIF_MODEL):
            _check_sources(manifest)
            writer = _cover if spec.model_version == C.COVER_WHATIF_MODEL else _tpah
            unsupported = writer(spec, out, manifest, screening, figures)
            manifest["status"] = "unsupported" if unsupported is not None else "completed"
            manifest["outcome"] = ({"status": "unsupported", **asdict(unsupported)} if unsupported is not None else
                                   {"status": "completed", "files": [o["path"] for o in manifest["outputs"]]})
        elif spec.endpoint != "cumulative_shoreline_retreat" or unsupported is not None:
            _check_sources(manifest)
            unsupported = _evidence_exports(spec, out, manifest, unsupported)
            if unsupported is not None:
                manifest["status"] = "unsupported"
                manifest["outcome"] = {"status": "unsupported", **asdict(unsupported),
                                       "historical_records_exported": [o["path"] for o in manifest["outputs"]]}
            else:
                manifest["status"] = "completed"
                manifest["outcome"] = {"status": "completed", "files": [o["path"] for o in manifest["outputs"]]}
        else:
            _check_sources(manifest)
            obs = observed_record(spec)            # deterministic; the seed is recorded for stochastic models in later sessions
            _use(manifest, "zengel2022_griidc_field_positions", "plot transect positions: cumulative retreat of each plot since 4 Dec 2010")
            last = obs[obs.available_at_as_of]
            if spec.model_version in ("rate_continuation/1", C.WHATIF_MODEL) and last.empty:
                u = Unsupported("no_anchor_observation", f"No survey on or before as_of {spec.as_of}; the first survey is "
                                f"{obs.date.iloc[0]}. A projection must start from an observation.", "as_of")
                manifest["status"], manifest["outcome"] = "unsupported", {"status": "unsupported", **asdict(u)}
                unsupported = u
            else:
                _write_csv(out, manifest, "observed.csv", obs, "Observed group means at survey dates")
                _record_types(manifest, obs)
                manifest["outcome"] = {"status": "completed", "n_observations": len(obs),
                                       "n_available_at_as_of": int(len(last)),
                                       "last_observation_at_as_of": None if last.empty else str(last.date.iloc[-1]),
                                       "final_survey": str(obs.date.iloc[-1])}
                manifest["limitations"] = list(LIMITATIONS)
                if spec.model_version == "rate_continuation/1":
                    _project(spec, out, manifest, obs, last.iloc[-1])
                manifest["status"] = "completed"
                if spec.model_version == C.WHATIF_MODEL:
                    unsupported = _whatif(spec, out, manifest, obs, screening, figures)
                    if unsupported is not None:
                        manifest["status"] = "unsupported"
                        manifest["outcome"] = {**manifest["outcome"], "status": "unsupported", **asdict(unsupported)}
    except Exception as exc:
        manifest["status"] = "failed"
        manifest["outcome"] = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
        manifest["finished_at"] = _now()
        _write_json(out / "manifest.json", manifest)
        raise
    manifest["finished_at"] = _now()
    _write_json(out / "manifest.json", manifest)
    return RunResult(manifest["status"], out, manifest, unsupported)
