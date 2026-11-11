# P1 plan: was oiled shoreline already eroding faster before the spill?

Written and committed on 11 November 2026, before any Landsat value or new exposure value was computed.
Each check below is run once. Quality-check fixes made before the checks run are allowed and will be
listed as amendments; anything changed after is exploratory.

Milestone P1 of the proof-of-concept track (`claude/roadmap.md`). Module 4 (recovery prediction) and
Module 5 (reliability). Approved decisions this builds on: D2 (NAIP 2010-2015 primary), D5, D6.

## Why

The NAIP result (heavily oiled salt-marsh edge lost 1.00 m/yr more than clean edge in the same 2 km block,
90% interval 0.58 to 1.43, 2010-2015) has no pre-spill image. If the shoreline that later received heavy
oil was already eroding faster, part or all of the 1.00 m/yr is not caused by oil. Heavy oil landed on
exposed, wave-facing edges, and exposure drives erosion, so this is the main threat to the result.

## Units

The same salt-marsh (ESI 10A) edge cells as the NAIP analysis: `data/external/naip_edge/cells_10A.csv`,
kept if 0.1 <= 2010 NAIP land fraction <= 0.9 and NAIP valid pixels >= 90% in 2010 (the cell held an edge
in 2010). Oiling classes and 2 km blocks unchanged.

## Measurement: Landsat water fraction per cell

Source: Landsat Collection 2 Level-2 surface reflectance, Microsoft Planetary Computer, April-October
scenes with less than 30% cloud. Same sensor within each pre-spill epoch.

| Epoch | Years | Sensor | Scenes available | Mid-point |
| --- | --- | --- | --- | --- |
| A, early pre-spill | 1998-2000 | Landsat 5 TM | 74 | about 1999.6 |
| B, late pre-spill | 2007-2009 | Landsat 5 TM | 62 | about 2008.6 |
| C, post-spill | 2014-2016 | Landsat 8 OLI | 56 | about 2015.6 |

1. Short-wave infrared (SWIR1: TM band 5, OLI band 6). Water absorbs it strongly even when turbid; marsh
   reflects it. This avoids the turbid-water failure seen with NDVI on NAIP.
2. Per scene, land fraction of each 30 m pixel = (SWIR1 - water value) / (marsh value - water value),
   clipped to 0-1 (linear unmixing). Water and marsh values = medians of that scene's clear pixels that lie
   more than 60 m inside 2010 water or 2010 land (2010 NAIP classification, the one used in the NAIP
   analysis). Clouds, shadows and snow removed with the QA band.
3. Per epoch, per-pixel median of the scene fractions (reduces tide and noise), then warped to 10 m and
   averaged over each 100 m cell. A cell needs at least 5 clear scenes in an epoch (ASSUMED).
4. Edge loss rate (m/yr) = (land fraction at the earlier epoch - at the later) x 100 m / years between epoch
   mid-points, as in the NAIP analysis.

## Checks (all use the NAIP model form: oiling class + open water within 1 km + 2 km block, standard errors
clustered by 2 km block, 90% intervals)

1. **Instrument check.** Outcome: Landsat edge loss B -> C (2008.6 to 2015.6). If Landsat can see the
   effect NAIP found, the Heavy coefficient should be positive with an interval excluding zero. If it does
   not, Landsat is too coarse and checks 2 and 3 cannot be read as evidence either way.
2. **Pre-spill placebo.** Outcome: Landsat edge loss A -> B (1999.6 to 2008.6), before any oil. The Heavy
   coefficient should be near zero. Read together with check 1: a pre-spill coefficient whose interval
   excludes zero, or that is at least half the post-spill coefficient, means part of the post-spill
   difference predates the spill.
3. **Pre-spill-adjusted effect (difference in differences).** Outcome: (B -> C rate) minus (A -> B rate)
   per cell. The Heavy coefficient is the change in edge loss after the spill, net of each cell's own
   earlier trend.
4. **Finer exposure.** NAIP primary model (2010-2015) with two extra covariates fixed from 2010 NAIP only:
   open-water fraction within 250 m, and log of mean fetch (open-water distance to the first land, averaged
   over 16 compass directions, capped at 10 km, on a 16 m water mask). The Heavy coefficient is compared with
   1.00 (0.58 to 1.43).

Before running on real data, the analysis code is run on simulated cells with a known pre-existing trend
and a known oil effect, and must recover both.

## How P1 is judged (fixed now)

- **Holds:** check 1 positive (interval excludes zero), check 2 interval includes zero and its estimate is
  less than half of check 1, check 4 Heavy interval still excludes zero.
- **Revised:** check 1 positive but check 2 says part of the gap predates the spill; the check 3 estimate
  replaces 1.00 m/yr as the headline.
- **Inconclusive:** check 1 fails (Landsat cannot see the effect). Then the pre-spill question needs NAIP
  2007/2009 (P1 optional step for Jaison).

## Known limits

- 30 m Landsat pixels are coarse against 1 m/yr retreat (about 9 m over an epoch interval); averaging over a
  100 m cell and many scenes is what makes it possible, and check 1 tests whether it works.
- Landsat 5 and Landsat 8 differ; unmixing per scene against that scene's own water and marsh values puts
  both on the same 0-1 scale.
- Hurricanes Katrina and Rita (2005) and Gustav and Ike (2008) fall in the pre-spill interval; they affected
  both oiled and clean shoreline in each block.
- Interior points 60 m inside 2010 land may have been water in 1999 in places; the median over many pixels
  limits the effect.
