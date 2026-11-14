"""F11 integrated validation runner; execute once after its pre-run plan is written."""
from __future__ import annotations

import csv
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.shoreline_remediation.data_model import Scenario
from src.shoreline_remediation.decision_pipeline import decide_case, run_decision
from validation.historical_validation import CASES, INPUT_SPECS, sample_scenarios

OUT = ROOT / "results" / "f11_validation"
REPORTS = OUT / "reports"
N_DRAWS = 40


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Two-sided Wilson interval, including stable endpoints for zero successes."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = successes / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return max(0.0, centre - half), min(1.0, centre + half)


def report_class(report) -> str:
    """F11 definition: any A is active; otherwise the monitor headline is natural."""
    if any(row["recommendation_class"] == "A" for row in report.options):
        return "active"
    if "monitor" in report.headline.lower():
        return "natural"
    return "unclassified"


def metric_row(metric: str, successes: int, n: int, basis: str) -> dict:
    lo, hi = wilson_interval(successes, n)
    return {"metric": metric, "successes": successes, "n": n,
            "rate": successes / n if n else np.nan, "wilson95_low": lo, "wilson95_high": hi,
            "basis": basis}


def modal(values: list[str]) -> str:
    counts = Counter(values)
    return sorted(counts, key=lambda value: (-counts[value], value))[0]


def historical_replay() -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    rows: list[dict] = []
    case_summary: list[dict] = []
    exclusions: list[str] = []
    for case_index, case in enumerate(c for c in CASES if c["Case_ID"] in INPUT_SPECS):
        reports = []
        for draw, scenario in enumerate(sample_scenarios(case["Case_ID"], seed=1100 + case_index), 1):
            blinded = {"Case_ID": case["Case_ID"], "scenario": scenario}
            report = decide_case(blinded, seed=20261114 + draw, n_draws=200)
            reports.append(report)
            classes = {row["option"]: row["recommendation_class"] for row in report.options}
            rows.append({"record_type": "draw", "case_id": case["Case_ID"], "draw": draw,
                         "documented_class": case["response_class"], "pipeline_class": report_class(report),
                         "class_agrees": report_class(report) == case["response_class"],
                         "headline": report.headline, "scope_tier": report.scope_tier,
                         "documented_method": "", "method_class": "", "method_allowed_ab": "",
                         "method_excluded_e": "", "input_provenance": "SOURCED fixed values plus ASSUMED LHS draw"})
            for method in filter(None, case["method_set"].split("|")):
                cls = classes.get(method, "not_present")
                rows.append({"record_type": "method_draw", "case_id": case["Case_ID"], "draw": draw,
                             "documented_class": case["response_class"], "pipeline_class": report_class(report),
                             "class_agrees": report_class(report) == case["response_class"],
                             "headline": report.headline, "scope_tier": report.scope_tier,
                             "documented_method": method, "method_class": cls,
                             "method_allowed_ab": cls in {"A", "B"}, "method_excluded_e": cls == "E",
                             "input_provenance": "SOURCED fixed values plus ASSUMED LHS draw"})
        predicted = [report_class(report) for report in reports]
        modal_class = modal(predicted)
        documented_methods = list(filter(None, case["method_set"].split("|")))
        method_modal = {}
        for method in documented_methods:
            statuses = [next((r["recommendation_class"] for r in report.options if r["option"] == method), "not_present") for report in reports]
            method_modal[method] = modal(statuses)
            if "E" in statuses:
                exclusions.append(f"{case['Case_ID']}: {method} (excluded in {statuses.count('E')}/{N_DRAWS} draws; modal {method_modal[method]})")
        case_summary.append({"case_id": case["Case_ID"], "documented_class": case["response_class"],
                             "pipeline_modal_class": modal_class, "class_agrees": modal_class == case["response_class"],
                             "n_draws": N_DRAWS, "documented_methods": "|".join(documented_methods),
                             "method_modal_classes": json.dumps(method_modal, sort_keys=True),
                             "documented_method_exclusions": "; ".join(x.split(": ", 1)[1] for x in exclusions if x.startswith(case["Case_ID"] + ": ")) or "none"})
    replay = pd.DataFrame(rows)
    summaries = pd.DataFrame(case_summary)
    return replay, summaries, exclusions


def cell_replay() -> pd.DataFrame:
    held = pd.read_csv(ROOT / "results" / "scenario_composer" / "c1c_cells.csv")
    sites = pd.read_csv(ROOT / "data" / "demo" / "p5_sites.csv")
    data = held[["basin", "cell"]].merge(sites, on=["basin", "cell"], how="left", validate="one_to_one")
    results = []
    for row in data.itertuples(index=False):
        site = row._asdict()
        report = run_decision(site, seed=20261114, n_draws=100, label=f"F11 C1c {site['cell']}")
        counts = Counter(option["recommendation_class"] for option in report.options)
        lookup = {option["option"]: option["recommendation_class"] for option in report.options}
        results.append({"cell": site["cell"], "basin": site["basin"], "headline": report.headline,
                        "headline_kind": report_class(report), "scope_tier": report.scope_tier,
                        "class_A_options": counts["A"], "class_B_options": counts["B"], "class_D_options": counts["D"],
                        "class_E_options": counts["E"], "planting_class_A": lookup.get("planting (after mechanical cleanup)") == "A",
                        "manual_removal_class_A": lookup.get("manual_removal") == "A",
                        "n_draws": 100, "coverage_note": "C1c/B1c coverage cited; not recomputed"})
    detail = pd.DataFrame(results)
    summary = detail.groupby("basin", dropna=False).agg(cells=("cell", "count"), monitor_headline_share=("headline_kind", lambda x: (x == "natural").mean()),
        planting_class_A_share=("planting_class_A", "mean"), manual_removal_class_A_share=("manual_removal_class_A", "mean"),
        mean_class_A_options=("class_A_options", "mean")).reset_index()
    pooled = pd.DataFrame([{"basin": "pooled", "cells": len(detail), "monitor_headline_share": (detail["headline_kind"] == "natural").mean(),
                            "planting_class_A_share": detail["planting_class_A"].mean(), "manual_removal_class_A_share": detail["manual_removal_class_A"].mean(),
                            "mean_class_A_options": detail["class_A_options"].mean()}])
    summary = pd.concat([summary, pooled], ignore_index=True)
    summary["cell"] = "ALL"
    summary["headline"] = "distribution summary"
    summary["headline_kind"] = "distribution"
    summary["scope_tier"] = "validated/experimental components"
    summary["class_A_options"] = summary["mean_class_A_options"]
    summary["class_B_options"] = np.nan
    summary["class_D_options"] = np.nan
    summary["class_E_options"] = np.nan
    summary["planting_class_A"] = summary["planting_class_A_share"]
    summary["manual_removal_class_A"] = summary["manual_removal_class_A_share"]
    summary["n_draws"] = 100
    summary["coverage_note"] = "C1c coverage: Barataria 94.6% (501); Breton 80.6% (31); pooled 93.8% (532). B1c coverage: 92.4%; cited, not recomputed."
    return pd.concat([detail, summary[detail.columns]], ignore_index=True)



def scope_table() -> pd.DataFrame:
    return pd.DataFrame([
        {"habitat_or_request": "Heavy salt marsh, northern Gulf of Mexico", "scope": "validated", "evidence": "edge_loss_v1 held out by basin; pah_decline_v1 within DWH", "main_limits": "one spill; treatment composer remains experimental; D32/C1c bias gate failed"},
        {"habitat_or_request": "Other salt-marsh inputs", "scope": "experimental", "evidence": "composer, vegetation curve and literature effects; registry marks composer/vegetation experimental", "main_limits": "generic scenarios lack cell validation; heavy-oil vegetation curve worse than no-trend baseline"},
        {"habitat_or_request": "Mangrove", "scope": "experimental", "evidence": "mangrove_damage_v1 and mangrove screening", "main_limits": "one-spill damage evidence; screening AI-proposed pending human review"},
        {"habitat_or_request": "Sand beaches, rocky shores, gravel and other habitats", "scope": "rules & literature", "evidence": "screening_rule and evidence_verdicts/literature; no site forecast", "main_limits": "not outcome-validated; literature is not a local treatment-effect prediction"},
        {"habitat_or_request": "Other contaminants, cost optimisation, offshore response", "scope": "out of scope", "evidence": "D30/F0 refusal rule", "main_limits": "no supported forecasting or cost data"},
    ])


def make_reports() -> list[str]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    made = []
    for source in sorted((ROOT / "results" / "f9_pipeline").glob("*.json")):
        target = REPORTS / f"f9_example_{source.name}"
        if not target.exists():
            shutil.copyfile(source, target)
        made.append(target.name)
    scenarios = [
        ("new_marsh_heavy.json", Scenario(shoreline_type="marsh", oil_coverage=80, oil_category="heavy", shoreline_sensitivity="high")),
        ("new_marsh_light.json", Scenario(shoreline_type="marsh", oil_coverage=25, oil_category="medium")),
        ("new_mangrove_heavy.json", Scenario(shoreline_type="mangrove", oil_coverage=85, oil_category="heavy")),
        ("new_sand_moderate.json", Scenario(shoreline_type="sand_beach", oil_coverage=50, oil_category="medium")),
        ("new_bedrock_heavy.json", Scenario(shoreline_type="bedrock", oil_coverage=80, oil_category="heavy")),
        ("new_cobble_light.json", Scenario(shoreline_type="cobble", oil_coverage=15, oil_category="light")),
    ]
    for name, scenario in scenarios:
        target = REPORTS / name
        if not target.exists():
            report = run_decision(scenario, seed=20261114, n_draws=200, label=f"F11 panel {name}")
            target.write_text(report.to_json() + "\n", encoding="utf-8")
        made.append(name)
    return made


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    replay_path = OUT / "historical_replay.csv"
    if replay_path.exists():
        replay = pd.read_csv(replay_path)
        draw_rows = replay[replay.record_type == "draw"]
        cases = []
        exclusions = []
        for case_id, group in draw_rows.groupby("case_id"):
            predicted = group.pipeline_class.tolist()
            documented = group.documented_class.iloc[0]
            modal_class = modal(predicted)
            method_group = replay[(replay.record_type == "method_draw") & (replay.case_id == case_id)]
            excluded = []
            for method, methods in method_group.groupby("documented_method"):
                count = int((methods.method_class == "E").sum())
                if count:
                    text = f"{case_id}: {method} (excluded in {count}/{N_DRAWS} draws; modal {modal(methods.method_class.tolist())})"
                    exclusions.append(text)
                    excluded.append(text.split(": ", 1)[1])
            cases.append({"case_id": case_id, "documented_class": documented, "pipeline_modal_class": modal_class,
                          "class_agrees": modal_class == documented, "documented_method_exclusions": "; ".join(excluded) or "none"})
        cases = pd.DataFrame(cases)
    else:
        replay, cases, exclusions = historical_replay()
        replay.to_csv(replay_path, index=False)
    class_successes = int(cases["class_agrees"].sum())
    method_rows = replay[(replay.record_type == "method_draw") & (replay.documented_method != "natural_attenuation")]
    allowed = method_rows.method_allowed_ab.astype(bool) & ~method_rows.method_excluded_e.astype(bool)
    metrics = [metric_row("active_vs_natural_modal_case_agreement", class_successes, len(cases), "modal class across 40 blinded LHS draws; n=6 cases"),
               metric_row("always_active_baseline", int((cases.documented_class == "active").sum()), len(cases), "all cases predicted active"),
               metric_row("majority_class_baseline", int(cases.documented_class.value_counts().max()), len(cases), "majority documented class"),
               metric_row("documented_active_method_allowed_not_excluded_draw_rate", int(allowed.sum()), len(method_rows), "documented active methods only; classes A/B and not E per draw")]
    for _, row in cases.iterrows():
        case_draws = replay[(replay.record_type == "draw") & (replay.case_id == row.case_id)]
        metrics.append(metric_row(f"case_modal_class_agreement:{row.case_id}", int(row.class_agrees), 1, "modal across 40 draws"))
        metrics.append(metric_row(f"case_draw_class_agreement:{row.case_id}", int(case_draws.class_agrees.astype(bool).sum()), len(case_draws), "individual blinded LHS draws; non-independent sensitivity"))
        case_methods = replay[(replay.record_type == "method_draw") & (replay.case_id == row.case_id) & (replay.documented_method != "natural_attenuation")]
        if len(case_methods):
            case_allowed = case_methods.method_allowed_ab.astype(bool) & ~case_methods.method_excluded_e.astype(bool)
            metrics.append(metric_row(f"case_documented_method_allowed:{row.case_id}", int(case_allowed.sum()), len(case_methods), "documented active methods only; classes A/B and not E per draw"))
    pd.DataFrame(metrics).to_csv(OUT / "metrics.csv", index=False)
    cell_path = OUT / "cell_replay_summary.csv"
    if not cell_path.exists():
        cell_replay().to_csv(cell_path, index=False)
    scope_path = OUT / "scope_table.csv"
    if not scope_path.exists():
        scope_table().to_csv(scope_path, index=False)
    reports = make_reports()
    archived = pd.read_csv(ROOT / "results" / "historical" / "metrics.csv", index_col=0)["value"].to_dict()
    v3 = pd.read_csv(ROOT / "results" / "historical_v3" / "metrics.csv", index_col=0)["value"].to_dict()
    metric_df = pd.DataFrame(metrics).set_index("metric")
    lines = ["F11 integrated validation: single pre-specified run.", "",
             f"Historical modal active/natural agreement: {class_successes}/{len(cases)} (Wilson 95% {metric_df.loc['active_vs_natural_modal_case_agreement','wilson95_low']:.3f}–{metric_df.loc['active_vs_natural_modal_case_agreement','wilson95_high']:.3f}).",
             f"Always-active and majority baselines: {int((cases.documented_class == 'active').sum())}/{len(cases)}.",
             f"Documented active-method draw rate allowed (A/B) and not excluded (E): {int(allowed.sum())}/{len(method_rows)}.",
             "Six sourced cases are too few for a general performance claim; intervals are descriptive.", "",
             "Methods excluded by the pipeline (review disagreements):", *(exclusions or ["none"]), "",
             f"Archived comparison: V4-R2 historical method top-choice agreement {archived.get('method_agreement')}/{archived.get('method_cases')}; v3 {v3.get('method_agreement')}/{v3.get('method_cases')}. Archived active/natural agreement is {archived.get('class_agreement')}/{archived.get('n_cases')} for V4-R2 and {v3.get('class_agreement')}/{v3.get('n_cases')} for v3.",
             "Cell replay covers C1c heavy held-out cells. C1c coverage is cited rather than recomputed: pooled 93.8% (532 cells); B1c 92.4%. See cell_replay_summary.csv.",
             f"Expert panel pack contains {len(reports)} reports. No reviewer responses were created."]
    (OUT / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
