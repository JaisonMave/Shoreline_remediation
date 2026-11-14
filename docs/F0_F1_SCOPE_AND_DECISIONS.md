# F0 scope and F1 decisions (14 November 2026)

Jaison delegated Track F decisions to the orchestrator on 14 Nov ("complete Track F independently by your own
decisions keeping the things for me to review"). Every decision below is marked "Approved by orchestrator
under delegation, for Jaison's review" in `docs/ROADMAP.md`. Jaison reviewed and accepted the literature
table on 14 Nov (it is treated as checked for use, still labelled AI-extracted).

## F0 Scope statement (D30)

The decision support system answers, for an oiled shoreline segment: which options are allowed, which are
expected to do better than natural recovery, by how much, with what confidence, and on what evidence. "No
option is distinguishable from natural recovery; monitor" is a valid answer.

| Scope tier | Content | What the tool may say |
| --- | --- | --- |
| Validated | Heavily oiled salt marsh, northern Gulf of Mexico: marsh-edge loss (edge loss v1, held out by basin); soil PAH-sum decline within DWH | Numbers with intervals and scope flags |
| Experimental | Composer forecasts with oil excess (bias gate failed, D32), vegetation recovery curve, mangrove damage (one spill), process model (until F5 gate), literature-pooled effects | Numbers shown with an "experimental" badge and the reason |
| Rules and literature only | Beaches, rocky shores, gravel, other habitats | Screening verdicts, literature evidence verdicts; no site-specific forecast |
| Out of scope | Other contaminants, cost optimisation, offshore response | Refused with a message |

## F1 Decisions taken

| ID | Decision | Basis |
| --- | --- | --- |
| D14 | Common schema adopted (source, site, event, observation with censoring, intervention) | Needed for DIVER censoring and second-spill harmonisation; F4 |
| D15 | Standard model interface adopted (value, interval, scope, explanation, state) | Lets the pipeline treat every model alike; F3 |
| D16 | Knowledge base as editable tables with source and status per row | Reviewable without code; F2 with an equivalence test |
| D17 | Fixed, logged pipeline; no language model in the decision path; no weighted-sum ranking | Reproducibility; D31 order |
| D18 | Process model in gated steps; surrogate not built | F5 |
| D19 | Offshore fate models deferred (no forecasting use case or second spill yet) | Unchanged; documented in F7 |
| D20 | Registry with validated and experimental states and a promotion gate | F3 |
| D21 | SSURGO and SoilGrids not used as marsh soil predictors | FINDINGS 13 (null) |
| D23, D24 | Stay Proposed (AI-PROPOSED) until a human expert reviews them | R6 |
| D30 | Scope tiers above | F0 |
| D31 | Decision order: constraints, do no harm, benefit vs natural recovery, endpoint and time, trade-offs shown not scored, recommendation classes | F9 |

## Parked reviews (still Jaison's)

P1-P5 reviews, the variable-definition check and the dashboard test remain his; Track F does not change any
validated number from P1-P5. Expert scoring (M6) is replaced for now by literature pooling (F8, D26); a human
expert panel stays desirable for F11 and is listed as an open item.
