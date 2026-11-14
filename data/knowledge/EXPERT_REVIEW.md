> **Provenance: written by an AI agent asked to act as an expert. Not a human expert review. Treat every range and verdict as AI-PROPOSED until reviewed by named human experts (V4 plan R6, F8).**

# Expert review of treatment conditions and literature ranges (13 Nov 2026)

Done by the orchestrator at Jaison's request ("act as a senior soil and environmental chemist and decide").
Inputs: `treatment_evidence_untested.csv`, `TREATMENT_EVIDENCE_NOTES.md`, `treatment_conditions.csv`.
The ranges first set by the mechanical rule are kept in `elicited_priors.csv` (`rule_lo`, `rule_hi`); the
revised ranges replace them in `tau_multiplier_lo/hi`, which the composer reads. A range multiplies the
vegetation recovery time constant: below 1 is faster recovery than leaving the marsh alone.

## Principles used
1. **Mechanism sets the direction, field evidence sets the width.** Where the mechanism makes harm
   implausible (oil removed without touching the soil), the range is pulled in on the harm side; where the
   mechanism is physical damage to roots or soil, the range sits at or above 1.
2. **Marsh soils are waterlogged and anoxic below a few millimetres.** Oil that reaches the soil degrades
   slowly whatever is added at the surface; treatments acting on surface oil can help only before
   penetration. This is why timing dominates the conditions.
3. **The plant, not the oil, decides recovery.** Spartina regrows from rhizomes if they survive; anything
   that kills rhizomes (burning dry soil, trampling, excavation, cutting in the growing season) is worse
   than the oil itself at moderate oiling.
4. **A narrower range is a claim of knowledge.** Ranges were narrowed only where mechanism and evidence
   agree, never because a number would look better.

## Decisions on ranges (revised; rule-based range in brackets)
| Treatment | Revised | Verdict | Reasoning |
| --- | --- | --- | --- |
| Nutrient addition | 0.7-1.2 (0.6-1.6) | Conditional | Nitrogen limits Spartina growth and surface oil degradation, so modest benefit is plausible; anoxia below the surface caps it; harm is unlikely at normal doses. Field benefit unproven. |
| Bioaugmentation | 0.8-1.2 (0.6-1.6) | Not recommended | Indigenous degraders are abundant in Gulf marsh soils; added cultures did not beat nutrients alone in tests. Little harm, no expected benefit, added cost. |
| In-situ burning | 0.6-1.6 (unchanged) | Conditional | Outcome flips with water over the soil (helps) versus dry soil (kills rhizomes). With the condition unknown the wide range is honest; the conditions table asks the user. |
| Vegetation cutting | 0.9-1.8 (0.6-1.6) | Not recommended | Most compiled cases recovered slower than no cleanup; cutting in the growing season removes photosynthetic tissue when the plant most needs it. Exception for access to thick oil in dormant season. |
| Low-pressure flushing | 0.8-1.2 (0.6-1.6) | Conditional | Louisiana plots show recovery similar to no cleanup; useful only for fresh liquid oil; small effect either way. |
| Shoreline cleaners | 0.6-1.2 (0.6-1.6) | Conditional | Benefit is real only within 1-2 days of oiling (before penetration); later, little effect. Harm is low if released oil is collected. |
| Passive sorbents | 0.7-1.3 (0.5-2.0) | Acceptable | Removes oil without disturbing soil; no controlled comparison, but no plausible mechanism of harm if collected. |
| Vacuum of pooled oil | 0.7-1.3 (0.5-2.0) | Conditional | Removes pooled oil early; nozzle damage is the risk, controlled by method. |
| Sediment removal | 1.0-2.0 (unchanged) | Not recommended | Lowers elevation and removes rhizomes; recovery slow unless elevation is rebuilt and replanted. |
| High-pressure washing | 1.0-1.8 (0.5-2.0) | Not recommended | Not in the literature search; physical stripping of stems and soil and driving oil into sediment make harm the expected direction. |

## Decisions on conditions
All conditions in `treatment_conditions.csv` are approved as **advisory**: they are shown as questions
beside each option and do not change rule verdicts. Reason: most cannot be checked from site data (season,
standing water, days since oiling), and silently changing a verdict on an unverifiable condition would
hide the reason from the planner.

## Mangroves
`mangrove_screening.csv` sets verdicts for mangrove from TROPICS, Galeta and guidance by analogy. Principle:
in mangroves, anything that enters the forest (foot traffic, cutting, excavation) is worse than in marsh,
because roots do not regrow from rhizomes and oil pushed into anoxic sediment persists for decades. So
mangrove treatment is restricted to work from the water or the fringe. Rows marked "to verify" rest on
analogy or judgement and should be checked against NOAA's 2014 mangrove guidance (listed for download).

## What this does not change
No measured effect (Zengel manual, mechanical, planting) is altered. Elicited options still carry the label
"ELICITED, not measured" and still have no edge-loss effect. The composer re-run with these ranges happens
after the current jobs finish.
