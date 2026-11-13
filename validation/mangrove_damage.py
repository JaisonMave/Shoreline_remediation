"""Mangrove oiling-effect (damage-trajectory) model, plan section Phase C2. Run once.

Data   : results/galeta/galeta_site_year.csv (site-year means from NCEI 9400033, built by scripts/galeta_description.py).
Unit   : the site. Outcomes: share of roots recorded dead and leaves per shoot (primary); root oil cover (secondary).
Models : M0 unoiled-group mean per year; M1 mixed model value ~ oiled x C(year since spill), site random intercept.
Validation: leave one whole site out; error = MAE over the held-out site's years, averaged over sites; difference M1 - M0
         bootstrapped over sites (2,000, seed 20261112). 90% interval = 5th/95th percentile of pooled leave-one-site-out
         residuals (includes the held-out site's own residuals, as for A1); coverage reported.
Reading: as A1 (validated / suggestive / not usable). Year since spill = calendar year - 1986 (ASSUMED).
Run    : python -m validation.mangrove_damage
Writes : results/mangrove/{summary,loso_by_site,effect_by_year}.csv, summary.txt; models/mangrove_damage_v1.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.shoreline_remediation import mangrove_model as mm  # noqa: E402

DATA = ROOT / "results" / "galeta" / "galeta_site_year.csv"
RESULTS = ROOT / "results" / "mangrove"
MODEL_JSON = ROOT / "models" / "mangrove_damage_v1.json"
SCOPE = ("One spill (Bahia Las Minas, Panama, April 1986); Caribbean coast; red mangrove (Rhizophora mangle) fringe; "
         "years 1-5 after the spill only (calendar 1987-1991; leaves per shoot years 3-5 only); no treatment or cleanup "
         "variable and no pre-spill data, so this is the oiling effect (oiled minus unoiled sites), not a treatment effect "
         "or recovery after cleanup; oiled and unoiled sites were chosen by the investigators, not randomised; source licence unclear.")


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    summ, bysite, eff, txt, card_out = [], [], [], [], {}
    for outcome, label in mm.OUTCOMES.items():
        df = mm.load_site_year(DATA, outcome)
        R = mm.run_outcome(df)
        d = R["diff"]
        bysite.append(R["tab"].assign(outcome=outcome))
        eff.append(R["effects"].assign(outcome=outcome, n_oiled_sites=R["n_oiled"], n_unoiled_sites=R["n_unoiled"]))
        for k, v in (("study_averaged_MAE_M0", d["M0"]), ("study_averaged_MAE_M1", d["M1"])):
            summ.append({"outcome": outcome, "row": k, "estimate": v, "lo90": np.nan, "hi90": np.nan})
        summ.append({"outcome": outcome, "row": "MAE_M1_minus_M0", "estimate": d["diff"], "lo90": d["lo"], "hi90": d["hi"]})
        for m in ("M0", "M1"):
            summ.append({"outcome": outcome, "row": f"interval_coverage_{m}", "estimate": R["coverage"][m],
                         "lo90": R["offsets"][m][0], "hi90": R["offsets"][m][1]})
        summ.append({"outcome": outcome, "row": "verdict_" + R["verdict"].replace(" ", "_"), "estimate": np.nan,
                     "lo90": np.nan, "hi90": np.nan})
        worse = int((R["tab"].MAE_M1 > R["tab"].MAE_M0).sum())
        txt += [f"{outcome} ({label})",
                f"  sites: {R['n_oiled']} oiled, {R['n_unoiled']} unoiled; calendar years {R['years']} "
                f"(year since spill {[y - mm.SPILL_YEAR for y in R['years']]}); site-years {len(df)}",
                f"  site-averaged LOSO MAE: M0 {d['M0']:.4f}, M1 {d['M1']:.4f}; M1 minus M0 {d['diff']:+.4f} "
                f"(90% bootstrap over sites {d['lo']:+.4f} to {d['hi']:+.4f}); M1 worse than M0 at {worse} of {len(R['tab'])} sites",
                f"  VERDICT: {R['verdict'].upper()}",
                f"  90% interval coverage (pooled LOSO residual quantiles): M0 {R['coverage']['M0']:.2f}, M1 {R['coverage']['M1']:.2f}; "
                f"M1 offsets {R['offsets']['M1'][0]:+.4f} / {R['offsets']['M1'][1]:+.4f}",
                "  oiling effect (oiled minus unoiled, mixed model, 90% Wald interval) by year since spill: "
                + "; ".join(f"y{r.year_since_spill} {r.effect:+.3f} ({r.lo90:+.3f} to {r.hi90:+.3f})" for r in R["effects"].itertuples()), ""]
        card_out[outcome] = {"label": label, "verdict": R["verdict"], "sites": R["sites"], "n_oiled": R["n_oiled"],
                             "n_unoiled": R["n_unoiled"], "calendar_years": R["years"],
                             "mae_m0": d["M0"], "mae_m1": d["M1"], "m1_minus_m0": {k: d[k] for k in ("diff", "lo", "hi")},
                             "fixed_effect_parameters": R["fe_params"], "residual_offsets_90_M1": R["offsets"]["M1"],
                             "interval_coverage": R["coverage"],
                             "effect_by_year": R["effects"].to_dict(orient="records")}
    pd.DataFrame(summ).to_csv(RESULTS / "summary.csv", index=False)
    pd.concat(bysite, ignore_index=True).to_csv(RESULTS / "loso_by_site.csv", index=False)
    pd.concat(eff, ignore_index=True).to_csv(RESULTS / "effect_by_year.csv", index=False)
    head = ["Mangrove oiling-effect model, plan Phase C2 (docs/SCENARIO_PROGRAMME_PLAN.md). Run once.",
            "Verdict rule (as A1): M1 below M0 and 90% interval of the difference excludes zero -> validated; M1 below M0 only -> suggestive; else not usable.",
            "Year since spill = calendar year - 1986 (ASSUMED). Effects are oiled minus unoiled; Wald intervals from the mixed model fitted on all sites.", ""]
    foot = ["Scope: " + SCOPE]
    (RESULTS / "summary.txt").write_text("\n".join(head + txt + foot) + "\n")
    card = {"name": "mangrove-damage-v1", "status": "experimental", "built": "2026-11-13",
            "plan": "docs/SCENARIO_PROGRAMME_PLAN.md Phase C2", "model": "M1: value ~ oiled * C(year since spill) + (1 | site); M0: unoiled-group mean per year",
            "target": "oiling effect (oiled minus unoiled site-year means)", "outcomes": card_out,
            "assumed": {"spill_year": mm.SPILL_YEAR, "n_boot": mm.N_BOOT, "seed": mm.SEED}, "scope": SCOPE,
            "training_data": "results/galeta/galeta_site_year.csv (NCEI 9400033; licence unclear)"}
    MODEL_JSON.write_text(json.dumps(card, indent=1, default=float))
    print((RESULTS / "summary.txt").read_text())


if __name__ == "__main__":
    main()
