# V5.3 map-first decision dashboard: handoff

Status: implemented, tested; committed and pushed as f00b22c (branch `model_v5_1`, on top of the V5.2 commit 4be0a64). Continued in `docs/V5_4_HANDOFF.md` (V5.4 shell, map-first Home and single results view). Continues `docs/V5_2_HANDOFF.md`.
This is a presentation change. No model, registry entry, validation result or recommendation was changed. The map does not validate any model.

## 1. Files (Stages 1 to 4)

Created: `src/shoreline_remediation/map_sites.py` (Streamlit-free site-table reader for the map), `ui_map.py` (Gulf map, coordinate check, open-site action),
`ui_decision_board.py` (decision board, plus Stage 3 deep links), `literature_priors.py` (provenance view of the priors table), `tests/test_map_sites.py`,
`tests/test_decision_board.py`, `tests/test_literature_priors.py`, `tests/test_stage3_links.py`.
Modified: `dashboard.py`, `site_view.py`, `ui_landing.py` (Stages 1 to 2); Stage 3 added to `site_view.py` (run record keeps ESI and habitat label; provenance expander),
`model_validation_data.py` (`edge_loss_scatter`), `ui_models.py` (`_scatter_block`). Not touched: `decision_pipeline.py`, `registry.py`, `ui_pipeline.py`, models, data, results, `ui_scenario.py`, `process_model.py`.

## 2. Stage 3 and 4 behaviour

- Model validation, "Held-out results" tab: predicted-against-observed scatter for `edge_loss_v1`, from `data/demo/p5_sites.csv` columns `lobo_pred` and `observed_rate`, rows with both present
  (n = 12,696, MAE 1.296 m/yr on all rows, same figure as the model card's leave-one-basin-out value). Coloured by basin, 1:1 line, axes share one range that includes zero (observed and predicted values include negatives, so the lower bound is the data minimum, not 0).
  Plot shows a fixed random subset of 4,000 points; MAE, n and per-basin values use all rows. Percentage error is reported only over rows whose observation is not 0 (12,666 rows).
  Caption states: leave-one-basin-out (trained on the other two basins), m/yr, one spill, northern Gulf salt marsh, Terrebonne out-of-sample but not a P2 gate basin, the deployed model is the all-cells refit and is not what is plotted.
- Decision board: "How good is the number?" appears only when the report's natural-recovery reference numbers come from `edge_loss_v1` or `pah_decline_v1`; it sets `mv_model` and opens Model validation. Otherwise a plain statement that no validated numerical forecast exists for this habitat.
  "Why?" (board level and per option) sets `ev_classes`, `ev_esi`, `ev_options` (option codes resolved to catalogue display names; values the catalogue does not offer are dropped) and opens the Evidence explorer. On_click callbacks; no tab keys were added.
- Provenance panel: collapsed expander on the Site assessment page below the board (also shown before Run). Table of the 9 SOURCED/LITERATURE priors (citation, DOI, unit, low, high), the ASSUMED statement (15 assumed rows not listed), and the "no literature-derived estimate" statement for the selected habitat (the priors table has no habitat or technology column). Imports neither `process_model` nor `process_uncertainty`.
- Keyboard alternative: the coordinate check expander and site picker are exercised by AppTest (`tests/test_map_sites.py`, `tests/test_decision_board.py`). New tables and charts use `width="stretch"` (checked structurally by a test).

## 3. Decisions

- Hold-out column: `lobo_pred` is a genuine leave-one-basin-out M1 prediction for all 12,696 in-scope cells. `p2_heldout_M1` is byte-identical to it on the 8,592 Barataria/Breton rows and adds nothing, so it is not used. Terrebonne is out-of-sample but was not a P2 gate basin (too few heavily oiled cells). Interval coverage is not independent of the offsets. `p5_edge_loss_v2` class intervals are not shown.
- PAH scatter: skipped. `results/pah_decline/` holds `station_campaign.csv` (station measurements) and summary files, but no file of hold-out predictions per station, so a plot could not be shown as the hold-out rather than the fit. The existing hold-out summary is unchanged.
- No scatter for any other model.

## 4. Tests

Command: `C:\Users\Jaison\AppData\Local\Programs\Python\Python311\python.exe -W ignore -m pytest -q`
Result: 631 collected: 627 passed, 4 failed, 0 skipped. `tests/test_stage3_links.py`: 14 passed.
The 4 failures are pre-existing and caused by `core.autocrlf` line endings (not by this work): `tests/test_data_catalogue.py::test_every_data_file_is_catalogued_and_unchanged`, `tests/test_habitat.py::test_transcription_matches_the_pdf_text`,
`tests/test_p5_demo.py::test_model_card_has_provenance`, `tests/test_v5_1_governance.py::test_noaa_transcription_matches_the_source_pdf_text`. `tests/test_v5_1_governance.py` and `tests/test_v52_model_validation.py` were not weakened.

## 5. Browser check

Playwright is not installed in the project interpreter and was not installed. No browser check was done in this stage: nothing was seen rendered at 1440 or 390 px, the map click was not exercised in a real browser, and no screenshots exist. Verification is by AppTest and structural tests only.

## 6. Known pre-existing issues (not fixed here)

1. `_pick_site` in `site_view.py` hard-codes status `in_scope` for typed sites, so the legacy detail views treat them as in scope while the decision board (which goes through the scenario path) does not.
2. The Site page shows both the live legacy detail views and the last-Run board, with a stale warning when the place or scenario changed since Run.

## 7. Next task

Run the browser check where Playwright is available (Home, Bay Jimmy open, Run, flags, both deep links, at 1440 and 390 px), then decide on commit with the owner. Not done: human verification of the NOAA ratings and AI-extracted study rows; no expert review exists.
