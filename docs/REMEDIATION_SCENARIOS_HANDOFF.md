# Remediation scenarios: session handoff

Plan: `docs/CLAUDE_REMEDIATION_SCENARIOS_PLAN.md`. Branch `codex/scenario-prediction-plan`.
Earlier projection programme: `docs/PROJECTION_HANDOFF.md` (complete; its results are unchanged by this work).

| Plan section | Status |
| --- | --- |
| 1. Technique-by-outcome inventory | **Complete** (21 Nov 2026, Session R1). Drives the technique selector since R3 |
| 2. Manual removal against natural recovery, three outcomes | **Complete**: contract (R2), shown in the Assessment (R3) |
| 3. User-defined what-if mode | **Complete for all three outcomes**: retreat (R4, replay R5), vegetation cover (R6) and soil tPAH (R7), each with dashboard download and CLI replay |
| 4. Validation protocol for process and statistical workflows | R9 protocol, source audit and matched historical benchmarks complete. Independent treatment-effect validation awaits new data. |
| 5. Assessment plots | Historical panels R3. All three single-technique futures, differences and PNG/SVG exports delivered through R8. A second intervention overlaid on the same dashboard figure remains a design option. |
| 6. Integration, contract versioning, full verification | Version-2 JSON and CSV replay R5–R7. R10 adds optional figure replay and checks the integrated branch. See verification below. |

## Session R1 (21 Nov 2026): section 1 inventory. COMPLETE

### Starting state
- HEAD `6842911` ("Add Bay Jimmy future-scenario panel to the Assessment view").
- The owner's untracked items were left untouched: `.vscode/`, `AGENTS.md` (same content as `CLAUDE.md`),
  `docs/CLAUDE_REMEDIATION_SCENARIOS_PLAN.md`, `results/projection_baseline_session6/`.

### What was built
`src/shoreline_remediation/projections/inventory.py` (`technique-endpoint-inventory/1`) is a pure adapter with no Streamlit
dependency and no decision authority. `build_inventory(report)` accepts the `DecisionReport` returned by `run_decision()`, or its
dict. It returns one `InventoryRow` for each report option and each endpoint (`total_vegetation_cover`, `soil_tpah`,
`cumulative_shoreline_retreat`).

- **The report is the source of eligibility.** The adapter takes options from `report.options` and keeps no list of its own. It
  copies the category, its label and reason, the rule verdict and ID, do-no-harm, harm flags, condition lines, exclusion reasons,
  evidence state and source IDs verbatim. A test confirms that it does not modify the report.
- **Existing rules:** `comparison.conditions_state` sets the conditions state, and unknown never counts as met.
  `comparison.compare` admits field contrasts. Prerequisites come from `Estimate.prerequisite` in the comparison layer. A test
  checks that these prerequisites equal `decision_pipeline._PREREQUISITE`.
- **Existing loaders:** observed support (dates and n per group) is read through `runner.observed_record`,
  `evidence.vegetation_observed` and `evidence.tpah_observed`, using a validated `observed_record/1` spec. Gap text reuses
  `catalogue.GAPS` constants and the mechanical-plot ineligibility note.
- **Reference:** each endpoint has exactly one natural-recovery reference row, `natural_attenuation`. If a report lacks that
  option, the reference row is taken from the report's `natural_recovery` block.
- **Site scope:** plot evidence applies only to the worked-example cell `8018_32612`, which maps to `bay_jimmy_zengel_plots`.
  The cell and the plots are different spatial units, as noted in the catalogue. Scope also requires `salt_marsh` and `Heavy`.
  Rocky and mangrove reports return `catalogue.UNSUPPORTED_HABITATS` reasons. A typed marsh with no linked site returns
  "no site evidence".
- **`what_if_allowed`:** this flag is permission only; plan section 3 is not implemented. Exploration is refused when an option
  is excluded, fails do-no-harm, has an excluded prerequisite, has unmet conditions, or has unknown conditions. Manual removal is
  permitted because the pipeline recommends it. Its unknown trampling condition stays attached to the arm in `what_if_reason`
  and `unresolved_conditions`.
- **Availability vocabulary:** `observed_and_contrast`, `observed`, `context_only` (only off-endpoint or different-comparator
  evidence), `evidence_gap` and `out_of_scope`. The `admissible_outputs` field uses `catalogue.RECORD_TYPES` keys.

### 16-by-3 coverage: committed Bay Jimmy fixture (`results/projection_baseline/bay_jimmy_mapped.report.json`)

The live report reproduces this table exactly (`test_live_report_reconciles_with_the_fixture`, `n_draws=500`).

| Option | Report category | Vegetation cover (%) | Soil tPAH (mg/kg) | Cumulative retreat (m) | What-if permitted |
| --- | --- | --- | --- | --- | --- |
| `planting (after mechanical cleanup)` | conditional | context only | gap | context only | no |
| `manual_removal` | recommended | observed + field contrast | observed | observed | yes |
| `passive_sorbents` | insufficient_evidence | gap | gap | gap | yes |
| `bioremediation` | insufficient_evidence | gap | gap | gap | no |
| `low_pressure_flushing` | no_demonstrated_benefit | gap | gap | gap | no |
| `surface_washing_agents` | no_demonstrated_benefit | gap | gap | gap | no |
| `vacuum_removal` | insufficient_evidence | gap | gap | gap | no |
| `vegetation_cutting` | no_demonstrated_benefit | gap | gap | gap | no |
| `natural_attenuation` (reference) | natural_recovery_monitoring | observed | observed | observed | no (reference) |
| `solidifiers` | excluded | gap | gap | gap | no |
| `low_pressure_heated_flushing` | excluded | gap | gap | gap | no |
| `mechanical_removal` | excluded | observed + field contrast (context only) | observed (2012 only; context only) | context only | no |
| `sediment_relocation` | excluded | gap | gap | gap | no |
| `high_pressure_heated_washing` | excluded | gap | gap | gap | no |
| `high_pressure_washing` | excluded | gap | gap | gap | no |
| `sediment_mixing` | excluded | gap | gap | gap | no |

Supporting values, each read through the existing loaders:
- **Manual removal, vegetation:** observed in Sept 2011 and Sept 2012 (n = 5, 5). The year-2 contrast with untreated oiled plots
  is +34.0 percentage points, with a 90% Welch interval of +19.0 to +49.0 (5 versus 9 plots). The design is observational.
- **Manual removal, tPAH:** observed in Jul–Aug 2011 and Sept 2012 (n = 5, 5; 220 and 101 mg/kg). No contrast is defined.
- **Manual removal, retreat:** observed at 7 surveys from 4 Dec 2010 to 5 Oct 2016 (n = 5). The two Zengel 2022 erosion-rate
  contrasts are in m/yr. They are kept as context only and are not plotted on the cumulative-metres endpoint.
- **Reference (untreated):** cover from 2011 to 2016 (n = 9, then 5); tPAH 260 and 112 mg/kg (n = 9, 9); retreat at 7 surveys
  (n = 9). Admissible outputs: vegetation `experimental_fit`, tPAH `model_reference_index` (DIVER) and retreat
  `conditional_projection`.
- **Planting:** the Spartina contrast is randomised, but it is incremental against mechanically treated, unplanted plots. It is
  a different outcome and comparator, so it is context only. The erosion-rate sequence contrast is also context only.

### Exact conditions, prerequisites and exclusions (identical for all three endpoints)

| Option | Conditions state | Exact condition lines / prerequisite / exclusion | What-if reason |
| --- | --- | --- | --- |
| `planting (after mechanical cleanup)` | unknown | presupposes mechanical_removal (excluded) | Presupposes mechanical_removal, which is excluded for this assessment. An incremental comparison applies only where that prior cleanup is independently documented and the comparator and outcome match. |
| `manual_removal` | not_required | Crews walk on the marsh surface without boards (trampling) -> harms [unknown (ask user)] | Permitted. The trampling condition is carried with the arm as unresolved. |
| `passive_sorbents` | not_required | (none) | Permitted (rule-eligible, no conditions; no evidence, so assumptions only). |
| `bioremediation` | unknown | Oil at the surface, plants present, soil not waterlogged (oxygen available) -> may help [unknown (ask user)] | Conditions not established. |
| `low_pressure_flushing` | unknown | Fresh liquid oil, low pressure, falling tide -> helps [unknown (ask user)]<br>Thick or emulsified oil -> no benefit [unknown (ask user)] | Conditions not established. |
| `surface_washing_agents` | unknown | Applied within 1-2 days of oiling -> helps [unknown (ask user)]<br>Applied later than about a week -> no benefit [unknown (ask user)] | Conditions not established. |
| `vacuum_removal` | unknown | Hard nozzles contact the marsh surface -> harms [unknown (ask user)] | Conditions not established. |
| `vegetation_cutting` | unmet | Autumn or winter (plants dormant) -> less harm [not met by input season]<br>Growing season -> harms [met by input season] | Condition not met: growing season. |
| `natural_attenuation` | not_required | (none) | Reference arm. |
| `mechanical_removal` | unknown | Marsh elevation restored and replanted afterwards -> less harm [unknown (ask user)]<br>Elevation lowered and not restored -> harms [unknown (ask user)]<br>excluded: Hot-water and heavy mechanical methods damage sensitive wetland habitat | Excluded by screening. |
| `solidifiers` | unknown | excluded: Surface-washing agents and solidifiers otherwise ineligible | Excluded by screening. |
| `sediment_relocation` | unknown | excluded: Sediment relocation otherwise ineligible | Excluded by screening. |
| `low_pressure_heated_flushing`, `high_pressure_heated_washing`, `high_pressure_washing`, `sediment_mixing` | unknown | excluded: Hot-water and heavy mechanical methods damage sensitive wetland habitat | Excluded by screening. |

### Evidence gaps (as the rows state them)
- **No-demonstrated-benefit options:** each row gives the screening rationale. A lack of demonstrated benefit supplies no
  numerical effect size. Each row also states the endpoint-specific evidence needed (`inventory.NEEDED`).
- **Insufficient-evidence options:** each row states the evidence needed for that endpoint. None of these options has Bay Jimmy
  plots.
- **Manual removal:** future cover is not projected (`VEG_FUTURE_GAP`). No treatment-specific future PAH decline is available
  (`PAH_TREATMENT_GAP`, two dates only). No treatment-specific retreat rate or cumulative-retreat contrast exists.
- **Mechanical removal:** no plot has the 4 Dec 2010 retreat origin. Its tPAH data cover 2012 only. All of its data are
  historical context and cannot be used as a prospective control.
- **All rows:** the shared-plot overlap between Zengel 2015 and Zengel 2022 is recorded once, in `Inventory.shared_plots_note`.

### Files
- New: `src/shoreline_remediation/projections/inventory.py`, `tests/test_remediation_inventory.py` and this handoff.
- Edited: `docs/PROJECTION_HANDOFF.md` (one pointer line). No production module, data file or frozen reference was changed.

### Verification (see the end of this section for exact counts)
- `python -m pytest -q tests/test_remediation_inventory.py`: **21 passed, 0 failed, 0 skipped**.
- `python -m pytest -q tests/test_comparison.py tests/test_projections.py tests/test_projections_rate.py tests/test_v54_results.py tests/test_recovery_trajectories.py`:
  **153 passed, 0 failed, 0 skipped**.
- These commands ran in Git Bash, where `pdftotext` (xpdf 4.06, `C:\Program Files\Git\ucrt64\bin`) is on PATH:
  - `python -m pytest -q tests/test_recovery_trajectories.py tests/test_recovery_view.py tests/test_comparison.py tests/test_v5_1_governance.py`:
    **112 passed, 1 failed, 0 skipped**.
  - `python -m pytest -q tests/test_v54_shell.py tests/test_v54_results.py tests/test_decision_board.py`: **58 passed, 0 failed, 0 skipped**.
  - `python -m pytest -q tests`: 890 collected, **886 passed, 4 failed, 0 skipped** (175 s).
- **The failures were not caused by this session.** No data file, knowledge table or production module was edited.
  - `test_data_catalogue::test_every_data_file_is_catalogued_and_unchanged` and `test_p5_demo::test_model_card_has_provenance`
    are the known `core.autocrlf` failures recorded in Session 1 of `docs/PROJECTION_HANDOFF.md`.
  - `test_habitat::test_transcription_matches_the_pdf_text` and
    `test_v5_1_governance::test_noaa_transcription_matches_the_source_pdf_text` were *skipped* in Session 1 ("pdftotext not
    installed"). Under PowerShell's PATH they still skip, which this session rechecked. Under Git Bash, xpdf's `pdftotext` is
    found and the checks run and fail. The NOAA check matches 63 of 126 rows. Most failures are `method_not_found_on_page` (for
    example, 3A Sand Beaches on p. 23 extracts empty ratings), and the rest are `MISMATCH` (1A 1, 5 10, 6A 2, 8A 1).
  - This is consistent with a text-layout difference between xpdf and the extractor the check was written for. It has not
    been shown to be a transcription error. The NOAA tables keep their "Proposed" status and still need human source
    verification (CLAUDE.md). It is an open issue for the owner, not a result of this work.

### Known limitations
- Coverage is for the Bay Jimmy worked example only. Other sites need entries in `OPTION_PLOT_GROUPS` and `REPORT_CELL_SITES`
  backed by documented evidence.
- `what_if_allowed` is a permission flag. Plan section 3 still has to apply the "defensible starting observation" test for each
  endpoint.
- `experimental_fit` is listed as admissible for any group with vegetation observations. The manual group has two surveys only,
  so any fit must borrow the untreated rate and label that assumption (see `recovery_fit/1`).
- The UI does not consume the inventory yet. No browser check was made.

## Session R2 work order (completed below)

1. Check branch, HEAD and status, then read this file.
2. Add a pure function, for example `projections/slice.py::manual_vs_natural(inventory)`. Its input is the rows for
   `inventory.cell("manual_removal", e)` and `inventory.reference(e)`, and it must return nothing unless both are present and
   `what_if_allowed` or `admissible_outputs` permits. Each endpoint returns tidy records in the `catalogue.RECORD_TYPES`
   vocabulary, with units, dates, n, record class, evidence ID and a limitations line:
   - **Vegetation:** observed group means of both groups from `evidence.vegetation_observed`, plus the year-2 `field_contrast`
     from the existing `field_contrast/1` path (`examples/projections/bay_jimmy_veg_contrast_year2.json`). Expected values are
     +34.0 points with an interval of 18.96 to 49.04, and n = 5 versus 9. Keep the planting Spartina contrast on its own
     comparator.
   - **tPAH:** observed values for both groups from `evidence.tpah_observed`: 260 and 112 mg/kg untreated, 220 and 101 mg/kg
     manual. Show the DIVER heavy-class index from `evidence.diver_index` as a separately labelled `model_reference_index`.
     Attach `PAH_TREATMENT_GAP` as the future-rate reason without hiding the measurements.
   - **Retreat:** observed values for both groups from `runner.observed_record` on the common 4 Dec 2010 origin, reusing the
     existing untreated rate explorer. Report the Zengel 2022 erosion-rate contrasts as a separate m/yr series with their time
     spans.
   - Keep the historical treatment timing (2010–2011 cleanup) separate from any hypothetical future intervention date in the
     record fields. Put `SHARED_PLOTS_NOTE` in the slice once.
3. Tests: the three expected value sets above. The slice must not appear for an excluded option (mechanical), for planting, or
   for rocky or mangrove reports. The tPAH future reason must be present while observed rows remain. No pre-2010 or synthetic
   rows. The report must be unchanged.
4. Rerun `tests/test_remediation_inventory.py`, the five-file command above and both regression commands, then record counts
   here. Wire the slice into `ui_future_scenarios.py` (plan section 5) only after this contract passes.

## Session R2 historical comparison

`projections.slice.manual_vs_natural(build_inventory(report))` returns three historical endpoint groups or a typed
`Unsupported` result. The contract uses the full record. The future intervention date is null. The manual treatment
month is December 2010, as documented in `docs/V5_4_RECOVERY_VIEW.md`. The broader cleanup campaign also included
mechanical work in 2011. The unknown trampling condition travels with the result.

| Endpoint | Checked result |
| --- | --- |
| Total cover | Plot-level manual means of 21.8% and 51.8%. The published year-two means of 52% and 18% yield +34 percentage points, 90% Welch interval 18.96 to 49.04, n = 5 and 9. |
| Soil tPAH | Untreated 260 and 112 mg/kg, manual 220 and 101 mg/kg. The treatment-specific future-rate gap accompanies the measurements. A separate DIVER reference contains 15 index points, station count, campaign support and consulted evidence IDs. |
| Cumulative retreat | Seven common dates from 4 Dec 2010 to 5 Oct 2016. The final means are 11.441917 m manual and 12.125645 m untreated. Separate aerial estimates of the difference in pre-spill-adjusted erosion rates are −0.634733 m/yr (2010–2012) and −0.129711 m/yr (2012–2018). |

Files for R2: new `src/shoreline_remediation/projections/slice.py` and `tests/test_remediation_slice.py`. Updated
`src/shoreline_remediation/projections/inventory.py`, `src/shoreline_remediation/projections/catalogue.py` and this
handoff. The inventory and comparison now share the observation loaders and validated spec builder. A separate evidence
ID identifies the aerial-rate worksheet, `DSAS lumped`, in the same workbook as the field-position measurements.

Verification in PowerShell:

- `python -m pytest -q tests/test_remediation_slice.py tests/test_remediation_inventory.py` — 31 collected, 31 passed.
- `python -m pytest -q tests/test_comparison.py tests/test_projections.py tests/test_projections_rate.py tests/test_v54_results.py tests/test_recovery_trajectories.py tests/test_recovery_view.py tests/test_v5_1_governance.py tests/test_v54_shell.py tests/test_decision_board.py` — 248 collected, 247 passed, 1 skipped. This runs the union of the requested three overlapping regression selections. Streamlit AppTests required local loopback access. No full-suite or browser run for this data-only session.

Next implementation task for Claude Code: extend the existing Assessment expander to render this historical comparison
for Bay Jimmy. Put published cover differences, the regional PAH index and aerial-rate contrasts on their own scales.
Retain the untreated retreat explorer for conditional futures. Test the manual selection, unsupported cases, desktop and
mobile layouts before adding prospective treatment assumptions. The outstanding Git Bash PDF verification from R1 is open.

## Session R3 (21 Nov 2026): manual removal in the Assessment panel. COMPLETE

Home → **Use Bay Jimmy** → Run assessment → **Explore future scenarios**. A technique selector at the top of the panel is
built from the live report through `inventory.build_inventory`. It lists all 16 report options, puts natural recovery first
(the default) and shows the category label beside each option.

- **Manual removal** calls the tested `slice.manual_vs_natural`. It shows three panels side by side on desktop, stacked at
  390 px:
  - **Cover (%):** both arms' September survey means. The year-two difference is +34.0 points (90% Welch interval +19.0 to
    +49.0; 5 vs 9 plots; published means 52% vs 18%), and the panel states that the design is observational.
  - **Soil tPAH (mg/kg):** both arms in Jul–Aug 2011 and Sep 2012, with a note that no treatment-specific future rate is
    available. The DIVER heavy-class index is behind a toggle, on its own scale, and labelled as a model reference rather than
    a plot measurement.
  - **Cumulative retreat since 4 Dec 2010 (m):** both arms at 7 surveys. The final values are 11.44 m (manual, n = 5) and
    12.13 m (untreated, n = 9). The aerial m/yr contrasts are in a separate table with 90% intervals and n.
  - **Every point** is a group mean with 90% interval bars. Tooltips give the survey, the n and the interval method. The two
    arms are drawn ±25 days apart so neither hides the other, and the caption says so.
  - **Also shown:** the shared-plots note, the unresolved trampling condition, a toggle for a table of the values, and
    JSON/CSV downloads of the comparison.
- **Other techniques** show their category, reason, prerequisite, condition lines and a per-outcome table explaining why no
  comparison is drawn. Excluded methods state that they are not offered as future interventions.
- **The conditional retreat explorer is unchanged in its logic, keys and text.** Its chart now has a legend ("Observed group
  mean (untreated plots)" as teal points; "Assumed-rate scenario (not a forecast)" as a dashed blue line) and a dotted rule at
  the last survey.
- `ui_results.py` now passes the report to `ui_future_scenarios.render(report)`. The gating is unchanged (Bay Jimmy cell,
  in scope, heavy oiling only).

Files: `src/shoreline_remediation/ui_future_scenarios.py`, `src/shoreline_remediation/ui_results.py` (one line),
`tests/test_future_scenarios_view.py` (new; chart data and labels without rendering), `tests/test_v54_results.py` (4 new
AppTests), `README.md` and this handoff.

### Verification
Test commands, run in Git Bash:
- `python -m pytest -q tests/test_future_scenarios_view.py tests/test_remediation_slice.py tests/test_remediation_inventory.py tests/test_projections.py tests/test_projections_rate.py`:
  **115 passed, 0 failed, 0 skipped**.
- `python -m pytest -q tests/test_v54_shell.py tests/test_v54_results.py tests/test_decision_board.py`: **62 passed, 0 failed, 0 skipped**.
  This includes the new manual-selection, blocked-technique and rocky/mangrove no-panel AppTests, and the unchanged explorer
  test.
- `python -m pytest -q tests/test_recovery_trajectories.py tests/test_recovery_view.py tests/test_comparison.py tests/test_v5_1_governance.py`:
  **112 passed, 1 failed**. The failure is the Git Bash-only NOAA PDF check recorded in R1. It still skips under PowerShell.
- The full suite was not rerun this session.

Baseline replay:
- Command: `python -W ignore scripts/capture_projection_baseline.py --out <scratch dir>`.
- All four decision reports reproduce the frozen Session 1 hashes: Bay Jimmy `4da6fa96`, typed marsh `32926391`, rocky 1A
  `d6d10541`, mangrove `658ec338`.
- Visible controls are identical for rocky, mangrove and typed marsh. Bay Jimmy differs only by the "Explore future scenarios"
  expander, which `6842911` added intentionally. The capture records the panel collapsed.

Browser run in Chromium (Playwright, headless, local `streamlit run`) at 1440×1000 and 390×844:
- **Workflow:** Home → Use Bay Jimmy → Run → open the panel, then select manual removal from the keyboard (desktop) or by
  pointer (mobile).
- **Content:** the contrast, interval, retreat values, PAH gap, aerial table, DIVER toggle and the unchanged 31.06 m explorer
  value were all present.
- **Downloads:** the JSON (option `manual_removal`, three endpoints) and the CSV (31 rows) both downloaded.
- **Planting:** selecting it shows "Presupposes mechanical removal, which is excluded here".
- **Layout and errors:** 0 px horizontal overflow and no page errors at either width.
- **Screenshots** were reviewed. Clipped legend labels, a repeated tPAH year tick, a too-wide aerial table on mobile and a
  clipped scenario legend were found and fixed before the final run.
- No contrast or screen-reader audit was made beyond the chart `alt` text, the tabular alternative and keyboard selection.

### Known limitations
- The panel appears only for the Bay Jimmy worked-example cell. Other techniques get status text, not charts.
- There is no effect plot, no PNG/SVG export and no what-if arm yet (plan sections 3 and 5).
- The DIVER index toggle lives inside the tPAH column. On mobile it sits between the tPAH and retreat panels.

## Next task (Session R4): plan section 3, a user-defined what-if for the retreat endpoint only

1. Check branch, HEAD and status, then read this file.
2. Add a pure two-arm function for retreat, for example `projection.project_two_arms`. It takes the untreated anchor (last
   survey 5 Oct 2016, 12.13 m) and the baseline rate, plus an explicit `user_assumption` for intervention date, duration and
   Δrate (m/yr, either sign allowed). It integrates piecewise in elapsed years.
3. Expected behaviour: both arms are identical before the intervention date, and Δ = 0 reproduces the baseline exactly. An
   off-grid change date must integrate correctly, and annual and monthly cadences must agree at shared dates. Exports must
   flag the user-supplied parameters. The function must stay outside ranking and recommendations.
4. Offer it only for options with `what_if_allowed` (manual removal and passive sorbents in this fixture). Leave the
   coefficient blank until the user enters one; do not fill in a default effect.

## Session R4 (21 Nov 2026): user-defined retreat what-if. COMPLETE (retreat only)

Start state: HEAD `6842911`, and the R1–R3 work is uncommitted (listed in `git status`). `AGENTS.md` differs from `CLAUDE.md`
only in its title and the words "Codex sessions"; the rules are the same.

### What was built
**`src/shoreline_remediation/projections/whatif.py`** (`retreat-treatment-what-if/1`) is pure, with no Streamlit dependency.
- **Starting point:** both arms start from the same observed anchor, the untreated plots on 5 Oct 2016 (12.13 m, n = 9).
- **Natural-recovery arm:** this is `rate_continuation/1`. It reuses `projection.rate_segments`, `additional_retreat` and
  `sample_dates`, and a test shows it equals `projection.project` exactly.
- **Treatment arm:** the natural arm plus `delta × overlap([start, end], [anchor, t])` in calendar decimal years. The baseline
  rate schedule, including a mid-period change, is carried through both arms. After the effect ends the baseline rate
  resumes, and the distance gained or lost is kept.
- **Sampling:** the intervention start and the end of the effect are sampled exactly, even when they fall between regular
  sample dates.
- **Blank versus zero:** a blank change (`None`) gives no treatment curve. An explicit 0 gives two identical curves.
- **Invalid inputs:** these give a plain reason and no curve:
  - a start on or before the last survey;
  - an effect end on or before the start;
  - a start on or after the scenario end;
  - a non-finite change;
  - a change that makes the treated rate negative (the shoreline would advance seaward, which this what-if does not
    represent).
- **Exports:** `export_rows` holds the observed surveys on their actual dates (2010-12-04 … 2016-10-05), the shared anchor
  rows and both arms. Treatment rows are labelled `status_label = "User-defined what-if"` and `origin = user_assumption`.
  `RetreatEffect.as_dict()` records `measured: false`.

**Panel (`ui_future_scenarios.py`, same expander and navigation):**
- **Eligibility:** the what-if block sits inside the existing conditional-retreat explorer. It reads eligibility from the live
  inventory (`what_if_allowed` for `cumulative_shoreline_retreat`).
  - **Manual removal:** allowed. It shows the unresolved trampling condition and states that no measured future retreat
    effect exists; the historical plots and aerial differences are not applied.
  - **Passive sorbents:** allowed. It states: "The repository has no measured treatment effect of passive sorbents on shoreline
    retreat."
  - **Planting, bioremediation and other blocked techniques:** they show "No what-if for …" with the inventory's reason and no
    inputs.
  - **Natural recovery (reference):** it asks the user to choose a technique.
- **Inputs:** intervention start, effect end, and a signed change in m/year. The change starts blank, with the placeholder
  "Blank: no treatment curve". A caption beside it reads "Negative = slower retreat. Positive = faster retreat."
- **Switching techniques:** the selector's `on_change` callback resets the three what-if keys to their defaults. It assigns
  values rather than deleting keys, because the browser test showed that deleted keys let the browser resend the old value.
- **Chart:** it is drawn from the same `export_rows` table as the CSV download. It has these marks:
  - survey points labelled "Surveys";
  - a pale dashed natural-recovery line and a teal dotted what-if line, with direct end labels;
  - a shaded and labelled intervention band;
  - a "Last survey" rule;
  - the title "User-defined what-if: <technique>".

  There is no legend. Direct labels keep the plot at full height at 390 px; a legend squeezed the plot to about 20 px.
- **Text and downloads:** an end-date sentence reads, for example, "By 01 Jan 2050: natural recovery 59.66 m; treatment
  scenario 54.66 m. 5.00 m less cumulative retreat under your assumption." There are "Download what-if JSON" and "Download
  what-if CSV" buttons. The existing scenario-inputs JSON and projection CSV are unchanged and still replayable.
- **Recommendations:** a what-if never changes the assessment outcome; the AppTest compares the outcome HTML before and after.

Files:
- New: `src/shoreline_remediation/projections/whatif.py` and `tests/test_retreat_whatif.py` (15 independent arithmetic tests).
- Edited: `src/shoreline_remediation/ui_future_scenarios.py`, `tests/test_future_scenarios_view.py` (chart equals export rows,
  labels, no legend) and `tests/test_v54_results.py` (4 new AppTests: blank, signed and zero values for manual removal; passive
  sorbents; blocked planting and bioremediation; clearing on technique change).
- This handoff.

### Verification (Git Bash, 21 Nov 2026)
- **A:** `python -m pytest -q tests/test_retreat_whatif.py tests/test_future_scenarios_view.py tests/test_remediation_slice.py tests/test_remediation_inventory.py tests/test_projections.py tests/test_projections_rate.py`:
  **132 passed, 0 failed, 0 skipped**.
- **B:** `python -m pytest -q tests/test_v54_shell.py tests/test_v54_results.py tests/test_decision_board.py`: **66 passed, 0 failed, 0 skipped** on the final code (rerun after the last caption edit).
- **C:** `python -m pytest -q tests/test_recovery_trajectories.py tests/test_recovery_view.py tests/test_comparison.py tests/test_v5_1_governance.py`:
  **112 passed, 1 failed** (`test_noaa_transcription_matches_the_source_pdf_text`, the NOAA PDF issue below).
- **D:** `python -W ignore scripts/capture_projection_baseline.py --out <scratch dir>`. All four production decision reports
  keep their frozen hashes: Bay Jimmy `4da6fa96`, typed marsh `32926391`, rocky 1A `d6d10541`, mangrove `658ec338`, with 0 app
  exceptions. Visible controls are identical for rocky, mangrove and typed marsh. Bay Jimmy differs only by the existing
  "Explore future scenarios" expander (added in `6842911`); the capture keeps the panel collapsed.
- **E:** `python -m pytest -q tests`: 932 collected, **928 passed, 4 failed, 0 skipped** (224 s). All four failures are the
  known environment failures below; none is new.

**Worked example (independent arithmetic):** baseline 1.43 m/yr, change −0.50 m/yr from 1 Jan 2030 to 1 Jan 2040.
- The arms are identical through 1 Jan 2030.
- The difference is −5.00 m at 2040 and still −5.00 m at 2050 (exact to 1e-12).
- The natural arm reaches 59.66 m by 2050, and the treatment arm 54.66 m.
- Other tests cover: blank (no curve), zero (identical curves), +0.30 m/yr (+1.50 m over 5 years), a baseline rate change in
  2035 during treatment (−2.50 m in 2035, −5.00 m from 2040, treated rate 1.69 m/yr), off-grid dates (15 Jul 2030 to 20 Mar
  2033), monthly against annual (identical at every shared date), truncation at the scenario end, and five invalid inputs.

**Browser (Chromium via Playwright, headless local `streamlit run`, 1440×1000 and 390×844):**
- **Manual removal:**
  - It starts blank with no curve, and the trampling caveat and sign text are visible.
  - Dates are typed into the date spinbuttons from the keyboard. With 2030 to 2040 and −0.5, the panel shows "5.00 m less" with
    natural recovery 59.66 m and treatment scenario 54.66 m.
  - The downloaded CSV has the same 2050 values (59.66, 54.66, −5.00), the seven actual survey dates and the "User-defined
    what-if" labels. The JSON has the same label, `origin: user_assumption` and a difference of −5.0.
  - Entering 0 shows "coincide".
- **Passive sorbents:** switching to it after entering −0.5 cleared the input and removed the what-if text. The no-measured-
  effect statement is shown, and +0.3 gives "more".
- **Planting:** blocked, with no inputs.
- **Layout and errors:** 0 px horizontal overflow and no page errors at either width. The server log has no warning about any
  `bj_` widget.
- **Screenshots reviewed:** two layout faults were found and fixed before the final run. A legend and two-line title squeezed
  the plot, and an absolutely positioned label shrank it further.
- **Not covered:** the last caption edit (the manual-only sentence about historical plots) came after the final browser run.
  It is covered by test B only.

### Known issues (unchanged by this session)
- **NOAA PDF check (R1):** in Git Bash, xpdf `pdftotext` 4.06 is on PATH, so
  `test_v5_1_governance::test_noaa_transcription_matches_the_source_pdf_text` and
  `test_habitat::test_transcription_matches_the_pdf_text` run and fail. 63 of 126 NOAA rows match; most failures are
  `method_not_found_on_page`. Under PowerShell both tests skip. This looks like a difference in the extractor's text layout and
  has not been shown to be a transcription error. The NOAA tables stay "Proposed" until a person verifies them against the
  source.
- **Line endings:** `test_data_catalogue::test_every_data_file_is_catalogued_and_unchanged` and
  `test_p5_demo::test_model_card_has_provenance` fail under `core.autocrlf=true`, the known CRLF issue.
- **`site_habitat` warning:** the server logs a Session State warning for the `site_habitat` widget. The code is identical in
  the committed `site_view.py:969`; it predates this work and was not changed.

### Limitations
- Retreat only. Cover and tPAH what-ifs (plan section 3) are not implemented.
- No PNG/SVG export and no effect plot (plan section 5).
- The what-if JSON is not yet replayable through the projections CLI; it records the full inputs and rows. Section 6 should
  version the multi-arm contract.

## Next task (Session R5)
Version the two-arm scenario contract so the what-if JSON replays through `python -m src.shoreline_remediation.projections run`.
Use a `shoreline-projection-spec/2` with optional `treatment_effect` (start, end, delta, origin `user_assumption`), and keep
`/1` files replayable. Test it by replaying the downloaded what-if JSON and comparing every CSV row at export precision. Then
decide with the owner whether to add the cover what-if, a bounded and time-limited cover shift in percentage points held
within 0–100%.

## Session R5 (21 Nov 2026): replay the dashboard what-if through the projections CLI. COMPLETE (retreat only)

Start state: HEAD `6842911`; the R1–R4 work is uncommitted and was preserved. Nothing was committed.

### What was built
**`shoreline-projection-spec/2`** (in `catalogue.py` and `spec.py`) is a version-2 scenario with model `retreat_whatif/1`, for
the cumulative-retreat endpoint only. It contains:
- the version-1 retreat fields and the baseline rate schedule (`retreat_rate`, plus an optional `rate_change_date` and
  `changed_retreat_rate`);
- `technique`, the report option key;
- `assessment_context`, which records how to re-run the assessment: `entry: mapped_site`, `cell`, `habitat`, `oil`, `season`,
  `n_draws` and `site_sha256`;
- an optional `treatment_effect`: `intervention_start`, `effect_end`, `rate_change` in m/yr, `unit`, `origin:
  user_assumption`, `source`.

How the effect and saved outputs are handled:
- **Missing or null `treatment_effect`:** the run writes the natural-recovery arm only.
- **`rate_change: 0`:** the run writes two arms with identical values.
- **`exported_outputs`:** this is what the page showed (eligibility text, summary, rows). It is parsed but never used as input,
  and it is not part of `to_dict()` or the run ID.
- **Invalid inputs** are refused before anything is written (SpecError):
  - version-2 fields or `retreat_whatif/1` in a version-1 file;
  - an unknown context key or a context entry other than `mapped_site`;
  - a null `rate_change` inside an effect;
  - a unit other than `m/yr`;
  - an origin other than `user_assumption`;
  - a treated rate below zero, or dates in the wrong order.

**One calculation and one export.** `projections/whatif.py` now contains:
- `compute()`, which applies the effect only when the screening row allows a what-if;
- `csv_text()`, the declared precision (`%.6f`, LF line endings);
- `spec_dict_v2()`, `effect_from_spec()`, `screen()` (inventory lookup) and `check_exported()`.

The dashboard panel and `runner._whatif` both call these functions. The what-if JSON download is now the version-2 spec with
`exported_outputs` attached, and the CSV download uses `csv_text`. A signed zero (−0.0) in the difference column is normalised to
0.0. Before this fix, the 2030 row of a negative change exported `-0.000000`.

**Screening on replay.** A new top-level module, `src/shoreline_remediation/assessment_screening.py`, re-runs
`decision_pipeline.run_decision` from the recorded context, the same call as `ui_pipeline.decision_for_site`. It checks the site
values against `site_sha256` and returns the report. `whatif.screen()` then reads the technique's retreat row from the existing
inventory. Eligibility text saved in the download is never consulted.
- **Loading:** the CLI loads the adapter lazily, and only for version-2 files. `runner.run(..., screening=...)` refuses a
  version-2 file that has no resolver.
- **Boundaries kept:** both existing tests still pass unchanged. `projections/*.py` never imports `decision_pipeline`, and only
  `ui_future_scenarios.py` imports `projections`.
- **New runtime test:** a version-2 replay loads the decision engine and never Streamlit; a version-1 run loads neither.
- **Blocked technique** (for example planting, or bioremediation with unknown conditions): exit 3. `manifest.outcome.code` is
  `technique_blocked_by_screening`, and `whatif.csv` contains the observations and the natural arm only.
- **Changed site table or unknown technique:** no treatment curve.

**CLI**
- `validate` prints the re-derived screening. It returns 3 when an effect is present but blocked.
- `run` prints the what-if sentence and warns on stderr if the saved outputs differ from the replay.
- The manifest records the screening (category, `what_if_allowed`, reason, unresolved conditions, pipeline version, seed,
  `n_draws`, outcome), the effect, the anchor, the rates, the summary and `exported_outputs_check`.
- Output-folder protection is unchanged: an existing path gives exit 4 and is left untouched.

### Replay commands (repository root)
```
python -m src.shoreline_remediation.projections validate --scenario bay_jimmy_retreat_whatif.json
python -m src.shoreline_remediation.projections run --scenario bay_jimmy_retreat_whatif.json --output runs/bj_whatif
```
`bay_jimmy_retreat_whatif.json` is the exact file from Bay Jimmy → Run assessment → Explore future scenarios → Download what-if
JSON. The run writes `input.json`, `manifest.json`, `observed.csv` and `whatif.csv`.

### Files
- New: `src/shoreline_remediation/assessment_screening.py` and `tests/test_whatif_replay.py` (18 tests).
- Edited: `projections/catalogue.py` (schema version 2, `retreat_whatif/1`), `projections/spec.py`, `projections/whatif.py`,
  `projections/runner.py`, `projections/__main__.py`, `ui_future_scenarios.py` (shared compute, version-2 download, context)
  and `ui_results.py` (passes the run spec), plus `README.md` and this handoff.

### Verification (Git Bash, 21 Nov 2026)
- **Acceptance with the actual dashboard download:** `tests/test_whatif_replay.py` drives the dashboard with AppTest and records
  the exact bytes the download buttons serve. It replays the JSON with the CLI into a fresh directory, and the replayed
  `whatif.csv` equals the downloaded CSV line for line: 78 lines of dates, series and arm labels, record types and values at
  `%.6f`.
  - **Worked example** (1.43 m/yr; −0.50 m/yr from 1 Jan 2030 to 1 Jan 2040): difference 0.000000 in 2030, −5.000000 in 2040
    and −5.000000 in 2050, or 5.00 m less retreat.
  - **Zero effect:** identical arms, difference 0.000000 throughout.
  - **Baseline rate change to 2.19 m/yr on 1 Jan 2035:** −2.500000 in 2035, −5.000000 in 2040, treated rate 1.690000 m/yr
    in 2037.
  - **Version-1 `bay_jimmy_retreat_2030.json`** reaches 31.06 m with its run ID unchanged.
- **Edited saved result:** the 2050 treatment value set to 50.0 in `exported_outputs`. The replay still writes 54.659470, and
  the manifest flags one differing row and two differing summary values. The run ID equals the unedited file's.
- **Real browser:** in Chromium (Playwright, 1440×1000 and 390×844), the JSON and CSV downloaded at each width were replayed with
  the commands above. The replayed `whatif.csv` was byte-identical to the downloaded CSV at both widths (78 lines). A second run
  into the same folder gave exit 4. All of the R4 journey checks still pass, with 0 px overflow and no page errors.
- **Version-1 baseline:** all nine `examples/projections/*.json` were run before and after the change. Run IDs, statuses,
  `spec_sha256` and every CSV output SHA-256 are identical. PNG and SVG figures were not compared, because figure files can carry
  render metadata. Run IDs are also pinned in `tests/test_whatif_replay.py`.
- **A:** `python -m pytest -q tests/test_whatif_replay.py tests/test_retreat_whatif.py tests/test_future_scenarios_view.py tests/test_remediation_slice.py tests/test_remediation_inventory.py tests/test_projections*.py`:
  **200 passed, 0 failed, 0 skipped**.
- **B:** `python -m pytest -q tests/test_v54_shell.py tests/test_v54_results.py tests/test_decision_board.py`: **66 passed, 0 failed, 0 skipped**.
- **C:** `python -m pytest -q tests/test_recovery_trajectories.py tests/test_recovery_view.py tests/test_comparison.py tests/test_v5_1_governance.py`:
  **112 passed, 1 failed** (`test_noaa_transcription_matches_the_source_pdf_text`, the NOAA PDF issue below).
- **D:** `python -W ignore scripts/capture_projection_baseline.py --out <scratch dir>`: all four production decision reports keep their frozen hashes: Bay Jimmy `4da6fa96`, typed marsh `32926391`, rocky 1A `d6d10541`, mangrove `658ec338`, with 0 app exceptions.
- **E:** `python -m pytest -q tests`: 950 collected, **946 passed, 4 failed, 0 skipped** (257 s). The four failures are the known environment failures listed below; none is new.

### Baseline differences
- **Version-1 runs:** none.
- **Production decision reports:** none (see D).
- **What-if JSON format:** the R4 payload has been replaced by the version-2 spec with `exported_outputs`. No R4 file was ever
  replayable, so nothing that could be replayed is lost.
- **What-if CSV:** values are now written at `%.6f`. In R4 the download used pandas' default full precision.

### Known issues (unchanged)
- **NOAA PDF check:** in Git Bash, xpdf `pdftotext` 4.06 makes `test_v5_1_governance::test_noaa_transcription_matches_the_source_pdf_text`
  and `test_habitat::test_transcription_matches_the_pdf_text` run and fail. 63 of 126 rows match; most failures are
  `method_not_found_on_page`. Under PowerShell both tests skip. This has not been shown to be a transcription error, and the NOAA
  tables stay "Proposed" pending human verification.
- **Line endings:** `test_data_catalogue` and `test_p5_demo` fail under `core.autocrlf=true`.
- **`site_habitat` warning:** the pre-existing Session State warning for this widget, logged by `site_view.py:969`.

### Limitations
- Only the mapped Bay Jimmy cell (`entry: mapped_site`) can be replayed. A typed-site or habitat-level assessment context is
  refused.
- Replay re-runs the decision pipeline. If the knowledge tables or pipeline change, a replay screens against the current
  pipeline, and the manifest records its version.
- Cover and tPAH what-ifs are not implemented.

## Next task (Session R6)
Ask the owner whether to add the cover what-if before writing any code. The R4 plan describes it as a bounded, time-limited
cover shift in percentage points, held within 0–100%, with a stated persistence or fade, applied from a defensible starting
observation. If approved, follow the retreat pattern: a pure function with independent arithmetic tests, spec version 2 with a
`cover_effect`, shared compute and export, and dashboard–CLI replay at export precision. Otherwise, start plan section 5's
remaining items: PNG/SVG export of the what-if figure and the compact effect plot.

## Session R6 (21 Nov 2026): vegetation-cover what-if with day-one replay. COMPLETE

Start state: HEAD `6842911`, and the R1–R5 work is uncommitted and was preserved. The owner approved the cover what-if, which
settles the R6 question. Nothing was committed.

### What was built
**`src/shoreline_remediation/projections/cover.py`** (model `cover_whatif/1`) is pure, with no Streamlit dependency.
- **Anchor:** the last untreated, heavily oiled survey available at as_of, read through the existing loader
  `evidence.vegetation_observed`. For the dashboard cutoff (2016-12-31) this is the September 2016 survey: mean total cover
  70.0%, 5 plots, date precision month. The loader records the survey month as "assumed (survey month not recorded in the
  sources examined)", and the panel shows that basis. The curve starts at the end of the survey month (30 Sep 2016), the date
  from which the loader treats that survey as available. If no survey exists at the cutoff, the reason is shown and no future
  curve is drawn (`Unsupported("no_anchor_observation")` on replay).
- **Baseline:** the arm is labelled "Natural recovery scenario: cover held at the last observed value". The panel adds that
  this is an assumption: cover fell from 92.0% in 2015 to 70.0% in 2016, and no later survey tests any rule.
- **Treatment:** a signed peak change in percentage points, with start < peak < end. The difference rises linearly to the peak
  and returns linearly to zero by the end, so the effect is explicitly temporary.
  - **Calendar convention:** calendar decimal years, the same as the retreat what-if.
  - **Sampling:** the exact start, peak and end dates are always sampled.
  - **Blank and zero:** a blank change draws the baseline only; an entered zero draws two coincident arms.
  - **Bounds:** cover must stay within 0–100%, checked exactly at the peak. The message gives the allowable range, for
    example "between −70.0 and +30.0 percentage points" at a 70.0% baseline.
  - **Peak report:** both cover values and the difference at the peak date.
- **Exports:** `export_rows()` keeps the actual survey dates (`2011-09` … `2016-09`, precision month, with 90% intervals,
  interval method and n), then both arms by date, with units `percent` and `percentage points`.

**Spec version 2 and replay.**
- `catalogue.COVER_WHATIF_MODEL` is added. `spec.py` validates the effect schema for each model: the cover effect needs
  `intervention_start`, `effect_peak`, `effect_end`, `peak_change`, `unit: percentage points` and `origin: user_assumption`.
  `check_scope` loads the anchor and refuses an out-of-range or out-of-order effect before anything is written.
- `runner._cover` writes `observed.csv` and `whatif.csv` with the shared `whatif.csv_text`, and records the baseline rule and
  anchor, the screening and the peak summary in the manifest. It also compares any saved outputs.
- Screening is re-derived on every run through `assessment_screening.reproduce` and the inventory's
  `total_vegetation_cover` row (`whatif.screen` now takes the endpoint). The CLI loads screening for both what-if models.
- Version-1 files and the R5 retreat downloads are unchanged (see Verification).

**Panel.** A new "Future outcome" segmented control in the existing expander switches between Shoreline retreat (the default,
so the retreat flow is unchanged) and Vegetation cover.
- **Cover explorer:** it shows the anchor, the baseline label and a scenario end date.
- **Technique gating:** it uses the live inventory's cover row.
  - **Manual removal:** the field evidence stays visible and is not applied: "+34.0 percentage points … September 2012 (90%
    Welch interval +19.0 to +49.0; 5 manual vs 9 untreated plots; published group means 52% vs 18%). Observational".
    The unresolved trampling condition is shown.
  - **Passive sorbents:** "There is no measured Bay Jimmy cover effect for passive sorbents."
  - **Planting and other blocked techniques:** "No what-if for …" with the reason, and no inputs.
- **Inputs:** the future effect is blank by default. Start, peak, end and the peak change sit beside a sign and
  allowed-range note, and the temporary-effect statement is shown.
- **Switching techniques:** this resets the cover inputs, through the same callback as retreat.
- **Chart:** drawn from the same rows as the CSV, on a 0–100% axis. It shows survey means with 90% interval bars, a "Last
  survey" rule, the pale dashed natural-recovery line and the teal dotted what-if line with direct end labels on opposite
  sides, a shaded effect period, and a "Peak" marker at the exact peak.
- **Downloads:** "Download cover JSON" (a version-2 spec with `exported_outputs`) and "Download cover CSV".

Files:
- New: `projections/cover.py`, `tests/test_cover_whatif.py` (17 tests) and `tests/test_cover_replay.py` (13 tests).
- Edited: `projections/catalogue.py`, `spec.py`, `runner.py`, `__main__.py` and `whatif.py` (`screen` takes an endpoint);
  `ui_future_scenarios.py`; `tests/test_future_scenarios_view.py` (+1 cover chart test); `README.md`; this handoff.

### Verification (Git Bash, 21 Nov 2026)
- **Hand-check (test fixture only; 60% anchor, +10 points on 1 Jan 2030 / 2032 / 2034):**
  - The treatment arm is 60% at the start, 70% at the peak and 60% at the end, and 65% on 1 Jan 2031 and 1 Jan 2033. The
    baseline stays at 60% throughout.
  - Damage (−20 points): 60, 50, 40, 50, 60.
  - Blank against zero, bounds (+40 and −60 allowed, +40.000000001 and −60.5 refused), date order, start before the survey,
    peak after the scenario end, and a non-finite value are all tested.
  - A blocked technique, or the wrong endpoint row, draws no curve.
  - Off-grid peak (15 Mar 2030 / 20 Aug 2031 / 10 Feb 2033, +12): exactly 72.0% at the peak date.
  - Monthly and annual output are identical at every shared date.
- **AppTest replay of the actual dashboard download:** the replayed `whatif.csv` equals the downloaded CSV line by line in each
  case.
  - **Manual removal, +10:** 70, 75, 80, 75 and 70% on the five 1 January dates. The baseline is 70.000000, the survey dates
    are 2011-09 … 2016-09, and the units are percent.
  - **−20 off-grid damage:** 50.0% at 20 Aug 2031.
  - **Zero and blank:** both replay correctly.
  - **Edited saved peak value (95):** ignored. The replay writes 50.0, the manifest flags the difference, and the run ID is
    unchanged.
  - **Technique switched to planting:** exit 3, `technique_blocked_by_screening`, no treatment rows.
  - **Invalid inputs:** an effect giving 105% or below 0%, peak dates out of order, the wrong unit, or a retreat key are
    refused with exit 2 and nothing written.
- **Chromium (Playwright, headless local `streamlit run`, 1440×1000 and 390×844):**
  - **Shown on the page:** the anchor (September 2016, 70.0%, 5 plots, month precision), the baseline label, the manual field
    evidence, a blank effect with the allowed range, the peak text after entering +10 (70.0% → 80.0%, +10.0 percentage
    points), and the bounds message at +35.
  - **Techniques:** the passive-sorbents statement is shown, the input is cleared after switching technique, and planting is
    blocked with no inputs.
  - **Layout and errors:** 0 px overflow and no page errors. The server log has no `bj_` widget warning.
  - **Replay of the downloads:** the cover JSON and CSV downloaded at each width were replayed with
    `python -m src.shoreline_remediation.projections run --scenario <downloaded json> --output <new folder>`. The replayed
    `whatif.csv` was byte-identical to the downloaded CSV (57 lines) at both widths.
  - **Retreat:** the browser journey was rerun on the same build. All checks pass and its download replays byte-identically,
    with the same run ID as in R5 (`145e11e7d52283ec`).
  - **Screenshots reviewed:** at 390 px the "Surveys" text and the natural-recovery end label collided with points and the
    peak. The text was removed (the caption names the survey points) and the end labels were moved to opposite sides; the
    final run is clean.
- **Version-1 examples:** all 9 run before and after this session. Run IDs, statuses, `spec_sha256` and every CSV SHA-256 are
  identical (PNG/SVG not compared).
- **A:** `python -m pytest -q tests/test_cover_whatif.py tests/test_cover_replay.py tests/test_whatif_replay.py tests/test_retreat_whatif.py tests/test_future_scenarios_view.py tests/test_remediation_slice.py tests/test_remediation_inventory.py tests/test_projections*.py`:
  **231 passed, 0 failed, 0 skipped**.
- **B:** `python -m pytest -q tests/test_v54_shell.py tests/test_v54_results.py tests/test_decision_board.py`: **66 passed, 0
  failed, 0 skipped**.
- **C:** `python -m pytest -q tests/test_recovery_trajectories.py tests/test_recovery_view.py tests/test_comparison.py tests/test_v5_1_governance.py`:
  **112 passed, 1 failed** (the NOAA PDF check below).
- **D:** `python -W ignore scripts/capture_projection_baseline.py --out <scratch dir>`. All four production decision reports
  keep their frozen hashes: Bay Jimmy `4da6fa96`, typed marsh `32926391`, rocky 1A `d6d10541`, mangrove `658ec338`, with 0 app
  exceptions.
- **E:** `python -m pytest -q tests`: 981 collected, **977 passed, 4 failed, 0 skipped** (335 s). The four failures are the known environment failures below; none is new.

### Known issues (unchanged)
- **NOAA PDF check:** in Git Bash, xpdf `pdftotext` 4.06 makes `test_v5_1_governance::test_noaa_transcription_matches_the_source_pdf_text`
  and `test_habitat::test_transcription_matches_the_pdf_text` run and fail. 63 of 126 rows match; most failures are
  `method_not_found_on_page`. Under PowerShell both tests skip. This has not been shown to be a transcription error, and the
  NOAA tables stay "Proposed" pending human verification.
- **Line endings:** `test_data_catalogue` and `test_p5_demo` fail under `core.autocrlf=true`.
- **`site_habitat` warning:** the pre-existing Session State warning for this widget, logged by `site_view.py:969`.

### Limitations
- The cover baseline is a flat carry-forward by assumption. No recovery trend is projected, because the logistic fit misses the
  2016 decline (`VEG_FUTURE_GAP`).
- The effect shape is fixed (linear rise, linear return), and there is no persistent-effect option.
- Only the mapped Bay Jimmy cell can be replayed. The tPAH what-if is not implemented.

## Next task (Session R7)
Ask the owner whether to (a) add the tPAH what-if, which needs a compatible starting concentration, a reference rate and a
stated provenance for any removal fraction, or (b) finish plan section 5: PNG/SVG export of both what-if figures and a compact
effect plot of the difference, with method, level and scope in the tooltips. Without an answer, do (b). It needs no new
scientific assumptions.

## Session R7 (21 Nov 2026): soil tPAH what-if with day-one replay. COMPLETE

Start state: HEAD `6842911`, and the R1–R6 work is uncommitted and was preserved. The owner chose option (a), the tPAH what-if,
which settles the R7 question. Nothing was committed.

### What was built
**`src/shoreline_remediation/projections/pah.py`** (model `tpah_whatif/1`) is pure, with no Streamlit dependency.
- **Anchor:** the last untreated, heavily oiled soil tPAH group mean available at as_of, read through the existing loader
  `evidence.tpah_observed`.
  - **Full record (as_of 2016-12-31):** September 2012, 112 mg/kg, 9 plots, date precision month.
  - **Carried with it:** the sampling depth ("0-10 cm cores, surface oil scraped aside") and the analyte ("tPAH as reported in
    the Zengel et al. 2015 S1 Table (43 to 45 compounds); dry or wet basis not recorded in the repository table").
  - **Start of the curve:** the end of the survey month, 30 Sep 2012.
  - **No measurement at the cutoff:** the reason is shown and no future curve is drawn (`Unsupported("no_anchor_observation")`
    on replay).
- **Baseline (the user's choice):**
  - "Hold concentration at the last observation", the default.
  - "Assume a decline half-life", with C(t) = C₀ × 2^(−t/h). This needs a positive, finite h in years, is blank by default,
    and the panel discloses: "This simple scenario assumes a zero long-term background concentration."
- **Treatment:** for techniques allowed by live screening, an intervention date, a one-time reduction (0–100% of the measured
  0–10 cm soil tPAH concentration) and a recorded basis. The default basis is "user-defined sensitivity assumption".
  - **Calculation:** the concentration drops from C(d) to C(d)·(1 − r) on d, and both arms then follow the same baseline rule:
    treatment(t) = natural(t)·(1 − r) for t ≥ d.
  - **Rows at the intervention:** two rows are written on d (`intervention_before` and `intervention_after`, kept in sequence
    by an `order` column), so the chart steps vertically instead of suggesting a gradual decline.
  - **Blank, zero and full:** blank draws the baseline alone; 0% draws two identical arms; 100% takes the treated arm to 0.
  - **Refused inputs:** a reduction outside 0–100%, an intervention on or before the last measurement or after the scenario end,
    and an empty basis.
  - **Panel note:** "The percentage applies to the measured 0-10 cm soil tPAH concentration. A percentage of visible surface oil
    collected does not establish that value."
- **Exports:** observed measurements keep their recorded dates (`2011-07/08`, `2012-09`) and survey periods, with interval, n,
  depth and analyte. Both arms follow by date, in mg/kg; the natural arm has one row per date.

**Spec version 2 and replay.** These follow the R5/R6 pattern.
- **Catalogue:** `catalogue.TPAH_WHATIF_MODEL` and an optional `tpah_half_life` assumption (unit `yr`; omitted means held).
- **Effect schema:** `intervention_date`, `reduction_percent`, `unit: percent of soil tPAH concentration`, a non-empty
  `basis`, and `origin: user_assumption`.
- **Scope check:** `check_scope` loads the anchor and refuses an invalid half-life or effect before anything is written.
- **Runner:** `runner._tpah` writes `observed.csv` and `whatif.csv` with the shared `whatif.csv_text`. The manifest records the
  anchor, baseline choice and rule, half-life, background assumption, screening, effect with its basis, the before and after
  values at the intervention, the end summary and `exported_outputs_check`.
- **Screening:** re-derived on every run through the `soil_tpah` inventory row.

**Panel.** The "Future outcome" control gains a third option, "Soil tPAH". Retreat stays the default, and the cover option is
unchanged.
- **Above the scenario:** the anchor (period, precision, mg/kg, plots, depth, analyte) and a table of both groups' measurements:
  untreated 260 (July–August 2011) and 112 (September 2012); manual removal 220 and 101, with 90% intervals and n. A note says
  the regional DIVER index (mostly 0–2 cm, 58 compounds) stays on its own scale in the manual-removal comparison and is not used.
- **Technique statements:**
  - **Manual removal:** the panel says that two dates identify no treatment-specific effect and that the group differences are
    not used to fill the reduction. The reduction input is never prefilled.
  - **Passive sorbents:** "There is no measured Bay Jimmy soil tPAH effect for passive sorbents."
  - **Planting and other blocked techniques:** they show the reason and no inputs.
  - **Switching technique:** clears the tPAH inputs.
- **Chart:** drawn from the export rows. It shows the measurements with 90% interval bars, a "Last measurement" rule, the pale
  dashed natural-recovery line and the teal dotted what-if line with direct labels, a dashed intervention rule, and diamond
  markers labelled "before 31.9" and "after 25.5" on the same date. Both paths are labelled conditional.
- **Downloads:** "Download tPAH JSON" (a version-2 spec with `exported_outputs`) and "Download tPAH CSV".

Files:
- New: `projections/pah.py`, `tests/test_tpah_whatif.py` (21 tests) and `tests/test_tpah_replay.py` (14 tests).
- Edited: `projections/catalogue.py`, `spec.py` and `runner.py`; `ui_future_scenarios.py`; `tests/test_future_scenarios_view.py`
  (+1 tPAH chart test); `README.md`; this handoff.

### Verification (Git Bash, 21 Nov 2026)
- **Hand-check (test fixture only; 100 mg/kg anchor on 1 Jan 2028, two-year half-life, 20% on 1 Jan 2030):**
  - Both arms are 50 mg/kg immediately before treatment, and the treated arm is 40 mg/kg after it.
  - At year four (1 Jan 2032): natural recovery 25 mg/kg, treatment scenario 20 mg/kg.
  - The held baseline is flat at 100 mg/kg with a treated step to 80 mg/kg.
  - Blank against zero, 100% (to 0), reductions of −0.1, 100.1, NaN and ∞, and half-lives of 0, −1, ∞ and NaN are all
    tested.
  - A date on or before the last measurement, a date after the end, and an empty basis are refused.
  - An off-grid intervention (15 Jul 2030) gives exact before and after values.
  - Monthly and annual output agree at shared dates, including both intervention rows.
  - A blocked technique, or the wrong endpoint row, draws no curve.
- **AppTest replay of the actual dashboard download:** the replayed `whatif.csv` equals the downloaded CSV line by line in each
  case.
  - **Half-life 4 years, 20% on 1 Jan 2020:** includes the before and after rows (after = 0.8 × before), the observed dates
    2011-07/08 and 2012-09 with survey periods, and one natural row on the intervention date. The manifest baseline reads
    half_life, 4.0, zero background, September 2012, 112.0 and 9.
  - **Zero, off-grid (15 Jul 2019, 35%), held baseline with 100%, and blank:** all replay.
  - **Edited saved value:** ignored, the difference is flagged, and the run ID is unchanged.
  - **Technique switched to planting:** exit 3, `technique_blocked_by_screening`, no treatment rows.
  - **Invalid inputs:** refused with exit 2 and nothing written: 120%, −5%, an empty basis, a surface-oil unit, an intervention
    in 2011, a half-life of 0, and a half-life in the wrong unit.
- **Chromium (Playwright, headless local `streamlit run`, 1440×1000 and 390×844):**
  - **Shown on the page:** the anchor and the evidence table, a blank reduction, the surface-oil note, and no future curve with
    a blank half-life.
  - **Half-life 4, 20% on 1 Jan 2020:** "31.9 mg/kg before, 25.5 mg/kg after a 20% reduction". The bounds message appears at
    120%.
  - **Techniques:** the passive-sorbents statement is shown, the inputs clear on switching, and planting is blocked.
  - **Layout and errors:** 0 px overflow and no page errors. The server log has no `bj_` widget warning.
  - **Replay of the downloads:** the tPAH JSON and CSV downloaded at each width were replayed with
    `python -m src.shoreline_remediation.projections run --scenario <downloaded json> --output <new folder>`. The replayed
    `whatif.csv` was byte-identical to the downloaded CSV (42 lines), including the before and after rows.
  - **Cover and retreat:** both browser journeys were rerun on the same build. All checks pass, and their downloads replay
    byte-identically with the same run IDs as in R6 and R5 (`9a88ac5e5418294b`, `145e11e7d52283ec`).
  - **Screenshots reviewed:** the 2011 measurement (260 mg/kg, interval up to ~450) compressed the step near the axis. The step
    labels now carry the values, before above and after below, so the drop reads at any scale; the final run was rechecked.
- **Version-1 examples:** all 9 `examples/projections/*.json` were run before R5 and again now. Run IDs, statuses, `spec_sha256` and every CSV SHA-256 are identical (PNG/SVG not compared).
- **A:** `python -m pytest -q tests/test_tpah_whatif.py tests/test_tpah_replay.py tests/test_cover_whatif.py tests/test_cover_replay.py tests/test_whatif_replay.py tests/test_retreat_whatif.py tests/test_future_scenarios_view.py tests/test_remediation_slice.py tests/test_remediation_inventory.py tests/test_projections*.py`:
  **267 passed, 0 failed, 0 skipped**.
- **B:** `python -m pytest -q tests/test_v54_shell.py tests/test_v54_results.py tests/test_decision_board.py`: **66 passed, 0 failed, 0 skipped**.
- **C:** `python -m pytest -q tests/test_recovery_trajectories.py tests/test_recovery_view.py tests/test_comparison.py tests/test_v5_1_governance.py`:
  **112 passed, 1 failed** (the NOAA PDF check below).
- **D:** `python -W ignore scripts/capture_projection_baseline.py --out <scratch dir>`: all four production decision reports keep their frozen hashes: Bay Jimmy `4da6fa96`, typed marsh `32926391`, rocky 1A `d6d10541`, mangrove `658ec338`, with 0 app exceptions.
- **E:** `python -m pytest -q tests`: 1017 collected, **1013 passed, 4 failed, 0 skipped** (438 s). The four failures are the known environment failures below; none is new.

### Known issues (unchanged)
- **NOAA PDF check:** in Git Bash, xpdf `pdftotext` 4.06 makes `test_v5_1_governance::test_noaa_transcription_matches_the_source_pdf_text`
  and `test_habitat::test_transcription_matches_the_pdf_text` run and fail. 63 of 126 rows match; most failures are
  `method_not_found_on_page`. Under PowerShell both tests skip. This has not been shown to be a transcription error, and the
  NOAA tables stay "Proposed" pending human verification.
- **Line endings:** `test_data_catalogue` and `test_p5_demo` fail under `core.autocrlf=true`.
- **`site_habitat` warning:** the pre-existing Session State warning for this widget, logged by `site_view.py:969`.

### Limitations
- Two measurement dates per group identify no decline rate, so any half-life is the user's assumption. The zero-background
  form can understate long-term residual PAH.
- The reduction is a single step. Removal spread over time, recontamination and changes in depth or analyte are not
  represented.
- In the CSV, the natural arm's row on the intervention date carries `sample = intervention_before` (one natural value per
  date). The treated arm's two rows are the before and after values.
- Only the mapped Bay Jimmy cell can be replayed.

## Next task (Session R8)
Plan section 5's remaining items, which need no new scientific assumptions:
- PNG/SVG export of the three what-if figures (retreat, cover, tPAH), with site, unit, comparator, support dates and "User-defined
  what-if" embedded. Reuse `projections/figure.py` (matplotlib Agg) so the CLI can write the same figure on replay.
- A compact difference plot (treatment minus natural) with a zero line and a labelled sign, shown only where outcome, unit, date
  and comparator match.

Test that the CLI and dashboard figures are drawn from the same rows.

## Session R8 (21 Nov 2026): what-if difference plots and PNG/SVG export. COMPLETE

Start: branch `codex/scenario-prediction-plan`, HEAD `48fe6c9` (R1–R7 committed by the owner).

### What was built
- **`projections/figure.py`:** adds `WHATIF_OUTCOMES`, `difference_rows()` and `whatif_figure()`. They reuse the module's
  matplotlib Agg setup, palette and deterministic SVG settings, and they draw from the CSV text the dashboard downloads.
  - **Difference rows:** the treatment arm's `difference_from_natural*` values in file order. Both tPAH rows on the intervention
    date are kept, so the drop is a vertical step.
  - **Figure contents:** Bay Jimmy, the technique, the natural-recovery baseline, the units, the last observation date and the
    "User-defined what-if" label. When a treatment arm is present, a lower panel shows treatment minus natural recovery with a
    zero line, and the subtitle explains the sign.
- **`ui_future_scenarios.py`:** `figure_section()` sits under each outcome (retreat, cover, tPAH) in the existing panel.
  - **Difference plot:** an Altair chart (treatment minus natural recovery, zero line) shown only when a treatment arm exists,
    with a plain-language sign caption. Units are m, percentage points or mg/kg.
  - **Blank and zero:** a blank assumption hides it; an explicit zero shows a flat line at zero.
  - **Downloads:** "Download PNG" and "Download SVG". The images are cached on the CSV text.
- **Unchanged:** scenario calculations, screening, the replay format, navigation and the CLI.

### Verification (Git Bash)
- `python -m pytest -q tests/test_whatif_figures.py`: **10 passed**. For all three outcomes, the plotted differences equal the CSV
  at `%.6f`: retreat −5.0 m at 2050, cover +10.0 points at the 2032 peak, and the tPAH before and after rows on 1 Jan 2020. Zero
  gives a flat line and blank gives no plot. The PNG opens (PIL verify) and the SVG parses with the required labels. One
  AppTest covers the PNG and SVG buttons per outcome and the difference caption appearing only once an assumption is entered.
- `python -m pytest -q tests/test_whatif_figures.py tests/test_future_scenarios_view.py tests/test_projections.py`: **72 passed,
  0 failed, 0 skipped**.
- **Chromium** (Playwright, headless local `streamlit run`, 1440×1000 and 390×844), manual removal: retreat −0.5 m/yr
  2030–2040, cover +10 points 2030/2032/2034, tPAH 20% on 2020-01-01.
  - The difference plot appeared for each outcome, and each downloaded PNG and SVG opened with "Bay Jimmy" and "User-defined
    what-if".
  - 0 px overflow and no page errors.
  - **Screenshots reviewed:** two faults were fixed before the final run. The mobile difference plot was clipped (height 150 px
    raised to 200 px, with a shorter axis title), and the PNG sign text overlapped the tPAH line (moved into the subtitle).
- **Full suite:** not rerun. The scenario calculation and replay code is unchanged, so the R7 full-suite result stands: 1017
  collected, 1013 passed, 4 known environment failures.

### Not done
- The CLI does not write these figures on replay. `whatif_figure()` can take the replayed `whatif.csv` text, but the replay
  format was kept unchanged as requested.
- The cover figure's subtitle lists "percentage points" as the unit, because it describes the difference panel; the main axis
  is labelled in %.

## R9 and R10, 21 November 2026

Starting branch `codex/scenario-prediction-plan`, revision `b4eb9d4`. R8 was already on the branch. R9's research-only benchmark compares a fit to prior paired observations with persistence and a zero-difference rule. The full protocol, scores, source limitations and external-data request are in [the model validation record](REMEDIATION_MODEL_VALIDATION.md). No endpoint met the conditions to advance the statistical challenger. The existing process-model gate and field contrast are preserved.

R10 adds the optional `--figures` flag to version-2 replay. Both interfaces use the same figure labels and renderer. The runner records image hashes and the rendering library version. The cover axes identify total cover in percent and its difference in percentage points. The original replay command retains its prior outputs.

```
python -m validation.remediation_benchmark
python -m src.shoreline_remediation.projections run --scenario bay_jimmy_retreat_whatif.json --output runs/replay_with_figures --figures
```

The second command uses an actual JSON downloaded from the Assessment and a fresh output directory. Cover and soil tPAH downloads accept the same command.

R9 files: `docs/REMEDIATION_MODEL_VALIDATION.md`, `validation/remediation_benchmark.py`, `tests/test_remediation_benchmark.py`. R10 files: `projections/__main__.py`, `projections/runner.py`, `projections/figure.py`, `ui_future_scenarios.py` under `src/shoreline_remediation/`; `tests/test_whatif_replay.py`, `tests/test_cover_replay.py`, `tests/test_tpah_replay.py`, `README.md` and this handoff.

### Acceptance in PowerShell

- `python -m pytest -q tests/test_remediation_benchmark.py` passed all three tests, including a hand-checked temporal split and rejection of an unmapped process option.
- `python -m pytest -q tests/test_whatif_figures.py tests/test_whatif_replay.py tests/test_cover_replay.py tests/test_tpah_replay.py tests/test_remediation_benchmark.py` passed 58 tests with zero skips.
- Headless Chromium at 1440 px and 390 px: selected manual removal and entered effects of −0.5 m/year, +10 cover points and 20% soil tPAH reduction. For each of the six combinations, downloaded JSON, CSV, PNG and SVG and replayed the JSON with `--figures`. All 18 CSV/image byte comparisons matched. Both viewport runs completed without page errors or horizontal overflow.
- The four fresh decision reports from `scripts/capture_projection_baseline.py` matched the frozen report bytes with zero app exceptions. The three cases outside the mapped site also kept their original visible controls. All nine version-1 examples replayed into fresh directories with six completions and the three expected abstentions.
- `python -m pytest -q tests --tb=short`: 1,030 collected, 1,026 passed, 2 failed and 2 skipped. Both failures compare file bytes on this CRLF checkout. A read-only hash check confirmed 82 catalogue files matched directly, the remaining 102 matched after CRLF-to-LF normalization, and all 12 P5 training-file hashes matched after normalization.
- PowerShell skipped the two NOAA PDF checks because its PATH has no `pdftotext`. Adding Git's xpdf directory to the test process PATH and running `python -m pytest -q tests/test_habitat.py::test_transcription_matches_the_pdf_text tests/test_v5_1_governance.py::test_noaa_transcription_matches_the_source_pdf_text --tb=short` reproduced both failures. Human source verification remains open.
- Next research task: obtain the independent site-and-treatment records specified in the R9 protocol, establish comparability and agree the useful error margin before scoring. The current numerical futures remain conditional.
