# Getting Real Outcome Data

> Update 11 November 2026: network egress now works. SCAT (section 2), Landsat (section 1, via Planetary
> Computer instead of Earth Engine) and Zengel 2015 (section 3) were obtained and analysed. See
> `docs/FINDINGS_2026-11-11.md`. The text below is the earlier plan, kept for reference.

The published marsh case table (63 cases) is too small for a predictive model, so the next gains have to come
from more outcome data. This session's network reaches GitHub only. Section 0 lists what was obtained
there; the sources in sections 1 to 4 have to be downloaded on your own computer.

## 0. Data already obtained (from GitHub, the only host this session could reach)

| Dataset | Where it is | What it is for |
| --- | --- | --- |
| NOAA ADIOS oil database (1,460 oils) | `data/oil_properties.csv`, built by `scripts/build_oil_table.py` from https://github.com/NOAA-ORR-ERD/noaa-oil-data | Measured API gravity, density, viscosity and pour point. `oil_library.py` looks an oil up by name and returns the tool's inputs, replacing a guessed oil category. |
| Louisiana marsh vegetation by site and year (341 CRMS sites, 2006-2025) | `data/external/crms/`, copied from https://github.com/anamikadristi/coastal-marsh-vegetation-extreme-events (MIT licence) | Field vegetation cover, MODIS NDVI and hurricane exposure per site. No oil information. A third party derived it from public CRMS data; it has not been checked here against the original CRMS export. |
| NOAA SCAT data standard | https://github.com/researchplanninginc/NOAA-SCAT-Standard (not copied) | Defines the tables and fields of SCAT survey data. Use it to write the loader once real SCAT data arrive. |

No repository on GitHub was found holding Deepwater Horizon shoreline oiling, cleanup records or Landsat
series for Barataria Bay. Those still need the steps below.

### What the marsh data showed (`python -m validation.marsh_event_study`)

The event-study method (`event_study.py`) was run on real data for two hurricanes, comparing sites inside
the 64-knot wind radius with the least exposed sites of the same marsh type.

| Storm | Outcome | Sites (exposed / comparison) | Pre-event check | Result |
| --- | --- | --- | --- | --- |
| Isaac 2012 | Vegetation cover | 116 / 143 | Passed (p = 0.25) | No detectable loss in the first three surveys (+1.9, +2.6, +1.1 points, all intervals include zero) |
| Isaac 2012 | NDVI | 107 / 143 | Failed (p = 0.008) | Not interpretable |
| Ida 2021 | Vegetation cover | 120 / 104 | Failed (p = 0.003) | About 15 to 17 points lower for at least three surveys, but exposed sites were already diverging, so the size is uncertain |
| Ida 2021 | NDVI | 110 / 104 | Failed (p < 0.001) | Not interpretable |

Reading: the method runs on real field data, and its pre-event check correctly refuses three of the four
comparisons. The one clean comparison says Isaac's winds did not measurably reduce vegetation cover at
these monitoring stations. That does not rule out the marsh-edge erosion other studies report after Isaac:
the plots measure vegetation cover where they stand, not shoreline retreat, and nothing in this dataset
says how close each plot is to the marsh edge. The 2010 spill oiled a narrow band at the edge, so check
plot positions before expecting these stations to detect it.

To use these sites for the spill, match each site's coordinates to the SCAT oiling layer (section 2) and
rerun the event study with oiled against unoiled sites.

## 1. Satellite recovery series for Barataria Bay (Project 5)

Needed: a Google Earth Engine account (free for research) and `pip install earthengine-api`.

1. Open the ERMA Gulf of America map (https://erma.noaa.gov/gulfofamerica/erma.html) and turn on the
   Deepwater Horizon SCAT shoreline oiling layer.
2. Pick a stretch of marsh edge in northern Barataria Bay mapped as heavily oiled, and a stretch nearby with
   the same vegetation and exposure mapped as unoiled. Digitise each as a narrow polygon along the edge
   (oiling was concentrated near the edge) that still holds at least 20 Landsat pixels.
3. Paste both polygons into `OILED` and `REFERENCE` in `scripts/gee_export_ndvi.py` and run it. It writes
   `ndvi_observations.csv`.
4. Run `python -m validation.satellite_recovery ndvi_observations.csv --spill-date 2010-04-20`.
   Add `--persistent` if the oiled edge may have eroded into open water.

What to expect: the runner reports the drop, years to 90% recovery with a 90% interval, a placebo check
(false spill dates should not find similar impacts) and whether the result agrees with Mo et al. (2017),
who found the major aboveground impact lasted about two years. Hurricane Isaac (August 2012) hit the same
marshes; if both sites were affected equally the reference cancels it, otherwise expect a second dip.

Repeat for several oiled/reference pairs. One pair is an anecdote; ten pairs start to be a dataset.

## 2. Deepwater Horizon shoreline oiling by segment

| Source | What it holds | How to get it |
| --- | --- | --- |
| NCEI Accession 0163818 (DOI 10.7289/v53t9ffx) | ERMA SCAT shoreline oiling layers, May 2010 to March 2014. Each line is a band of oil with similar coverage and thickness. | Files over HTTPS: https://www.ncei.noaa.gov/data/oceans/archive/arc0110/0163818/1.1/ (`scripts/download_scat.sh`). Downloaded 11 Nov 2026. |
| NCEI DIVER archive | Bulk archive of most Deepwater Horizon data held in DIVER, including field observations such as extent of oiling in marshes. | Linked as "direct download of data" from https://www.diver.orr.noaa.gov/deepwater-horizon-nrda-data/. |
| DIVER Explorer | Query and export of the same data. | Same page, "Search & Query DWH Data in DIVER Explorer". |
| Nixon et al. 2016, Mar. Pollut. Bull. 107(1):170-178 | Integrated segment database: 2,113 km oiled of 9,545 km surveyed, with habitat, oiling category and timing. | Ask the authors (Research Planning, Inc.) whether the segment database is shared. |

Once you have a file, send it here. I will write the loader against its real columns rather than guess them.

## 3. Treatment effects in oiled marsh

| Source | What it holds | Use |
| --- | --- | --- |
| Zengel et al. 2015, PLoS ONE 10(7):e0132324 | Heavily oiled Barataria Bay plots over two years: untreated, manual, mechanical, with and without planting. | The best field comparison of treatments. Manual treatment gave the best balance; mechanical treatment mixed oil into the soil and accelerated erosion; planting sped recovery. Extract the group means and errors from its tables to build treatment-effect priors. |
| Zengel et al. 2021, meta-analysis of salt marsh vegetation impacts and recovery after Deepwater Horizon (Ecological Applications, doi 10.1002/eap.2489) | A synthesis across Deepwater Horizon marsh studies. | Effect sizes by oiling degree and time since spill. |

The PLoS ONE paper is open access. This session could not open its full text, so its numbers have not been
extracted yet.

## 4. Beaches (later)

The Exxon Valdez pit-survey data behind Nixon and Michel (2015), Environ. Sci. Technol. 49(7), are the best
training set for a beach oil persistence model. Ask the authors or the Exxon Valdez Oil Spill Trustee Council.
