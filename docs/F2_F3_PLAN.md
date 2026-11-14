# F2 and F3 plan: knowledge tables, model interface and registry (14 November 2026)

Status: **Plan written before any move or run**, per the Track F brief rule 1. Covers V4 plan tasks
F2 (D16) and F3 (D15, D20). No validated number changes; `dashboard.py` and `site_view.py` are not touched.
Results and notes go to `results/f2_f3/`. Tests: `tests/test_f2_f3.py` (new), plus the unchanged
`tests/test_ranking.py`, `tests/test_p5_demo.py`, `tests/test_scenario_composer.py`.

## F2 Knowledge base as editable tables (D16)

### What moves

| From (code) | To (table) | Behaviour |
| --- | --- | --- |
| `fast_engine.FASTRuleEngine._classify_treatment` FAST-like rules | `data/knowledge/tables/screening_rule.csv` | unchanged |
| `treatment_effects` Zengel 2015 veg + Zengel 2022 erosion priors | `data/knowledge/tables/evidence_effect.csv` | recorded as data (point + 90% interval), source/design/n/period |
| the treatment library + mechanism/habitat notes | `data/knowledge/tables/technology.csv` | new descriptive table |
| `decision_framework._ecological_score` / `ecological_score_explanation` ASSUMED scores | `data/knowledge/tables/ecological_score.csv` | moved — exact equivalence shown below |

`src/shoreline_remediation/knowledge.py` is a new loader. `FASTRuleEngine` keeps its public API and
`_classify_treatment`, which now delegates to `knowledge.classify`. `HybridDecisionModel._ecological_score`
and `ecological_score_explanation` keep their signatures and read `ecological_score.csv`.

### Machine-readable condition form (documented)

A rule row has a `technology` match (a `|`-separated set of treatment codes, or `*` for any) and a
`condition` over Scenario fields. The condition is zero or more clauses joined by `;` (logical AND); an
empty condition is always true. Each clause is `field op value`:

- Fields (and the exact Scenario expression they read, preserving the original's case handling):
  `shoreline`=`shoreline_type.lower()`, `oil`=`oil_category.lower()`, `exposure`=`wave_exposure.lower()`,
  `sensitivity`=`shoreline_sensitivity.lower()`, `coverage`=`oil_coverage` (float),
  `penetration`=`penetration_depth_cm` (float), `surface_oil`=`surface_oil` (bool),
  `permeability`=`substrate_permeability` (str, not lowercased), `accessibility`=`accessibility` (str, not lowercased).
- Ops: `in`, `not_in` (value is a `|`-separated set), `<`, `<=`, `>`, `>=`, `==`.

Rules are evaluated in ascending `order`; the first rule whose technology matches and whose condition is
true returns its verdict. This reproduces the original sequential `if ... return` fall-through exactly: each
original `return` becomes one ordered row, and compound `OR` conditions (hard-substrate pressure washing) are
split into separate rows. A final `*` / empty row returns `conditional`, matching the function's last line.

### Equivalence criteria (test written before the move, must pass after)

`tests/test_f2_f3.py` embeds a frozen copy of the original `_classify_treatment` and the original
`_ecological_score` / `ecological_score_explanation` as oracles. Over a dense grid of Scenarios — every
shoreline type x oil category x coverage {5,20,35,50,80} x penetration {0,3,6,10,30} x wave exposure x
sensitivity x surface_oil {True,False} — plus the 30 blind scoring scenarios from
`expert_scoring.build_scoring_sheet()`:

1. every treatment's screening verdict from `FASTRuleEngine` (table-driven) equals the oracle;
2. every treatment's ecological score and explanation (`score`, `basis`) equals the oracle.

A further test fails any row in any of the four tables that lacks a non-empty `source` or `status`.

Ecological-score equivalence is achievable exactly because the original is a pure function of
(treatment, shoreline, sensitivity) returning fixed numbers and fixed basis strings, so it moves to the
table. It is moved.

## F3 Model interface and registry (D15, D20)

### Interface (`model_interface.py`)

- `SiteRecord(site_id, habitat, region, lat, lon, oiling, fields: dict)` — site fields plus the predictors a
  model declares it needs (in `fields`).
- `ScenarioRequest(treatment, horizon_years)`.
- `Prediction(value, unit, interval_lo, interval_hi, interval_level, interval_method,
  scope, scope_reasons, explanation, evidence_grade, model_id, model_version, state)` where
  `scope` is one of `in range` / `new region` / `outside training range`, and `state` is
  `validated` / `experimental`.
- `Model` Protocol and `BaseModel` ABC with `predict(site, scenario) -> Prediction`.

### Adapters (thin wrappers, no new science)

| model_id | wraps | state | evidence grade |
| --- | --- | --- | --- |
| `edge_loss_v1` | `site_evidence.predict_edge_loss` + `site_flags` | validated | validated (P2 held-out) |
| `composer_natural_recovery_v1` | `scenario_composer.natural_recovery_summary` / `compose` | experimental | bias gate failed (FINDINGS_V4 26) |
| `veg_recovery_v1` | `models/veg_recovery_v1.json` curve | experimental | suggestive |
| `pah_decline_v1` | `results/pah_decline` half-lives by oiling class + `models/pah_decline_v1.json` | validated | validated within DWH (FINDINGS 22) |
| `mangrove_damage_v1` | `mangrove_model` / `models/mangrove_damage_v1.json` | experimental | experimental (oiling effect, one spill) |

Each adapter reads its model card (JSON, or for PAH a card summarising the committed results) for state,
training range and interval, and returns a `Prediction` with an interval and a scope flag.
`models/pah_decline_v1.json` is created to package the already-committed PAH results (no new science).

### Registry

`registry.py` + `models/registry.json`: `registry.get(model_id)`, `registry.list(state=...)`,
`registry.validated_only()`. The registry resolves each entry's final `state` from the D20 promotion check
(below) combined with the entry's declared state; experimental models are only returned by `list(...)`, never
by `validated_only()`.

### Promotion rule (D20) as a check function

`meets_promotion_criteria(card) -> (bool, reasons)` reads card fields and requires: a committed plan is
recorded; the model beat a no-predictor baseline on whole held-out units; interval coverage is reported; a
training range is present. A model is `validated` only if it passes this check **and** its registry entry
declares it validated (the composer declares experimental because of the R3 bias gate, FINDINGS_V4 26, even
though it reports coverage); otherwise it is `experimental`.

### Contract test

For the worked site Bay Jimmy cell `8018_32612` (`data/demo/p5_sites.csv`, Heavy, in scope) every registered
marsh/DWH model returns a `Prediction` carrying an interval and a scope; the mangrove model is called with a
Galeta-like input (oiled, year since spill). The test also checks `validated_only()` excludes experimental
models and that `list(state="validated")` matches.

## Out of scope / not changed

Science is unchanged: no coefficient, prior or verdict is altered. `dashboard.py`, `site_view.py` and all
existing results files are untouched. Human review of the tables is F8.
