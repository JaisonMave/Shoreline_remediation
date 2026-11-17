# Handoff: Shoreline Remediation (14 November 2026, after V5)

**Historical record below. Current branch: `model_v5_1`.** For the 17 November dashboard and recovery-plot corrections, start with [V5.4 recovery-view handoff](V5_4_RECOVERY_VIEW.md), then [plot-first assessment handoff](V5_4_PLOT_FIRST_HANDOFF.md). The older branch, publication status and browser-check statements below describe 14 November, not the current release.

Written for Jaison, a soil scientist new to machine learning. Short sentences; a technical term is explained the first time it appears.

## Start here

- **Working branch:** `model_v4` (not `process-model-audit`, which was the earlier branch).
- **Commits are local. Nothing was pushed.** A git bundle (one file that holds the branch history) is provided to the owner. To bring the work into a clone:
  - `git pull <bundle> model_v4`, or
  - `git fetch <bundle> model_v4:model_v4_v5` (this keeps it beside your own branch).
- **Newest findings:** [`docs/FINDINGS_V5.md`](FINDINGS_V5.md), sections 43-51 (plain summary at the top). Earlier: [`docs/FINDINGS_V4.md`](FINDINGS_V4.md), sections 25-42.
- **Status:** [`docs/ROADMAP_STATUS.md`](ROADMAP_STATUS.md). **Decision register D1-D40 and V5 table:** [`docs/ROADMAP.md`](ROADMAP.md). **Change history:** [`CHANGELOG.md`](../CHANGELOG.md).

## What the tool is, and is not

It is an evidence-led research prototype for screening shoreline oil-spill response options. Its validated numbers are narrow: heavily oiled northern Gulf salt-marsh edge loss within Deepwater Horizon (held out by Louisiana basin), and the decline of the soil PAH sum within Deepwater Horizon (held out by station). Beaches are rules and literature, with one experimental reference curve. It is not an operational response tool, not a cross-spill validation, not a cost optimiser. "No option is shown to beat natural recovery; monitor" is a valid output.

## What changed in V5 (ten bullets)

1. Your attestation that you checked all 144 literature rows against the PDFs is recorded (D33). It is your statement, not an independent check.
2. The original F8 two-study rule is back (D34). The two "harm" verdicts for hot-water washing are gone; the caution now comes from sourced NOAA habitat ratings. A sign defect in row B023 was fixed; no verdict changed.
3. The report can now say "insufficient evidence to compare with natural recovery" separately from "no clear difference" (D35).
4. Beaches have a habitat table keyed to ESI shoreline codes and a first screening step using NOAA 2017 ratings (D36). Rule 160 no longer makes hot high-pressure washing eligible on permeable mixed sediment.
5. Oil excess estimated out of sample was tested against "no excess" (D37). **Gate 0.1 failed.**
6. Per-class edge-loss intervals calibrated out of sample were tested (D38). **Gate 0.2 failed.**
7. A sand-beach persistence model was built from DWH SCAT (D39). **Gates B-1 and B-2 failed**; the packaged output is the baseline curve.
8. F11 was rerun: agreement with responders is still 2 of 6 (always-active: 5 of 6). "Method allowed" rose from 264 to 320 of 400, but allowing everything scores 400 of 400, so it shows no skill.
9. The dashboard was re-based on the decision pipeline; the made-up uncertainty band and the constant "decision confidence" are removed (D40). Script-tested only.
10. Open-access papers and Exxon Valdez lingering-oil and hydrocarbon data were downloaded and indexed. None is analysed yet.

## What failed (and what it means)

- **Oil excess (gate 0.1).** Heavily oiled cells lose about 0.5 to 0.8 m/yr more edge on average, but individual 100 m cells vary far more, so adding the oil term does not make single-cell predictions more accurate. The dashboard now shows "no excess" as the per-site number and the excess as a separate average (for your review).
- **Intervals (gate 0.2).** Coverage was outside 80-97% in 3 of 12 groups and the interval did not beat a no-predictor interval in Breton. Do not quote pooled 90% coverage as validation.
- **Sand beach (B-1, B-2).** The model was worse than a curve by starting oiling category in all three states. "Time until no oil observed" is a weak measure: 74% of cleared segments were oiled again, and the result depends on how often a segment was visited.
- **F11.** 2 of 6 agreement is not a performance measure. Responders act by default.

## Open evidence gaps

1. No public segment-level DWH cleanup-treatment records. OR&R 42 shows treated stretches only in map figures; it has not been obtained.
2. No second spill with harmonised oiling, treatment and outcome data.
3. No independent expert-panel responses; AI-proposed rows are not expert elicitation.
4. The composer's oil term did not beat a no-excess baseline; heavy cells are over-predicted when it is used.
5. The process model does not beat the empirical PAH decline curve.
6. Literature rows are AI-extracted and owner-attested, not independently double-checked.
7. OSAT-2/3 and paywalled papers (Short 2004/2007, Li and Boufadel 2010, Hayes and Michel 1999) not obtained.
8. No treatment record for beaches, so persistence cannot be separated from cleanup effort.

## Next steps for Jaison

**Review items**
- Read `docs/FINDINGS_V5.md` top summary and sections 44, 45 and 48 (the three failures).
- Decide the open questions below.

**Dashboard eyeball list** (never seen in a browser; light and dark theme both): landing page (answer card, chips, metric cards); the interval chart zero line and faint marks; option cards; the "Scope and limits" popover; the hatched AI-proposed block in "Detailed tables"; the sand-beach persistence panel; the legacy scenario view side by side; the HTML report download opened in a browser. Start with `streamlit run src/shoreline_remediation/dashboard.py`.

**Spot-check list**
- NOAA rating transcription: `data/knowledge/tables/noaa_response_rating.csv` against NOAA 2017 pages 14, 23, 29, 32, 42.
- Beach literature notes: `data/knowledge/tables/beach_literature_notes.csv` (AI-drafted).
- The rows that change decisions: B005, B006, B019, B023, B024, the Zengel rows, planting, and the 14 condition rows.

**Decisions awaiting you**
- D36 NOAA A-D mapping (now Proposed): accept or change.
- Whether to keep the F8b outcome-keyword precedence and the C011 exclusion (kept in the restore).
- Whether to show "no excess" as the per-site edge-loss number, with the excess as a labelled average (proposal from FINDINGS_V5 44), and whether to update the composer's bias note.
- D40 visual acceptance.

## Proposed next milestones, in order

Each needs a written plan with its gate before anything runs.

1. **Owner review and browser check.** Reason: nothing in V5 has been seen by a person. Gate idea: a list of your corrections, each fixed or declined.
2. **OR&R 42 digitisation (figures 35, 36, 39).** Reason: the only route to treatment effects and the only test of hidden treatment in the edge-loss data. Gate idea: within-block treated-minus-untreated heavy-cell edge loss per basin, reported whatever the result; you check a 10% sample.
3. **Beach outcome redefinition.** Reason: "time to first clear" failed because of re-oiling and visit frequency. Candidates: fraction of surveys oiled per season, or oiling-category trajectory. Gate idea: pre-specify the outcome and the visit-frequency handling before running; hold out by state; beat the category baseline in at least 2 of 3 states.
4. **Exxon Valdez lingering-oil persistence for gravel and mixed beaches** from the downloaded tables (`data/external/evos_lingering_oil/`). Reason: the only open gravel-beach repeat survey in hand. Gate idea: pre-specified persistence outcome, hold out by site group, beat a simple baseline.
5. **Second spill.** Reason: the only way to test transfer beyond one spill. Gate idea: hold out a whole spill; compare with a no-predictor baseline.

## Useful commands

The test count is 327 tests, all passing on 14 Nov 2026 with Python 3.13. Earlier sessions recorded Python 3.11; this run used 3.13.

```bash
python -m pip install -r requirements-analysis.txt
python -m pytest tests
streamlit run src/shoreline_remediation/dashboard.py
python -m validation.v5_p0_oil_excess      # gated 0.1 (already run; deterministic, seed 20261114)
python -m validation.v5_p0_intervals       # gated 0.2
python -m validation.v5_beach_sand         # about 7 minutes; needs bash scripts/download_scat_mobile.sh first
python -m validation.literature_pooling    # restored F8 rule is the default; --rule f8b reproduces F8b
python -m validation.f11_integrated_validation --out-dir results/f11_validation_v5
```

Gated analyses were run once and not rerun after the session was interrupted twice. Some analyses need local, git-ignored data (DIVER, SCAT, raw photos); see `docs/DATA_ACQUISITION.md`. Do not commit restricted data.

## Documentation map

- Scope and decisions: [`docs/F0_F1_SCOPE_AND_DECISIONS.md`](F0_F1_SCOPE_AND_DECISIONS.md), [`docs/ROADMAP.md`](ROADMAP.md)
- V5 plans: [`docs/V5_P0_PLAN.md`](V5_P0_PLAN.md), [`docs/V5_BEACH_SAND_PLAN.md`](V5_BEACH_SAND_PLAN.md); earlier `docs/F2_F3_PLAN.md` to `docs/F11_INTEGRATED_VALIDATION_PLAN.md`
- Findings: [`docs/FINDINGS_V5.md`](FINDINGS_V5.md), [`docs/FINDINGS_V4.md`](FINDINGS_V4.md), [`docs/REVIEW_NOTES.md`](REVIEW_NOTES.md)
- Data: [`docs/DATA_CATALOGUE.md`](DATA_CATALOGUE.md), [`docs/VARIABLE_DICTIONARY.md`](VARIABLE_DICTIONARY.md) (the new V5 data and variables are not yet catalogued)
- Literature: `docs/reference/REFERENCE_INDEX.csv`, [`docs/LITERATURE_TO_DOWNLOAD.md`](LITERATURE_TO_DOWNLOAD.md)
- Decision pipeline: `src/shoreline_remediation/decision_pipeline.py`; beach model: `beach_model.py`; habitat table: `habitat.py`
- Results: `results/v5_p0/`, `results/v5_beach/`, `results/f8_pooling/v3_original_rule/`, `results/f11_validation_v5/` (v4 outputs kept beside them)
- Model states: `models/registry.json`

This handoff is a concise guide, not a replacement for the plans, results, decision register or sources linked above.
