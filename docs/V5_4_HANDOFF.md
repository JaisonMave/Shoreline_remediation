# V5.4 unified shell, map-first Home and single results view: handoff

**Current continuation (17 November 2026):** [Recovery-view handoff](V5_4_RECOVERY_VIEW.md) covers continuous retreat and vegetation fits, conditional manual-cover and PAH scenarios, parameter provenance, uncertainty exclusions, and evidence/synthetic chart corrections. These research curves do not change decisions or reports and are not validated site forecasts. Branch `model_v5_1`. The status and layout below are the historical shell implementation record.

Status: implemented, tested, seen running in Chromium; uncommitted (branch `model_v5_1`, on top of f00b22c). Continues `docs/V5_3_HANDOFF.md`.
Continued in `docs/V5_4_PLOT_FIRST_HANDOFF.md` (plot-first Assessment, treatment comparison, simplified Map); sections 2 and 6 below describe the layout before that work.
Presentation change only. No model, registry entry, validation result, class, category or recommendation was changed or recomputed. `ui_pipeline` is still the only caller of `run_decision()`.

## 1. Files

Stages 1-2 (earlier in V5.4): created `src/shoreline_remediation/ui_site_panel.py`, `tests/test_v54_shell.py`; modified `.streamlit/config.toml`, `dashboard.py`, `map_sites.py`, `site_view.py`, `ui_landing.py`, `ui_map.py`, `ui_nav.py`, `ui_theme.py`, `tests/test_map_sites.py`, `tests/test_ui_stage2.py`, `tests/test_ui_stage3.py`.
Stages 3-5 (this session):
- Created `ui_results.py` (results view and Streamlit-free helpers `top_card`, `this_site`, `breadcrumb_items`), `tests/test_v54_results.py`, this file.
- Modified `site_view.py` (run record gets `crumb`; `_run_button` with on_click callback; `_results_section`; `_technical_area`; the three habitat renderers re-laid out; composer baseline relabelled; `render_site_evidence(lead=...)`; old `_decision_section` and `_download` removed, the download now lives in the title row), `dashboard.py` (Assessment page header removed, Back to home in the habitat row), `ui_decision_board.py` (public aliases `benefit_lines`, `reference_rows`), `ui_models.py` (`scatter_chart` shared by Models and Assessment; `INDIVIDUAL_ERROR_NOTE` caption), `ui_theme.py` (results CSS), `tests/test_decision_board.py`, `tests/test_v54_shell.py`, `CHANGELOG.md`, `docs/V5_3_HANDOFF.md` (first line corrected: V5.3 is f00b22c).
- Not touched: `decision_pipeline.py`, `registry.py`, `ui_pipeline.py`, `models/`, `data/`, `results/`, `ui_scenario.py`, `process_model.py`, the governance and validation tests.

## 2. Behaviour

After a run (Home panel or the page's own Run) the Assessment page shows: title row "Remediation assessment" with breadcrumb (place | shoreline and ESI | oil | oiling and its source, record or entered) and the report download; primary outcome card (report's `decision_outcome_label`, top non-empty category from `board_model`, class and evidence chips; abstention outcomes get an explicit pill and equal weight; natural recovery is called the reference); key-flags card (abstentions, advisories, site-scope flags verbatim, first 3 then "Show all N flags"); alternatives in CATEGORY_ORDER (no-demonstrated-benefit and insufficient-evidence are separate groups, excluded is a collapsed expander with reasons); expected-outcome card (reference rows with model id, registry-state chip and scope; for an in-scope known marsh cell a "this site" block); validation card (edge_loss_v1 hold-out scatter with MAE, n, method, unit, identity line and the "How good is the number?" link; PAH is text status only); supporting-evidence link. Then a collapsed "Change place or scenario" (open before any run) and a collapsed "Technical details and evidence" (older answer card and option views, assumptions and limitations, literature-prior provenance, applicability and scope warnings, technical trace). Stale-run warning kept. One primary button (`run_<habitat>`) before and after a run.

## 3. Decisions

- Three edge-loss numbers, always labelled by source, never merged: deployed edge_loss_v1 all-cell fit (1.42 m/yr, from the report); scenario-composer baseline (1.32 m/yr, experimental, only in Technical details, label and chip now say so; it previously carried the Validated chip of the other model); leave-one-basin-out prediction (1.31 m/yr, `data/demo/p5_sites.csv`, with the cell's observed 1.54 m/yr). The "this site" block shows deployed, observed, leave-one-basin-out and the absolute difference (percentage only where observed is not 0), captioned as one cell's individual error against the overall MAE 1.296 m/yr, n 12,696.
- The run button uses an on_click callback so the results and the collapsed form reflect the run in the same script run.
- Old "Decision board for" text is replaced by the title row; the full per-option board (`render_decision_board`) is no longer drawn on the Assessment page (its content is in the alternatives and in the technical area); the function is kept and tested.
- Typed site: not changed to out of scope (that would change the older views' numbers). The older views now say "no model scope status assigned" and that they nevertheless treat typed values as in scope; the results do not. Pre-existing `_pick_site` behaviour is documented, not fixed.
- Rocky ESI 1A at the default scenario returns `conditional_only`, not an abstention; ESI 8A and mangrove return the insufficient-evidence abstention with natural recovery as the reference.
- No tabs on the expected-outcome card (mockup has them); the validation card sits beside it instead. No Share button (no share function exists).

## 4. Test changes (existing tests)

- `tests/test_decision_board.py` (2 assertions) and `tests/test_v54_shell.py` (1): the text "Decision board for" no longer exists; assertions now require "Remediation assessment" (and "Bay Jimmy, Louisiana" for the Home-run test; the cell id is still asserted on `rec["where"]`). Same strength.
- Earlier Stage 1-2 edits to `test_ui_stage2.py`, `test_ui_stage3.py`, `test_map_sites.py` are as recorded in Stage 1-2 work (label and structure changes of the shell).

## 5. Tests

Command: `C:\Users\Jaison\AppData\Local\Programs\Python\Python311\python.exe -W ignore -m pytest -q`
Result: 672 collected: 668 passed, 4 failed, 0 skipped. The 4 failures are the pre-existing `core.autocrlf` failures (`test_data_catalogue::test_every_data_file_is_catalogued_and_unchanged`, `test_habitat::test_transcription_matches_the_pdf_text`, `test_p5_demo::test_model_card_has_provenance`, `test_v5_1_governance::test_noaa_transcription_matches_the_source_pdf_text`) and no others. `tests/test_v54_results.py`: 22 tests.

## 6. Browser check

Playwright and Chromium, server on port 8602: Home to "Use Bay Jimmy" to "Run assessment", then Assessment-page runs for the exposed rocky shore and the mangrove, at 1440x900 and 390 px wide; screenshots in the session scratchpad `after_s5/`. Seen: outcome card and key flags are above the fold at 1440x900 (Bay Jimmy); no horizontal overflow at 390 px; no Streamlit exceptions. Known visual defects: the hold-out scatter's plot area is flat because the axes share a wide range (-15 to 10); the mangrove breadcrumb wraps with a leading separator at 1440; the rocky/mangrove outcome card is taller than the fold at 390 px. Not checked: other beach types, Pick-a-cell and typed-site flows in a browser, keyboard use, the download file contents, Safari/Firefox.

### 6a. Stage 6 acceptance pass (orchestrator, 17 Nov 2026)

Scripted Playwright/Chromium pass at 1440x900 and 390x844: Home renders with the map canvas; Run is disabled until a place or shoreline type is chosen; "Use Bay Jimmy" shows the record and enables Run; Run lands on the Assessment page showing the report's own outcome label, manual removal, the three labelled site numbers (1.42 deployed, 1.54 observed, 1.31 leave-one-basin-out), MAE 1.296 and n 12,696; no Share button; the "How good is the number?" link opens Models on `edge_loss_v1`; the "Why?" link opens the Evidence explorer; an unknown coordinate (25.0, -90.0) gives the screening-only message, no "Select this cell" button and Run stays disabled; no horizontal overflow and no Streamlit exception on any page at either width. 46 of 48 scripted checks passed; the 2 misses were the script looking for a "Show all" button where the control is an expander (seen working in the screenshot). Keyboard: Tab reaches "Use Bay Jimmy" and "Run assessment" with a visible focus ring, and Enter runs the assessment. A real mouse click on the Bay Jimmy pin selects the cell; wheel zoom and drag pan raise no error. Fixed in this pass: a Streamlit warning that `map_basin` had both a default index and a session-state value (the default is now set through session state only). Assessment page height at 1440: 3,000 px (7,692 before V5.4).
The flat look of the hold-out scatter is a property of the data on equal axes, not a rendering defect: predictions span a much narrower range than observations. Still not checked: other beach types, Pick-a-cell and typed-site flows in a browser, the downloaded file's contents, a screen reader, browsers other than Chromium. On 390 px the collapsed-sidebar toggle overlaps the first line of text when scrolled.

## 7. Remaining limitations

Technical area content (older views) is long and unchanged. Expected-outcome table is dense on narrow screens. No expert review; NOAA ratings still unverified by a person. The hold-out scatter is a descriptive check, not a new validation.

## 8. Next task

Decide on commit with the owner. Then: review the Technical details area for further trimming, add a tabbed expected-outcome card if wanted, and fix `_pick_site` scope status for typed sites together with the older views' dependence on it.
