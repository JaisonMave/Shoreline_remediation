"""R9 historical next-survey benchmark. Run with python -m validation.remediation_benchmark."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.shoreline_remediation.process_model import TREATMENT_PARAMETERS
from src.shoreline_remediation.projections.catalogue import EVIDENCE
from src.shoreline_remediation.projections.inventory import REFERENCE, build_inventory
from src.shoreline_remediation.projections.slice import manual_vs_natural

PROCESS_KEYS = {REFERENCE: "no_cleanup", "manual_removal": "manual_removal", "passive_sorbents": "passive_sorbents"}


def process_key(option: str) -> str:
    """Resolve a screened research arm without the transport engine's implicit fallback."""
    key = PROCESS_KEYS.get(option)
    if key not in TREATMENT_PARAMETERS:
        raise ValueError(f"No explicit process parameter set for {option!r}")
    return key


def next_surveys(observations: list) -> list:
    """One-step historical forecasts of manual minus untreated, using only paired dates."""
    df = pd.DataFrame(observations)
    fields = ["date", "decimal_year", "value", "n_plots"]
    natural = df.loc[df.role == "reference", fields]
    manual = df.loc[df.role == "intervention", fields]
    paired = natural.merge(manual, on=["date", "decimal_year"], validate="one_to_one",
                           suffixes=("_natural", "_manual")).sort_values("decimal_year")
    years = paired.decimal_year.to_numpy()
    differences = (paired.value_manual - paired.value_natural).to_numpy()
    rows = []
    for i in range(1, len(paired)):
        forecast = {"zero": 0.0, "persistence": float(differences[i - 1])}
        if i >= 3:
            time = years[:i] - years[0]
            slope, intercept = np.polyfit(time, differences[:i], 1)
            forecast["linear"] = float(intercept + slope * (years[i] - years[0]))
        target = paired.iloc[i]
        rows.append({"cutoff": paired.iloc[i - 1].date, "target": target.date,
                     "lead_years": float(years[i] - years[i - 1]), "n_manual": int(target.n_plots_manual),
                     "n_untreated": int(target.n_plots_natural), "observed_difference": float(differences[i]),
                     "predictions": forecast, "errors": {k: float(v - differences[i]) for k, v in forecast.items()}})
    return rows


def scores(rows: list, rules: tuple) -> dict:
    if not rows:
        return {}
    return {rule: {"mae": float(np.mean([abs(r["errors"][rule]) for r in rows])),
                   "bias": float(np.mean([r["errors"][rule] for r in rows]))} for rule in rules}


def benchmark():
    root = Path(__file__).resolve().parents[1]
    report = json.loads((root / "results/projection_baseline/bay_jimmy_mapped.report.json").read_text(encoding="utf-8"))
    inventory = build_inventory(report)
    history = manual_vs_natural(inventory)
    outcomes = {}
    for endpoint, panel in history["endpoints"].items():
        rows = next_surveys(panel["observations"])
        common = [r for r in rows if "linear" in r["errors"]]
        baselines = ("zero", "persistence")
        matched = scores(common, (*baselines, "linear"))
        verdict = "insufficient_paired_dates"
        if matched:
            linear = matched["linear"]
            advance = all(linear["mae"] < matched[k]["mae"] and abs(linear["bias"]) <= abs(matched[k]["bias"])
                          for k in baselines)
            verdict = "eligible_for_external_test" if advance else "fails_temporal_comparison"
        outcomes[endpoint] = {
            "unit": "percentage points" if endpoint == "total_vegetation_cover" else inventory.reference(endpoint).endpoint_unit,
            "transitions": rows, "baseline_only_scores": scores([r for r in rows if "linear" not in r["errors"]], baselines),
            "common_test_pairs": len(common), "common_scores": matched, "challenger_verdict": verdict,
        }
    mappings = {}
    for row in inventory.rows:
        if row.endpoint != "cumulative_shoreline_retreat" or not (row.role == "reference" or row.what_if_allowed):
            continue
        try:
            mappings[row.option] = {"key": process_key(row.option)}
        except ValueError as exc:
            mappings[row.option] = {"unavailable_reason": str(exc)}
    sources = {}
    for source_id in ("zengel2015_s1_group_means", "zengel2022_griidc_vegetation", "zengel2022_griidc_field_positions"):
        path = EVIDENCE[source_id].path
        sources[source_id] = {"path": path, "file_sha256": hashlib.sha256((root / path).read_bytes()).hexdigest()}
    return {"protocol": "R9/1", "site": inventory.site_id, "observation_sources": sources,
            "process_parameter_inventory": mappings, "outcomes": outcomes}


if __name__ == "__main__":
    print(json.dumps(benchmark(), indent=2, allow_nan=False))
