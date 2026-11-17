# V5.4 Bay Jimmy recovery view (model and field values): handoff

Updated 17 November 2026: rendering and layout corrections on branch `model_v5_1`, based on `7f46f38` ("Add model-backed Bay Jimmy recovery view"). The original recovery view is already committed; this handoff describes its correction release. Presentation and time-support metadata only: no outcome estimate, interval limit, synthetic formula, model, registry state, evidence verdict, screening status, recommendation, ranking or download was changed. `recovery_view.py` reads the composer, the field tables and the PAH card; `ui_plots.py` only prepares plot records and draws.

## Start here: rendering correction release

The reported poor appearance had two separate causes:

1. **Synthetic demonstration bug.** Curve layers declared 2010-2030, but projection shading, rule and annotation layers used quantitative X encodings without that same scale. The browser merged a zero-origin scale, squeezing all curves into 20/2030 of the width. The concatenated SVG also overflowed its container (about 1096 px in a 937 px desktop container, 478 px in a 315 px mobile container).
2. **Evidence limits and layout.** The evidence-backed view combined ten erosion series with incompatible interval meanings and forced short vegetation/PAH records onto an eight-year axis. Cosmetic offsets moved survey years and the cell-period mean. None of this was a reason to invent smooth curves.

Fixes:
- Every synthetic time-bearing layer explicitly uses domain `[2010, 2030]`, `nice=False`, `zero=False`. `illustrative_recovery_charts()` returns three separate layered charts, not a concatenation. Fit-with-padding sizing includes axes and the one-column legend; the original synthetic values and solid/dotted split at 2018 are unchanged.
- Erosion is split into **Field observations** (default), **Experimental scenarios** and **This cell**. The experimental selector shows one treatment's full uncertainty at a time. Its failed-gate warning remains in that tab. The cell tab keeps deployed and observed values separate from the untreated oiled scenario.
- Each chart zooms to its own evidence dates with small whitespace margins. **Use common year axis (2010 to 2018)** restores the shared `[2010, 2018.5]` domain without extending any series.
- Survey points stay at the exact survey year. All period means, including the cell's 2010-2015 observation, have horizontal time extents and markers at the exact midpoint. Field erosion now stores periods 2010-2012 and 2012-2018, not point dates 2011 and 2015; the values and intervals are identical.
- Circles identify field group means, squares experimental means, diamonds the deployed reference and triangles the observed cell mean. Capped whiskers retain all original limits, including negative erosion values. Tooltips name time endpoints, evidence basis, source and interval type. Legends list only series in the current chart.
- Evidence charts are 340 px tall; synthetic charts are 360 px tall. Percent cover includes the 0-100% range. The existing dark theme and series colours are unchanged.
- Absolute-rate uncertainty is not used as a treatment-difference test. The existing treatment-minus-untreated comparison remains above the recovery section. No interval is narrowed for appearance.

## What the audit found

- **Erosion.** `scenario_composer.compose` gives absolute annual rates (m/yr, positive = land lost) = clean-edge baseline + shared baseline residual draw + oil excess (D32-scaled Zengel 2022, heavy only) + treatment shift (Zengel 2022, change from 2005-2010 against untreated oiled plots). Rates are constant inside two periods (years 1-2 = 2010-2012, years 3-8 = 2012-2018), so they are drawn as steps; the horizon is 2018. Untreated 2.85 then 1.60 m/yr; the published field plot means are 2.96 and 1.67 m/yr. Intervals are 5th-95th percentiles of the joint draws for the absolute rate. The deployed `edge_loss_v1` (1.42 m/yr, 2010-2015, no oiling term) is a separate reference; no contrast is added to it.
- **Vegetation.** The composer's cover is a ratio to reference marsh (0.86 untreated at year 2) from `veg_recovery_v1`. Times the Bay Jimmy reference cover (95%) that is about 81%, against 18% measured on untreated oiled plots, because the curve is a multi-study fit that is worse than a no-trend baseline for heavy oiling. It is therefore **not converted**. Absolute cover comes from Zengel et al. (2015) group means at the 2011 and 2012 surveys.
- **PAH.** The DIVER decline model (`pah_decline_v1`) is a first-order decline of the PAH sum by oiling class (heavy k = 0.430 per year, half-life 1.61 years, 90% interval 1.25 to 2.38) with an unknown station-level intercept, so only a relative index is supported. It has no treatment variable. Zengel et al. (2015) report absolute tPAH (mg/kg) for untreated, manual and mechanical plots; the unit and analyte set differ, so it is a separate chart, never on the same axis.
- **Shared sources.** Zengel 2022 plots calibrate the composer's oil excess and treatment shifts and are also the field erosion points; Zengel 2015 and 2022 share plots. The field points are not independent evaluation of the composer.

## What is displayed

| Outcome | Series displayed | Source and evidence status | Time span and interval | Missing, and the evidence needed |
| --- | --- | --- | --- | --- |
| Erosion rate, m/yr | Untreated baseline, manual removal, mechanical removal, mechanical removal then planting as period steps (scenario); the same four as plot-group means (field); deployed model; observed cell rate | Composer: **Experimental** (R3 and D32 heavy-cell bias gates failed, +0.55 and +0.33 m/yr). Field means: Zengel 2022 GRIIDC, observational. Deployed model: validated reference without an oiling term | Scenario 2010-2012 and 2012-2018, ends 2018. Scenario whisker: 90% simulation interval of the absolute rate. Field: 90% t interval of the group mean. Deployed: 90% one-cell interval | Anything after 2018: a later treated-and-untreated comparison or an erosion model with a treatment term. Validated levels: pass the heavy-cell bias gates |
| Total vegetation cover, % | Untreated baseline, manual removal, mechanical removal (field points) | Zengel 2015 S1 Table group means, observational, 5 to 9 plots | 2011 and 2012 surveys only; 90% t interval of the group mean, lower limit cut at 0 | Planting (source has Spartina cover only, an incremental contrast); absolute cover from a model (needs a vegetation model validated for heavy oiling with a matching reference denominator); surveys after 2012 |
| Soil PAH | tPAH, mg/kg: untreated, manual, mechanical (2012 only), field points. Separate chart: class decline reference as an index (first campaign = 100) | tPAH: Zengel 2015, observational, basis not recorded. Index: `pah_decline_v1`, validated within Deepwater Horizon only, a decline of the sum (physical loss as well as degradation) | tPAH 2011 and 2012, 90% t interval. Index: first to last campaign (2011.3 to 2013.8), 90% interval of the class decline rate, not a station prediction interval | Treatment-specific decline: PAH on treated and untreated plots at three or more times, or a PAH model with a treatment variable. Absolute decline curve: a first-campaign PAH-sum concentration for the class |

Nothing in the evidence-backed charts is drawn after the evidence ends and there are no dotted lines there (no series is a forward projection). The synthetic demonstration remains only in a separate collapsed "Synthetic demonstration curves (not data)" section for Bay Jimmy; its three independently sized panels retain dotted synthetic values after 2018.

## Where it shows

Only a run of an in-scope mapped marsh cell gets the section. Heavily oiled cells get all series. A cell of another oiling class gets the untreated composer scenario and the decline reference, with compact "unavailable" notes for vegetation and tPAH. A typed or generic marsh scenario, rocky shores, mangrove and beaches get no recovery view, so the Bay Jimmy series are not presented as applying to them. Treatment series carry the report's own screening label and a note that mechanical removal and planting are historical treatments, not recommendations.

## Files

Original release: created `src/shoreline_remediation/recovery_view.py`, `tests/test_recovery_view.py` and this file; added drawing in `ui_plots.py` and the section in `ui_results.py`.

Correction release: modified those three source files and the existing recovery tests. Documentation: this handoff, `CHANGELOG.md`, README start-here guidance and current pointers in `HANDOFF.md` and `V5_4_HANDOFF.md`. No new documentation file or dependency is required. Pipeline, registry, models, data, results, comparison layer and report are untouched.

## Verification

- Python 3.11, Streamlit 1.67.0, Altair 6.3.0. Command from the repository root: `python -m pytest tests/test_recovery_view.py tests/test_comparison.py tests/test_v54_results.py tests/test_decision_board.py -q`: **97 passed, 0 failed**. Recovery tests: **20 passed**, including five new checks for consistent nonzero synthetic X scales and standalone fit sizing, true dates and period support, default/common axes, intact scenario uncertainty at period midpoints, and control changes preserving the finding and screening table.
- Four new plotting checks failed before implementation; all pass after it. Pylance syntax checks passed for all three changed source files; signature compatibility passed for the recovery-chart callers. `git diff --check` clean.
- Chromium, Bay Jimmy at **1440x1000 and 390x844**: inspected erosion observations, experimental/manual selection and the cell reference tab; vegetation and PAH records; the fitted PAH index; all three synthetic figures. Synthetic X axes read 2010-2030, not 0-2030. After resize settles, rendered SVG width equals container width (about **937 px desktop, 315 px mobile**), with visible solid and dotted curves and no horizontal page overflow. The common-axis switch was exercised in the browser; it changes dates only. No Streamlit exception in the checked view.
- Imported modules in the long-running local server initially stayed stale after editing; restart Streamlit before browser acceptance checks if the new toggle/tabs do not appear. Browser resize is asynchronous: wait for SVG width to match the container before measuring.
- Existing warnings: openpyxl cannot parse spreadsheet headers/footers; pytest plugin deprecation. These did not fail the tests. Full suite not rerun. Typed/generic marsh and rocky absence are covered by AppTest, not a new browser pass. Light theme, other browsers, screen readers and keyboard-only navigation were not checked. Passing tests and improved presentation do not validate the models.

## Remaining scientific work (not a visual fix)

- Vegetation and treatment-specific tPAH still have only one or two sampled dates. Do not fit splines, add scatter points from group summaries or extend curves to fill the chart.
- A continuous treatment-specific recovery model needs longitudinal treated and untreated observations, a stated temporal mechanism and a pre-specified held-out evaluation against a baseline. No such model was fitted in this correction.
- The heavy-oiling vegetation curve still implies about 81% untreated cover at year 2 against 18% observed; it is not shown as a supported absolute-cover forecast. The PAH decline still has no treatment variable and does not establish biodegradation.
- Composer R3/D32 gates remain failed; field and scenario treatment terms share source plots; most cleanup contrasts are observational. No new spill, independent evaluation or expert review was added.
- With the optional common axis enabled, short records intentionally leave empty space. Points/whiskers can still overlap where the estimates themselves are close; their dates and uncertainty are not displaced to hide that.
