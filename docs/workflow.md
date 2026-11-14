# Project workflow and validation guardrails

This file records the current working principles. For current phase status, begin with `docs/ROADMAP_STATUS.md`; for the next AI session, read `docs/TRACK_F_BRIEF.md` and `docs/HANDOFF.md`. The historical Track F design is in `docs/V4_PROGRAMME_PLAN.md`.

## Evidence-first workflow

1. **Define before analysis.** Record the question, input data, method, baseline, validation unit, pass/fail gate and interpretation in a plan before inspecting results.
2. **Preserve the comparison.** Compare against a simple baseline. Hold out whole spills, basins, stations or studies as the question requires—not random rows. Keep original results and label later reruns.
3. **Track provenance.** Distinguish measured, sourced, AI-extracted, human-elicited, AI-proposed, assumed and unavailable information. Do not describe AI-generated content as human expert evidence.
4. **Report what happened.** Put results in the appropriate `results/` folder; report nulls, failed gates, uncertainty and deviations. Every number in documentation should trace to an artifact and its method.
5. **Keep status synchronized.** Update findings, `docs/ROADMAP_STATUS.md`, the historical decision register as needed, `CHANGELOG.md`, and `docs/HANDOFF.md`. Rebuild catalogue/dictionary and run focused tests when data or schema changes.
6. **Keep claims inside evidence.** Consult `models/registry.json` and `docs/F0_F1_SCOPE_AND_DECISIONS.md`. Experimental predictions and screening rules are not validated treatment-effect predictions.
7. **Respect ownership.** Record pending Jaison review as pending; do not infer approval. Commit or push only when explicitly authorized.

## Current important limitations

- The process model failed its held-out gate and remains illustrative, outside the decision path.
- The scenario composer’s heavy-cell bias gate remains failed; its coverage result does not promote it.
- F11 historical replay agreement is 2/6, below the 5/6 always-active baseline. Six cases are too few for a broad performance claim; preserve the disagreements for review.
- There are no collected expert-panel responses, no usable public segment-level DWH treatment records, and no qualifying second spill for whole-spill validation.
- Do not claim cross-spill transfer, operational readiness, expert endorsement, or F12 release.

## Reproduction starting point

From the repository root, install the analysis dependencies and run the test suite:

```bash
python -m pip install -r requirements-analysis.txt
python -m pytest tests
```

For data-dependent checks, first consult their plan and `docs/DATA_ACQUISITION.md`; DIVER/SCAT raw data may be local and git-ignored. Record the exact command, environment, outputs and limitations. The historical workflow below is superseded; retain its expert-scoring template and files as artifacts, but do not use synthetic labels as human judgments.
