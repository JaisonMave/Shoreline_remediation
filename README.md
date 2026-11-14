# Shoreline Remediation Decision Support

An evidence-led prototype for screening oil-spill shoreline response options. It combines SCAT/shoreline inputs, feasibility rules, field and literature evidence, and scoped prediction components. It is a research prototype—not an operational response recommendation system.

## Start here

For continuation or review, read these in order:

1. [`docs/HANDOFF.md`](docs/HANDOFF.md) — current state, owner actions, blockers and commands.
2. [`docs/ROADMAP_STATUS.md`](docs/ROADMAP_STATUS.md) — current milestone status; this supersedes older summary rows in the historical roadmap.
3. [`docs/TRACK_F_BRIEF.md`](docs/TRACK_F_BRIEF.md) — concise AI-agent continuation instructions and guardrails.
4. [`docs/FINDINGS_V4.md`](docs/FINDINGS_V4.md) — evidence and results (sections 34–42 are latest).
5. [`docs/ROADMAP.md`](docs/ROADMAP.md) — historical roadmap and decision register; retain historical entries.
6. [`CHANGELOG.md`](CHANGELOG.md) and [`docs/WRAP_UP.md`](docs/WRAP_UP.md) — change trail and documentation close-out.

## Current scope and limitations

The validated numerical scope is limited to heavily oiled northern Gulf salt-marsh edge loss (held out by Louisiana basin) and DWH soil PAH-sum decline, within the documented scopes. Other habitats are screening/literature-only or experimental. The process model failed its held-out comparison gate and stays illustrative, outside the decision path. The experimental scenario composer still fails its heavy-cell bias gate after D32 scaling.

F11 historical replay agreed with active versus natural recovery in 2 of 6 cases, compared with 5 of 6 for an always-active baseline. The sample is small and the disagreements need human review. Ten expert-review reports are prepared, but no expert responses have been collected. There is no qualifying second spill for whole-spill validation and no usable public segment-level DWH cleanup-treatment record. Do not claim cross-spill transfer, expert endorsement, operational readiness, or a v4.0 release.

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

The prior handoff records 177 tests passing on Python 3.11; the latest documentation-only work did not rerun them. Confirm locally before reporting a current pass. Some validation checks require local, git-ignored DIVER/SCAT data; consult `docs/DATA_ACQUISITION.md` and the relevant plan first.

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
