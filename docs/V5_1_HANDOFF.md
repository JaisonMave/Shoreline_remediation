# V5.1 handoff

Updated 15 November 2026, end of **Session 1** (architecture and scientific stabilisation). Read this first in the next
session, then go straight to "Next session: exact starting point". Do not repeat the Session 1 audit.

## 1. Branch and commit

- Session branch: `claude/shoreline-v5-1-stabilisation-5qqym3`, cut from `model_v4` at the same commit.
- Commit before Session 1: `37835e7` ("Document project guidelines for shoreline remediation platform").
- Session 1 was accepted by the owner and committed as one commit on this branch ("V5.1 Session 1: architecture and
  scientific stabilisation"), then pushed to `origin/claude/shoreline-v5-1-stabilisation-5qqym3`. Find its hash with
  `git log -1 --oneline`. It was authorised for this branch only: not pushed to `model_v4`, not merged, no pull request.
- Start every session with `git status`, `git branch --show-current` and `git log -1 --oneline`.

## 2. Completed objectives (Session 1)

| Objective | State |
|---|---|
| One authoritative pathway `dashboard → site_view → ui_pipeline → decision_pipeline.run_decision` | Implemented, tested, seen running |
| Legacy call removed from the production site view | Implemented, tested |
| Recommendation categories, decision outcome, ranking basis (D41) | Implemented, tested; **Proposed**, owner to confirm |
| Abstention: unsupported habitat, missing inputs, out of scope, limited evidence | Implemented, tested |
| Registry governance record and stricter promotion | Implemented, tested |
| Validation figures reconciled (5/6, 2/6, baseline) | Documented in `V5_1_VALIDATION.md` |
| NOAA transcription check against the PDF | Software check done, 126/126; human review still open |

## 3. Files created or modified

Created:
- `docs/V5_1_IMPLEMENTATION.md`, `docs/V5_1_VALIDATION.md`, `docs/V5_1_HANDOFF.md`
- `tests/test_v5_1_governance.py` (44 tests)
- `validation/noaa_rating_source_check.py`
- `results/v5_1/noaa_rating_source_check.csv`, `results/v5_1/noaa_rating_source_check_summary.txt`

Modified:
- `src/shoreline_remediation/decision_pipeline.py`: categories, outcome, abstentions, rank basis, unsupported-habitat
  abstention, prerequisite rule, headline clause, `PIPELINE_VERSION = "f9-v3"`
- `src/shoreline_remediation/registry.py`: `governance_gaps`, `failed_gates`, `promotion_report`, `governance_table`,
  stricter `resolve_state`, `_attach_governance`
- `src/shoreline_remediation/model_interface.py`: `Prediction.interval_status`
- `src/shoreline_remediation/site_view.py`: `_rule_table` reads the pipeline report; legacy `_screen` removed
- `src/shoreline_remediation/ui_evidence.py`, `ui_components.py`, `ui_report.py`, `ui_theme.py`: carry and show the
  new fields; `unsupported_habitat` tier
- `models/registry.json`: `governance` blocks; `process_model_v2` card entry
- `tests/test_f9_pipeline.py`, `tests/test_v5_p0.py`: one assertion each, to allow the new card entry
- `README.md`, `CHANGELOG.md`, `docs/ROADMAP.md` (D41), `docs/ROADMAP_STATUS.md`

## 4. Architectural decisions

1. `run_decision()` stays the only place that assigns classes and categories. The UI never recomputes them; it reads
   `OptionView.category*` and `ReportView.decision_outcome / abstentions / recommendation_summary`.
2. Categories are a pure function (`decision_pipeline._category`) of class letter, evidence state, scope tier and an
   excluded prerequisite. Class letters A to E are untouched, so F8, F9 and F11 outputs keep their meaning.
3. Abstention reuses the refusal path (`_refuse`) with a `tier` argument; a new tier is one more key in
   `OUTCOME_LABELS` and `ui_theme.TIER_TEXT`.
4. Governance lives in `models/registry.json`, not in the cards, so historical cards are not rewritten.
   `registry.governance_table()` is the single source for the Session 3 model-validation view.
5. Legacy code is kept and labelled, not deleted: `decision_framework`, `fast_engine`, `ml_models`, `process_model`,
   `scenario_runner`, `validation_panel`, `ui_scenario`. Only `dashboard.py` imports `ui_scenario`.

## 5. Scientific limitations (unchanged by this session)

See `V5_1_VALIDATION.md`. In short: one spill per data model; validated numbers only for salt-marsh edge loss in
three Louisiana basins and DWH soil PAH sum; the edge-loss interval is not independently validated; composer, oil
excess, vegetation curve, mangrove damage, sand-beach persistence and the process model are experimental or failed;
no expert responses; NOAA tables and D36 mapping are Proposed; no replay metric shows skill.

## 6. Tests

Environment: Python 3.11.15 in a fresh virtual environment, `pip install -r requirements-analysis.txt`
(includes `requirements.txt` and `pytest`). The documented launcher uses Python 3.11.

| Command | Result |
|---|---|
| `python -m pytest tests -q` (before any change) | 327 passed, 0 failed, 0 skipped |
| `python -m pytest tests/test_v5_1_governance.py -q` | 44 passed, 0 failed, 0 skipped |
| `python -m pytest tests -q` (after all changes) | **371 passed, 0 failed, 0 skipped**, 257 warnings (pandas and openpyxl deprecation notices), about 2 minutes |
| `python -m validation.noaa_rating_source_check` | 126 of 126 rows match the PDF text |

`test_noaa_transcription_matches_the_source_pdf_text` skips itself when `pdftotext` (poppler) is not installed; it
ran here.

Browser check (real, not just script): `streamlit run src/shoreline_remediation/dashboard.py` was launched and the
"Site evidence" salt-marsh worked example was loaded in headless Chromium at 1440 x 900. No Streamlit exception;
"Decision outcome", the "What the platform does not state" expander and the re-based rule table rendered. **Not
checked in a browser:** mangrove and beach tabs, the legacy scenario view, the HTML report download, dark theme,
narrow screens. Python 3.13 was not re-run this session.

Not re-run: F11 (`results/f11_validation_v5/` is from 14 Nov). Class letters did not change, so its figures should be
unaffected, but that is an expectation, not a check.

## 7. Known bugs and open issues

1. **No rocky-shoreline entry in the dashboard.** `site_view.HABITATS` has marsh, mangrove and four beach types. The
   pipeline supports `rocky_shore` (ESI 1A, 8A) and is tested, but the required rocky demonstration case cannot be
   reached from the UI.
2. The dashboard is still the V5 light theme; none of the `CLAUDE.md` palette is applied.
3. The headline for the worked example still opens with planting as "field evidence of benefit" and only then says
   it is conditional. Correct but awkward; reword when the answer card is redesigned.
4. The answer card shows the class-based grade chips; the new category label is shown only in the rule table and the
   HTML report. Option cards should show the category (Session 3).
5. `registry._promotion_summary` still accepts the word "cover" as "coverage reported" (see `V5_1_VALIDATION.md` 3).
6. `noaa_crosswalk.py` page references (2013 manual) are unverified; legacy view only.
7. Mudflat, peat and tundra borrow salt-marsh evidence (declared, not fixed). Owner decision needed.

## 8. Decisions awaiting the owner

- **D41**: accept the category rules; accept the sixth label "Allowed, no demonstrated benefit"; decide whether
  "Recommended" is too strong for one-site observational evidence carried by an experimental model.
- Earlier open items still stand: D36 mapping, D40 visual acceptance, F8b keyword precedence.

## 9. Incomplete tasks

Session 1 is complete against its criteria. Sessions 2 and 3 have not started.

## 10. Next session: exact starting point (Session 2, premium dashboard foundation)

Do these in order. Each step is independently testable.

1. **Design system.** In `src/shoreline_remediation/ui_theme.py` add a `PALETTE` dict with the eight `CLAUDE.md`
   colours and rewrite the `CSS` string (line 199 onward) around them: page background `#080D17`, secondary
   `#111A29`, cards `#182438`, teal `#28B8A5`, blue `#4E9BE8`, highlight `#B6D9CF`, text `#F4F7FA` / `#A6B2C2`. Set the
   same values in `.streamlit/config.toml` (`[theme] base = "dark"`). Keep `GRADES` and `CLASS_STYLE` semantics; only
   recolour for contrast on dark. `ui_components.is_dark()` and `themed_fig()` must keep working for matplotlib and
   Altair charts.
2. **Reusable components.** In `ui_components.py` add `section_header(title, kicker)`, `status_label(category)`
   (one colour per `decision_pipeline.CATEGORY_ORDER` entry), `site_card(...)`, `card_row(cards)` (horizontal scroll
   via CSS), and `hero_feature(...)`. Replace the body of `hero()` rather than adding a second hero.
3. **Navigation and landing page.** In `dashboard.py` replace the two-item `st.segmented_control` with a page state
   in `st.session_state["page"]`: `landing`, `site`, `evidence`, `models`, `legacy`. Create
   `src/shoreline_remediation/ui_landing.py` with `render_landing()`: platform name "Shoreline Intelligence", a
   featured Bay Jimmy section (cell `8018_32612`), habitat cards, and three case-study cards (Bay Jimmy salt marsh,
   rocky shoreline, mangrove). Each card button must set the page and `st.session_state["site_habitat"]`.
   Every figure on a card must come from `site_evidence.load_sites()` or the habitat table; no ratings, no invented
   numbers. The legacy scenario view moves under a clearly labelled "Legacy and research" entry.
4. **Rocky shoreline.** In `site_view.py` add `HabitatView` entries for ESI 1A ("Exposed rocky shore",
   `shoreline_type="rocky_shore"`, `esi="1A"`) and ESI 8A ("Sheltered rocky shore", `esi="8A"`) using
   `_beach_renderer` generalised to a `_screening_renderer` (it already calls `P.decision_for_scenario`). Confirm
   the page shows the `no_site_forecast` abstention and no numerical forecast.
5. **Site assessment page.** Restructure `site_view.render_marsh` into sections: location and habitat, available
   observations (label each value as observed, derived or model estimate; show "not available" for missing ones),
   contamination (SCAT oiling), shoreline condition (observed NAIP rate where present), data availability table,
   assessment limitations (`view.abstentions`), map.
6. **Imagery.** The repository has no coastal photographs. Do not hot-link images. Either use CSS gradients and
   inline SVG, or add properly licensed images under `src/shoreline_remediation/assets/` with a credits file. Decide
   with the owner if photographs are wanted.
7. **Tests.** Extend `tests/test_dashboard_v5.py` (Streamlit `AppTest`) for landing page render, each card button
   changing the page, and the rocky page. Then run the browser check for landing, Bay Jimmy, rocky and mangrove.

Session 3 then covers: option cards with categories and "why" explanations, scenario comparison, an evidence
explorer, the model-validation page built on `registry.governance_table()`, and the full report.
