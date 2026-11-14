from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PART_E = ROOT / "data" / "knowledge" / "literature_effects" / "part_E_marsh_erosion.csv"
SOURCES_E = ROOT / "data" / "knowledge" / "literature_effects" / "sources_E_marsh_erosion.csv"
P3_A = ROOT / "results" / "p3_treatment" / "A_prespill_adjusted.csv"
RESULTS = ROOT / "results" / "scenario_composer"
ELIG_OUT = RESULTS / "d32_eligibility.csv"
POOLED_OUT = RESULTS / "d32_pooled.csv"
MODEL_OUT = ROOT / "models" / "oil_excess_d32.json"
Z90 = 1.6448536269514722


def _study_id(citation: str) -> str:
    c = str(citation)
    if "Zengel" in c:
        return "zengel_2015_2022"
    if "Challenger" in c:
        return "challenger_2021"
    if "Turner" in c and "Islands in the oil" in c:
        return "turner_2016"
    if "McClenachan" in c:
        return "mcclenachan_2013"
    if "Silliman" in c and "(2012" in c:
        return "silliman_2012"
    if "Silliman" in c and "(2016" in c:
        return "silliman_2016"
    if "Deis" in c and "(2019" in c:
        return "deis_2019"
    if "Beland" in c and "(2017" in c:
        return "beland_2017"
    return "other"


STUDY_LABELS = {
    "silliman_2012": "Silliman et al. (2012)",
    "mcclenachan_2013": "McClenachan et al. (2013)",
    "turner_2016": "Turner et al. (2016)",
    "zengel_2015_2022": "Zengel et al. (2015 + 2022, one study)",
    "challenger_2021": "Challenger et al. (2021)",
    "silliman_2016": "Silliman et al. (2016)",
    "deis_2019": "Deis et al. (2019)",
    "beland_2017": "Beland et al. (2017)",
}

SOURCE_ID = {
    "silliman_2012": "E-S01",
    "mcclenachan_2013": "E-S02",
    "turner_2016": "E-S03",
    "zengel_2015_2022": "E-S05",
    "challenger_2021": "E-S06",
    "silliman_2016": "E-S07",
    "deis_2019": "E-S08",
    "beland_2017": "E-S09",
}


def _num(x):
    try:
        v = float(x)
        return v if np.isfinite(v) else np.nan
    except Exception:
        return np.nan


def _n_used(row: pd.Series) -> float:
    nt, nc = _num(row.get("n_treated")), _num(row.get("n_control"))
    if np.isfinite(nt) and np.isfinite(nc):
        return nt + nc
    if np.isfinite(nt):
        return nt
    if np.isfinite(nc):
        return nc
    return np.nan


def _se_from_interval(lo: float, hi: float) -> float:
    if np.isfinite(lo) and np.isfinite(hi) and hi > lo:
        return (hi - lo) / (2 * Z90)
    return np.nan


def _period_years(days: float) -> float:
    d = _num(days)
    if not np.isfinite(d):
        return np.nan
    return d / 365.0


def _choose_study_row(study: str, g: pd.DataFrame) -> dict:
    g = g.copy()
    g["effect_num"] = pd.to_numeric(g["reported_effect"], errors="coerce")
    g["n_used"] = g.apply(_n_used, axis=1)
    g["years"] = g["time_since_treatment_days"].apply(_period_years)
    g["remote_sensing"] = g["design"].fillna("").str.contains("remote sensing", case=False)

    if study == "zengel_2015_2022":
        z = g[g.effect_id.isin(["E005", "E006"])].copy()
        if len(z) == 2 and z["effect_num"].notna().all() and z["n_used"].notna().all():
            e1 = float(z.loc[z.effect_id == "E005", "effect_num"].iloc[0])
            e2 = float(z.loc[z.effect_id == "E006", "effect_num"].iloc[0])
            n = float(z.loc[z.effect_id == "E005", "n_used"].iloc[0])
            lo1 = _num(z.loc[z.effect_id == "E005", "reported_effect_lo"].iloc[0])
            hi1 = _num(z.loc[z.effect_id == "E005", "reported_effect_hi"].iloc[0])
            lo2 = _num(z.loc[z.effect_id == "E006", "reported_effect_lo"].iloc[0])
            hi2 = _num(z.loc[z.effect_id == "E006", "reported_effect_hi"].iloc[0])
            se = (2 / 5) * _se_from_interval(lo1, hi1) + (3 / 5) * _se_from_interval(lo2, hi2)
            eff = (2 * e1 + 3 * e2) / 5
            return {
                "included": True,
                "reason": "Included: Zengel 2015+2022 treated as one study; 2022 periods averaged for years 1-5.",
                "excess_used": eff,
                "n_used": n,
                "unit": "plots",
                "grade": "B",
                "remote_sensing": True,
                "arithmetic": f"(2*{e1:.2f} + 3*{e2:.2f})/5 = {eff:.3f}",
                "se_used": se,
            }
        return {"included": False, "reason": "Excluded: missing numeric Zengel 2022 period values.", "excess_used": np.nan,
                "n_used": np.nan, "unit": "", "grade": "", "remote_sensing": True, "arithmetic": "", "se_used": np.nan}

    if study == "challenger_2021":
        c = g[g["treatment_detail"].fillna("").str.contains("Heavy vs NOO")].copy()
        c = c[c["effect_num"].notna() & c["n_used"].notna()]
        c = c.sort_values("years")
        if len(c):
            row = c.iloc[-1]
            return {
                "included": True,
                "reason": "Included: period covering years 1-5 (Heavy vs NOO, Fall 2011-Summer 2015).",
                "excess_used": float(row["effect_num"]),
                "n_used": float(row["n_used"]),
                "unit": "sites",
                "grade": str(row.get("grade", "")),
                "remote_sensing": bool(row["remote_sensing"]),
                "arithmetic": f"Selected {row['effect_id']} as closest years 1-5 period.",
                "se_used": _se_from_interval(_num(row.get("reported_effect_lo")), _num(row.get("reported_effect_hi"))),
            }
        return {"included": False, "reason": "Excluded: no numeric Heavy-vs-reference contrast with unit count.", "excess_used": np.nan,
                "n_used": np.nan, "unit": "", "grade": "", "remote_sensing": False, "arithmetic": "", "se_used": np.nan}

    if study == "deis_2019":
        d = g[g["effect_num"].notna() & g["n_used"].notna()].copy()
        d = d[~d["treatment_detail"].fillna("").str.contains("Before-after", case=False)]
        if len(d):
            row = d.iloc[0]
            return {
                "included": True,
                "reason": "Included: heavy-oiled vs reference contrast with reported station counts.",
                "excess_used": float(row["effect_num"]),
                "n_used": float(row["n_used"]),
                "unit": "stations",
                "grade": str(row.get("grade", "")),
                "remote_sensing": bool(row["remote_sensing"]),
                "arithmetic": f"Selected {row['effect_id']} (oiled vs reference).",
                "se_used": _se_from_interval(_num(row.get("reported_effect_lo")), _num(row.get("reported_effect_hi"))),
            }
        return {"included": False, "reason": "Excluded: only before-after within-oiled contrast (no reference).", "excess_used": np.nan,
                "n_used": np.nan, "unit": "", "grade": "", "remote_sensing": True, "arithmetic": "", "se_used": np.nan}

    usable = g[g["effect_num"].notna() & g["n_used"].notna()].copy()
    if not len(usable):
        reason = "Excluded: no numeric effect and/or no reported unit count."
        return {"included": False, "reason": reason, "excess_used": np.nan, "n_used": np.nan, "unit": "", "grade": "",
                "remote_sensing": bool(g["remote_sensing"].any()), "arithmetic": "", "se_used": np.nan}

    if study == "beland_2017":
        return {"included": False, "reason": "Excluded: unit count for oiled group not reported (cannot define independent units).",
                "excess_used": np.nan, "n_used": np.nan, "unit": "", "grade": str(usable.iloc[0].get("grade", "")),
                "remote_sensing": True, "arithmetic": "", "se_used": np.nan}

    if study == "silliman_2012":
        return {"included": False, "reason": "Excluded: text-only non-numeric difference.", "excess_used": np.nan,
                "n_used": float(usable.iloc[0]["n_used"]), "unit": "sites", "grade": str(usable.iloc[0].get("grade", "")),
                "remote_sensing": False, "arithmetic": "", "se_used": np.nan}

    if study == "silliman_2016":
        return {"included": False, "reason": "Excluded: numeric contrast but no class-specific unit count.", "excess_used": np.nan,
                "n_used": np.nan, "unit": "sites", "grade": str(g.iloc[0].get("grade", "")), "remote_sensing": False,
                "arithmetic": "", "se_used": np.nan}

    row = usable.sort_values("years").iloc[0]
    return {
        "included": True,
        "reason": "Included: numeric effect with reported unit count.",
        "excess_used": float(row["effect_num"]),
        "n_used": float(row["n_used"]),
        "unit": "sites" if study == "mcclenachan_2013" else "units",
        "grade": str(row.get("grade", "")),
        "remote_sensing": bool(row["remote_sensing"]),
        "arithmetic": f"Selected {row['effect_id']}.",
        "se_used": _se_from_interval(_num(row.get("reported_effect_lo")), _num(row.get("reported_effect_hi"))),
    }


def _zengel_mean_years_1_5() -> float:
    d = pd.read_csv(P3_A)
    d = d[d.contrast == "Oiled, untreated minus Reference (unoiled)"]
    e12 = float(d.loc[d["analysis"].str.startswith("A 2010-2012"), "difference"].iloc[0])
    e38 = float(d.loc[~d["analysis"].str.startswith("A 2010-2012"), "difference"].iloc[0])
    return (2 * e12 + 3 * e38) / 5


def _weighted_mean(excess: np.ndarray, n: np.ndarray) -> float:
    return float(np.sum(n * excess) / np.sum(n))


def _weighted_sd(excess: np.ndarray, n: np.ndarray, mean: float) -> float:
    return float(np.sqrt(np.sum(n * (excess - mean) ** 2) / np.sum(n)))


def _dl_random_effects(excess: np.ndarray, se: np.ndarray) -> tuple[float, float, float] | tuple[float, float, float]:
    vi = se ** 2
    wi = 1.0 / vi
    mu_fixed = float(np.sum(wi * excess) / np.sum(wi))
    q = float(np.sum(wi * (excess - mu_fixed) ** 2))
    c = float(np.sum(wi) - (np.sum(wi ** 2) / np.sum(wi)))
    tau2 = max(0.0, (q - (len(excess) - 1)) / c) if c > 0 else 0.0
    w_star = 1.0 / (vi + tau2)
    mu = float(np.sum(w_star * excess) / np.sum(w_star))
    se_mu = float(np.sqrt(1.0 / np.sum(w_star)))
    half = Z90 * se_mu
    return mu, mu - half, mu + half


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(PART_E)
    df["study_id"] = df["citation"].apply(_study_id)
    df = df[df.study_id.isin(STUDY_LABELS)].copy()

    src = pd.read_csv(SOURCES_E)
    read_map = src.set_index("source_id")["read_level"].to_dict()

    rows = []
    for sid in STUDY_LABELS:
        g = df[df.study_id == sid]
        pick = _choose_study_row(sid, g)
        rows.append({
            "study": STUDY_LABELS[sid],
            "included": "yes" if pick["included"] else "no",
            "reason": pick["reason"],
            "excess_used_m_per_yr": pick["excess_used"],
            "n_used": pick["n_used"],
            "unit": pick["unit"],
            "grade": pick["grade"],
            "read_level": read_map.get(SOURCE_ID[sid], ""),
            "remote_sensing_flag": "yes" if pick["remote_sensing"] else "no",
            "period_arithmetic": pick["arithmetic"],
            "se_used": pick["se_used"],
        })

    elig = pd.DataFrame(rows)
    elig.to_csv(ELIG_OUT, index=False)

    inc = elig[elig.included == "yes"].copy()
    if len(inc) < 2:
        pooled = {
            "n_eligible_studies": int(len(inc)),
            "E_field_size_weighted": np.nan,
            "E90_lo": np.nan,
            "E90_hi": np.nan,
            "weighted_between_sd": np.nan,
            "mean_within_se": np.nan,
            "sd_total": np.nan,
            "dl_E": np.nan,
            "dl_E90_lo": np.nan,
            "dl_E90_hi": np.nan,
            "loso_min": np.nan,
            "loso_max": np.nan,
            "zengel_mean_years_1_5": _zengel_mean_years_1_5(),
            "scale_s": 1.0,
            "interval_inflation_90": 0.0,
            "note": "Fewer than 2 eligible studies; no scaling.",
        }
    else:
        x = inc["excess_used_m_per_yr"].to_numpy(float)
        n = inc["n_used"].to_numpy(float)
        E = _weighted_mean(x, n)
        sd_between = _weighted_sd(x, n, E)
        se = inc["se_used"].to_numpy(float)
        mean_within_se = float(np.nanmean(se)) if np.isfinite(se).any() else 0.0
        sd_total = float(np.sqrt(sd_between ** 2 + mean_within_se ** 2))
        half90 = Z90 * sd_total
        loso = []
        for i in range(len(inc)):
            xx = np.delete(x, i)
            nn = np.delete(n, i)
            if len(xx) >= 1 and np.sum(nn) > 0:
                loso.append(_weighted_mean(xx, nn))
        se_ok = np.isfinite(se) & (se > 0)
        if se_ok.sum() >= 3:
            dl_mu, dl_lo, dl_hi = _dl_random_effects(x[se_ok], se[se_ok])
        else:
            dl_mu, dl_lo, dl_hi = np.nan, np.nan, np.nan
        z_mean = _zengel_mean_years_1_5()
        scale = float(E / z_mean) if z_mean != 0 else 1.0
        pooled = {
            "n_eligible_studies": int(len(inc)),
            "E_field_size_weighted": E,
            "E90_lo": E - half90,
            "E90_hi": E + half90,
            "weighted_between_sd": sd_between,
            "mean_within_se": mean_within_se,
            "sd_total": sd_total,
            "dl_E": dl_mu,
            "dl_E90_lo": dl_lo,
            "dl_E90_hi": dl_hi,
            "loso_min": float(np.min(loso)) if len(loso) else np.nan,
            "loso_max": float(np.max(loso)) if len(loso) else np.nan,
            "zengel_mean_years_1_5": z_mean,
            "scale_s": scale,
            "interval_inflation_90": half90,
            "note": "DL not computed: fewer than 3 studies with SE." if not np.isfinite(dl_mu) else "",
        }

    pd.DataFrame([pooled]).to_csv(POOLED_OUT, index=False)

    model_payload = {
        "source": "validation/d32_oil_excess.py",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "n_eligible_studies": int(pooled["n_eligible_studies"]),
        "E_field_size_weighted": float(pooled["E_field_size_weighted"]) if np.isfinite(pooled["E_field_size_weighted"]) else None,
        "E90_lo": float(pooled["E90_lo"]) if np.isfinite(pooled["E90_lo"]) else None,
        "E90_hi": float(pooled["E90_hi"]) if np.isfinite(pooled["E90_hi"]) else None,
        "zengel_mean_years_1_5": float(pooled["zengel_mean_years_1_5"]),
        "scale": float(pooled["scale_s"]) if np.isfinite(pooled["scale_s"]) else 1.0,
        "pooled_sd_total": float(pooled["sd_total"]) if np.isfinite(pooled["sd_total"]) else 0.0,
        "interval_inflation_90": float(pooled["interval_inflation_90"]) if np.isfinite(pooled["interval_inflation_90"]) else 0.0,
    }
    MODEL_OUT.write_text(json.dumps(model_payload, indent=2))

    print(f"Wrote {ELIG_OUT}")
    print(f"Wrote {POOLED_OUT}")
    print(f"Wrote {MODEL_OUT}")


if __name__ == "__main__":
    main()
