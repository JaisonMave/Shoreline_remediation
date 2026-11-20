# Scenario-based shoreline projections with Claude Code

Implementation plan | 20 November 2026 | Local branch `codex/scenario-prediction-plan` | Base `model_v5_1` at `726d944`

## Product and first milestone

A scientist runs a saved scenario from the repository, changes one documented assumption, and compares the resulting shoreline trajectories with the historical field record. Each exported point identifies its outcome, unit, date, evidence source and assumptions. The existing dashboard continues to open, run assessments and export its usual report through the same controls. The new deliverable is a Python API, a local command-line runner and standalone results a stakeholder can inspect without installing the dashboard.

Start with **cumulative shoreline retreat in metres for the heavily oiled Bay Jimmy untreated plots**. This endpoint has dated positions, a physical unit and an existing plot-level fitter. Make 2030 and 2050 **planning horizons** selectable in an input file. A year selected by a user establishes the end of a scenario, never its validated horizon. Branch completion is a reproducible research workflow. Scientific promotion is a separate outcome with its own evidence requirements.

## Repository starting points

| Read first | How to use it |
| --- | --- |
| `CLAUDE.md`, `AGENTS.md`, `docs/V5_1_HANDOFF.md`, `docs/V5_4_RECOVERY_VIEW.md` | Follow repo rules and the current recovery-view addendum. The plot-level retreat and vegetation records used by the continuous fits end in 2016. The borrowed PAH rate has support to about 2013.78. |
| `docs/SCENARIO_PROGRAMME_PLAN.md`, `docs/V5_1_VALIDATION.md`, `models/registry.json` | Reuse prior experiments and their recorded outcomes. Edge-loss point estimates and PAH decline have narrow validated uses. Read the cards before reusing either. The F5 and D32 gates remain failed. |
| `src/shoreline_remediation/recovery_trajectories.py`, `recovery_view.py`, `comparison.py` in that package | Use existing loaders, dates, units, fit diagnostics and field-comparison provenance. Distinguish the Bay Jimmy plots from the larger mapped cell. Several publications use the same plots. |
| `src/shoreline_remediation/data_model.py`, `scenario_composer.py`, `scenario_runner.py` in that package | Reuse compatible types and conventions. The composer already has horizon and uncertainty logic with documented limitations. The existing runner imports the legacy `HybridDecisionModel`. Give the research workflow its own entry point. |

## Work in six Claude Code sessions

### 1. Capture the baseline and specify the experiment

- Inspect branch, HEAD, and status. Identify the Python interpreter used for this checkout. Capture the regression commands below and their actual results before making implementation edits. Record existing failures, including their cause where verified.
- Create a small protocol covering endpoint, population, time origin, observation depth where relevant, units, evidence window, candidate models, baseline, data splits, error measures and acceptance criteria. Specify a minimum useful gain with scientific justification before fitting. If its value needs owner input, mark promotion pending and continue developing the scenario runner.
- Record mapped Bay Jimmy, typed marsh, rocky and mangrove reference cases. Use reproducible inputs and seeds. Record current decisions, exclusions, abstentions, report fields and visible controls. Normalize only genuinely volatile fields such as a generation timestamp.
- **Exit check:** another session can identify which data calibrated each quantity, which data are available for an independent test, and which existing behaviours to compare after implementation.

### 2. Build a versioned scenario contract and offline runner

- Suggested location is a small `projections/` package under `src/shoreline_remediation/`. Start with a spec, runner and tests. Keep imports flowing from the research package to reusable scientific modules. The production dashboard and decision engine must have zero imports of the research package.
- Input fields include schema version, stable site and plot-group identifiers, habitat, oiling class, endpoint and unit, reference or intervention, last observation or as-of date, end date, output cadence, assumption IDs with values and units, evidence IDs, model version and random seed. Distinguish a missing value from a measured zero.
- For every input, retain its origin (observation, derived value, literature, fitted parameter, user assumption or synthetic fixture). Validate units, date order, source identifiers, finite values and habitat scope before calculating. Unknown site or unsupported endpoint returns a structured reason.
- Proposed command once implemented, from the repo root:

  ```powershell
  python -m src.shoreline_remediation.projections run --scenario examples/projections/bay_jimmy_retreat.json --output runs/bay_jimmy_reference
  ```

- Write each run to a new directory. Include the exact input, model/code version, source checksums, dependency versions and seed in a manifest. An existing output directory should yield a clear error or a new run ID. An interrupted run must be distinguishable from a completed run.
- **Exit check:** round-trip a spec and reproduce the same normalized output on two offline runs. Invalid input produces a useful message. Synthetic fixtures appear only in tests or expressly identified demonstrations.

### 3. Deliver the first continuous projection

- Reproduce observed retreat from the existing field-position loader. Confirm the reference date, group, sign, units and final survey. Write measured points at their actual dates. Reproduce the existing within-record fit before adding future values.
- First scenario: continue an explicitly chosen annual retreat rate from the final observed group mean. For elapsed years `t`, compute `retreat(t) = last_observed_retreat + rate * t`. Record whether the rate came from the historical series or the user. Use actual elapsed time so choosing monthly instead of annual output cannot change the endpoint.
- Counter-scenario: use the same initial value and a user-specified rate after a stated change date. Integrate both periods continuously. This permits a concrete comparison without inventing a local storm, sea-level or treatment coefficient. Use named climate pathways only when versioned forcing data and a defensible mapping into retreat are available.
- Export a tidy trajectory table, manifest, assumption summary and standalone plot. Place observation markers at survey dates, identify the fitted support, and mark the start of extrapolation. Put the scenario name, units, support cutoff and conditional status on the figure itself.
- Keep alternative assumptions as separate curves. Define a shaded band only if the sampling method, level, unit of resampling and included uncertainty sources can be described. A range across two chosen rates is a sensitivity range. The existing plot bootstrap describes historical fit uncertainty and cannot by itself quantify future storms or model-form error.
- **Exit check:** both scenarios meet at the anchor date. A zero-rate fixture gives a flat line. A change date between output points integrates correctly. Monthly and annual endpoints agree. Unsupported rocky or mangrove runs return reasons. The same Bay Jimmy dashboard assessment still produces the baseline result.

### 4. Add evidence and further endpoints individually

| Request | First supported output | Evidence required for a stronger claim |
| --- | --- | --- |
| Manual removal versus natural recovery | Historical comparison for matching Bay Jimmy endpoint, year, groups and comparator. Include sample sizes, uncertainty, observational design and shared-source IDs. | Independent treated and untreated units with comparable baseline conditions and repeated follow-up before estimating transferable treatment effects. |
| Vegetation cover | Existing observed total cover and within-record experimental fit. Manual plots have two observed years. Any later path using the untreated rate records that assumption. | Later manual-plot observations and a test on independent plots/sites. Check bounded cover and the fit's documented miss of the 2016 decline. |
| Soil PAH | Existing within-scope relative decline reference over its supported campaign dates. Display measured concentration with its depth, analyte set and units. | Compatible concentrations over time, background or residual pool evidence, and treatment histories before estimating long-run absolute or treatment-specific concentrations. |
| Rocky shore, mangrove or a new location | A scoped evidence summary, screening outcome where available and an explicit reason when a requested number is unavailable. | Habitat-specific measurements and an independent evaluation for that endpoint and horizon. |

Keep intervention assumptions explicit when comparing future scenarios. A historical contrast at year two does not establish an annual benefit through 2050. Users should be able to retrieve the field evidence even when the requested projection is unavailable.

**Exit check:** exports distinguish measured values, literature contrasts, experimental fits and conditional projections. Missing evidence produces no fabricated point or interval. The new runner cannot assign a recommendation.

### 5. Extend to release and exposure scenarios when inputs exist

This session can follow the retreat milestone independently. Add release location, time, oil type, amount with units, shoreline geometry, and versioned current and wind inputs. Inventory available archived forcing and independent shoreline-contact observations first. If these are missing, deliver a data-gap record and keep the observed-site workflow usable.

Evaluate one transport adapter, with PyGNOME as a candidate. Run it in an optional environment so its dependencies cannot alter dashboard startup. Its contract should return segment ID, arrival window, estimated exposure, forcing provenance and uncertainty method. Treat ensemble member agreement as a scenario frequency until calibration supports probabilities. Include distinct outcomes for missing forcing, model failure, outside domain and a successful run with no simulated contact.

For a historical hindcast, freeze inputs as of the scenario start and reserve later shoreline observations for evaluation. Compare contact hits, misses, false alarms and arrival-time errors with a simple pre-specified baseline. A contact estimate can identify where field assessment would be useful. Any future mapping to an oiling class requires independent comparison with field classifications. Exposure alone supplies no treatment effect.

**Exit check:** replay a documented hindcast or explicitly record insufficient data. The offline retreat example still runs with the transport package absent.

### 6. Evaluate claims and accept the branch

- For within-site forecasts, progressively fit through an earlier survey year and predict later surveys. Report actual tested lead times and number of independent plots. For transfer, hold out whole sites or spills and account for repeated measurements and shared plots. Reserve final evaluation data from tuning. With one eligible site, cross-site skill stays unevaluated.
- For retreat, report error and signed bias in metres against constant-rate and last-observation baselines. For cover, use percentage-point errors. For PAH, specify the analyte and use the predeclared scale. For any claimed prediction interval, assess empirical coverage and width at each supported horizon. Report failures and sample counts by group.
- Preserve the historical record: legacy replay 5/6, integrated F11 replay 2/6, always-active baseline 5/6. These numbers evaluate different decision rules and supply no validation for the new curves. Review scientific claims per endpoint, population and horizon. A successful six-year test supplies no evidence of 2050 accuracy.
- Rerun regression tests and compare production case outputs with Session 1. Include new, untracked files in the scope review. Confirm the diff against the original base excludes dashboard sources, configuration, assets and existing public schemas. A hidden flag or a new dashboard tab would change the agreed scope.
- **Exit check:** a clean checkout with the eventual authorized changes can reproduce a Bay Jimmy reference run, a changed-rate run and an unsupported-site result from documented commands. Each numerical series traces to a source or assumption. Record scientific gate outcomes separately from software and UI test results.

## Regression and session handoff

Run these existing checks from the repo root for the baseline and final comparison. Add the new projection tests to the targeted run as they are implemented.

```powershell
python -m pytest -q tests/test_recovery_trajectories.py tests/test_recovery_view.py tests/test_comparison.py tests/test_v5_1_governance.py
python -m pytest -q tests/test_v54_shell.py tests/test_v54_results.py tests/test_decision_board.py
python -m pytest -q tests
git diff --name-status 726d944
git status --short --branch
```

Use the existing Streamlit app tests for navigation, controls and decisions. At final acceptance, exercise Bay Jimmy and a screening-only case in the running dashboard, including the download, and compare them with the baseline. Record actual browser observations, environment, and any untested path. At each handoff record changed paths, exact commands, pass/fail/skip counts, scientific limitations and the next small task. Commit and push only with explicit owner authorization.

## Paste into Claude Code

Open Claude Code from this repository with the plan present in the working tree. For the first implementation session, paste:

> Read CLAUDE.md, AGENTS.md, and docs/CLAUDE_SCENARIO_PREDICTION_PLAN.md. Verify that I am on codex/scenario-prediction-plan and inspect the working tree before editing. Execute Session 1 only. Use the existing validation and handoff records to prepare the Bay Jimmy retreat protocol, identify the real data cutoffs and collect a reproducible regression baseline. Preserve the existing dashboard, decision pipeline, reports and my untracked files. At the end, show the evidence and actual test results, list changed files and write the next session's starting point. Leave changes local and uncommitted.

For subsequent sessions:

> Read the plan and last handoff. Implement the next incomplete session through its exit check. Reuse the current loaders and fit code where compatible. Work on the same branch and expose new capabilities through the research API, CLI and standalone exports. If scientific data are missing, return an explicit unavailable outcome and finish the independent engineering checks. Record the exact replay commands, tests, output paths and limitations. Leave changes local and uncommitted.
