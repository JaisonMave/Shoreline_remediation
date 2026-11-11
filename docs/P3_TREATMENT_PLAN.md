# P3 plan: cleanup treatment and marsh-edge erosion

Written and committed on 11 November 2026, before any comparison between treatment groups was computed.
Each analysis below is run once. Milestone P3 (`docs/ROADMAP.md`); Modules 3 and 4.

## Part 1. Data search (done before this plan)

Goal from the roadmap: segment-level cleanup records to split the NAIP edge cells by cleanup method.

| Source checked | What it holds | Usable for a segment-level split? |
| --- | --- | --- |
| NCEI Accession 0163818 (all four layers) | SCAT oiling observations; fields include oiling, ESI and dates, no treatment fields | No |
| NCEI DIVER archive, Shoreline, `CWV-MarshResponseCleanupAreas` Feb/Spring/Fall 2011 | 14 staked NRDA sites in Bay Jimmy (zones B, C, D, E, H, I): plot cover, oiling height and extent, erosion notes | No: no field records whether or how a site was treated |
| NOAA Technical Memorandum NOS OR&R 42 (Zengel and Michel 2013) | Treatment history under STR S3-045 (11 km treated, Feb to Sep 2011) and S4-032; zones treated named | No: treated stretches are shown only as map figures; no segment table |
| Gibeaut, DWH administrative record DWH-AR0270436 | 20 control-impact pairs, aerial photos fall 2010 to spring 2013: treated heavy-oiled sites eroded 1.36 m/yr vs 0.94 m/yr at nearby untreated, less-oiled controls (difference 0.41 m/yr, p = 0.029) | Benchmark only (published summary; oiling and cleanup confounded) |
| Zengel et al. 2022, Sci. Rep. 12:13802, data at GRIIDC doi:10.7266/VF524143 (CC0) | Plot-level erosion by treatment group: aerial-photo erosion 1956-2018 (33 plots), field erosion 2010-2016, wave power, soil shear strength, GPS positions | Yes, at plot level (not segment level) |

Conclusion of the search: no public, machine-readable record of which shoreline segments were cleaned and how
was found. The segment-level split of the NAIP cells is therefore **not possible** with open data. Digitising
the treated stretches from the memorandum's maps is possible but imprecise; it is listed as an option for
Jaison, not done here.

What was seen before writing this plan: the readme, group counts per sheet, and the first seven rows of each
sheet (printed while checking the file structure). No group means or comparisons were computed.

## Part 2. Analyses on the Zengel et al. (2022) plot data (fixed now)

Groups (as labelled in the data): REFERENCE (unoiled), UNTREATED (oiled, natural recovery), TREATED - MANUAL,
TREATED - MECHANICAL, TREATED - PLANTED (mechanical treatment then planting). Baseline for every treatment
contrast: UNTREATED. Units: plots (rates in m/yr, positive = erosion). Each plot's DSAS value is already the
mean over its transects.

**A. Treatment effect on erosion, pre-spill adjusted (primary).** Aerial-photo (DSAS lumped) rates. Per plot:
change = rate(2010-2012) minus rate(2005-2010). Contrasts against UNTREATED for MANUAL, MECHANICAL and PLANTED,
and UNTREATED against REFERENCE (the oiling effect). Welch two-sample t, 90% interval (the same method as
`treatment_effects.py`). Secondary: the same for 2012-2018 minus 2005-2010 (longer term).

**A2. Wave-power sensitivity.** change ~ group + log(weighted mean wave power for the same period), least
squares with heteroskedasticity-robust (HC3) standard errors.

**B. Field-measured erosion (secondary).** Per plot, mean annual erosion over 2010-2016 from the field
sheet (years available per plot); Welch contrasts against UNTREATED. Mechanical plots have only 2 field plots
before 2014, so B is weak for mechanical.

**C. Check of the NAIP edge-loss measurement against field data.** Each plot's mean GPS position is placed in
the 100 m edge-cell grid. For plots in a cell with a NAIP 2010-2015 edge-loss rate (P2 Barataria data, same
filters), compare the cell rate with the plot's aerial-photo erosion over 2010-2015 (DSAS annual periods
2010-2011, 2011-2012, 2012-2013, 2013-2015, weighted by years). Spearman rank correlation with a 90% bootstrap
interval (2,000 resamples of plots, seed 0). NAIP "tracks" field erosion if the interval excludes zero. Also
the mean difference (NAIP minus plot). Caveat fixed now: plots are about 6 m of shoreline inside a 100 m cell,
so agreement can only be partial.

**D. Tool priors.** Results of A (with intervals) are added to `treatment_effects.py` as erosion priors,
scoped to heavily oiled Spartina marsh, northern Barataria Bay, and labelled as from one study site.

## Known limits

- One site (Bay Jimmy, northern Barataria Bay); 5 to 9 plots per group; treatments not randomly assigned
  except planting; the plots overlap the Zengel et al. (2015) study, so A and the existing vegetation priors
  are not independent evidence.
- Mechanical plots were the most heavily oiled; mechanical effects are confounded with oiling severity.
- Gibeaut's benchmark and P1 both measure heavy oiling plus cleanup together; neither isolates cleanup.
