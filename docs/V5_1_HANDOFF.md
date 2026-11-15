# V5.1 handoff

Updated 15 November 2026, end of **Session 3, Stage 5** (ESI 1A/8A headline wording, five-part answer card, option-card wording).
Stage 5 is implemented, tested (537 passed) and seen running in a browser, and is committed to `model_v5_1` (hash in section 1a). Canonical branch for V5.1: **`model_v5_1`** (see section 1a). Session work was done on the harness branch `ccr-bebfcb64-immuzm`, which was started from `29aba8d`. Session 2 Stages 1 to 4 are committed (`e502dfa`, `7894759`, `2008c19`/`cf659e9`, `710aefe`); Session 1 is committed. Read
section 2g and then section 10a ("Next session: exact starting point") first. Sections 2a to 2f and section 10 are the Session 2 record and are
kept for history; their test counts (371, 510) were correct at the time and are superseded by section 6a. Do not repeat the Session 1 audit.

## 1. Branch and commit

- Session branch: `claude/shoreline-v5-1-stabilisation-5qqym3`, cut from `model_v4` at the same commit.
- Commit before Session 1: `37835e7` ("Document project guidelines for shoreline remediation platform").
- Session 1 was accepted by the owner and committed as one commit on this branch ("V5.1 Session 1: architecture and
  scientific stabilisation"), then pushed to `origin/claude/shoreline-v5-1-stabilisation-5qqym3`. Find its hash with
  `git log -1 --oneline`. It was authorised for this branch only: not pushed to `model_v4`, not merged, no pull request.
- Session 2 works on branch `claude/shoreline-v5-1-dashboard-design-ot1i5s`, which starts at the Session 1 commit
  `f2b3e51`. Session 2 Stage 1 is committed as `e502dfa882f33040677cb4abd161425de66ad993` (message "V5.1 Session 2 Stage 1: premium dark dashboard design foundation") and pushed to this branch only. The commit hash is recorded in a follow-up commit, because a commit cannot contain its own hash.
- Start every session with `git status`, `git branch --show-current` and `git log -1 --oneline`.

## 1a. Canonical branch, release state and architecture summary (V5.1)

- **Canonical V5.1 branch: `model_v5_1`** on `https://github.com/JaisonMave/Shoreline_remediation`. It carries the full history from the V4 baseline `model_v4` (`37835e7`) through Session 1 (`f2b3e51`), Session 2 Stages 1 to 4
  (`e502dfa`, `7894759`, `2008c19`/`cf659e9`, `710aefe`) and Session 3 Stage 5 (the tip commit, "Complete V5.1 shoreline decision support platform"; a commit cannot record its own hash, so use `git log -1 model_v5_1`).
- `model_v4` is the preserved historical V4 branch and was not modified. `model_v3` is the older historical branch. `main` is GitHub's default branch and has an unrelated two-commit history ("Add files via upload"); it was preserved as is.
- The earlier temporary V5.1 branches (`claude/shoreline-v5-1-stabilisation-5qqym3`, `claude/shoreline-v5-1-dashboard-design-ot1i5s`, `ccr-ed209fd7-hn5mdk`) were ancestors of `model_v5_1` with no unique commits and no pull requests, and were removed
  from GitHub during consolidation; `git ls-remote --heads origin` shows the actual remote state. New work starts from `model_v5_1`; do not build on a harness session branch.
- Architecture: `dashboard.py` -> `site_view.py` -> `ui_pipeline.py` -> `decision_pipeline.run_decision()` is the only decision pathway. `run_decision()` assigns classes (A to E), recommendation categories, evidence states, outcomes and abstentions;
  `ui_evidence.py` (view models, `answer_sections`), `ui_components.py`, `ui_theme.py` and `ui_report.py` only read and present those fields. Legacy views stay under "Legacy and research" and do not drive recommendations.
- Stages: 1 design foundation (2a); 2 reusable components and hero (2b); 3 landing page, navigation, site discovery (2d, 2e); 4 rocky-shoreline screening pages and UI corrections (2f); 5 headline wording, five-part answer card, option-card wording (2g).
- Evidence-category semantics: Recommended; Conditional; Natural recovery with monitoring (reference); Allowed, no demonstrated benefit (evidence exists, no clear difference); Insufficient evidence (no eligible evidence rows); Excluded. Eligibility is never effectiveness, and insufficient evidence is never ineffectiveness.
- Provenance limits that still apply: NOAA 1A/8A ratings are AI-transcribed and Proposed (not human-verified); the literature table is AI-extracted and not checked by a person; no expert review exists; rocky-shore effectiveness is not numerically validated; the composer and veg/oil-excess/sand-persistence components stay experimental; F5 and D32 failed their gates.
- Final verification record: `/tmp/claude-0/venv/bin/python -m pytest -q` = 537 passed, 0 failed, 0 skipped; 37-case pipeline comparison against `29aba8d` identical apart from the intended headline sentence; desktop (1440) and mobile (390) full-card screenshots inspected for ESI 1A (medium oil), ESI 8A (medium oil) and the salt-marsh worked example, plus rendered text checks of four beach types and mangrove.
- Install: `python -m venv <dir>; <dir>/bin/pip install -r requirements.txt pytest seaborn statsmodels pyproj` (the last three are analysis-only imports some tests need; the documented launcher uses Python 3.11, this session used 3.13). Run the app with `streamlit run src/shoreline_remediation/dashboard.py`.
- Next priorities, in order: (1) Evidence Explorer page (section 10a step 3); (2) Model Validation page (step 4); (3) navigation, QA and demonstration readiness; (4) human verification of the NOAA 1A/8A ratings and the AI-extracted literature table; (5) the latent `_headline` and class A wording items in section 2g. Do not redo Stages 1 to 5.

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

## 2a. Session 2, Stage 1: design foundation (implemented, tested, seen running; committed as `e502dfa`)

Scope was the theme only. The decision engine, the registry, the models and all Session 1 governance are untouched.

- `ui_theme.PALETTE`: the eight `CLAUDE.md` colours, the single source of dashboard colour. `PALETTE_DERIVED` adds a
  hairline border (`#26344D`) and a raised-card tone. `GRADE_COLOURS_DARK` lightens the five evidence-grade chip
  colours for contrast on dark cards; grade and class meanings, order, fill styles and symbols are unchanged.
- CSS is now two layers. `COMPONENT_CSS` (chips, class labels, AI-proposed block) has no fixed text or background
  colours and is what the HTML report embeds, so **the downloaded report stays light and printable**. `CSS`
  (injected by `ui_components.inject_css`) adds the dark shell: page background with soft teal and blue glows, hero
  banner (CSS gradients only, no images), cards, expanders, metrics, tables, teal primary button with dark label,
  tabs, focus rings, reduced-motion and small-screen rules. All colours are CSS variables (`--sr-teal` and so on).
- Ready for Stage 2 but **not yet used by any component**: `.sr-kicker`, `.sr-section`, `.sr-card`, `.sr-row`
  (horizontal scroll row).
- `.streamlit/config.toml`: one dark theme (`base = "dark"`) with the palette; the old light and dark pair is removed.
  The dashboard is now dark only. `ui_components.is_dark()` returns true in the browser, so matplotlib and Altair
  text uses `PALETTE["text"]`.
- No new dependency, no image, no web font.

Files: modified `src/shoreline_remediation/ui_theme.py`, `src/shoreline_remediation/ui_components.py` (one line,
`text_colour`), `src/shoreline_remediation/ui_report.py` (one line, embeds `COMPONENT_CSS`), `.streamlit/config.toml`,
`CHANGELOG.md`, this file. Created `tests/test_ui_theme.py`.

Tests (Python 3.11.15, fresh virtual environment, Streamlit 1.67.0):

| Command | Result |
|---|---|
| `python -m pytest tests/test_ui_theme.py -q` | 8 passed, 0 failed, 0 skipped |
| `python -m pytest tests -q` | **379 passed, 0 failed, 0 skipped** (371 existing + 8 new), 257 warnings, about 2 minutes |
| `python -m pytest tests/test_ui_theme.py tests/test_dashboard_v5.py tests/test_v5_1_governance.py -q` (after the last CSS edits) | 71 passed, 0 failed, 0 skipped |

The new tests check: palette equals `CLAUDE.md`; config matches the palette; text contrast is at least 4.5:1 on all
three surfaces; chip and class outlines at least 3:1 on cards; grade fill styles kept; report CSS contains no dark
palette colour; focus, reduced-motion and small-screen rules exist.

Browser check (real): the dashboard was launched and inspected in headless Chromium.
- 1440 x 900, salt-marsh worked example, top and scrolled through the answer card, metrics, interval chart and
  option cards: palette applied (computed page `#080D17`, sidebar `#111A29`, expanders and metrics `#182438`), no
  Streamlit exception, chips and class labels readable, captions at full-opacity secondary text.
- Mangrove tab and the legacy scenario view (before pressing Run): opened, no exception, theme applied; the primary
  Run button computes to teal with dark text.
- 390 x 844: no horizontal page scroll; hero, chips and controls wrap.

**Not checked in a browser:** beach tabs, legacy scenario results after Run, the map section, the downloaded HTML
report, keyboard-only navigation, a screen reader, real phones, light-mode operating systems beyond the config.

Issues seen and left for later stages (outside the theme):
- The interval chart's two y-axis option labels overlap at 1440 px ("Planting (after mechanical cleanup)" over
  "Manual removal"). Not investigated; whether it predates the theme is unknown. Fix with the option-card redesign.
- On a 390 px screen the sidebar opens expanded and covers the page until closed (`initial_sidebar_state` in
  `dashboard.py`). Address with the navigation work in step 3. (Now done in Session 2 Stage 3, section 2d: the sidebar
  starts collapsed on a phone.)
- `ui_components.ai_style_dataframe` uses `#8A7F99` text, about 4:1 on dark cards (below 4.5:1).
- Hard-coded hex values remain in matplotlib and Altair chart code (Okabe-Ito series, `NEUTRAL`); they read on dark
  but are not palette-driven.
- Streamlit's settings menu may still let a user choose its built-in Light theme; the custom CSS is dark only.

## 2b. Session 2, Stage 2: reusable components and hero (implemented, tested, seen running; committed `7894759`)

Starting commit `4e6a03d`, branch `claude/shoreline-v5-1-dashboard-design-ot1i5s`. The decision engine, the registry,
the models, the report and `PIPELINE_VERSION` are untouched. No new dependency, image or web font.

Components, all in `src/shoreline_remediation/ui_components.py`. Each has a pure `*_html` builder (tested without a
browser) and a thin Streamlit renderer.

| Function | Signature | Use |
|---|---|---|
| `section_header` | `(title, kicker=None, description=None, meta=None, anchor=None) -> None` (`section_header_html` returns the HTML) | Section introductions. `meta` is right-hand context such as a data source. Uses `.sr-section`, `.sr-kicker`. |
| `status_label` | `(category, label=None) -> str` (HTML) | Recommendation category chip. `category` is a key of `decision_pipeline.CATEGORY_ORDER`; the wording is `decision_pipeline.CATEGORY_LABELS`. Missing shows "Status not available"; an unknown key shows "Unrecognised status: ..." in a dotted neutral style. Never falls back to a real category. |
| `site_card` | `(card: SiteCard, on_select=None) -> None` (`site_card_html(card)`) | One card. `SiteCard(site_id, name, kicker, location, habitat, description, facts, evidence, action_label)`; `SiteFact(label, value, kind)` with `kind` in `ui_theme.VALUE_KINDS` (observed, derived, model, screening, record, unavailable). `value=None` prints "not available". The button calls `on_select(card.site_id)`; without `on_select` no button is drawn. |
| `card_row` | `(items, render, key, empty_text=...) -> int` | Calls `render(item)` for each item in one wrapping flex container; returns the count; empty input shows `empty_text`. |
| `hero_feature` | `(title, description, kicker=None, points=(), meta=(), primary=None, secondary=None, key="main") -> str or None` (`hero_feature_html`) | Featured banner for the platform, a site or a habitat. `HeroAction(label, key, on_click=None, args=())`. Returns the key of the button pressed in this run. |
| `hero` | `(subtitle=None, chips=None, primary=None, secondary=None) -> str or None` | The one platform hero, now a call to `hero_feature` with `HERO_TITLE` ("Shoreline Remediation Intelligence"), `HERO_DESCRIPTION` and the three `HERO_POINTS`. The old call `hero(subtitle, chips)` still works; chip colours are ignored so a scope tag cannot read as a validation status. |

Also added: `evidence_legend_body()` (shared by the sidebar legend and the new `evidence_dialog()`), `ui_theme.CATEGORY_STYLE`
(one symbol and colour per pipeline category), `CATEGORY_UNKNOWN`, `VALUE_KINDS`, and CSS for the above in the dashboard
layer only (`_APP`), so the printable report CSS is unchanged.

Design decisions:
- **Card row wraps, it does not scroll sideways.** Streamlit buttons cannot live inside a raw-HTML strip, so a card with
  a working button cannot use `.sr-row`. `card_row` uses `st.container(horizontal=True, wrap=True)` with a keyed CSS
  rule: three cards side by side at 1440 px, stacked at 390 px, no page overflow, no JavaScript. `.sr-row` stays in the
  theme for static HTML strips.
- **Keyed containers carry the styling.** The hero, each site card and each row are `st.container(key="sr_hero_*" /
  "sr_site_*" / "sr_row_*")`, styled through `[class*="st-key-sr_..."]`. Button keys use other prefixes
  (`sr_act_hero_*`, `sr_open_site_*`) on purpose: a shared prefix makes the button inherit the card look.
- **Categories are displayed, never computed.** `ui_components` imports only `CATEGORY_LABELS` from the pipeline (a test
  checks this). Site cards carry no category at all.

Integration (data sources):
- `site_view.featured_sites()` builds three cards. Bay Jimmy: row `8018_32612` of `data/demo/p5_sites.csv` through
  `load_sites()` (coordinates, SCAT oiling, observed 2010 to 2015 edge loss, mean fetch). Bahía Las Minas:
  `results/mangrove/effect_by_year.csv` (site counts, years covered); coordinates and cleanup outcome data are shown as
  not available because the repository has none. Fine-to-medium sand beach: a habitat entry from `HABITATS`, labelled
  "No site record", no numbers. Evidence chips take their grade from `registry.governance_table()` states, so a chip
  cannot say more than the registry does. No card shows a model estimate, a recommendation or a percentage.
- `site_view.select_site(site_id)` and `dashboard.open_site(site_id)` set the existing widget keys (`top_view`,
  `site_habitat`, `site_mode`). No second navigation system. Unknown ids are ignored.
- `dashboard.py`: hero (primary "Open the Bay Jimmy worked example", secondary "How evidence is graded" opening a
  dialog), "Featured locations" header and card row, "Assessment" header, then the unchanged view switch. The legacy
  view keeps its "(legacy)" label.
- `_option_card` now shows `status_label(o.category, o.category_label)` before the class letter and grade chip. This
  closes the option-card half of known issue 4; the answer card and the class E table are unchanged.

Files: modified `src/shoreline_remediation/ui_components.py`, `ui_theme.py`, `site_view.py`, `dashboard.py`,
`tests/test_dashboard_v5.py` and `tests/test_p5_demo.py` (one token each: the legacy tests clicked `at.button[0]`, which
is now a hero button, so they click `at.sidebar.button[0]`, the same "Run scenario analysis" button as before),
`CHANGELOG.md`, this file. Created `tests/test_ui_stage2.py` (44 tests).

Tests (Python 3.11, fresh virtual environment outside the repository, Streamlit 1.67.0, `pdftotext` present):

| Command | Result |
|---|---|
| `python -m pytest tests/test_ui_stage2.py -q` | 44 passed, 0 failed, 0 skipped |
| `python -m pytest tests/test_ui_stage2.py tests/test_ui_theme.py tests/test_dashboard_v5.py tests/test_v5_1_governance.py tests/test_p5_demo.py -q` | 132 passed, 0 failed, 0 skipped |
| `python -m pytest tests -q` | **423 passed, 0 failed, 0 skipped** (379 existing + 44 new), about 2 minutes |

A first full run, before the two legacy tests were pointed at the sidebar button, had 3 failures (those tests pressed
the new hero button instead of "Run scenario analysis"). They are software tests of the interface, not model validation.

Browser check (real): launched with `streamlit run`, driven in headless Chromium.
- 1440 x 900: hero (kicker, title, description, three points, four scope tags, two buttons), both section headers,
  three cards in one row with equal height, status labels on the option cards (Conditional, Recommended, Insufficient
  evidence, Allowed no demonstrated benefit, Natural recovery). Card background computes to `#182438`, label text to
  `#F4F7FA`. No Streamlit exception, no element past the right edge, page width equals the viewport.
- 390 x 844 (sidebar closed by hand, see below): hero wraps, cards stack at full width, the long "Allowed, no
  demonstrated benefit over natural recovery" label wraps onto two lines inside its card, page scroll width 390.
- Navigation, both sizes: the mangrove card opened the mangrove page; the hero primary button returned to the Bay Jimmy
  worked example; the secondary button opened the evidence dialog.
- A first capture showed the hero and card buttons drawn inside their own small card (the key-prefix clash above). Fixed
  and captured again.

**Not checked in a browser:** the beach card button (covered by `AppTest` only), keyboard-only navigation, the
downloaded HTML report, a real phone, a card row with more than three cards. One spacing change (a 0.35 rem margin under
the card's evidence chips) was made after the last capture and was not captured again.

Known limits of this stage:
- No rocky-shoreline card: the dashboard has no rocky entry yet (issue 1, step 4). A card is added only for an entry
  that can be opened.
- Card descriptions and the names "Bay Jimmy, Barataria Bay" and "Bahía Las Minas" are fixed text in `site_view.py`,
  consistent with the existing page text; the numbers are read from files.
- The cards sit above the assessment on every run, so the answer card starts lower on the page. Step 3 (landing page)
  should move them. (Now done in Session 2 Stage 3: the cards are on the landing page, section 2d.)
- Stage 1 backlog unchanged: interval-chart label overlap (seen again), expanded sidebar on phones, `ai_style_dataframe`
  contrast, report download and keyboard navigation unverified. None is caused or touched by these components.

### 2c. Continuation state at the end of the Stage 2 session (committed as `7894759`, pushed)

- Branch `claude/shoreline-v5-1-dashboard-design-ot1i5s`, HEAD `4e6a03d` at the start of Stage 2 (now `ccc0d35`, section 1).
  No stash. The session started on
  `claude/shoreline-dashboard-components-hcizxj` (same commit); the owner chose to switch to the design branch.
- `git status --short`: modified `CHANGELOG.md`, `docs/V5_1_HANDOFF.md`, `src/shoreline_remediation/dashboard.py`,
  `site_view.py`, `ui_components.py`, `ui_theme.py`, `tests/test_dashboard_v5.py`, `tests/test_p5_demo.py`; untracked
  `tests/test_ui_stage2.py`. Nothing deleted. 8 tracked files, 491 insertions, 29 deletions, plus the new test file.
- **Committed and pushed on the owner's authorisation** as `7894759` ("V5.1 Session 2 Stage 2: reusable dashboard
  components and hero redesign") to `origin/claude/shoreline-v5-1-dashboard-design-ot1i5s`. This file's hash was recorded
  in a follow-up commit. The status list above describes the tree before that commit.
- The test environment (a Python 3.11 virtual environment in a scratch directory) is not part of the repository;
  recreate it with `pip install -r requirements-analysis.txt`.
- Stage 2 acceptance criteria 1 to 10 are met as far as this session could check. Left to do in Stage 2: the owner's
  review; optionally one more browser capture of the card row (the last spacing change) and of the beach card button.
  (Now committed and pushed as `7894759`, which is recorded in `ccc0d35`; the owner's review is still open.)
- Open questions for the owner: (1) is a wrapping card row acceptable in place of a sideways-scrolling strip;
  (2) should the featured cards stay above the assessment until the landing page exists (step 3); (3) is the beach
  "habitat screening" card wanted, given it is not a surveyed site; (4) is showing the category on option cards now,
  ahead of Session 3, acceptable; (5) D41 is still Proposed, so the labels shown are proposed wording.

## 2d. Session 2, Stage 3: landing page, navigation and site discovery (implemented, tested, seen running; not committed)

Scope was navigation, presentation and the habitat coverage read model. The decision engine, the registry, the models,
the printable report and `PIPELINE_VERSION` are untouched. No new dependency or image.

- **Navigation.** New `src/shoreline_remediation/ui_nav.py`. `PAGES` maps the page ids to labels: `landing` "Home",
  `site` "Site assessment", `evidence` "Evidence explorer", `models` "Model validation", `legacy` "Legacy and research".
  `st.session_state["page"]` is the key of one `st.segmented_control` at the top of every page, so there is one source
  of truth. The old `top_view` control and `VIEW_SITE` / `VIEW_SCENARIO` are removed. `go(page)` ignores unknown ids;
  `current_page()` falls back to `landing`. The page is mirrored to the URL (`?page=`): a reload stays on the same page,
  and an invalid value falls back to `landing`. `keep_alive(("site_habitat", "site_mode"))` re-assigns those widget
  values on each run, so the site selection survives while another page is shown. `dashboard.open_site(site_id)` sets
  the page to `site` and calls the existing `site_view.select_site`; unknown ids change nothing. Every non-landing page
  has a "Back to home" button (key `sr_nav_home`). `initial_sidebar_state` is now `"auto"`, so the sidebar starts
  collapsed on a phone. This closes the Stage 1 sidebar backlog item.
- **Pages.**
  - Landing: `ui_landing.render_landing(on_open_site, on_navigate)`.
  - Site assessment: the unchanged `render_site_evidence()`. The production pathway is still `dashboard.py` →
    `site_view.py` → `ui_pipeline.py` → `decision_pipeline.run_decision`, and it is not duplicated.
  - Legacy and research: the existing `render_scenario_view()` under a warning that it is kept for comparison and
    research and does not drive production recommendations.
  - Evidence explorer and Model validation: `ui_landing.render_placeholder`. It says the page is not yet available, what
    it will hold (Session 3) and where related information is today. It contains no data, tables or numbers.
- **Landing components.** All reuse Stage 2 components; no new card or hero code.
  - Hero (`C.hero`, title "Shoreline Remediation Intelligence"). The primary button "Explore shoreline sites" opens the
    site page and keeps the current selection. The secondary button "How evidence is graded" opens the evidence dialog.
  - "Featured locations": `featured_sites()`, `site_card` and `card_row`. The same three entries, unchanged data.
  - "Explore habitats": the tier legend and `habitat_cards()`.
  - "How the platform works": three static steps, no figures.
- **Coverage tiers and data sources.** `site_view.habitat_coverage()` returns `HabitatCoverage` entries. The tier of each
  habitat is derived from the `registry.governance_table()` states of the models linked to it in
  `site_view.HABITAT_MODELS`: any validated model gives "Numerical validation available"; otherwise any experimental model
  gives "Experimental evidence"; otherwise "Screening and literature only". The labels are `ui_theme.COVERAGE_TIERS`. The
  tier is never hard-coded, so a registry demotion changes the card. Result today:
  - Salt marsh: numerical. `edge_loss_v1` and `pah_decline_v1` are validated. The card states the limits: three Louisiana
    basins, Deepwater Horizon soil PAH, one spill. The treatment comparison is experimental.
  - Mangrove: experimental.
  - Fine-to-medium sand beach: experimental. The only model is the persistence reference.
  - Coarse sand, mixed sand and gravel, and gravel beaches: screening and literature only.
  - ESI 1A and 8A are read from `habitat.table()` (`data/knowledge/tables/habitat.csv`). They are shown as screening
    entries labelled "Not yet available in the dashboard", with no button.
  - A last "Other shoreline types" card states the unsupported-habitat abstention, using
    `decision_pipeline.OUTCOME_LABELS["unsupported_habitat"]`.
  - Habitat cards carry no facts, numbers, recommendations or percentages.
- **Component change.** `ui_components.site_card(card, on_select=None, key=None, button_key=None)`; the defaults are
  unchanged. Habitat cards use container keys `sr_site_hab_<tier>_<id>` and button keys `sr_open_site_hab_<id>`, so an
  entry can appear in both rows. The tier colours are CSS in the dashboard layer only; the printable report CSS is
  unchanged.
- **Files.** Created: `src/shoreline_remediation/ui_nav.py`, `src/shoreline_remediation/ui_landing.py`,
  `tests/test_ui_stage3.py`. Modified: `src/shoreline_remediation/dashboard.py`, `site_view.py` (additions only),
  `ui_components.py`, `ui_theme.py`, `tests/test_dashboard_v5.py`, `tests/test_p5_demo.py`, `tests/test_ui_stage2.py`,
  `tests/test_v5_1_governance.py`, `CHANGELOG.md`, this file. Untouched: `decision_pipeline.py`, `registry.py`, `models/`,
  `ui_report.py`, `PIPELINE_VERSION`.
- **Existing tests changed (navigation only).** No scientific assertion was weakened and no test was deleted.
  - The helpers navigate to the site page, because the default page is now the landing page. `top_view` becomes `page`.
  - The Stage 2 hero test now checks that "Explore shoreline sites" opens the site page.
  - `test_legacy_view_is_reached_only_from_the_labelled_legacy_entry` in `tests/test_v5_1_governance.py` now checks the
    "Legacy and research" page label and the warning text. The importer-isolation check is unchanged.

Tests (Python 3.11, fresh virtual environment outside the repository, Streamlit 1.67.0):

| Command | Result |
|---|---|
| `python -m pytest tests/test_ui_stage3.py -q` | 65 passed, 0 failed, 0 skipped (35 test functions) |
| `python -m pytest tests -q` | **488 passed, 0 failed, 0 skipped** (423 existing + 65 new), about 2.5 minutes |

A first run of the new file had 3 failures. They were caused by the test helper reading the injected stylesheet rather
than the info boxes. This was a test fault, fixed in the helper; there was no application change. These are software
tests of the interface, not model validation. The new tests cover: landing render, navigation to each page, featured and
habitat card navigation, return to home, site-selection preservation, missing site data, coverage tiers following the
registry (including demotion), unsupported-habitat abstention, legacy navigation, no fabricated numbers, and `ui_nav`
fallbacks.

Browser check (real: headless Chromium, `streamlit run`, at 1440 x 900 and 390 x 844):
- Landing page: four headings in order; featured cards; 12 habitat cards with no overlapping card boxes.
- Bay Jimmy card opened the site page with the worked example; "Back to home" returned to the landing page.
- Mangrove card opened the mangrove assessment. The hero primary button opened the site page with mangrove still selected.
- Legacy and research showed the warning. Reloading on legacy stayed on legacy (`?page=legacy`). `?page=evidence`
  opened the placeholder. `?page=nonsense` fell back to the landing page. The Model validation placeholder opened, and
  "Back to home" returned to the landing page.
- No Streamlit exception on any page. Page scroll width equals the viewport at both sizes, and no checked element is past
  the right edge. Evidence chips compute to 12.5 px in `#F4F7FA`. At 390 px the navigation wraps onto two rows and the
  sidebar starts collapsed.

**Not checked:** the browser Back button (one attempt after a reload stayed on the same page; whether Streamlit adds a
history entry per page change was not established); keyboard-only navigation; a real phone; the beach and remaining
habitat card buttons in a browser (AppTest only); legacy results after pressing Run; the HTML report download.

Known limitations of this stage:
- Streamlit logs an existing warning that `site_habitat` has both a default and a session-state value (it comes from
  `select_site`; a log line only).
- The landing page finds a card's tier by its kicker label (`ui_landing.render_habitat`). A `tier` field on the card would
  be cleaner.
- The fine-sand-beach tier is "Experimental evidence" because of the persistence reference, although its cleanup options
  are rules only (both chips are shown).
- The Evidence explorer and Model validation pages are placeholders.
- The Stage 1 backlog items other than the sidebar are unchanged (interval-chart label overlap, `ai_style_dataframe`
  contrast, unverified report download and keyboard navigation, Streamlit's settings menu offering a Light theme).

Rocky shoreline (next dedicated task, not started): the integration point is ready. To finish:
- In `site_view.py`, add `HabitatView` entries for ESI 1A and 8A (`shoreline_type="rocky_shore"`) through a
  `_screening_renderer` generalised from `_beach_renderer`.
- `habitat_coverage()` should then give those entries `opens=<key>` instead of the "Not yet available" label.
- Confirm the page shows the `no_site_forecast` abstention and no numerical forecast.
- Add AppTest and browser checks.
- No rocky demonstration site or forecast exists, and none should be invented.

Multi-agent record: orchestration, architecture, interface contract, review, the test-helper fix, the full-suite run and
the browser verification were done by the lead session. Implementation was done by a Sonnet subagent. Data-structure
inspection, the Stage 3 test file and this documentation were done by Haiku subagents. No agent committed or pushed.

Continuation state:
- Branch `claude/shoreline-v5-1-dashboard-design-ot1i5s`, HEAD `ccc0d35`, equal to origin.
- `git status --short`: the eight tracked files listed above plus `CHANGELOG.md` and this file are modified; the untracked
  files are `src/shoreline_remediation/ui_landing.py`, `src/shoreline_remediation/ui_nav.py` and `tests/test_ui_stage3.py`.
- Commit and push need the owner's explicit authorisation.
- Open questions for the owner: (1) is the placeholder approach acceptable for the two unbuilt pages; (2) should rocky
  shoreline be the next stage before the Session 3 pages; (3) D41 is still Proposed.

### 2e. Stage 3 checkpoint location and how to integrate it

- The owner authorised preserving Stage 3 as a commit on the local design branch, pushed to
  `origin/ccr-ed209fd7-hn5mdk` only. That is the one push target this cloud session is configured to use; it was not
  pushed to `origin/claude/shoreline-v5-1-dashboard-design-ot1i5s`, `model_v4` or anywhere else. The checkpoint commit
  is `2008c19` ("V5.1 Session 2 Stage 3: landing page, navigation and site discovery"), parent `ccc0d35`. The branch
  `ccr-ed209fd7-hn5mdk` did not exist on the remote before this push (git reported a new branch), so it now holds the
  Stage 2 history plus this commit. A follow-up commit on top records this hash.
- `origin/claude/shoreline-v5-1-dashboard-design-ot1i5s` still ends at `ccc0d35` (Stage 2). Stage 3 is therefore not yet
  on the design branch on the remote.
- Next session, integrate without rewriting history: `git fetch origin`, check out
  `claude/shoreline-v5-1-dashboard-design-ot1i5s`, confirm it equals `ccc0d35`, then
  `git merge --ff-only origin/ccr-ed209fd7-hn5mdk` (it is a fast-forward because the checkpoint descends from
  `ccc0d35`). Run `python -m pytest tests -q` (488 expected) and push the design branch only when the owner authorises
  it. If the design branch has moved, stop and ask; do not rebase or force-push.

## 2f. Session 2, Stage 4: rocky-shoreline screening and UI corrections (implemented, tested, seen running; committed as `710aefe`)

Integration: on `claude/shoreline-v5-1-dashboard-design-ot1i5s` (local), `git merge --ff-only origin/ccr-ed209fd7-hn5mdk`; before
that the local branch and origin were both `ccc0d35`, the tree was clean and the checkpoint descended from it. HEAD is now
`cf659e9`. The design branch was not pushed. Baseline after integration: 488 passed (after installing `requirements.txt`,
`statsmodels`, `seaborn`, `pyproj`, `geopandas`, `shapely`, `rasterio`, `pytest` in this container).

Stage 4 (files: `site_view.py`, `ui_components.py`, `ui_landing.py`, `ui_theme.py`, `tests/test_ui_stage3.py`,
`tests/test_ui_stage4.py`; `decision_pipeline.py`, `registry.py`, `model_v4` untouched):
- ESI 1A and 8A open from the landing cards (`esi_1A`, `esi_8A`; button keys are lower-cased by `_slug`: `sr_open_site_hab_esi_1a`).
  Labels come from `habitat.table()`; if it cannot be read the entries are omitted. No site record, model or forecast.
- Screening and abstention: the pipeline returns `no_site_forecast`, `no_model`, `insufficient_evidence`, `no_recommendation`;
  natural recovery with monitoring stays the reference. The coverage chip is rules and literature only.
- Phase 3: interval-chart rows no longer collide; AI-proposed table text contrast fixed; `SiteCard.tier` replaces the label
  lookup; fine-sand-beach chips and caption separate persistence reference from cleanup options. Mobile sidebar (already
  closed in Stage 3) re-confirmed.

Tests: `python -m pytest tests/test_ui_stage4.py -q` 20 passed; `python -m pytest tests -q` **510 passed, 0 failed, 0 skipped**
(488 + 20 + 2 parametrised Stage 3 cases), about 2.5 minutes. Software tests only, not scientific validation.

Browser (Playwright Chromium against `streamlit run`, 1440 x 900 and 390 x 844): landing; cards open at ESI 1A, 8A, marsh,
mangrove and fine-sand beach; no document-level horizontal overflow on landing, 8A or legacy; reload on `?page=site` stays on the
site page; "Back to home" returns to the landing page; beach report downloads (`shoreline_report_beach_fine.html`); legacy page
shows its warning; mobile sidebar starts collapsed; interval chart checked at 1440 after the fix (marsh worked example).
**Not checked in a browser**: coarse, mixed and gravel beach pages, the mangrove page beyond its text, the Evidence explorer and
Model validation placeholders, keyboard navigation, downloads for marsh, mangrove and rocky pages, the mobile interval chart.

Remaining limitations:
- The 1A/8A headline contradiction is resolved in Session 3 Stage 5 (section 2g).
- NOAA ESI ratings and the AI-extracted literature table remain unverified by a person; no expert review exists.
- Streamlit's `site_habitat` default/session-state warning (log only) is unchanged.
- Fine-sand-beach tier stays "Experimental evidence" because of the persistence reference alone.

Next recommended stage: Session 3 pages (Evidence explorer, Model validation from `registry.governance_table()`), then the
answer-card category display (known issue 4). Committed as `710aefe` and pushed to `origin/claude/shoreline-v5-1-dashboard-design-ot1i5s` (fast-forward from `ccc0d35`, carrying Stage 3 `2008c19`, `cf659e9`). Full suite re-run on the committed tree: 510 passed, 0 failed, 0 skipped. The harness branch `ccr-a0d4b16d-zf5kkb` was not pushed.

## 2g. Session 3, Stage 5: headline wording, five-part answer card, option-card wording (implemented, tested, seen running; not committed)

**Investigation (Phase 1, read-only).** ESI 1A/8A: class B means "allowed by screening" (hard rule `hard_elig` plus the NOAA habitat-impact rating). Every
class B option on 1A and 8A has `evidence_state = insufficient_evidence`. The only rocky/hard evidence row with content is `high_pressure_heated_washing`,
biological recovery, "no clear difference" (Houghton 1993; Coats 1999); it does not establish effectiveness. There was no classification or
aggregation defect; the old headline sentence "Best allowed options (class B)" was misleading wording. Manual removal depends on the oil setting through
the NOAA oil category: at the default oil setting 1A is excluded (rating "-") and 8A is conditional (rating C); at medium oil both are class B with
insufficient evidence (this reproduces the original report of manual removal listed among "best allowed options"). Pinned in the tests.

**Changed (authoritative file touched, wording only).** `decision_pipeline._headline`: insufficient-evidence state lists all class B options with
"Eligible under screening rules, but effectiveness relative to natural recovery has not been established: ... Eligibility reflects habitat-impact
screening, not demonstrated remediation effectiveness. The order shown is not a performance ranking."; no-clear-difference state appends only the
caveat (no second option list); the class A branch and the natural-recovery wording are unchanged.

**Answer card** (`ui_components.answer_card`, content from `ui_evidence.answer_sections`, which only reads pipeline fields): 1 decision outcome, 2 screening
eligibility, 3 demonstrated benefit vs natural recovery (grouped by each option's own `evidence_state`), 4 conditions and restrictions (the pipeline's own
reason per conditional option, the excluded list, the scope message), 5 confidence and uncertainty (no calibrated probability; heuristic evidence grade;
no site forecast; NOAA 1A/8A ratings AI-transcribed, Proposed, not human-verified; effectiveness not numerically validated). The pipeline headline sits in the
expander "Pipeline's full text statement (technical wording)". **Option cards** (`_verdict_text`, class B) separate "no eligible evidence" from "evidence exists,
no clear difference"; the class B group heading in `ui_theme.CLASS_STYLE` was reworded ("Allowed by screening, benefit not established"). `decision_pipeline.CLASS_LABELS["B"]` ("allowed, no clear evidence either
way") is authoritative and was not changed; reword it only with owner approval.

**Rendered-QA corrections.** (1) ESI 1A at medium oil: the card said "No clear difference (evidence exists)" and then "Not established" for every option because the
single option with evidence is conditional; fixed by grouping per option. (2) "nOAA" (lower-casing "NOAA") in the card and in the existing option-card text. (3) "(see harm_flags)"
leaked an internal field name. (4) the marsh planting condition showed the code 'mechanical_removal'; condition text now passes through `humanise`. A Haiku review of the card wording found no eligibility/effectiveness conflation and no verification claims; its suggestion to pin the wording
literally in tests was adopted.

**Verification.** `/tmp/claude-0/venv/bin/python -m pytest -q`: 537 passed, 0 failed, 0 skipped (about 2.5 minutes). New file `tests/test_session3_answer_card.py` (27 tests); one label changed in
`tests/test_dashboard_v5.py`. 37-case comparison against HEAD `29aba8d` (1A, 8A, 3A, 5 x 3 oiling levels x 3 oil settings, plus the marsh worked cell): classes, categories, evidence
states, order and rank, abstentions, summary, outcome, natural-recovery block, plots and numbers identical; only the appended headline sentence differs (36 of 37; marsh class A
unchanged). Browser (Playwright Chromium, `streamlit run`, 1440 and 390 px wide, tall viewport): marsh, 1A, 8A, four beach types and mangrove, no horizontal overflow; screenshots of the whole card were read for the marsh and ESI 1A pages (before the last headline edit, which only changes the
expander text), and the rendered text of all 16 captures was scanned for the old phrases (none found) and for the renamed expander. **Not checked in a browser:** report downloads, keyboard navigation, the legacy page, the Evidence explorer and Model validation placeholders.

**Haiku review findings carried forward (not changed).** (a) Latent: the no-difference sentence in `_headline` groups every class B/D option with any evidence under "no clear difference"; a class D option with harm or
mixed evidence would be mislabelled in that sentence (the card handles those states correctly). A scan of all habitat codes at 3 oiling levels and 5 oil settings found no such option today, so it cannot occur with current data. Fix it
in `_headline` (split `with_evidence` by `evidence_state`) when the evidence tables change. (b) `CLASS_STYLE["A"]` and the class A headline say "Field evidence of benefit"; the evidence is composer output the pipeline marks experimental with a failed
bias gate. The UI already shows the Experimental chip beside it; consider rewording with the owner. (c) The NOAA "Proposed, not human-verified" caveat fires when the rating source string contains "proposed" or "transcribed by AI"; a rating with a different
source label would be shown without the caveat.

**Environment.** Virtual environment outside the repository (`/tmp/claude-0/venv`, Python 3.13): `pip install -r requirements.txt pytest seaborn statsmodels pyproj`. The last three are analysis-only imports
needed to collect some test files (`requirements-analysis.txt` lists them with others); without `pyproj`, `tests/test_p3_treatment_erosion.py` fails at collection. No dependency file changed.

**Limitations.** The 1A/8A NOAA ratings are still not verified by a person; no expert review exists; no rocky-shore effectiveness is numerically validated; the mobile card is long
(about three screens on the marsh page); a caption on the marsh interval chart ("All of these come from one site's field plots") is hard-coded and unchanged; the headline still says "continue
with natural recovery and monitoring" in the no-difference state (existing wording, consistent with natural recovery being the reference).

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

Session 3 Stage 5 (uncommitted): modified `src/shoreline_remediation/decision_pipeline.py` (`_headline` wording only), `ui_evidence.py` (`answer_sections`,
`_lower_first`, class B `_verdict_text`), `ui_components.py` (five-section `answer_card`), `ui_theme.py` (class B heading), `tests/test_dashboard_v5.py` (one label),
`CHANGELOG.md`, `docs/V5_1_HANDOFF.md`; created `tests/test_session3_answer_card.py`.

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

## 6a. Tests (current, Session 3 Stage 5)

| Command | Result |
|---|---|
| `python -m pytest tests/test_session3_answer_card.py -q` | 27 passed |
| `python -m pytest -q` (whole suite, uncommitted tree) | **537 passed, 0 failed, 0 skipped**, 347 warnings, about 2.5 minutes |

The earlier baselines (371 after Session 1; 510 at the Stage 4 commit) are historical. 537 = 510 + 27 new tests.

## 7. Known bugs and open issues

1. ~~No rocky-shoreline entry in the dashboard.~~ Done in Session 2 Stage 4 (section 2f). Original text: `site_view.HABITATS` has marsh, mangrove and four beach types. The
   pipeline supports `rocky_shore` (ESI 1A, 8A) and is tested, but the required rocky demonstration case cannot be
   reached from the UI. (Now, Session 2 Stage 3: the landing page lists ESI 1A and 8A as screening entries labelled "Not
   yet available in the dashboard", with no button. The rocky case still cannot be opened.)
2. ~~The dashboard is still the V5 light theme.~~ Palette and dark theme applied in Session 2 Stage 1 (section 2a).
   ~~Layout, navigation and components are still the V5 ones.~~ Components (Stage 2, section 2b), the landing page and
   navigation (Stage 3, section 2d) are done. The two unbuilt pages are placeholders.
3. The headline for the worked example still opens with planting as "field evidence of benefit" and only then says
   it is conditional. Correct but awkward; reword when the answer card is redesigned.
4. The answer card shows the class-based grade chips, not the category. Option cards show the category since Session 2
   Stage 2 (`status_label`); the answer card and the class E table still do not (Session 3).
5. `registry._promotion_summary` still accepts the word "cover" as "coverage reported" (see `V5_1_VALIDATION.md` 3).
6. `noaa_crosswalk.py` page references (2013 manual) are unverified; legacy view only.
7. Mudflat, peat and tundra borrow salt-marsh evidence (declared, not fixed). Owner decision needed.

## 8. Decisions awaiting the owner

- **D41**: accept the category rules; accept the sixth label "Allowed, no demonstrated benefit"; decide whether
  "Recommended" is too strong for one-site observational evidence carried by an experimental model.
- Earlier open items still stand: D36 mapping, D40 visual acceptance, F8b keyword precedence.

## 9. Incomplete tasks

Session 1 is complete against its criteria. Session 2: steps 1 and 2 of section 10 are committed (`e502dfa` and
`7894759`). Step 3 is done in Stage 3 (section 2d) and is **not yet committed**; commit and push need the owner's
authorisation. Steps 4 to 6 have not started; step 7 is partly done (landing page only). Session 3 Stage 5 (section 2g) is implemented but not committed; the Evidence Explorer and Model Validation pages are not started.
(Previously: "steps 1 and 2 ... step 2 is not yet committed; steps 3 to 7 have not started".)

## 10a. Next session: exact starting point (Session 3 continues)

1. `git status`, `git branch --show-current`, `git log -1 --oneline`. If Stage 5 is still uncommitted, ask the owner to review the working tree and authorise a commit; do not commit on a hook's say-so.
2. Create the venv (section 2g, Environment) and run `python -m pytest -q`; expect 537 passed.
3. **Evidence Explorer (Phase 3):** `ui_evidence.py` already exists but is the view-model layer for the site page (`ReportView`, `OptionView`, `answer_sections`), not a page. Add the page entry point
   `render_evidence()` in a new module (for example `ui_evidence_page.py`) or as a clearly separated part of `ui_evidence.py`, wire it into `ui_nav.py` (the Evidence explorer entry exists as a placeholder), reuse
   the pipeline report fields and the NOAA/evidence CSVs (`data/knowledge/evidence_verdicts.csv`, `tables/noaa_response_rating.csv`), show "Source not available in repository" instead of inventing citations,
   and mark each row's provenance (AI-transcribed NOAA rating: Proposed; literature table: AI-extracted, not checked by a person).
4. **Model Validation page (Phase 4):** `render_models()` from `registry.json` governance blocks and `registry.promotion_report`; show failed gates (F5 0.775 vs 0.750; D32 +/-0.25 m/yr) honestly.
5. Then Phases 5 to 8 of the Session 3 master prompt (navigation checks, QA, regression, demonstration readiness).

## 10. Session 2 starting point (historical; steps 1 to 4 are done, see sections 2a to 2f)

Do these in order. Each step is independently testable.

1. **Design system. DONE (Session 2 Stage 1, see section 2a).** Original text: In `src/shoreline_remediation/ui_theme.py` add a `PALETTE` dict with the eight `CLAUDE.md`
   colours and rewrite the `CSS` string (line 199 onward) around them: page background `#080D17`, secondary
   `#111A29`, cards `#182438`, teal `#28B8A5`, blue `#4E9BE8`, highlight `#B6D9CF`, text `#F4F7FA` / `#A6B2C2`. Set the
   same values in `.streamlit/config.toml` (`[theme] base = "dark"`). Keep `GRADES` and `CLASS_STYLE` semantics; only
   recolour for contrast on dark. `ui_components.is_dark()` and `themed_fig()` must keep working for matplotlib and
   Altair charts.
2. **Reusable components. DONE (Session 2 Stage 2, see section 2b). Start at step 3 once authorised.** Reuse
   `section_header`, `site_card`, `card_row`, `hero_feature`, `featured_sites` and `open_site` for the landing page;
   do not write new card or hero code. Original text: Use the existing CSS classes `.sr-kicker`, `.sr-section`, `.sr-card`,
   `.sr-row` and the `--sr-*` variables; add new colours only through `ui_theme`. In `ui_components.py` add `section_header(title, kicker)`, `status_label(category)`
   (one colour per `decision_pipeline.CATEGORY_ORDER` entry), `site_card(...)`, `card_row(cards)` (horizontal scroll
   via CSS), and `hero_feature(...)`. Replace the body of `hero()` rather than adding a second hero.
   (As built, `card_row` wraps rather than scrolls; see section 2b. Stage 3 started step 3, see section 2d.)
3. **Navigation and landing page. DONE (Session 2 Stage 3, see section 2d; not committed).** As built, the title is
   "Shoreline Remediation Intelligence", the featured cards are Bay Jimmy, Bahía Las Minas and a fine-to-medium sand beach
   entry, and rocky shoreline appears only as a habitat entry that cannot be opened. Original text: In `dashboard.py` replace the two-item `st.segmented_control` with a page state
   in `st.session_state["page"]`: `landing`, `site`, `evidence`, `models`, `legacy`. Create
   `src/shoreline_remediation/ui_landing.py` with `render_landing()`: platform name "Shoreline Intelligence", a
   featured Bay Jimmy section (cell `8018_32612`), habitat cards, and three case-study cards (Bay Jimmy salt marsh,
   rocky shoreline, mangrove). Each card button must set the page and `st.session_state["site_habitat"]`.
   Every figure on a card must come from `site_evidence.load_sites()` or the habitat table; no ratings, no invented
   numbers. The legacy scenario view moves under a clearly labelled "Legacy and research" entry.
4. **Rocky shoreline. NEXT TASK (not started).** Integration point and steps are in section 2d. In `site_view.py` add `HabitatView` entries for ESI 1A ("Exposed rocky shore",
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
7. **Tests. Landing-page part DONE (Session 2 Stage 3):** landing render, card navigation and return home are tested in
   `tests/test_ui_stage3.py` (AppTest), not `tests/test_dashboard_v5.py`; the browser check covered landing, Bay Jimmy and
   mangrove. **Rocky page still to do** (with step 4). Original text: Extend `tests/test_dashboard_v5.py` (Streamlit
   `AppTest`) for landing page render, each card button changing the page, and the rocky page. Then run the browser check
   for landing, Bay Jimmy, rocky and mangrove.

Session 3 then covers: option cards with categories and "why" explanations, scenario comparison, an evidence
explorer, the model-validation page built on `registry.governance_table()`, and the full report.
