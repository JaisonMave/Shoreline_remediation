from __future__ import annotations

import csv
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
EFFECTS = ROOT / "data" / "knowledge" / "literature_effects.csv"
SOURCES = ROOT / "data" / "knowledge" / "literature_sources.csv"
POOLED = ROOT / "data" / "knowledge" / "pooled_effects.csv"
VERDICTS = ROOT / "data" / "knowledge" / "evidence_verdicts.csv"
TAU_RANGES = ROOT / "data" / "knowledge" / "literature_tau_ranges.csv"
RESULTS = ROOT / "results" / "f8_pooling"
ROW_EFFECTS = RESULTS / "row_effects.csv"
SUMMARY = RESULTS / "summary.txt"
V1_VERDICTS = RESULTS / "v1" / "evidence_verdicts.csv"

PRIMARY_GRADES = {"A", "B", "C"}
SENSITIVITY_GRADES = PRIMARY_GRADES | {"D"}
Z975 = float(stats.norm.ppf(0.975))


def _num(value: Any) -> float:
    try:
        result = float(str(value).strip())
    except (TypeError, ValueError):
        return math.nan
    return result if math.isfinite(result) else math.nan


def _spread_sd(spread: Any, spread_type: Any, n: Any) -> float:
    value, size = _num(spread), _num(n)
    kind = str(spread_type).strip().lower()
    if not math.isfinite(value) or value < 0:
        return math.nan
    if kind.startswith("sd"):
        return value
    if kind.startswith("se") and math.isfinite(size) and size > 0:
        return value * math.sqrt(size)
    return math.nan


def log_response_ratio(
    treated_mean: float,
    control_mean: float,
    treated_spread: Any = math.nan,
    control_spread: Any = math.nan,
    n_treated: Any = math.nan,
    n_control: Any = math.nan,
    treated_spread_type: str = "SD",
    control_spread_type: str = "SD",
) -> tuple[float, float]:
    """Return ln(treated/control) and its delta-method sampling variance."""
    treated, control = float(treated_mean), float(control_mean)
    if treated <= 0 or control <= 0:
        raise ValueError("lnRR requires positive treated and control means")
    effect = math.log(treated / control)
    sd_t = _spread_sd(treated_spread, treated_spread_type, n_treated)
    sd_c = _spread_sd(control_spread, control_spread_type, n_control)
    nt, nc = _num(n_treated), _num(n_control)
    if not (math.isfinite(sd_t) and sd_t >= 0 and math.isfinite(sd_c) and sd_c >= 0
            and math.isfinite(nt) and nt > 0 and math.isfinite(nc) and nc > 0):
        return effect, math.nan
    variance = sd_t**2 / (nt * treated**2) + sd_c**2 / (nc * control**2)
    return effect, variance if variance > 0 else math.nan


def verdict_rule(
    *,
    n_studies: int,
    effect: float = math.nan,
    ci_lo: float = math.nan,
    ci_hi: float = math.nan,
    pi_lo: float = math.nan,
    pi_hi: float = math.nan,
    grade: str = "",
    pooled: bool = False,
    has_evidence: bool = True,
    study_intervals: list[tuple[float, float, float]] | None = None,
) -> str:
    if not has_evidence or n_studies < 1:
        return "no evidence"
    if pooled:
        if not all(math.isfinite(x) for x in (effect, pi_lo, pi_hi)):
            return "no clear difference"
        if pi_lo > 0:
            return "evidence of benefit"
        if pi_hi < 0:
            return "evidence of harm"
        return "no clear difference"
    if study_intervals is not None:
        benefit = any(lo > 0 for _, lo, _ in study_intervals)
        harm = any(hi < 0 for _, _, hi in study_intervals)
        if benefit and not harm:
            return "evidence of benefit"
        if harm and not benefit:
            return "evidence of harm"
        return "no clear difference"
    if n_studies == 1 and grade in {"A", "B"} and all(
        math.isfinite(x) for x in (effect, ci_lo, ci_hi)
    ):
        if ci_lo > 0:
            return "evidence of benefit"
        if ci_hi < 0:
            return "evidence of harm"
    return "no clear difference"

def _habitat_class(text: str) -> str:
    value = text.lower()
    if "mangrove" in value or "rhizophora" in value:
        return "mangrove"
    if any(word in value for word in ("marsh", "spartina", "salicornia", "wetland")):
        return "marsh"
    if any(word in value for word in ("rock", "bedrock", "hard substrate", "riprap", "seawall")):
        return "rocky/hard"
    if any(word in value for word in ("sand", "gravel", "pebble", "cobble", "beach", "sediment")):
        return "sand/gravel beach"
    return "other"


def _outcome_family(row: dict[str, str]) -> str:
    if row.get("effect_id", "").strip().upper() == "C011":
        return ""
    text = " ".join(
        str(row.get(key, ""))
        for key in ("outcome", "metric", "effect_type", "unit", "treatment_detail")
    ).lower()
    if any(
        word in text
        for word in (
            "rate constant",
            "rate-constant",
            "decay rate",
            "half-life",
            "half_life",
            "biodegradation rate",
            "acceleration factor",
            "annualized loss rate",
        )
    ):
        return "degradation rate"
    if any(word in text for word in ("erosion", "shoreline retreat", "sediment loss", "elevation change")):
        return "erosion"
    if any(
        word in text
        for word in (
            "vegetation",
            "plant",
            "algal",
            "fucus",
            "fauna",
            "clam",
            "bivalve",
            "limpet",
            "mussel",
            "invertebrate",
            "infauna",
            "epibiota",
            "biota",
            "biomass",
            "species",
            "survival",
            "abundance",
            "density",
            "recruitment",
            "community recovery",
        )
    ):
        return "biological recovery"
    if any(
        word in text
        for word in (
            "oil removal",
            "oil recovered",
            "oil remain",
            "residual oil",
            "hydrocarbon mass",
            "hydrocarbon mobilization",
            "oil cover",
            "persistence",
            "percent removed",
            "percent loss",
            "percent decrease",
            "percent reduction",
            "reduction factor",
        )
    ):
        return "residual oil"
    return ""

def _parse_time_days(value: Any) -> float:
    text = str(value).strip().replace(",", "")
    if not text:
        return math.nan
    numbers = [float(item) for item in re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?", text)]
    return max(numbers) if numbers else math.nan


def _study_id(row: dict[str, str]) -> str:
    experiment = re.sub(r"\W+", " ", row.get("spill_or_experiment", "").lower()).strip()
    if experiment and experiment not in {"multiple", "unknown"}:
        return f"experiment:{experiment}"
    doi = row.get("doi", "").strip().lower()
    if doi:
        return f"doi:{doi}"
    citation = re.sub(r"\W+", " ", row.get("citation", "").lower()).strip()
    return f"citation:{citation}"


def _citation_label(citation: str) -> str:
    citation = citation.strip()
    if not citation:
        return "citation unavailable"
    match = re.match(r"([^,(]+(?: et al\.)?).*?\((\d{4})", citation)
    if match:
        return f"{match.group(1).strip()} ({match.group(2)})"
    return citation[:100]


def _is_abstract(row: dict[str, str]) -> bool:
    return "abstract" in row.get("value_origin", "").lower()


def _percent_removal(row: dict[str, str]) -> float:
    effect_type = row.get("effect_type", "").lower()
    outcome = row.get("outcome", "").lower()
    if not any(term in effect_type for term in ("percent_oil_removed", "percent_oil_recovered", "percent removed")):
        return math.nan
    value = _num(row.get("reported_effect"))
    if not math.isfinite(value) and "remov" in outcome:
        value = _num(row.get("treated_mean"))
    return value


def _effect_from_row(row: dict[str, str], family: str) -> tuple[float, float, str, float, float]:
    treated, control = _num(row.get("treated_mean")), _num(row.get("control_mean"))
    nt, nc = _num(row.get("n_treated")), _num(row.get("n_control"))
    effect_type = row.get("effect_type", "").lower()
    metric = row.get("metric", "").lower()
    if "threshold" in effect_type:
        return math.nan, math.nan, "threshold metric is not a treated/control effect", math.nan, math.nan

    removal = _percent_removal(row)
    if family == "residual oil" and math.isfinite(removal):
        if removal < 0 or removal >= 100:
            return math.nan, math.nan, "invalid percent removal for finite residual-oil lnRR", math.nan, math.nan
        raw = math.log(1.0 - removal / 100.0)
        return -raw, math.nan, "percent removal converted to residual-oil lnRR", math.nan, math.nan

    is_rate = family == "degradation rate"
    if is_rate and (not math.isfinite(treated) or not math.isfinite(control)):
        ratio = _num(row.get("reported_effect"))
        if math.isfinite(ratio) and ratio > 0 and ("ratio" in effect_type or "ratio" in metric):
            return math.log(ratio), math.nan, "reported rate-constant ratio", math.nan, math.nan

    if not math.isfinite(treated) or not math.isfinite(control):
        return math.nan, math.nan, "numeric treated and control means unavailable", math.nan, math.nan
    if is_rate:
        treated, control = abs(treated), abs(control)
    if treated <= 0 or control <= 0:
        return math.nan, math.nan, "non-positive arm mean cannot form lnRR", math.nan, math.nan

    raw, variance = log_response_ratio(
        treated,
        control,
        row.get("treated_spread", ""),
        row.get("control_spread", ""),
        nt,
        nc,
        row.get("treated_spread_type", ""),
        row.get("control_spread_type", ""),
    )
    direction = 1.0
    detail = "ln(treated/control)"
    recovery_time = "recovery time" in (row.get("outcome", "") + " " + metric).lower()
    if family in {"residual oil", "erosion"} or recovery_time:
        direction = -1.0
        detail += "; sign reversed so benefit is positive"
    sd_t = _spread_sd(row.get("treated_spread"), row.get("treated_spread_type"), nt)
    sd_c = _spread_sd(row.get("control_spread"), row.get("control_spread_type"), nc)
    cv_t = sd_t / treated if math.isfinite(sd_t) and treated > 0 else math.nan
    cv_c = sd_c / control if math.isfinite(sd_c) and control > 0 else math.nan
    return direction * raw, variance, detail, cv_t, cv_c


def _fixed_collapse(rows: list[dict[str, Any]], variance_key: str = "variance_used") -> dict[str, Any]:
    finite = [r for r in rows if math.isfinite(r["effect"]) and math.isfinite(r.get(variance_key, math.nan)) and r.get(variance_key, 0) > 0]
    if finite:
        weights = np.array([1.0 / r[variance_key] for r in finite])
        effects = np.array([r["effect"] for r in finite])
        return {"effect": float(np.sum(weights * effects) / np.sum(weights)), "variance": float(1.0 / np.sum(weights)), "n_rows": len(finite)}
    effects = [r["effect"] for r in rows if math.isfinite(r["effect"])]
    return {"effect": float(np.mean(effects)) if effects else math.nan, "variance": math.nan, "n_rows": len(effects)}


def _select_time(rows: list[dict[str, Any]], longest: bool = False) -> list[dict[str, Any]]:
    timed = [r for r in rows if math.isfinite(r["time_days"])]
    if not timed:
        return rows
    if longest:
        target = max(r["time_days"] for r in timed)
    else:
        within = [r["time_days"] for r in timed if r["time_days"] <= 730]
        target = max(within) if within else min(r["time_days"] for r in timed)
    return [r for r in timed if r["time_days"] == target]


def _study_estimates(
    rows: list[dict[str, Any]], longest: bool, sensitivity: bool, mark_selection: bool = True
) -> list[dict[str, Any]]:
    by_study: dict[str, list[dict[str, Any]]] = defaultdict(list)
    grades = SENSITIVITY_GRADES if sensitivity else PRIMARY_GRADES
    for row in rows:
        if row["grade"] in grades and row["eligible_effect"]:
            by_study[row["study_id"]].append(row)
    estimates = []
    variance_key = "sensitivity_variance" if sensitivity else "variance"
    for study_id, study_rows in by_study.items():
        selected = _select_time(study_rows, longest=longest)
        collapsed = _fixed_collapse(selected, variance_key)
        selected_ids = ";".join(r["effect_id"] for r in selected)
        if mark_selection:
            for row in selected:
                row["selected_longest" if longest else "selected_primary"] = "yes"
        estimates.append(
            {
                "study_id": study_id,
                "effect": collapsed["effect"],
                "variance": collapsed["variance"],
                "grade": min((r["grade"] for r in selected), default=""),
                "citation": selected[0]["citation"] if selected else "",
                "citation_label": _citation_label(selected[0]["citation"]) if selected else "",
                "effect_ids": selected_ids,
                "time_days": max((r["time_days"] for r in selected if math.isfinite(r["time_days"])), default=math.nan),
            }
        )
    return estimates


def _random_effects(estimates: list[dict[str, Any]]) -> dict[str, float]:
    usable = [e for e in estimates if math.isfinite(e["effect"]) and math.isfinite(e["variance"]) and e["variance"] > 0]
    k = len(usable)
    empty = {key: math.nan for key in ("effect", "ci_lo", "ci_hi", "pi_lo", "pi_hi", "tau2", "i2")}
    empty["k"] = k
    if k < 3:
        return empty
    yi = np.array([e["effect"] for e in usable], dtype=float)
    vi = np.array([e["variance"] for e in usable], dtype=float)
    wi = 1.0 / vi
    fixed = float(np.sum(wi * yi) / np.sum(wi))
    q = float(np.sum(wi * (yi - fixed) ** 2))
    df = k - 1
    c = float(np.sum(wi) - np.sum(wi**2) / np.sum(wi))
    tau2 = max(0.0, (q - df) / c) if c > 0 else 0.0
    wr = 1.0 / (vi + tau2)
    pooled = float(np.sum(wr * yi) / np.sum(wr))
    q_re = float(np.sum(wr * (yi - pooled) ** 2))
    hk_scale = q_re / df
    se_hk = math.sqrt(hk_scale / float(np.sum(wr)))
    critical = float(stats.t.ppf(0.975, df))
    ci_lo, ci_hi = pooled - critical * se_hk, pooled + critical * se_hk
    pred_df = max(k - 2, 1)
    pred_critical = float(stats.t.ppf(0.975, pred_df))
    pred_se = math.sqrt(tau2 + se_hk**2)
    pi_lo, pi_hi = pooled - pred_critical * pred_se, pooled + pred_critical * pred_se
    i2 = max(0.0, (q - df) / q) * 100.0 if q > 0 else 0.0
    return {"effect": pooled, "ci_lo": ci_lo, "ci_hi": ci_hi, "pi_lo": pi_lo, "pi_hi": pi_hi, "tau2": tau2, "i2": i2, "k": k}


def _single_summary(estimates: list[dict[str, Any]]) -> dict[str, float]:
    if len(estimates) != 1:
        return {"effect": math.nan, "ci_lo": math.nan, "ci_hi": math.nan}
    item = estimates[0]
    effect, variance = item["effect"], item["variance"]
    if math.isfinite(variance) and variance > 0:
        half = Z975 * math.sqrt(variance)
        return {"effect": effect, "ci_lo": effect - half, "ci_hi": effect + half}
    return {"effect": effect, "ci_lo": math.nan, "ci_hi": math.nan}



def _study_interval(estimate: dict[str, Any]) -> tuple[float, float, float] | None:
    effect, variance = estimate["effect"], estimate["variance"]
    if estimate["grade"] not in {"A", "B"} or not (
        math.isfinite(effect) and math.isfinite(variance) and variance > 0
    ):
        return None
    half = Z975 * math.sqrt(variance)
    return effect, effect - half, effect + half


def _study_detail_notes(estimates: list[dict[str, Any]], include_ratio: bool) -> str:
    details = []
    for estimate in estimates:
        if estimate["grade"] not in {"A", "B"}:
            continue
        effect = estimate["effect"]
        interval = _study_interval(estimate)
        detail = f"{estimate['citation_label']}: lnRR={effect:.3f}"
        if include_ratio and math.isfinite(effect):
            detail += f", ratio={math.exp(effect):.3f}"
        if interval is None:
            detail += ", CI unavailable"
        else:
            detail += f", 95% CI [{interval[1]:.3f}, {interval[2]:.3f}]"
        details.append(detail)
    return "study evidence: " + "; ".join(details) if details else ""


def _selected_row_notes(rows: list[dict[str, Any]], include_ratio: bool) -> str:
    details = []
    for row in rows:
        if row["selected_primary"] != "yes" or row["grade"] not in {"A", "B"}:
            continue
        effect, variance = row["effect"], row["variance"]
        if not math.isfinite(effect):
            continue
        detail = f"{row['effect_id']} lnRR={effect:.3f}"
        if include_ratio:
            detail += f" ratio={math.exp(effect):.3f}"
        if math.isfinite(variance) and variance > 0:
            half = Z975 * math.sqrt(variance)
            detail += f" CI [{effect - half:.3f}, {effect + half:.3f}]"
        else:
            detail += " CI unavailable"
        details.append(detail)
    return "selected rows: " + "; ".join(details) if details else ""


def _fmt(value: Any) -> str:
    if isinstance(value, (float, np.floating)):
        return "" if not math.isfinite(float(value)) else f"{float(value):.8g}"
    return str(value)


def _write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _fmt(row.get(field, "")) for field in fields})


def _forest_plot(group: tuple[str, str, str], estimates: list[dict[str, Any]], pooled: dict[str, float]) -> Path:
    usable = [e for e in estimates if math.isfinite(e["variance"]) and e["variance"] > 0]
    labels = [e["citation_label"] for e in usable]
    effects = np.array([e["effect"] for e in usable])
    errors = 1.96 * np.sqrt(np.array([e["variance"] for e in usable]))
    y = np.arange(len(usable), 0, -1)
    fig, ax = plt.subplots(figsize=(8, max(3.2, 0.55 * len(usable) + 1.8)))
    ax.errorbar(effects, y, xerr=errors, fmt="o", color="#1f5a85", capsize=3)
    ax.errorbar(pooled["effect"], 0, xerr=[[pooled["effect"] - pooled["ci_lo"]], [pooled["ci_hi"] - pooled["effect"]]], fmt="D", color="#c44e52", capsize=4)
    ax.axvline(0, color="black", linewidth=0.8, linestyle="--")
    ticks = np.concatenate((y, np.array([0], dtype=int)))
    ax.set_yticks(ticks, labels + ["Pooled (HK 95% CI)"])
    ax.set_xlabel("Benefit-oriented lnRR")
    ax.set_title(" | ".join(group))
    fig.tight_layout()
    name = re.sub(r"[^a-z0-9]+", "_", "_".join(group).lower()).strip("_") + ".png"
    path = RESULTS / name
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def _grade_mix(estimates: list[dict[str, Any]]) -> str:
    counts = Counter(e["grade"] for e in estimates)
    return ";".join(f"{grade}:{counts[grade]}" for grade in sorted(counts))


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    previous_mappings: dict[str, str] = {}
    if ROW_EFFECTS.exists():
        with ROW_EFFECTS.open(encoding="utf-8-sig", newline="") as handle:
            previous_mappings = {
                row["effect_id"]: row.get("outcome_family", "")
                for row in csv.DictReader(handle)
            }
    with EFFECTS.open(encoding="utf-8-sig", newline="") as handle:
        source_rows = list(csv.DictReader(handle))
    with SOURCES.open(encoding="utf-8-sig", newline="") as handle:
        source_index_rows = list(csv.DictReader(handle))

    computed: list[dict[str, Any]] = []
    for original in source_rows:
        row: dict[str, Any] = dict(original)
        row["habitat_class"] = _habitat_class(row.get("habitat", ""))
        row["outcome_family"] = _outcome_family(row)
        row["study_id"] = _study_id(row)
        row["time_days"] = _parse_time_days(row.get("time_since_treatment_days"))
        row["grade"] = row.get("grade", "").strip().upper()
        row["selected_primary"] = "no"
        row["selected_longest"] = "no"
        effect, variance, method, cv_t, cv_c = _effect_from_row(row, row["outcome_family"])
        row.update({"effect": effect, "variance": variance, "effect_method": method, "cv_treated": cv_t, "cv_control": cv_c})

        reasons = []
        control_ok = row.get("untreated_oiled_control", "").strip().lower().startswith("yes")
        if not control_ok:
            reasons.append("no untreated oiled control")
        if not row["outcome_family"]:
            reasons.append("outcome not in a pooling family")
        if row["grade"] not in SENSITIVITY_GRADES:
            reasons.append(f"grade {row['grade'] or 'missing'} outside A-D")
        arms_numeric = math.isfinite(_num(row.get("treated_mean"))) and math.isfinite(_num(row.get("control_mean")))
        if _is_abstract(row) and not arms_numeric:
            reasons.append("abstract-only without both numeric arms")
        if not math.isfinite(effect):
            reasons.append(method)
        row["eligible_effect"] = not reasons
        if reasons:
            row["inclusion_reason"] = "Excluded: " + "; ".join(dict.fromkeys(reasons))
            row["analysis_tier"] = "excluded"
        elif row["grade"] == "D":
            row["inclusion_reason"] = "Sensitivity only: grade D"
            row["analysis_tier"] = "sensitivity"
        elif math.isfinite(variance) and variance > 0:
            row["inclusion_reason"] = "Primary eligible: controlled numeric lnRR with reported variance"
            row["analysis_tier"] = "primary"
        else:
            row["inclusion_reason"] = "Effect eligible; primary meta-analysis excluded because sampling variance is unavailable"
            row["analysis_tier"] = "listing/sensitivity"
        row["variance_status"] = "reported" if math.isfinite(variance) and variance > 0 else "missing"
        row["sensitivity_variance"] = variance
        computed.append(row)

    by_group_all: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in computed:
        if row["outcome_family"]:
            key = (row["technology"], row["habitat_class"], row["outcome_family"])
            by_group_all[key].append(row)

    for group_rows in by_group_all.values():
        cv_t = [r["cv_treated"] for r in group_rows if math.isfinite(r["cv_treated"]) and r["cv_treated"] >= 0]
        cv_c = [r["cv_control"] for r in group_rows if math.isfinite(r["cv_control"]) and r["cv_control"] >= 0]
        med_t = float(np.median(cv_t)) if cv_t else math.nan
        med_c = float(np.median(cv_c)) if cv_c else math.nan
        for row in group_rows:
            if not row["eligible_effect"] or math.isfinite(row["sensitivity_variance"]):
                continue
            nt, nc = _num(row.get("n_treated")), _num(row.get("n_control"))
            if all(math.isfinite(x) and x > 0 for x in (med_t, med_c, nt, nc)):
                row["sensitivity_variance"] = med_t**2 / nt + med_c**2 / nc
                row["variance_status"] = "ASSUMED median group CV"
                row["inclusion_reason"] += "; sensitivity variance imputed from median group CV (ASSUMED)"

    pooled_rows: list[dict[str, Any]] = []
    verdict_rows: list[dict[str, Any]] = []
    tau_rows: list[dict[str, Any]] = []
    plot_paths: list[Path] = []

    for group, group_rows in sorted(by_group_all.items()):
        technology, habitat, family = group
        primary_est = _study_estimates(group_rows, longest=False, sensitivity=False)
        longest_est = _study_estimates(group_rows, longest=True, sensitivity=False)
        sensitivity_est = _study_estimates(group_rows, longest=False, sensitivity=True, mark_selection=False)
        primary_model = _random_effects(primary_est)
        longest_model = _random_effects(longest_est)
        sensitivity_model = _random_effects(sensitivity_est)
        single = _single_summary(primary_est)
        has_evidence = len(primary_est) > 0
        pooled_ok = primary_model["k"] >= 3
        effect = primary_model["effect"] if pooled_ok else single["effect"]
        ci_lo = primary_model["ci_lo"] if pooled_ok else single["ci_lo"]
        ci_hi = primary_model["ci_hi"] if pooled_ok else single["ci_hi"]
        pi_lo = primary_model["pi_lo"] if pooled_ok else math.nan
        pi_hi = primary_model["pi_hi"] if pooled_ok else math.nan
        study_intervals = [
            interval for estimate in primary_est
            if (interval := _study_interval(estimate)) is not None
        ]
        verdict = verdict_rule(
            n_studies=len(primary_est), effect=effect, ci_lo=ci_lo, ci_hi=ci_hi,
            pi_lo=pi_lo, pi_hi=pi_hi, pooled=pooled_ok,
            has_evidence=has_evidence,
            study_intervals=None if pooled_ok else study_intervals,
        )
        if pooled_ok:
            basis = f"pooled k={primary_model['k']}"
            plot_paths.append(_forest_plot(group, primary_est, primary_model))
        elif primary_est:
            citations = "; ".join(dict.fromkeys(e["citation_label"] for e in primary_est))
            basis = f"single studies (k={len(primary_est)}, citations={citations})"
        else:
            basis = "no eligible rows"

        notes = []
        missing_var = sum(not math.isfinite(e["variance"]) for e in primary_est)
        if missing_var:
            notes.append(f"{missing_var} selected study estimate(s) lack variance")
        study_details = _study_detail_notes(primary_est, include_ratio=family == "degradation rate")
        if study_details:
            notes.append(study_details)
        row_details = _selected_row_notes(group_rows, include_ratio=family == "degradation rate")
        if row_details:
            notes.append(row_details)
        if sensitivity_model["k"] >= 3:
            notes.append("sensitivity includes grade D and/or ASSUMED variance where available")
        if not pooled_ok and len(primary_est) >= 1:
            notes.append("fewer than 3 variance-complete independent studies; not pooled")

        pooled_rows.append(
            {
                "technology": technology, "habitat": habitat, "outcome_family": family,
                "effect_scale": "benefit-oriented lnRR", "n_studies": len(primary_est),
                "k": primary_model["k"], "pooled_effect": primary_model["effect"],
                "ci_lo": primary_model["ci_lo"], "ci_hi": primary_model["ci_hi"],
                "pi_lo": primary_model["pi_lo"], "pi_hi": primary_model["pi_hi"],
                "tau2": primary_model["tau2"], "i2": primary_model["i2"],
                "grade_mix": _grade_mix(primary_est),
                "longest_n_studies": len(longest_est), "longest_k": longest_model["k"],
                "longest_effect": longest_model["effect"], "longest_ci_lo": longest_model["ci_lo"],
                "longest_ci_hi": longest_model["ci_hi"], "longest_pi_lo": longest_model["pi_lo"],
                "longest_pi_hi": longest_model["pi_hi"], "longest_tau2": longest_model["tau2"],
                "longest_i2": longest_model["i2"], "sensitivity_k": sensitivity_model["k"],
                "sensitivity_effect": sensitivity_model["effect"], "sensitivity_ci_lo": sensitivity_model["ci_lo"],
                "sensitivity_ci_hi": sensitivity_model["ci_hi"], "sensitivity_pi_lo": sensitivity_model["pi_lo"],
                "sensitivity_pi_hi": sensitivity_model["pi_hi"], "sensitivity_tau2": sensitivity_model["tau2"],
                "sensitivity_i2": sensitivity_model["i2"], "notes": "; ".join(notes),
            }
        )
        verdict_rows.append(
            {
                "technology": technology, "habitat": habitat, "outcome_family": family,
                "verdict": verdict, "basis": basis, "effect": effect, "ci_lo": ci_lo,
                "ci_hi": ci_hi, "pi_lo": pi_lo, "pi_hi": pi_hi,
                "grade_mix": _grade_mix(primary_est), "n_studies": len(primary_est),
                "notes": "; ".join(notes),
            }
        )
        if habitat == "marsh" and family == "biological recovery":
            if pooled_ok:
                tau_rows.append(
                    {
                        "option": technology, "lo": math.exp(pi_lo), "hi": math.exp(pi_hi),
                        "basis": f"ASSUMED mapping exp(95% PI), pooled k={primary_model['k']}; positive biological lnRR -> larger vegetation recovery multiplier",
                    }
                )
            elif len(primary_est) == 1:
                interval = _study_interval(primary_est[0])
                if interval is not None:
                    tau_rows.append(
                        {
                            "option": technology, "lo": math.exp(interval[1]), "hi": math.exp(interval[2]),
                            "basis": f"ASSUMED mapping exp(single-study 95% CI), {primary_est[0]['citation_label']}; positive biological lnRR -> larger vegetation recovery multiplier",
                        }
                    )

    row_fields = list(source_rows[0].keys()) + [
        "habitat_class", "outcome_family", "study_id", "time_days", "effect",
        "variance", "effect_method", "cv_treated", "cv_control", "eligible_effect",
        "analysis_tier", "variance_status", "sensitivity_variance", "selected_primary",
        "selected_longest", "inclusion_reason",
    ]
    pooled_fields = [
        "technology", "habitat", "outcome_family", "effect_scale", "n_studies", "k",
        "pooled_effect", "ci_lo", "ci_hi", "pi_lo", "pi_hi", "tau2", "i2", "grade_mix",
        "longest_n_studies", "longest_k", "longest_effect", "longest_ci_lo", "longest_ci_hi",
        "longest_pi_lo", "longest_pi_hi", "longest_tau2", "longest_i2", "sensitivity_k",
        "sensitivity_effect", "sensitivity_ci_lo", "sensitivity_ci_hi", "sensitivity_pi_lo",
        "sensitivity_pi_hi", "sensitivity_tau2", "sensitivity_i2", "notes",
    ]
    verdict_fields = [
        "technology", "habitat", "outcome_family", "verdict", "basis", "effect", "ci_lo",
        "ci_hi", "pi_lo", "pi_hi", "grade_mix", "n_studies", "notes",
    ]
    _write_csv(ROW_EFFECTS, computed, row_fields)
    _write_csv(POOLED, pooled_rows, pooled_fields)
    _write_csv(VERDICTS, verdict_rows, verdict_fields)
    _write_csv(TAU_RANGES, tau_rows, ["option", "lo", "hi", "basis"])

    reason_counts = Counter(row["analysis_tier"] for row in computed)
    verdict_counts = Counter(row["verdict"] for row in verdict_rows)
    pooled_count = sum(_num(row["k"]) >= 3 for row in pooled_rows)
    imputed_count = sum(row["variance_status"] == "ASSUMED median group CV" for row in computed)
    mapping_changes = [
        (row["effect_id"], previous_mappings[row["effect_id"]] or "unclassified",
         row["outcome_family"] or "excluded/unclassified")
        for row in computed
        if row["effect_id"] in previous_mappings
        and previous_mappings[row["effect_id"]] != row["outcome_family"]
    ]

    with V1_VERDICTS.open(encoding="utf-8-sig", newline="") as handle:
        v1_rows = list(csv.DictReader(handle))
    key_fields = ("technology", "habitat", "outcome_family")
    v1_by_group = {tuple(row[field] for field in key_fields): row for row in v1_rows}
    f8b_by_group = {tuple(row[field] for field in key_fields): row for row in verdict_rows}
    before_counts = Counter(row["verdict"] for row in v1_rows)
    verdict_order = ("evidence of benefit", "evidence of harm", "no clear difference", "no evidence")
    before_after_lines = ["| Verdict | F8 | F8b |", "|---|---:|---:|"]
    before_after_lines.extend(
        f"| {label} | {before_counts[label]} | {verdict_counts[label]} |"
        for label in verdict_order
    )
    changed_groups = []
    for key in sorted(set(v1_by_group) | set(f8b_by_group)):
        before = v1_by_group.get(key, {}).get("verdict", "group absent")
        after = f8b_by_group.get(key, {}).get("verdict", "group removed")
        if before != after:
            changed_groups.append((key, before, after))
    changed_lines = ["| Technology | Habitat | Outcome | F8 | F8b |", "|---|---|---|---|---|"]
    changed_lines.extend(
        f"| {key[0]} | {key[1]} | {key[2]} | {before} | {after} |"
        for key, before, after in changed_groups
    )

    crosscheck_groups = [
        row for row in pooled_rows
        if row["habitat"] == "marsh"
        and row["technology"] in {"manual_removal", "mechanical_removal", "planting"}
        and row["outcome_family"] in {"biological recovery", "erosion"}
        and _num(row["k"]) >= 3
    ]
    if crosscheck_groups:
        crosscheck = "Matching pooled marsh coefficient(s) existed, but held-data comparison requires an exact common ratio endpoint; none was common without refitting. Agreement not classified."
    else:
        crosscheck = "No pooled marsh manual_removal, mechanical_removal, or planting biological-recovery/erosion coefficient exists. The requested Zengel/held-data agreement cross-check is therefore not testable without refitting; no agreement was claimed."

    summary_lines = [
        "F8b LITERATURE POOLING SUMMARY (DEFECT-FIX RERUN)",
        "Evidence: LITERATURE (AI-extracted; Jaison accepted 14 Nov 2026).",
        "F8 verdict and pooled tables are preserved in results/f8_pooling/v1/.",
        "Effect scale: benefit-oriented lnRR; positive = benefit, zero = no effect, negative = harm.",
        "",
        f"Input rows processed: {len(computed)} (source-index rows read for provenance: {len(source_index_rows)}).",
        f"Row tiers: {dict(sorted(reason_counts.items()))}.",
        f"Observed technology-habitat-outcome groups: {len(pooled_rows)}.",
        f"Primary pooled groups (>=3 independent variance-complete studies): {pooled_count}.",
        f"Forest plots written: {len(plot_paths)}.",
        f"ASSUMED median-CV variance imputations (sensitivity only): {imputed_count}.",
        f"Verdicts: {dict(sorted(verdict_counts.items()))}.",
        f"Marsh vegetation tau-multiplier ranges: {len(tau_rows)}.",
        "",
        "BEFORE/AFTER VERDICT COUNTS",
        *before_after_lines,
        "",
        "CHANGED GROUP VERDICTS",
        *changed_lines,
        "",
        "OUTCOME-MAPPING CHANGES",
        *([f"- {effect_id}: {before} -> {after}" for effect_id, before, after in mapping_changes]
          or ["- None."]),
        "",
        "Verdict gate: pooled groups use the 95% prediction interval. Unpooled groups evaluate each grade A/B independent study CI; one unopposed direction gives benefit/harm and conflicting directions give no clear difference. Sensitivity cannot upgrade verdicts.",
        "Multiple rows from one study/group were collapsed after selecting the latest time <=730 days; longest-time estimates are supplementary columns.",
        "Rate-constant effects without variance remain listings; their exp(lnRR) ratios are reported in evidence_verdicts.csv notes.",
        "",
        "ZENGEL / HELD-DATA CROSS-CHECK (NO REFITTING)",
        crosscheck,
        "",
        "ASSUMPTIONS AND LIMITATIONS",
        "- Missing variance is excluded from primary pooling; median group-CV imputation is ASSUMED and sensitivity-only.",
        "- C011 is excluded as a Fowler Beach physical-balance covariate, not treated as shoreline erosion or an oil-response coefficient.",
        "- Vegetation tau mapping is ASSUMED as exp(pooled PI) or exp(a single grade A/B study CI); missing CI yields no range.",
        "- No checked_by or source extraction field was modified.",
    ]
    SUMMARY.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
