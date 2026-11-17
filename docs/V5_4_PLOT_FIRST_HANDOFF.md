# V5.4 plot-first assessment and treatment comparison: handoff

Status: implemented, tested, seen running in Chromium; committed on branch `model_v5_1` as "Simplify shoreline assessment and add plot-first treatment comparisons" (on top of fac111e). Continues `docs/V5_4_HANDOFF.md`.
No model, registry state, evidence verdict, validation result, screening status, harm flag, abstention or recommendation was changed. `ui_pipeline` is still the only caller of `run_decision()`. The comparison layer reads the report and cannot write to it (tested).

## 1. Reading order and what each scenario shows

Assessment page, after a run:

1. **Scenario**: one line (place, shoreline and ESI, oil, oiling with "record" or "entered") and the report download.
2. **Finding**: one sentence, then one "Main limitation", then the report's own decision-outcome label ("Screening outcome"). Abstentions keep their pill.
3. **Primary visual**: treatment-effect plot, historical visible-oil curve, or nothing (then the table is the result).
4. **Response options** (titled "Screening result" when it is the primary result): one table, every option of the report in the pipeline's category order, with method, screening status, evidence basis and main condition or exclusion reason. Excluded options stay in the table with their reason. For salt marsh a fifth column quotes the comparison shown in the plot, or "No comparative data".
5. **Methods and sources** (collapsed): links to Evidence and Models, scope tier, every flag, field comparisons in detail (including historical values of methods that are not ranked), how the order is made, the model-candidate audit, natural-recovery reference values, then the older detail views, model assumptions, literature-prior provenance and the technical trace.

The "Change place or scenario" form sits between 4 and 5. The stale-run warning is unchanged.

| Scenario | Finding | Primary visual |
| --- | --- | --- |
| Bay Jimmy (heavy, known cell) | Total vegetation cover was 34 percentage points higher in manually treated plots than in untreated oiled plots at year 2 | Dot-and-interval plot, switchable between vegetation year 2, erosion 2010 to 2012 and erosion 2012 to 2018; site-model strip under it |
| Typed or habitat-level heavy salt marsh | Same sentence; the limitation says these are the Bay Jimmy plots and that conditions are not established | Same plot, row labelled "not ranked: conditions not established"; no site strip |
| Salt marsh, not heavy | "No comparative data for this scenario" | No plot; site strip for an in-scope cell; table |
| Fine-to-medium sand (ESI 3A) | Share of segments still oiled at day 365 for the chosen first-oiling group | "Historical response" curve at days 90, 180, 365, 730 with 90% intervals |
| Other beaches, exposed and sheltered rocky shore, mangrove | "No treatment has a comparable effect estimate" with the screening counts; first abstention as the limitation | Screening table |
| Unsupported habitat | The report's abstention label and scope message | None; no table |

Map page: one coverage line ("Mapped sites are historical Louisiana salt-marsh cells (Deepwater Horizon, 2010)."), the map with its colour key, the coordinate check with the unknown-coordinate message, the panel with the Bay Jimmy shortcut and the one primary "Run assessment" button, and one collapsed "Geographic and habitat coverage" section (a table of habitats and coverage tiers). Removed: intro sentence, four step cards, scope chips, Featured locations and Explore habitats card rows (their "open" buttons repeated the panel).

## 2. Bay Jimmy estimates that shipped

All are differences from untreated oiled plots with 90% Welch t intervals (sampling uncertainty of a difference of group means). Observational: plots were not randomly assigned to cleanup method. One site, one spill.

| Outcome | Method | Estimate | 90% interval | Plots | Basis | Screening status | In the order |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Total vegetation cover, year 2 (2012), percentage points | Manual removal | +34.0 | +19.0 to +49.0 | 5 vs 9 | Derived from published group means and SEs (52 ± 7 against 18 ± 3; Zengel et al. 2015 S1 Table), not plot-level | Recommended | Yes, single method, no rank |
| same | Mechanical removal | +5.0 | -12.1 to +22.1 | 5 vs 9 | same | Excluded | No (historical value in Methods only) |
| Spartina cover, year 2 | Planting after mechanical | +69.0 | +47.7 to +90.3 | 5 vs 5 | Randomised, incremental on a mechanically treated baseline | Conditional | No: different outcome and comparator |
| Erosion-rate change 2005-2010 to 2010-2012, m/yr (negative = less erosion) | Manual removal | -0.63 | -1.25 to -0.02 | 5 vs 9 | Computed from plot-level rates (Zengel et al. 2022, GRIIDC) | Recommended | Yes, single method, no rank |
| same | Mechanical removal | +0.28 | -0.17 to +0.73 | 9 vs 9 | same | Excluded | No |
| same | Mechanical removal, then planting (sequence against untreated) | -1.47 | -2.06 to -0.88 | 5 vs 9 | same | Conditional | No: mechanical removal is excluded |
| Erosion-rate change to 2012-2018, m/yr | Manual removal | -0.13 | -0.62 to +0.36 | 5 vs 9 | same | Recommended | Yes, single method, no rank |
| same | Mechanical removal | -0.24 | -0.74 to +0.26 | 9 vs 9 | same | Excluded | No |
| same | Mechanical removal, then planting | -0.97 | -1.99 to +0.05 | 5 vs 9 | same | Conditional | No |

Verified by recomputing from `data/external/zengel2015/zengel2015_group_means.csv` and `data/external/zengel2022/zengel2022_griidc_erosion.xlsx`; they equal `docs/P5_WORKED_EXAMPLE.md`. The two studies share plots and are not independent.

**Was there a ranking?** No. For every target exactly one method is eligible (manual removal), so each plot is titled "comparison with natural recovery" and no rank is shown. The ranking logic (sorting, shared ranks for exact ties, the "provisional order" label) is implemented and tested but is not exercised by runtime data today.

Site-model strip (cell 8018_32612): deployed estimate 1.42 m/yr, historical observation 1.54 m/yr, held-out test prediction 1.31 m/yr, each labelled; dataset-level held-out MAE 1.296 m/yr (n 12,696) in the caption. The cell's own absolute difference is no longer shown. The full scatter is on Models only.

Fine sand, default group (moderate or heavy surface oil, n 87): 77%, 77%, 74%, 68% at days 90, 180, 365, 730. Denominator and endpoint checked in `models/beach_sand_persistence_v1.json`: ever-oiled ESI 3A SCAT segments with a later visit; cleared at the first survey with no oil observed; interval from 200 refits resampling whole segments.

## 3. Theory-based candidate: none qualified

Nearest candidate: `composer_natural_recovery_v1`, year-2 vegetation difference for manual removal (0.355 of reference cover). It fails all five checks:

1. Same target: no. Its unit is cover relative to a reference marsh, not percentage points of total cover.
2. Explicit pathway: no. It divides the Zengel et al. (2015) contrast by the reference cover (95%) and adds it to the vegetation curve, then holds and decays it by an assumed rule.
3. Discrepancy documented: no. The field interval is read as a normal distribution (assumed); the curve under it (`veg_recovery_v1`) is worse than a no-trend baseline for heavy oiling.
4. Calibration against evaluation: no. Its only input for this outcome is the same plots as the field row (0.355 x 95 = 33.7 points). It is the field estimate in another unit, so it would be counted twice.
5. Gates: no. Experimental; R3, D32 and V5-0.1 heavy-cell bias gates failed.

`process_model_v2` is further away: it predicts residual oil, failed its F5 gate, and has no supported link from residual oil to vegetation cover. F8 literature pooling has no pooled marsh coefficient for manual removal, mechanical removal or planting.

Needed for admission: a model that predicts total vegetation cover at year 2 in percentage points against untreated oiled plots, with its treatment-to-cover pathway evaluated on treated and untreated plots that did not calibrate it (a second site or spill with both groups).

The comparison logic still accepts model estimates (`ModelAdmission`, five checks, shared-source record). A synthetic test shows a model estimate of 41 sorting above a field estimate of 34 while both screening statuses stay as they were. Synthetic values exist only in `tests/test_comparison.py`; `runtime_estimates()` raises if it meets one.

## 4. Decisions

- Eligibility: excluded never ranked; category `recommended` or (not conditional and screening rule `eligible`) needs no condition; otherwise every listed condition must be resolved in favour, and no listed condition or an unreadable one counts as unknown. Unknown is not met.
- Allowed rows whose conditions are not established are drawn and labelled, never ranked. Excluded rows and off-target contrasts are not drawn; they are in Methods and sources.
- No unit conversion exists in the comparison layer. No cross-outcome score. No order-stability probability (no effect threshold with a scientific basis).
- Typed marsh site (user-visible change): five inputs were removed from "New site (enter values)": open water within 1 km, open water within 250 m, mean fetch, pre-spill edge-loss trend, and the shoreline (ESI) choice "10A / other". Nothing in the authoritative path read them; they only fed the older detail views, which treated the typed values as an in-scope model cell. A typed site keeps latitude, longitude and oiling class, is never given `in_scope`, and the older detail views now use the same generic-scenario report as the results. Lost for typed sites: the composer baseline, the edge-loss metric and the extrapolation warning. The form states what is available without a matched site record (screening, literature evidence, the Bay Jimmy field comparison for heavy oiling, unranked) and what is not (site edge-loss estimate, observed rate, held-out prediction).
- The older answer card is kept inside "Option evidence in detail"; it repeats the outcome there. The one-line scope bar and its popover were removed from the main view (their content is in "Model assumptions and limitations").
- Report download gains a "Field comparisons with untreated oiled plots" section built from the same records as the dashboard. The existing composer chart section is retitled "Scenario-composer differences from natural recovery (experimental)".

## 5. Files

- Created: `src/shoreline_remediation/comparison.py`, `src/shoreline_remediation/ui_plots.py`, `tests/test_comparison.py`, `tests/_nav.py`, this file.
- Modified: `ui_results.py` (rewritten), `site_view.py`, `ui_landing.py`, `ui_map.py`, `ui_site_panel.py`, `ui_report.py`, `ui_theme.py`, `dashboard.py` (docstring), `CHANGELOG.md`, `docs/V5_4_HANDOFF.md` (pointer), and tests `test_v54_results.py`, `test_ui_stage2.py`, `test_ui_stage3.py`, `test_ui_stage4.py`, `test_decision_board.py`, `test_stage3_links.py`, `test_map_sites.py`, `test_session3_answer_card.py`, `test_dashboard_v5.py`, `test_p5_demo.py`.
- Not touched: `decision_pipeline.py`, `ui_pipeline.py`, `registry.py`, `treatment_effects.py`, `scenario_composer.py`, `models/`, `data/`, `results/`, governance and validation tests.
- No longer rendered but kept (still tested as data functions): `site_view.featured_sites()`, `site_view.habitat_cards()`, `ui_components.scope_panel()`, `ui_decision_board.render_decision_board()`, the step-card CSS.

## 6. Existing tests changed

- Tests that opened a habitat through a Map card now use `tests/_nav.open_habitat` (page switch plus habitat switcher) or the panel's Run button. Same assertions afterwards.
- Map content tests (`test_ui_stage2`, `test_ui_stage3`): assertions on step cards, Featured locations and Explore habitats were replaced by assertions on the coverage line, the single coverage section and `ui_landing.coverage_rows()`; `test_featured_card_opens_the_site_page_at_its_habitat` was removed (no such cards).
- `test_p5_demo::test_dashboard_new_site_extrapolation_warning` became `test_dashboard_new_site_gets_no_site_model`: the old test asserted the typed-site promotion that this work removes.
- `test_v54_results.py`: eight tests rewritten for the new layout (finding, table, site strip, methods area); three added.
- `test_map_sites::test_home_renders_map_and_existing_cards` became `test_home_renders_map_and_the_bay_jimmy_shortcut` (the card button it looked for is gone).
- `test_dashboard_v5::test_every_habitat_loads`: the "Scope: " bar assertion became a check for the Methods and sources area.

## 7. Tests

Command: `C:\Users\Jaison\AppData\Local\Programs\Python\Python311\python.exe -W ignore -m pytest -q -p no:cacheprovider`
Baseline before any edit: 672 collected, 668 passed, 4 failed, 0 skipped.
After: 711 collected, 707 passed, 4 failed, 0 skipped.
The 4 failures are the same four as the baseline (`test_data_catalogue::test_every_data_file_is_catalogued_and_unchanged`, `test_habitat::test_transcription_matches_the_pdf_text`, `test_p5_demo::test_model_card_has_provenance`, `test_v5_1_governance::test_noaa_transcription_matches_the_source_pdf_text`), the `core.autocrlf` hash failures.
`tests/test_comparison.py`: 39 tests (mismatch on each target field, sign direction, missing values, exclusions, met, unmet and unknown conditions, planting prerequisite and incremental contrast, ties, single eligible method, synthetic model above field with statuses unchanged, incomplete admission, shared source, report download equals dashboard). `git diff --check`: clean (exit 0; only line-ending notices from `core.autocrlf`).

## 8. Browser check

Playwright with Chromium against `streamlit run src/shoreline_remediation/dashboard.py` on port 8611, at 1440x900 and 390x844: 92 of 94 scripted checks passed. Covered: Map (coverage line, no featured content, unknown coordinate 25.0, -90.0 gives the message and no select button); Bay Jimmy from Map to Assessment (finding, limitation, plot, strip, table); switching the plot to erosion; editing the oil category (stale warning), rerunning (warning gone, scenario line updated); Methods and sources; the report download (file saved and checked for the comparison section, +34.0 points, source and exclusion text); the Models and Evidence links; exposed rocky shore, sheltered rocky shore, mangrove, fine sand and a salt-marsh scenario without a site record, each from the Map panel. No Streamlit exception and no horizontal page overflow in any case at either width.
The 2 misses are the same check at each width: after "Held-out test on Models" the page is Models on `edge_loss_v1`, but the script did not find the scatter heading in the visible text. The app test confirms the scatter is rendered on that page; it was not confirmed by eye in the browser.
Seen in screenshots: the opening result fits above the fold at 1440x900; plot tick labels, zero line, value labels and axis title are readable at both widths; the options table becomes stacked cards at 390 px.
Not checked: a typed heavy marsh in the browser (covered by an app test), keyboard-only use, a screen reader, light theme, browsers other than Chromium.

## 9. Remaining limitations

- Every plot shows one method, because one method is eligible. The ranking is untested on real data.
- The finding stays on vegetation when the plot is switched to erosion.
- On a narrow screen the full options list is long (16 stacked cards for salt marsh).
- The zero line can cross the row label where the interval lies far from zero.
- Field evidence: one spill, one site, 5 to 9 plots per group, observational. NOAA ratings shown in the evidence-basis column are still unverified transcriptions. No expert review.
- A typed site's latitude and longitude are used only for the locator map in the detail views.
- `README.md` was not changed (it does not describe the pages that changed).

## 10. Follow-ups and next task

Follow-ups recorded at commit:
- The Finding keeps the vegetation headline when the plot is switched to an erosion tab. Decide whether the finding should follow the selected outcome or stay fixed with a label saying which outcome it describes.
- The browser check did not find the scatter heading in the visible text of Models after "Held-out test on Models" (both widths). The app test shows the scatter is rendered; confirm by eye where it sits on the page and whether it is visible without opening anything.

Next: either remove the unrendered card functions with their tests, or bring a second treated-and-untreated plot dataset in, which is what both a real ranking and a model admission need.

## 11. Git status at handoff

Branch `model_v5_1`. This work is one commit on top of fac111e. `.vscode/` was untracked before this work, was not touched and is not part of the commit.
