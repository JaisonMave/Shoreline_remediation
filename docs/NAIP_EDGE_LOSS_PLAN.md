# Analysis plan: marsh-edge loss after Deepwater Horizon oiling, from NAIP imagery

Written and committed on 11 November 2026, before any NAIP imagery was read. The model below will be run once.
Measurement problems found by the quality check in step 4 may be fixed before the model is run, without
looking at any outcome by oiling class. Anything changed after the run will be reported as exploratory.

## Question

Did heavily oiled salt-marsh edge in Barataria Bay lose more vegetated marsh after 2010 than nearby
edge where SCAT teams found no oil?

## Data

| Item | Source |
| --- | --- |
| Units | `scripts/build_edge_cells.py`: 100 m x 100 m grid cells (ASSUMED size) crossed by SCAT-surveyed shoreline, Barataria Bay box -90.15 to -89.75 E, 29.25 to 29.62 N. Oiling class = worst SCAT maximum-oiling category in the cell (NCEI Accession 0163818). |
| Habitat | Cells whose most frequent ESI code is 10A (salt marsh). |
| Imagery | NAIP (USDA), 4 bands including near-infrared, from Microsoft Planetary Computer. 2010 (flown 10 May to 31 July 2010), 2013 (27 Sep to 7 Oct), 2015 (30 Apr to 3 May), 2017 (8 to 12 Sep). No pre-2010 NAIP is reachable from here. |

## Measurement

1. NDVI = (NIR - red) / (NIR + red) from the raw NAIP values, read on a common 2 m UTM 15N grid (ASSUMED).
2. Land = NDVI at or above a threshold set by Otsu's method (the value that best separates the two peaks of
   the NDVI histogram, here vegetated marsh and water) on each NAIP tile and year, from a 16 m overview. NAIP
   brightness is not calibrated between flights, so a fixed threshold would not be comparable across years.
3. Land fraction f per cell and year. Edge loss in metres = (f_2010 - f_year) x 100 m, i.e. lost area divided
   by 100 m of shoreline per cell (ASSUMED: one shoreline crossing per cell). Annual rate = loss / years
   between the two flight dates of that cell.
4. Quality check before the model: view the land mask over imagery for several tiles and years; check that
   thresholds fall between plausible water and marsh values. Cells keep only if 0.1 <= f_2010 <= 0.9
   (ASSUMED: the cell holds an actual land-water edge in 2010) and every year has valid pixels.
5. Exposure covariate: open-water fraction within 1 km of the cell centre in 2010, from 16 m overviews.
   This uses only 2010 imagery, i.e. information fixed before the outcome.

Note: "land" means vegetated marsh. Marsh killed by oil but not yet eroded counts as lost. The outcome is
loss of vegetated edge, which mixes mortality and erosion.

## Model (primary, run once)

Salt-marsh cells, outcome = edge-loss rate 2010 to 2013 (m/yr):

    rate = class effects (Very Light, Light, Moderate, Heavy; NOO is the reference)
           + b * open-water fraction within 1 km
           + one intercept per 2 km block

Least squares; standard errors clustered by 2 km block (cells in one block are not independent).
The block intercepts mean each oiled cell is compared with clean cells in the same 2 km block.
Primary estimate: the Heavy coefficient, with a 90% interval.

Baselines reported alongside:
- the clean (NOO) cells' mean rate;
- the raw Heavy minus NOO difference with no covariates and no blocks.

Secondary: the same model for 2010 to 2015 and 2010 to 2017; the pattern across oiling classes (does loss
rise with oiling?).

## Benchmark

Zengel et al. (2015), same bay, 2011-2012 field measurements: shoreline retreat 2.4 to 3.1 m/yr on heavily
oiled untreated plots against 0.8 to 1.2 m/yr on reference plots, an excess of about 1.2 to 2.3 m/yr. The
check asks whether the Heavy coefficient's interval overlaps that range. It is not a pass/fail test: Zengel
measured a few plots on the most heavily oiled shoreline, and most heavily oiled cells here were also cleaned.

## Known limits

- No pre-spill image, so a difference in edge loss that predates the spill cannot be ruled out; the block
  intercepts and the exposure covariate reduce this but do not remove it.
- Tide level and season differ between flights; both classes in a block are usually on the same tile and
  flight, so this mostly cancels within blocks.
- Most heavily oiled marsh was treated in 2010-2011; the treatment applied to each cell is unknown here. The
  estimate is "heavy oiling plus whatever cleanup followed".
- Hurricane Isaac (August 2012) falls between the 2010 and 2013 flights.
- One spill: no hold-out across spills is possible.
