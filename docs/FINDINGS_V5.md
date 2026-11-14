# Findings, V5 programme (14 November 2026)

Continues `docs/FINDINGS_V4.md` (sections 25-42). Plans: `docs/V5_P0_PLAN.md`, `docs/V5_BEACH_SAND_PLAN.md` (both written
before their analyses ran). Numbers are rounded from the results files named in each section. "Implemented" does not
mean "validated". The review these changes answer is in the project knowledge base (`claude/v4-review-and-v5-plan.md`).

## Summary in plain words

1. V5 answers the review of branch `model_v4` made on 14 Nov 2026. It changed code, evidence rules and the dashboard,
   and ran four gated tests. All four gates failed, and are reported as failures.
2. Gate 0.1 FAILED. A heavily oiled marsh cell loses about 0.5 to 0.8 m/yr more edge than an unoiled cell on average,
   but adding that amount did not lower the typical error of single cells.
3. Gate 0.2 FAILED. Splitting the edge-loss interval by oiling class, calibrated without the target basin, was outside
   the 80-97% coverage band in 3 of 12 groups and did not beat a no-predictor interval in Breton.
4. Sand-beach gates B-1 and B-2 FAILED. The model was worse than a simple curve by starting oiling category in all
   three states. The packaged beach prediction is that baseline curve, labelled experimental.
5. The F8 literature rule was put back to the original two-study rule (D34). The two "harm" verdicts for hot-water
   washing are gone; that caution now rests on sourced NOAA habitat ratings.
6. Beaches now have a habitat table keyed to ESI shoreline codes and a first sourced screening step. Sand beaches have
   data; mixed sand and gravel (and gravel) have rules and literature only.
7. F11 was rerun once. Agreement with what responders did is still 2 of 6, against 5 of 6 for "always act". "Method
   allowed" went from 264 to 320 of 400, but allowing everything scores 400 of 400, so it says nothing about skill.
8. The dashboard no longer shows a made-up uncertainty band or constant "decision confidence". It reads the decision
   pipeline. It was tested by script only; nobody has looked at it in a browser.
9. Jaison states he checked all 144 literature rows against the PDFs and asked for them to be marked. That is recorded
   as his attestation, not as an independent check.
10. What the tool may claim is unchanged: heavily oiled northern Gulf salt-marsh edge loss within Deepwater Horizon and
    DWH soil PAH-sum decline, with their stated limits. Beaches are rules and literature with one experimental
    reference curve.
11. What it may not claim: that an oil term improves single-cell predictions, that edge-loss intervals were validated
    by class, that any beach model beats a simple baseline, or that the method-allowed rate shows skill.
12. Still missing: OR&R 42 (the only route to treatment effects), a second spill, expert review, and a visual check of
    the dashboard.

---

## 43. Owner decisions and the literature check (14 Nov 2026)

**Why.** The V4 review found the 144 literature rows had an empty `checked_by` while a doc said Jaison had accepted
them, that a verdict rule (F8b) was changed after its run, and that the beach scope and the old scenario views needed
a decision.

**What was done.** Jaison decided on 14 Nov 2026:
- D33: he stated he checked all 144 rows against the PDFs and asked for them to be marked on his behalf. `checked_by`
  in `data/knowledge/literature_effects.csv` and the five part files reads "Jaison (owner attestation 2026-11-14:
  checked against the PDFs)" for all 144 rows. No other field changed.
- D34: restore the original F8 two-study rule; F8b Superseded (section 46).
- D36 scope: sand beach with data; mixed sand and gravel with rules and literature only (sections 47, 48).
- D40: keep the legacy scenario views and improve them with current models (section 50).
- He also asked that all required literature be downloaded independently (section 49), agents be used by task
  complexity, everything be documented for handover, and all changes be committed. Commits are local; nothing was pushed.

**Reading.** The mark records what the owner said. It is not an independent check. The review's proposed test (two
independent extractors agreeing on value and sign for the decision-changing rows) was not run. The rows keep the label
"AI-extracted" in the provenance columns.

**Limits.** For a consequential decision, open the PDF behind the row. Note for the owner: 19 rows were extracted from
abstracts only, and the restricted PDFs (Challenger 2021, Deis 2019 and others) are not in this clone. Row B023 is
correct as extracted, but its metric means "deeper initial depletion" when higher; the pooling code read it as a
benefit until the fix in section 46.

---

## 44. Out-of-sample oil excess against no excess (V5 Phase 0.1, D37)

Plan `docs/V5_P0_PLAN.md`. Script `validation/v5_p0_oil_excess.py`. Results `results/v5_p0/oil_excess_summary.txt`,
`oil_excess_estimates.csv`, `oil_excess_gate.csv`. Seed 20261114. Run once.

**Why.** The composer's "oil effect" had never been compared with the same baseline without it. On the 532 heavy
held-out cells in Barataria and Breton the no-excess baseline has mean absolute error (MAE) 1.044 m/yr (bias -0.475);
the composer with the Zengel excess scored 1.302 and with the D32-scaled excess 1.185. The gate was set after the
reviewer had seen these baseline numbers, so the test is not blind.

**What was done.** For each oiling class, the excess is the mean difference in edge-loss rate, within 2 km blocks,
between cells of that class and "no oil observed" (NOO) cells. It was estimated only from the other basins ("out of
sample") and added to the clean-edge baseline. Intervals are 90% block-bootstrap.

**Gate (fixed before the run).** In each held-out basin with 30 or more heavy cells, the heavy-cell mean absolute error
with the out-of-sample excess is strictly below that of the no-excess baseline, AND (heavy-cell bias minus unoiled-cell
bias) is within plus or minus 0.25 m/yr.

**Result.**

| Basin held out | Heavy cells | Excess from other basins, m/yr (90%) | MAE no excess | MAE with excess | Heavy-minus-NOO bias, none / with | MAE lower | Bias within 0.25 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Barataria | 501 | +0.529 (0.135 to 1.306); 13 blocks, 45 heavy cells | 1.011 | 1.036 | -0.448 / +0.081 | No | Yes |
| Breton | 31 | +0.783 (0.353 to 1.297) | 1.570 | 1.743 | -1.531 / -0.749 | No | No |
| Terrebonne (not gated) | 20 | +0.690 (0.266 to 1.153) | 1.268 | 1.193 | -0.380 / +0.310 | Yes | No |

- Deployable estimate, all three basins: Heavy +0.714 (0.349 to 1.145); Moderate +0.794 (0.464 to 1.111); Light +0.324
  (0.004 to 0.662).
- Pooled Barataria and Breton heavy cells (n = 532): MAE 1.077, bias +0.069 with the excess; 1.044 and -0.475 with none.
- Barataria MAE difference, excess minus none: +0.025 (90% block bootstrap -0.046 to +0.088).

**GATE 0.1: FAILED.** MAE was not below the baseline in either gated basin. The bias condition passes in Barataria and
fails in Breton.

**In plain words.** Heavily oiled cells really do lose more edge on average, about 0.5 to 0.8 m/yr more than unoiled
cells in the same block, so adding the oil term corrects the average. But individual 100 m cells vary far more
(typical errors about 1 m/yr) than the oil effect. Shifting every heavy cell by one constant moves as many cells away
from their observed value as towards it, so the typical error does not fall. The oil term cannot make single-cell
predictions more accurate; it describes an average difference. This agrees with P2 (FINDINGS section 8: oiling class
adds no cell-level accuracy over exposure).

**Reading.** In the two gated basins and pooled, no excess tested (out of sample, Zengel, D32) beat no excess on MAE.
In Terrebonne (20 heavy cells, not gated) the excess scored slightly lower; descriptive only. In Breton the whole
basin is offset (unoiled cells already over-predicted by 0.58 m/yr), with 31 heavy cells in 5 blocks, so no constant
could pass. The average excess (0.71) sits below the Zengel site value (0.88) and near D32 (0.67).

**Limits.** Why a mean-based excess removes bias but raises MAE (skewed residuals are likely) was not tested. Exposure
confounding within blocks was not tested. Hidden treatment in the "natural" group remains untested (needs OR&R 42).

**Code.** `models/oil_excess_oos_v1.json` is "experimental (gate failed)". `scenario_composer.compose()` and
`natural_recovery_summary()` gained `oil_excess_source="default"|"oos_v1"`; defaults unchanged.

**Applied in the dashboard (orchestrator's call under the owner's delegation, for his review; see section 51).** The
per-site number is the clean-edge prediction with no excess. The heavy-oiling excess is shown separately as "average
extra loss on heavily oiled marsh, +0.71 m/yr (90% 0.35 to 1.15); not a cell-level prediction".

---

## 45. Out-of-sample per-class intervals (V5 Phase 0.2, D38)

Script `validation/v5_p0_intervals.py`. Results `results/v5_p0/interval_summary.txt`, `interval_coverage_gate.csv`,
`interval_by_basin.csv`, `deployable_offsets.csv`. Run once.

A **conformal interval** reads its width off the sorted errors a model made on data it was not fitted to, so that about
90% of similar new cells should fall inside. The **Winkler score** is the interval width plus a penalty for each miss,
averaged over cells; lower is better.

**Why.** The deployed edge-loss interval was calibrated on the same leave-one-basin-out residuals it was judged by, so
its pooled coverage of 0.900 is true by construction.

**What was done.** The 90% interval was recalibrated per oiling class using only the other basins. A refit check
reproduces the committed predictions to within 0.0001. Held-out Barataria Heavy had only 51 calibration cells, so it
used the all-class offsets, as the plan says.

**Gate (fixed before the run).** Coverage of the 90% interval is between 80% and 97% in every basin-by-oiling-class
group with 100 or more cells, AND the interval (Winkler) score is lower than that of the no-predictor baseline interval
in each held-out basin.

**Result.**
- Coverage: 9 of 12 groups pass. Fails: Breton Very_Light 0.990, Terrebonne Light 0.795, Terrebonne Very_Light 0.756.
  Barataria Heavy 0.930.
- Winkler, gated vs baseline: Barataria 12.10 vs 12.66 (pass); Breton 11.28 vs 11.20 (FAIL); Terrebonne 10.26 vs 10.29
  (pass).
- Descriptive: one all-class out-of-sample interval scores better than per-class in Barataria and Terrebonne (11.89,
  10.06) and about the same in Breton (11.30). Mean width of the gated interval 5.6 to 6.7 m/yr.

**GATE 0.2: FAILED.**

**In plain words.** The interval is about 6 m/yr wide while the signal is about 1 m/yr, so coverage is easy to reach
and says little. Calibrating without the target basin shows basins differ in level by about 0.5 m/yr, which leaves
small classes in Terrebonne and Breton over- or under-covered. Splitting by class made intervals wider, not better.

**Reading.** Do not switch to per-class intervals. Stop quoting pooled 90% coverage as validation. A fair label, now
used in the dashboard: "about plus or minus 3 m/yr; covered 76 to 99% of held-out cells depending on basin and oiling
class". In Breton the predictor adds so little over a plain average that its interval scores no better.

**Corrections made.** `models/p5_edge_loss_v1.json` keeps its original sentence with a bracketed correction (the 89% is
P2 model M2's inner interval, not the deployed interval) and a new `interval_calibration_note`.
`models/p5_edge_loss_v2.json` is "experimental (gate failed)" and must not be promoted.

---

## 46. Pipeline and evidence rules (D34, D35)

Files: `validation/literature_pooling.py`, `src/shoreline_remediation/{decision_pipeline,knowledge,habitat,noaa_crosswalk}.py`,
`data/knowledge/`, `results/f8_pooling/v3_original_rule/`, `results/f11_validation_v5/`.

**Why.** The review found that F8b changed a written verdict rule after the run and its two "harm" verdicts drove
do-no-harm exclusions; that "monitor" covered both "no clear difference" and "no evidence"; that AI-proposed rows set
class D flags; and that planting was shown as randomised evidence.

**What was done.**
- F8 restored (D34): the original rule is the default (a group with two studies is "no clear difference"). F8b stays
  behind `--rule f8b` for reproducibility; Superseded. The restore covers the verdict rule only; F8b's other two
  changes (outcome-family keyword precedence, row C011 excluded from erosion) were kept: open question for the owner.
- B023 direction fix: "larger rebound at washed sites" had been read as a benefit; the pooling code now reads it as
  harm. The extracted row was not edited. It changes no verdict under either rule (`verdict_comparison.csv`).
- Insufficient evidence (D35): a separate `evidence_state` from "no clear difference (evidence exists)"; the headline
  says which applies; class letters A-E unchanged.
- Honest labels: planting is "observational, one site" and presupposes mechanical removal, which the rules exclude.
  AI-proposed condition rows are advisory notes and no longer set class D. AI-proposed reviews are displayed as
  "AI-proposed review (not reviewed by an expert)". The mangrove and PAH cards carry dated wording notes.

**Result.**
- F8 verdicts (`results/f8_pooling/v3_original_rule/summary.txt`): 0 benefit, 0 harm, 9 no clear difference, 24 no
  evidence. Both hot-water groups are "no clear difference" again.
- F11 rerun once into `results/f11_validation_v5/` (v4 folder untouched):

| Metric | v4 | v5 |
| --- | --- | --- |
| Active vs natural agreement (6 cases) | 2 of 6 | 2 of 6 |
| Always-active baseline | 5 of 6 | 5 of 6 |
| Documented method allowed (class A or B) | 264 of 400 | 320 of 400 |
| Allowed or flagged (A-D) | not reported | 360 of 400 |
| Allow-everything pipeline | 400 of 400 | 400 of 400 |
| Documented methods excluded | DWH-04 mechanical; EVOS-01 hot water | DWH-04 mechanical |

**In plain words.** Nothing got better at matching responders. The allowed rate rose only because AI-proposed
condition rows no longer make class D, and hot-water washing in the Exxon Valdez case moved from excluded to flagged
on a NOAA rating. Agreement with responders is not a performance measure: responders act by default, and
amenity-beach decisions were driven by human use, which the tool's objective leaves out.

**Limits.** The Exxon Valdez replay inputs assume an exposed rocky shore (NOAA rating C, conditional); the actual sites
were largely sheltered, where NOAA rates hot water D (excluded). Pre-specified sampling ranges were not changed. The v5
review pack holds 12 reports against 10 in v4; no reviewer responses exist for either.

---

## 47. Beach screening and habitat table (D36)

Files: `src/shoreline_remediation/habitat.py`, `data/knowledge/tables/{habitat,noaa_response_rating,noaa_rating_mapping,
noaa_oil_category,beach_literature_notes}.csv`, `screening_rule.csv`, `tests/test_habitat.py`.

**Why.** The code had only `sand_beach` and `mixed_sediment`, mapped cobble two ways, applied hot-water harm evidence
from gravel beaches to fine sand, and rule 160 made hot high-pressure washing eligible on permeable mixed sediment.

**What was done.**
- Habitat table keyed to ESI code (fine-to-medium sand 3A, coarse sand 4, mixed sand and gravel 5, gravel 6A, marsh,
  mangrove, rocky and others); every string used in the code is an alias. Cobble resolves to ESI 6A.
- NOAA "Characteristic Coastal Habitats" ratings transcribed for 3A, 4, 5, 6A and rocky shores with page numbers.
  The letters A-D rate the adverse habitat impact of a method by oil type, not how well it removes oil.
- Mapping (Proposed): A or B eligible; C conditional (flag shown, option stays); D not advised, excluded with the
  source cited; "-" not applicable, excluded; I insufficient information.
- Rule 160 fixed. Evidence rows are filtered by ESI family, so mixed and gravel evidence no longer applies to fine sand.
- Mixed sand and gravel, and gravel: scope tier "rules and literature only", with literature notes shown as
  "literature, not a prediction".

**Reading.** Beaches now have habitat-specific screening with a cited source. This is screening, not a forecast of
cleanup outcome.

**Limits.** ASSUMED: the mapping from the tool's oil categories to NOAA's I-V, and the exposed/sheltered rocky split.
Grain size is not yet a rule input. The NOAA transcription and the beach literature notes were made by an AI agent and
need the owner's spot-check. Surf washing and sediment relocation are not in NOAA's tables.

---

## 48. Sand-beach persistence of visible oil (D39)

Plan `docs/V5_BEACH_SAND_PLAN.md` (gates written before the analysis). Script `validation/v5_beach_sand.py`. Results
`results/v5_beach/summary.txt` and CSVs. Seed 20261114.

**Why.** The one open source with repeated beach surveys is Deepwater Horizon SCAT, NCEI 0163818 layer 18613
(Alabama, Mississippi, Florida), not used by the project before.

**What was done.** 40,427 survey records on 3,007 segments (the earlier counts were reproduced exactly). The unit is
the segment, not the zone within a segment, because the NCEI metadata say zone letters are re-assigned at every survey.
Fine-to-medium sand segments first seen oiled: 1,007 (Alabama 239, Mississippi 269, Florida 499). For 713 the clearing
date is known only to lie between two visits (interval-censored); 294 were never recorded clear (right-censored). An
interpretable time-to-event model was held out by state against a baseline curve by starting oiling category. Coarse
sand (ESI 4) could not be modelled: 9 segments, none oiled.

**Gates (fixed before the run).** B-1: holding out each state in turn, the model's integrated Brier score over 90, 180,
365 and 730 days is lower than the baseline's in at least two of the three held-out states and pooled over all three.
B-2: in each held-out state, predicted and observed persistence at 365 days differ by no more than 10 percentage
points, and the 90% interval for state-level persistence at 365 days contains the observed value. (The Brier score is
the average squared gap between a predicted probability and what happened; lower is better.)

**Result.**

| Held-out state | Score, model | Score, baseline | Oiled at 1 year, observed | Model [90%] | Baseline |
| --- | --- | --- | --- | --- | --- |
| Alabama | 0.306 | 0.256 | 0.550 | 0.502 [0.444, 0.565] | 0.484 |
| Mississippi | 0.270 | 0.228 | 0.541 | 0.308 [0.260, 0.361] | 0.378 |
| Florida | 0.280 | 0.190 | 0.219 | 0.542 [0.471, 0.613] | 0.412 |
| Pooled | 0.284 | 0.216 | | | |

- Gradient boosting (secondary, not gated): pooled 0.317, worse still.
- County hold-out (descriptive, 10 counties): observed one-year persistence 0.00 to 0.84.
- Re-oiling: 510 of 686 cleared segments with a later visit (74%) were recorded oiled again, median 16 days later.
- Packaged baseline, share still oiled at one year: light surface oil 0.49; moderate or heavy surface oil 0.74; light
  tarballs 0.13; moderate or heavy tarballs 0.35.

**GATE B-1: FAILED** (model better in 0 of 3 states). **GATE B-2: FAILED** (Alabama passes; Mississippi off by 23
points; Florida by 32). Declared state "experimental (gate failed: B-1, B-2)"; the packaged prediction is the baseline
curve and the output says so.

**In plain words.** "Time until no oil observed" is a weak measure. Three in four cleared segments were oiled again
within weeks, and the answer depends on how often a segment was visited and when surveying stopped. The spread between
counties (0 to 84% at one year) is far larger than the spread between oiling categories, so local cleanup effort and
survey decisions, which the data do not record, dominate.

**Reading.** The tool may show the baseline curve by starting category, labelled experimental, with the warning that
held-out states were missed by up to 19 points. It describes visible oil under the response as carried out. It is not
natural recovery, not chemical or ecological recovery, misses buried oil, and cannot rank treatments.

**Limits.** One spill, three states. Treatment is unrecorded (Michel et al. 2017 report about 683 of 965 km of oiled
sand beach treated; figure taken from the abstract). Surveys followed response priority. The pre-specified
visit-frequency check turned out to select on the outcome and is uninformative; reported as run. One run crashed while
writing the card; the rerun gave byte-identical result tables and nothing was tuned.

**Next (Proposed).** Redefine the beach outcome before any new model: for example the share of surveys oiled per
season, or the oiling category through time, with visit frequency handled explicitly.

---

## 49. Literature and data obtained (Module 1)

Files: `docs/reference/literature/`, `docs/reference/REFERENCE_INDEX.csv` (12 rows added), `docs/LITERATURE_TO_DOWNLOAD.md`,
`data/external/{evos_lingering_oil,evthd_goa,evos_bioremediation_pilot}/`, `scripts/download_evos_lingering_oil.sh`,
`scripts/download_evthd_goa.sh`, `results/v5_literature/url_checks.csv`. Lawful open sources only.

**Obtained.** Michel et al. 2013 (with supplement) and 2017, Lindeberg et al. 2018 (318 pages), NOAA sunken oil mats
guide (2020), two open Geng and Boufadel papers, NOAA/API 1994 freshwater options, USGS OFR 2015-1057 (partial, HTML).
Data: Exxon Valdez 2015 lingering-oil survey tables (DOI 10.24431/rw1k1h), a 2015-2025 segment-status synthesis (draft
agency analysis, DOI 10.24431/rw1kaio), and the EVTHD hydrocarbon database as CSV. Each has a `SOURCE.md` with
checksums. Large raw files are git-ignored with download scripts.

**Not obtained.** NOAA TM OR&R 42 (NOAA's repository refuses scripted requests); OSAT-2 and OSAT-3 (host
decommissioned); Short 2004/2007, Li and Boufadel 2010, Hayes and Michel 1999, Owens 2003, Challenger 2021, Deis 2019
(paywalled); 2001/2003/2005 pit surveys (not public as files); the Prince William Sound bioremediation pilot tables
(access controlled). Each is listed with a lawful route in `docs/LITERATURE_TO_DOWNLOAD.md`.

**Reading.** Acquisition only: nothing was extracted or analysed, and no result depends on these files yet. The Exxon
Valdez lingering-oil data are the best open candidate for a gravel and mixed-beach persistence analysis; it needs its
own pre-specified plan first.

---

## 50. Dashboard (D40)

Files: `src/shoreline_remediation/{ui_theme,ui_evidence,ui_pipeline,ui_components,ui_compare,ui_report,ui_scenario}.py`,
`dashboard.py`, `site_view.py`, `validation_panel.py`, `.streamlit/config.toml`, `tests/test_dashboard_v5.py`.

**Why.** The review found a formula-based uncertainty band, constant "decision confidence" (0.6, 0.4, 0.2 by tier),
"ML-ranked" wording on a rule screening, process-model charts that looked like predictions, internal ids in user text,
a red-to-green colour ramp, and both views running on every click.

**What was done.** The dashboard reads the decision pipeline; legacy scenario views are kept and re-based on it (D40).
The formula band and the constants are removed and replaced by evidence-grade chips. "ML-ranked" became "rule screening
ordered by an ASSUMED ecological score". Process charts are labelled illustrative (FINDINGS_V4 section 37). AI-proposed
ranges appear only as "AI-proposed range, not evidence", in a hatched block. Internal ids moved to a "Sources and
decisions" expander. Answer-first landing card, interval bars with a zero line, colour-blind-safe colours, light and
dark theme, one "Scope and limits" panel, option cards, HTML report download, habitat switcher with four beach entries.
Only the active view runs.

**Result.** Streamlit's script tester, before to after: cold load 3.1 s to 2.7 s; scenario run 3.9 s to 1.2 s;
site-view rerun after a scenario run 3.8 s to 0.5 s (agent's measurements; no results file).

**Limits.** No person has seen the screen: dark mode, contrast, hatched chips, mobile layout and the HTML report are
unchecked. The satellite map was not built (`st.map` kept). The pipeline is called with 3,000 draws for speed (default
5,000). `decision_framework.py` still holds the constants; the UI no longer shows them.

**For the owner to look at.** Landing answer card; interval chart with zero line; option cards; "Scope and limits";
light and dark theme; hatched AI-proposed block; beach panel; legacy scenario view; HTML report opened in a browser.

---

## 51. Integration

Files: `models/registry.json`, `src/shoreline_remediation/registry.py`, `decision_pipeline.py` (beach hook),
`site_view.py`, `ui_*.py`, `data/meta/variable_dictionary.csv`, tests.

**What was done.**
- Registry: `beach_sand_persistence_v1` added with its adapter; `oil_excess_oos_v1` and `edge_loss_v2` listed as cards
  without adapters. All three experimental (gate failed). A `max_state` cap stops the beach and mangrove entries being
  promoted. `edge_loss_v1` and `pah_decline_v1` remain the only models marked validated, in their stated scope.
- Pipeline: for fine-to-medium sand beach (ESI 3A) only, the report carries the baseline persistence curve as a
  reference, state "experimental (gate failed)". Scope text: "rules and literature, plus an experimental persistence
  reference (did not beat its baseline; not transferable between states)". ESI 4, 5 and 6A return no outcome model.
- Dashboard beach panel: the curve at 90, 180, 365 and 730 days with its 90% range, the chip "Experimental: failed
  validation", and plain text that this is visible oil under the cleanup as carried out, that 74% of cleared segments
  were oiled again (510 of 686, read from `results/v5_beach/reoiling.csv`), and that results differed between states.
  The starting group defaults from the oiling class (ASSUMED) and can be chosen by the user.
- Marsh site view: the headline is the clean no-excess prediction; the heavy-oiling excess is a separately labelled
  average read from the card; the interval caption gives the 76 to 99% held-out coverage range read from
  `results/v5_p0`. The option comparison still uses the composer and says so.
- Ten beach variables added to the variable dictionary.

**Result.** Full test suite after integration and catalogue rebuild: 327 tests, all passing on 14 Nov 2026 with Python 3.13.

**Limits.** The marsh headline number changed (it no longer includes the Zengel excess); this is the orchestrator's
call under the owner's delegation and awaits his review. The composer's own defaults are unchanged, so the headline
and the option comparison use different baselines, and the screen says so. Not viewed in a browser.
