# Track F brief for AI agents (current checkpoint: 14 November 2026)

**Read this file first when continuing Track F.** This is the machine-readable continuation note for the next AI session. It supersedes the older environment-specific and “do not edit handoff/roadmap” restrictions in prior copies of this brief. Current status: `docs/ROADMAP_STATUS.md`; human/owner handoff: `docs/HANDOFF.md`; full history and decision register: `docs/ROADMAP.md`; results: `docs/FINDINGS_V4.md` sections 34–42.

## Repository and current checkpoint

- Repository: `JaisonMave/Shoreline_remediation`
- Branch: `process-model-audit`
- Latest code/results checkpoint: `3f6b74a` (F11 integrated validation).
- Documentation wrap-up commit: `066d445` (handoff and roadmap status).
- Python 3.11 was the recorded test environment. Previous handoff says 177 tests passed; the documentation wrap-up did not rerun tests. Verify locally before making any new pass claim.
- DIVER/SCAT inputs may be local and git-ignored; never assume they exist in a clean checkout. Do not commit restricted data or credentials.

## Immediate continuation objective

Do not start a speculative new model. Continue from the actual blockers and owner gates:

1. Review `docs/ROADMAP_STATUS.md` and `docs/HANDOFF.md` before choosing work.
2. The next owner-facing work is Jaison’s review of parked P1–P5 findings, variables, dashboard, decisions, and the F11 disagreements. Do not mark accepted without his response.
3. Human expert review has not happened. Use `docs/F11_EXPERT_REVIEW_PACK.md` to collect genuine responses; never invent or imply reviewer input.
4. F6 needs treatment-segment data; digitising OR&R 42 maps is an optional, uncompleted task requiring a plan and owner check. F7 lacks a qualifying second spill. Do not claim cross-spill validation.
5. F12 is not released. Release requires owner sign-off, final checks, current model cards/docs, and an explicit release decision.
6. If owner feedback or data are unavailable, make a small, clearly-labelled documentation/status improvement or stop with a precise handoff. Do not substitute guessed work for missing evidence.

## Scientific guardrails

- Keep validated, experimental, rules/literature-only, and out-of-scope claims separate as defined in `docs/F0_F1_SCOPE_AND_DECISIONS.md` and `models/registry.json`.
- The F5 process model failed its held-out gate (0.775 versus empirical 0.750) and stays illustrative/out of the decision path.
- The scenario composer’s heavy-cell bias gate still fails after D32; coverage alone does not promote it.
- F11 historical active/natural agreement is 2/6 versus 5/6 for the always-active baseline. Report this unfavorable result and its small sample; do not tune the pipeline to this replay.
- AI-extracted literature is not equivalent to independent expert review. AI-PROPOSED knowledge rows are not human-elicited.
- Plan before analysis; specify question, data, method, baseline, gates and interpretation. Preserve original runs; label any rerun. Hold out whole units where appropriate. Source every reported number in committed result artifacts.

## Documentation protocol for each substantive phase

After a phase, update only relevant docs and evidence artifacts, keeping the trail aligned:

1. The phase plan/status and any deviations.
2. `docs/FINDINGS_V4.md` with findings tied to result paths; record nulls and failed gates.
3. `docs/ROADMAP_STATUS.md` and, when decisions/status history change, `docs/ROADMAP.md`.
4. `docs/HANDOFF.md` with checkpoint, exact next actions, owner gates and reproducible commands.
5. `CHANGELOG.md` with why, files, rerun command, result and status.
6. Catalogue/dictionary and tests if tracked data/schema changed.

Do not create a commit or push unless Jaison asks for it. If authorized, commit to the named branch, report the exact SHA, list changed paths, and state tests actually run (or not run). Keep changes scoped; do not edit scientific numbers without rerunning the pre-specified analysis.

## Useful entry points

- `docs/ROADMAP_STATUS.md` — current phase status and close-out sequence.
- `docs/HANDOFF.md` — current state and human owner actions.
- `docs/V4_PROGRAMME_PLAN.md` — original Track R/F design and process model.
- `docs/F0_F1_SCOPE_AND_DECISIONS.md` — scope and decision principles.
- `docs/FINDINGS_V4.md` — evidence and result references.
- `docs/REVIEW_NOTES.md` — unresolved scientific/technical concerns.
- `docs/F11_EXPERT_REVIEW_PACK.md` — review form and reports.
- `docs/WRAP_UP.md` — documentation close-out record.

## Environment-neutral commands

Run from the repository root; adapt executable paths to the environment:

```bash
python -m pip install -r requirements-analysis.txt
python -m pytest tests
streamlit run src/shoreline_remediation/dashboard.py
python -m validation.f11_integrated_validation
```

Some validation modules require local raw data. Check the relevant plan and acquisition notes first.
