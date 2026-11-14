# F8 literature pooling plan

**Status:** Fixed before analysis, 14 November 2026. This plan converts the 144 Jaison-accepted, AI-extracted rows in `data/knowledge/literature_effects.csv` into traceable coefficients. The extraction fields, including `checked_by`, are inputs and will not be edited.

## Question and evidence

For each treatment technology and shoreline setting, does controlled literature show less residual oil, faster degradation, better biological recovery, or less erosion than an untreated oiled control? The inputs are `literature_effects.csv` and `literature_sources.csv`; source citation, grade, extraction origin, and study identity remain attached to every computed row. Evidence labels are **LITERATURE (AI-extracted; Jaison accepted 14 Nov 2026)**. Any imputation or vegetation-tau mapping is **ASSUMED**.

Natural recovery/untreated oiled control is the baseline. The unit held independent is a study (`doi` when present, otherwise normalised citation plus spill/experiment), never an extracted row.

## Effect metrics and sign convention

For positive arm means, the raw log response ratio is `lnRR = ln(treated/control)`. With SDs and arm sizes its sampling variance is `SD_T^2/(n_T*T^2) + SD_C^2/(n_C*C^2)`; an SE is converted to SD as `SE*sqrt(n)`. A log rate-constant ratio is `ln(k_T/k_0)` with the same delta-method variance when arm uncertainty exists. Reported percent removal relative to control, `p`, is converted to the residual-oil ratio `1-p/100` and then to `lnRR = ln(1-p/100)`; values outside 0-100% are ineligible and exactly 100% requires an arm-based estimate rather than an infinite logarithm.

Pooling uses a benefit-oriented effect while retaining the raw effect at row level:

- residual oil: benefit is less residual oil, so `effect = -ln(T/C)`;
- degradation rate: benefit is faster degradation, so `effect = ln(k_T/k_0)`;
- biological recovery: benefit is higher cover, biomass, abundance, density or survival, so `effect = ln(T/C)`; for recovery time, benefit is faster recovery and `effect = -ln(T/C)`;
- erosion: benefit is lower erosion/retreat/loss, so `effect = -ln(T/C)`.

Thus positive values always mean benefit, zero means no effect, and negative values mean harm. Metrics that cannot be represented as a positive-valued arm ratio or residual-oil percent removal are listed with an exclusion reason rather than coerced.

## Grouping and selection

Groups are `technology x habitat_class x outcome_family`. Habitat classes are **marsh**, **sand/gravel beach**, **rocky/hard**, **mangrove**, and **other**, assigned from habitat text/ESI descriptions by fixed keyword rules. Outcome families are **residual oil**, **degradation rate**, **biological recovery**, and **erosion**, assigned from outcome/metric/effect-type text by fixed rules.

Within each study and group, the primary row is the latest numeric time point at or before 730 days. If none exists, the earliest numeric post-treatment time is used and flagged. Multiple outcomes at that selected time are collapsed by fixed-effect inverse-variance averaging so one study contributes once. The longest-time row is also selected and reported as a separate supplementary estimate; it does not replace the primary estimate.

## Inclusion and sensitivity

An eligible row must have an untreated oiled control, a supported metric, positive required means, and a resolvable group. Grades A-C enter the primary analysis. Grade D enters sensitivity only; grade E is excluded. An abstract-only row enters only when both treated and control arms are numeric. Primary meta-analysis additionally requires a reported variance derivable from SD/SE and `n` for both arms.

For otherwise eligible rows missing variance, the sensitivity analysis may impute arm CVs from the median reported CV within that exact group and use `CV_T^2/n_T + CV_C^2/n_C`. This is labelled **ASSUMED**. It is not done when either arm size or a group median CV is unavailable, and imputed rows never enter the primary result.

## Pooling and outputs

At least three independent studies are required to pool. The primary random-effects model uses DerSimonian-Laird tau-squared on benefit-oriented lnRRs and Hartung-Knapp t intervals. It reports pooled effect, 95% confidence interval, 95% prediction interval, tau-squared, I-squared and `k`. Groups with fewer than three studies are reported as individual-study evidence, not pooled. A parallel sensitivity estimate includes grade D and variance-imputed rows where possible. Forest plots are produced only for primary pooled groups.

`data/knowledge/pooled_effects.csv` contains one row per observed group and primary plus longest/sensitivity statistics. `data/knowledge/evidence_verdicts.csv` contains technology, habitat, outcome family, verdict, basis, effect, CI, PI, grade mix, number of independent studies and notes. `results/f8_pooling/row_effects.csv` records every input row, computed values, selections, and inclusion reasons; `summary.txt` records counts, cross-checks, assumptions, and deviations.

## Verdict gate

- **evidence of benefit**: the primary 95% prediction interval is wholly above zero; for a single study, its 95% CI is wholly above zero and grade is A or B;
- **evidence of harm**: the corresponding interval is wholly below zero;
- **no clear difference**: eligible evidence exists but the relevant interval includes zero, there are two studies, or single-study precision/grade does not satisfy the rule;
- **no evidence**: no eligible grade A-C row exists.

Sensitivity results cannot upgrade a primary verdict.

## Composer mapping and external cross-check

For marsh biological-recovery groups with a primary lnRR estimate, the **ASSUMED** vegetation recovery multiplier is `exp(effect)`. A pooled group uses `exp(PI bounds)`; an eligible single grade A/B study uses `exp(CI bounds)`. Positive benefit-oriented biological lnRR is mapped to a larger recovery multiplier. These option ranges and their basis are written to `literature_tau_ranges.csv`; no composer code is changed.

Without refitting, the summary will compare any pooled marsh manual-removal, mechanical-removal, or planting biological/erosion coefficient with held Zengel group data. Agreement means the held-data lnRR point estimate falls within the literature 95% prediction interval. If no matching pooled coefficient exists, that absence is reported rather than a comparison being invented.

## Fixed gate and pass/fail rule

**Pass:** the script processes all 144 rows; every row has a documented inclusion/exclusion reason; independent studies, not rows, determine `k`; all requested tables and pooled-group plots are created; formulas and verdict boundaries pass the focused tests; and no source or `checked_by` field is changed. **Fail:** any output lacks provenance, a row is silently dropped, a group with fewer than three studies is pooled, sensitivity-only evidence changes a primary verdict, or the toy metric/verdict tests fail. The analysis is run once after the tests.

## Amendment F8b (defect fix, after run)

The F8 outputs are preserved in `results/f8_pooling/v1/`. F8 had two implementation defects. First, its verdict code returned "no clear difference" whenever a group had two studies instead of applying the planned individual-study rule. In F8b, every grade A/B study in a group with fewer than three independent studies is evaluated using its own 95% CI. A direction is accepted when at least one CI excludes zero in that direction and no grade A/B CI excludes zero in the opposite direction; conflicting directions give "no clear difference". The basis is `single studies (k=..., citations)` and notes retain each usable study effect and CI.

Second, outcome keywords were applied too broadly. F8b gives rate-constant, rate-ratio and half-life terms precedence and maps them to **degradation rate**. Fowler Beach row C011 (plot elevation, a physical-balance covariate rather than a residual-oil, degradation-rate, or shoreline-erosion treatment endpoint) is removed from the erosion family and excluded from coefficient estimation; the related C001-C010 rate rows remain degradation-rate evidence and residual-oil rows remain residual-oil evidence. The F8b summary lists every changed row mapping. Rate effects without variance remain eligible listings and their `exp(lnRR)` ratios are reported in verdict notes, but cannot upgrade a verdict.

For marsh biological recovery, a pooled PI still maps to `exp(PI)` and an individual grade A/B study with a finite CI maps to `exp(CI)` as an **ASSUMED** tau-multiplier range. Missing-variance studies do not yield a range. F8b reruns the fixed analysis once after the extended tests.
