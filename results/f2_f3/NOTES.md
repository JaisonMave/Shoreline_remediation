F2 and F3 results (plan: docs/F2_F3_PLAN.md). Run 14 November 2026.

F2 Knowledge base as editable tables (D16)
-------------------------------------------
Moved, unchanged in behaviour, into data/knowledge/tables/ and read through
src/shoreline_remediation/knowledge.py:
  screening_rule.csv    32 ordered rules  <- fast_engine.FASTRuleEngine._classify_treatment
  ecological_score.csv  13 ordered rules  <- decision_framework._ecological_score / ecological_score_explanation
  technology.csv        15 technologies   (new descriptive catalogue)
  evidence_effect.csv   10 priors         <- treatment_effects (Zengel 2015 vegetation + Zengel 2022 erosion)

FASTRuleEngine keeps its public API and _classify_treatment (now delegates to knowledge.classify).
HybridDecisionModel._ecological_score and ecological_score_explanation keep their signatures (now read
ecological_score.csv). dashboard.py and site_view.py were not touched.

Equivalence (test tests/test_f2_f3.py, oracles frozen from the original code):
  - Screening verdicts identical over the dense grid (9 shorelines x 4 oils x coverage{5,20,35,50,80} x
    penetration{0,3,6,10,30} x 4 exposures x 4 sensitivities x surface_oil, permeability/accessibility
    cycled) = 28,800 scenarios x 15 treatments = 432,000 verdicts: 0 differences.
  - Screening verdicts identical on the 30 blind scoring scenarios (expert_scoring.build_scoring_sheet).
  - Ecological score and basis identical on the 30 scoring scenarios and the shoreline x sensitivity grid.
  - A manual exhaustive check (permeability/accessibility fully crossed, 2.59M+ verdicts) also found 0
    differences before committing the move.
  Ecological scores MOVED (exact equivalence achieved), not left in code.

Provenance: a test fails any row in any of the four tables without a non-empty source and status; the loader
raises on such a row. All rows carry source + status + evidence_type.

F3 Model interface and registry (D15, D20)
-------------------------------------------
src/shoreline_remediation/model_interface.py: SiteRecord, ScenarioRequest, Prediction (value, unit, interval
lo/hi/level, interval_method, scope {in range / new region / outside training range} with reasons,
explanation, evidence_grade, model_id, model_version, state {validated / experimental}); Model Protocol +
BaseModel ABC with predict(site, scenario) -> Prediction. Prediction validates scope, state and that the
value lies inside its interval.

src/shoreline_remediation/registry.py + models/registry.json register five thin adapters (no new science):
  edge_loss_v1                 validated     (site_evidence.predict_edge_loss + site_flags)
  pah_decline_v1               validated     (results/pah_decline half-lives; new card models/pah_decline_v1.json)
  composer_natural_recovery_v1 experimental  (scenario_composer.natural_recovery_summary / compose)
  veg_recovery_v1              experimental  (models/veg_recovery_v1.json curve)
  mangrove_damage_v1           experimental  (mangrove_model / models/mangrove_damage_v1.json)

registry.get / list(state=...) / validated_only(). validated_only() = {edge_loss_v1, pah_decline_v1}.

Promotion gate (D20, registry.meets_promotion_criteria) reads card fields: committed plan, baseline beaten on
whole held-out units, interval coverage reported, training range present. resolve_state keeps a model
validated only if it passes AND is declared validated. The composer PASSES the generic gate (clean-edge card
beats its baseline and reports coverage) but is declared experimental because the R3 heavy-cell bias gate
failed (FINDINGS_V4 26), so it stays experimental. veg_recovery_v1 FAILS the gate (suggestive: did not beat
the no-change baseline, m2_minus_m0 hi = +0.082 > 0).

Contract test: every registered model returns a Prediction with an interval and a scope for Bay Jimmy cell
8018_32612 (Heavy, in scope); the mangrove model for a Galeta-like input (oiled, year since spill 2).
Worked-site predictions:
  edge_loss_v1                 1.42 m/yr  [-1.74, 4.30]  in range   validated
  composer_natural_recovery_v1 2.08 m/yr  [-1.16, 5.23]  in range   experimental
  veg_recovery_v1              0.945 ratio [0.27, 2.43]  in range   experimental (suggestive)
  pah_decline_v1               1.61 yr    [1.25, 2.38]   in range   validated (within DWH)
  mangrove_damage_v1           0.071      [0.025, 0.117] in range   experimental

Tests
-----
tests/test_f2_f3.py       : PASS (equivalence, provenance, interface, registry, promotion gate)
tests/test_ranking.py     : PASS
tests/test_p5_demo.py     : PASS (17)
tests/test_scenario_composer.py : PASS
Full suite minus tests/test_data_catalogue.py: 139 passed + 17 p5 = 156, no regressions.

Left for Jaison
---------------
- Review the four knowledge tables (science unchanged; human review is F8; evidence_effect status=approved,
  ecological_score status=proposed as ASSUMED).
- Confirm models/pah_decline_v1.json packaging of the committed PAH results is acceptable as a model card.
- Catalogue rebuild (scripts/build_catalogue.py) for the new data/knowledge/tables files is left to the
  central run per the Track F brief (not run here).
