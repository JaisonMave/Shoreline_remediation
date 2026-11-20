# Shoreline Remediation Decision Support

An evidence-led prototype for screening oil-spill shoreline response options. It combines SCAT/shoreline inputs, feasibility rules, field and literature evidence, and scoped prediction components. It is a research prototype—not an operational response recommendation system.

## Start here

On the scenario branch, select **Use Bay Jimmy**, run the assessment, and open **Explore future scenarios**
below the historical trajectories. Adjust the end date and the assumed retreat rate, optionally change the rate
on a second date, and download the scenario inputs or resulting series. The curve describes the nine untreated
Bay Jimmy plots under the selected assumptions. The long-term endpoint has no independent forecast validation.

**Current dashboard (17 Nov 2026, branch `model_v5_1`):** map-first assessment with continuous experimental recovery trajectories. Start with
[`docs/V5_4_RECOVERY_VIEW.md`](docs/V5_4_RECOVERY_VIEW.md) (continuous trajectory equations, sources, recovery-plot fixes and scientific limits) and
[`docs/V5_4_PLOT_FIRST_HANDOFF.md`](docs/V5_4_PLOT_FIRST_HANDOFF.md) (assessment and treatment comparisons).
The older recovery-view and synthetic-demonstration sections are no longer displayed; their source helpers remain for reproducibility.
The retained **Continuous trajectories: experimental fits and conditional scenarios** section shows Bay Jimmy marsh-edge retreat fits,
logistic total-cover fits and conditional PAH decay, with observed survey points and uncertainty. Manual cover borrows the untreated rate;
all PAH scenarios borrow a class-wide rate with different sampling depth and analytes. These are one-site research curves, not validated
site forecasts or treatment-effect estimates, and do not change screening, comparisons or reports.
For architecture/governance history see [`docs/V5_1_HANDOFF.md`](docs/V5_1_HANDOFF.md); for interpretation of validation results see
[`docs/V5_1_VALIDATION.md`](docs/V5_1_VALIDATION.md).

Latest (V5, 14 Nov 2026, branch `model_v4`): [`docs/FINDINGS_V5.md`](docs/FINDINGS_V5.md) (plain summary at the top; four gated tests, three failed or experimental) and [`docs/HANDOFF.md`](docs/HANDOFF.md) (how to restore the work and what to do next).

For continuation or review, read these in order:

1. [`docs/HANDOFF.md`](docs/HANDOFF.md) — current state, owner actions, blockers and commands.
2. [`docs/ROADMAP_STATUS.md`](docs/ROADMAP_STATUS.md) — current milestone status; this supersedes older summary rows in the historical roadmap.
3. [`docs/TRACK_F_BRIEF.md`](docs/TRACK_F_BRIEF.md) — concise AI-agent continuation instructions and guardrails.
4. [`docs/FINDINGS_V4.md`](docs/FINDINGS_V4.md) — evidence and results (sections 34–42; V5 continues in `docs/FINDINGS_V5.md`).
5. [`docs/ROADMAP.md`](docs/ROADMAP.md) — historical roadmap and decision register; retain historical entries.
6. [`CHANGELOG.md`](CHANGELOG.md) and [`docs/WRAP_UP.md`](docs/WRAP_UP.md) — change trail and documentation close-out.

## Current scope and limitations

The validated numerical scope is limited to heavily oiled northern Gulf salt-marsh edge loss (held out by Louisiana basin) and DWH soil PAH-sum decline, within the documented scopes. Other habitats are screening/literature-only or experimental. The process model failed its held-out comparison gate and stays illustrative, outside the decision path. The experimental scenario composer still fails its heavy-cell bias gate after D32 scaling.

F11 historical replay agreed with active versus natural recovery in 2 of 6 cases, compared with 5 of 6 for an always-active baseline. The older legacy replay's 5 of 6 is that same always-active baseline (the legacy model chose an active method in every case), so neither figure shows skill; see `docs/V5_1_VALIDATION.md`. The sample is small and the disagreements need human review. Ten expert-review reports are prepared, but no expert responses have been collected. There is no qualifying second spill for whole-spill validation and no usable public segment-level DWH cleanup-treatment record. Do not claim cross-spill transfer, expert endorsement, operational readiness, or a v4.0 release.

See [`docs/F0_F1_SCOPE_AND_DECISIONS.md`](docs/F0_F1_SCOPE_AND_DECISIONS.md), [`models/registry.json`](models/registry.json), and [`docs/ROADMAP_STATUS.md`](docs/ROADMAP_STATUS.md) for precise scope and status.

## Run the application

Windows launcher:

```text
run_shoreline_dashboard.bat
```

Or in PowerShell:

```powershell
py -3.11 -m pip install -r requirements.txt
py -3.11 -m streamlit run src\shoreline_remediation\dashboard.py
```

From another shell, use the equivalent `python` command. The primary dashboard includes a site-evidence view; treat experimental predictions and screening results according to their displayed scope and evidence labels.

## Tests and analysis dependencies

```bash
python -m pip install -r requirements-analysis.txt
python -m pytest tests
```

The historical full-suite record was 371 passing tests on 15 Nov 2026 with Python 3.11.15 (327 on 14 Nov with Python 3.13 before V5.1).
Current recovery-change acceptance: 107 passing tests across recovery trajectories, recovery view, comparison, V5.4 results and decision board.
The full suite was not rerun for this change. Passing tests are software checks, not model validation.
Some validation checks require local, git-ignored DIVER/SCAT data; consult `docs/DATA_ACQUISITION.md` and the relevant plan first.

## Repository map

- `data/`: input, external, knowledge, schema and demo data; see provenance files and catalogue.
- `docs/`: analysis plans, findings, decisions, roadmap, handoff and protocols.
- `models/`: model cards and registry states.
- `results/`: preserved outputs, including `results/f11_validation/`.
- `scripts/`: acquisition and build helpers.
- `src/shoreline_remediation/`: Python package and Streamlit dashboard.
- `tests/`: focused and integration tests.
- `validation/`: reproducible analysis and validation modules.

## Reproducible work principles

Plan before analysis; define a baseline and gate; hold out whole units; label assumptions and evidence provenance; preserve failed/null results; source numbers from result files; update findings, roadmap status, changelog and handoff together. See [`docs/workflow.md`](docs/workflow.md) and [`docs/TRACK_F_BRIEF.md`](docs/TRACK_F_BRIEF.md).
