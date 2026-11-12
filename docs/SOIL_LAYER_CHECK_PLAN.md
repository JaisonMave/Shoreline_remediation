# Plan: do national and global soil maps match measured marsh soil? (Stage 3a)

Status: **Approved to run once** (Jaison, 12 Nov 2026: "yes to all"). Written and committed before any
SSURGO or SoilGrids value was compared with a CRMS measurement. Only one point (lon -89.90, lat 29.45) was
queried from each service beforehand, to test that the services answer; it is excluded from nothing and
was not compared with CRMS.

## Question
The tool will meet sites with no soil cores. Can SSURGO (USDA soil survey) or SoilGrids (ISRIC global
250 m maps) stand in for measured soil properties in Louisiana coastal marsh? Tested against CRMS soil cores.

## Data
- **Measured:** CPRA CIMS `CRMS_Soil_Properties.zip` (downloaded 12 Nov 2026; 16,508 rows, 392 CRMS sites,
  2006-2023, coordinates included). Copied to `data/external/crms_soil/` with `SOURCE.md`.
- **SSURGO:** Soil Data Access (`sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest`), map unit at the site point.
- **SoilGrids v2:** read from the ISRIC cloud rasters (`files.isric.org/soilgrids/latest/data/`, VRT via
  rasterio) at the site point. If those cannot be read from here, fall back to the REST point service for
  a random sample of 100 sites (seed 20261112; the service allows about 5 calls a minute), and say so.
- Retrieved values are cached in `data/external/soil_layers/` so the comparison can be rerun offline.

## Unit of analysis
The **CRMS site** (first 8 characters of Station ID), never the core or depth slice. Site value = mean over
all cores and dates of depth slices whose top is shallower than 16 cm (0 to 16 cm; ASSUMED to match the map
products' 0 to 15 cm). Site position = mean of its core coordinates. Sites with no slice in that depth
range, or no coordinates, are dropped and counted.

## Variables and matching
| Variable | CRMS (measured) | SSURGO | SoilGrids | Note |
| --- | --- | --- | --- | --- |
| Bulk density, g/cm3 | Bulk Density | `dbthirdbar_r` | `bdod` (cg/cm3 / 100) | Same quantity, different method |
| Organic matter, % | Organic Matter | `om_r` | `soc` (dg/kg / 10 = g/kg), times 1.724 / 10 for % OM | 1.724 factor ASSUMED; known to be poor for organic soils. Also reported as SOC against CRMS OM / 1.724 |
| pH | Wet Soil pH | `ph1to1h2o_r` | `phh2o` (/10) | CRMS wet-soil pH vs 1:1 water: method differs |
| Salinity | Soil Specific Conductance, uS/cm / 1000 = dS/m | `ec_r` (dS/m, saturated paste) | not available | Different methods: **rank agreement only**, no bias or error reported |

SSURGO value: horizons clipped to 0-15 cm and thickness-weighted within each component, then weighted by
component percentage over components with a value. Map units with no soil value (water, miscellaneous) are
missing and counted. SoilGrids value: 0-5 cm and 5-15 cm layers weighted 1:2; the Q0.05 and Q0.95 layers
are kept.

## Analysis (run once)
For each variable and product, over sites with both values:
1. n sites; number missing and why.
2. **Baseline:** predict every site with the median measured value (no map). MAE of that.
3. Bias (map minus measured), MAE, RMSE, Spearman rank correlation, Lin's concordance correlation.
4. MAE of the map minus MAE of the baseline.
5. SoilGrids only: share of measured site values inside the map's Q0.05 to Q0.95 range (should be near 90%).
6. 90% intervals for every statistic by bootstrap over sites (2,000 resamples, seed 20261112).
7. Secondary, same statistics: sites inside the P5 training box (lat 29.05-30.32, lon -91.14 to -89.38).

No model is fitted; no map value is recalibrated to CRMS.

## Pre-specified reading (thresholds ASSUMED, fixed here)
| Result for a variable and product | Verdict |
| --- | --- |
| Spearman at least 0.5 with lower bound above 0.3, **and** map MAE below baseline MAE with the interval of the difference excluding zero | Usable as a predictor where no core exists |
| Spearman lower bound above 0 but the rest not met | Weak: ranks sites roughly; do not use the values |
| Otherwise | Not usable in marsh |

## Limits known in advance
Core dates (2006-2023) and map dates differ. CRMS sites sit in marsh interiors, not on the oiled edge.
SoilGrids was trained mostly on upland profiles and is 250 m; SSURGO marsh map units are broad. A site's
cores may lie in different map pixels. Agreement in Louisiana says nothing about other coasts.
