# CHECK: numbers used and their source files

Numbers were taken from the files named; rounding is from CSV or model-card values. Slide ids refer to root/project/slides/<id>.html.

| Slide | Numbers | Source |
| --- | --- | --- |
| tool-claim | 1.35, 1.47, 89%, 81 to 94% | results/p2_basin_holdout/pooled.csv; results/scenario_composer/*coverage*.csv |
| tool-io | 39,320; 12,696; 1,460; 0.34 to 0.83 | docs/FINDINGS_2026-11-11.md sections 8, 10; results/p2_basin_holdout/oil_effect_transfer.csv |
| tool-scoreboard | 1.35, 1.47; 0.85 (0.49 to 1.22); 0.42 to 0.85; 0.42/0.28; -1.47 (-2.06 to -0.88); 3.0 y; 1.6 y | results/p2_basin_holdout/pooled.csv; results/p1_prespill/checks.csv; results/period_split/A1.csv; results/p3_treatment/A_prespill_adjusted.csv; results/veg_recovery/summary.csv; results/pah_decline/by_oiling_class.csv; results/mangrove/summary.csv |
| changed-numbers | 1.00, 0.85, 0.49-1.22, 0.42-0.85, 1.33, 1.47, 1.30, 1.42, 1.35 | docs/FINDINGS_2026-11-11.md 6, 7, 10, 12; results/p2_basin_holdout/pooled.csv; models/p5_edge_loss_v1.json |
| changed-analyses | 14,926; 202; 16,508; 392; 1,158; 10 studies; 54 rows | docs/STAGE2_INVENTORY.md; docs/FINDINGS_2026-11-11.md 13, 17 |
| changed-tool | 108 to 167 tests; D1-D13 to D1-D24 | CHANGELOG.md; docs/ROADMAP.md |
| data-overview-1 | 5,721; 15,984; 1,044; 341; 16,508; 392; 86; 33; 1,158; 10 | docs/DATA_CATALOGUE.md; docs/STAGE2_INVENTORY.md; docs/FINDINGS_2026-11-11.md 1, 3, 9 |
| data-overview-2 | 46; 22/24; 1,460; 63; 14,926; 202; 1,870; 25 files; 488; 12; 3 of 9 | docs/STAGE2_INVENTORY.md; docs/DATA_CATALOGUE.md |
| data-overview-3 | 392; 302; 54; 1.11 GB; 2009-09-02 | results/soil_layer_check/summary.txt; docs/STAGE2_INVENTORY.md; data/knowledge/treatment_evidence_untested.csv |
| data-scat | 5,721; 15,984; 7,077; 65 MB | docs/FINDINGS_2026-11-11.md 1; docs/DATA_CATALOGUE.md EXT-SCAT |
| data-scat-cells | 39,320 cells; 100 m | docs/FINDINGS_2026-11-11.md 8 |
| data-naip | 2010, 2013, 2015, 2017; 2019, 2021, 2023; 2, 8, 16 m | docs/FINDINGS_2026-11-11.md 5; docs/DATA_CATALOGUE.md EXT-NAIP |
| data-naip-photos | 59.4%, 52.0%, 1.54 m/yr, 69 m | data/external/p2/barataria/cell_land_by_year.csv; docs/P5_WORKED_EXAMPLE.md |
| data-naip-problems | 406 cells; 0.4; 1.2 m/yr; 0.2 vs 0.8-1.2 | docs/FINDINGS_2026-11-11.md 6, 8, 9 |
| data-landsat | 1,044 scenes; 26,529; 52-69; r 0.68/0.73 | docs/FINDINGS_2026-11-11.md 3, 7 |
| data-crms | 341; 2006-2025; 200 m; 4 of 20 within 50 m; 16,508; 392; 2006-2023 | docs/DATA_CATALOGUE.md; docs/FINDINGS_2026-11-11.md 2 |
| data-zengel | 33 plots; 5/9/5/9/5; 5 to 9 per group; 86 values | docs/FINDINGS_2026-11-11.md 4, 9; docs/DATA_CATALOGUE.md |
| data-zengel-meta-turner | 1,158; 255; 10; 810/348; 37 units; 46; 41; 22/24 | docs/STAGE2_INVENTORY.md; results/veg_recovery/summary.txt |
| data-oils-cases | 1,460 oils; 63 cases; API -37.2 | docs/DATA_CATALOGUE.md; docs/REVIEW_NOTES.md B0 |
| data-diver | 14,926; 202; 60 columns; 30% no limit; 0.5 GB | docs/STAGE2_INVENTORY.md; docs/REVIEW_NOTES.md E00 |
| data-diver-read | 1,697; 58; 12; 200; 125; 144; 612; 0.3% | docs/FINDINGS_2026-11-11.md 22; results/pah_decline/processing_log.txt |
| data-galeta | 1986; 1987-1992; 11-14 sites; 25 files; 2 unoiled seedling sites | docs/FINDINGS_2026-11-11.md 16, 20 |
| data-other-gulf | 488; 12; 11 sampling days; 1,152 days; six depths | docs/STAGE2_INVENTORY.md |
| data-soil-layers | 392 sites; 90 masked; 302 | docs/FINDINGS_2026-11-11.md 13 |
| data-evidence | 54 rows | data/knowledge/treatment_evidence_untested.csv |
| data-synthetic | 30 scenarios | data/expert_scoring_sheet.csv |
| data-reproduce-1 | 167 tests; 4 GB; Python 3.13 | CHANGELOG.md; docs/REVIEW_NOTES.md D |
| data-reproduce-2 | command list | CHANGELOG.md; scripts/*.sh; docs/*_PLAN.md |
| data-quality | 449 MB; 183 MB; 1.11 GB; 65 MB; 2%; 45 variables | docs/STAGE2_INVENTORY.md; docs/DATA_CATALOGUE.md; docs/VARIABLE_DICTIONARY.md |
| an-event-study | 20/24; +7.9 (-2.5 to 18.4); NDVI +0.06 (-0.01 to 0.13); 203 m; p=0.106; 18 of 20 vs 5 of 25 | results/oil_event_study/summary.csv; docs/FINDINGS_2026-11-11.md 2 |
| an-landsat | +0.025 (-0.057 to 0.113); +0.021 (-0.179 to 0.272); 0.025-0.062; 14-115 y; 34 vs 4; 1,044 | results/satellite/estimate.json; results/satellite/secondary/summary.csv |
| an-naip | 4,779; 524/2,951; 176; 1.00 (0.58-1.43); 1.01 (0.65-1.38); 0.69 (0.28-1.11); 0.22; 3.5 | results/naip_edge_loss/coefficients.csv; docs/FINDINGS_2026-11-11.md 6 |
| an-p1 | 1.00; 1.15; 0.30; 0.85 (0.49-1.22); 0.47; 0.62; 0.72; 0.10 | results/p1_prespill/checks.csv; results/p1_prespill/exploratory.csv |
| an-period | 0.42 (0.07-0.76); 0.28 (-0.27-0.84); -0.14 (-0.80-0.52); +0.78 (0.02-1.53); 4,241; 159 | results/period_split/A1.csv; A2.csv; A3.csv |
| an-p2-setup | 39,320; 12,696; 4,104/5,386/3,206; 501 heavy; 31; 20 | docs/FINDINGS_2026-11-11.md 8 |
| an-p2-result | 1.47/1.33/1.35/1.41; skill 8%; coverage 90/88/89%; 0.83 (0.37-1.30); 0.37 (0.03-0.70) | results/p2_basin_holdout/*.csv; docs/FINDINGS_2026-11-11.md 8 |
| an-p3 | +1.88 (1.57-2.20); +0.21; -0.63; +0.28; -1.47 (-2.06 to -0.88); 0.68 (0.30-0.91); 1.2 | results/p3_treatment/A_prespill_adjusted.csv; C_naip_check.csv |
| an-p5 | 12,696; 1.30 vs 1.42; -3.2 to +2.9; 1.42 (-1.74 to 4.30); 1.31; 1.54; 0.34-0.83 | models/p5_edge_loss_v1.json; docs/P5_WORKED_EXAMPLE.md |
| an-soil | 0.15 (0.06-0.24); 0.20 vs 0.11; 1.06 vs 0.10; -0.13; 0.20; 0.21; 392; 13% | results/soil_layer_check/agreement.csv; summary.txt |
| an-veg | 0.417 vs 0.450; -0.032 (-0.144 to 0.082); A 1.15; tau 1.8 (0.5-4.5); 3.0 y (1.2-5.2); 4 of 9; +0.088; 37 units; 9 studies | results/veg_recovery/summary.csv; summary.txt |
| an-composer | 5,000 draws; +1.88 (1.57-2.20); +0.21 (-0.56-0.97); 8 years | src/shoreline_remediation/scenario_composer.py; results/p3_treatment/A_prespill_adjusted.csv |
| an-coverage | 94%/81%; 88%/93%; 92%; 94%; 1.48 vs 0.94; 17% narrower; 4.8 vs 5.7 | results/scenario_composer/*.csv; docs/FINDINGS_2026-11-11.md 15, 18, 19 |
| an-paired | 4.7 ha (-5.7 to 12.8); -2.5 (-4.3 to -0.8); -0.6 (-1.5 to 0.4); -0.2 (-1.2 to 0.6); 46 cells; 16.9/14.9/16.1/8.1 m; 0.86/0.67/0.99 | results/scenario_composer/worked_block.csv; docs/FINDINGS_2026-11-11.md 15, 18 |
| an-pah | 0.592 vs 0.631; -0.039 (-0.066 to -0.010); 1.6 (1.2-2.4); 1.8 (1.2-3.3); 2.9 (1.6-8.7); 0.429 vs 0.450; 200 stations; 684 | results/pah_decline/by_oiling_class.csv; summary.csv |
| an-mangrove | 0.044 vs 0.072; -0.028; 0.00, +0.07, +0.12, +0.17, +0.18; 0.91 vs 1.16; -0.8,-1.2,-1.7; +0.9 (-1.0 to 2.7); 11/12; 12/14 | results/mangrove/summary.csv; effect_by_year.csv |
| an-expert | 0.6-1.2; 0.7-1.2; 0.9-1.8; 1.0-2.0; 1.0-1.8; 54 rows | data/knowledge/elicited_priors.csv |
| an-expert-result | 0.77; 0.70; 0.58-0.60; 0.05 | results/scenario_composer/worked_example_elicited_summary.csv |
| an-recovery-fail | -0.021; 0.012; 0.001; -0.004; SE 0.045/0.044/0.072/0.103 | results/recovery/cv_scores.csv |
| an-uncertainty | -3.2 to +2.9; 5,000; 89%; 81-94%; 89-90% | models/p5_edge_loss_v1.json; results/* |
| tool-install | Python 3.11; streamlit>=1.67 | requirements.txt, run_shoreline_dashboard.bat |
| tool-bj-1 | 0.87, 0.81, 3,638 m, 0.58 m/yr, 69 m | docs/P5_WORKED_EXAMPLE.md |
| tool-bj-2 | 1.42, -1.74 to 4.30, 1.54, 1.31, 0.34 to 0.83, 0.85 (0.49 to 1.22) | docs/P5_WORKED_EXAMPLE.md |
| tool-bj-3 | block 400_1630 differences in ha, 46 cells, 29 heavy | results/scenario_composer/worked_block.csv |
| sl-table | 89%, 1.30, 1.42, 6 m/yr, 5 to 9 plots, 1.6 to 1.8 y, 31 heavy cells, 167 tests, 80-97% gate | results/p2_basin_holdout/verdict.txt; docs/REVIEW_NOTES.md; CHANGELOG.md |
| sl-failed | 63 cases; +0.025 (-0.057 to 0.113); 20 vs 24; 3 of 4; 392 sites; 0.42, 0.28 | docs/HANDOFF.md; docs/REVIEW_NOTES.md; FINDINGS 12, 13, 22 |
| co-conclusions | 0.85 (0.49 to 1.22); 0.42 to 0.85 | docs/ROADMAP.md D9a |
| co-recs | 0.5 m/yr over-prediction; bias +0.534 m/yr for heavy cells | results/scenario_composer/summary.txt B1 |
| app-files | 167 tests | CHANGELOG.md |
