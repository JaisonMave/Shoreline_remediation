# Bay Jimmy dashboard integration review

Use this plan from the repository root on `codex/scenario-prediction-plan`. The offline engine is committed at `d458d15`. The Assessment integration is in the working tree, including the new `src/shoreline_remediation/ui_future_scenarios.py`. Include untracked implementation files in the review. Preserve the existing navigation, theme, assessment report and decision pathway.

## One review pass

1. Read the Assessment integration entry in `docs/PROJECTION_HANDOFF.md`. Trace the selected assessment record from `ui_results.render_results` through the new panel to the shared projection function. Verify that only the in-scope, heavily oiled Bay Jimmy worked example exposes the controls. Try switching to a typed marsh, another mapped cell and rocky or mangrove shore after using the explorer.
2. Trace a fixed-rate scenario and a two-rate scenario from controls to chart and downloads. Check the field-plot anchor, date convention, change-date bounds, conditional labels and replayability of the downloaded JSON. Verify that the user can clear or shorten dates, turn the rate change off, and reopen the panel without an exception or a stale curve. Check the online/offline results at shared dates. The assessment outcome and existing report should remain invariant under edits to a research scenario.
3. Check claims against the protocol. Retain the distinction between the example rate of 1.43 m/year and B1, the historical comparison baseline. Short horizons still represent conditional assumptions. Mark observations and extrapolation clearly. Give a useful message when required input or evidence is unavailable.
4. Record findings once with a reproducible input, observed result, expected result and affected code. Prioritize incorrect results, cross-site leakage, broken controls, misleading claims and export discrepancies. Fix each confirmed defect with a focused change and regression coverage. Verification of a fix is part of this pass.

## Acceptance

| Case | Expected result |
| --- | --- |
| 1 Jan 2030, 1.43 m/year | Additional retreat 18.93 m and cumulative retreat 31.06 m. |
| Zero rate | Additional retreat 0.00 m; cumulative retreat stays at the observed 12.13 m anchor (rounded). |
| 1 Jan 2050, 1.43 then 2.19 m/year from 1 Jan 2030 | Cumulative retreat 74.86 m; continuous at the rate change. |
| Shorten the end date across a previously selected rate change | Controls remain usable, with an explicitly valid date or a corrective message. |
| Unmatched site or unsupported habitat | Existing assessment is available; Bay Jimmy plot controls are absent. |
| Download both files | Input JSON replays through the CLI in a fresh directory. CSV dates, rates, anchor and endpoint agree with the displayed scenario. |

Run the dashboard regression command from the handoff and any new targeted tests:

```powershell
python -m pytest -q tests/test_v54_results.py tests/test_projections.py tests/test_projections_rate.py tests/test_recovery_trajectories.py
```

Open Home → Use Bay Jimmy → Run assessment → Explore future scenarios in a running dashboard. Verify the changed interaction, download and one narrow viewport. Record exact commands, results, any checks skipped and remaining limitations in the handoff. Keep existing reference captures intact. Leave all changes local and uncommitted.

## Claude Code prompt

> Follow docs/CLAUDE_ASSESSMENT_REVIEW.md on the current branch. Review the working-tree integration once, including the untracked view module. Reproduce and fix confirmed findings, add targeted regression tests and verify the affected user journey. Preserve my other changes and report what was actually exercised.
