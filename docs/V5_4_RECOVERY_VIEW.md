# V5.4 Bay Jimmy recovery view (model and field values): handoff

Status: implemented, tested, seen running in Chromium; uncommitted and unpushed (branch `model_v5_1`, on top of 7698761). Presentation and data preparation only: no model, registry state, evidence verdict, screening status, recommendation, ranking or download was changed. `recovery_view.py` reads the composer, the field tables and the PAH card; `ui_plots.py` only draws.

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

Nothing is drawn after the evidence ends and there are no dotted lines (no series is a forward projection). The old synthetic figure remains only in a separate collapsed "Synthetic demonstration curves (not data)" section for Bay Jimmy.

## Where it shows

Only a run of an in-scope mapped marsh cell gets the section. Heavily oiled cells get all series. A cell of another oiling class gets the untreated composer scenario and the decline reference, with compact "unavailable" notes for vegetation and tPAH. A typed or generic marsh scenario, rocky shores, mangrove and beaches get no recovery view, so the Bay Jimmy series are not presented as applying to them. Treatment series carry the report's own screening label and a note that mechanical removal and planting are historical treatments, not recommendations.

## Files

Created: `src/shoreline_remediation/recovery_view.py`, `tests/test_recovery_view.py`, this file. Modified: `src/shoreline_remediation/ui_plots.py` (panel drawing added), `src/shoreline_remediation/ui_results.py` (recovery section; the synthetic section is kept, renamed, collapsed). Not touched: pipeline, registry, models, data, results, comparison layer, report, existing tests.

## Verification

- `python -m pytest tests/test_recovery_view.py tests/test_comparison.py tests/test_v54_results.py tests/test_decision_board.py`: 92 passed. `tests/test_recovery_view.py` alone: 15 tests (units, identity, source equality of field points, step faithfulness, horizon limit, index origin and support, separate PAH units, missing treatments, no view for typed or rocky runs, serialisation, no dotted lines, app visibility). The full suite was not rerun.
- Chromium, Bay Jimmy at 1440 and 390 px: all four panels, legend, composer-gate warning and notes render; no Streamlit exception and no horizontal overflow. Not browser-checked: the typed-marsh and rocky controls (covered by app tests), keyboard use, light theme.
- Known visual limits: on the shared 2010-2018 axis the vegetation and PAH points occupy the left third; erosion whiskers overlap near the period edges; the legend lists every series used anywhere, including ones absent from a panel.
