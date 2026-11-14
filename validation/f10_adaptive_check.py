from __future__ import annotations

import sys
import warnings
import zlib
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

from src.shoreline_remediation import adaptive
from src.shoreline_remediation import scenario_composer as sc
from validation.scenario_composer_check import HELD_OUT

RESULTS = ROOT / "results" / "f10_adaptive"
NAIP = ROOT / "results" / "naip_edge_loss" / "cell_rates.csv"
SEED = 20261114
N_DRAWS = 4000
MIN_CELLS = 5
FRACTIONS = (0.10, 0.25, 0.50)
GATE = (0.80, 0.97)


def _rng(seed: int, *keys) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence([seed] + [zlib.crc32(str(k).encode()) for k in keys]))


def _sample_monitored(cells: pd.DataFrame, fraction: float, seed: int, *keys) -> pd.DataFrame:
    if len(cells) < 2:
        return cells.iloc[[]][["cell", "observed_rate"]].copy()
    n = int(round(fraction * len(cells)))
    n = max(1, min(len(cells) - 1, n))
    r = _rng(seed, "monitor", *keys)
    idx = np.sort(r.choice(np.arange(len(cells)), size=n, replace=False))
    return cells.iloc[idx][["cell", "observed_rate"]].copy()


def _metrics(df: pd.DataFrame, scenario: str, fraction: float, basin: str, group: str) -> dict:
    d = df if group == "all" else df[df.max_oiling == group]
    if d.empty:
        return {
            "scenario": scenario,
            "fraction": fraction,
            "basin": basin,
            "group": group,
            "n": 0,
            "prior_mae": np.nan,
            "updated_mae": np.nan,
            "mae_improved": np.nan,
            "prior_median_width": np.nan,
            "updated_median_width": np.nan,
            "width_narrowed": np.nan,
            "prior_coverage": np.nan,
            "updated_coverage": np.nan,
            "updated_coverage_pass": np.nan,
            "gate_pass_25": np.nan,
        }
    prior_mae = float(np.mean(np.abs(d.prior_median - d.observed_rate)))
    updated_mae = float(np.mean(np.abs(d.updated_median - d.observed_rate)))
    prior_width = float(np.median(d.prior_width))
    updated_width = float(np.median(d.updated_width))
    prior_cov = float(np.mean(d.prior_covered))
    updated_cov = float(np.mean(d.updated_covered))
    cov_pass = bool(GATE[0] <= updated_cov <= GATE[1])
    gate_pass = bool((updated_mae < prior_mae) and (updated_width < prior_width) and cov_pass) if abs(fraction - 0.25) < 1e-12 else np.nan
    return {
        "scenario": scenario,
        "fraction": fraction,
        "basin": basin,
        "group": group,
        "n": int(len(d)),
        "prior_mae": prior_mae,
        "updated_mae": updated_mae,
        "mae_improved": float(prior_mae - updated_mae),
        "prior_median_width": prior_width,
        "updated_median_width": updated_width,
        "width_narrowed": float(prior_width - updated_width),
        "prior_coverage": prior_cov,
        "updated_coverage": updated_cov,
        "updated_coverage_pass": cov_pass,
        "gate_pass_25": gate_pass,
    }


def run_primary(clean: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for basin in HELD_OUT:
        other = clean[clean.basin != basin]
        pools = sc.split_block_residuals(other.cell_2km, other.observed_rate - other.lobo_pred_clean)
        data = clean[clean.basin == basin]
        for block, g in data.groupby("cell_2km"):
            if len(g) < MIN_CELLS:
                continue
            block_cells = g[["cell", "max_oiling", "lobo_pred_clean", "observed_rate"]].rename(columns={"lobo_pred_clean": "pred_rate"}).copy()
            for frac in FRACTIONS:
                monitored = _sample_monitored(block_cells, frac, SEED, "primary", basin, block, frac)
                res = adaptive.update_block(block_cells, monitored, residual_pools=pools, horizon_years=5, n_draws=N_DRAWS,
                                            seed=SEED, observation_col="observed_rate")
                if res.empty:
                    continue
                res.insert(0, "scenario", "primary_2010_2015")
                res.insert(1, "fraction", frac)
                res.insert(2, "basin", basin)
                res.insert(3, "block", block)
                rows.append(res)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def run_time_update(clean: pd.DataFrame) -> pd.DataFrame:
    basin = "barataria"
    other = clean[clean.basin != basin]
    pools = sc.split_block_residuals(other.cell_2km, other.observed_rate - other.lobo_pred_clean)
    naip = pd.read_csv(NAIP, dtype={"cell": str})
    naip = naip[(naip.period == "2010-2017") & naip.rate.notna()]
    d = clean[clean.basin == basin][["cell", "cell_2km", "max_oiling", "lobo_pred_clean", "observed_rate"]].rename(
        columns={"lobo_pred_clean": "pred_rate", "observed_rate": "observed_rate_2010_2015"}
    )
    m = d.merge(naip[["cell", "rate"]].rename(columns={"rate": "observed_rate"}), on="cell", how="inner")
    rows = []
    for block, g in m.groupby("cell_2km"):
        if len(g) < MIN_CELLS:
            continue
        block_cells = g[["cell", "max_oiling", "pred_rate", "observed_rate"]].copy()
        monitor_base = g[["cell", "observed_rate_2010_2015"]].rename(columns={"observed_rate_2010_2015": "observed_rate"})
        for frac in FRACTIONS:
            monitored = _sample_monitored(monitor_base, frac, SEED, "time", basin, block, frac)
            res = adaptive.update_block(block_cells, monitored, residual_pools=pools, horizon_years=7, n_draws=N_DRAWS,
                                        seed=SEED, observation_col="observed_rate")
            if res.empty:
                continue
            res.insert(0, "scenario", "time_update_2010_2017")
            res.insert(1, "fraction", frac)
            res.insert(2, "basin", basin)
            res.insert(3, "block", block)
            rows.append(res)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def summarise(cell_results: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (scenario, frac), d in cell_results.groupby(["scenario", "fraction"]):
        for basin, b in d.groupby("basin"):
            for group in ("all", "Heavy", "NOO"):
                rows.append(_metrics(b, scenario, frac, basin, group))
        for group in ("all", "Heavy", "NOO"):
            rows.append(_metrics(d, scenario, frac, "pooled", group))
    return pd.DataFrame(rows)


def make_plot(summary: pd.DataFrame, out_path: Path) -> None:
    p = summary[(summary.basin == "pooled") & (summary.group == "all")].copy()
    if p.empty:
        return
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    for scenario, d in p.groupby("scenario"):
        d = d.sort_values("fraction")
        ax.plot(d.fraction, d.prior_median_width, marker="o", linestyle="--", label=f"{scenario} prior")
        ax.plot(d.fraction, d.updated_median_width, marker="o", linestyle="-", label=f"{scenario} updated")
    ax.set_xlabel("Monitored fraction in block")
    ax.set_ylabel("Median 90% interval width (m/yr)")
    ax.set_title("F10 adaptive monitoring: interval width vs monitoring fraction")
    ax.set_xticks([0.10, 0.25, 0.50])
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def write_summary(summary: pd.DataFrame, out_path: Path) -> None:
    lines = [
        "F10 adaptive monitoring (run once).",
        "Gate at 25% monitoring: updated MAE < prior MAE, updated median 90% width < prior, updated coverage in [0.80, 0.97].",
        "",
    ]
    for scenario in ("primary_2010_2015", "time_update_2010_2017"):
        lines.append(f"Scenario: {scenario}")
        d = summary[(summary.scenario == scenario) & (summary.fraction == 0.25)]
        if d.empty:
            lines.append("  No rows.")
            lines.append("")
            continue
        for r in d.sort_values(["basin", "group"]).itertuples():
            lines.append(
                f"  {r.basin:9s} {r.group:5s} n={r.n:4d} "
                f"MAE {r.prior_mae:.3f}->{r.updated_mae:.3f} "
                f"width {r.prior_median_width:.3f}->{r.updated_median_width:.3f} "
                f"coverage {r.updated_coverage:.3f} gate={r.gate_pass_25}"
            )
        lines.append("")

    lines.append("All fractions (pooled, Heavy and NOO):")
    for scenario in ("primary_2010_2015", "time_update_2010_2017"):
        d = summary[(summary.scenario == scenario) & (summary.basin == "pooled") & (summary.group.isin(["Heavy", "NOO"]))]
        lines.append(f"  {scenario}")
        for r in d.sort_values(["group", "fraction"]).itertuples():
            lines.append(
                f"    f={r.fraction:.2f} {r.group:5s} n={r.n:4d} "
                f"MAEΔ={r.mae_improved:+.3f} widthΔ={r.width_narrowed:+.3f} updated_cov={r.updated_coverage:.3f}"
            )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    clean = sc._baseline_lobo()
    clean = clean[clean.observed_rate.notna() & clean.lobo_pred_clean.notna()]

    primary = run_primary(clean)
    time_update = run_time_update(clean)
    cell_results = pd.concat([primary, time_update], ignore_index=True)
    cell_results.to_csv(RESULTS / "cell_results.csv", index=False)

    summary = summarise(cell_results)
    summary.to_csv(RESULTS / "coverage.csv", index=False)
    write_summary(summary, RESULTS / "summary.txt")
    make_plot(summary, RESULTS / "interval_width_vs_fraction.png")

    pooled = summary[(summary.fraction == 0.25) & (summary.basin == "pooled") & (summary.group == "all")]
    for r in pooled.itertuples():
        print(f"{r.scenario}: MAE {r.prior_mae:.3f}->{r.updated_mae:.3f}; width {r.prior_median_width:.3f}->{r.updated_median_width:.3f}; "
              f"coverage {r.updated_coverage:.3f}; gate={r.gate_pass_25}")


if __name__ == "__main__":
    main()
