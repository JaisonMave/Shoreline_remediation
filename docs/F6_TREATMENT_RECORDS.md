# F6: Deepwater Horizon treatment records at scale

Inventory 14 November 2026. Plan: `docs/F6_F7_PLAN.md`. URL log:
`results/f6_f7/url_checks.csv`. No modelling.

**Question:** is there a public, machine-readable record of treatment method per
shoreline segment for Deepwater Horizon, or only map figures?

**Answer:** no public segment-level treatment GIS/CSV was found in the sources
checked. The only spatially explicit treatment history still in the open
literature is map figures in NOAA Technical Memorandum NOS OR&R 42 (northern
Barataria Bay). DIVER “Marsh Response Cleanup Areas” files are 14 Bay Jimmy
NRDA plots with oiling and cover, not treatment method. SCAT layers are oiling
only. This matches the P3 search (`docs/P3_TREATMENT_PLAN.md` and FINDINGS
section 9) and does not overturn it.

## 1. NOAA Technical Memorandum NOS OR&R 42 (verified)

| Field | Value |
| --- | --- |
| Exact title | Deepwater Horizon Oil Spill: Salt Marsh Oiling Conditions, Treatment Testing, and Treatment History in Northern Barataria Bay, Louisiana (Interim Report October 2011) |
| Authors | Zengel, Scott A.; Michel, Jacqueline |
| Series | NOAA Technical Memorandum NOS OR&R 42 (library also styles NOS-OR&R 42) |
| Date | April 2013 (subtitle: interim report October 2011) |
| Landing page | https://repository.library.noaa.gov/view/noaa/380 |
| PDF | https://repository.library.noaa.gov/view/noaa/380/noaa_380_DS1.pdf |
| Size | 16.89 MB on the library page; PDF header `/L 17713154` |
| Licence | CC0 1.0 (library page) |
| SHA-512 (library) | f507933e82aacd26f2e86fee68d7fae8d92b6ff36cf45d36f90cf2e81ebcb45f7c444911ef3c14ba731ab6ebe85528deae5f48200d7905c74e8c99dd609820c2 |
| HTTP here | Browser landing **200**. curl/Python **403**. Playwright PDF download **aborted**. File not saved. Script: `scripts/download_orr42.ps1` |

Cite as on the PDF title block (search-indexed text): Zengel, S. and J. Michel
(2013). … NOAA Technical Memorandum NOS OR&R 42. Seattle, WA: Emergency
Response Division, NOAA. 74 pp.

### Figures that show treated stretches (from the PDF list of figures)

Indexed from the NOAA IR PDF text (not from a local file):

| Figure | Caption | Page |
| --- | --- | ---: |
| 35 | STR S3-045 potential treatment and test areas (zones) | 58 |
| 36 | STR S3-045 treatment areas (yellow) and final potential treatment zones (red) | 62 |
| 37 | Mechanical treatment platforms (equipment photos, not a map) | 63 |
| 38 | Mechanical tools (examples) | 64 |
| 39 | Map of set-aside (no treatment) locations | 68 |
| 40 | Tulane/NSU marsh planting study plots … STR S3-045, Zone K, November 2011 | 70 |

P3 already named Figures 35, 36 and 39. Figure 40 is planting plots, not the
full treated shoreline. STR S3-045: about 11 km treated, February–September
2011 (P3 / FINDINGS section 9). No accompanying shapefile is cited on the
library record.

## 2. Other public sources checked

| Source | URL / path | HTTP | What it holds | Segment treatment method? |
| --- | --- | --- | --- | --- |
| NCEI SCAT 0163818 | doi:10.7289/v53t9ffx ; archive `…/0163818/1.1/data/0-data/` | 200 | Layers 18611 Houma max oiling; 18612 all ground surveys; 18613 cumulative oiling; 18614 Mobile max oiling | No (oiling only; P3 already read these) |
| NCEI shoreline 0163814 | doi:10.7289/v5mw2fcq | landing 000/301 from curl; archive folder 200 | Shoreline oiling miles, exposure model, wetland vegetation, shoreline change | No treatment layer in the index |
| DIVER archive root | https://www.ncei.noaa.gov/data/deepwater-horizon-diver-system/archive/ | 200 | 15 top-level folders, no sizes on the index | See §3 |
| DIVER Shoreline / CWV-MarshResponseCleanupAreas (Feb/Spring/Fall 2011) | under `…/archive/Shoreline/` | 200 | FieldObservations tars 2.8–3.2 MB; photos 0.62–1.44 GB | No: 14 plots, oiling/cover only (§4) |
| DIVER Explorer / DWH NRDA | https://www.diver.orr.noaa.gov/deepwater-horizon-nrda-data/ | 200 | Query UI | No bulk STR/treatment GIS linked from the page fetched |
| ERMA Gulf | https://erma.noaa.gov/gulfofamerica/erma.html and gulfofmexico | 200 (8 024 B HTML) | Map application | No anonymous REST catalog |
| ERMA `/rest` and `/arcgis/rest/services` | same host | 200, same 8 024 B HTML as the map home | Not an ArcGIS REST directory | No |
| NGDC ArcGIS `DWH` folder | https://gis.ngdc.noaa.gov/arcgis/rest/services/DWH | 200 | `DWHAtlas_CTDs`, `ERMA_GLIDERs` only | No |
| NOAA CUSP FeatureServer | services.arcgis.com/…/NOAA_Coastal_Shoreline | 200 | Mean-high-water shoreline, not SCAT | No |
| coast.noaa.gov ArcGIS | /arcgis/rest/services | 200 | CCAP, flood, landcover, … | No SCAT/treatment service listed |
| GRIIDC Zengel 2022 erosion | doi:10.7266/VF524143 | 200 | Plot erosion by treatment group (already in repo) | Plot-level, not segments |
| GRIIDC search “shoreline treatment” | data.griidc.org/search | 200 | HTML search page | No new segment treatment dataset identified from the page |
| Louisiana CPRA CIMS | https://cims.coastal.louisiana.gov/ | 200 | CRMS monitoring | No DWH STR layer found |
| CPRA home | https://www.coastal.louisiana.gov/ | 000 (no response) | — | Not reached |
| NOAA IR / OR&R DWH page | response.restoration.noaa.gov/…/deepwater-horizon-oil-spill | 200 | Incident page | Narrative |
| IOSC 2011 “Shoreline Treatment during DWH” | iosc.kglmeridian.com/…/article-p271.xml | 200 | Paper on STR process and NFT guidelines | No data file |
| DWH admin record (guessed FWS URL) | fws.gov/doh/dwh-ar | 403 | — | Not reached |
| NOAA-SCAT-Standard (GitHub) | researchplanninginc/NOAA-SCAT-Standard | 200 | Draft schema + synthetic demos | Not DWH records |
| InPort item 57299 (guess) | fisheries.noaa.gov/inport/item/57299 | 404 | — | Does not exist |

Nixon et al. 2016 integrated segment oiling database was not found as a public
download (same as `docs/DATA_ACQUISITION.md`: ask Research Planning, Inc.).

## 3. NCEI DIVER archive folders

Index: https://www.ncei.noaa.gov/data/deepwater-horizon-diver-system/archive/
(HTTP 200). Top-level names (sizes not printed on the index): BPPublic,
Chemistry, DWHResponse, DeepWaterBenthic, Fish, HumanUse,
MarineMammalsandTurtles, NearshoreSedimentandWater, OtherTaskingAgency, Oyster,
SAV, ShallowWaterCoral, **Shoreline**, Telemetry, WaterColumn.

`DWHResponse/` is cruise and strike-team chemistry, not shoreline STR.

`Shoreline/` subfolders, **bytes summed from the file-size column on each
index** (`results/f6_f7/diver_shoreline_folder_sizes.csv`):

| Folder | Listed bytes (approx.) | Treatment-related? |
| --- | ---: | --- |
| BPShorelineStakingPlanFall2011 | 880 MB | Staking / NRDA, not STR method |
| BPShorelineStakingPlanSpring2012 | 1.75 GB | same |
| CWV-MarshResponseCleanupAreas-February2011 | 679 MB (photos dominate) | Plot oiling/cover; no method field |
| CWV-MarshResponseCleanupAreas-Spring2011 | 1.07 GB | same |
| CWV-MarshResponseCleanupAreas-Fall2011 | 1.54 GB | same |
| CoastalWetlandVegetationPlan* (five campaigns) | 0.03–18 GB each | Vegetation/chemistry (already used) |
| RapidMarshOilingAssessment | 67.9 GB | Oiling assessment; not downloaded |
| Shoreline-Baseline-2010 | 53 MB | Baseline samples |
| ShorelinePre-Assessment | 39 GB | Pre-assessment |
| others (FL/TX baselines, fiddler/periwinkle, LiDAR, RTK) | 2 MB–3.6 GB | Not STR |

No folder named Shoreline Treatment, STR, or SCAT treatment recommendations.

## 4. Machine-readable files obtained (not the F6 table)

See `data/external/dwh_treatment/SOURCE.md`. February 2011 FieldObservations
tar opened: 14 named sites (B, C, D, E, H, I series). Fields listed there.
**Do not treat this as cleanup method per SCAT segment.**

Zengel et al. 2022 GRIIDC plot erosion (already in `data/external/zengel2022/`)
remains the only open table with treated vs untreated vs planted labels, at
plot scale in Bay Jimmy.

## 5. Digitisation protocol (if Jaison proceeds)

Scope is **northern Barataria Bay only** (Bay Jimmy, Bay Batiste, Wilkinson
Bay, St. Mary’s Point). It cannot label the whole Gulf NAIP grid.

**Effort (ASSUMED, not timed):** 1 working day to georeference three map
figures and digitise treated / potential / set-aside lines; half a day for
Jaison’s sample check; a further half day to join to 100 m edge cells. Positional
error of 50–200 m is likely (map figures, not survey GPS).

Steps:

1. Download the TM PDF with `scripts/download_orr42.ps1` or by hand from the
   NOAA IR landing page. Confirm SHA-512 against SOURCE.md.
2. Export Figures 35, 36 and 39 as images (300 dpi or the PDF page raster).
   Keep Figure 40 only as a planting overlay, not as the treatment shoreline.
3. In QGIS, load a 2010 NAIP mosaic (already used for edge cells) and the
   Louisiana SCAT max-oiling polylines (`scripts/download_scat.sh`, layer
   18611). Set CRS to the edge-cell CRS (NAD83 / UTM).
4. Georeference each figure with 8–12 control points on identifiable marsh
   points, canals and island tips. Record RMSE. Reject a figure if RMSE is
   worse than 100 m without a stated reason.
5. Digitise as polylines along the marsh edge (not polygons over water):
   `treated_s3_045`, `potential_untreated`, `set_aside`. Split where the
   figure colour changes. Do not invent stretches off the map.
6. Attributes (minimum): `str_id` (S3-045 / S4-032 if labelled), `zone_id` if
   lettered, `map_class` (treated / potential / set_aside / planting_plot),
   `figure`, `page`, `tool_code` (see below), `evidence` = LITERATURE
   (map figure).
7. Map figure classes to tool codes from `noaa_crosswalk.py` / knowledge
   tables, **only where the memorandum text for that zone names a method**:

   | Figure / text class | tool_code |
   | --- | --- |
   | Set-aside / no treatment | natural_attenuation |
   | Manual treatment | manual_removal |
   | Mechanical treatment | mechanical_removal |
   | Mechanical then planting (Fig. 40 / Zone K) | mechanical_removal plus planting (two flags) |
   | Unstated treated (yellow on Fig. 36 with no method in text) | `treated_unspecified` (do not guess) |

   Do not code flushing, sorbents or bioremediation from these maps unless the
   caption says so.
8. Join: buffer 50 m, intersect with NAIP edge cells (`data/external/naip_edge/`
   or P2 Barataria cells). One cell may touch more than one class; keep a
   majority rule and a conflict flag. Pre-specify the rule in an F6 analysis
   plan before computing erosion contrasts.
9. **QA (Jaison):** 20 cells drawn at random from treated and 20 from
   set-aside. Compare on-screen to Figures 36 and 39. Pass if at least 18/20
   in each group match. Failures stay on the map as a documented error rate;
   do not silently edit.
10. Deliverables: GeoPackage of lines, cell join table, georeferencing report
    (RMSE, control points), QA sheet. No analysis in this step.

## 6. Gate

F6 feasibility **passes as (b)**: no machine-readable treatment-per-segment
source in the public places listed; figure pages and a digitisation protocol
are recorded. Gulf-wide segment split of NAIP cells remains **not possible**
with open data.
