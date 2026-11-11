"""Expert scoring: build blind scoring sheets, measure agreement between experts, and turn scores into labels.

The suitability model is trained on rule-generated labels. Expert scores are the first real replacement.
This module supports the protocol in docs/EXPERT_SCORING_PROTOCOL.md:

    python -m src.shoreline_remediation.expert_scoring sheet            # writes data/expert_scoring_sheet.csv
    python -m src.shoreline_remediation.expert_scoring combine a.csv b.csv c.csv

Agreement is measured with ICC(2,1): the two-way random-effects, absolute-agreement, single-rater intraclass
correlation of Shrout and Fleiss (1979). It answers "if another expert scored this scenario, how close would
the score be?". Common reading: below 0.5 poor, 0.5 to 0.75 moderate, 0.75 to 0.9 good, above 0.9 excellent
(Koo and Li 2016).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .data_model import TREATMENT_LIBRARY

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
SCENARIO_COLUMNS = [
    "scenario_id", "shoreline_type", "substrate_permeability", "oil_category", "viscosity_cP", "weathering_pct",
    "oil_coverage_pct", "oil_thickness_cm", "oil_distribution", "penetration_depth_cm", "subsurface_oil",
    "wave_exposure", "tidal_range_m", "temperature_C", "season", "shoreline_sensitivity", "vegetation",
    "recovery_potential", "accessibility", "waste_handling",
]
MIN_ACCEPTABLE_ICC = 0.5
HIGH_DISAGREEMENT_SD = 2.0  # on the 0-10 scale


def build_scoring_sheet(n_scenarios: int = 30, seed: int = 11, source: str | Path | None = None) -> pd.DataFrame:
    """Pick scenarios spread evenly across shoreline types and return a sheet with one empty score column per
    treatment. The rule-generated scores in the source file are left out so they cannot anchor the experts."""
    scenarios = pd.read_csv(source or DATA_DIR / "scenario_training_dataset.csv")
    rng = np.random.default_rng(seed)
    shuffled = scenarios.iloc[rng.permutation(len(scenarios))]
    # Deal scenarios out one shoreline type at a time so every type is represented.
    order = shuffled.groupby("shoreline_type").cumcount()
    chosen = shuffled.assign(_turn=order).sort_values(["_turn", "shoreline_type"]).head(n_scenarios)
    sheet = chosen[SCENARIO_COLUMNS].sort_values("scenario_id").reset_index(drop=True)
    for treatment in TREATMENT_LIBRARY:
        sheet[treatment] = ""
    sheet["notes"] = ""
    return sheet


def icc_absolute_agreement(scores: np.ndarray) -> float:
    """ICC(2,1) for a complete table with one row per scored item and one column per expert."""
    scores = np.asarray(scores, dtype=float)
    if scores.ndim != 2 or scores.shape[0] < 2 or scores.shape[1] < 2 or np.isnan(scores).any():
        raise ValueError("ICC needs a complete table with at least 2 items and 2 experts.")
    n, k = scores.shape
    grand = scores.mean()
    ms_items = k * np.sum((scores.mean(axis=1) - grand) ** 2) / (n - 1)
    ms_experts = n * np.sum((scores.mean(axis=0) - grand) ** 2) / (k - 1)
    residual = scores - scores.mean(axis=1, keepdims=True) - scores.mean(axis=0, keepdims=True) + grand
    ms_error = np.sum(residual**2) / ((n - 1) * (k - 1))
    denominator = ms_items + (k - 1) * ms_error + k * (ms_experts - ms_error) / n
    return float((ms_items - ms_error) / denominator) if denominator > 0 else float("nan")


def combine_expert_scores(sheets: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Combine filled sheets. Returns (labels, agreement, disputed):

    labels     one row per scenario: the mean score per treatment, plus '<treatment>_sd'
    agreement  ICC(2,1) and mean between-expert SD per treatment, with a usable / not usable verdict
    disputed   scenario-treatment pairs where experts differ by more than HIGH_DISAGREEMENT_SD
    """
    if len(sheets) < 2:
        raise ValueError("At least two experts are needed to measure agreement; three or more are recommended.")
    names = list(sheets)
    indexed = {name: sheet.set_index("scenario_id") for name, sheet in sheets.items()}
    common = sorted(set.intersection(*(set(frame.index) for frame in indexed.values())))
    if not common:
        raise ValueError("The sheets share no scenario_id values.")
    labels = pd.DataFrame({"scenario_id": common})
    agreement_rows, disputed_rows = [], []
    for treatment in TREATMENT_LIBRARY:
        table = np.column_stack([pd.to_numeric(indexed[name].loc[common, treatment], errors="coerce") for name in names])
        if np.isnan(table).any():
            raise ValueError(f"Missing or non-numeric scores for '{treatment}'. Every expert must score every scenario.")
        if (table < 0).any() or (table > 10).any():
            raise ValueError(f"Scores for '{treatment}' must lie between 0 and 10.")
        spread = table.std(axis=1, ddof=1)
        labels[treatment] = table.mean(axis=1).round(2)
        labels[f"{treatment}_sd"] = spread.round(2)
        icc = icc_absolute_agreement(table)
        agreement_rows.append({
            "treatment": treatment, "icc_2_1": round(icc, 3), "mean_between_expert_sd": round(float(spread.mean()), 2),
            "usable_as_labels": bool(icc >= MIN_ACCEPTABLE_ICC),
        })
        for scenario_id, sd, row in zip(common, spread, table):
            if sd > HIGH_DISAGREEMENT_SD:
                disputed_rows.append({"scenario_id": scenario_id, "treatment": treatment, "sd": round(float(sd), 2),
                                      **{name: value for name, value in zip(names, row)}})
    return labels, pd.DataFrame(agreement_rows), pd.DataFrame(disputed_rows)


def main(arguments: list[str]) -> None:
    if arguments[:1] == ["sheet"]:
        path = DATA_DIR / "expert_scoring_sheet.csv"
        build_scoring_sheet().to_csv(path, index=False)
        print(f"Wrote {path}. Send one copy to each expert; they must not see each other's scores.")
    elif arguments[:1] == ["combine"] and len(arguments) >= 3:
        sheets = {Path(name).stem: pd.read_csv(name) for name in arguments[1:]}
        labels, agreement, disputed = combine_expert_scores(sheets)
        labels.to_csv(DATA_DIR / "expert_labels.csv", index=False)
        agreement.to_csv(DATA_DIR / "expert_agreement.csv", index=False)
        disputed.to_csv(DATA_DIR / "expert_disputed_items.csv", index=False)
        print(agreement.to_string(index=False))
        print(f"\n{len(disputed)} scenario-treatment pairs need discussion (see data/expert_disputed_items.csv).")
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
