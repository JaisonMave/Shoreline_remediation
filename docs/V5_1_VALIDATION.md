# V5.1 validation record

Written 15 November 2026 (V5.1 Session 1). This file reconciles the validation figures that are quoted across the
project. No analysis was re-run to produce it and no result was changed. Every number is read from the results file
named beside it. "Implemented" and "tests pass" never mean "validated".

## 1. Historical replay: why 5/6 and 2/6 are different measurements

Three figures are quoted. They must stay separate.

| Figure | What was replayed | Rule that turns output into "active" or "natural" | Result | Source |
|---|---|---|---|---|
| Legacy replay | Legacy `HybridDecisionModel.rank_treatments` (rule tiers + ASSUMED ecological score) | Class of the top-ranked treatment (modal over 40 input draws) | 5 of 6 | `results/historical/metrics.csv`, `validation/historical_validation.py` |
| Integrated F11 replay | `decision_pipeline.decide_case` (the production pipeline) | "active" only if some option is class A (evidence of benefit over natural recovery); otherwise "natural" | 2 of 6 | `results/f11_validation_v5/metrics.csv`, `validation/f11_integrated_validation.py` |
| Always-active baseline | No model | Always "active" | 5 of 6 | both files |

Same six cases (DWH-01 to DWH-05, EVOS-01; five documented "active", one documented "natural"), same 40 Latin-hypercube
input draws per case.

**Why they differ (established from the result files).**

1. The legacy replay is the always-active baseline. In `results/historical/inference_results.csv` the modal top
   choice is `passive_sorbents` in all six cases, so the legacy model says "active" every time. Its 5 of 6 is the
   5 of 6 of "always act": the one miss is DWH-03, the only case documented as natural recovery. The v3 archive
   (`results/historical_v3/`) also says "active" in all six cases. The legacy 5 of 6 therefore shows no skill.
2. The two replays ask different questions. The legacy model asks "which allowed method ranks first?", which is
   almost never natural recovery. The pipeline asks "is any method shown by evidence to beat natural recovery?",
   which outside heavily oiled Gulf salt marsh is almost never yes.
3. Per case, F11 (`results/f11_validation_v5/historical_replay.csv`, draws saying active / natural):
   DWH-01 0/40, DWH-02 0/40, DWH-05 0/40, EVOS-01 0/40 (all documented active; beaches and rocky shore, tier
   "rules and literature", no class A possible, so the pipeline says natural and disagrees); DWH-03 5/35
   (documented natural, agrees); DWH-04 24/16 (documented active, agrees).
4. So the 2 of 6 is produced by scope, not by wrong predictions: four of the six cases are on shoreline types
   where the platform has no benefit evidence and abstains.

**What may be claimed.** Neither figure is a performance measure. Responders act by default; amenity use and
re-oiling drove the beach decisions, and the tool's objective excludes them. Six cases are too few for any rate.
Do not write "83% agreement", do not average the two, and do not quote the legacy figure without saying it equals
the always-active baseline.

**Unresolved.** No replay metric exists that can show skill. One would need cases with documented outcomes under
both action and natural recovery. Method-level agreement (legacy 1 of 5; F11 "method allowed" 320 of 400 draws
against 400 of 400 for allowing everything) shows no skill either.

## 2. Gate status of every model (rechecked against cards and results)

The same information is machine-readable in `models/registry.json` (`governance` blocks) and is returned by
`registry.governance_table()`.

| Model | State | Gate | Result | Evidence |
|---|---|---|---|---|
| `edge_loss_v1` (marsh-edge loss) | validated (point prediction) | P2: beat no-predictor baseline on held-out basins | Passed: MAE 1.296 against 1.416 m/yr | `models/p5_edge_loss_v1.json` |
| | | V5-0.2: per-class out-of-sample interval coverage | **Failed** (tested as `edge_loss_v2`) | `models/p5_edge_loss_v2.json` |
| `pah_decline_v1` (soil PAH sum) | validated within DWH | Beat no-change baseline on held-out stations | Passed: ln-MAE 0.592 against 0.631; interval coverage 0.89 | `models/pah_decline_v1.json` |
| `composer_natural_recovery_v1` | experimental | R3 coverage 80-97% | Passed (0.932) | `results/scenario_composer/summary_v4_r3.txt` |
| | | R3 heavy-cell bias within 0.25 m/yr | **Failed** (+0.549) | same |
| | | D32 heavy-cell bias after literature scaling | **Failed** (+0.330 cell, +0.389 horizon; `all_gates_pass=False`) | `results/scenario_composer/summary_d32.txt` |
| | | V5-0.1 out-of-sample oil excess lowers heavy-cell MAE | **Failed** (Barataria 1.036 against 1.011; Breton 1.743 against 1.570) | `models/oil_excess_oos_v1.json` |
| `veg_recovery_v1` | experimental ("suggestive") | Beat no-trend baseline with interval excluding zero | **Not met**: difference -0.032, 90% interval -0.144 to +0.082 | `models/veg_recovery_v1.json` |
| `mangrove_damage_v1` | experimental (capped) | Independent second spill | **Not attempted**: no data | `docs/F7_SECOND_SPILL_INVENTORY.md` |
| `beach_sand_persistence_v1` | experimental (capped) | B-1 beat category baseline in 2 of 3 states | **Failed**: 0 of 3; pooled score 0.284 against 0.216 | `models/beach_sand_persistence_v1.json` |
| | | B-2 calibration at 365 days within 10 points | **Failed** in Mississippi and Florida | same |
| `oil_excess_oos_v1` (card only) | experimental | V5-0.1 | **Failed** | card |
| `edge_loss_v2` (card only) | experimental | V5-0.2 | **Failed**: coverage 0.756, 0.795, 0.990 in three groups; Breton interval score | card |
| `process_model_v2` (card only, new in registry) | illustrative | F5: beat empirical PAH curve | **Failed**: 0.775 against 0.750 | `models/process_model_v2.json` |

**Prediction interval coverage.** The deployed edge-loss interval was calibrated on the same residuals it was scored
on, so its pooled 0.900 coverage is true by construction. On held-out predictions it runs from 0.76 to 0.99 by basin
and oiling class. It is recorded as "NOT independently validated" in the registry and that text now travels with
every `Prediction` (`interval_status`). Do not quote pooled 90% coverage as validation.

**Scope.** Validated numbers exist only for salt-marsh edge (ESI 10A) in Terrebonne, Barataria and Breton, and for
DWH marsh-soil PAH sum. Everything else is experimental, screening or literature. Mangrove evidence is one spill,
one species, one coast.

## 3. What V5.1 changed in promotion rules

A model is `validated` only if all of these hold (`registry.promotion_report`):

1. its registry entry declares `validated` and is not capped;
2. the D20 card check passes (plan, baseline beaten on held-out units, coverage reported, training range);
3. its `governance` block is complete (intended use, habitat scope, geographic scope, training data, validation
   data, validation design, baseline, uncertainty method, interval status, limitations, gates);
4. no recorded gate with `blocks_promotion: true` has failed.

The set of validated models did not change (`edge_loss_v1`, `pah_decline_v1`). The rule only makes promotion harder.
A passing software test is not one of the criteria.

Known weakness kept on record: the D20 "coverage reported" check still accepts the word "cover" in a card's
validation text. It is no longer sufficient on its own because of items 3 and 4, but it should be replaced by a
numeric field when the cards are next revised.

## 4. NOAA ratings and crosswalks

- `data/knowledge/tables/noaa_response_rating.csv` (126 rows, AI-transcribed) was compared by software with the text
  layer of the NOAA (2017) PDF: `python -m validation.noaa_rating_source_check`. Result on 15 Nov 2026: 126 of 126
  rows match on all five oil-category letters; table titles match on all rows
  (`results/v5_1/noaa_rating_source_check_summary.txt`).
- This is a transcription check only. It is **not** a human review. The table and the letter-to-verdict mapping
  (D36) keep the status "Proposed" and the pipeline prints that status in every rating source string.
- Not checked: whether rating C should mean "conditional" and D "excluded"; the method-to-option crosswalk; using
  the single NOAA sand-beach table for both ESI 3A and 4. These are owner decisions.
- `noaa_crosswalk.py` (`NOAA_TREATMENT_CROSSWALK`, page numbers from the 2013 manual) is used only by the legacy
  scenario view and has not been source-checked.

## 5. Scientific limitations that stand

- One spill for every data model. No cross-spill transfer is shown.
- Treatment differences come from one site (Bay Jimmy; 5 to 9 plots per group; observational).
- The "Recommended" category (D41, Proposed) can therefore rest on one-site observational evidence carried by an
  experimental model. The category reason states this. The owner should decide whether "Recommended" is too strong.
- Mudflat, peat and tundra shorelines borrow the salt-marsh evidence verdicts through the habitat table (D36). The
  pipeline now declares this as an abstention note; the transfer is untested.
- No expert responses exist. Nothing in the platform is expert-reviewed.
- Literature rows are AI-extracted and owner-attested, not independently double-checked.
