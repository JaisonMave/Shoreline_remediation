"""F5 uncertainty for the shoreline transport engine. Plan: docs/F5_PROCESS_MODEL_PLAN.md.

Step 2 and step 3 each run once from main(). A smoke call does not write the gated files.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm, qmc

from .data_model import Scenario
from .shoreline_transport import simulate_transect

ROOT = Path(__file__).resolve().parents[2]
PRIORS_PATH = ROOT / "data" / "knowledge" / "process_parameter_priors.csv"
PAH_CELLS = ROOT / "results" / "pah_decline" / "station_campaign.csv"
PAH_CLASS = ROOT / "results" / "pah_decline" / "by_oiling_class.csv"
OUT_DIR = ROOT / "results" / "f5_process"
CARD_PATH = ROOT / "models" / "process_model_v2.json"

SEED = 20261114
N_SALTELLI = 128
N_MC = 400
N_BOOT = 200
N_IMPORTANCE = 1500
N_FOLDS = 5
SIGMA = 0.75  # ASSUMED sd of log relative PAH; not fitted
HORIZON_DAYS = (365, 730)
GRID_DAYS = list(range(0, 1461, 30))
FRACTION_FLOOR = 1e-4


def load_priors(path: Path = PRIORS_PATH) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["sampled_in_sobol"] = frame["sampled_in_sobol"].str.lower().eq("yes")
    return frame


def _unit_to_value(row: pd.Series, unit: np.ndarray) -> np.ndarray:
    u = np.clip(np.asarray(unit, float), 1e-8, 1.0 - 1e-8)
    if row.distribution == "uniform":
        value = row.low + u * (row.high - row.low)
    elif row.distribution == "lognormal":
        value = np.exp(np.log(row["median"]) + row.sigma_ln * norm.ppf(u))
    elif row.distribution == "normal":
        value = row["median"] + row["sigma"] * norm.ppf(u)
    else:
        value = np.full(u.shape, row["median"])
    return np.clip(value, row.low, row.high)


def saltelli_units(n: int, k: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """A and B from one scrambled Sobol sequence of dimension 2k. n must be a power of two."""
    sampler = qmc.Sobol(d=2 * k, scramble=True, seed=seed)
    draw = sampler.random(n)
    return draw[:, :k], draw[:, k:]


def sobol_indices(y_a: np.ndarray, y_b: np.ndarray, y_ab: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Saltelli et al. (2010) first-order and Jansen (1999) total-order indices.

    y_a, y_b: (n,). y_ab: (k, n), AB_i = A with column i taken from B.
    Variance is the pooled sample variance of f(A) and f(B).
    """
    var = float(np.var(np.concatenate([y_a, y_b]), ddof=1))
    if var <= 0.0:
        raise ValueError("Sobol variance is zero")
    s1 = np.mean(y_b * (y_ab - y_a), axis=1) / var
    st = np.mean((y_a - y_ab) ** 2, axis=1) / (2.0 * var)
    return s1, st


def bootstrap_indices(y_a, y_b, y_ab, n_boot: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    n = len(y_a)
    s1 = np.empty((n_boot, y_ab.shape[0]))
    st = np.empty_like(s1)
    for b in range(n_boot):
        take = rng.integers(0, n, n)
        s1[b], st[b] = sobol_indices(y_a[take], y_b[take], y_ab[:, take])
    lo, hi = 0.05, 0.95
    return np.quantile(s1, [lo, hi], axis=0), np.quantile(st, [lo, hi], axis=0)


def marsh_case(oil_class: str) -> tuple[Scenario, float]:
    """Heavy matches the step-2 case. Moderate differs only by coverage and thickness (plan)."""
    if oil_class == "heavy":
        coverage, thickness = 80.0, 25.0
    elif oil_class == "moderate":
        coverage, thickness = 40.0, 10.0
    else:
        raise ValueError(oil_class)
    scenario = Scenario(
        "marsh", oil_category="heavy", oil_coverage=coverage, oil_thickness=thickness,
        wave_exposure="low", tidal_range="low", temperature_c=22.0, substrate_permeability="low",
    )
    return scenario, thickness


def _call(oil_class: str, days: list[int], overrides: dict, oil_thickness: float | None,
          penetration_depth_cm: float | None) -> pd.DataFrame:
    scenario, default_thickness = marsh_case(oil_class)
    return simulate_transect(
        scenario, "no_cleanup", days,
        oil_thickness=default_thickness if oil_thickness is None else oil_thickness,
        penetration_depth_cm=2.0 if penetration_depth_cm is None else penetration_depth_cm,
        parameter_overrides=overrides or None,
    )


def surface_fraction(frame: pd.DataFrame, day: int) -> float:
    initial = float(frame.loc[frame.survey_day == 0, "residual_oil_kg"].iloc[0])
    row = frame.loc[frame.survey_day == day].iloc[0]
    return float(row.surface_oil_mass_kg) / initial


def total_fraction_grid(frame: pd.DataFrame) -> np.ndarray:
    initial = float(frame.loc[frame.survey_day == 0, "residual_oil_kg"].iloc[0])
    return np.clip(frame["residual_oil_kg"].to_numpy(float) / initial, FRACTION_FLOOR, None)


def split_draw(sampled: pd.DataFrame, values: np.ndarray) -> tuple[dict, float | None, float | None]:
    overrides: dict = {}
    thickness = None
    penetration = None
    for value, key in zip(values, sampled.override_key):
        if key == "oil_thickness":
            thickness = float(value)
        elif key == "penetration_depth_cm":
            penetration = float(value)
        else:
            overrides[str(key)] = float(value)
    return overrides, thickness, penetration


def evaluate_surface(sampled: pd.DataFrame, values: np.ndarray, day: int) -> float:
    overrides, thickness, penetration = split_draw(sampled, values)
    frame = _call("heavy", [0, day], overrides, thickness, penetration)
    return surface_fraction(frame, day)


def run_sensitivity(priors: pd.DataFrame, n: int = N_SALTELLI, seed: int = SEED) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    sampled = priors[priors.sampled_in_sobol].reset_index(drop=True)
    k = len(sampled)
    a_u, b_u = saltelli_units(n, k, seed)
    a = np.column_stack([_unit_to_value(sampled.iloc[i], a_u[:, i]) for i in range(k)])
    b = np.column_stack([_unit_to_value(sampled.iloc[i], b_u[:, i]) for i in range(k)])
    matrices = {"A": a, "B": b}
    for i in range(k):
        ab = a.copy()
        ab[:, i] = b[:, i]
        matrices[f"AB{i}"] = ab

    outputs = {name: {} for name in HORIZON_DAYS}
    total = 0
    for label, matrix in matrices.items():
        for row in range(n):
            total += 1
            frame = _call("heavy", [0, *HORIZON_DAYS], *split_draw(sampled, matrix[row]))
            for day in HORIZON_DAYS:
                outputs[day].setdefault(label, []).append(surface_fraction(frame, day))
            if total % 256 == 0:
                print(f"sensitivity {total} evaluations", flush=True)

    rows = []
    for day in HORIZON_DAYS:
        y_a = np.asarray(outputs[day]["A"], float)
        y_b = np.asarray(outputs[day]["B"], float)
        y_ab = np.vstack([np.asarray(outputs[day][f"AB{i}"], float) for i in range(k)])
        # A failed row is replaced by the finite median of A so the Saltelli matrices stay complete.
        fill = np.nanmedian(y_a)
        for block in (y_a, y_b, y_ab):
            block[np.isnan(block)] = fill
        s1, st = sobol_indices(y_a, y_b, y_ab)
        (s1_lo, s1_hi), (st_lo, st_hi) = bootstrap_indices(y_a, y_b, y_ab, N_BOOT, seed)
        for i, row in sampled.iterrows():
            rows.append({
                "output": f"surface_fraction_day_{day}", "parameter_id": row.parameter_id,
                "calibration_group": row.calibration_group, "S1": s1[i], "ST": st[i],
                "S1_lo90": s1_lo[i], "S1_hi90": s1_hi[i], "ST_lo90": st_lo[i], "ST_hi90": st_hi[i],
            })
    sobol = pd.DataFrame(rows)
    rank = (sobol[sobol.calibration_group == "rate"].groupby("parameter_id").ST.mean()
            .sort_values(ascending=False))
    chosen = list(rank.index[:4] if len(rank) >= 4 and rank.iloc[3] >= 0.05 else rank.index[:3])
    return sobol, sampled, chosen


def run_monte_carlo(priors: pd.DataFrame, n: int = N_MC, seed: int = SEED + 1) -> pd.DataFrame:
    sampled = priors[priors.sampled_in_sobol].reset_index(drop=True)
    rng = np.random.default_rng(seed)
    unit = rng.random((n, len(sampled)))
    values = np.column_stack([_unit_to_value(sampled.iloc[i], unit[:, i]) for i in range(len(sampled))])
    store = {day: [] for day in HORIZON_DAYS}
    mass = {day: [] for day in HORIZON_DAYS}
    for row in range(n):
        frame = _call("heavy", [0, *HORIZON_DAYS], *split_draw(sampled, values[row]))
        initial = float(frame.loc[frame.survey_day == 0, "residual_oil_kg"].iloc[0])
        for day in HORIZON_DAYS:
            store[day].append(surface_fraction(frame, day))
            mass[day].append(float(frame.loc[frame.survey_day == day, "surface_oil_mass_kg"].iloc[0]))
        if (row + 1) % 100 == 0:
            print(f"monte carlo {row + 1}", flush=True)
    rows = []
    for day in HORIZON_DAYS:
        for name, series in (("surface_fraction_of_initial", store[day]), ("surface_oil_kg", mass[day])):
            q = np.quantile(series, [0.05, 0.50, 0.95])
            rows.append({"output": name, "day": day, "p05": q[0], "p50": q[1], "p95": q[2],
                         "mean": float(np.mean(series)), "n": n})
    return pd.DataFrame(rows)


def load_targets() -> pd.DataFrame:
    cells = pd.read_csv(PAH_CELLS)
    cells = cells[cells.oil_class.isin(["heavy", "moderate"]) & (cells.pah_sum > 0)].copy()
    cells = cells.sort_values(["station", "depth_class", "t"])
    first = (cells.groupby(["station", "depth_class"], as_index=False).first()
             [["station", "depth_class", "t", "pah_sum"]]
             .rename(columns={"t": "t0", "pah_sum": "pah0"}))
    merged = cells.merge(first, on=["station", "depth_class"])
    merged = merged[merged.t > merged.t0].copy()
    merged["obs"] = np.log(merged.pah_sum / merged.pah0)
    return merged.reset_index(drop=True)


def empirical_k() -> dict[str, float]:
    table = pd.read_csv(PAH_CLASS)
    use = table[(table.outcome == "PAH sum") & (table.stratum_type == "oiling_class")]
    return {row.stratum: float(row.k_per_year) for _, row in use.iterrows() if row.stratum in ("heavy", "moderate")}


def station_folds(stations, n_folds: int = N_FOLDS, seed: int = SEED) -> dict:
    names = np.array(sorted(set(stations)))
    perm = np.random.default_rng(seed).permutation(len(names))
    return {names[i]: int(j % n_folds) for j, i in enumerate(perm)}


def _fraction_cache(draws: pd.DataFrame, oil_class: str) -> tuple[np.ndarray, np.ndarray]:
    grids = np.empty((len(draws), len(GRID_DAYS)))
    for i, row in enumerate(draws.itertuples(index=False)):
        overrides = {key: float(getattr(row, key)) for key in draws.columns}
        frame = _call(oil_class, GRID_DAYS, overrides, None, None)
        grids[i] = total_fraction_grid(frame)
        if (i + 1) % 250 == 0:
            print(f"trajectory {oil_class} {i + 1}", flush=True)
    return np.asarray(GRID_DAYS, float), grids


def log_relative(days: np.ndarray, grids: np.ndarray, t: np.ndarray, t0: np.ndarray) -> np.ndarray:
    day = np.asarray(t, float) * 365.25
    day0 = np.asarray(t0, float) * 365.25
    pred = np.empty((grids.shape[0], len(t)))
    for i in range(grids.shape[0]):
        pred[i] = np.log(np.interp(day, days, grids[i]) / np.interp(day0, days, grids[i]))
    return pred


def _station_loglik(pred: np.ndarray, obs: np.ndarray, codes: np.ndarray, mask: np.ndarray) -> np.ndarray:
    err = ((pred[:, mask] - obs[mask]) / SIGMA) ** 2
    use = codes[mask]
    ll = np.zeros(pred.shape[0])
    for code in np.unique(use):
        ll += -0.5 * err[:, use == code].mean(axis=1)
    return ll


def _weights(loglik: np.ndarray) -> np.ndarray:
    shifted = np.exp(loglik - np.max(loglik))
    return shifted / shifted.sum()


def _weighted_median(pred: np.ndarray, weights: np.ndarray) -> np.ndarray:
    out = np.empty(pred.shape[1])
    for j in range(pred.shape[1]):
        order = np.argsort(pred[:, j])
        cumulative = np.cumsum(weights[order])
        out[j] = pred[order[min(np.searchsorted(cumulative, 0.5), len(order) - 1)], j]
    return out


def _weighted_quantile(x: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(x)
    cumulative = np.cumsum(weights[order])
    cumulative /= cumulative[-1]
    return float(np.interp(q, cumulative, x[order]))


def run_calibration(priors: pd.DataFrame, influential: list[str], n: int = N_IMPORTANCE,
                    seed: int = SEED) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    rows = priors.set_index("parameter_id").loc[influential]
    rng = np.random.default_rng(seed)
    unit = rng.random((n, len(influential)))
    draws = pd.DataFrame({
        rows.iloc[i].override_key: _unit_to_value(rows.iloc[i], unit[:, i]) for i in range(len(influential))
    })
    targets = load_targets()
    folds = station_folds(targets.station, N_FOLDS, seed)
    targets = targets.assign(fold=targets.station.map(folds), code=pd.factorize(targets.station)[0])
    k_emp = empirical_k()
    days_h, grid_h = _fraction_cache(draws, "heavy")
    days_m, grid_m = _fraction_cache(draws, "moderate")
    pred = np.empty((n, len(targets)))
    heavy = targets.oil_class.eq("heavy").to_numpy()
    pred[:, heavy] = log_relative(days_h, grid_h, targets.loc[heavy, "t"], targets.loc[heavy, "t0"])
    pred[:, ~heavy] = log_relative(days_m, grid_m, targets.loc[~heavy, "t"], targets.loc[~heavy, "t0"])
    obs = targets.obs.to_numpy(float)
    codes = targets.code.to_numpy()
    prior_w = np.full(n, 1.0 / n)
    prior_pred = _weighted_median(pred, prior_w)
    emp_pred = -targets.oil_class.map(k_emp).to_numpy(float) * (targets.t - targets.t0).to_numpy(float)

    heldout_pred = np.empty(len(targets))
    for fold in range(N_FOLDS):
        train = (targets.fold != fold).to_numpy()
        test = ~train
        weights = _weights(_station_loglik(pred, obs, codes, train))
        heldout_pred[test] = _weighted_median(pred[:, test], weights)
        print(f"fold {fold} ess {1.0 / np.sum(weights ** 2):.1f}", flush=True)

    targets = targets.assign(pred_prior=prior_pred, pred_empirical=emp_pred, pred_calibrated=heldout_pred)
    targets["ae_prior"] = (targets.obs - targets.pred_prior).abs()
    targets["ae_empirical"] = (targets.obs - targets.pred_empirical).abs()
    targets["ae_calibrated"] = (targets.obs - targets.pred_calibrated).abs()
    by_station = (targets.groupby(["station", "oil_class", "fold"], as_index=False)
                  .agg(n_cells=("obs", "size"), MAE_prior=("ae_prior", "mean"),
                       MAE_empirical=("ae_empirical", "mean"), MAE_calibrated=("ae_calibrated", "mean")))

    full_w = _weights(_station_loglik(pred, obs, codes, np.ones(len(targets), dtype=bool)))
    posterior_rows = []
    for i, parameter_id in enumerate(influential):
        column = rows.iloc[i].override_key
        sample = draws[column].to_numpy(float)
        prior_q = np.quantile(sample, [0.05, 0.25, 0.50, 0.75, 0.95])
        post_q = [_weighted_quantile(sample, full_w, q) for q in (0.05, 0.25, 0.50, 0.75, 0.95)]
        width_prior = prior_q[4] - prior_q[0]
        width_post = post_q[4] - post_q[0]
        shrink = 1.0 - width_post / width_prior if width_prior > 0 else 0.0
        outside = post_q[2] < prior_q[1] or post_q[2] > prior_q[3]
        posterior_rows.append({
            "parameter_id": parameter_id, "override_key": column,
            "prior_p05": prior_q[0], "prior_p25": prior_q[1], "prior_p50": prior_q[2],
            "prior_p75": prior_q[3], "prior_p95": prior_q[4],
            "post_p05": post_q[0], "post_p25": post_q[1], "post_p50": post_q[2],
            "post_p75": post_q[3], "post_p95": post_q[4],
            "width90_prior": width_prior, "width90_post": width_post, "shrink": shrink,
            "median_outside_prior_50": bool(outside), "differs": bool(shrink >= 0.30 or outside),
        })
    posterior = pd.DataFrame(posterior_rows)
    summary = {
        "n_stations": int(by_station.station.nunique()),
        "n_cells": int(len(targets)),
        "mae_prior": float(by_station.MAE_prior.mean()),
        "mae_empirical": float(by_station.MAE_empirical.mean()),
        "mae_calibrated": float(by_station.MAE_calibrated.mean()),
        "ess_full": float(1.0 / np.sum(full_w ** 2)),
        "k_heavy": k_emp["heavy"],
        "k_moderate": k_emp["moderate"],
        "any_differs": bool(posterior["differs"].any()),
    }
    summary["beats_prior"] = summary["mae_calibrated"] < summary["mae_prior"]
    summary["beats_empirical"] = summary["mae_calibrated"] < summary["mae_empirical"]
    summary["gate_pass"] = bool(summary["beats_prior"] and summary["beats_empirical"] and summary["any_differs"])
    return by_station, posterior, summary


def _plots(sobol: pd.DataFrame, intervals: pd.DataFrame, cv: pd.DataFrame, posterior: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    mean_st = sobol.groupby("parameter_id").ST.mean().sort_values()
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(mean_st.index, mean_st.values, color="#4C78A8")
    ax.set_xlabel("Mean total-order index (1 year and 2 years)")
    ax.set_title("Marsh, heavy oil, no cleanup")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "sobol_total_order.png", dpi=120)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    use = intervals[intervals.output == "surface_fraction_of_initial"]
    ax.errorbar(use.day / 365.0, use.p50, yerr=[use.p50 - use.p05, use.p95 - use.p50], fmt="o", color="#4C78A8",
                capsize=4)
    ax.set_xlabel("Years")
    ax.set_ylabel("Surface oil / initial oil")
    ax.set_title("Prior predictive interval (5th, 50th, 95th)")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "mc_intervals.png", dpi=120)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    y = np.arange(len(posterior))
    ax.hlines(y, posterior.prior_p05, posterior.prior_p95, color="#B0B0B0", linewidth=6, label="Prior 90%")
    ax.hlines(y, posterior.post_p05, posterior.post_p95, color="#E45756", linewidth=2, label="Posterior 90%")
    ax.plot(posterior.post_p50, y, "o", color="#E45756")
    ax.set_yticks(y)
    ax.set_yticklabels(posterior.parameter_id)
    ax.set_xlabel("Parameter value")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "posterior_vs_prior.png", dpi=120)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.boxplot([cv.MAE_prior, cv.MAE_empirical, cv.MAE_calibrated])
    ax.set_xticklabels(["Prior", "Empirical k", "Calibrated"])
    ax.set_ylabel("Station MAE of log relative PAH")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "calibration_mae.png", dpi=120)
    plt.close(fig)


def write_card(influential: list[str], summary: dict) -> None:
    passed = summary["gate_pass"]
    card = {
        "name": "process-model-v2",
        "model_id": "process_model_v2",
        "status": "validated" if passed else "experimental",
        "label": "calibrated" if passed else "illustrative",
        "decision_path": passed,
        "built": "2026-11-14",
        "plan": "docs/F5_PROCESS_MODEL_PLAN.md",
        "engine": "adr_shoreline_transport_v1_1",
        "scenario": "marsh, heavy oil category, no_cleanup; moderate differs by coverage 40% and thickness 10 mm",
        "influential_parameters": influential,
        "gate": summary,
        "limits": (
            "Soil PAH is mostly physical loss (FINDINGS section 22). The engine has no erosion term. "
            "Calibration updates only the influential rate coefficients and does not identify cleanup, "
            "which is unrecorded at these stations. Not wired into the dashboard."
        ),
    }
    if not passed:
        card["decision_path_statement"] = (
            "Gate failed. This process model is illustrative and must not enter the decision path."
        )
    CARD_PATH.write_text(json.dumps(card, indent=2) + "\n")


def write_summary(intervals: pd.DataFrame, sobol: pd.DataFrame, influential: list[str], summary: dict) -> None:
    lines = ["F5 process model, run once. Plan: docs/F5_PROCESS_MODEL_PLAN.md.", ""]
    lines.append("Step 2. Residual surface oil / initial oil, marsh heavy no_cleanup, 400 prior draws.")
    use = intervals[intervals.output == "surface_fraction_of_initial"]
    for _, row in use.iterrows():
        lines.append(f"  day {int(row.day)}: p05 {row.p05:.4f}, p50 {row.p50:.4f}, p95 {row.p95:.4f}")
    lines.append("Influential rate coefficients (mean total-order index):")
    mean_st = sobol.groupby("parameter_id").ST.mean()
    for name in influential:
        lines.append(f"  {name}: {mean_st[name]:.3f}")
    scenario = sobol[sobol.calibration_group == "scenario"].groupby("parameter_id").ST.mean()
    if len(scenario) and scenario.max() > mean_st[influential[0]]:
        lines.append(f"Scenario input with a higher total-order index than every calibrated rate: {scenario.idxmax()} ({scenario.max():.3f}). Not calibrated.")
    lines.append("")
    lines.append("Step 3. Held-out station MAE on log relative PAH (heavy and moderate).")
    lines.append(f"  stations {summary['n_stations']}, cells {summary['n_cells']}")
    lines.append(f"  prior {summary['mae_prior']:.4f}")
    lines.append(f"  empirical k {summary['mae_empirical']:.4f} (heavy {summary['k_heavy']:.5f}/yr, moderate {summary['k_moderate']:.5f}/yr)")
    lines.append(f"  calibrated {summary['mae_calibrated']:.4f}")
    lines.append(f"  beats prior: {summary['beats_prior']}; beats empirical: {summary['beats_empirical']}; posterior differs: {summary['any_differs']}")
    lines.append(f"  full-data effective sample size: {summary['ess_full']:.1f}")
    if summary["gate_pass"]:
        lines.append("GATE: PASS. Status validated. Eligible for the decision path; not wired into the dashboard by this task.")
    else:
        lines.append("GATE: FAIL. The process model is illustrative and must not enter the decision path.")
    (OUT_DIR / "summary.txt").write_text("\n".join(lines) + "\n")


def main() -> None:
    if (OUT_DIR / "summary.txt").exists():
        raise SystemExit("results/f5_process/summary.txt already exists; the gated run is not repeated.")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    priors = load_priors()
    print("step 2 sensitivity", flush=True)
    sobol, _, influential = run_sensitivity(priors)
    sobol.to_csv(OUT_DIR / "sobol.csv", index=False)
    print("influential", influential, flush=True)
    print("step 2 monte carlo", flush=True)
    intervals = run_monte_carlo(priors)
    intervals.to_csv(OUT_DIR / "mc_intervals.csv", index=False)
    print("step 3 calibration", flush=True)
    cv, posterior, summary = run_calibration(priors, influential)
    cv.to_csv(OUT_DIR / "calibration_cv.csv", index=False)
    posterior.to_csv(OUT_DIR / "posterior.csv", index=False)
    _plots(sobol, intervals, cv, posterior)
    write_card(influential, summary)
    write_summary(intervals, sobol, influential, summary)
    print((OUT_DIR / "summary.txt").read_text(), flush=True)


if __name__ == "__main__":
    main()
