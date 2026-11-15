# V5.1 implementation record

V5.1 is a stabilisation release: architecture, scientific governance, then the premium dashboard. It is not a rebuild.
This file records what was implemented and why. Validation figures live in [`V5_1_VALIDATION.md`](V5_1_VALIDATION.md);
session state lives in [`V5_1_HANDOFF.md`](V5_1_HANDOFF.md). Status words: **implemented** (code exists), **tested**
(software tests pass), **validated** (a pre-specified scientific gate passed), **experimental**, **planned**.

## Session 1 (15 Nov 2026): architecture and scientific stabilisation

### 1. Runtime pathway (verified by reading the code and by launching the app)

```
dashboard.py ── "Site evidence" ──▶ site_view.py ──▶ ui_pipeline.py ──▶ decision_pipeline.run_decision()
            └─ "Scenario screening (legacy)" ──▶ ui_scenario.py ──▶ ui_pipeline.py ──▶ run_decision()   (answer card)
                                                              └──▶ decision_framework.HybridDecisionModel (legacy panel)
                                                              └──▶ process_model (illustrative curves, gate failed)
```

- `run_decision()` is the only function that assigns recommendation classes and categories.
- **Defect fixed.** `site_view._rule_table` (production view, "Detailed tables") called the legacy
  `HybridDecisionModel.rank_treatments` and showed its order as "Rule-screening order", a second ranking beside the
  pipeline's. It now reads verdicts, categories and order from the pipeline report. `site_view.py` no longer imports
  any legacy module.
- **Kept, labelled.** The legacy scenario view still shows the legacy rule ranking and the illustrative process
  model under the headings "Legacy rule screening" and an "Illustrative" badge, below the pipeline's answer. It is
  reachable only from the tab named "Scenario screening (legacy)". Nothing was deleted.
- `tests/test_v5_1_governance.py` checks by static import analysis that 16 production modules import none of the
  legacy modules (`decision_framework`, `fast_engine`, `ml_models`, `process_model`, `scenario_runner`,
  `shoreline_transport`, training scripts, `validation_panel`).

### 2. Recommendation categories (decision D41, Proposed)

Class letters A to E and `evidence_state` are unchanged. A rule-based category is added to every option
(`recommendation_category`, with its label, rule and reason) and a `decision_outcome` to every report.

| Category | Rule |
|---|---|
| Recommended | class A, input inside the scope of the benefit evidence (tier "validated"), no excluded prerequisite |
| Conditional | class D; or class A outside that scope; or class A whose prerequisite method is excluded |
| Natural recovery with monitoring | class C (the reference option) |
| Allowed, no demonstrated benefit | class B with evidence showing no clear difference from natural recovery |
| Insufficient evidence | class B with no eligible evidence rows |
| Excluded | class E |

A sixth label ("Allowed, no demonstrated benefit") was added to the five in `CLAUDE.md` because "evidence exists and
shows no difference" is neither "conditional" nor "insufficient evidence". Owner to confirm.

Consequences seen on the worked example (Bay Jimmy cell 8018_32612): manual removal is Recommended, with the reason
naming its one-site observational basis; planting is now Conditional because it presupposes mechanical removal,
which the screening rules exclude on marsh (this tension was previously only a caveat). The headline says so.

### 3. Ranking honesty

`rank_in_class` is kept. Each option now carries `rank_basis` (`evidence` or `display_convention`),
`rank_basis_text` and `rank_tied_with`. An order is called evidence only when a benefit-interval lower bound
separates the option from every other member of its class. Everything else is declared a display convention
(ASSUMED ecological score, then name).

### 4. Abstention

- **Unsupported habitat (defect fixed).** A shoreline type absent from the habitat table (for example
  `coral_reef`) used to be screened with the generic rules and returned seven "allowed" options. It now returns a
  report with tier and outcome `unsupported_habitat`, no options, no numbers, and the list of supported types.
- Every report has `abstentions`: no site forecast (rules-and-literature tiers), outside validated scope (with the
  reasons), quantities with no model, options with no evidence to compare, borrowed salt-marsh evidence (mudflat,
  peat, tundra), and "no intervention is recommended".
- Missing site inputs: no edge-loss number is produced, the reason is stated, and nothing is recommended outright
  (tested).

### 5. Model registry

- `models/registry.json`: a `governance` block on all nine entries (six models, three cards). The failed F5 process
  model is now listed as a card-only entry so its failure is visible in one place.
- `registry.py`: `governance_gaps`, `failed_gates`, `promotion_report`, `governance_table`; `resolve_state` now also
  requires a complete governance record and no failed blocking gate. Validated set unchanged.
- `model_interface.Prediction.interval_status`: validation status of the interval, set by the registry on every
  prediction.

### 6. NOAA provenance

`validation/noaa_rating_source_check.py` compares the AI-transcribed ratings with the PDF text layer (126 of 126
match). Status stays "Proposed". See `V5_1_VALIDATION.md` section 4.

### 7. Dashboard touched only where needed

`ui_evidence` view models carry the new fields; `ui_components.render_pipeline_section` shows the decision outcome
and a "What the platform does not state" expander; the HTML report has a Category column, the outcome and the
abstention list. No redesign yet (Session 2).

### Interfaces changed (all additive)

- `DecisionReport`: `decision_outcome`, `decision_outcome_label`, `recommendation_summary`, `abstentions`.
- Option rows: `recommendation_category*`, `rank_basis`, `rank_basis_text`, `rank_tied_with`.
- New `scope_tier` value: `unsupported_habitat`. `PIPELINE_VERSION` is now `f9-v3`.
- `Prediction.interval_status` (default empty string).
- Registry JSON: `governance` per entry; `cards_without_adapter` gains `process_model_v2`.

## Session 2 and 3

Planned. See the handoff for the exact starting point.
