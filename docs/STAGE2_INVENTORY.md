# Stage 2: dataset inventory (12 November 2026)

Inventory only: nothing here was modelled or analysed. Checks were run by two reading agents; the counts
marked "verified" were recounted by the orchestrator from the downloaded files
(`verify_counts.txt` in the session folder; commands in CHANGELOG). Full per-file detail, URLs and SHA-256:
`data/external/*/SOURCE.md`, `docs/DATA_CATALOGUE.md`. "In repo" means committed under `data/external/`.

| # | Source | Reachable / downloaded | Format | Licence | Units | Coordinates | Detection limits | Dates | Size (verified) | Main problem |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | GRIIDC Landsat marsh cover, Terrebonne/Barataria/Breton (R4.x264.000:0051, doi 10.7266/N7Z31X2K) | Reachable; **not downloaded** (1.11 GB, over the 300 MB session limit) | ENVI rasters (per landing page; files unread) | CC0 (page metadata) | Not checked | Not checked | n/a | Landing page says 2009-09-02; abstract says 1984-2011 scenes (conflict, unresolved) | 1.11 GB stated | Contents unread; needed for the D10 land/water cross-check |
| 2 | GRIIDC shoreline movement, Chandeleur Islands (doi 10.7266/n7-0caw-d652) | Downloaded; in repo | xlsx + shapefiles | CC0 (page metadata) | m, m/yr | Projected metres (NAD83 UTM 16N per .prj); metadata wrongly says decimal degrees | n/a | 4 shorelines, 2012-10-29 to 2017-09-08 | 488 transect-date rows; mangrove and marsh habitats | Barrier-island mangrove/marsh, not Louisiana mainland marsh; oiling not in the file |
| 3 | GRIIDC oil residue fingerprinting, Chandeleur (doi 10.7266/N7GQ6WCZ) | Downloaded; CSV in repo (9.8 MB chromatogram PDF not committed) | CSV + PDF | CC0 (page metadata) | Categorical result only | Lat/long, decimal degrees | None; "No residue detected" style results | Sep-Oct 2016 (rows seen) | 12 rows | Too small and categorical for modelling; context only |
| 4 | Turner et al. 2016 island erosion (doi 10.7266/N72J68WS) | Downloaded; in repo | xlsx, 3 sheets | CC0 (page metadata) | m, m/yr | Not in the data sheets (site names only; precision sheet has 6 lat/long) | n/a | 1988/89 to Dec 2012 | 46 islands (length), 41 (width); 22 oiled, 24 unoiled | Multi-row headers; 41 vs 46 rows unexplained; blanks in some intervals; no island coordinates |
| 5 | Zengel et al. 2022 meta-analysis (Ecol. Appl. 32:e02489) | Journal supplement blocked (Wiley); **GRIIDC copy downloaded** (doi 10.7266/n7-cn03-z792); in repo | xlsx | CC0 (page metadata) | Cover %, height, density, biomass (units in Metadata sheet; not all checked) | **None** (site IDs only) | n/a | 2010-2017 | 1,158 rows, 17 columns; 255 sites in 10 source studies; 810 oiled and 348 reference rows (verified) | No coordinates; link between this file and the paper's supplement unconfirmed |
| 6 | NOAA DIVER coastal wetland soil chemistry (asked: 1,894 samples, 2010-2013) | Downloaded (5 Coastal Wetland Vegetation Plan packages, 449 MB); **not committed**, `scripts/download_diver.sh` | tar of long CSV, 60 columns, one row per result | Public; NOAA "no warranty" wording; no licence identifier | PPB dry weight (PAH etc.); % by weight; mg/L and ug/L on some soil rows (unexplained) | Lat/long, NAD83 (one package checked) | Qualifier_Code (U, J, ...) and Detection_Extent on every row; **no numeric limit column** | 2010-09-16 to 2013-12-11 | **14,926 soil sample IDs**, 998 sediment, 3,078 tissue; 202 stations; 484,289 result rows (verified) | Does not match "1,894": the exact package asked for was not identified. 30% of rows have no detection limit available |
| 7 | NOAA DIVER nearshore sediment chemistry (asked: 1,731 samples, 2010-2011) | Downloaded (183 MB); not committed | as 6 | as 6 (one record says "non-public", the NCEI page says public; 5% of rows are "Trustee and RP") | PPB dry weight (sediment); ug/L (water) | Lat/long | as 6; 51% of rows at or below detection limit | 2010-06-21 to 2011-03-24 | **1,870 sediment sample IDs**, 651 water, 135 blanks (verified) | Count differs from 1,731; station labels unusable (one label), use coordinates |
| 8 | NOAA pre-assessment plant oiling (asked: 2,779 sites) | **Not obtained.** ERMA accession 0163814 (doi 10.7289/v5mw2fcq) download timed out; DIVER field-observation tars not fetched | GIS layers (per record) | Public (record) | Not checked | Not checked | n/a | 2010-2015 (record) | Not checked | Plant oiling is not in the sample files; needs the ERMA layers or DIVER FieldObservations |
| 9 | Michel et al. 2017 beach treatment (MEPS 576:203-218, doi 10.3354/meps11917) | Paper record reachable; **no public dataset found** | - | Article CC BY (NOAA repository) | - | - | - | - | - | Full text and data statement not read |
| 10 | Huettel et al. 2018 buried oil, Pensacola Beach (Mar Pollut Bull 126:488-500, doi 10.1016/j.marpolbul.2017.10.061; the brief said 2019) | 3 of 9 GRIIDC records downloaded; 2 small files in repo | xlsx | None stated on page | O2 umol/L by depth; hydrocarbons mg/kg; CO2 ppm | Not in the sheets read | Not checked | 2010-2014 (profiles); 2010-06-06 (reference cores); 2014-2017 (lab) | 42-row profile sheet; 64-row reference sheet; lab series 17.7 MB (not committed) | The oil-concentration time series (the useful part for degradation rates) is probably in the 6 records not yet opened (ASSUMED) |

## What this means for the project (orchestrator's reading)

1. **The soil-chemistry gap (REVIEW_NOTES E0) can now be closed with data.** The DIVER wetland files hold PAH,
   organic matter, bulk density, pH, salinity, nutrients and metals for about 200 marsh stations revisited
   over five campaigns (2010-2013), with censoring flags. This is the first chemical-recovery time series
   available to the project, and it is Jaison's own field (soil chemistry).
2. **Censoring must be handled, not ignored.** There is no numeric detection limit, only a category per result.
   Rows "at or below detection limit" cannot be treated as zeros or as measured values. Any model needs a
   censored-data method (for example Kaplan-Meier or a Tobit-type likelihood), specified before running.
3. **The Zengel meta-analysis file is the first multi-study vegetation-recovery table** (1,158 site-year-zone
   rows from several studies). It allows hold-out by study, which the 63-case NOAA table did not support well.
   It has no coordinates, so it cannot be joined to exposure or SCAT without the source studies.
4. **Turner's islands give an independent erosion dataset in three basins**, but without coordinates the
   islands cannot be matched to our edge cells.
5. **Chandeleur data are a different system** (barrier-island mangrove and marsh). Keep for later (D1 order:
   marsh first), not for the proof of concept.
6. **Beaches remain thin.** No public treatment dataset (Michel); Huettel's degradation series not yet located.

## What Jaison would need to fetch (only if wanted; nothing here blocks Stage 3)

| Item | Where | Why |
| --- | --- | --- |
| ERMA coastal wetland vegetation layers | https://doi.org/10.7289/v5mw2fcq (NCEI accession 0163814), download from a browser | Plant oiling at the vegetation sites (item 8) |
| Zengel 2022 Ecol. Appl. supporting information | https://doi.org/10.1002/eap.2489 | Confirm the GRIIDC file is the paper's dataset; site coordinates if listed |
| Michel et al. 2017 full text | https://doi.org/10.3354/meps11917 | Whether treatment data exist anywhere |

Claude can fetch on approval (no action needed from Jaison): the 1.11 GB Landsat marsh-cover archive (item 1),
the six remaining Huettel GRIIDC records (item 10), the DIVER field-observation tars (item 8).

## Not verified
Licence wording for GRIIDC is the page's machine-readable field (CC0), not a read licence text. All Huettel contents beyond the first rows are agent-reported. Why DIVER soil rows carry mg/L
units is unknown. The sample counts in the brief (1,894; 1,731; 2,779) could not be traced to a package.

## Update after Stage 3 downloads (12 Nov 2026)

- **Item 1, Landsat marsh cover: downloaded** (1,113,115,709 bytes; not committed). It is one base scene,
  2009-09-02 (Landsat TM path 022, rows 039/040), not a time series: 27 ENVI rasters, 5298 x 3964 pixels at
  30 m, UTM 15N; three-class vegetation maps (40% cover threshold) plus surface reflectance and unmixing
  fractions (vegetation, water, soil). Use for D10: a one-date, pre-spill cross-check of our 2007-2009
  Landsat land fraction. Not yet compared (needs a plan). Licence not checked.
- **Item 10, Huettel: the buried-oil series is found** (GRIIDC R5.x278.000:0015, doi 10.7266/n7-jjcn-y650):
  n-alkanes C15-C40 in mg/kg at 11 sampling days over 1,152 days and six depths, in sediment-oil agglomerates
  buried at Pensacola Beach. In repo. This is the first oil-degradation time series for a beach in the
  project (one site, one experiment). Records 0003-0005 return HTTP 404.
- **New: CRMS soil cores** (CPRA CIMS; 16,508 rows, 392 sites, 2006-2023; bulk density, organic matter, pH,
  conductance, salinity, some carbon, nutrients and texture; coordinates included). In repo. Used in the
  soil layer check (FINDINGS section 13).

