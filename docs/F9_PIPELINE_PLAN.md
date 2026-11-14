# F9 plan: fixed, logged decision pipeline (D17, D31; 14 November 2026)

Status: **plan written before any pipeline code or example run**, per the Track F brief rule 1. Task: V4 plan F9.
Code: `src/shoreline_remediation/decision_pipeline.py`. Tests: `tests/test_f9_pipeline.py`. Examples and a short
summary: `results/f9_pipeline/`. `dashboard.py` and `site_view.py` are not touched (a later step does the UI);
no validated number, rule, prior or verdict is changed. No weighted-sum score (D13, D17); no language model.

## Question

For an oiled shoreline segment: which options are allowed, which are shown by field evidence to beat natural
recovery, by how much (90% interval), on what evidence, and where is the tool allowed to speak (D30)?
"No option is shown to beat natural recovery; monitor" is a valid answer.

## Inputs

`run_decision(inputs, habitat=None, oiling_class=None, oil=None, season=None, options=None, *, seed, n_draws,
horizon_years=8, contaminant="oil", objective="environmental_benefit", response_zone="shoreline")`

- `inputs`: a `Scenario` (generic shoreline) or a site dict from `data/demo/p5_sites.csv` (marsh edge cell, needs the
  four edge-loss features, `max_oiling`, `status`, `lat`, `lon`).
- `habitat`: `salt_marsh`, `mangrove` or a `Scenario.shoreline_type` (marsh, mudflat, peat, tundra, sand_beach,
  mixed_sediment, bedrock, boulder, cobble, other). Default: `salt_marsh` for a site dict, the Scenario's own type otherwise.
- `oiling_class`: SCAT class (Heavy, Moderate, Light, Very_Light, NOO). Default: the site's `max_oiling`; for a Scenario,
  derived from `oil_coverage` with the same breaks as `site_evidence.OIL_COVERAGE_BY_CLASS` read backwards (ASSUMED:
  >=70 Heavy, >=40 Moderate, >=20 Light, >0 Very_Light, 0 NOO) and labelled so in the trace.
- `oil`: oil category (light, medium, heavy, solid) or an ADIOS `oil_id` (category from `oil_library`). `season`
  overrides the Scenario season. `options`: default all 15 library options plus the planting add-on.
- Out-of-scope requests: `contaminant != "oil"`, `objective` asking for cost optimisation, `response_zone == "offshore"`.

## Steps (each logged in `trace` with step number, name, inputs, outputs and source ids)

| Step | Rule | Source |
| --- | --- | --- |
| 1 Characterise | habitat, oil category, oiling class, exposure (fetch for a site), access, season, sensitivity; scope tier (below); refusal for out-of-scope. | inputs, `oil_library`, `site_evidence.site_flags` |
| 2 Hard constraints | Marsh, beach, rocky and other shores: first matching row of `screening_rule.csv`; verdict, reason, `rule_id`. Mangrove: the table has no mangrove rows, so `mangrove_screening.csv` is the rule source (acceptable = eligible, conditional, not_recommended = ineligible). A mangrove option with no screening row is excluded ("not screened"). `ineligible` removes the option. | F2 tables |
| 3 Do no harm | Remove an option with `evidence of harm` in `evidence_verdicts.csv` for this habitat class (citation kept). Flag, not remove, an option with a `harms` row in `treatment_conditions.csv` (marsh only; a season-checkable condition that the input season does not meet is not flagged) and an option the composer shows harmful (step 4). Mangrove: `not_recommended` is removal. | F8 verdicts, F2 conditions |
| 4 Benefit vs natural recovery | Heavily oiled marsh: `scenario_composer.compose`, paired difference from natural recovery (same draw, shared uncertainty cancels) for options with Zengel field evidence (manual, mechanical, planting). **Two pre-specified outcomes, one evaluation point each**: cumulative edge loss at year `min(horizon, 8)` (the end of the observed record) and vegetation cover ratio to reference at year 2 (the only year with a measured shift; independent of the vegetation curve). Years 2, 5, 8 are all reported, only the pre-specified point decides. Benefit interval = minus the paired edge-loss interval (m of edge not lost) and the paired vegetation interval. Other options and habitats: aggregate `evidence_verdicts` rows (benefit / harm / no clear difference / no evidence / mixed) with the basis string. No outcomes are combined into one score. | composer (experimental), verdicts |
| 5 Endpoint and time | PAH-sum half-life by oiling class (`pah_decline_v1`, validated within DWH; "no decline detected" with the lower bound where the card has none); vegetation time to 80% of reference (`veg_recovery_v1`, experimental; heavy flagged "worse than a no-trend baseline", FINDINGS 14); cumulative natural edge loss to years 5 and 8 (composer) with the validated `edge_loss_v1` 2010-2015 rate beside it, for an in-scope marsh cell. Mangrove: `mangrove_damage_v1` oiling effect by year (experimental). Missing: "no model". | registry |
| 6 Trade-offs | Production rate, waste per m2 from `literature_effects.csv` rows for the same technology and habitat class; cost class "not sourced" (no cost column exists); secondary impacts from `technology.csv`. Shown, never scored. | literature, technology table |
| 7 Recommendation | Classes below; ordering basis stated; headline. | steps 2-6 |
| 8 Report | `DecisionReport`: headline, scope tier and message, options table, natural-recovery reference, plot data (paired differences with intervals, cumulative edge-loss trajectories natural vs top options, evidence-verdict matrix), trace, version info (git commit when available, model ids and states, table checksums). | all |

## Scope tiers (D30), step 1

| Tier | When | Message |
| --- | --- | --- |
| validated | Salt marsh, Heavy, a cell that passes `site_flags` (in scope, inside the training box) | edge-loss and PAH-sum numbers validated (Gulf of Mexico, one spill); composer differences and vegetation curve carry an experimental badge |
| experimental | Other salt-marsh inputs (non-heavy, cell outside scope or box, generic marsh Scenario) and mangrove | numbers shown with an experimental badge and the reason |
| rules_and_literature | Sand, mixed sediment, bedrock, boulder, cobble, other | screening verdicts and literature verdicts only; no site forecast |
| out_of_scope | other contaminant, cost optimisation, offshore | refusal message; options empty; the eight steps are still logged (steps 2-7 "skipped") |

Mangrove input never calls an edge-loss, composer, vegetation-curve or PAH model (Galeta oiling effect only).

## Recommendation classes (step 7)

Precedence for one option: **E** (rule or harm excluded) first; then **A** if a pre-specified benefit interval excludes
zero favourably and no pre-specified outcome excludes zero unfavourably (or a verdict is "evidence of benefit");
then **D** if harm is reported under some conditions (condition flag or an unfavourable composer interval);
otherwise **B** (allowed, no clear evidence either way). **C** is `natural_attenuation`, always present as the
reference. Table order: A, B, C, D, E.

Within a class: group by evidence type (edge-loss benefit in m, then vegetation benefit, then literature lnRR),
descending lower bound of the benefit interval within a group (units are never mixed), then the ASSUMED
ecological score (higher = lower disturbance first), then name. The ordering basis is written into each row and the report.
If A is empty: headline "No option is shown by evidence to beat natural recovery; monitor" plus the best class-B options.

## Determinism, speed, caching

Seeded (`seed` default 20261112, as the composer). Knowledge tables, evidence files, model cards and composer
frames are cached (`lru_cache`); target under 5 s for a single cell including a cold load. `decide_case(case_row)`
builds a generic Scenario from a historical case dict (`scenario` key, or text fields mapped with documented
keywords; unstated fields keep `Scenario` defaults and are logged as ASSUMED) and calls `run_decision`; it does not touch
`validation/historical_validation.py`. F11 will call it.

## Pass / fail rules (tests, `tests/test_f9_pipeline.py`)

1. trace has the eight steps in order; 2. an excluded option never appears in A-D; 3. natural recovery always present
(class C); 4. heavy marsh cell 8018_32612: planting in A with a benefit interval; the test asserts what the data
say (worked-cell expectation from FINDINGS 18: planting avoids edge loss with a 90% interval excluding zero; exact numbers are read
from the run, not fixed in the test); 5. mangrove input uses no marsh model; 6. out-of-scope returns the refusal; 7. hot-water washing on rocky shore is
removed by do-no-harm (F8b evidence of harm); 8. same seed gives the same report; 9. JSON round-trips; 10. a cold
single-cell run is under 5 s. Also run `tests/test_ranking.py`, `tests/test_f2_f3.py`.

## Known limits (stated in the report)

- Planting evidence is planted vs oil-untreated plots **inside mechanically treated areas** (Zengel 2022), while mechanical
  removal is excluded on marsh by rule. The planting option is therefore class A with a caveat; the two rules are in tension and
  are listed for Jaison's review.
- Composer paired differences are one site (Bay Jimmy), observational except planting, and the composer is experimental (R3 bias gate).
- `evidence_verdicts` holds no "evidence of benefit" row yet; class A outside heavy marsh is empty until pooled benefits exist.
- Aliases used to map condition and mangrove rows without a tool code to library options (ASSUMED, listed in the code): sediment
  removal / excavation -> `mechanical_removal`; hot-water washing -> `high_pressure_heated_washing`.
- The planting add-on is excluded outside marsh and mangrove by a pipeline applicability rule (`f9:planting_applicability`, not a
  knowledge-table row); a harm verdict is cited in addition to a rule exclusion when both apply.
