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
