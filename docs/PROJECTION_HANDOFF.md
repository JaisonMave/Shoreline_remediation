# Scenario projections: session handoff

Plan: `docs/CLAUDE_SCENARIO_PREDICTION_PLAN.md` (owner's file). Protocol: `docs/PROJECTION_RETREAT_PROTOCOL.md`.
Branch `codex/scenario-prediction-plan`, base `726d944`. Commit `d458d15` records the offline implementation.

### Assessment integration (21 November 2026)

Home → Use Bay Jimmy → Run assessment → Explore future scenarios opens an additional collapsed panel beneath the historical
trajectories. It applies the existing research engine to nine untreated field plots. The selected end date and one or two user
rates drive the chart, replayable JSON and CSV. Only the in-scope heavily oiled Bay Jimmy worked example gets the panel.
The earlier offline-only instructions below describe the original implementation. Screening and report generation retain
their existing inputs. The integration changes the Bay Jimmy controls intentionally; keep the Session 1 baseline as historical evidence.

Files: `src/shoreline_remediation/ui_future_scenarios.py`, `src/shoreline_remediation/ui_results.py`, `tests/test_projections.py`,
`tests/test_v54_results.py`, `README.md` and this handoff. The import guard permits the one presentation adapter.

Verification: `python -m pytest -q tests/test_v54_results.py tests/test_projections.py tests/test_projections_rate.py tests/test_recovery_trajectories.py`
gave 113 passed, 0 failed, 0 skipped. A local Streamlit session returned cumulative endpoints of 31.06 m (2030 fixed),
12.13 m (zero rate) and 74.86 m (2050 with a 2030 rate change). Full suite not rerun. Scientific status remains conditional.

**Integration review, 21 November:** See `docs/CLAUDE_ASSESSMENT_REVIEW.md`. The local review reproduced two failures before
the fixes. The caption now states the historical test coverage for any selected horizon, including dates within four years.
The shared `projections/projection.py` calculation rejects numeric overflow with a corrective message. Tests changed in
`tests/test_projections_rate.py` and `tests/test_v54_results.py`. The four-file pytest command above gave 114 passed, 0 failed,
0 skipped. The extended interaction check also passed individually with
`python -m pytest -q tests/test_v54_results.py::test_bay_jimmy_future_scenario_controls_use_the_observed_anchor`.
Chromium exercised both downloads; replaying the downloaded JSON through the CLI reproduced all 15 CSV dates, record types,
rates and retreat values within export precision. No horizontal page overflow at 390 px. The full suite was not rerun.
The external Claude Code invocation was blocked before execution; these are local review and verification results.

## Session 1 (20 Nov 2026): baseline and experiment specification. COMPLETE

### Starting state
- Branch `codex/scenario-prediction-plan`, HEAD `726d944` ("Show only continuous recovery trajectories in Assessment").
- Untracked before the session (owner's, untouched): `.vscode/`, `AGENTS.md`, `docs/CLAUDE_SCENARIO_PREDICTION_PLAN.md`.
- Interpreter: Python 3.11.9

### Regression baseline (run before any edit; no production source has been edited since)

| Command (repo root) | Result |
| --- | --- |
| `python -m pytest -q tests/test_recovery_trajectories.py tests/test_recovery_view.py tests/test_comparison.py tests/test_v5_1_governance.py` | 113 collected: **112 passed, 0 failed, 1 skipped** |
| `python -m pytest -q tests/test_v54_shell.py tests/test_v54_results.py tests/test_decision_board.py` | **57 passed, 0 failed, 0 skipped** |
| `python -m pytest -q tests` | 741 collected: **737 passed, 2 failed, 2 skipped** (212 s) |

Failures, cause verified: `test_data_catalogue::test_every_data_file_is_catalogued_and_unchanged` and
`test_p5_demo::test_model_card_has_provenance`. The system Git config (`C:/Program Files/Git/etc/gitconfig`, `core.autocrlf=true`)
checks LF blobs out as CRLF. For `data/demo/p5_sites.csv` the working file's SHA-256 equals the HEAD blob converted to CRLF, and
`git status` shows no data change. Same cause as the 4 failures recorded in `docs/V5_4_HANDOFF.md`.

Skips: `test_habitat::test_transcription_matches_the_pdf_text` and
`test_v5_1_governance::test_noaa_transcription_matches_the_source_pdf_text`: **"pdftotext not installed"**. Earlier handoffs list
these two as autocrlf failures; in this environment they are untested, not passing.

### Production reference cases

Command used: `python -W ignore scripts/capture_projection_baseline.py` (wrote `results/projection_baseline/`; since Session 2 the
script requires `--out` and refuses a non-empty directory). The script drives the real
dashboard with Streamlit AppTest, takes the exact run spec each case sends, replays it through `decision_pipeline.run_decision`
outside Streamlit (`UI_DRAWS` = 3000, pipeline default seed 20261112) and records visible controls. Normalization: only
`version.git_commit` (and any timestamp key, none present) is replaced. Two complete runs gave byte-identical files.

| Case | How driven | Scope tier | Outcome | Evidence state | Normalized report SHA-256 prefix |
| --- | --- | --- | --- | --- | --- |
| `bay_jimmy_mapped` | Home > Use Bay Jimmy > Run (cell 8018_32612) | validated | intervention_recommended | benefit | `4da6fa96b77d` |
| `typed_marsh` | Site > marsh > New site, default 29.40/-89.90, Heavy | experimental | conditional_only | benefit | `32926391d3c2` |
| `rocky_esi_1A` | Site > esi_1A > Run (defaults) | rules_and_literature | conditional_only | no_clear_difference | `d6d10541523e` |
| `mangrove` | Site > mangrove > Run (defaults) | experimental | insufficient_evidence | insufficient_evidence | `658ec33839a0` |

Classes, abstentions (1, 4, 6, 6 respectively), report fields and controls are in `results/projection_baseline/summary.json`.
Controls after the run: Bay Jimmy 6 charts, 1 map, the four trajectory tabs, 4 buttons, "Download report (HTML)"; typed marsh 2
charts, 1 map; mangrove 3 charts; rocky 0 charts (screening table only). Every case has the HTML report download.

Notes: the default Site-page marsh run uses the mapped worked-example cell, not a typed site, so the typed case explicitly selects
"New site (enter values)". Streamlit logs a non-fatal warning (with stack) that `site_habitat` has a default and a Session State
value; it is the same driving pattern as `tests/test_v54_results.py`, and no app exception occurred. The HTML download bytes are not
hashed (only the report JSON); Session 6 should compare the download through the existing report tests or the browser.

### Retreat protocol and data cutoffs
See `docs/PROJECTION_RETREAT_PROTOCOL.md`. Key facts: origin 4 Dec 2010; final survey **5 Oct 2016**; untreated n = 9 at all 7
dates, final mean 12.126 m; mechanical plots ineligible; no untouched data (all dates already used by the existing fits);
one eligible site, so cross-site skill is unevaluated. **Minimum useful gain 0.5 m is proposed and awaits owner confirmation;
promotion is pending.** No forecast evaluation has been run.

### Files changed in Session 1
- Created `scripts/capture_projection_baseline.py`
- Created `results/projection_baseline/` (`summary.json`, four `*.report.json`)
- Created `docs/PROJECTION_RETREAT_PROTOCOL.md`
- Created `docs/PROJECTION_HANDOFF.md` (this file)
- No production source, test, configuration, data, model or registry file was modified.

### Open items for the owner
1. Confirm or change Delta = 0.5 m (protocol section 7) before the section 5 evaluation is run.
2. Whether `results/projection_baseline/` should be committed (recommended: yes, so Session 6 can diff against it).

### Owner feedback after Session 1 (20 Nov 2026), applied at the start of Session 2
- Delta = 0.5 m is kept and worded as a **proposed research criterion**; owner confirmation remains pending. The 0.37 to 0.82 m
  standard errors are context for sampling noise, not evidence of a management threshold (protocol section 7).
- B1 "whole-record constant rate" means all surveys available at each simulated forecast date (protocol section 6); every rule is
  scored on the same pairs.
- The Session 1 baseline is preserved: `scripts/capture_projection_baseline.py` now requires `--out` and refuses a non-empty
  directory; `tests/test_projections.py` checks the five baseline files against line-ending-normalized SHA-256 values. Session 6
  writes to a fresh directory (for example `results/projection_baseline_session6`). Owner recommends including the original baseline
  in the first authorized commit.

## Session 2 (20 Nov 2026): scenario spec, offline runner, CLI, manifest, isolation. COMPLETE

### What exists
`src/shoreline_remediation/projections/`:
- `catalogue.py`: schema version `shoreline-projection-spec/1`; origins (observation, derived, literature, fitted_parameter,
  user_assumption, synthetic_fixture); site `bay_jimmy_zengel_plots` with groups `untreated_heavy`, `manual_removal_heavy`,
  `unoiled_reference` and the ineligible `mechanical_removal_heavy`; the mapped cell `bay_jimmy_cell_8018_32612` as a known
  non-projection site; unsupported habitats (rocky_shore, mangrove, sand_beach) with reasons; endpoint
  `cumulative_shoreline_retreat` (m) implemented, vegetation cover and soil tPAH defined but not implemented; assumption IDs
  `retreat_rate`, `rate_change_date`, `changed_retreat_rate`; model `observed_record/1` only.
- `spec.py`: `ScenarioSpec`, `from_dict`, `load`, `check_scope`. `SpecError` lists every problem with its field path (nothing
  runs). `Unsupported(code, reason, field)` for valid but unsupported requests. Null plus `missing_reason` is missing; 0 is zero.
  NaN/Infinity are rejected when reading files; booleans are not numbers. `synthetic_fixture` values require `demonstration: true`.
- `runner.py`: `run(spec | dict | path, output_dir)`. Refuses any existing output path (left untouched). Writes `input.json` (exact
  bytes), `manifest.json` (status `running` first, then `completed`, `unsupported` or `failed`; spec and its hash, input hash,
  code hash over this package plus the reused loaders, git commit and dirty flag, dependency versions, source file SHA-256, seed,
  outcome, outputs with hashes, limitations) and, when supported, `observed.csv`. `normalized()` drops only times, git commit
  and dirty flag. Hashes of text are line-ending normalized.
- `__main__.py`: `validate` and `run` subcommands. Exit codes 0 completed, 3 unsupported (record written), 2 invalid (nothing
  written), 4 output exists, 1 failed.

`observed.csv` columns: scenario_id, site_id, plot_group_id, endpoint, unit, date, decimal_year, elapsed_years, value,
interval_lo, interval_hi, interval_method, n_plots, record_type (`observed_group_mean`), origin (`derived`: a mean of plot
observations), derivation, evidence_id, available_at_as_of (observations after `as_of` are flagged, so a hindcast anchor cannot use
them). Values reproduce the protocol table (final 12.126 m, n = 9 at all 7 dates).

Examples: `examples/projections/bay_jimmy_observed.json` (supported), `examples/projections/rocky_retreat_unsupported.json`.

Replay commands (repo root):
```
python -m src.shoreline_remediation.projections validate --scenario examples/projections/bay_jimmy_observed.json
python -m src.shoreline_remediation.projections run --scenario examples/projections/bay_jimmy_observed.json --output runs/bay_jimmy_observed
python -m src.shoreline_remediation.projections run --scenario examples/projections/rocky_retreat_unsupported.json --output runs/rocky_unsupported
```
Smoke run results: exit 0 (run ID `a10afcdc134a1a08`), a second run into the same path exit 4, rocky exit 3 with
`habitat_unsupported`. `runs/` was not created in the repository (smoke runs went to the session scratchpad).

### Finding: the parent package loads the legacy model
`src/shoreline_remediation/__init__.py` imports `HybridDecisionModel` (and `fast_engine`, `ml_models`) eagerly, so any import
of any submodule, including the dashboard's and this package's, loads `decision_framework`. The projections package neither
imports nor calls it. The isolation test therefore checks what importing `projections` adds on top of the parent package (no
Streamlit, `ui_*`, dashboard, site_view, decision_pipeline, decision_framework or scenario_runner) plus an AST check of the
package's own imports. Making the parent `__init__` lazy is a production change and was not made; it would also cut about 2 s of
import time from the runner.

### Tests (Session 2)
| Command | Result |
| --- | --- |
| `python -m pytest -q tests/test_projections.py` | **51 passed**, 0 failed, 0 skipped (7 s) |
| `python -m pytest -q tests/test_recovery_trajectories.py tests/test_recovery_view.py tests/test_comparison.py tests/test_v5_1_governance.py` | **112 passed, 1 skipped** (identical to baseline) |
| `python -m pytest -q tests/test_v54_shell.py tests/test_v54_results.py tests/test_decision_board.py` | **57 passed** (identical to baseline) |
| `python -m pytest -q tests` | 792 collected: **788 passed, 2 failed, 2 skipped** (356 s). 788 = 737 baseline + 51 new. The 2 failures and 2 skips are the same as the Session 1 baseline (`core.autocrlf` hashes; `pdftotext` not installed) |

`tests/test_projections.py` covers: round trip; zero survives and differs from missing; 19 invalid-input cases with field and fix;
missing required fields; NaN in files; synthetic only in demonstrations (and none in `examples/`); 9 unsupported codes
including rocky, mangrove, unknown site, mapped cell, mechanical, vegetation; fixable unit/arm/citation errors; two reproducible
runs; observed series values; `as_of` withholding; existing directory preserved (API and CLI); invalid input writes nothing;
unsupported run writes a reason and no numbers; `running` written first and `failed` recorded; CLI exit codes; isolation both
ways; Session 1 baseline hashes; capture script refusal. These are software checks, not scientific validation.

### Files changed in Session 2
- Created `src/shoreline_remediation/projections/` (`__init__.py`, `__main__.py`, `catalogue.py`, `spec.py`, `runner.py`)
- Created `examples/projections/bay_jimmy_observed.json`, `examples/projections/rocky_retreat_unsupported.json`
- Created `tests/test_projections.py`
- Modified (Session 1 files, untracked): `scripts/capture_projection_baseline.py` (required `--out`, refuses non-empty
  directory), `docs/PROJECTION_RETREAT_PROTOCOL.md` (sections 6 and 7 wording), this file.
- No tracked file modified. No dashboard, decision pipeline, report, model, registry, data or configuration change.

### Limitations
- `observed_record/1` produces no value after `as_of`; projection models start in Session 3.
- Only the Bay Jimmy plot site is a projection site. Manual and reference groups run the observed record but are not
  promotion targets.
- The HTML report download is still compared only through existing tests; browser acceptance is for Session 6.

## Session 3 (20 Nov 2026): continuous Bay Jimmy retreat projection. COMPLETE

Owner direction at the start: leave the parent package's `HybridDecisionModel` import for a separate maintenance change; keep
Delta = 0.5 m pending until forecast scoring; verify the projection arithmetic directly.

### What exists
- `catalogue.py`: model `rate_continuation/1`; `MODEL_ASSUMPTIONS` (observed_record/1 takes none; rate_continuation/1 requires
  `retreat_rate`, optionally `rate_change_date` + `changed_retreat_rate` together); `CONDITIONAL_LABEL`; plot-group labels.
- `spec.py`: model-specific checks raise `SpecError` (unused or missing assumptions, half a rate change, change date not strictly
  between `as_of` and `end_date`). A `retreat_rate` of null with a reason returns `Unsupported("rate_not_available")`.
- `projection.py` (pure functions): anchor = last survey on or before `as_of`, with its **unrounded** group mean.
  additional(t) = r1 x (min(t, c) - a) + r2 x max(t - c, 0) in calendar decimal years (`recovery_trajectories.decimal_year`, the
  protocol convention); cumulative = anchor + additional. Sample dates: anchor, first-of-month/quarter/January dates, the change
  date and the exact end date, so annual dates are a subset of quarterly and monthly ones.
- `runner.py`: for rate_continuation/1 writes `observed.csv`, `projection.csv`, `projection.png`, `projection.svg`; manifest gains
  `projection` (anchor, each rate with unit, origin, source and dates applied, endpoint, a hand-checkable `arithmetic` string,
  time convention) and projection limitations. No survey on or before `as_of` returns `Unsupported("no_anchor_observation")`.
  `compare(run_dirs, stem)` overlays at most two completed runs with the same site, group and anchor.
- `figure.py`: matplotlib Agg, light surface, reference categorical slots 1-2 plus line style; observations in neutral ink
  with 90% t whiskers; shaded observed span; vertical line and label at 5 Oct 2016 "last survey; extrapolation starts"; dotted
  rate-change line; endpoint labels; title with site, place, spill, endpoint, unit, group and n; subtitle with the conditional
  status (and "not a probability band" on comparisons); footer with source, scenario, run ID, model and each rate's origin and
  source. SVG keeps text as text; PNG and SVG are byte-reproducible.
- `__main__.py`: new `compare --runs A B --output STEM` (existing files refused).
- Examples: `bay_jimmy_retreat_2030.json` (1.43 m/yr, fitted parameter: M1 long-run rate b = 1.4338 rounded) and
  `bay_jimmy_retreat_2050_changed_rate.json` (1.43 m/yr to 1 Jan 2030, then 2.19 m/yr, fitted parameter: the M0 **full-period
  fitted constant slope** across all 2010-2016 surveys, 2.1933 rounded; change date a user assumption). The fitted slope includes
  the early post-spill excess and is **not** the endpoint average (12.1256 m / 5.8363 yr = 2.08 m/yr). It is a sensitivity case,
  not a climate or storm scenario. (Label corrected in Session 4; the value and the 2050 endpoint are unchanged.)

### Demonstration runs (fresh directories in the session scratchpad, not in the repository)
Commands (repo root; use new output paths each time):
```
python -m src.shoreline_remediation.projections run --scenario examples/projections/bay_jimmy_retreat_2030.json --output runs/bj_2030
python -m src.shoreline_remediation.projections run --scenario examples/projections/bay_jimmy_retreat_2050_changed_rate.json --output runs/bj_2050
python -m src.shoreline_remediation.projections compare --runs runs/bj_2030 runs/bj_2050 --output runs/bj_sensitivity
```
| Run | Run ID | Endpoint | Arithmetic (decimal years; 5 Oct 2016 = 2016 + 278/366 = 2016.759563) |
| --- | --- | --- | --- |
| 2030 fixed | `8dd6de47e97a8527` | 1 Jan 2030: +18.933825 m after the last survey; 31.059470 m since 4 Dec 2010 | 1.43 x (2030 - 2016.759563) = 1.43 x 13.240437 = 18.933825; 12.125645 + 18.933825 = 31.059470 |
| 2050 changed | `98f26e707c233154` | 1 Jan 2050: +62.733825 m; 74.859470 m | 1.43 x 13.240437 = 18.933825 to 1 Jan 2030, + 2.19 x 20 = 43.800000; total 62.733825; 12.125645 + 62.733825 = 74.859470 |

Both runs pass through 31.059470 m at 1 Jan 2030 (continuous join). Figures inspected as PNG: the 2030 figure, the 2050 figure
with the slope change at 2030, and the two-run sensitivity figure. Earlier drafts clipped the endpoint label, title and footer
and used a rotated change label that crossed the curve; all were fixed before the final runs. Run IDs depend only on the spec, so
they are the same on every replay.

### Tests (Session 3)
| Command | Result |
| --- | --- |
| `python -m pytest -q tests/test_projections_rate.py tests/test_projections.py` | **76 passed** (25 new + 51 Session 2), 0 failed, 0 skipped (9 s) |
| `python -m pytest -q tests/test_recovery_trajectories.py tests/test_recovery_view.py tests/test_comparison.py tests/test_v5_1_governance.py` | **112 passed, 1 skipped** (identical to baseline) |
| `python -m pytest -q tests/test_v54_shell.py tests/test_v54_results.py tests/test_decision_board.py` | **57 passed** (identical to baseline) |

Full suite not rerun this session (Session 2: 788 passed, the 2 known autocrlf failures, 2 pdftotext skips).
`tests/test_projections_rate.py` hand checks: anchor exactly 0 / exactly the unrounded mean; zero rate flat; fixed rate at
1 Jan 2017 and 2030; two equal rates = one rate; change on 1 Jul 2025 (between annual samples) before, at and after the change
and at the end; end date 15 Jun 2030 between samples; annual/quarterly/monthly agreement at all shared dates for a fixed and a
changed-rate case; sample-date construction; five model input errors; null rate abstains; rocky and mangrove unsupported;
as_of before the first survey abstains; both example endpoints and arithmetic strings; earlier as_of anchors on 8 Sep 2013
(7.223314 m); byte-reproducible CSV/PNG/SVG; figure text (site, group, n, unit, conditional, extrapolation start, rates, change,
endpoint); no recommendation or rank field; compare overlay, overwrite refusal, mismatched anchors and non-projection runs.

### Files changed in Session 3
- Created `src/shoreline_remediation/projections/projection.py`, `figure.py`; `tests/test_projections_rate.py`;
  `examples/projections/bay_jimmy_retreat_2030.json`, `bay_jimmy_retreat_2050_changed_rate.json`.
- Modified (untracked, this programme): `projections/catalogue.py`, `spec.py`, `runner.py`, `__main__.py`, this file.
- The Session 2 observed-only command still writes exactly `input.json`, `manifest.json`, `observed.csv` (tested). The five
  Session 1 baseline files are unchanged (hash test). No tracked file modified; no dashboard, pipeline, report, registry, model,
  data or configuration change.

### Limitations (unchanged science)
- Every number after 5 Oct 2016 is arithmetic on a stated rate. No storm, sea-level, subsidence, geometry or management effect is
  represented, and no rate rule has been scored (protocol P-RET-1 is still unrun; Delta = 0.5 m pending).
- No interval after the anchor. Two runs drawn together are a sensitivity comparison, not a probability band.
- The example rates are rounded fitted parameters from fits to all seven surveys; they are illustrations of a historical rate,
  not tested forecasts. The 2.19 m/yr full-period fitted constant slope includes the early excess and is high relative to the fitted long-run
  rate.
- One site, one plot group per run; the manual and reference groups run but are not promotion targets.
- Linear extrapolation of cumulative retreat over 13 to 33 years ignores that the marsh edge, plots and stakes may not persist.

## Session 4 (20 Nov 2026): historical evidence exports. COMPLETE

### Label correction (value unchanged)
The 2050 example's second rate, 2.19 m/yr, is now labelled the **M0 full-period fitted constant slope** (least-squares slope
through the origin of plot increments at all 2010-2016 surveys, 2.1933). It is not the endpoint average, 12.1256 m / 5.8363 yr =
2.08 m/yr. Value, arithmetic and the 2050 endpoint (74.859470 m) are unchanged. Because the run ID hashes the spec, including
the source text, the 2050 example's run ID is now `c40c06ac3aec2bfe` (was `98f26e707c233154`). The 2030 example's ID
`8dd6de47e97a8527` is unchanged (tested).

### What exists
- `catalogue.py`: evidence `zengel2022_griidc_vegetation`, `zengel2015_s1_group_means`, `pah_decline_v1_heavy_class`; endpoints
  `total_vegetation_cover` (percent) and `soil_tpah` (mg/kg) implemented; models `field_contrast/1` and `recovery_fit/1`;
  `SUPPORTED` (model, endpoint) pairs with the evidence each must cite; `GAPS` with explicit reasons; `CONTRASTS` (vegetation:
  manual or mechanical vs untreated); `GROUP_MODEL_GAPS` (no recovery fit for reference plots); plot-group eligibility is now
  per endpoint (mechanical plots: ineligible for retreat only); one `RECORD_TYPES` vocabulary with reader-facing classes
  observation / derived_field_contrast / experimental_fit / conditional_projection / model_reference, and `SHARED_PLOTS_NOTE`.
- `spec.py`: optional `comparator_group_id` (field_contrast/1 only; omitted from the spec dict when empty, so earlier run IDs
  are unchanged). `check_scope` follows the support table; an `evidence_gap` needs the endpoint's observation evidence cited
  because it exports them.
- `evidence.py` (new): `vegetation_observed`, `vegetation_fit`, `vegetation_contrast`, `tpah_observed`, `diver_index`. Reuses
  `recovery_trajectories.vegetation_plots/_veg_fit/_logistic/_t90`, `comparison.vegetation_year2_estimates`, `treatment_effects.load`,
  `recovery_view.pah_decline_panel/_pah_support/_t90`. Survey dates are exported as month and period with a verified or assumed basis.
  An observation becomes available at `as_of` after the last day of its survey period, because the day is not recorded.
- `runner.py`: dispatch for the new endpoints. An `evidence_gap`, or a fit that cannot be made at `as_of`, still exports the
  observations and records `historical_records_exported`. Manifests gain `record_types`, `record_class_meaning`, and `contrast`,
  `fit` or `reference_index` blocks. Retreat `observed.csv` and `projection.csv` gain a `record_class` column; nothing else
  changes in retreat outputs.

### The four reader questions, per export
| Export | What was measured | Plots and dates | Compared with what | What depends on an assumption |
| --- | --- | --- | --- | --- |
| `contrast.csv` (field_contrast/1) | total cover group means (S1 Table) | plot IDs, n 5 and 9, September 2012 (verified) | comparator group, n, Welch 90% interval, observational design | nothing; `applies_to` restricts it to year 2 |
| vegetation `observed.csv` | total cover, plot visual estimates | plot IDs, n per survey, Sept 2011-2016 (2013-2016 month assumed) | n/a | nothing |
| `fit.csv` (recovery_fit/1) | logistic fit to surveys available at as_of | r, t50 and K with sources; data years in the manifest | n/a | manual rows after 2012-09 are `conditional_projection` (borrowed untreated r; `borrowing_begins`, manifest `borrowing`) |
| tPAH `observed.csv` | tPAH mg/kg, 0-10 cm cores, analyte definition | n, July-August 2011 and September 2012 | n/a | nothing |
| `reference_index.csv` | DIVER heavy-class relative index (100 = first campaign) | campaign support 2011.34 to 2013.78; 36 stations | not a plot measurement; not on the tPAH axis | it is a model reference within support; withheld if as_of precedes the support end |

### CLI replays (fresh directories in the session scratchpad, `...\scratchpad\s4\<name>`)
```
python -m src.shoreline_remediation.projections run --scenario examples/projections/bay_jimmy_veg_contrast_year2.json --output runs/veg_contrast
python -m src.shoreline_remediation.projections run --scenario examples/projections/bay_jimmy_veg_manual_fit.json --output runs/veg_manual_fit
python -m src.shoreline_remediation.projections run --scenario examples/projections/bay_jimmy_tpah_observed.json --output runs/tpah_observed
python -m src.shoreline_remediation.projections run --scenario examples/projections/bay_jimmy_tpah_manual_future_unsupported.json --output runs/tpah_future
```
| Example | Exit | Run ID | Files | Inspected content |
| --- | --- | --- | --- | --- |
| veg contrast | 0 | `1c3e23fab97e18f4` | contrast.csv | manual 52% (n 5), untreated 18% (n 9), +34 points, 90% Welch 18.96 to 49.04, September 2012, observational |
| manual fit | 0 | `78ec0ada1f2b30ae` | observed.csv, fit.csv | observed 21.8% / 51.8% (GRIIDC plot data; S1 22 / 52), r 1.197 borrowed, t50 2012.58, K 93.6; conditional from 2012.95 to 2016.70 |
| tPAH observed | 0 | `fde8109d673e2e41` | observed.csv, reference_index.csv | 260 and 112 mg/kg (n 9); index 100 at 2011.34 to 35.1 (25.9 to 49.2) at 2013.78 |
| tPAH future (manual) | 3 | `41de4fc939fa68fa` | observed.csv only | `evidence_gap`; 220 and 101 mg/kg exported; no projection |

### Tests (Session 4)
| Command | Result |
| --- | --- |
| `python -m pytest -q tests/test_projections_evidence.py tests/test_projections_rate.py tests/test_projections.py` | **93 passed** (17 new), 0 failed, 0 skipped (12 s) |
| `python -m pytest -q tests/test_recovery_trajectories.py tests/test_recovery_view.py tests/test_comparison.py tests/test_v5_1_governance.py` | **112 passed, 1 skipped** (identical to baseline) |
| `python -m pytest -q tests/test_v54_shell.py tests/test_v54_results.py tests/test_decision_board.py` | **57 passed** (identical to baseline) |
| `python -m pytest -q "tests/test_projections.py::test_session1_baseline_files_are_unchanged"` | **1 passed**: the five Session 1 baseline files are unchanged |

Full suite not rerun. `tests/test_projections_evidence.py`:
- **Contrast:**
  - the year-2 regression, checked against an independent hand Welch calculation;
  - the mechanical contrast equals the comparison layer's value;
  - `as_of` before the survey abstains;
  - comparator rules.
- **Vegetation:**
  - manual observations end in 2012; untreated 2011-2016 with verified and assumed months;
  - manual fit rows: experimental to 2012-09, conditional after, borrowed r equal to the untreated fit;
  - the documented full-record fit values are reproduced;
  - an `as_of` fit uses only earlier surveys; too few surveys abstains but keeps observations;
  - reference plots have no fit.
- **PAH:**
  - tPAH units, depth, analyte and dates; mechanical sampled 2012 only;
  - DIVER index reference, class, support and k;
  - the index is withheld before its support end and for unoiled plots;
  - the future treatment PAH evidence gap, through the CLI, keeps its measurements.
- **Other gaps:** the vegetation-rate and retreat-contrast evidence gaps still export observations.
- **Shared:**
  - one vocabulary across all six examples, all five classes seen;
  - retreat compatibility: observed-only files, 2030 run ID and endpoint;
  - the 2.19 label.

One Session 2 test case changed: vegetation is no longer "endpoint_not_implemented"; that case now checks a reference-plot
contrast returns `no_field_contrast`.

### Files changed in Session 4
- Created `src/shoreline_remediation/projections/evidence.py`, `tests/test_projections_evidence.py`, and examples
  `bay_jimmy_veg_contrast_year2.json`, `bay_jimmy_veg_manual_fit.json`, `bay_jimmy_tpah_observed.json`,
  `bay_jimmy_tpah_manual_future_unsupported.json`.
- Modified (untracked, this programme): `projections/catalogue.py`, `spec.py`, `runner.py`, `projection.py` (record_class column),
  `tests/test_projections.py` (one case), `examples/projections/bay_jimmy_retreat_2050_changed_rate.json` (label only), this file.
- No tracked file modified. Dashboard, decision pipeline, comparison layer, reports, registry, models and data are unchanged.

### Limitations
- No figures for vegetation, tPAH or contrasts yet; the CSV and manifest are the export.
- Vegetation fits carry no interval in this export (the dashboard's bootstrap band uses all surveys and is not as_of-aware).
- The 2011-2012 manual means differ slightly between the GRIIDC plot data (21.8, 51.8) and the S1 Table (22, 52); the contrast
  uses the S1 Table, as the comparison layer does.
- The tPAH analyte basis (dry or wet) is not recorded. The DIVER index is a class-level PAH-sum reference, not a plot measurement.
- Erosion-rate contrasts (comparison layer) are not exported; retreat contrasts are recorded as an evidence gap.

## Session 5 (20 Nov 2026): offline release-and-exposure feasibility. COMPLETE (data-gap outcome)

Offline only: nothing downloaded, no dependency added, no engine installed or imported.

### Finding
Candidate case `dwh_mobile_sector_2010`: Deepwater Horizon release, 20 Apr to 31 Aug 2010, SCAT segments of the Mobile ICP
(MS, AL, FL panhandle). It is the only release in the checkout with visit-level dated shoreline surveys. The essential run inputs
are missing:
- release location (absent);
- release amount or rate (absent);
- winds (absent);
- currents (absent);
- release timing (partial: start date only, as code constants);
- oil type (proxy: generic South Louisiana ADIOS crudes, no MC252 record);
- shoreline geometry (partial: segment midpoints only; the raw SCAT shapefile and `data/raw/` are not in this checkout).

No NetCDF/GRIB file exists anywhere in the checkout. Full inventory with paths, provenance, variables, units, dates, coverage
and overlap: `docs/PROJECTION_EXPOSURE_DATA_GAP.md`.

What the surveys can verify (window 20 Apr to 31 Aug 2010, 3,007 segments), from `beach_visits.csv`:
- `clear_then_oiled` 944: possible arrival window between the last clear and the first oiled visit; median 11 days (IQR 4-27,
  max 89).
- `oiled_at_first_visit` 255: window from the release start, 27 to 125 days.
- `no_oil_observed` 1,756: 29 of these were oiled after 31 Aug; 1,727 have no oiled visit in the whole 2010-2013 record.
- `not_visited_in_window` 52.

Never-oiled surveyed segments exist, so a false-alarm measure is possible with care. The proposed denominator is 731 segments:
at least two clear visits in the window and no oiled visit in the record. A simulated contact there is a candidate false alarm,
not a proven one. A "clear" visit uses the builder's ASSUMED 50% NOO-cover threshold. Unsurveyed shoreline is not in the files.

### What exists
- `catalogue.py`: evidence `noaa_scat_mobile_visits` and `noaa_scat_mobile_segments`; endpoint `shoreline_oil_contact` (unit
  `contact`); model `transport_hindcast/1` (contract only); record type `observed_survey_contact` (class observation);
  `EXPOSURE_OUTCOMES`; `ExposureInput` and `ExposureCase`; case `DWH_MOBILE_2010` with its eight-input inventory.
  `no_contact` is reserved for a completed simulation.
- `spec.py`: `_exposure_scope`, checked before the habitat checks.
  - Input errors (`SpecError`): unit, group, oiling class, arm, habitat, evidence, comparator.
  - Unsupported: `unknown_exposure_case`; `outside_domain` when the request window is outside the case window;
    `exposure_inputs_unavailable`, which names every missing essential input.
  - A `model_not_installed` branch is reachable only once every input is present. No path emits `no_contact`.
- `exposure.py` (new): `survey_contact(spec, root)` classifies each segment from the visit table. Every row is an evaluation
  observation dated after `as_of`, never a simulation input. It also returns the summary and survey limitations.
- `runner.py`: `EXPORTING_CODES = ("evidence_gap", "exposure_inputs_unavailable")`. The exposure gap exports
  `survey_contact.csv`, and the manifest gets an `exposure` block: case, inputs, `missing_essential`,
  `simulation_attempted: false`, outcome codes, survey summary and a pointer to the data-gap record.
- `examples/projections/dwh_mobile_exposure_hindcast.json`; `docs/PROJECTION_EXPOSURE_DATA_GAP.md`.

### CLI replays (fresh directories `...\scratchpad\s5\` and `...\scratchpad\s5b\`)
```
python -m src.shoreline_remediation.projections run --scenario examples/projections/dwh_mobile_exposure_hindcast.json --output runs/dwh_exposure
python -m src.shoreline_remediation.projections run --scenario examples/projections/bay_jimmy_retreat_2030.json --output runs/bj_2030
```
- Exposure: exit 3, run ID `4f39be155fd5d57f`.
  - Status `unsupported`, code `exposure_inputs_unavailable`, field `site_id`.
  - Files: input.json, manifest.json, survey_contact.csv.
  - Both evidence files present, with SHA-256 recorded.
- Retreat 2030: exit 0, run ID `8dd6de47e97a8527`, endpoint 31.059470 m. Same as Session 3.

### Tests (Session 5)
| Command | Result |
| --- | --- |
| `python -m pytest -q tests/test_projections_exposure.py tests/test_projections_evidence.py tests/test_projections_rate.py tests/test_projections.py` | **106 passed** (13 new), 0 failed, 0 skipped (14 s) |
| `python -m pytest -q tests/test_recovery_trajectories.py tests/test_recovery_view.py tests/test_comparison.py tests/test_v5_1_governance.py` | **112 passed, 1 skipped** (identical to baseline) |
| `python -m pytest -q tests/test_v54_shell.py tests/test_v54_results.py tests/test_decision_board.py` | **57 passed** (identical to baseline) |
| `python -m pytest -q "tests/test_projections.py::test_session1_baseline_files_are_unchanged"` | **1 passed** (five baseline files unchanged) |

`tests/test_projections_exposure.py`:
- CLI exit code and manifest record: reason, missing inputs, inventory fields, source hashes.
- `no_contact` never emitted.
- Survey classes re-derived from the visit table, with a 50-segment check of window start and end visits.
- Not-visited and no-oil-observed logic; false-alarm denominator arithmetic.
- Seven input errors; unknown case; outside-window abstention.
- No gnome or opendrift import.
- Data-gap record content.

### Files changed in Session 5
- Created `src/shoreline_remediation/projections/exposure.py`, `tests/test_projections_exposure.py`,
  `examples/projections/dwh_mobile_exposure_hindcast.json`, `docs/PROJECTION_EXPOSURE_DATA_GAP.md`.
- Modified (untracked, this programme): `projections/catalogue.py`, `spec.py`, `runner.py`, this file.
- No tracked file modified. No dashboard, decision pipeline, report, registry, model, data or configuration change.

### Limitations
- No adapter contract or baseline is implemented, because nothing can be run. Data-gap record section 5 lists the inputs that
  would unblock it and the hindcast rules to follow then.
- Arrival windows are inter-visit intervals, not arrival times. Survey frequency differs by segment and state.
- The case covers the Mobile sector only. Louisiana marsh visit-level SCAT is not in this checkout.

## Session 6 (20 Nov 2026): evaluation and acceptance. COMPLETE. Programme close-out

### Order of work
Delta = 0.5 m was recorded as owner-confirmed in `docs/PROJECTION_RETREAT_PROTOCOL.md` (status block and section 7) **before** any
score was computed. The protocol was then implemented as written. No rule, cutoff, bin or criterion was changed after results were
seen.

### Scientific verdicts (protocol P-RET-1; full table in protocol section 10)
| | C1 recent-interval rate | C2 M1 long-run rate b |
| --- | --- | --- |
| Pairs scored / omitted | 10 / 0 | 6 / 4 (cutoff 2012-09-17: fewer than three post-origin surveys) |
| Longest lead scored | 4.05 yr | 3.07 yr |
| MAE candidate / B1 / B0 (m) | 2.246 / 2.742 / 3.108 | 3.696 / 1.883 / 2.649 |
| Candidate minus B1 | -0.497 m (90% bootstrap -1.77 to +0.66) | +1.814 m (90% bootstrap -0.59 to +2.57) |
| Signed bias candidate / B1 / B0 | +1.83 / +2.73 / -3.11 | -3.70 / +1.87 / -2.65 |
| Criterion 1, gain >= 0.5 m | **fail** (0.497 m, short by 0.003) | **fail** |
| Criterion 2, no worse than B1 per bin | pass | **fail** |
| Criterion 3, bias within B1 + 0.25 | pass | **fail** |
| Criterion 4, B1 beats B0 | pass | pass |
| **Verdict** | **fail** | **fail** |

- **C2 identification:** at all three scored cutoffs A sits at its +20 m bound and b is negative. The long-run rate is not
  identified in substance, but the protocol's rule (tau only) did not trigger, so C2 was scored as specified. Under a
  bound-aware reading C2 is unevaluable. Recorded as a diagnostic; a future protocol version should test every bound.
- **2015-2016 jump:** the 2016 targets carry the largest errors. Without them (sensitivity, not a criterion) the C1 gain is
  0.514 m, so C1's result turns on that year.
- **What this supports:** B1 remains the default historical rate. It beats persistence but overpredicts later retreat because
  the post-spill excess fades. Nothing here is evidence beyond about four years' lead, beyond these nine plots or about 2030
  and 2050. Those outputs keep their conditional-projection labels. The decision-replay records are unaffected: legacy 5/6;
  integrated F11 2/6 against an always-active baseline of 5/6. Exposure stays `exposure_inputs_unavailable`.

### What exists (Session 6)
- `projections/evaluation.py`:
  - `untreated_plots`, `rates_at` (training surveys <= cutoff only), `score_pairs`, `summarise` (each candidate on its own pairs);
  - per-bin tables, criteria, verdict, longest lead and the without-2016 sensitivity;
  - `bootstrap` (2000 whole-plot draws, seed 20261120, descriptive) and `c2_identification`.
- `runner.write_evaluation` writes `evaluation.json`, `pairs.csv` (40 rows: 10 pairs x 4 rules, with omitted reasons) and
  `rates.csv`. `evaluation.json` records status, Delta and its confirmation, seed, source SHA-256, code hash and scope.
- CLI: `evaluate --output DIR [--n-boot N]`.
- Protocol section 10: results.

### Software acceptance
| Check | Command | Result |
| --- | --- | --- |
| Projection tests | `python -m pytest -q tests/test_projections_evaluation.py tests/test_projections_exposure.py tests/test_projections_evidence.py tests/test_projections_rate.py tests/test_projections.py` | **114 passed** (8 new), 0 failed, 0 skipped |
| Regression 1 | `python -m pytest -q tests/test_recovery_trajectories.py tests/test_recovery_view.py tests/test_comparison.py tests/test_v5_1_governance.py` | **112 passed, 1 skipped** (= baseline) |
| Regression 2 | `python -m pytest -q tests/test_v54_shell.py tests/test_v54_results.py tests/test_decision_board.py` | **57 passed** (= baseline) |
| Full suite | `python -m pytest -q tests` | 855 collected: **851 passed, 2 failed, 2 skipped** (171 s); 851 = 737 baseline + 114 projection |
| Reference cases | `python -W ignore scripts/capture_projection_baseline.py --out results/projection_baseline_session6` | all **5 files byte-identical** to `results/projection_baseline` (4 normalized reports + summary of decisions, abstentions and controls) |

Full-suite failures and skips are the same as the Session 1 baseline:
- `test_data_catalogue::test_every_data_file_is_catalogued_and_unchanged` and `test_p5_demo::test_model_card_has_provenance`:
  `core.autocrlf` hashes.
- The two PDF-transcription tests: `pdftotext` not installed.

**Browser acceptance (actually performed).** Streamlit 1.67.0 server on localhost:8765, headless Chromium (Playwright 1.65.2,
already installed) at 1440x1000. Script: scratchpad `browser_check.py`.
- **Bay Jimmy** (Map > "Use Bay Jimmy (worked example)" > Run assessment):
  - page renders in the dark theme with no Streamlit exception;
  - finding "+34 percentage points … (90% interval +19 to +49; 5 treated and 9 untreated plots)";
  - outcome "At least one intervention is recommended over natural recovery", matching baseline `intervention_recommended`;
  - the continuous-trajectories section is present.
  - Downloaded HTML report: 27,118 bytes, title "Worked example: cell 8018_32612 …"; contains the baseline headline,
    pipeline f9-v3, commit 726d944, seed 20261112, 3000 draws; no traceback.
- **Screening-only case** (Assessment > "Exposed rocky shore" (ESI 1A) > Run):
  - finding "screening allows 8 of 15 methods, 3 of them conditionally, and excludes 7", matching the baseline classes;
  - "No site-specific numerical forecast …"; screening table shown; no trajectory section; no exception.
  - Downloaded HTML report: 18,961 bytes; baseline headline "No clear difference from natural recovery …" present.
- **Not checked:** mobile width, other browsers, keyboard and screen-reader use, every expander and tab, mangrove and typed
  marsh in the browser (covered by AppTest and the baseline capture), visual comparison with an earlier release.

### Change-set review (`git status --short --branch`; `git diff --name-status 726d944`)
- **Tracked diff against 726d944: empty.** No dashboard source, configuration, asset, public schema, data, model, registry or
  report file changed.
- **Untracked, owner's files, not touched:** `.vscode/extensions.json`, `AGENTS.md`, `docs/CLAUDE_SCENARIO_PREDICTION_PLAN.md`.
- **Untracked, this programme (38 files):**
  - `src/shoreline_remediation/projections/`: `__init__`, `__main__`, `catalogue`, `spec`, `runner`, `projection`, `figure`,
    `evidence`, `exposure`, `evaluation` (10 files, about 1,830 lines). Imported by no production module (tested). Imports no
    Streamlit, UI, dashboard, decision or legacy code beyond what the parent package `__init__` already loads (tested).
  - Tests: `tests/test_projections.py`, `_rate`, `_evidence`, `_exposure`, `_evaluation` (5 files, 114 tests).
  - Examples: `examples/projections/*.json` (9 scenarios; no synthetic values).
  - Docs: `docs/PROJECTION_HANDOFF.md`, `PROJECTION_RETREAT_PROTOCOL.md`, `PROJECTION_EXPOSURE_DATA_GAP.md`.
  - Baselines: `scripts/capture_projection_baseline.py`; `results/projection_baseline/` (Session 1, read-only, hash-tested);
    `results/projection_baseline_session6/` (acceptance capture, identical).
- **Reviewed for:** debugging leftovers and secrets (none; prints are CLI output only), personal names (none written; SCAT team
  fields were dropped upstream), and synthetic data outside tests (none).
- Nothing committed or pushed. Recommended first authorised commit: everything above except the owner's three files, unless
  the owner wants them included. Per owner instruction this includes `results/projection_baseline/`.

### Replay (repo root)
```
python -m src.shoreline_remediation.projections run --scenario examples/projections/bay_jimmy_observed.json --output runs/obs
python -m src.shoreline_remediation.projections run --scenario examples/projections/bay_jimmy_retreat_2030.json --output runs/bj_2030
python -m src.shoreline_remediation.projections run --scenario examples/projections/bay_jimmy_retreat_2050_changed_rate.json --output runs/bj_2050
python -m src.shoreline_remediation.projections compare --runs runs/bj_2030 runs/bj_2050 --output runs/bj_sensitivity
python -m src.shoreline_remediation.projections run --scenario examples/projections/bay_jimmy_veg_contrast_year2.json --output runs/veg_contrast
python -m src.shoreline_remediation.projections run --scenario examples/projections/bay_jimmy_veg_manual_fit.json --output runs/veg_fit
python -m src.shoreline_remediation.projections run --scenario examples/projections/bay_jimmy_tpah_observed.json --output runs/tpah
python -m src.shoreline_remediation.projections run --scenario examples/projections/bay_jimmy_tpah_manual_future_unsupported.json --output runs/tpah_gap
python -m src.shoreline_remediation.projections run --scenario examples/projections/rocky_retreat_unsupported.json --output runs/rocky
python -m src.shoreline_remediation.projections run --scenario examples/projections/dwh_mobile_exposure_hindcast.json --output runs/exposure
python -m src.shoreline_remediation.projections evaluate --output runs/p_ret_1
```
Expected exits: 0, 0, 0, 0, 0, 0, 0, 3, 3, 3, 0. Each output path must not exist beforehand (exit 4 otherwise).
`runs/` is not git-ignored, so use a path outside the repository or delete `runs/` after inspection.

### Outstanding limitations
- **Retreat projections:** no rule beats B1, and B1 overpredicts within the record. Every post-2016 value is arithmetic on a
  stated rate. One site, nine plots, no independent site; transfer is unevaluated.
- **Vegetation and tPAH:** no figures; fits carry no interval; manual plots end in 2012; tPAH has two dates and no treatment
  decline.
- **Exposure:** blocked by missing release and forcing inputs (`docs/PROJECTION_EXPOSURE_DATA_GAP.md`).
- **Housekeeping:** the parent package `__init__` loads the legacy `HybridDecisionModel` (separate maintenance change, per
  owner).
- **Line endings:** the two autocrlf test failures remain an environment issue.
- **Protocol:** a future version should test every M1 parameter bound and justify Delta against a management need.

### Possible next steps (not started)
1. Owner review, then an authorised commit.
2. Protocol P-RET-2 (new version, specified before any scoring): bound-aware identification, and possibly a rule for the fading
   excess.
3. Exposure inputs, if the owner authorises fetching them.
4. Figures for the vegetation and tPAH exports.

## Pre-commit review fixes (20 Nov 2026, after Session 6). COMPLETE

Each finding received a regression test in `tests/test_projections_review_fixes.py` first. All five original tests failed on the
reviewed code for the reported reason and pass after the fix. A sixth test, for an adjacent defect found while replaying
finding 1, was also written before its fix and failed first.

| # | Finding | Fix | Evidence |
| --- | --- | --- | --- |
| 1 | A segment oiled before the window received a first-arrival window inside it (ALBA1-001 with a 1 July start: "oiled_at_first_visit", 1-6 July) | New class `oiled_before_window`: `prior_oiled_observation` keeps the first oil on or before as_of (ALBA1-001: 2010-06-04); window fields unset; in-window visits still counted (ALBA1-001: 5 visits from 6 July) | test 1 |
| 1a (adjacent) | With a later start, arrival windows began at as_of even when the segment had a clear visit before it, or none at all | Window start = last clear visit before the first oil in the whole record (may precede as_of); with no clear visit, the case's release start (20 Apr 2010) | test 1a; 1 July start: 160 segments move from `oiled_at_first_visit` to `clear_then_oiled` |
| 2 | A window holding only partial_clear visits was "no_oil_observed" (FLGU1-135, 12-31 Aug) | New class `inconclusive_partial_clear`; n_visits kept; excluded from `no_oil_observed` and the candidate false-alarm denominator | test 2 |
| 3 | Figures with an earlier as_of drew later surveys as ordinary observations | Surveys available at as_of are solid ("N survey dates available at as_of"); later ones are hollow and labelled "Retrospective observations after as_of … not used by the projection" in single-run and comparison figures. Anchor label reads "last survey on or before as_of"; the subtitle states as_of; the y-range includes later surveys; the shaded-span label is dropped when it would collide | test 3; rendered and inspected (scratchpad `s7\early_2030\projection.png`, `s7\early_cmp_v2.png`, as_of 2013-09-08) |
| 4 | Mechanical 2012 summaries listed all 9 mechanical plot IDs beside n = 5 | `evidence.plot_membership`: vegetation IDs come from GRIIDC plot-level records for that survey, only when their count equals the published n (mechanical 2012: 16-17, 17-18, 19-20, 20-21, 22-23; mean 22.6% vs published 23%). S1-only tPAH lists IDs only when n equals the whole group (untreated 9/9, manual 5/5); mechanical tPAH 2012 has blank IDs and "not established by the source". New `plot_membership` / `comparator_plot_membership` columns on group-mean, contrast and vegetation observation rows. Published values unchanged (mechanical 23%, n 5, contrast equal to the comparison layer; manual +34, 18.96 to 49.04) | tests 4a, 4b; existing Session 4 contrast tests still pass |

**Mobile-sector replay** (`dwh_mobile_exposure_hindcast.json`, start 20 Apr 2010): exit 3, `exposure_inputs_unavailable`, run ID
`4f39be155fd5d57f`, every total **unchanged**:
- 944 `clear_then_oiled`;
- 255 `oiled_at_first_visit`;
- 1,756 `no_oil_observed`;
- 52 not visited;
- 0 `oiled_before_window`;
- 0 inconclusive;
- candidate false-alarm denominator 731.

Later-start counts are in `docs/PROJECTION_EXPOSURE_DATA_GAP.md` section 3.

**Observation, not changed:** the example rates (1.43 and 2.19 m/yr) were fitted to surveys through 2016. A scenario that copies
them with an earlier as_of uses later information in its stated assumption. The source text says so, and the rate stays a user
assumption. Use rates computed at the cutoff (protocol B1) for retrospective scenarios.

### Tests (review fixes)
| Command | Result |
| --- | --- |
| `python -m pytest -q tests/test_projections_review_fixes.py tests/test_projections_evaluation.py tests/test_projections_exposure.py tests/test_projections_evidence.py tests/test_projections_rate.py tests/test_projections.py` | **120 passed** (6 new), 0 failed, 0 skipped |
| `python -m pytest -q tests/test_recovery_trajectories.py tests/test_recovery_view.py tests/test_comparison.py tests/test_v5_1_governance.py` | **112 passed, 1 skipped** (= baseline) |
| `python -m pytest -q tests/test_v54_shell.py tests/test_v54_results.py tests/test_decision_board.py` | **57 passed** (= baseline) |
| `python -m pytest -q tests` | 861 collected: **857 passed, 2 failed, 2 skipped** (176 s); 857 = 851 + 6 new. **No new failures.** Known only: `test_data_catalogue` and `test_p5_demo` hash failures. Its list names 102 paths, all under `data/` and none from this work, and all 203 tracked data files equal HEAD after line-ending normalisation. The 2 skips are the PDF-transcription tests (`pdftotext` not installed) |
| `python -W ignore scripts/capture_projection_baseline.py --out results/projection_baseline_review` | 5/5 files byte-identical to `results/projection_baseline` (the temporary directory was then deleted) |

### Files changed by the review fixes
- `projections/exposure.py`: classes, prior oil, arrival windows, summary.
- `projections/figure.py`: as_of split and labels.
- `projections/evidence.py`: plot membership.
- `docs/PROJECTION_EXPOSURE_DATA_GAP.md`: section 3.
- Created `tests/test_projections_review_fixes.py`.
- This file.
- No tracked file modified; dashboard and decision pathway unchanged.

## Follow-up (21 Nov 2026): complete source provenance for year-2 vegetation contrasts. COMPLETE

Problem: since the plot-membership fix, a `field_contrast/1` vegetation run reads three sources, but its manifest listed only the
one cited in the scenario (the S1 Table).

Fix:
- `catalogue.DEPENDENCIES` maps (model, endpoint) to sources the run reads beyond its required citations, each with what it is
  read for. Contrast runs: `zengel2022_griidc_vegetation` (plot-level 2012 records for membership) and
  `zengel2022_griidc_field_positions` (sheet "DSAS lumped", plot types).
- `runner._sources` lists the cited sources first, then the resolved dependencies. Each entry has a SHA-256 and two new fields:
  `cited_in_spec` and `read_for`.

Scenario files are unchanged and still replay: the runner resolves the dependencies, so the spec, and therefore the run ID, are
unchanged.

Replay: `python -m src.shoreline_remediation.projections run --scenario examples/projections/bay_jimmy_veg_contrast_year2.json
--output <new dir>` exits 0 with run ID `1c3e23fab97e18f4` (unchanged). Manifest sources:
- `zengel2015_s1_group_means`: 585d4ff7…, cited;
- `zengel2022_griidc_vegetation`: bb2b4891…, resolved;
- `zengel2022_griidc_field_positions`: e1615f13…, resolved.

The contrast is unchanged: +34.0 points, 90% Welch 18.962854 to 49.037146, n 5 and 9.

Regression test (written first; it failed with only the S1 source listed): `tests/test_projections_review_fixes.py::
test_contrast_manifest_lists_all_three_sources_read`. It replays the existing example and checks:
- the run ID;
- exactly three sources, each present, with a SHA-256 equal to the file's;
- the cited and resolved flags;
- the +34 estimate and its interval.

| Command | Result |
| --- | --- |
| `python -m pytest -q tests/test_projections_review_fixes.py tests/test_projections_evaluation.py tests/test_projections_exposure.py tests/test_projections_evidence.py tests/test_projections_rate.py tests/test_projections.py` | **121 passed** (1 new), 0 failed, 0 skipped |

Files: `projections/catalogue.py` (DEPENDENCIES), `projections/runner.py` (`_sources`), `tests/test_projections_review_fixes.py`,
this file. Targeted regressions and the full suite were not rerun for this change: it touches only the research package's manifest
writer. No tracked file changed.

Remaining: other runs that read files outside the evidence catalogue are not yet listed. tPAH observed runs read
`results/pah_decline/station_campaign.csv` and `models/pah_decline_v1.json` through `recovery_view`. They are candidates for the
same mechanism once given evidence IDs.

## Follow-up (21 Nov 2026): provenance of the DIVER reference index. COMPLETE

Problem: tPAH runs consult `models/pah_decline_v1.json` (model card) and `results/pah_decline/station_campaign.csv` (campaign
table) through `recovery_view`, but neither had an evidence ID or appeared in manifests.

Fix:
- **New evidence IDs:** `pah_decline_v1_card` and `pah_decline_v1_campaigns`. A test checks they resolve to
  `recovery_view.PAH_CARD` and `recovery_view.CAMPAIGNS`.
- **Every manifest source entry** now has `cited_in_spec`, `used_in_calculation` and `roles` (what it was consulted for).
  `runner._use()` records each source as the calculation consults it, and adds an uncited source with its SHA-256.
- **Usage is recorded on every export path:** retreat, vegetation observations, fit and contrast, tPAH, and exposure.
- **`evidence.diver_index`** now checks campaign support first. It reads the model card and rate table only when the index will
  be exported, and returns the list of sources it consulted.
- **Spec files and run IDs are unchanged:** tPAH observed `fde8109d673e2e41`, PAH gap `41de4fc939fa68fa`, retreat 2030
  `8dd6de47e97a8527`, contrast `1c3e23fab97e18f4`.

| Path | Status | Sources: cited / used (SHA-256 prefix) |
| --- | --- | --- |
| Heavy-class tPAH (`bay_jimmy_tpah_observed.json`) | completed; index exported (15 points) | S1 table cited/used (585d4ff7…); heavy-class rate table cited/used (1699fc88…); campaigns not cited/used (583fae97…); model card not cited/used (9cdfa889…) |
| Early as_of 2012-10-15 (same spec, as_of and end changed) | completed; index withheld after the support check ("estimated from campaigns up to about 2013-10-11") | S1 used; campaigns not cited/used; rate table cited/**not used**; model card **not consulted** (absent) |
| Treatment-specific future request (`bay_jimmy_tpah_manual_future_unsupported.json`) | unsupported `evidence_gap`; observed.csv only | S1 cited/used; rate table cited/**not used**; no campaign or card read |

Checked against the Session 4 outputs (scratchpad `s4`) by replaying into scratchpad `s9`:
- the index values, dates, intervals, reference and support columns are identical (15 rows);
- the tPAH observations for the untreated run (260 and 112 mg/kg) and the manual gap run (220 and 101 mg/kg) are identical in
  value, SE, interval, n, dates, depth and analyte.

Regression tests (written first; all five failed before the change): `tests/test_projections_pah_sources.py`:
- the evidence IDs resolve to the files `recovery_view` reads;
- heavy export;
- early withhold;
- evidence gap;
- usage flags on the retreat and contrast runs.

| Command | Result |
| --- | --- |
| `python -m pytest -q tests/test_projections_pah_sources.py tests/test_projections_review_fixes.py tests/test_projections_evaluation.py tests/test_projections_exposure.py tests/test_projections_evidence.py tests/test_projections_rate.py tests/test_projections.py` | **126 passed** (5 new), 0 failed, 0 skipped (22 s) |

Files:
- `projections/catalogue.py` (two evidence IDs);
- `projections/runner.py` (`_source_entry`, `_use`, usage on every path);
- `projections/evidence.py` (`diver_index` order and `uses`);
- `tests/test_projections_pah_sources.py` (new);
- this file.

Targeted regression suites and the full suite were not rerun: the change is inside the research package only. No tracked file
changed. Everything is local and uncommitted.

## Session 6 starting point as written at the end of Session 5 (historical; done, see the Session 6 section)

Recommended: **Session 6, retreat evaluation (protocol P-RET-1)**, which needs no new data.
1. Owner confirms or changes Delta = 0.5 m before any scoring (protocol section 7).
2. Implement scoring in `projections/evaluation.py`:
   - cutoffs 2012-09-17, 2013-09-08, 2014-09-26 and 2015-09-30 against every later survey;
   - rules B0, B1, C1 and C2, computed only from surveys on or before each cutoff;
   - signed and absolute errors of the group-mean increment, per pair and per lead-time bin;
   - plot cluster bootstrap with seed 20261120;
   - gates exactly as written.
   Report through the CLI (new `evaluate` subcommand) without changing any rule after seeing results.
3. Final acceptance (plan Session 6):
   - rerun the full suite;
   - run `scripts/capture_projection_baseline.py --out results/projection_baseline_session6` and diff against
     `results/projection_baseline`;
   - browser check of Bay Jimmy and a screening-only case with the download;
   - scope review of the diff against `726d944`.

Exposure work resumes only when the owner supplies or authorises fetching the inputs in data-gap record section 5. Then: adapter
contract, a pre-specified simple baseline, a frozen-input hindcast protocol, and an optional-environment engine evaluation.

## Session 5 starting point as written at the end of Session 4 (historical; done, see the Session 5 section)

Per the plan, Session 5 (release and exposure scenarios) is independent of the retreat milestone and starts with a data
inventory:
1. Check branch/HEAD/status; read this file and the plan's Session 5.
2. Inventory archived forcing (currents, winds) and independent shoreline-contact observations already in the repository
   (`docs/DATA_CATALOGUE.md`, `docs/F7_SECOND_SPILL_INVENTORY.md`, `data/external/scat_dwh*`), without downloading anything.
3. If forcing or contact observations are missing, write a data-gap record (a new `docs/PROJECTION_EXPOSURE_DATA_GAP.md` and an
   `Unsupported("forcing_unavailable")` path in the catalogue), and keep the offline retreat workflow usable with no new
   dependency. PyGNOME, if evaluated, must be an optional environment that the projection tests never import.
4. Rerun all `tests/test_projections*.py` and both regression commands.

Alternatively, if the owner prefers to defer Session 5, go to Session 6 (evaluation): implement protocol P-RET-1 scoring once Delta
is confirmed.

## Session 4 starting point as written at the end of Session 3 (historical; done, see the Session 4 section)

1. Check branch/HEAD/status; read this file, the protocol and the plan's Session 4 table.
2. Historical comparison export for manual removal versus natural recovery: a `historical_contrast/1` output that reads the
   existing comparison layer / field records for the matching Bay Jimmy endpoint, year, groups and comparator, with sample sizes,
   uncertainty, observational design and shared-source IDs. It must be a separate record type (`literature_or_field_contrast`) and
   must not be turned into an annual benefit through 2050.
3. Vegetation cover and soil tPAH: implement the endpoints as observed records first (existing loaders in
   `recovery_trajectories.vegetation_plots` and `treatment_effects.load`), with the experimental fit labelled as such and manual-plot
   continuation recorded as a borrowed-rate assumption. PAH stays a relative index within 2011.3 to 2013.78 support plus measured
   tPAH with depth, analyte set and units.
4. Exports must distinguish measured values, field contrasts, experimental fits and conditional projections in a single
   `record_type` vocabulary; missing evidence produces an `Unsupported` reason and no point or interval.
5. Rerun `tests/test_projections*.py` and both regression commands; record counts here.

## Session 3 starting point as written at the end of Session 2 (historical; done, see the Session 3 section)

1. Check branch/HEAD/status; read this file, the protocol and the plan's Session 3.
2. Add model `rate_continuation/1` to `catalogue.MODELS` and a `projection.py` module: anchor = last observation on or before
   `as_of` (Unsupported `no_anchor_observation` if none); retreat(t) = anchor + integral of the rate over actual elapsed time,
   with `retreat_rate` before and `changed_retreat_rate` after `rate_change_date` (validate that the change date lies between
   anchor and end; both rates required when a change date is given). Output dates from `cadence`, always including the anchor and
   `end_date` exactly, so cadence cannot change the endpoint value.
3. Historical-rate option: `retreat_rate` with origin `fitted_parameter` and source naming the rule (B1 per protocol section 6,
   computed only from surveys on or before `as_of`). Record which was used (user or historical) in the manifest and rows.
4. `projection.csv` rows: record_type `conditional_projection`, origin of the rate, `status_label` "conditional projection:
   holds only IF the stated rate applies", no interval columns filled (a range across two rates is a sensitivity range, kept as
   separate runs/curves). Standalone matplotlib PNG/SVG (Agg backend) with survey markers, fitted-support span, extrapolation
   start line, scenario name, unit, support cutoff and "conditional" on the figure.
5. Examples: `bay_jimmy_retreat.json` (historical rate to 2030) and a changed-rate counter-scenario to 2050.
6. Tests: both scenarios meet at the anchor; zero rate gives a flat line; a change date between output points integrates
   exactly; monthly and annual endpoints agree; rocky/mangrove still unsupported; no recommendation field anywhere; rerun the
   two regression commands and `tests/test_projections.py`.

## Session 2 starting point as written at the end of Session 1 (historical; done, see the Session 2 section)

Deviations as implemented: tests are in `tests/test_projections.py` (one file); the example added is
`bay_jimmy_observed.json`, and `bay_jimmy_retreat.json` is left for Session 3.

1. Check branch/HEAD/status; read this file and the plan's Session 2.
2. Create `src/shoreline_remediation/projections/` with `__init__.py`, `__main__.py` (CLI: `run --scenario <json> --output <dir>`),
   `spec.py` (versioned scenario dataclass + JSON load/validate; every input carries an origin: observation, derived, literature,
   fitted, user_assumption, synthetic_fixture; missing distinct from zero; structured `Unsupported(reason)` for unknown site,
   endpoint or habitat), `runner.py` (new run directory or clear error if it exists; manifest with input copy, git commit, source
   checksums, dependency versions, seed; `status: running` written first and replaced by `completed`).
3. Allowed imports: `recovery_trajectories` (`field_positions`, `decimal_year`, `ORIGIN`), `treatment_effects` paths. Forbidden:
   `scenario_runner`/`HybridDecisionModel`, any Streamlit module. Add a test asserting that `dashboard.py`, `site_view.py`,
   `ui_pipeline.py`, `decision_pipeline.py` and `ui_*.py` do not import `projections`.
4. Tests in `tests/test_projections_spec.py`: spec round-trip, two identical offline runs, invalid units/dates/non-finite values,
   existing output directory, rocky/mangrove unsupported reasons, synthetic fixtures only under `tests/`.
5. Add `examples/projections/bay_jimmy_retreat.json` only once the spec is fixed (Session 3 fills in the projection).
6. Rerun the two targeted regression commands above plus the new tests; record counts here.
