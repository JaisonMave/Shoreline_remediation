# Handoff — Shoreline Remediation (14 November 2026)

## Start here

- **Repository:** [JaisonMave/Shoreline_remediation](https://github.com/JaisonMave/Shoreline_remediation)
- **Working branch:** `process-model-audit`
- **Latest implementation checkpoint before this documentation wrap-up:** [3f6b74a](https://github.com/JaisonMave/Shoreline_remediation/commit/3f6b74aeca691d742f6279ff26d4c93861a311b3) (F11 integrated validation).
- **Current milestone snapshot:** [`docs/ROADMAP_STATUS.md`](ROADMAP_STATUS.md). It supersedes the older “F1-F12 not started” status in the historical roadmap table; the original decision register and milestone history remain in [`docs/ROADMAP.md`](ROADMAP.md).
- **Latest findings:** [`docs/FINDINGS_V4.md`](FINDINGS_V4.md), sections 34–42. **Change history:** [`CHANGELOG.md`](../CHANGELOG.md).

## What the project is—and is not

This is an evidence-led prototype for screening shoreline oil-spill response options. Its validated numerical scope remains narrow: heavily oiled northern Gulf salt-marsh edge loss (held-out by Louisiana basin) and DWH soil PAH-sum decline. Other habitats are screening/literature-only or experimental. The process model failed its held-out comparison gate and must stay illustrative, outside the decision path. This is not an operational response tool, a cross-spill validation, or a cost optimizer.

The fixed recommendation pipeline is intentionally conservative: it can return “no option is shown to beat natural recovery; monitor.” Its historical replay agreed with the active/natural direction in 2 of 6 cases versus 5 of 6 for an always-active baseline. This is a material limitation, not a result to hide or tune away. The F11 pack contains ten reports but **no expert responses**.

## Track F checkpoint

See [`ROADMAP_STATUS.md`](ROADMAP_STATUS.md) for the item-by-item status. In brief, F2–F11 have code/results and documented findings. This does **not** mean all are scientifically validated or signed off: the composer bias gate failed; process-model promotion failed; F11 exposed historical disagreements; and expert review is still outstanding. F1 owner reviews and F12 release/sign-off remain open.

Important open evidence gaps:

1. No public, usable segment-level DWH cleanup-treatment records; OR&R 42 provides treatment stretches in map figures only.
2. No second spill with harmonized oiling, treatment, and outcome data for whole-spill validation.
3. No independent expert-panel responses; AI-proposed rows must not be presented as human-elicited.
4. The experimental composer continues to over-predict heavy-oiling cells; its bias gate fails, including after D32 scaling.
5. The process model does not beat the empirical PAH decline curve on held-out stations.
6. The public literature extraction is labelled AI-extracted; retain its provenance and verify individual rows before relying on them for consequential decisions.

## Suggested next steps for Jaison

1. Review the parked P1–P5 findings, variable definitions, and dashboard as a user; record corrections or acceptance.
2. Review the D14–D21 and D25–D31 decisions and the F11 disagreements in `docs/FINDINGS_V4.md`.
3. Obtain human expert review of the ten fixed reports using `docs/F11_EXPERT_REVIEW_PACK.md`; do not manufacture responses.
4. Decide whether to pursue OR&R 42 map digitisation and recruit reviewers. Keep these as gates, not implied completed work.
5. Only after owner review, update the release checklist, run the full tests and any chosen validation commands, then decide whether to tag/publish. Do not claim F12 release or external validation before that happens.

## Useful commands

Python 3.11 was the recorded environment for the full test suite and dashboard check. The prior handoff records 177 tests passing; this wrap-up did not rerun them.

```bash
python -m pip install -r requirements-analysis.txt
python -m pytest tests
streamlit run src/shoreline_remediation/dashboard.py
python -m validation.f11_integrated_validation
```

Some analyses require local, git-ignored source data. In particular, DIVER and SCAT inputs are not guaranteed to be present in a fresh clone; see `docs/DATA_ACQUISITION.md`, `docs/F6_TREATMENT_RECORDS.md`, and `docs/F7_SECOND_SPILL_INVENTORY.md`. Do not commit restricted or locally held raw data.

## Documentation map

- Scope and decisions: [`docs/F0_F1_SCOPE_AND_DECISIONS.md`](F0_F1_SCOPE_AND_DECISIONS.md)
- Implementation plans: `docs/F2_F3_PLAN.md` through `docs/F11_INTEGRATED_VALIDATION_PLAN.md`
- Findings: [`docs/FINDINGS_V4.md`](FINDINGS_V4.md) and [`docs/REVIEW_NOTES.md`](REVIEW_NOTES.md)
- Data provenance: [`docs/DATA_CATALOGUE.md`](DATA_CATALOGUE.md), [`docs/VARIABLE_DICTIONARY.md`](VARIABLE_DICTIONARY.md)
- Final pipeline: `src/shoreline_remediation/decision_pipeline.py`
- Integrated validation outputs: `results/f11_validation/`
- Model promotion states: `models/registry.json`

This handoff is a concise current-state guide, not a replacement for the detailed plans, results, decision register, or source citations linked above.
