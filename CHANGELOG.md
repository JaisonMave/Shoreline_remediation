# Changelog

All changes on branch `model_v4` (earlier entries were made on `process-model-audit`) relative to `main` (commit 4b0c118). Newest first.
Each entry gives what changed, why, where it lives, the result, and its status. Statuses follow
`docs/ROADMAP.md`: Completed means validated and documented, not just coded. Decisions are numbered as in
the decision register in `docs/ROADMAP.md`.

How to reproduce the analyses: `pip install -r requirements-analysis.txt`, then the commands listed per entry.
Raw SCAT shapefiles come from `scripts/download_scat.sh`; imagery is read on demand from Microsoft Planetary
Computer (no account needed).

---

## 2026-11-15: V5.1 Session 2 Stage 4: rocky-shoreline screening pages, Stage 3 integrated (implemented, tested, seen running; not committed)

- **Integrated** Stage 3 (`2008c19`, `cf659e9`) into the local design branch by fast-forward from `origin/ccr-ed209fd7-hn5mdk`
  (the design branch was at `ccc0d35`, equal to origin). Nothing pushed.
- **Added** ESI 1A and ESI 8A pages (`site_view._screening_renderer`, generalised from the beach renderer; entries `esi_1A`,
  `esi_8A`, labels read from the habitat table). The landing cards are now openable. The pages show the pipeline's abstentions
  (`no_site_forecast`, `no_model`, `insufficient_evidence`, `no_recommendation`), "No outcome model: rules and literature only",
  and a rocky scope panel. No rocky site record, model or numerical forecast exists and none was added. Screening eligibility is
  not demonstrated benefit. `decision_pipeline.py` and the registry were not changed.
- **Fixed** interval-chart row collision (total chart height left no plot area; `ui_components._INTERVAL_CHROME`); AI-proposed
  table text contrast (`#8A7F99` to `#B4AAC4`, at least 7:1 on the dark surfaces); landing tier lookup now uses a structured
  `SiteCard.tier` instead of the display label; fine-sand-beach chips and a page caption now separate the experimental
  persistence reference from the cleanup options (rules and literature only, no experimental evidence).
- **Tests**: `tests/test_ui_stage4.py` (20 tests); two Stage 3 tests updated because rocky cards are now openable.
  `python -m pytest tests -q`: 510 passed, 0 failed, 0 skipped. These are software tests, not scientific validation.
- Status: implemented and tested; screening only, nothing validated.

---

## 2026-11-15 (V5.1 Session 2, Stage 3): landing page, navigation and site discovery
- **Why:** handoff section 10 step 3: a stakeholder should enter on a page that shows the sites and habitats, and see
  what kind of evidence exists for each, before reaching the assessment.
- **What:** new `ui_nav.py` (one page state in `st.session_state["page"]`, mirrored to `?page=`, with a "Back to home"
  button) and `ui_landing.py` (hero, featured locations, habitat coverage cards, method steps, placeholders for the
  Evidence explorer and Model validation pages). The landing page reuses the Stage 2 components. Habitat coverage tiers
  are derived from the model registry states (`site_view.habitat_coverage()`), not hard-coded. The "Legacy and research"
  page shows a warning that it does not drive production recommendations. The sidebar starts collapsed on a phone.
  `site_card` gained optional `key` and `button_key` arguments. No decision-engine, registry, model or report change.
  No new dependency or image.
- **Where:** created `src/shoreline_remediation/ui_nav.py`, `src/shoreline_remediation/ui_landing.py`,
  `tests/test_ui_stage3.py`; modified `src/shoreline_remediation/{dashboard,site_view,ui_components,ui_theme}.py`,
  `tests/test_dashboard_v5.py`, `tests/test_p5_demo.py`, `tests/test_ui_stage2.py`, `tests/test_v5_1_governance.py`
  (navigation changes only), `docs/V5_1_HANDOFF.md` section 2d.
- **Result:** `python -m pytest tests/test_ui_stage3.py -q`: 65 passed, 0 failed, 0 skipped. `python -m pytest tests -q`
  on Python 3.11: 488 passed, 0 failed, 0 skipped (423 existing + 65 new). Launched with `streamlit run` and inspected in
  headless Chromium at 1440 x 900 and 390 x 844: every page opens, card buttons navigate, the reload keeps the page, no
  Streamlit exception and no horizontal page overflow. Not checked in a browser: the browser Back button, keyboard-only
  navigation, a real phone, the beach and remaining habitat card buttons, legacy results after Run, the HTML report.
- **Status:** Implemented, tested and seen running (software tests and a headless browser check). **Not committed or
  pushed.** Not scientific validation. The Evidence explorer and Model validation pages are placeholders. No rocky-shoreline
  site or forecast yet (the rocky entries are shown but cannot be opened).

## 2026-11-15 (V5.1 Session 2, Stage 2): reusable dashboard components and hero
- **Why:** handoff section 10 step 2: one small component set on the Stage 1 theme, so later pages do not each invent
  their own cards and headers.
- **What:** `section_header`, `status_label`, `site_card`, `card_row`, `hero_feature` in `ui_components.py`; `hero()` is
  now a call to `hero_feature` ("Shoreline Remediation Intelligence", three capability points, neutral scope tags, two
  working buttons). The dashboard shows a "Featured locations" row of three cards built by `site_view.featured_sites()`
  from `data/demo/p5_sites.csv`, `results/mangrove/effect_by_year.csv` and the model registry; missing values read "not
  available". Card buttons drive the existing view, habitat and site controls. Option cards show the pipeline's
  recommendation category through `status_label`; an unknown or missing category is shown as such. No decision-engine,
  registry, model or report change. No new dependency or image.
- **Where:** `src/shoreline_remediation/{ui_components,ui_theme,site_view,dashboard}.py`, `tests/test_ui_stage2.py`
  (new), `tests/test_dashboard_v5.py` and `tests/test_p5_demo.py` (the legacy "Run" click now names the sidebar button),
  `docs/V5_1_HANDOFF.md` section 2b.
- **Result:** `python -m pytest tests` on Python 3.11: 423 passed, 0 failed, 0 skipped (379 existing + 44 new).
  Launched and inspected in headless Chromium at 1440 x 900 and 390 x 844: hero, headers, cards, status labels, card
  navigation and the evidence dialog work; no exception and no horizontal page overflow. Beach card button, keyboard
  navigation and the downloaded report were not checked in a browser.
- **Status:** Implemented and tested (software). Not scientific validation. Visual acceptance by the owner is open. No
  rocky-shoreline card yet (no rocky entry in the dashboard).

## 2026-11-15 (V5.1 Session 2, Stage 1): dashboard design foundation
- **Why:** `CLAUDE.md` section 6 and handoff section 10 step 1: a dark, premium theme built on one palette.
- **What:** `ui_theme.PALETTE` (eight colours) and a rewritten `CSS` (dark shell, hero banner, cards, buttons, focus
  rings, reduced motion, small screens). Chip CSS split out as `COMPONENT_CSS` so the HTML report stays light.
  `.streamlit/config.toml` is now one dark theme. Evidence grades and classes keep their meaning, order and fill
  styles; only chip contrast changed. No decision-engine, registry or model change. No new dependency or image.
- **Where:** `src/shoreline_remediation/{ui_theme,ui_components,ui_report}.py`, `.streamlit/config.toml`,
  `tests/test_ui_theme.py`, `docs/V5_1_HANDOFF.md`.
- **Result:** `python -m pytest tests` on Python 3.11.15: 379 passed, 0 failed, 0 skipped (371 existing + 8 new).
  Launched and inspected in headless Chromium at 1440 x 900 and 390 x 844 (salt marsh, mangrove, legacy view before
  Run): no exceptions. Beach tabs, map, downloaded report and keyboard navigation not checked.
- **Status:** Implemented and tested (software). Visual acceptance by the owner is open. Layout, navigation, landing
  page and rocky-shoreline entry are still to do (handoff section 10, steps 2 to 7).

## 2026-11-15 (V5.1 Session 1): architecture and scientific stabilisation
- **Why:** V5.1 stabilisation brief and `CLAUDE.md`: one decision pathway, honest validation reporting, transparent model
  status, safe abstention. No analysis was re-run and no validation result was changed.
- **What:**
  - Pathway: `site_view._rule_table` no longer calls the legacy `HybridDecisionModel`; it reads the pipeline report.
  - D41 (Proposed): rule-based recommendation categories, `decision_outcome`, `abstentions`, and an honest `rank_basis`
    on every option. Class letters A-E unchanged. Planting becomes Conditional while mechanical removal is excluded.
  - Unsupported habitats now return an explicit abstention instead of generic rule screening.
  - Registry: `governance` block on every entry, stricter promotion (`registry.promotion_report`), `governance_table`,
    failed F5 process model listed as a card, `Prediction.interval_status`.
  - NOAA ratings compared by software with the PDF text layer (126 of 126 match); status stays Proposed.
  - Validation figures reconciled in `docs/V5_1_VALIDATION.md`: the legacy 5/6 replay equals the always-active baseline.
- **Where:** `src/shoreline_remediation/{decision_pipeline,registry,model_interface,site_view,ui_evidence,ui_components,ui_report,ui_theme}.py`,
  `models/registry.json`, `validation/noaa_rating_source_check.py`, `results/v5_1/`, `tests/test_v5_1_governance.py`,
  `docs/V5_1_{IMPLEMENTATION,VALIDATION,HANDOFF}.md`.
- **Result:** `python -m pytest tests` on Python 3.11.15: 371 passed, 0 failed, 0 skipped (327 existing + 44 new). Dashboard
  launched and inspected in headless Chromium: no exceptions on the salt-marsh worked example.
- **Status:** Implemented and tested. Not a scientific validation. D41 awaits owner decision. F11 was not re-run.

## 2026-11-14 (V5): review response, four gated tests, beach screening, dashboard re-base
- **Why:** the v4 review of branch `model_v4` found that the oil term was never tested against a no-excess baseline, the deployed
  interval was calibrated in sample, F8b changed a rule after its run, AI-proposed numbers reached outputs, beaches had no habitat
  table, and the dashboard showed a made-up band and constant "confidence". Jaison made decisions D33-D40 the same day.
- **What:**
  - D33: owner attestation recorded for all 144 literature rows (his statement, not an independent check).
  - D34/D35: original F8 two-study rule restored (F8b Superseded); B023 direction defect fixed (no verdict changes); "insufficient
    evidence" kept apart from "no clear difference".
  - D36: ESI habitat table, NOAA 2017 response ratings transcribed, rule 160 fixed, beach scope tiers.
  - D37/D38: out-of-sample oil excess and per-class intervals as non-default options.
  - D39: sand-beach persistence model from DWH SCAT (baseline packaged).
  - D40: dashboard re-based on the decision pipeline; fabricated band and constant confidence removed.
  - Literature and data: Michel 2013 and 2017, Lindeberg 2018, Geng papers, sunken oil mat guide, Exxon Valdez lingering-oil and EVTHD data.
- **Files:** `docs/FINDINGS_V5.md` (43-51); `docs/V5_P0_PLAN.md`, `docs/V5_BEACH_SAND_PLAN.md`; `validation/v5_p0_*.py`,
  `validation/v5_beach_sand.py`; `results/v5_p0/`, `results/v5_beach/`, `results/f8_pooling/v3_original_rule/`,
  `results/f11_validation_v5/`, `results/v5_literature/`; `src/shoreline_remediation/{habitat,beach_model,ui_*}.py` and edits to
  `decision_pipeline`, `knowledge`, `noaa_crosswalk`, `scenario_composer`, `site_evidence`, `registry`, `site_view`, `dashboard`;
  `models/{oil_excess_oos_v1,p5_edge_loss_v2,beach_sand_persistence_v1}.json`; `data/knowledge/tables/`;
  `data/external/{scat_dwh_mobile,evos_lingering_oil,evthd_goa,evos_bioremediation_pilot}/`; docs and tests.
- **Run:** `python -m validation.v5_p0_oil_excess`; `python -m validation.v5_p0_intervals`; `python -m validation.v5_p0_cards`;
  `python -m validation.v5_beach_sand`; `python -m validation.literature_pooling`;
  `python -m validation.f11_integrated_validation --out-dir results/f11_validation_v5`; `python -m pytest tests` (327 tests, all passing on 14 Nov 2026 with Python 3.13).
- **Result:**
  - Gate 0.1 FAILED (MAE not below no excess in Barataria 1.036 vs 1.011, or Breton 1.743 vs 1.570).
  - Gate 0.2 FAILED (3 of 12 coverage groups outside 80-97%; Breton Winkler 11.28 vs 11.20).
  - Beach gates B-1 and B-2 FAILED (pooled integrated Brier 0.284 vs 0.216 baseline); baseline curve packaged.
  - F11 rerun: agreement 2 of 6 (v4: 2 of 6), always-active 5 of 6, method allowed 320 of 400 (v4: 264 of 400), allow-everything 400 of 400.
  - F8 restored rule: 0 benefit, 0 harm, 9 no clear difference, 24 no evidence.
- **Status:** Implemented; gated models Experimental (gates failed); dashboard Under validation (script-tested only, no browser check);
  not validated, not released. Commits are local; nothing was pushed.

---

## 2026-11-14: literature collection, D32, DIVER
- **Literature:** five AI agents (GPT, Gemini, Grok) collected 144 effect rows from 90 sources into
  `data/knowledge/literature_effects.csv` and `literature_sources.csv`; 31 open or US-government PDFs committed under
  `docs/reference/`, 11 all-rights-reserved PDFs kept locally in git-ignored `docs/reference/restricted/`; index
  `docs/reference/REFERENCE_INDEX.csv`. FINDINGS_V4 31.
- **D32:** oil excess scaled to a field-size-weighted literature estimate; checks C1c, B1c; heavy bias reduced, gate still
  fails. `validation/d32_oil_excess.py`, `models/oil_excess_d32.json`. FINDINGS_V4 32.
- **DIVER and SCAT** downloaded locally (git-ignored); PAH replicate sensitivity run, no change. FINDINGS_V4 33.
- **Status:** Under validation (literature rows AI-extracted, unchecked).

## 2026-11-14: V4 Track R (review fixes R1-R8)
- **R1** ranking tiers (D25); **R2** synthetic suitability out of the decision path (D26), literature guide and
  extraction template; **R3** clean-edge composer baseline (D27), checks C1b, C2b, B1b; **R4** one edge-loss number
  per site; **R5** wording; **R6** AI-PROPOSED provenance; **R7** covariance sensitivity, vegetation decay and
  heavy-oiling flag (D28), held-out headline, reports regenerated; **R8** repository hygiene, stays public (D29).
- **Files:** see commits 24a620f..HEAD; findings in `docs/FINDINGS_V4.md` sections 25-30.
- **Result:** decision-path ranking passes 3 of 5 SCAT checks and matches the documented method in 1 of 5
  historical cases (v3 3 of 5 came from the synthetic labels); composer coverage holds but heavy cells stay
  over-predicted by about 0.5 m/yr (D32 proposed); edge-loss headlines unchanged.
- **Rerun:** `python -m pytest tests` (176 pass); `python -m validation.historical_validation`;
  `python -m validation.scenario_composer_check_b`, `scenario_block_check_b`, `forecast_horizon_check_b`.
- **Status:** Under validation (awaiting Jaison's dashboard test and D32).

## 2026-11-14: v3 review and V4 programme plan
- **Why:** critical review of the branch found two output-changing defects (ranking order, oil double count)
  and several overstatements; Jaison asked for a plan to fix them and reach a final decision support system.
- **What:** `docs/V4_PROGRAMME_PLAN.md` (Track R: R1-R8 fixes; Track F: F0-F12 final system);
  review findings in `docs/REVIEW_NOTES.md` section R; V4 table and decisions D25-D31 (Proposed) in
  `docs/ROADMAP.md`; HANDOFF updated. Branch pushed to `origin/model_v3` (f2986f6) before this change.
- **Checked:** 167 tests pass on Python 3.11 (pytest and requirements-analysis installed).
- **Status:** Not started (plan only; awaiting Jaison's decisions D26, D27 choice, D29).

## 2026-11-12 (session 3): literature reconciliation and data inventory

### Scenario programme (Phase A1, A2; Phase C step 1)
- **Plan:** `docs/SCENARIO_PROGRAMME_PLAN.md`, committed before any analysis.
- **A1:** `validation/veg_recovery_curve.py`, tests, `results/veg_recovery/`, `models/veg_recovery_v1.json`.
  Result: suggestive only (held-out error 0.417 vs 0.450 baseline, interval of the difference includes zero;
  worse than baseline for heavily oiled sites). FINDINGS 14. Rerun: `python -m validation.veg_recovery_curve`.
- **A2:** `src/shoreline_remediation/scenario_composer.py`, `validation/scenario_composer_check.py`, tests,
  `results/scenario_composer/`. Check C1 passes (94% and 81% coverage); single-cell option ranges all overlap.
  FINDINGS 15. Not in the dashboard.
- **Phase C:** `docs/MANGROVE_INVENTORY.md`. FINDINGS 16.
- **A3:** `data/knowledge/` (evidence table, notes, elicited ranges; catalogued). No untested treatment is
  distinguishable from natural recovery; conditions for use recorded. FINDINGS 17.
- **Status:** Under validation.

## 2026-11-13: full walkthrough slide deck
- 92-slide deck (https://claude.ai/artifact/MeLp9tsyde7PwAHsnVCd8S) with 13 charts from results files and 11
  dashboard screenshots; number sources in `docs/deck/NUMBER_SOURCES.md`. Five dashboard views lack screenshots.

## 2026-11-13: PAH decline, mangrove model and mode, expert review

- **PAH decline:** `diver_soil.py`, `validation/pah_decline.py`, tests, `results/pah_decline/`. Sum validated
  (half-life 1.6 y heavy, 1.8 y moderate); hopane ratio does not decline, so loss is mostly physical.
  FINDINGS 22. Rerun: `python -m validation.pah_decline` (needs the DIVER files: `scripts/download_diver.sh`).
- **Mangrove:** `mangrove_model.py`, `validation/mangrove_damage.py`, `models/mangrove_damage_v1.json`,
  Habitat selector and mangrove mode in `site_view.py`. Dead roots and leaves per shoot validated within
  Galeta. FINDINGS 23. Rerun: `python -m validation.mangrove_damage`.
- **Expert review:** `data/knowledge/EXPERT_REVIEW.md`, revised `elicited_priors.csv`, approved
  `treatment_conditions.csv`, new `mangrove_screening.csv`. FINDINGS 24. Decisions D22-D24.
- 167 tests pass. **Status:** Under validation.

### Phase B1, Phase C1, DIVER structure
- **B1:** `forecast()` in `scenario_composer.py`, `validation/forecast_horizon_check.py`, tests (152 pass).
  7-year check in Barataria passes (92% of cells, 94% of blocks); heavy cells over-predicted by 0.53 m/yr.
  FINDINGS 19. Rerun: `python -m validation.forecast_horizon_check`.
- **C1:** `docs/GALETA_MANGROVE_DESCRIPTION.md`, `scripts/galeta_description.py`, `scripts/download_galeta.sh`
  (not run), `results/galeta/`; catalogue entry EXT-GALETA (raw data not committed). FINDINGS 20.
- **DIVER:** `docs/DIVER_SOIL_STRUCTURE.md`; `docs/PAH_DECLINE_PLAN_DRAFT.md` (Proposed, not run). FINDINGS 21.
- **Status:** Under validation; PAH analysis awaiting Jaison's choices.

### Phase A4: option differences, block-level composer, conditions, dashboard section
- **Plan:** A4 section of `docs/SCENARIO_PROGRAMME_PLAN.md` (committed first; amends the A2 labelling rule).
- **What:** paired-difference flags and `compose_block()` in `scenario_composer.py`;
  `validation/scenario_block_check.py`; "Compare options" in `site_view.py`;
  `data/knowledge/treatment_conditions.csv`; tests (149 pass).
- **Result:** check C2 passes (88% and 93% block coverage) but block ranges are only 17% narrower than cell
  ranges. Planting after mechanical cleanup is distinguished from natural recovery (-2.5 ha, -4.3 to -0.8, in
  the worked block by year 8); manual and mechanical are not; untested options cannot be ranked. FINDINGS 18.
- **Rerun:** `python -m validation.scenario_block_check`; `streamlit run src/shoreline_remediation/dashboard.py`.
- **Status:** Under validation (awaiting Jaison's test as a user).

### Stage 3b: foundation architecture (design only)
- **What:** `docs/ARCHITECTURE_FOUNDATION.md`: common data schema, model interface, knowledge tables,
  orchestration, process-informed layer in gated steps, offshore models as an upstream provider, model
  registry. Decisions D14 to D20, all **Proposed**; nothing built.
- **Status:** Not started (design awaiting Jaison's decisions).

### Stage 3a: soil layer check (SSURGO and SoilGrids against CRMS cores)
- **Why:** can soil maps stand in for measurements at sites without cores?
- **What:** plan committed first (`docs/SOIL_LAYER_CHECK_PLAN.md`); `scripts/fetch_soil_layers.py`,
  `validation/soil_layer_check.py`, tests; CRMS soil cores in `data/external/crms_soil/`, retrieved map values
  cached in `data/external/soil_layers/`.
- **Result:** null. Neither map beats the regional median for bulk density, organic matter or pH at 392
  sites; SoilGrids bulk density is 1.06 g/cm3 too high. SSURGO salinity ranks sites moderately (0.42).
  FINDINGS section 13.
- **Rerun:** `python -m validation.soil_layer_check` (uses the cache; `scripts/fetch_soil_layers.py` refetches).
- **Status:** Under validation (awaiting Jaison's review).

### Period-split check (did the heavy-oiling excess fade?)
- **What:** `validation/period_split_check.py`, tests, `results/period_split/`; plan committed first.
- **Result:** inconclusive. Heavy minus clean 0.42 (0.07 to 0.76) in 2010-2015 and 0.28 (-0.27 to 0.84) in
  2015-2017; Light shore shows an unexpected +0.78 in 2015-2017. Adjusted range for the headline is now 0.42
  to 0.85. Part B (Landsat split) not run and not recommended (sensor gap in 2012). FINDINGS section 12.
- **Rerun:** `python -m validation.period_split_check`.
- **Status:** Under validation.

### Stage 3 downloads
- GRIIDC Landsat marsh cover fetched (1.11 GB, one 2009-09-02 scene, not committed; catalogue entry updated).
  Huettel 2018: buried-oil n-alkane series found (GRIIDC R5.x278.000:0015) and committed; records 0003-0005
  return 404.

### Stage 2: dataset inventory (no modelling)
- **Why:** find chemistry, vegetation and erosion data beyond the proof of concept, and say what is reachable.
- **What:** ten sources checked (`docs/STAGE2_INVENTORY.md`). Five small datasets committed under
  `data/external/` with `SOURCE.md` (Turner 2016 islands, Zengel 2022 meta-analysis, Chandeleur shoreline and
  fingerprinting, Huettel 2018); ten catalogue entries added (`scripts/build_catalogue.py`);
  `scripts/download_diver.sh` (not run) for the 630 MB NOAA DIVER files, which are git-ignored;
  DIVER pointers added to 7 rows of `data/meta/planned_variables.csv`.
- **Result:** DIVER wetland files hold 14,926 soil sample IDs at 202 stations, 2010-2013, with censoring
  flags (counts verified from the files); nearshore files 1,870 sediment sample IDs. These do not match the
  counts in the brief (1,894; 1,731). Not obtained: plant-oiling layers, Michel 2017 data (none found),
  Landsat marsh cover (1.11 GB, reachable, not downloaded), six of nine Huettel records.
- **Also:** `docs/LITERATURE_TO_DOWNLOAD.md` (papers not reachable); `docs/PERIOD_SPLIT_CHECK_PLAN.md`
  (proposed, not run); dashboard uplift caption now says "average over 2010-2015"; correction note for the P6
  artifacts in `docs/P6_POC_REPORT.md` (artifacts themselves not edited).
- **Rerun:** `python scripts/build_catalogue.py`; `python -m pytest tests` (108 pass).
- **Status:** Under validation (awaiting Jaison's review of the inventory).

### Stage 1: P1 headline against Challenger et al. 2021 and Turner et al. 2016
- **Why:** Challenger et al. report extra loss on heavily oiled shore only in the first year; P1 reports
  0.85 m/yr averaged over 2010-2015.
- **What:** comparison of periods, sites, oiling definitions and methods (`docs/FINDINGS_2026-11-11.md`
  section 11; extraction in `docs/STAGE1_PAPER_EXTRACTION.md`; `docs/REVIEW_NOTES.md` C0). No analysis rerun.
- **Result:** not contradictory; P1 gets a note, not a revision. 0.85 m/yr is a period average, compatible with
  a 1 to 2.5 year effect; "for at least seven years" (section 6) withdrawn. Our NAIP data show no fade
  (implied 2015-2017 excess about 1.04 m/yr), so residual exposure confounding remains possible.
- **Not done:** full texts not reachable (abstracts, Turner's data file and Zengel 2022 Table 1 only).
  Period-split check proposed, not run. Dashboard and P6 wording not changed (needs Jaison).
- **Status:** Under validation (awaiting Jaison's review).

## 2026-11-11 (session 2): proof-of-concept track

### P6: walkthrough deck for non-specialists
- 69 slides in six parts, with aerial photos of the worked-example edge (2010 vs 2015, true colour and
  near-infrared), a study-area map, step charts and 13 dashboard screenshots. Link in `docs/P6_POC_REPORT.md`;
  generators in `scripts/walkthrough_deck/`. Dashboard caption updated: D13 approved.

### P6: proof-of-concept report and slides
- **Why:** the deliverable for project leads (roadmap P6).
- **What:** an editable report (claim, what the tool does, evidence with two charts, failures, limits, a phased
  path to scale with gates, method, sources) and a 12-slide deck with speaker notes. Links and the source of
  every number: `docs/P6_POC_REPORT.md`.
- **Checked:** numbers against results files; citations against publishers' records (one wrong title corrected).
- **Status:** Under validation (awaiting Jaison's review). D13 approved by Jaison.

### Corrected: rounding of P3 results
- Several P3 values had been rounded up in the docs (e.g. 1.8849 reported as 1.89, -0.6347 as -0.64). Corrected in
  FINDINGS section 9, HANDOFF and here from `results/p3_treatment/A_prespill_adjusted.csv`. No analysis changed.

### P5: demo dashboard ("Site evidence (real data)" view)
- **Why:** leads need to see the tool working on a real site, with intervals and scope flags (roadmap P5; D9, D11).
- **What:** a new first tab: map of Louisiana salt-marsh edge cells; site picker (worked example, any edge cell,
  or a new site typed in); expected edge loss with a 90% interval and the heavy-oiling uplift as a separate range;
  out-of-scope and extrapolation flags with reasons; rule screening for the site beside field evidence per option
  (Zengel 2022 erosion, years 0-2 and 2-8; Zengel 2015 vegetation cover). The old view is now the second tab,
  labelled as rules and synthetic data; its model tab is relabelled "Method test (synthetic data)". The oil search
  offers spill oils only by default.
- **Files:** `docs/P5_DEMO_PLAN.md` (committed before the build), `scripts/build_p5_demo.py`,
  `models/p5_edge_loss_v1.json` (model card with coefficients, interval, training ranges and checksums),
  `data/demo/p5_sites.csv`, `docs/P5_WORKED_EXAMPLE.md`, `src/shoreline_remediation/site_evidence.py` (logic),
  `src/shoreline_remediation/site_view.py` (layout), `dashboard.py`, `oil_library.py` (`SPILL_OIL_TYPES`),
  `tests/test_p5_demo.py` (12 checks incl. Streamlit AppTest), `tests/test_oil_library.py`.
- **Run:** `python scripts/build_p5_demo.py` after any change to `data/external/p2`; then
  `streamlit run src/shoreline_remediation/dashboard.py`.
- **Result:** held-out error 1.30 vs 1.42 m/yr for the no-predictor baseline; worked example 1.42 m/yr (-1.74 to
  4.30), observed 1.54. See FINDINGS section 10.
- **Fixed on the way:** `openpyxl` added to `requirements.txt` (clean-install check failed without it);
  `streamlit>=1.67` (map colours and the `width` argument; `use_container_width` is deprecated); hero title was
  invisible (dark text on the dark banner).
- **Status:** Under validation (awaiting Jaison's test as a user). D13 (treatment mapping) proposed.

### Flagged: soil and sediment chemistry not in the PoC
- **Why:** Jaison asked for the missing soil and sediment chemistry to be flagged with comments.
- **What:** `data/meta/planned_variables.csv` (15 variables: why each matters, status absent/partial, open-source
  candidates, comments), rendered at the end of `docs/VARIABLE_DICTIONARY.md`; soil shear strength (`SHST_KPA`,
  Zengel 2022) added to the dictionary; REVIEW_NOTES E0 gives the reasoning and priorities.
- **Status:** Completed as documentation; the variables themselves are future work.

### P4: data catalogue and variable dictionary
- **Why:** every input to the demo must be traceable to source, date and method (roadmap P4).
- **What:** 18 datasets and 49 files catalogued with role (external, derived, synthetic, reference,
  instrument), source, licence, date, how obtained and read, and SHA-256; 40 variables defined with unit,
  type, valid range or allowed values, missing-value rule, derivation and module.
- **Files:** `scripts/build_catalogue.py`, `data/meta/catalogue.csv`, `data/meta/variable_dictionary.csv`,
  `docs/DATA_CATALOGUE.md`, `docs/VARIABLE_DICTIONARY.md`, `tests/test_data_catalogue.py` (42 checks).
  Also `scripts/run_p2_measurements.sh` and `scripts/landsat_split.sh`, which record how the P2 tables were
  built (previously only in a scratch folder), and `docs/REVIEW_NOTES.md` (open scientific concerns).
- **Run:** `python scripts/build_catalogue.py` after any data change; `pytest tests/test_data_catalogue.py`.
- **Found:** the oil table includes non-oils (an anti-knock additive at API -37.2); noted for P5.
- **Status:** Under validation (awaiting Jaison's check of definitions). D11 approved; D12 implemented.

### P3: cleanup treatment and marsh-edge erosion
- **Why:** the tool needs data-based treatment effects, not only rules (roadmap P3).
- **What:** searched SCAT, the NCEI DIVER archive, NOAA TM OR&R 42 and the DWH administrative record for
  segment-level cleanup records (none public in usable form); obtained Zengel et al. 2022 plot data from GRIIDC
  (CC0); pre-specified contrasts of erosion change by treatment; checked NAIP edge loss against field erosion.
- **Files:** `docs/P3_TREATMENT_PLAN.md`, `data/external/zengel2022/` (with `SOURCE.md`),
  `validation/p3_treatment_erosion.py`, `tests/test_p3_treatment_erosion.py`, `results/p3_treatment/`;
  `treatment_effects.erosion_effects()` and `erosion_prior()` added with tests.
- **Run:** `python -m validation.p3_treatment_erosion`
- **Result:** 2010-2012 vs untreated: manual -0.63 m/yr (-1.25 to -0.02), mechanical +0.28 (-0.17 to 0.73),
  mechanical + planting -1.47 (-2.06 to -0.88); oiling +1.88 vs reference, fading to +0.21 by 2012-2018.
  NAIP ranks plots like field data (Spearman 0.68) but reads 1.2 m/yr low.
- **Status:** Under validation (awaiting Jaison's review). D11 proposed.

### Changed: documentation and tracking
- `CHANGELOG.md` (this file) and `requirements-analysis.txt` added. `README.md` gains a section on the
  real-data evidence. D9 approved by Jaison.

### P2: leave-one-basin-out test of edge-loss prediction
- **Why:** leads will ask whether the model works on marsh it was not fitted to (D6).
- **What:** 39,320 salt-marsh edge cells along the oiled Louisiana coast, split into four basins by fixed
  geographic lines (D8). Models fitted on other basins predict the held-out basin: no-predictor baseline (M0),
  exposure + pre-spill trend (M1), M1 + oiling class (M2, primary), boosted trees (M3). 90% intervals from
  inner leave-one-basin-out residuals.
- **Files:** `docs/P2_BASIN_HOLDOUT_PLAN.md` (plan and 5 amendments, committed before the run),
  `scripts/build_edge_cells.py --louisiana`, `scripts/assign_basins.py`, `validation/p2_basin_holdout.py`,
  `tests/test_p2_basin_holdout.py`, `data/external/p2/`, `results/p2_basin_holdout/`.
- **Run:** `python -m validation.p2_basin_holdout data/external/p2`
- **Result:** "partly transfers". Beats the baseline in both tested basins (pooled error 1.35 vs 1.47 m/yr),
  90% intervals cover 89%; oiling class adds no cell-level accuracy over exposure; heavy-oiling uplift 0.34 to
  0.83 m/yr depending on training basins. Boosted trees worse than linear.
- **Found:** the 2010 land/water rule fails on tiles dominated by open water or river plume. Birdfoot delta,
  eastern Breton Sound and south-west Barataria excluded by a class-blind rule; backlog D10.
- **Status:** Under validation (awaiting Jaison's review).

### P1: pre-spill erosion check and finer exposure
- **Why:** the NAIP result had no pre-spill image; heavy oil landed on exposed shore, which erodes anyway.
- **What:** Landsat short-wave infrared unmixed per scene, three epochs (1998-2000, 2007-2009, 2014-2016);
  open water within 250 m and fetch from 2010 NAIP; four pre-specified checks.
- **Files:** `docs/P1_PRESPILL_CHECK_PLAN.md`, `scripts/exposure_metrics.py`, `scripts/landsat_edge_fraction.py`,
  `validation/p1_prespill_check.py`, `tests/test_p1_prespill_check.py`, `data/external/p1/`,
  `results/p1_prespill/`.
- **Run:** `python -m validation.p1_prespill_check data/external/p1`
- **Result:** "revised". Landsat confirms the post-spill gap (1.15 m/yr) but heavy-oil shore was already
  eroding 0.30 m/yr faster before the spill; headline 0.85 m/yr (0.49 to 1.22); 0.62 to 0.85 across exposure
  adjustments (exploratory). Robust to the P2 measurement problem (0.80 m/yr after filtering).
- **Status:** Under validation. Jaison: Landsat land-fraction maps not very clean; revisit (D10).

### Roadmap and decision register
- `docs/ROADMAP.md` (mirrored to the claude.ai project as `claude/roadmap.md`): module status, the six
  proof-of-concept milestones P1-P6, the full programme M1-M10, and decisions D1-D10.

## 2026-11-11 (session 1, continued): marsh-edge loss from NAIP

### NAIP marsh-edge loss, Barataria Bay
- **Why:** CRMS plots and 30 m Landsat pixels were too coarse for the 10-20 m oiled marsh band.
- **What:** 100 m edge cells from SCAT; NAIP 1 m imagery 2010-2017; land/water per tile (2010 Otsu rule;
  later years a classifier trained on 2010 interior pixels); edge loss vs oiling class within 2 km blocks.
- **Files:** `docs/NAIP_EDGE_LOSS_PLAN.md` (plan, then amendments), `scripts/build_edge_cells.py`,
  `scripts/naip_edge_extract.py`, `validation/naip_edge_loss.py`, `tests/test_naip_edge_loss.py`,
  `data/external/naip_edge/`, `results/naip_edge_loss/`.
- **Run:** `python -m validation.naip_edge_loss data/external/naip_edge`
- **Result:** heavy-oiled edge lost 1.00 m/yr more than clean edge (0.58 to 1.43), rising with oiling class
  (later revised by P1). NAIP 2013 dropped as too hazy (D2).
- **Status:** superseded as headline by P1.

## 2026-11-11 (session 1): first real Deepwater Horizon data

### SCAT shoreline oiling
- NCEI Accession 0163818 Louisiana layers (maximum oiling; all surveys including No Oil Observed).
  `scripts/download_scat.sh`. The NCEI download service failed; the HTTPS archive path works.

### 2010 event study at CRMS marsh stations
- `scripts/match_crms_scat.py`, `validation/oil_event_study.py`, `data/external/scat_dwh/`.
- Result: no detectable effect (20 oiled vs 24 unoiled sites); most stations sit hundreds of metres from the
  oiled edge, so they cannot see it. Status: Completed (null, documented).

### Landsat NDVI recovery, northern Barataria Bay
- `scripts/select_barataria_sites.py`, `scripts/landsat_ndvi.py`, `scripts/pool_ndvi_for_runner.py`,
  `data/external/landsat_barataria/`, `results/satellite/`.
- Result: no detectable drop; placebo check failed; does not reproduce Mo et al. (2017). Status: Completed
  (null, documented).

### Treatment effects from Zengel et al. (2015)
- `src/shoreline_remediation/treatment_effects.py`, `data/external/zengel2015/` (authors' Excel supplement),
  `tests/test_treatment_effects.py`.
- Result: manual cleanup +34 points vegetation cover at year 2 vs untreated (19 to 49); mechanical +5
  (-12 to 22); planting (randomized) +69 points Spartina. Priors only (D3). Status: Completed.

### Dashboard: oil chosen by name
- `src/shoreline_remediation/dashboard.py`, `oil_library.search_options()`, `tests/test_oil_library.py`.
- 1,460 NOAA ADIOS oils; category set from measured API gravity and pour point at the scenario temperature.
  Status: Completed (checked with Streamlit's app tester).

## Earlier (previous chat, restored from zip as commit 6647423)
- Process-model mass-balance fix; ranking fixes (no placeholder scores); marsh recovery model fitted to 63
  published cases (fails baseline, D4); expert scoring protocol; event-study and satellite-recovery code;
  NOAA ADIOS oil library; CRMS marsh data. Details: `docs/PROCESS_MODEL_AUDIT.md`, `docs/RANKING_FIXES.md`,
  `docs/HANDOFF.md`.

## Known open issues
- See `docs/REVIEW_NOTES.md` for the full list of open scientific and technical concerns.
- No soil or sediment chemistry in any model (REVIEW_NOTES E0; `data/meta/planned_variables.csv`).
- D10: land/water classification fails on water-dominated and plume tiles; Landsat maps not clean (Jaison).
- One spill only; transfer shown within Louisiana, not to a new spill (D6).
- Cleanup method per shoreline segment: no public machine-readable records (P3); treated stretches exist only
  as map figures in NOAA TM OR&R 42.
- NAIP absolute edge-loss rates read about 1.2 m/yr below field measurements (P3, analysis C).
- `seaborn` was imported by existing code but missing from `requirements.txt` (now in requirements-analysis.txt).
- `openpyxl` was missing from `requirements.txt` (fixed in P5).
