# F4 plan: common multi-site data schema (D14)

Status: **Pre-specified plan, written before running the schema loaders or computing reconciliation outputs (14 November 2026).**
References: `docs/TRACK_F_BRIEF.md`, `docs/ARCHITECTURE_FOUNDATION.md` (section D14), `docs/V4_PROGRAMME_PLAN.md` (F4).

## 1. Question

Can the existing multi-source project datasets (Zengel 2015 and 2022 marsh field plots, NAIP and P2/P5 salt-marsh edge cells, DIVER coastal wetland soil chemistry, and Galeta mangrove if raw files exist locally) be mapped into the five-table D14 common schema (`source`, `site`, `event`, `observation`, `intervention`) without modifying any original data files, while strictly enforcing D14 validation rules and reconciling row counts, site counts, and key value checksums/summaries against the existing per-analysis tables?

## 2. Data inputs (read-only; originals untouched)

1. **Zengel et al. (2015)** (`EXT-ZENGEL2015` / `DER-ZENGEL2015`):
   - `data/external/zengel2015/zengel2015_S1_Table.xlsx` and `data/external/zengel2015/zengel2015_group_means.csv` (86 group-year-metric rows across `main`, `planting`, and `pre_treatment`; 83 numeric means and 3 `ND` rows).
   - Plot-group sites in Bay Jimmy (northern Barataria Bay, LA) have no individual coordinates in the S1 supplement (`coordinate_quality = "none"`).
   - Interventions: `manual_removal` and `mechanical_removal` in `main`/`pre_treatment` are observational (`assigned = "chosen"`), whereas `planting` (Spartina planting after mechanical cleanup) was randomly assigned (`assigned = "randomized"`), per `treatment_effects.py` and `docs/FINDINGS_2026-11-11.md` sections 4 and 9.
2. **Zengel et al. (2022)** (`EXT-ZENGEL2022`):
   - `data/external/zengel2022/zengel2022_griidc_erosion.xlsx` (`DSAS lumped`, `DSAS annual`, `GIS field erosion`, `GIS field erosion points`, `Wave Power`, `Shear strength`) and `data/external/zengel2022/SOURCE.md`.
   - 33 plots in DSAS sheets (`REFERENCE`: 5, `UNTREATED`: 9, `TREATED - MANUAL`: 5, `TREATED - MECHANICAL`: 9, `TREATED - PLANTED`: 5); 25 plots have GPS coordinates in `GIS field erosion points` (`coordinate_quality = "gps"`), and 8 plots (`6A`–`6E`, `19-20`, `20-21`, `22-23`) lack GPS rows (`coordinate_quality = "none"`).
   - Interventions: manual and mechanical cleanup rows carry `assigned = "chosen"`; planted plots (`TREATED - PLANTED`, `6A`–`6E`) carry `assigned = "randomized"`.
3. **NAIP and P2/P5 salt-marsh edge cells** (`DER-NAIP-EDGE`, `DER-P2`, `DER-P5`):
   - `data/external/naip_edge/cells_10A.csv` (9,160 Barataria box cells) and `data/external/naip_edge/cell_land_by_year.csv` (36,640 cell-year rows for 2010, 2013, 2015, 2017).
   - `data/external/p2/la_cells_basins.csv` (45,404 Louisiana SCAT cells across Barataria, Breton, Terrebonne, Birdfoot) and `data/external/p2/{terrebonne,barataria,breton}/{cells_10A.csv, cell_land_by_year.csv, exposure.csv, landsat_cell_fraction.csv}` (34,729 10A cells in the 3 non-delta basins; 69,458 cell-year rows for 2010 and 2015).
   - Reconciled against `results/naip_edge_loss/summary.csv` (4,779 primary 2010–2015 cells; 4,727 secondary 2010–2017 cells) and `data/demo/p5_sites.csv` (45,404 total cells; 12,696 `in_scope` cells).
4. **DIVER coastal wetland soil chemistry** (`EXT-DIVER-WETLAND`):
   - `data/external/diver_dwh/extracted_csv/cwvp_{Fall2010,Spring2011,Fall2011,Fall2012,Fall2013}_samples.csv` and `data/raw/scat/18611/SCAT_Max_OilZones_Louisiana_2014_09_30Sorted.shp`, read using `src/shoreline_remediation/diver_soil.py`.
   - Reconciled against `docs/DIVER_SOIL_STRUCTURE.md` (330,464 soil rows; 14,926 soil samples) and `results/pah_decline/processing_log.txt` / `results/pah_decline/station_campaign.csv` (127,585 filtered PAH+hopane rows; 1,698 PAH/hopane samples; 200 stations; 100,181 resolved sample-compound keys across 58 PAH analytes + hopane; 24,705 non-detect compound observations; 1,697 complete-compound sample sums; 684 station-campaign-depth rows).
5. **Galeta mangrove** (`EXT-GALETA`):
   - Check default destination from `scripts/download_galeta.sh`: `data/raw/galeta_ncei_9400033/data`.
   - If raw files exist locally, map site-visit records; otherwise record `"not loaded: raw data absent"` in `source.csv` (`method_read`) and in `results/f4_schema/reconciliation.csv`.

## 3. Method and schema rules (`src/shoreline_remediation/schema.py`)

### 3.1 Five tables and columns (D14)
- `source`: `source_id`, `citation`, `doi`, `licence`, `acquired`, `method_read`, `checksum`
- `site`: `site_id`, `source_id`, `lat`, `lon`, `datum`, `coordinate_quality`, `region`, `spill_id`, `habitat`, `zone`, `geometry_type`
- `event`: `event_id`, `site_id`, `date`, `date_precision`, `method`, `campaign`
- `observation`: `event_id`, `variable`, `value`, `unit`, `original_value`, `original_unit`, `matrix`, `depth_top`, `depth_bottom`, `basis`, `censor_flag`, `detection_limit`, `qualifier`, `lab_method`, `value_type`
- `intervention`: `site_id`, `treatment`, `start`, `end`, `intensity`, `assigned`, `source_id`

### 3.2 Validation rules enforced by `validate(table_name, df)`
1. **Dictionary membership**: Every `observation.variable` must exist in `data/meta/variable_dictionary.csv` or `data/meta/schema_variables.csv`. Unknown variables raise `ValueError`.
2. **Unit conversion and provenance**: Units are converted on load via `convert_units(df)` to the dictionary's canonical unit for each variable while keeping `original_value` and `original_unit`. Any row whose `unit` disagrees with the dictionary canonical unit raises `ValueError`.
3. **Censoring integrity**: `censor_flag` must be in `{"measured", "below_detection", "between_limits", "no_limit_available"}` (or space-separated equivalents). For left-censored rows (`below_detection` / `below detection`), `value` is **never** stored as `0` and **never** equal to `detection_limit`. Raw left-censored observations store `value = NaN` (keeping the raw reported string/number in `original_value`); any Tobit/regression-imputed value is explicitly labelled `value_type = "assumed"` or `"modelled"` and verified not to equal `0` or `detection_limit`.
4. **Value type**: `value_type` must be in `{"measured", "derived", "modelled", "assumed"}`.
5. **Coordinate quality and spatial-join gate**: Sites missing `lat` or `lon` are permitted only when `coordinate_quality == "none"`. Sites with `coordinate_quality == "none"` must have `lat`/`lon` empty (`NaN`) and are barred from spatial joins by `filter_spatial_sites(site_df)`.
6. **Intervention assignment**: `assigned` must be in `{"randomized", "chosen", "unknown"}`.

### 3.3 Output locations
- Small committable tables (Zengel 2015/2022 + NAIP/P2/P5 edge cells; each CSV < 20 MB): `data/schema/{source,site,event,observation,intervention}.csv`.
- DIVER-derived tables (git-ignored due to DIVER licence and size): `data/schema_local/{source,site,event,observation,intervention}.csv`, with `data/schema_local/` appended as one line to `.gitignore`.
- Reconciliation report: `results/f4_schema/reconciliation.csv`.

## 4. Baseline, gate, and pass/fail rule

- **Baseline**: Current per-analysis files (`data/external/zengel2015/zengel2015_group_means.csv`, `results/p3_treatment/A_prespill_adjusted.csv`, `results/p3_treatment/B_field.csv`, `results/p3_treatment/C_naip_check.csv`, `results/naip_edge_loss/summary.csv`, `data/demo/p5_sites.csv`, `docs/DIVER_SOIL_STRUCTURE.md`, `results/pah_decline/processing_log.txt`, `results/pah_decline/station_campaign.csv`).
- **Gate (run once)**:
  1. All 5 tables in `data/schema/` and all 5 tables in `data/schema_local/` pass `validate(table_name, df)`.
  2. **Zengel 2015**: 86 observation rows (83 numeric + 3 `ND`), max absolute difference of group means against `zengel2015_group_means.csv` $\le 10^{-9}$.
  3. **Zengel 2022**: 33 DSAS plots (25 with GPS, 8 with `coordinate_quality = "none"`), 165 `DSAS lumped` rows, 165 `DSAS annual` rows, 132 `GIS field erosion` rows, 17 `Shear strength` rows; pre-spill-adjusted group change means (2010–2012 and 2012–2018 minus 2005–2010) and field 2010–2016 means match `results/p3_treatment/A_prespill_adjusted.csv` and `B_field.csv` within $10^{-4}$. Raw sheet `PLOT_ID` string discrepancies (`Wave Power` spaces around hyphens on 4 plots; `Shear strength` reversed hyphenated plot numbers on 4 plots) are reported plainly in `results/f4_schema/reconciliation.csv`.
  4. **NAIP edge cells**: 45,404 total Louisiana cells and 12,696 `in_scope` cells (and sum/mean of `observed_rate`) match `data/demo/p5_sites.csv` within $10^{-6}$; Barataria `naip_edge` filtered cell counts (4,779 in 2010–2015; 4,727 in 2010–2017), per-oiling-class cell counts, and `noo_mean_rate` (0.215 and 0.249 m/yr) match `results/naip_edge_loss/summary.csv`.
  5. **DIVER soil chemistry**: 330,464 soil rows and 14,926 soil samples match `docs/DIVER_SOIL_STRUCTURE.md`; 127,585 filtered PAH+hopane rows, 1,698 PAH/hopane samples, 200 stations, 100,181 resolved sample-compound observations, 24,705 `below_detection` PAH observations (0 stored as zero or limit), 1,697 complete sample sums, and 684 station-campaign-depth rows (plus median `pah_sum` and `ratio` checksums) match `results/pah_decline/processing_log.txt` and `results/pah_decline/station_campaign.csv` within $10^{-6}$.
  6. **Galeta**: status recorded as `"not loaded: raw data absent"` if `data/raw/galeta_ncei_9400033/data` is absent.
- **Pass/fail rule**: Pass if all 6 gate checks reconcile within tolerance and any source-level mismatches (such as Zengel 2022 sheet `PLOT_ID` formatting differences and Galeta raw data absence) are reported plainly in `results/f4_schema/reconciliation.csv`.
