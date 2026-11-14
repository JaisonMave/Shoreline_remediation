from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "scenario_composer"
MODEL_JSON = ROOT / "models" / "oil_excess_d32.json"
SUMMARY = RESULTS / "summary_d32.txt"

HEAVY_BIAS_GATE = 0.25
NOO_WORSE_GATE = 0.10


def _f(v: float) -> str:
    return "nan" if not np.isfinite(v) else f"{v:+.3f}"


def main() -> None:
    pooled = pd.read_csv(RESULTS / "d32_pooled.csv").iloc[0]
    elig = pd.read_csv(RESULTS / "d32_eligibility.csv")

    c1b = pd.read_csv(RESULTS / "c1b_coverage.csv")
    c1c = pd.read_csv(RESULTS / "c1c_coverage.csv")
    c1b_p = c1b[c1b.basin == "pooled"].iloc[0]
    c1c_p = c1c[c1c.basin == "pooled"].iloc[0]

    noo_b = pd.read_csv(RESULTS / "c1b_noo_bias_cells.csv")
    noo_c = pd.read_csv(RESULTS / "c1c_noo_bias_cells.csv")
    c1b_noo = float((noo_b.median_clean - noo_b.observed_rate).mean())
    c1c_noo = float((noo_c.median_clean - noo_c.observed_rate).mean())
    c1_noo_worse = abs(c1c_noo) - abs(c1b_noo)

    b1b = pd.read_csv(RESULTS / "b1b_horizon_coverage.csv")
    b1c = pd.read_csv(RESULTS / "b1c_horizon_coverage.csv")
    b1b_cells = b1b[b1b.unit == "cells pooled"].iloc[0]
    b1c_cells = b1c[b1c.unit == "cells pooled"].iloc[0]
    b1b_heavy = b1b[b1b.unit == "cells, oiling Heavy"].iloc[0]
    b1c_heavy = b1c[b1c.unit == "cells, oiling Heavy"].iloc[0]
    b1b_noo = b1b[b1b.unit == "cells, oiling NOO"].iloc[0]
    b1c_noo = b1c[b1c.unit == "cells, oiling NOO"].iloc[0]
    b1_noo_worse = abs(float(b1c_noo.bias)) - abs(float(b1b_noo.bias))

    c1_pass = bool(c1c_p.passes_80_97) and bool(c1c_p.passes_heavy_bias) and (c1_noo_worse <= NOO_WORSE_GATE)
    b1_pass = bool(b1c_cells.passes_80_97) and (abs(float(b1c_heavy.bias)) <= HEAVY_BIAS_GATE) and (b1_noo_worse <= NOO_WORSE_GATE)
    all_gates = c1_pass and b1_pass

    heavy_improved = (abs(float(c1c_p.heavy_bias)) < abs(float(c1b_p.heavy_bias)) and
                      abs(float(b1c_heavy.bias)) < abs(float(b1b_heavy.bias)))
    adopt = all_gates or heavy_improved

    if not adopt and MODEL_JSON.exists():
        data = json.loads(MODEL_JSON.read_text())
        data["scale"] = 1.0
        data["pooled_sd_total"] = 0.0
        data["interval_inflation_90"] = 0.0
        data["decision"] = "revert_to_zengel"
        MODEL_JSON.write_text(json.dumps(data, indent=2))

    lines = [
        "D32 oil-excess scaling summary (run once).",
        "",
        "Eligibility table (study, included, excess, n):",
    ]
    for r in elig.itertuples():
        lines.append(f"  {r.study}: {r.included}, excess={r.excess_used_m_per_yr}, n={r.n_used}")

    lines += [
        "",
        f"Primary pooled E (field-size weighted): {float(pooled.E_field_size_weighted):.3f} m/yr, 90% range [{float(pooled.E90_lo):.3f}, {float(pooled.E90_hi):.3f}]",
        f"Scale s = E / Zengel(yrs1-5): {float(pooled.scale_s):.3f} (Zengel mean {float(pooled.zengel_mean_years_1_5):.3f})",
        f"DL sensitivity (if available): E={pooled.dl_E}, 90% [{pooled.dl_E90_lo}, {pooled.dl_E90_hi}]",
        f"LOSO range of E: [{float(pooled.loso_min):.3f}, {float(pooled.loso_max):.3f}]",
        "",
        "C1 comparison (pooled heavy cells):",
        f"  C1b coverage={float(c1b_p.coverage):.3f}, heavy_bias={_f(float(c1b_p.heavy_bias))}, NOO_bias={_f(c1b_noo)}",
        f"  C1c coverage={float(c1c_p.coverage):.3f}, heavy_bias={_f(float(c1c_p.heavy_bias))}, NOO_bias={_f(c1c_noo)}, NOO_worse_by={_f(c1_noo_worse)}",
        "",
        "B1 comparison (cells pooled + heavy/NOO bias):",
        f"  B1b coverage={float(b1b_cells.coverage):.3f}, heavy_bias={_f(float(b1b_heavy.bias))}, NOO_bias={_f(float(b1b_noo.bias))}",
        f"  B1c coverage={float(b1c_cells.coverage):.3f}, heavy_bias={_f(float(b1c_heavy.bias))}, NOO_bias={_f(float(b1c_noo.bias))}, NOO_worse_by={_f(b1_noo_worse)}",
        "",
        f"Decision: {'ADOPT scaled excess' if adopt else 'REVERT to Zengel default (scale set to 1.0 in models/oil_excess_d32.json)'}.",
        f"Rule check: all_gates_pass={all_gates}, heavy_bias_improved_vs_C1b_and_B1b={heavy_improved}",
    ]

    SUMMARY.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
