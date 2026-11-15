# Roadmap status snapshot (14 November 2026, V5)

This is the current status view for branch `model_v4` after the V5 work. It supersedes older summary rows in `docs/ROADMAP.md` that say Track F is not started. The detailed milestone history and decision register (D1-D40) remain in `docs/ROADMAP.md`; evidence and numbers are in `docs/FINDINGS_V4.md` (sections 34-42) and `docs/FINDINGS_V5.md` (sections 43-51). "Implemented" does not mean "validated", "human-reviewed" or "released".

## Track F (carried forward from the F11 checkpoint)

| Item | Current status | Evidence / remaining gate |
| --- | --- | --- |
| F0 Scope (D30) | Documented; beach rows updated by D36/D39 | Validated, experimental, rules/literature-only and out-of-scope tiers in `docs/F0_F1_SCOPE_AND_DECISIONS.md`. Keep claims within those tiers. |
| F1 Decisions (D14-D21, D30-D31) | Implemented/documented; owner review remains | Parked P1-P5, variable-definition and dashboard reviews remain Jaison's. D23-D24 remain Proposed / AI-PROPOSED. |
| F2 Knowledge tables | Implemented; equivalence check passed in V4 | V5 changed rule 160 on purpose (hot high-pressure washing on permeable mixed sediment: eligible to conditional); nothing else in the frozen oracle changed. |
| F3 Interface and registry | Implemented; promotion limits apply | Edge-loss v1 and PAH decline v1 validated within stated scope; composer, vegetation, mangrove, process, oil-excess option, interval option and beach persistence are experimental or gated. The D20 promotion check is a presence check and is not a validation. |
| F4 Common schema | Implemented; reconciliation passed | 38/38 checks. Raw Galeta data not loaded. |
| F5 Process model | Gate failed; illustrative only | Calibrated held-out error 0.775 versus empirical 0.750. Outside the decision path. |
| F6 Treatment records | Awaiting usable data / owner action | No public segment-level DWH treatment records. OR&R 42 digitisation is the only route and is not started. |
| F7 Second spill | Awaiting data | No qualifying spill. Exxon Valdez lingering-oil data are downloaded, not analysed. |
| F8 Literature pooling | Completed with limited conclusions | Original two-study rule restored (D34): 0 benefit, 0 harm, 9 no clear difference, 24 no evidence. Rows carry the owner's attestation (D33). |
| F9 Decision pipeline | Implemented; conservative | Habitat-aware (ESI), NOAA ratings, `evidence_state` (D35). Not a claim of operational effectiveness. |
| F10 Adaptive monitoring | Within-period check passes; temporal update fails | Unchanged in V5. |
| F11 Integrated validation | Rerun in V5; review/sign-off outstanding | Agreement 2 of 6 (v4: 2 of 6) against 5 of 6 always-active; method allowed 320 of 400 (v4: 264) with allow-everything 400 of 400. No reviewer responses collected. |
| F12 Release v4.0 | Not released | Requires Jaison's review and sign-off, final test run, release decision. |

## V5 (14 Nov 2026)

| Item | Current status | Evidence / remaining gate |
| --- | --- | --- |
| Gate 0.1 out-of-sample oil excess (D37) | FAILED; non-default option, experimental | MAE not below no-excess baseline in Barataria (1.036 vs 1.011) or Breton (1.743 vs 1.570). FINDINGS_V5 44. |
| Gate 0.2 per-class intervals (D38) | FAILED; non-default option, experimental | 3 of 12 coverage groups outside 80-97%; Breton Winkler 11.28 vs 11.20. FINDINGS_V5 45. |
| F8 rule and B023 fix (D34) | Completed | No verdict changed by the B023 fix. FINDINGS_V5 46. |
| Insufficient-evidence state (D35) | Completed | Field `evidence_state`; class letters unchanged. |
| ESI habitat table and NOAA screening (D36) | Under validation | Scope approved; A-D mapping Proposed; transcription and beach notes need owner spot-check. FINDINGS_V5 47. |
| Sand-beach persistence (D39) | Gates B-1 and B-2 FAILED; baseline packaged, experimental | Pooled integrated Brier 0.284 model vs 0.216 baseline. FINDINGS_V5 48. |
| Literature and data obtained | Acquisition done; not analysed | OR&R 42, OSAT-2/3 and paywalled papers not obtained. FINDINGS_V5 49. |
| Dashboard (D40) | Under validation | Script-tested; no browser check; pydeck map not built. FINDINGS_V5 50. |
| Integration (registry, beach model, dashboard) | In progress | FINDINGS_V5 51. |
| Owner attestation of literature rows (D33) | Recorded | His statement, not an independent check. |

## V5.1 (15 Nov 2026 onward)

| Item | Current status | Evidence / remaining gate |
| --- | --- | --- |
| Session 1: one decision pathway | Implemented and tested | Legacy model call removed from the production site view; static import test. `docs/V5_1_IMPLEMENTATION.md`. |
| Session 1: recommendation categories and abstention (D41) | Implemented and tested; Proposed | Owner to accept the category rules and the sixth label. |
| Session 1: registry governance and stricter promotion | Implemented and tested | Validated set unchanged (`edge_loss_v1`, `pah_decline_v1`). |
| Session 1: validation figures reconciled | Documented | `docs/V5_1_VALIDATION.md`; no replay metric shows skill (unresolved). |
| Session 1: NOAA transcription check | Software check done (126/126) | Human review and D36 mapping still Proposed. |
| Session 2: premium dashboard foundation | Planned | Start point in `docs/V5_1_HANDOFF.md`. |
| Session 3: decision experience, evidence explorer, report, release | Planned | |

## Claim boundaries

- **Validated scope is unchanged:** heavily oiled northern Gulf salt-marsh edge loss within Deepwater Horizon (held out by Louisiana basin) and DWH soil PAH-sum decline (held out by station). Both are within one spill.
- **Beaches are rules and literature only**, with one experimental reference: the sand-beach persistence curve by starting oiling category (baseline; the model failed both gates). It describes persistence of visible oil under the response as carried out. It is not natural recovery and cannot rank treatments. Mixed sand and gravel, and gravel, have rules and literature only.
- **Wording corrected in V5 because the v4 wording overstated:**
  - The edge-loss card said held-out intervals "covered 89%". That figure belongs to P2 model M2's inner interval, not the deployed interval. The deployed interval's pooled 0.900 is true by construction (calibrated in sample); by basin and oiling class it covers 76-99%. Both are now stated on the card.
  - The edge-loss "validated" model has no oiling term; the oil term in the composer is experimental and did not beat no excess (gate 0.1).
  - The mangrove card's per-outcome "verdict: validated" is an outcome-level grade from one site, not a model state (model state: experimental).
  - The PAH card's "validated" means the PAH sum falls in soil; the PAH/hopane ratio does not fall, so degradation is not shown.
  - Planting is labelled observational, one site, not randomised.
  - Hot-water washing "harm" verdicts came from a post-run rule change (F8b) and are withdrawn; the caution now rests on sourced NOAA habitat ratings.
  - The literature table was described as accepted by Jaison with an empty `checked_by`; it now carries his attestation (D33).
- AI-proposed rows are not expert elicitation. Heavy-cell composer bias is not fixed. F11 agreement with responders and the "method allowed" rate are not performance measures.
- One spill supplies the evidence. Louisiana basin hold-out is within-spill generalisation, not independent-spill validation.
- Costs, other contaminants, offshore response and broad ecosystem generalisation are out of scope.

## Not done or open

No browser check of the dashboard; OR&R 42, OSAT-2/3 and the paywalled papers not obtained; NOAA rating transcription and beach literature notes need the owner's spot-check; pydeck satellite map not built; no second spill; no treatment records per segment; no expert review. Exxon Valdez lingering-oil data are downloaded but not analysed.

## Close-out sequence

1. Jaison reviews the dashboard, the spot-check list and the decisions awaiting him (`docs/HANDOFF.md`).
2. Obtain genuine expert feedback; if unavailable, state that explicitly.
3. Resolve gates only through a pre-specified plan and new evidence. Do not weaken gates after the fact.
4. Run `python -m pytest tests` (327 tests, all passing on 14 Nov 2026 with Python 3.13) and the reproduction checks in the target environment; record outputs.
5. Release only after explicit owner sign-off.
