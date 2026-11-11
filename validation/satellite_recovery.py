"""Estimate post-spill recovery from a satellite NDVI export and check it against the published finding.

Workflow:
  1. Digitise an oiled and a reference marsh polygon and run scripts/gee_export_ndvi.py. It writes
     ndvi_observations.csv (one row per image and site).
  2. Run:  python -m validation.satellite_recovery ndvi_observations.csv --spill-date 2010-04-20
     Add --persistent if the oiled edge may have eroded into open water.
  3. Results go to results/satellite/: the estimate, the placebo table, the monthly series and a figure.

--demo runs the same steps on a simulated series so the outputs can be inspected before real data exist.
Demo results are written to results/satellite/demo/ and must never be reported as findings.

Published benchmark for Barataria Bay, Deepwater Horizon (Mo, Kearney and Riter 2017, Remote Sensing 9(6):547,
https://www.mdpi.com/2072-4292/9/6/547): oiling significantly lowered Landsat NDVI in 2010 and 2011, and the
major aboveground impact lasted about two years. The check below asks only whether your estimate is
consistent with that; it is not a pass or fail test of the method.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.shoreline_remediation.recovery_timeseries import (  # noqa: E402
    fit_recovery, monthly_medians, placebo_test,
)

PUBLISHED_IMPACT_YEARS = 2.0  # Mo et al. 2017: major aboveground impact lasted about two years
RESULTS_DIR = ROOT / "results" / "satellite"


def simulated_observations(seed: int = 0) -> pd.DataFrame:
    """Per-image NDVI for two sites, 2003-2016, with a 0.15 drop that recovers with a 1-year time constant."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2003-01-05", "2016-12-20", freq="16D")
    t = dates.year + (dates.dayofyear - 1) / 365.25
    shared = 0.55 + 0.15 * np.sin(2 * np.pi * (t - 0.3)) + rng.normal(0, 0.03, len(t))
    spill = 2010 + 110 / 365.25
    impact = np.where(t >= spill, -0.15 * np.exp(-(t - spill) / 1.0), 0.0)
    clear = rng.random(len(t)) > 0.4
    rows = []
    for date, ref, oiled, ok in zip(dates, shared, shared - 0.03 + impact + rng.normal(0, 0.02, len(t)), clear):
        if ok:
            rows += [{"date": date, "site": "reference", "ndvi": ref, "pixels": 60},
                     {"date": date, "site": "oiled", "ndvi": oiled, "pixels": 45}]
    return pd.DataFrame(rows)


def benchmark_check(estimate) -> str:
    low, high = estimate.years_to_90pct_interval
    if estimate.drop_interval[0] <= 0:
        return "No clear impact: the 90% interval for the drop includes zero, so recovery time is not meaningful."
    if low <= PUBLISHED_IMPACT_YEARS <= high:
        return (f"Consistent with Mo et al. (2017): the 90% interval for 90% recovery ({low:.1f} to {high:.1f} years) "
                f"includes their ~{PUBLISHED_IMPACT_YEARS:.0f} years.")
    side = "longer" if low > PUBLISHED_IMPACT_YEARS else "shorter"
    return (f"Differs from Mo et al. (2017): recovery here is {side} ({low:.1f} to {high:.1f} years) than their "
            f"~{PUBLISHED_IMPACT_YEARS:.0f} years. Check the polygons and the reference site before interpreting this.")


def plot(monthly: pd.DataFrame, spill_date: str, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    difference = monthly["oiled"] - monthly["reference"]
    figure, axes = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    axes[0].plot(monthly["date"], monthly["reference"], color="#4C78A8", lw=1, label="Reference")
    axes[0].plot(monthly["date"], monthly["oiled"], color="#E45756", lw=1, label="Oiled")
    axes[0].set_ylabel("NDVI")
    axes[0].legend(frameon=False, loc="lower left")
    axes[1].plot(monthly["date"], difference, color="#333333", lw=1)
    axes[1].axhline(difference[monthly["date"] < spill_date].mean(), color="#999999", lw=0.8, ls="--")
    axes[1].set_ylabel("Oiled minus reference")
    for axis in axes:
        axis.axvline(pd.Timestamp(spill_date), color="#E45756", lw=0.8, ls=":")
        axis.spines[["top", "right"]].set_visible(False)
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def run(observations: pd.DataFrame, spill_date: str, persistent: bool, out_dir: Path, n_boot: int) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    monthly = monthly_medians(observations)
    estimate = fit_recovery(monthly, spill_date, n_boot=n_boot, persistent=persistent)
    placebos = placebo_test(monthly, spill_date)
    real = placebos.loc[placebos["kind"] == "real", "impact_2yr"].iloc[0]
    largest_placebo = placebos.loc[placebos["kind"] == "placebo", "impact_2yr"].abs().max()

    summary = {key: (list(value) if isinstance(value, tuple) else value) for key, value in asdict(estimate).items()}
    summary.update({
        "spill_date": spill_date,
        "persistent_model": persistent,
        "months_used": len(monthly),
        "real_impact_vs_largest_placebo": round(float(real / largest_placebo), 2) if largest_placebo else None,
        "placebo_check": "passed" if largest_placebo and real > 2 * largest_placebo else "failed: false spill dates find similar impacts",
        "benchmark_check": benchmark_check(estimate),
    })
    monthly.to_csv(out_dir / "monthly_series.csv", index=False)
    placebos.to_csv(out_dir / "placebo_test.csv", index=False)
    (out_dir / "estimate.json").write_text(json.dumps(summary, indent=2, default=float))
    plot(monthly, spill_date, out_dir / "recovery.png")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("observations", nargs="?", help="CSV from scripts/gee_export_ndvi.py")
    parser.add_argument("--spill-date", default="2010-04-20", help="date oil arrived or the spill began (YYYY-MM-DD)")
    parser.add_argument("--persistent", action="store_true", help="allow part of the impact to be permanent")
    parser.add_argument("--n-boot", type=int, default=300)
    parser.add_argument("--demo", action="store_true", help="run on a simulated series (not a finding)")
    args = parser.parse_args()
    if args.demo:
        observations, out_dir = simulated_observations(), RESULTS_DIR / "demo"
        print("DEMO: simulated data with a known 0.15 drop and 1-year time constant (2.3 years to 90% recovery).")
    elif args.observations:
        observations, out_dir = pd.read_csv(args.observations), RESULTS_DIR
    else:
        parser.error("give the observations CSV, or --demo")
    summary = run(observations, args.spill_date, args.persistent, out_dir, args.n_boot)
    for key in ["drop", "drop_interval", "years_to_90pct_recovery", "years_to_90pct_interval", "persistent_loss",
                "months_used", "placebo_check", "benchmark_check"]:
        value = summary[key]
        print(f"{key:26s} {np.round(value, 3) if isinstance(value, (float, list)) else value}")
    print(f"Wrote results to {out_dir}")


if __name__ == "__main__":
    main()
