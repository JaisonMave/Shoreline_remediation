"""P2: leave-one-basin-out prediction of marsh-edge loss (plan: docs/P2_BASIN_HOLDOUT_PLAN.md). Run once.

Run:  python -m validation.p2_basin_holdout data/external/p2
Each basin folder holds cells_10A.csv, cell_land_by_year.csv, exposure.csv, landsat_cell_fraction.csv.
Writes results/p2_basin_holdout/{per_basin.csv, pooled.csv, block_level.csv, oil_effect_transfer.csv,
predictions.csv, verdict.txt}
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.ensemble import HistGradientBoostingRegressor

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from validation.naip_edge_loss import CLASSES, cell_rates, fit  # noqa: E402

RESULTS = ROOT / "results" / "p2_basin_holdout"
# birdfoot excluded before the run: land rule fails in the river plume (plan amendment 1)
BASINS = ["terrebonne", "barataria", "breton"]
EXPOSURE = ["water_1km_2010", "water_250m_2010", "log_fetch", "pre_rate"]
OIL = [f"oil_{c}" for c in CLASSES[1:]]
MID_A, MID_B = 1999.55, 2008.55
MIN_HEAVY, MIN_CLEAN, MIN_BLOCK_CELLS = 30, 100, 5
AGREE = 0.4  # ASSUMED, plan amendment 4


def load_basin(d: Path, basin: str) -> pd.DataFrame:
    r = cell_rates(d, 2015)
    ex = pd.read_csv(d / "exposure.csv")
    ls = pd.read_csv(d / "landsat_cell_fraction.csv")
    ls = ls[ls.valid_fraction >= 0.9].pivot(index="cell", columns="epoch", values="land_fraction")
    ls["pre_rate"] = (ls["A"] - ls["B"]) * 100 / (MID_B - MID_A)
    r = r.merge(ex, on="cell").merge(ls[["pre_rate", "B"]], left_on="cell", right_index=True)
    # plan amendment 4: drop cells whose 2010 NAIP and 2007-2009 Landsat land fractions disagree by > 0.4
    n0 = len(r); r = r[(r.land_fraction_2010 - r["B"]).abs() <= AGREE]
    r.attrs["dropped_disagree"] = n0 - len(r)
    r["log_fetch"] = np.log(r.fetch_mean_m + 16)
    r["basin"] = basin
    return r


def design(d: pd.DataFrame, oil: bool) -> pd.DataFrame:
    X = d[EXPOSURE].astype(float).copy()
    if oil:
        for c in CLASSES[1:]:
            X[f"oil_{c}"] = (d.max_oiling.astype(str) == c).astype(float)
    return sm.add_constant(X, has_constant="add")


def fit_predict(train: pd.DataFrame, test: pd.DataFrame, model: str):
    if model == "M0":
        return np.full(len(test), train.rate.mean()), None
    if model in ("M1", "M2"):
        m = sm.OLS(train.rate.values, design(train, model == "M2")).fit()
        return m.predict(design(test, model == "M2")).values, m
    if model == "M3":
        X = design(train, True).drop(columns="const"); Xt = design(test, True).drop(columns="const")
        g = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
                                          min_samples_leaf=50, random_state=0).fit(X, train.rate)
        return g.predict(Xt), g
    raise ValueError(model)


def interval_offsets(train: pd.DataFrame) -> tuple[float, float]:
    """5th/95th percentile of M2 residuals from inner leave-one-basin-out among the training basins."""
    res = []
    for b in train.basin.unique():
        inner_tr, inner_te = train[train.basin != b], train[train.basin == b]
        p, _ = fit_predict(inner_tr, inner_te, "M2")
        res.append(inner_te.rate.values - p)
    res = np.concatenate(res)
    return float(np.quantile(res, 0.05)), float(np.quantile(res, 0.95))


def mae(y, p):
    return float(np.mean(np.abs(y - p)))


def eligible(d: pd.DataFrame) -> bool:
    return (d.max_oiling == "Heavy").sum() >= MIN_HEAVY and (d.max_oiling == "NOO").sum() >= MIN_CLEAN


def run(panel: pd.DataFrame) -> dict:
    per, preds, blocks, transfer = [], [], [], []
    for b in [x for x in BASINS if x in set(panel.basin)]:
        test = panel[panel.basin == b]; train = panel[panel.basin != b]
        if not eligible(test):
            per.append({"basin": b, "tested": False, "cells": len(test),
                        "heavy": int((test.max_oiling == "Heavy").sum()), "clean": int((test.max_oiling == "NOO").sum())})
            continue
        out = test[["cell", "basin", "cell_2km", "max_oiling", "rate"]].copy()
        models = {}
        for m in ("M0", "M1", "M2", "M3"):
            out[m], models[m] = fit_predict(train, test, m)
        lo, hi = interval_offsets(train)
        out["M2_lo"], out["M2_hi"] = out.M2 + lo, out.M2 + hi
        cover = float(((out.rate >= out.M2_lo) & (out.rate <= out.M2_hi)).mean())
        row = {"basin": b, "tested": True, "cells": len(test), "heavy": int((test.max_oiling == "Heavy").sum()),
               "clean": int((test.max_oiling == "NOO").sum()), "observed_mean": round(float(test.rate.mean()), 3)}
        for m in ("M0", "M1", "M2", "M3"):
            row[f"MAE_{m}"] = round(mae(out.rate, out[m]), 4)
            row[f"RMSE_{m}"] = round(float(np.sqrt(np.mean((out.rate - out[m]) ** 2))), 4)
        for m in ("M1", "M2", "M3"):
            row[f"skill_{m}"] = round(1 - row[f"MAE_{m}"] / row["MAE_M0"], 4)
        row["coverage_90"] = round(cover, 3)
        # block level
        g = out.groupby(["cell_2km", "max_oiling"], observed=True)
        bl = g.agg(n=("rate", "size"), obs=("rate", "mean"), M0=("M0", "mean"), M1=("M1", "mean"),
                   M2=("M2", "mean"), M3=("M3", "mean")).reset_index()
        bl = bl[bl.n >= MIN_BLOCK_CELLS].assign(basin=b)
        blocks.append(bl)
        for m in ("M0", "M1", "M2", "M3"):
            row[f"block_MAE_{m}"] = round(mae(bl.obs, bl[m]), 4)
        row["block_groups"] = len(bl)
        per.append(row)
        preds.append(out)
        # oil effect transfer: training M2 Heavy coefficient vs held-out within-block estimate
        m2 = models["M2"]
        held = fit(test.assign(max_oiling=pd.Categorical(test.max_oiling.astype(str), CLASSES)),
                   "rate ~ C(max_oiling, Treatment('NOO')) + water_1km_2010 + water_250m_2010 + log_fetch + C(cell_2km)")
        hk = "C(max_oiling, Treatment('NOO'))[T.Heavy]"; ci = held.conf_int(alpha=0.10).loc[hk]
        tci = m2.conf_int(alpha=0.10).loc["oil_Heavy"]
        transfer.append({"basin": b, "train_heavy_coef": round(float(m2.params["oil_Heavy"]), 3),
                         "train_lo": round(float(tci[0]), 3), "train_hi": round(float(tci[1]), 3),
                         "heldout_within_block": round(float(held.params[hk]), 3),
                         "heldout_lo": round(float(ci[0]), 3), "heldout_hi": round(float(ci[1]), 3)})
    per = pd.DataFrame(per); preds = pd.concat(preds) if preds else pd.DataFrame()
    pooled = {}
    if len(preds):
        for m in ("M0", "M1", "M2", "M3"):
            pooled[f"MAE_{m}"] = round(mae(preds.rate, preds[m]), 4)
        for m in ("M1", "M2", "M3"):
            pooled[f"skill_{m}"] = round(1 - pooled[f"MAE_{m}"] / pooled["MAE_M0"], 4)
        pooled["coverage_90"] = round(float(((preds.rate >= preds.M2_lo) & (preds.rate <= preds.M2_hi)).mean()), 3)
        pooled["cells"] = len(preds)
    return {"per_basin": per, "pooled": pooled, "predictions": preds,
            "blocks": pd.concat(blocks) if blocks else pd.DataFrame(), "transfer": pd.DataFrame(transfer)}


def judge(res: dict) -> str:
    per = res["per_basin"]; t = per[per.tested]; p = res["pooled"]
    if not len(t):
        return "No basin met the test thresholds."
    if p["MAE_M2"] >= p["MAE_M0"]:
        return "Does not transfer: M2 does not beat the no-predictor baseline pooled."
    wins = int((t.MAE_M2 < t.MAE_M0).sum()); need = min(3, len(t))
    cover_ok = bool(t.coverage_90.between(0.80, 0.95).all())
    oil_adds = p["MAE_M2"] < p["MAE_M1"]
    if wins >= need and cover_ok and oil_adds:
        return f"Transfers: M2 beats M0 in {wins} of {len(t)} basins and pooled; oiling adds value; coverage 80-95% everywhere."
    reasons = []
    if wins < need: reasons.append(f"M2 beats M0 in only {wins} of {len(t)} basins")
    if not cover_ok: reasons.append("coverage outside 80-95% in some basins")
    if not oil_adds: reasons.append("oiling does not improve on exposure alone (M2 vs M1 pooled)")
    return "Partly transfers: " + "; ".join(reasons) + "."


def main(p2_dir: str) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    parts = [load_basin(Path(p2_dir) / b, b) for b in BASINS if (Path(p2_dir) / b / "exposure.csv").exists()]
    for p in parts:
        print(p.basin.iloc[0], "cells kept:", len(p), "dropped by NAIP/Landsat disagreement:", p.attrs["dropped_disagree"])
    panel = pd.concat(parts)
    res = run(panel)
    verdict = judge(res)
    res["per_basin"].to_csv(RESULTS / "per_basin.csv", index=False)
    pd.DataFrame([res["pooled"]]).to_csv(RESULTS / "pooled.csv", index=False)
    res["blocks"].to_csv(RESULTS / "block_level.csv", index=False)
    res["transfer"].to_csv(RESULTS / "oil_effect_transfer.csv", index=False)
    res["predictions"].to_csv(RESULTS / "predictions.csv", index=False)
    (RESULTS / "verdict.txt").write_text(verdict + "\n")
    pd.set_option("display.width", 250)
    print(res["per_basin"].T.to_string()); print(); print("pooled:", res["pooled"]); print()
    print(res["transfer"].to_string(index=False)); print(); print("VERDICT:", verdict)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "data" / "external" / "p2"))
