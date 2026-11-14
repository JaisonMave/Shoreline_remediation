# F11 integrated validation plan (14 November 2026)

Status: pre-run plan. This plan fixes the F11 replay and review-pack procedures before inspecting F11 outcomes. It does not change `decision_pipeline.py`.

## Question

Does the fixed F9 decision pipeline reproduce the documented decision direction and retain documented methods for six sourced historical cases, and how should its evidence-bound scope be presented? The small six-case set is descriptive, not a general validation estimate. A separate human panel will review ten reports; no responses will be invented.

## Data and provenance

- Historical source cases: DWH-01..05 and EVOS-01 from `validation/historical_validation.py` and `results/historical/`. Only pre-treatment inputs in its traceable case records are passed to `decide_case`/`run_decision`; documented treatment methods, decisions and outcomes are held back as labels.
- Unrecorded inputs use the historical-validation sampling convention: 40 reproducible Latin-hypercube draws, ASSUMED and logged. Seeds are fixed by case/draw.
- Held-out DWH heavy marsh-edge cells and their basin assignment are reused from C1c outputs. Composer-forecast coverage is cited from C1c/B1c and is not recomputed.
- V3 and V4-R2 comparison values are read from their preserved historical results.

## Methods

1. Run each historical case for 40 draws. Classify a report as **active** when at least one class-A option exists, otherwise **natural** when its headline says monitor. Compare the draw-level modal class with the documented decision direction. Report the always-active and majority-class baselines.
2. A documented method is allowed when a matching pipeline option occurs in class A or B and never E across the draw summary. Record methods excluded (class E) as review disagreements. Report case and pooled rates with Wilson 95% intervals.
3. For C1c held-out heavy marsh cells, call `run_decision`, summarise headline/class frequencies and how often planting and manual removal are class A; cite existing C1c/B1c coverage rather than recalculating it.
4. Produce a scope table from D30/F0, registry states, and the supporting validation records.
5. Create ten JSON recommendation reports: four existing F9 examples plus six deterministic new reports spanning habitats and oiling classes. The expert pack asks option-level class agreement, missing considerations and free text, without responses.

## Baselines

Always-active and majority-class historical classifiers. No alternative outcome model is fitted. Historical v3 and V4-R2 values are comparison context only and are labelled from their archived results.

## Gates and interpretation

Pass/fail is not a promotion gate: F11 passes operationally only if all six sourced cases, 40 draws each, outputs, Wilson intervals, baselines, cell summary, scope table and ten reports are produced. Any disagreement, exclusion, unavailable archived comparison, or pipeline error is retained and reported. Jaison's expert-panel review and sign-off remain required; six cases are too few to establish general performance.

## Outputs and reproducibility

`results/f11_validation/historical_replay.csv`, `metrics.csv`, `cell_replay_summary.csv`, `scope_table.csv`, `summary.txt`, `reports/`; `docs/F11_EXPERT_REVIEW_PACK.md`; focused metric tests in `tests/test_f11_validation.py`. Run once with Python 3.11 from repository root.
