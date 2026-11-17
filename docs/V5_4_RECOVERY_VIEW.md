# V5.4 Bay Jimmy recovery view (model and field values): handoff

Current UI continuation, 17 November 2026: only **Continuous trajectories: experimental fits and conditional scenarios** remains in the
Assessment recovery area. The older **Recovery view: erosion, vegetation and soil PAH** and **Synthetic demonstration curves (not data)**
sections, including their controls and charts, are no longer rendered. Their data and chart helpers remain for reproducibility; no source
data, model, fitted value, scope gate, decision or report was changed. The historical layout descriptions below remain a record of earlier releases.

### Why not extend the current curves to 2030 or beyond?

There is no plotting or mathematical barrier. The current endpoints deliberately follow source support: shoreline and vegetation
surveys end in 2016, and the borrowed PAH decline rate has campaign support only to about 2013.78. Manual cover has observations only
in 2011-2012 and already borrows the untreated rate for its conditional scenario.

Extending to 2030 would assume that the shoreline's fitted long-run rate, the vegetation ceiling and rate, and the borrowed PAH rate
continue unchanged for many unobserved years. The logistic form already misses the 2016 cover decline. Changing marsh geometry,
storms, sea-level rise, PAH background or slow pools, and later management are not represented. Bootstrap/Monte Carlo bands quantify
only the stated parameter uncertainty and would not become credible long-range prediction intervals by extending the x grid.

A future 2030+ scenario mode is technically possible, but must visibly separate extrapolation from fitted support, state its assumptions,
and include or explicitly exclude long-horizon structural/environmental uncertainty. It must not be labelled a validated forecast.
This UI simplification does not add extrapolation or change any time support.

Verification for the UI simplification: the five-file recovery/comparison/results/decision-board command below gives **107 passed**.
One obsolete recovery-axis/scenario-control test was removed because those controls no longer exist; the remaining AppTests check that
the legacy sections are absent, all three trajectory charts and four tabs remain, and generic/rocky runs still receive no Bay Jimmy curves.

Updated 17 November 2026 (second release): continuous experimental trajectories added in a separate collapsed section, and the vegetation and tPAH survey points moved to their verified sampling months (values unchanged). See **Continuous trajectories (experimental)** below. Everything else in this file describes the earlier correction release.

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
| Total vegetation cover, % | Untreated baseline, manual removal, mechanical removal (field points) | Zengel 2015 S1 Table group means, observational, 5 to 9 plots | September 2011 and September 2012 surveys only (plotted at 2011.70 and 2012.70); 90% t interval of the group mean, lower limit cut at 0 | Planting (source has Spartina cover only, an incremental contrast); absolute cover from a model (needs a vegetation model validated for heavy oiling with a matching reference denominator); surveys after 2012 |
| Soil PAH | tPAH, mg/kg: untreated, manual, mechanical (2012 only), field points. Separate chart: class decline reference as an index (first campaign = 100) | tPAH: Zengel 2015, observational, basis not recorded. Index: `pah_decline_v1`, validated within Deepwater Horizon only, a decline of the sum (physical loss as well as degradation) | tPAH cores July-August 2011 and September 2012 (plotted at 2011.58 and 2012.70), 90% t interval. Index: first to last campaign (2011.3 to 2013.8), 90% interval of the class decline rate, not a station prediction interval | Treatment-specific decline: PAH on treated and untreated plots at three or more times, or a PAH model with a treatment variable. Absolute decline curve: a first-campaign PAH-sum concentration for the class |

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

- Treatment-specific tPAH still has only one or two sampled dates, and manual-plot vegetation two. Do not fit splines, add scatter points from group summaries or extend curves to fill the chart.
- The continuous trajectories below are simple fits to one site's plots with plot-level hold-out checks against simpler forms. They are not validated forecasts: no independent site, no pre-registered evaluation and no treatment-specific PAH or post-2012 manual-plot data.
- The older multi-study `veg_recovery_v1` curve still implies about 81% untreated cover at year 2 against 18% observed; it is not used by the new plot-level fits or shown as a supported absolute-cover forecast. The PAH decline still has no treatment variable and does not establish biodegradation.
- Composer R3/D32 gates remain failed; field and scenario treatment terms share source plots; most cleanup contrasts are observational. No new spill, independent evaluation or expert review was added.
- With the optional common axis enabled, short records intentionally leave empty space. Points/whiskers can still overlap where the estimates themselves are close; their dates and uncertainty are not displaced to hide that.

## Continuous trajectories (experimental)

Module `src/shoreline_remediation/recovery_trajectories.py` (data and fitting; no Streamlit). Drawing: `ui_plots.trajectory_records` and `ui_plots.trajectory_chart`. Section: `ui_results._trajectory_section`, a collapsed expander **"Continuous trajectories: experimental fits and conditional scenarios"** placed directly after the recovery view. Nothing in the decision pipeline, comparison layer, screening statuses, registry, report or recovery view imports the module (a test checks imports in `decision_pipeline.py`, `comparison.py` and `recovery_view.py`). It is a research presentation, not an evidence input.

Gate: same as the recovery view (in-scope mapped marsh cell, report present). Curves are fitted to the heavily oiled Bay Jimmy plots only. A cell of another oiling class gets a one-line "unavailable" note and no curves, because these plots are not evidence for other classes.

### Curve roles

- **Fit** (solid line): a model fitted to the group's own plot-level longitudinal data and drawn only between its first and last survey.
- **Conditional scenario** (dashed line): the group's own data cannot identify a rate, so a rate is borrowed from another group or from an external model. The label, the legend and the parameter table say so.
- **Observed** (circles and whiskers): group means of the same plot data with 90% t intervals at the exact survey dates. They are separate records from the curves.

No value in this section is a fixed literature prior. Every parameter is estimated from repository data or is the existing `pah_decline_v1` coefficient.

### Data (all already in the repository)

| Quantity | File and sheet | Source | What it is |
| --- | --- | --- | --- |
| Marsh-edge position | `data/external/zengel2022/zengel2022_griidc_erosion.xlsx`, sheets "GIS field erosion points" (positions) and "GIS field erosion" (plot types) | Zengel et al. 2022, Sci. Rep. 12:13802 (PMC9376092); GRIIDC doi:10.7266/VF524143, CC0 | Distance from a back stake to the marsh edge on two transects per plot, tape and DGPS (about 10 cm, per the paper's Methods), dated surveys 4 Dec 2010 to 5 Oct 2016 |
| Total vegetation cover | `data/external/zengel2022_meta/dataset_compiled_for_GRIIDC.xlsx`, sheet "Dataset", rows with Source = "Zengel (B)"; plot types from the "DSAS lumped" sheet above | GRIIDC doi:10.7266/n7-cn03-z792 (compiled dataset of the Zengel et al. 2022 Ecol. Appl. meta-analysis) | Plot-year total cover (%), 2011 to 2016. The 2011 and 2012 plot means reproduce the Zengel et al. 2015 S1 Table group means (tested to within 0.6 percentage points, same plot counts) |
| Soil tPAH | `data/external/zengel2015/zengel2015_group_means.csv` via `treatment_effects.load()` | Zengel et al. 2015, PLoS ONE 10:e0132324 (PMC4511762), S1 Table | Group means, SE and n, 2011 and 2012 (mechanical 2012 only) |
| PAH decline rate | `results/pah_decline/by_oiling_class.csv`, PAH sum, heavy class | `pah_decline_v1` (DIVER) | k = 0.430 per year, 90% interval 0.291 to 0.556, 36 stations with two or more campaigns |

Plots: untreated 3, 8, 12, 13, 15, 16, 18, 19, 23; manual 11, 17, 20, 21, 22; reference 24 to 28; mechanical 1-2, 7-8, 8-9, 9-10, 16-17, 17-18, 19-20, 20-21, 22-23.

Dates verified in the full text of Zengel et al. 2015 (Europe PMC XML): vegetation sampled "primarily in September 2011 and 2012"; subsurface cores (0-10 cm, surface oil scraped aside) "July-August 2011 and September 2012"; manual treatment December 2010; mechanical treatment May-June 2011. Decimal years: mid-September = .70, midpoint of July-August = .58. The months of the 2013-2016 vegetation surveys are not recorded in the sources examined; September is **assumed**. The evidence-backed recovery view now uses the same verified dates (`recovery_view.VEG_SURVEY_X`, `PAH_SURVEY_X`; previously points sat at 2011.0 and 2012.0). Only the x positions changed.

### Shoreline retreat (m)

Quantity: cumulative landward movement of the marsh edge since 4 December 2010 (the first survey with every untreated, manual and reference transect). Per plot, the increment is the mean over its two transects of (first distance minus current distance); repeated readings of one transect on one date are averaged. The partial 9 October 2010 survey is excluded so that all groups share one origin. Retreat before December 2010 (oiling began mid-2010) is not in the curves.

Cumulative retreat is the time integral of the erosion rate, so the slope of a curve is the rate. The two published period means (2010-2012, 2012-2018) in the recovery view are integrals over periods. The field positions used here are dated instantaneous positions, so no period mean is treated as instantaneous.

Models, fitted by bounded least squares to plot increments, using R(t) minus R(t0) where t0 is the plot's first survey:

- M0: R(t) = b t (constant rate, the form of a DSAS linear-regression rate).
- M1: R(t) = b t + A (1 - exp(-t / tau)). The rate is b + (A / tau) exp(-t / tau): an excess over a long-run rate that fades. Bounds: b in [-10, 10] m/yr, A in [-20, 20] m, tau in [0.05, 10] yr.

Selection rule, fixed before the fits were inspected: use M1 only if its leave-one-plot-out RMSE is lower than M0's.

| Group (plots) | Chosen | Estimates (90% plot-bootstrap interval) | Held-out RMSE, M0 vs M1 (m) |
| --- | --- | --- | --- |
| Untreated (9) | M1 | b 1.43 m/yr (0.59 to 1.75); A 3.4 m (2.2 to 10.3); tau 1.2 yr (0.6 to 3.6) | 1.99 vs 1.82 |
| Manual removal (5) | M1 | b 1.20 m/yr (0.15 to 1.43); A 4.4 m (2.7 to 16.4); tau 1.6 yr (0.6 to 5.4) | 2.31 vs 2.15 |
| Reference (5) | M0 | b 1.25 m/yr (0.98 to 1.49); M1 was degenerate (tau at its bound) | 1.53 vs 1.54 |

Observed group means of cumulative retreat (m) at 13 Nov 2011, 17 Sep 2012, Sep 2013, Sep 2014, Sep 2015 and 5 Oct 2016: untreated 2.77, 5.63, 7.22, 8.59, 9.77, 12.13; manual 2.84, 5.40, 7.02, 8.53, 9.77, 11.44; reference 0.88, 2.09, 3.34, 4.59, 5.88, 7.69. Curve ends (5 Oct 2016, 90% band): untreated 11.8 (10.5 to 12.9), manual 11.3 (9.2 to 13.2), reference 7.3 (5.7 to 8.7).

Consistency checks, not fits:

- Retreat to September 2012 was untreated 5.6 m and reference 2.1 m. That is about 170% greater, inside the range reported by Zengel et al. 2022 (147 to 198% greater field erosion on oiled than reference plots over 2010-2012).
- The M1 long-run rate for untreated plots (1.43 m/yr) and the reference rate (1.25 m/yr) are of the same order as the pre-spill aerial (DSAS) rates for these plots (about 1.2 to 1.3 m/yr, 1956-2004). That is a different method and period and is mentioned only as context.

Not drawn:

- **Mechanical removal.** 2 plots were first surveyed on 13 Nov 2011 (after treatment) and 4 more only from 2014. There is no December 2010 origin and too few plots for a plot-resampling band. The aerial period rates remain in the recovery view.
- **Planting.** The source has no field GPS positions for planted plots.
- The aerial "DSAS annual" sheet is not used, because the image dates for its periods were not confirmed (the image table is in a supplement that was not obtained).

The date of the largest excess erosion is **not identified**. In M1 the excess is largest at the first survey by construction. No peak is drawn.

### Total vegetation cover (%)

C(t) = K / (1 + exp(-r (t - t50))), with K the mean total cover of reference plots 24 to 28 over 2011 to 2016 (plot-year mean 93.6%). This keeps the curve between 0 and K, so it is always inside 0 to 100%. It is total cover of all species, not Spartina cover. Fitted to plot-year values by bounded least squares (r in [0.05, 10] per year, t50 in [2009, 2025]).

| Series | Role | Estimates (90% interval) | Held-out RMSE, logistic vs no-trend mean (cover %) | Mean residual by year, fit minus observed |
| --- | --- | --- | --- | --- |
| Untreated (9 plots 2011-2012, 5 followed to 2016) | Fit | r 1.20 per yr (0.88 to 2.14); t50 2013.8 (2013.3 to 2014.4) | 20.8 vs 36.4 | 2011 +0.7, 2012 +2.1, 2013 -3.7, 2014 +0.9, 2015 -6.8, **2016 +20.9** |
| Mechanical (5 plots in 2011-2012, one followed to 2016; 4 more from 2013) | Fit | r 0.97 per yr (0.77 to 1.38); t50 2014.0 (2013.6 to 2014.5) | 19.1 vs 35.1 | 2011 +7.8, 2012 -2.4, 2013 -3.6, 2014 +5.5, 2015 -10.9, **2016 +13.9** |
| Manual (5 plots, 2011 and 2012 only) | **Conditional** | r shared from the untreated fit; t50 2012.6 (2012.3 to 2012.9) estimated given that r | 13.5 vs 20.0 (2 dates; t50 only) | 2011 +2.3, 2012 -1.8 |

K = 93.6% (90.1 to 96.2). Reference yearly means were 95.6, 95.0, 97.2, 99.0 and 96.6, then 78.2 in 2016. The 2016 drop occurs on the reference plots as well and a monotone curve cannot follow it. With manual plots surveyed on only two dates, a free (r, t50) fit would pass exactly through the two means, so the rate is not identified. The manual curve is therefore drawn dashed to 2016.7, labelled "shared untreated rate", and its summary reads "IF the manual plots followed the untreated recovery rate after 2012". Planting: not drawn (the sources give Spartina cover only, July 2012, not plot-level total cover).

This replaces nothing in the evidence view. The multi-study `veg_recovery_v1` curve, which implies about 81% untreated cover at year 2 against 18% observed, is still **not** used.

### Soil tPAH (mg/kg): conditional only

C(t) = C_a exp(-k (t - t_a)). C_a is the group's first-survey mean (S1 Table) at t_a (2011.58, or 2012.70 for mechanical). k is the `pah_decline_v1` heavy-class rate. Each curve stops at the end of the DIVER campaigns that support k (2013.78 = `SPILL_YEAR` + the heavy-class support end of `recovery_view._pah_support`).

Every PAH curve is **conditional**. The plots have one or two samples, so no plot-specific rate is identified, and k has no treatment variable. The mismatches are stated in the panel note:

- DIVER PAH sum is mostly 0-2 cm grabs and 58 compounds; plot tPAH is 0-10 cm cores and 43 to 45 compounds.
- k describes the decline of the sum, which includes physical removal and dilution. The PAH/hopane ratio did not decline (heavy-class k for the ratio about 0.018 per year), so k is not evidence of biodegradation.

Band: Monte Carlo with 4000 draws. C_a is lognormal with matched mean and SE. k is normal with sd = (hi90 - lo90) / (2 x 1.645).

| Series | Start (mg/kg) | End at 2013.78 (90% band) |
| --- | --- | --- |
| Untreated | 260 (2011.58) | 101 (48 to 186) |
| Manual | 220 (2011.58) | 86 (51 to 134) |
| Mechanical | 178 (2012.70) | 112 (39 to 244) |

Weak checks (the 2012 values were not used in the fit): untreated 2012 observed 112 mg/kg against a scenario range of 79 to 288; manual 101 against 88 to 198. Both fall inside the range, which says little with these intervals. Not drawn: planting (no tPAH), and any treatment-specific rate (needs PAH on treated and untreated plots at three or more dates, or a PAH model with a treatment variable).

### Uncertainty: what the bands are and what they exclude

- Retreat and vegetation bands are 5th to 95th percentiles of the group-mean curve over 400 plot-level cluster bootstrap refits (whole plots resampled with replacement; seed 20261117). The vegetation bootstrap also resamples the reference plots that set K. The model form is fixed within the bootstrap. Refits that do not converge are counted in the diagnostics table (0 in the current data); none is silently dropped. The PAH band is the Monte Carlo described above.
- The bands **exclude**:
  - the choice of model form (structural uncertainty);
  - weather and between-year variation (for example the 2016 decline shared with the reference plots);
  - measurement error (GPS and staking error, visual cover estimates);
  - the spread of individual plots (the bands are not prediction intervals for a single plot or a new site);
  - for conditional curves, any difference between the borrowed rate and the group's true rate.
- With two dates, a band cannot show that kinetics were identified, and the manual and PAH curves are not presented as identified.

### Exclusions and limits

- One site (Bay Jimmy, heavily oiled Spartina/Juncus marsh, Deepwater Horizon) and 5 to 9 plots per group. No independent site and no pre-registered evaluation, so nothing is a validated forecast. Nothing is drawn after 5 October 2016 (retreat), September 2016 (vegetation) or the DIVER support end (PAH).
- Group composition changes over time:
  - vegetation: untreated 9 then 5 plots; mechanical 5 plots, then 1 continued plus 4 new;
  - retreat: mechanical plots not fitted.
  The fits treat each group as one population.
- Treatment effect is not estimated. Overlapping or separated curves are not a test of treatment differences. Contrasts remain in the comparison layer, which is unchanged.
- The source plots overlap with the Zengel 2022 data that calibrate the composer's treatment terms. Curves and composer are therefore not independent.
- The retreat curves describe the plots' marsh edge. They are not the cell's `edge_loss_v1` rate, and the cell's observed rate is not used.

### UI controls to inspect

Run Bay Jimmy (Map > "Use Bay Jimmy (worked example)" > Run assessment), then open **Continuous trajectories: experimental fits and conditional scenarios** under the recovery view.

- The tabs are **Shoreline retreat**, **Vegetation cover**, **Soil tPAH** and **Parameters and sources**. The last tab has the parameter table (value, 90% interval, unit, type, source) and the diagnostics table (model chosen, held-out RMSE against a simpler form, residuals by year, refit counts).
- Each chart has:
  - one legend chip per series ("observed and fit", "observed; dashed conditional scenario");
  - a marks caption, curve summaries, the panel note, checks, and "Not drawn" items with the evidence needed.
- Tooltips give the equation and band type for curves, and the plot count, survey dates and source for observed means.
- Charts are single layered Altair charts, 340 px tall, with autosize fit. They have no vconcat. Every layer has explicit x and y domains with `zero=False` and `nice=False`.
- Browser check on a temporary server (Chromium 1440 wide and 390 wide): the three charts render, with no horizontal page overflow at 390 px. The first build in a server process takes several seconds (400 bootstrap refits per group with analytic Jacobians) and is then cached for the process (`functools.lru_cache`).

### Tests

`tests/test_recovery_trajectories.py` (10 tests):

- source reproduction of the S1 group means and plot counts;
- retreat origin, monotonicity, band containment, span and model choice;
- held-out selection and tau not at a bound;
- vegetation bounds and the manual curve's conditional role with the shared rate;
- PAH conditional role, nonnegativity, exponential form and end at the support end;
- other classes and out-of-scope cells;
- parameter types and formatting;
- chart scales, no vconcat, dashes only for conditional curves;
- decision modules do not import the module;
- an AppTest that checks the collapsed expander, its four tabs and three charts, with the recovery view (6 charts) and options table intact.

`tests/test_recovery_view.py`: date assertions updated to 2011.70/2012.70 (vegetation) and 2012.70 (mechanical PAH), and the zoomed vegetation domain to [2011.35, 2013.05]. The minimum time padding of the evidence charts was raised from 0.2 to 0.35 years so that a one-year record keeps two year ticks.

Command: `python -m pytest tests/test_recovery_trajectories.py tests/test_recovery_view.py tests/test_comparison.py tests/test_v54_results.py tests/test_decision_board.py -q` gives **107 passed** (97 before plus 10 new). The full suite was not rerun.

Integration acceptance adds an explicit nonconvergence regression: the initial untreated/mechanical vegetation fits are checked before
the manual scenario borrows a rate. A failed optimizer now raises the intended `RuntimeError` rather than indexing `None`.
The same five-file command gives **108 passed** with this additional test. These remain software checks, not new scientific validation.

Independent release-browser acceptance on the restarted localhost dashboard: Chromium at 1440x1000 and 390x844, all three trajectory tabs
render continuous lines with observations and bands. SVG widths match their containers (about 937 px desktop and 315 px mobile);
the curve paths span about 809-815 px for retreat/cover on desktop and 233-239 px on mobile, rather than collapsing to single-point marks.
No horizontal page overflow or Streamlit exception was found. The Parameters and sources tab renders both tables without mobile page overflow.
Desktop vegetation and mobile PAH charts were visually inspected; the dark theme is retained.
