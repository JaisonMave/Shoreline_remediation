# V5.2 handoff: Evidence explorer and Model validation

Updated 15 November 2026. Branch `model_v5_1` (canonical V5.1/V5.2 branch; starting point `0846919`). The V5.2 work is committed as one commit,
"Implement V5.2 evidence explorer and model validation" (a commit cannot record its own hash; use `git log -1`). **Not pushed.** Read this first, then
`docs/V5_1_HANDOFF.md` section 1a for the release and branch state. Do not redo V5.1 (Stages 1 to 5) or the V5.2 pages.

## 1. What exists now (implemented and tested; not scientifically validated by this work)

| Page | Entry point | Data layer |
|---|---|---|
| Evidence explorer (`?page=evidence`) | `ui_evidence_explorer.render_evidence()` | `evidence_catalog.py` |
| Model validation (`?page=models`) | `ui_models.render_models()` | `model_validation_data.py` |

`dashboard.py` routes the two pages (the Session 3 placeholders are gone; `ui_landing.render_placeholder` is kept but unused). Navigation is unchanged
(`ui_nav.PAGES`); widget keys of both pages are in `STATE_KEYS` and kept by `ui_nav.keep_alive`, so filters, the inspected record/model and the gap-class choice
survive a page change, and the site selection still persists. Invalid `?page=` values still fall back to Home.

### Evidence explorer
- **Catalogue** (389 rows, no row dropped or changed): 144 AI-extracted study records (`literature_effects.csv`, status Proposed or abstract_only), 54 literature summaries
  (`treatment_evidence_untested.csv`, not used in any number), 10 field-plot effects (`tables/evidence_effect.csv`, experimental composer input), 148 screening metadata rows
  (126 NOAA habitat-impact ratings, AI-transcribed and Proposed; 14 mangrove screening rows, AI-proposed; 8 beach literature notes), 33 evidence verdicts (`evidence_verdicts.csv`).
  Each row keeps `source_file`, `source_id`, citation, DOI/URL (else "Source not available in repository"), recorded grade and status, provenance text and a plain statement of how
  the platform uses it. Kinds are never merged; the chip reuses `ui_theme.GRADES`.
- **Tabs:** Evidence records (search, filters by kind, habitat class, ESI code, option, grade, status, location; table; record detail), Gaps and unsupported applications (per habitat class: number of study records per option and the
  verdict the pipeline reads, zero counts highlighted), Relation to pipeline decisions (a read-only call to `run_decision({}, habitat=ESI, oiling_class="moderate", oil="medium")`; categories, evidence states and NOAA ratings are copied from the report;
  the default ESI follows the habitat chosen on the Site assessment page).
- **Provenance statements that the page makes and the data support:** `checked_by` is one blanket owner attestation on every study row (not an independent expert review) and the 19 abstract-only rows are flagged because the attestation says
  "checked against the PDFs"; verdict rows come from one or two single studies or from no eligible rows (none is a meta-analytic pool), and "no clear difference" is the rule's label for that, not a measured null effect; counts of records do not measure strength of evidence.

### Model validation
- **Inventory** = `registry.governance_table()` unchanged: 2 validated (edge_loss_v1, pah_decline_v1) and 7 experimental. A validated model shows its failed gates (edge_loss_v1: V5-0.2, does not block promotion). Per-model detail shows intended use, habitat and
  geographic scope, training and validation data, hold-out design, baseline, uncertainty method, interval status, limitations, every gate with its result, blocking flag and source, and the reasons a model is not validated.
- **Held-out results**, each from a real file with an unavailable fallback: marsh-edge loss whole-basin hold-out (`results/p2_basin_holdout/per_basin.csv`, `pooled.csv`; M0, M1, M2 MAE; Terrebonne shown as not tested; recorded verdict "Partly transfers"), soil PAH-sum hold-out
  (`results/pah_decline/summary.csv`), F5 (`results/f5_process/summary.txt`: calibrated 0.775 vs empirical 0.750 vs prior 0.795; gate failed), heavy-cell bias gates (registry gate records: R3 +0.549, D32 +0.330 vs +/-0.25; D32 reduced the bias but the gate failed). Axes start at zero.
- **Uncertainty and use:** the scenario_runner confidence score is stated to be a heuristic, not a calibrated probability; each model's uncertainty method and interval status are listed as recorded.

## 2. Architecture and reuse
Data layers (`evidence_catalog.py`, `model_validation_data.py`) have no Streamlit import and no scientific calculation; the UI modules only present. Decision authority stays with `decision_pipeline.run_decision()`; `registry.governance_table()` is the only source of model state.
`evidence_catalog.habitat_class_of` reuses `decision_pipeline._literature_habitat` (a private function; promote it to a shared module if a third caller appears) and a test compares it with `validation.literature_pooling._habitat_class`.
Not changed: `decision_pipeline.py`, `registry.py`, `models/`, `data/`, `results/`. The 37-case pipeline comparison against `0846919` is byte-for-byte identical (headline included).

## 3. Tests and QA
- `/tmp/claude-0/venv/bin/python -m pytest -q` : **583 passed, 0 failed, 0 skipped** (537 before V5.2; 46 net new). New files: `tests/test_v52_evidence_catalog.py`, `tests/test_v52_model_validation.py`, `tests/test_v52_pages.py`. `tests/test_ui_stage3.py`: the placeholder test for evidence/models was replaced by a test that they are real pages (their premise, "placeholder", no longer holds; no assertion was weakened elsewhere).
- Browser (Playwright Chromium against `streamlit run`): both pages and all three tabs at 1440 and 390 px, tall viewports; no horizontal overflow; screenshots inspected for the evidence records/gaps/context tabs and the model inventory/results tabs (desktop) and the results and gaps tabs (mobile). Not checked in a browser: keyboard navigation, downloads, the uncertainty tab on mobile, the Home and Legacy pages after the change (AppTest loads them).
- Environment: external venv `/tmp/claude-0/venv` (`pip install -r requirements.txt pytest seaborn statsmodels pyproj`); no dependency file changed.

## 4. Haiku reviews and what was done
Plan review: blanket `checked_by`, "Proposed" status and abstract-only rows, BOMs, free-text habitats, validated-with-failed-gate display, P2 two-basin scope, reuse of `_literature_habitat` (all adopted). Implementation review: renamed the verdict kind (not "pooled"), added "counts do not measure strength" text,
derived the rocky-shore statement and bias-gate text from data instead of hard-coding, reconciled the habitat class 'other' (4 study records) and made multi-ESI beach notes deterministic, showed "n/a" instead of 0 when a habitat class is unknown, stronger and additional tests. Not adopted: moving `_literature_habitat` out of `decision_pipeline.py` (would touch the authoritative module).

## 5. Limitations and deferred work
- All study rows are AI-extracted and not verified by an independent expert; the NOAA 1A/8A ratings are not human-verified; no expert review exists. Rocky-shore effectiveness is not numerically validated; no technology has a positive evidence verdict in `evidence_verdicts.csv`.
- `literature_sources.csv` (90 sources with S-ids, access level, PDF availability) is not joined to study rows (only some citations match by prefix). Deferred: a reliable source key.
- Gap counts are row counts regardless of grade; a grade-aware view needs a protocol-level definition of grades A to E (the repository defines the criteria, not the letters).
- Model charts for P2 and PAH show the files' own MAE values; the registered `edge_loss_v1` baseline figures (1.296 vs 1.416 leave-one-basin-out) come from its card and are shown as text. A per-model chart for every experimental model would need result files that do not exist.
- Gate values for bias are read from registry gate descriptions (checked against `results/scenario_composer/summary_*.txt` by a test), not parsed from those files.
- The pipeline context uses default inputs and no site record; it is a screening view.
- Mobile tables scroll inside their frame; the first columns carry the key facts.

## 6. Next priorities
1. Review and, if approved, push `model_v5_1` (the V5.2 commit is local only).
2. Delete the three redundant remote branches (see `docs/V5_1_HANDOFF.md` section 1a) from a machine whose git can delete refs.
3. Human verification of the NOAA 1A/8A ratings and a sample of the AI-extracted study rows; record outcomes in the tables (status fields), then the explorer will show them.
4. Navigation and demonstration readiness (Phases 5 to 8 of the Session 3 plan): keyboard checks, report downloads, the three-site demonstration script.
5. Latent items from `docs/V5_1_HANDOFF.md` section 2g (headline `with_evidence` grouping; "Field evidence of benefit" wording for experimental composer output).

## 7. Continued in V5.3

The map-first decision dashboard work (map, decision board, deep links, provenance panel, scatter) is recorded in `docs/V5_3_HANDOFF.md`.
