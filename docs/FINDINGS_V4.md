# Findings, V4 programme (from 14 November 2026)

Continues `docs/FINDINGS_2026-11-11.md` (sections 1-24). Plan: `docs/V4_PROGRAMME_PLAN.md`.
Numbers are rounded from the results files named in each section.

## 25. R1 and R2: ranking without the synthetic suitability layer (14 Nov 2026)

R1 (D25): ineligible treatments now get utility 0 and are sorted below eligible and conditional options
(feasibility tier, then evidence, then utility). Before the fix, scored-but-ineligible options kept 0.4 x
ecological score and outranked eligible unscored options (e.g. on sand, eligible low-pressure heated flushing
ranked 10th). Test over 32 scenarios (30 blind scoring scenarios plus two probes).

R2 (D26, Jaison 14 Nov): the GPR suitability layer, trained on rule-generated labels, is out of the decision
path and available only as the method test (`HybridDecisionModel(use_synthetic_suitability=True)`). The
default ranking is rule feasibility tier, then an ASSUMED ecological (lower-disturbance-first) score.

SCAT checks rerun (`results/v4_r1r2/scat_checks_after_r1_r2.csv`, seed 11):

| Check | Decision path (screening only) | Method test (synthetic GPR) |
| --- | --- | --- |
| E1 NA preferred as marsh sensitivity rises | PASS | PASS |
| E2 intrusive methods not top 3 in heavily oiled marsh | PASS | PASS |
| E3 thick oil moves ranking away from NA | FAIL (rank 2.77 to 2.70) | PASS (2.98 to 4.07) |
| E4 buried oil changes the top 3 | FAIL (identical in 83%) | PASS (identical in 32%) |
| E5 high-pressure washing better on bedrock than sand | PASS (7.25 vs 13.80) | PASS |

Historical validation rerun (`results/historical/metrics.csv`; v3 values in `results/historical_v3/`):
documented method top choice 1 of 5 (v3: 3 of 5; 95% interval 4% to 62%); one distinct top choice across six
cases (passive sorbents; v3: 2); mean best documented rank 2.8 (v3 2.9; random 5.4); active/natural class
agreement 5 of 6, still equal to always predicting "active".

Reading: most of v3's improvement on E3, E4 and the historical method agreement came from the synthetic
labels, which had been edited to pass those checks. Without them, rules and the ASSUMED ecological score
cannot respond to oil thickness or burial, and passive sorbents (lowest disturbance) come first wherever they
are eligible. The within-tier order is "least disturbance first", not "most effective", and the dashboard
now says so. Effectiveness has to come from evidence: literature coefficients (R2 guide,
`docs/R2_LITERATURE_EVIDENCE_GUIDE.md`) and field data. Until then the ranking is a screening aid only.

## 26. R3: is the oil effect counted twice in the scenario composer? (14 Nov 2026)

Plan `docs/R3_OIL_DOUBLE_COUNT_PLAN.md`, committed before the run. Results `results/scenario_composer/`
(`r3_diagnostic.csv`, `c1b_*`, `c2b_*`, `b1b_*`, `summary_v4_r3.txt`).

Diagnostic, in-sample residual of the deployed baseline M1 by oiling class (90% block bootstrap): Heavy +0.43
(+0.22 to +0.70); Moderate +0.35 (+0.11 to +0.55); Light -0.19; Very Light +0.03; NOO -0.04 (-0.14 to +0.07).

Fix as pre-specified (D27): composer baseline refitted on clean-edge cells only (NOO and Very Light, 10,772
cells), `models/p5_edge_loss_clean_v1.json`. Coefficients change modestly (constant -3.81 to -3.62, pre-spill
trend 0.222 to 0.249); held-out error 1.294 vs 1.296.

| Check | Coverage, original to b | Heavy-cell bias, m/yr, original to b | Gates |
| --- | --- | --- | --- |
| C1b (cells, 2010-2015) | 93.4% to 93.2% | +0.57 to +0.55 | coverage pass, bias fail |
| C2b (blocks) | 89.9% to 89.9% | (cells in used blocks) +0.61 | coverage pass, bias fail |
| B1b (cells, 2010-2017) | 91.9% to 92.3% | +0.53 to +0.59 | coverage pass, bias fail |

NOO-bias gate passes in all three.

Reading (orchestrator; the plan's confirmation rule was mis-specified): a positive Heavy residual means M1
under-predicts heavy cells, so it did not absorb the oil effect. The double count is minor: removing oiled
cells from the baseline fit moves heavy-cell bias by only -0.02 to +0.06 m/yr. The over-prediction comes from
the size of the added excess: Zengel's untreated-plot excess averages about 0.88 m/yr over five years, while
NAIP shows about 0.43 m/yr beyond exposure and the pre-spill trend. Part of the C1 gap is a basin-level shift
common to all cells (C1b NOO bias +0.43). The clean-edge baseline is kept because it is the correct baseline
for "unoiled behaviour plus oil excess"; the bias is not fixed. Candidate: D32 (scale or replace the excess
with a NAIP-based estimate, own plan), or keep Zengel and show the bias, which R4 now does.

## 27. R6: provenance of the "expert review" (14 Nov 2026)

`data/knowledge/elicited_priors.csv` (8 rows AI-PROPOSED, 2 RULE), `mangrove_screening.csv` (14 AI-PROPOSED)
and `treatment_conditions.csv` (14 AI-PROPOSED) now carry a `provenance` column; `EXPERT_REVIEW.md` opens with a
provenance note; the dashboard says "AI-proposed range (not human-reviewed)". No value changed. D23 and D24
revert to Proposed.

## 28. R7: sensitivity of the edge-loss intervals and stale outputs (14 Nov 2026)

`validation/v4_r7_edge_loss_covariance.py`, `results/v4_r7/edge_loss_covariance.csv`. The block-dummy models
had more parameters than clusters (181 vs 176; 185 vs 180; P1 205 vs 200), so the cluster covariance was
singular. Heavy coefficient, 90% intervals (point estimates identical by construction):

| Model | Estimate | Original | Within-block clustered | Wild cluster bootstrap |
| --- | --- | --- | --- | --- |
| NAIP 2010-2015 | 1.00 | 0.58 to 1.43 | 0.59 to 1.42 | 0.56 to 1.43 |
| NAIP 2010-2017 | 1.01 | 0.65 to 1.38 | 0.65 to 1.38 | 0.65 to 1.39 |
| P1 headline (adjusted) | 0.85 | 0.49 to 1.22 | 0.49 to 1.21 | 0.49 to 1.20 |

No headline changes. PAH replicate sensitivity not run (DIVER files not on this machine;
`scripts/download_diver.sh`). Scenario reports regenerated (`reports/`, v3 in `reports/v3_archive/`): the
synthetic ML benchmark is unchanged; the scenario ranking top choice changed for cobble and bedrock (to natural
attenuation) after R1/R2.

## 29. R8: repository (14 Nov 2026)

Compiled Python files untracked and ignored; README updated (structure, V4 ranking, Python 3.11 tested);
`core.fileMode false` set locally (Windows lost the executable bit on five shell scripts). Repository stays
public: only public datasets are used (Jaison, D29). Changes committed locally; not pushed until Jaison asks.

## 30. R4, R5, R7 (composer parts): one number per site, wording, vegetation (14 Nov 2026)

- R4: `scenario_composer.natural_recovery_summary()` feeds both the Site evidence headline and Compare options.
  Bay Jimmy worked cell (8018_32612): before, Site evidence showed 1.42 m/yr (-1.74 to 4.30) with no oil term while
  Compare options added the Zengel excess. Now both show baseline 1.32 m/yr (-1.81 to 4.24, clean-edge model) plus
  oil excess +1.88 (years 1-2) and +0.21 (years 3-8), mean years 1-5 **2.30 m/yr (-0.71 to 5.10)**, with the note
  that this excess over-predicted held-out NAIP heavy cells by about 0.5 m/yr (section 26). The D9 NAIP-based
  uplift (0.34 to 0.83) is shown beside it for comparison. A test checks the two views agree.
- R5: "distinguished" now reads "difference supported by field evidence (Zengel et al., Bay Jimmy; the same at
  every heavily oiled site)"; a caption explains that paired differences remove the site's shared uncertainty.
- R7a: the Zengel year-2 vegetation shift now persists and decays with each draw's recovery time constant
  (ASSUMED) instead of a one-year spike. Manual removal, worked cell, vegetation ratio to reference: year 2
  unchanged (1.21); year 5 1.04 to 1.13; year 8 1.10 to 1.14. Ratios above 1 come from the shift and the curve's
  residual spread, not from evidence that treated marsh exceeds reference.
- R7b (D28): heavy sites carry the flag "worse than no-trend baseline for heavy oiling (FINDINGS 14); shown for
  transparency only" next to every vegetation output.
- R7c: the worked example leads with the held-out prediction (1.31 m/yr), then the full-data one (1.42).

## 31. Literature collection for treatment coefficients (14 Nov 2026)

Five AI agents on different models (GPT-5.6-sol high: marsh removal; Gemini-4-argon medium: washing; Grok-4.7 medium:
bio/chemical/burning; GPT-5.6-terra medium: beaches and natural recovery; Grok-4.6 high: oiling effect on marsh erosion)
followed `docs/R2_LITERATURE_EVIDENCE_GUIDE.md`. Merged table `data/knowledge/literature_effects.csv`: **144 rows from 90
sources** (grade A 30, B 31, C 41, D 18, E 24; 19 abstract-only). By technology: hot-water washing 25, bioremediation 28,
surface washing agents 17, oiling effect 17, natural attenuation 16, in-situ burning 10, low-pressure flushing 6, cutting 5,
planting 5, heated flushing 4, high-pressure washing 3, mechanical, vacuum, sorbents, solidifiers 2 each.
PDFs: 31 committed (open licence or US government; `docs/reference/REFERENCE_INDEX.csv`), 11 all-rights-reserved kept in
the git-ignored `docs/reference/restricted/` (incl. Challenger 2021, Deis 2019, Michel 2022 marsh guide).

Examples (as extracted; not yet checked by a person): Exxon Valdez hot-water washing cut Fucus cover to 6.9% vs 87.5% on
unwashed oiled rock 15 days after (Houghton et al. 1993) and delayed clam recovery to about 11 years; Delaware Bay nutrient
addition raised the hopane-normalised alkane loss rate from 0.026 to 0.056 per day (Venosa et al. 1996); vegetation cutting
favoured recovery in 21% of 19 comparisons (Michel et al. 2022); marsh burning is safe for roots only with standing water
(Lin et al. 2002). Gaps: no controlled evidence for vacuum, sorbents or solidifiers; sediment relocation and mixing have
no numeric treated-vs-control values; nearly all marsh evidence is Deepwater Horizon.

Reading: enough rows exist to pool washing (rocky shore, biological recovery), bioremediation (degradation rate ratio) and
the marsh oiling effect; most other technologies stay "single-study" or "no evidence". Every row is AI-extracted and
Proposed; Jaison's check of a sample against the PDFs is the next gate (guide section 5, step 1).

## 32. D32: oil excess scaled by field-size-weighted literature (14 Nov 2026)

Plan `docs/D32_OIL_EXCESS_PLAN.md` (committed before extraction). Five eligible DWH studies (McClenachan 2013 +0.33 m/yr,
30 sites; Turner 2016 +1.54, 46 islands; Zengel 2015/2022 +0.88, 14 plots; Challenger 2021 -0.13, 59 sites; Deis 2019 +1.64,
14 stations): **E = 0.665 m/yr (90% -0.69 to 2.02)**, leave-one-out 0.32 to 1.12; scale s = 0.756 of the Zengel excess.
C1c heavy bias +0.55 to **+0.33** (coverage 93.8%); B1c +0.59 to **+0.39** (92.4%); NOO unchanged. The +/-0.25 gate still
fails; adopted by the plan's rule (bias smaller than C1b and B1b). `models/oil_excess_d32.json`.
Deviation: Challenger entered with years 2-5 only; with year 1 included E would be about 0.73 (s 0.83), heavy bias about
0.05 m/yr higher. All five studies are one spill; two are remote sensing (flagged).

## 33. R7 completed: PAH replicate rule (14 Nov 2026)

DIVER downloaded (14 files, 629 MB, git-ignored) and SCAT layers fetched. `results/v4_r7/pah_replicate_sensitivity.csv`:
plain means instead of the nearer-to-median rule leave the result unchanged (PAH-sum half-life heavy 1.61 vs 1.61 years,
moderate 1.83 vs 1.83; PAH/hopane no decline in either; both validated). The primary run reproduces `results/pah_decline`.

## 34. Track F decisions and scope (F0, F1; 14 Nov 2026)

`docs/F0_F1_SCOPE_AND_DECISIONS.md`: scope tiers (validated: heavily oiled northern Gulf salt-marsh edge loss and
DWH soil PAH-sum decline; experimental: composer with oil excess, vegetation curve, mangrove damage, process model,
literature effects; rules and literature only: beaches, rocky shores, other habitats; out of scope: other
contaminants, cost optimisation, offshore). D14-D21, D30, D31 approved by the orchestrator under Jaison's delegation,
for his review. D23, D24 stay Proposed (AI-PROPOSED).

## 35. F2, F3: knowledge tables, model interface and registry (14 Nov 2026)

Plan `docs/F2_F3_PLAN.md`. Screening rules (32), ecological scores (13), technologies and the Zengel priors now live in
`data/knowledge/tables/` with source and status per row, read by `knowledge.py`. Equivalence test frozen before the
move: 0 differences over about 432,000 verdicts plus the 30 blind scenarios. `model_interface.py` (Prediction with
interval, scope, explanation, state) and `registry.py` / `models/registry.json` register five adapters; the D20
promotion check reads the model cards. Validated: edge loss v1, PAH decline v1. Experimental: composer (bias gate
failed), vegetation curve (suggestive), mangrove damage (one spill).

## 36. F4: common data schema (14 Nov 2026)

Plan `docs/F4_SCHEMA_PLAN.md`; `schema.py`; five tables in `data/schema/` (Zengel 2015/2022, edge cells) and
`data/schema_local/` (DIVER, git-ignored). Reconciliation 38 of 38 checks pass (`results/f4_schema/reconciliation.csv`):
Zengel 2015 86 values (3 non-detects carried as censored), Zengel 2022 33 plots, 45,404 edge cells (12,696 in scope),
DIVER 14,926 samples / 1,697 PAH sums / 24,705 below-detection values never stored as zero. Galeta not loaded (raw
data kept local; licence unclear). For Jaison: canonical soil units and four Zengel 2022 plot-ID aliases.

## 37. F5: process model priors, sensitivity and calibration (14 Nov 2026)

Plan `docs/F5_PROCESS_MODEL_PLAN.md`. Priors for every parameter (`data/knowledge/process_parameter_priors.csv`;
two missing ODE coefficients added); optional thickness, penetration and season inputs (defaults unchanged).
Monte Carlo, heavy-oil marsh, no cleanup: surface oil fraction year 1 0.38 (0.16 to 0.60), year 2 0.30 (0.12 to 0.51).
Sobol total-order: labile fraction 0.32, subsurface return 0.25, edge export 0.15, heavy-oil evaporation 0.11.
Calibration on DIVER PAH, 61 held-out stations: error prior 0.795, empirical first-order curve 0.750, calibrated
0.775. **Gate failed** (does not beat the empirical curve), so the process model stays illustrative and outside the
decision path (`models/process_model_v2.json`). Reason: no erosion or burial term, while PAH loss is mostly physical
(section 22 of the earlier findings).

## 38. F6, F7: treatment records and a second spill (14 Nov 2026)

`docs/F6_TREATMENT_RECORDS.md`, `docs/F7_SECOND_SPILL_INVENTORY.md`. No public segment-level DWH treatment records:
NOAA TM NOS OR&R 42 (Zengel and Michel 2013) has treated stretches only as maps (figures 35, 36, 39); the PDF returned
403 to scripts, so `scripts/download_orr42.ps1` and a digitisation protocol are left for Jaison. No spill with
oiling, treatment and outcome per segment was found for a whole-spill hold-out; partial sources (Galeta, TROPICS,
Bouchard 120, Exxon Valdez) are documented. Transfer between spills remains unclaimed.

## 39. F8: literature pooled into evidence verdicts (14 Nov 2026)

Plan `docs/F8_LITERATURE_POOLING_PLAN.md` (with amendment F8b, a defect fix after the run). No group reached three
studies with complete variances, so nothing was pooled; single-study rules apply. Verdicts
(`data/knowledge/evidence_verdicts.csv`): **evidence of harm** for hot-water washing on rocky and on gravel/sand shores
(Exxon Valdez, grade B; e.g. lnRR -0.94, 95% CI -1.58 to -0.30); all other groups "no clear difference" or "no
evidence". F8b fixed two defects: the single-study rule was not applied to two-study groups, and a bioremediation rate
row had been mapped to erosion. Venosa et al. 1996 rate ratio (about 2.2) is reported in notes without variance.
Reading: the literature supports excluding hot-water washing on biologically sensitive hard shores; it does not yet
show any option beating natural recovery outside the Zengel marsh evidence.

## 40. F9: decision pipeline (14 Nov 2026)

Plan `docs/F9_PIPELINE_PLAN.md`; `decision_pipeline.py`. Eight logged steps (characterise, hard constraints, do no
harm, benefit vs natural recovery, endpoint and time, trade-offs, recommendation classes A-E, report). Worked Bay Jimmy
cell: planting class A (8.7 m less edge loss by year 8, 90% 2.5 to 15.1, experimental composer); manual removal class
A through year-2 vegetation (+0.36 ratio, 0.20 to 0.52; edge-loss interval includes zero; trampling flag);
mechanical removal excluded by rule. Rocky shore, sand beach and mangrove examples: "No option is shown by evidence
to beat natural recovery; monitor"; hot-water washing removed on rocky shore by do-no-harm. Out-of-scope requests
refused. For Jaison: planting evidence comes from mechanically cleaned plots while the rules exclude mechanical
removal; mangrove options without a screening row are excluded as "not screened"; trade-offs mostly "not sourced".

## 41. F10: adaptive monitoring (14 Nov 2026)

Plan `docs/F10_ADAPTIVE_PLAN.md`; `adaptive.py`. Observing 25% of cells in a 2 km block and updating the shared block
residual: error of the median for the other cells 1.34 to 1.25 m/yr, 90% interval width 7.1 to 5.2 m/yr, coverage 88%
(**passes**). Time update (2010-2015 observations to forecast 2010-2017 in Barataria): interval narrows (7.0 to 5.1)
with coverage 91%, but error does not improve (1.00 to 1.00): **fails**. Monitoring helps within a period; it does not
yet carry forward in time.

## 42. F11: integrated validation (14 Nov 2026)

Plan `docs/F11_INTEGRATED_VALIDATION_PLAN.md`; `validation/f11_integrated_validation.py`; `results/f11_validation/`.
Blinded historical replay (6 sourced cases, 40 draws each): active vs natural-recovery agreement **2 of 6** (Wilson 95%
10% to 70%), below the always-active baseline (5 of 6) and below v3 and V4-R2 (5 of 6). The pipeline recommends
"monitor" wherever no option has evidence of benefit, while responders acted in five of six cases. Documented methods
were allowed (class A or B, not excluded) in 264 of 400 draw-method checks. Disagreements to review: DWH-04 mechanical
removal (excluded by rule) and EVOS-01 hot-water washing (excluded by do-no-harm; the harm evidence comes from Exxon
Valdez itself, so this is hindsight, not an independent test). Cell replay: all 532 heavy held-out cells get planting
in class A, because the paired difference is the same Zengel evidence at every heavy site (R5); coverage cited from
C1c (93.8%) and B1c (92.4%). Expert review pack with 10 reports and a form: `docs/F11_EXPERT_REVIEW_PACK.md` (no
responses collected).

Reading: the pipeline is deliberately conservative. It does not reproduce what responders did, and it should not be
judged by that alone: documented actions are not outcomes. Agreement with outcomes needs outcome data per treated
segment (F6) and a second spill (F7), neither of which exists in open form.
