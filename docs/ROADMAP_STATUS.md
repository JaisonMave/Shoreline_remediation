# Roadmap status snapshot (14 November 2026)

This is the current status view for the `process-model-audit` branch at the F11 checkpoint. It supersedes older summary rows in `docs/ROADMAP.md` that say Track F is not started. The detailed milestone history and decision register D1–D32 remain in `docs/ROADMAP.md`; evidence and numbers are in `docs/FINDINGS_V4.md` sections 34–42. “Implemented” does not mean “validated,” “human-reviewed,” or “released.”

## Track F

| Item | Current status | Evidence / remaining gate |
| --- | --- | --- |
| F0 Scope (D30) | Documented | Validated, experimental, rules/literature-only and out-of-scope tiers in `docs/F0_F1_SCOPE_AND_DECISIONS.md`. Keep claims within those tiers. |
| F1 Decisions (D14–D21, D30–D31) | Implemented/documented; owner review remains | Decisions and evidence are recorded; parked P1–P5, variable-definition and dashboard reviews remain Jaison’s. D23–D24 remain Proposed / AI-PROPOSED. |
| F2 Knowledge tables | Implemented; equivalence check passed | 0 differences across approximately 432,000 verdicts and the blind scenarios; row provenance/status retained. |
| F3 Interface and registry | Implemented; promotion limits apply | Five adapters registered. Edge-loss v1 and PAH decline v1 are validated in their stated scope; composer, vegetation, mangrove and process components remain experimental or gated. |
| F4 Common schema | Implemented; reconciliation passed | 38/38 checks. Galeta raw data was not loaded; local DIVER schema data is not necessarily in a fresh clone. |
| F5 Process model | Gate failed; illustrative only | Calibrated held-out error 0.775 versus empirical 0.750. It must not enter the decision path. |
| F6 Treatment records | Awaiting usable data / owner action | No public machine-readable segment-level DWH treatment records found. OR&R 42 map digitisation is a possible, uncompleted next step. |
| F7 Second spill | Awaiting data | No qualifying spill found for whole-spill hold-out; no cross-spill transfer claim. Partial candidates are inventoried. |
| F8 Literature pooling | Completed with limited conclusions | No group met the pre-specified minimum for pooling; single-study verdicts only. Hot-water washing harm on rocky and gravel/sand shores is documented. Retain extraction provenance. |
| F9 Decision pipeline | Implemented; conservative behavior documented | Fixed, logged pipeline and worked examples exist. Recommendation classes are not a claim of operational effectiveness; see F11 disagreements. |
| F10 Adaptive monitoring | Within-period check passes; temporal update fails | 25% cell monitoring improves within-period error/interval width (coverage 88%); update to a later period narrows intervals but does not improve error. |
| F11 Integrated validation | Run and documented; review/sign-off outstanding | Six sourced cases: active/natural agreement 2/6 versus 5/6 always-active; 264/400 draw-method checks allowed. Ten reports prepared, no reviewer responses collected. |
| F12 Release v4.0 | Not released | Requires Jaison’s review/sign-off, independent review as feasible, final test run, release documentation, and explicit release decision. |

## Other open work and claim boundaries

- P1–P5 and dashboard/variable reviews remain with Jaison; do not silently relabel them as accepted.
- D23/D24 and AI-proposed knowledge-table entries are not human expert elicitation.
- Heavy-cell composer bias remains outside its gate after D32. Coverage alone does not make the composer validated.
- Only one spill supplies the main evidence base. Louisiana basin hold-out is within-spill generalisation, not independent-spill validation.
- Soil-map layers are not suitable substitutes for marsh measurements in this analysis; see D21 and FINDINGS 13.
- Costs, other contaminants, offshore response, and broad ecosystem generalisation are out of scope.

## Close-out sequence

1. Jaison reviews the parked work and the F11 disagreement cases.
2. Obtain and preserve genuine expert feedback; if unavailable, state that explicitly.
3. Resolve data and bias gates only through a pre-specified plan and new evidence—do not weaken gates post hoc.
4. Run `python -m pytest tests` and required reproduction checks in the target environment; record outputs and limitations.
5. Update the release notes/model cards and make a release only after explicit owner sign-off.

No new scientific analysis or test run is asserted by this status snapshot. See `docs/HANDOFF.md` for the working handoff.
