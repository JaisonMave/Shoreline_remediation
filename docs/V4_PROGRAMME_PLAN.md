# V4 programme plan: review fixes and the final decision support system (14 November 2026)

Status: **Proposed.** Nothing in this plan has been run. Written after the critical review of branch
`process-model-audit` (pushed to `model_v3`, commit f2986f6) and after reading `ROADMAP.md`,
`REVIEW_NOTES.md`, `ARCHITECTURE_FOUNDATION.md`, `HANDOFF.md` and `CHANGELOG.md`.
New decisions are numbered D25 onwards in the register in `docs/ROADMAP.md`.

Two tracks:
- **Track R (review fixes):** defects and overstatements found in v3. Done first, because the dashboard is
  live and two of them change what a user sees.
- **Track F (final system):** the roadmap milestones M2 to M10 turned into a decision support system whose
  every recommendation can be traced to a rule, a validated prediction or a labelled piece of evidence.

## 0. Working pattern (unchanged from v3, made explicit)

Each activity below follows the same cycle. An activity is not Completed until every step is done.

1. **Plan before run.** A plan section (in this file or `docs/<ID>_PLAN.md`) fixes the question, data,
   method, baseline, gate and what counts as pass or fail. It is committed before any outcome is looked at.
2. **Run once.** Analyses with a gate are run once. A rerun after a defect fix is a new, labelled check
   (e.g. C1b), and the original result is kept.
3. **Baseline always.** Every model is compared with a no-predictor or no-change baseline on whole held-out
   units (D5, D20). Nulls are reported.
4. **Label everything.** Every parameter is SOURCED or ASSUMED; every evidence row is MEASURED, ELICITED
   (human), AI-PROPOSED or NO EVIDENCE; every model is experimental or validated.
5. **Record.** After each activity:
   - results in `results/<activity>/`, tests in `tests/`, catalogue rebuilt if data changed
     (`python scripts/build_catalogue.py`);
   - a numbered section in the findings file (start `docs/FINDINGS_V4.md` at section 25);
   - a `CHANGELOG.md` entry (why, what, files, rerun command, result, status);
   - status and decisions in `docs/ROADMAP.md`; resolved or new notes in `docs/REVIEW_NOTES.md`;
   - the job table in `docs/HANDOFF.md` updated at every checkpoint;
   - one commit per activity with a descriptive message. No push unless Jaison asks.
6. **Numbers from files.** Reported numbers are rounded from the results CSVs, never from earlier text.
7. **Jaison's gate.** Items marked "Jaison" wait for his review; they stay "Under validation" until then.

Status words as in the roadmap: Not started, In progress, Awaiting data, Under validation, Completed, On hold.

---

## Track R: fixes from the v3 review

Order: R1 -> R2 -> R3 -> R4/R5 -> R6 -> R7 -> R8. R1 and R3 change outputs a user sees and come first.

### R1 Ranking: ineligible treatments ranked above eligible ones (defect)

- **Found:** `decision_framework.py` gives scored treatments utility `0.4*E` even when ineligible, and sorts
  all scored treatments before unscored ones. On sand, eligible `low_pressure_heated_flushing` ranks 10th
  below two ineligible options; on marsh, ineligible mechanical removal (U 1.20) ranks above conditional
  vegetation cutting.
- **Fix:** utility 0 for every ineligible treatment, scored or not; sort by feasibility tier
  (eligible > conditional > ineligible), then evidence (scored before unscored), then utility.
- **Tests (written first, must fail on the current code):** no ineligible treatment above an eligible or
  conditional one in any of the 30 blind scenarios and the six historical cases; utility of ineligible = 0.
- **Rerun as labelled checks:** SCAT checks E1-E5 and `python -m validation.historical_validation`;
  before/after table in FINDINGS.
- **Decision:** D25 (tiered sort).

### R2 Ranking: passive sorbents first for heavy, thick oil; checks no longer independent

- **Found:** sorbent labels have skewed noise (-0.8 to +2.0) and a fixed ecology score of 6.5; checks E3
  and E5 pass because the rules were edited to pass them (`RANKING_FIXES.md`).
- **Question for the plan:** is a smoothed copy of hand-written rules worth keeping in the decision path?
- **Proposed answer (D26):** no. Until human expert scores (M6) or field outcome labels exist, the
  rule-trained GPR suitability layer leaves the decision path and stays only as "Method test (synthetic
  data)". The ranking view becomes **screening plus evidence**: feasibility tier from rules, field evidence
  beside it (D13), and no single synthetic suitability score.
- **If Jaison prefers to keep the score:** make the label noise symmetric for every treatment, make the
  sorbent ecology and suitability depend on oil load (sorbents as a secondary or polishing method where oil
  is thick or heavy; source: NOAA Shoreline Assessment Manual and NOAA marsh guidance, both ASSUMED magnitudes),
  and pre-specify **new** checks E6-E8 before any change, written from the guidance and not from model
  output. Report E1-E5 as "not independent".
- **Gate:** D26 decided by Jaison before code changes.

### R3 Scenario composer: oil effect probably counted twice (defect, to be confirmed)

- **Found:** the composer baseline (`p5-edge-loss-v1`, model M1 without an oiling term) was fitted on
  2010-2015 rates that include heavily oiled cells, and the full Zengel untreated-plot excess (+1.88 m/yr in
  years 1-2, +0.21 after) is added on top. Heavy cells are over-predicted by +0.53 m/yr (B1) and about
  +0.6 (C1); clean cells by +0.06.
- **Diagnostic (pre-specified, run first, no outcome comparison):** mean in-sample M1 residual by oiling
  class in the training data. A heavy-cell residual clearly above zero confirms that M1 already absorbs part
  of the oil effect.
- **Candidate fixes, choice fixed in the plan before C1b/B1b are run (D27):**
  1. Clean-edge baseline: refit M1 on NOO and Very Light cells only; keep the Zengel excess. Primary.
  2. Single-model: use M2 (with oiling term) as baseline and drop the separate excess.
  3. Keep M1 and subtract the mean heavy-cell M1 residual from the Zengel excess.
- **Checks C1b, C2b, B1b:** same data, same gates (80-97% coverage) plus a new bias gate: heavy-cell mean
  bias within +/-0.25 m/yr without worsening the NOO bias by more than 0.1 m/yr. Original C1, C2, B1 kept.
- **Note:** NAIP reads about 1.2 m/yr low against field plots, and most heavy shoreline was cleaned. Both
  remain open after the fix and are stated beside the result.

### R4 One absolute edge-loss number per site (consistency)

- **Found:** "Site evidence" leaves out the heavy-oiling uplift (D9); "Compare options" adds it. The same
  cell shows 1.42 m/yr and about 3.4 m/yr.
- **Fix:** both views call one function for the absolute forecast (the R3-corrected composer); the D9 range
  is shown as a component of that number, not as a separate rule. Test: both views give the same median for
  the worked cell.

### R5 "Distinguished" overstates what the comparison shows (wording)

- **Found:** paired differences cancel the baseline and oil draws, so "distinguished" restates whether the
  Zengel interval (one site, observational except planting) excludes zero; it is the same at every site.
- **Fix:** rename to "difference supported by field evidence (Zengel, Bay Jimmy; same at every heavy site)";
  show the share of each option's range that is shared site uncertainty versus option evidence. No change
  to numbers.

### R6 AI-written expert review labelled as expert (provenance)

- **Found:** `data/knowledge/EXPERT_REVIEW.md`, the revised `elicited_priors.csv` ranges and
  `mangrove_screening.csv` were produced by the AI orchestrator acting as an expert. D23 and D24 are marked
  "Approved by orchestrator".
- **Fix:** new evidence label AI-PROPOSED; D23 and D24 back to Proposed; dashboard text "AI-proposed range,
  not reviewed by a human expert"; the rule-based ranges stay visible. Human review is part of F8.

### R7 Statistical and modelling details

| Item | Fix | Type |
| --- | --- | --- |
| Edge-loss model: 181 parameters, 176 clusters, singular cluster covariance | Absorb block fixed effects (within transformation) and recompute clustered errors; report beside the original | Sensitivity, original kept |
| Vegetation: year-2 treatment shift applied to year 2 only (spike) | Apply the Zengel shift as a change in the recovery time constant fitted to the year-2 difference, or hold it from year 2 with a stated decay; choice in plan | Defect |
| Vegetation curve worse than baseline for heavy oiling but used in the composer | Show the curve only with a "worse than no-trend for heavy oiling" flag, or drop it for heavy cells (D28) | Scope |
| PAH replicate rule keeps the value nearer the station median | Sensitivity run with plain means; primary result unchanged unless the plan says otherwise | Sensitivity |
| Worked example headline from a model that included Barataria | Headline the held-out prediction (1.31 m/yr); in-sample shown second | Wording |
| `reports/comparison_report.csv` and benchmark figures predate the ranking changes | Regenerate after R1/R2 | Stale output |

### R8 Repository and governance

- Stop tracking `__pycache__/*.pyc`; extend `.gitignore` to all Python versions.
- README: current structure, Python version actually tested (3.11 dashboard check, D-review note D2).
- Public repository: the remote is public and contains DWH-derived tables, claude.ai links and AI-written
  reviews. **Jaison decides (D29)** whether it should be private under Shell data rules before any further push.
- Local tooling note in HANDOFF: the git on PATH fails to start; GitHub Desktop's git works.

---

## Track F: from proof of concept to the final decision support system

### F0 What "final" means here (scope statement, D30)

The system answers, for a given oiled shoreline segment: **which options are allowed, which are expected
to do better than natural recovery, by how much, with what confidence, and on what evidence.** It returns
"no option is distinguishable from natural recovery; monitor" as a legitimate answer.

Scope by evidence, not by ambition (D1 holds):
- **Validated scope today:** heavily oiled salt marsh, northern Gulf of Mexico, physical outcome (edge loss).
- **Experimental scope:** vegetation recovery, soil PAH (physical loss), red-mangrove damage.
- **Rules only:** beaches, rocky shores, other habitats (screening, no outcome prediction).
- Out of scope until data exist: other contaminants (M7), cost-optimal ranking.

### F1 Close the parked reviews (Jaison)

P1-P5 reviews, variable-definition check, dashboard test, decisions D14-D21 and D25-D30. Nothing in F3
onwards changes a validated number before this. **Gate:** decisions recorded in the register.

### F2 Knowledge base as tables (D16)

Move `fast_engine.py` rules, `treatment_effects.py` priors and treatment conditions into `technology`,
`screening_rule` and `evidence_effect` tables with source, evidence type and status per row.
**Gate:** an equivalence test shows the engine gives identical verdicts before and after the move; a test
fails any row without source and status.

### F3 Model interface and registry (D15, D20)

`predict(site, scenario) -> Prediction` (value, interval, scope flags, explanation, evidence grade, model
id). Register: edge loss v1 (validated), composer (validated only for C1b/B1b scope), vegetation curve,
PAH decline, mangrove damage (experimental). **Gate:** a contract test every registered model passes; the
orchestration layer can reach validated models only, experimental ones only with a visible flag.

### F4 Common data schema (D14)

Five tables (source, site, event, observation with censoring, intervention). Loaders in order: DIVER
wetland chemistry, Zengel 2015/2022, edge cells, Galeta. **Gate:** row counts and checksums reconcile with
the current per-analysis tables; catalogue tests pass.

### F5 Process model made honest (D18 steps 1-3)

1. **Priors:** each of the 19 transport parameters gets a distribution with source (8 sourced today) or a
   wide ASSUMED range. Add oil thickness, penetration depth and season as inputs (review gap).
2. **Monte Carlo and global sensitivity** (Sobol indices): output distributions; identify the three or four
   influential parameters.
3. **Bayesian calibration** of those parameters against DIVER soil PAH, stations held out whole: the PAH sum
   for physical loss, the PAH/hopane ratio for degradation (D22).
**Gate:** calibrated model beats the uncalibrated priors and the empirical first-order decline curve on
held-out stations; at least one posterior differs from its prior. If it fails, the process model stays
"illustrative" and leaves the decision path. Step 4 (ML surrogate) not planned.

### F6 Treatment effects at scale (M3)

Digitise the treated stretches from NOAA TM OR&R 42 map figures (the only segment-level cleanup record
found), georeference and join to edge cells; pre-specified comparison of edge loss by cleanup method with
exposure and pre-spill trend adjustment. This is the proper fix for the heavy-oiling over-prediction.
**Gate:** plan committed; digitisation checked by Jaison on a sample; result reported whether or not it
agrees with Zengel.

### F7 Second spill (M4) and transfer (D5)

Candidates, data availability to be verified and each source cited (no case without a source; missing
stays NOT_SOURCED): Exxon Valdez beach and rock monitoring (NOAA), other NOAA SCAT archives, Hebei Spirit,
Prestige, Wakashio (mangroves). Harmonise to the F4 schema; hold out the whole spill.
**Gate:** at least one spill with oiling, treatment and outcome data; transfer result reported per habitat.
Without it, the system is described as "within-spill validated" and no wider claim is made.

### F8 Human expert elicitation (M6)

Three or more human experts score the 30 blind scenarios (`docs/EXPERT_SCORING_PROTOCOL.md`); agreement by
ICC. A structured elicitation (SHELF-style) for the untested-treatment ranges replaces the AI-proposed
values (R6). **Gate:** ICC reported; if agreement is poor the ranges stay wide and the disagreement is shown.
Needs collaborators (On hold until Jaison has them).

### F9 Decision logic (D31, extends D17)

A fixed, logged pipeline. No weighted-sum score until two validated outcomes and cost data exist (D17).
Each step's output is shown and traceable.

| Step | Logic | Source |
| --- | --- | --- |
| 1 Characterise | Habitat, oil (ADIOS), oiling class, exposure, access, season, sensitivity | Inputs, oil library, SCAT |
| 2 Hard constraints | Rules: ineligible options removed with the reason | Knowledge tables (F2) |
| 3 Do no harm | Options with field evidence of harm in this habitat removed or flagged (e.g. sediment removal in marsh) | `evidence_effect` |
| 4 Benefit vs natural recovery | Validated predictions per option minus natural recovery, paired, with 90% interval; experimental ones flagged | Registry (F3) |
| 5 Endpoint and time | Time to cleanup endpoint (e.g. DWH marsh endpoints, Michel et al. 2013), where a model supports it | Endpoint table |
| 6 Trade-offs | Waste volume, access, workforce, cost class; shown, not scored, until sourced cost data exist | Literature, Jaison |
| 7 Recommendation | Ordered: allowed and evidence of benefit; allowed, no evidence; natural recovery with monitoring; excluded | Steps 2-6 |
| 8 Report | Every number with source, model id, interval, scope flag | Pipeline log |

The logic follows net environmental benefit analysis (each option judged against natural recovery) and
keeps rules and evidence side by side (D13).

### F10 Adaptive monitoring (M9)

Monitoring data from a site update the prediction (Bayesian update of the baseline residual and, where
calibrated, process parameters). **Gate:** shown on a held-out DWH time series that updating narrows the
interval without losing coverage.

### F11 Integrated validation (M10)

- Historical replay, blinded: DWH segments and the sourced historical cases (DWH-01..05, EVOS-01; others
  only when sourced). Compare against documented decisions and, where available, outcomes; report
  agreement against the always-active baseline.
- Human expert panel review of 10 recommendation reports.
- Per-habitat scope statement and limits.
**Gate:** results reported including failures; Jaison signs off.

### F12 Release v4.0

Model cards for every registered model, user guide, limitations page, a versioned release on a branch Jaison
names. Push only when asked, and only after D29.

---

## Order and dependencies

| Order | Activity | Depends on | Jaison's part |
| --- | --- | --- | --- |
| 1 | R1 ranking defect | - | Review before/after |
| 2 | R3 diagnostic, then plan for C1b/B1b | - | Approve D27 |
| 3 | R2 (after D26), R4, R5, R6 | R1, R3 | Decide D26 |
| 4 | R7, R8 | - | Decide D29 |
| 5 | F1 parked reviews and decisions | Track R | All of it |
| 6 | F2 knowledge tables, F3 interface and registry | F1 | Review tables |
| 7 | F4 schema | F1 (D14) | Soil units |
| 8 | F5 process model steps 1-2, then 3 | F4 | Soil chemistry judgement |
| 9 | F6 treatment records | F4 | Digitisation check |
| 10 | F9 pipeline | F2, F3 | Review logic |
| 11 | F7 second spill, F8 experts | F4; collaborators | Sources, experts |
| 12 | F10, F11, F12 | F5-F9 | Sign-off |

## Proposed decisions (to add to the register)

| ID | Decision | Status |
| --- | --- | --- |
| D25 | Ranking sorted by feasibility tier, then evidence, then utility; ineligible utility = 0 | Proposed |
| D26 | Rule-trained suitability layer leaves the decision path until human scores or field labels exist | Proposed (Jaison) |
| D27 | Composer baseline fixed for the oil double count; option chosen in the R3 plan before C1b/B1b | Proposed |
| D28 | Vegetation curve flagged or withheld for heavily oiled cells (worse than baseline there) | Proposed |
| D29 | Repository visibility and data governance before further pushes | Proposed (Jaison) |
| D30 | Final-system scope by evidence: validated, experimental, rules only, out of scope | Proposed |
| D31 | Decision logic: constraints, do-no-harm, benefit vs natural recovery, trade-offs shown not scored | Proposed |
| -   | D23, D24 revert from "Approved by orchestrator" to Proposed (R6) | Proposed |

## What this plan does not solve

One spill until F7 delivers. No public segment-level cleanup records beyond map figures. No cost data. No
bioavailability measures. Beaches and rocky shores remain rules only. The plan makes these limits visible in
every output instead of removing them.
