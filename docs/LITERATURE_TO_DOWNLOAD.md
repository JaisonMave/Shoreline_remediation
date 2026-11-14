# Literature to download (papers Claude could not reach)

Jaison cannot download these at present. Each entry says what is missing and which conclusion depends on it.
When a PDF arrives, put it in `docs/reference/`, complete the relevant table, and mark the row Done.
Add rows at the bottom; do not delete rows.

| # | Paper | DOI | What was read instead | What the full text is needed for | Blocks | Status |
| --- | --- | --- | --- | --- | --- | --- |
| L1 | Challenger GE, Gmur S, Taylor E (2021). A review of Gulf of Mexico coastal marsh erosion studies following the 2010 Deepwater Horizon oil spill and comparison to over 4 years of shoreline loss data from Fall 2010 to Summer 2015. Mar Pollut Bull 164:111983 | 10.1016/j.marpolbul.2021.111983 | Abstract; Zengel et al. 2022 Sci Rep Table 1 | Source studies pooled; oiling definition and comparison group; sub-period boundaries; m/yr rates with uncertainty; how exposure, pre-spill rates and Hurricane Isaac were handled; whether the 131-site table is public | FINDINGS section 11 table (Challenger column); REVIEW_NOTES C0 | Wanted (closed access) |
| L2 | Turner RE, McClenachan G, Tweel AW (2016). Islands in the oil: quantifying salt marsh shoreline erosion after the Deepwater Horizon oiling. Mar Pollut Bull 110(1):316-323 | 10.1016/j.marpolbul.2016.06.046 | Abstract; authors' data file (GRIIDC 10.7266/N72J68WS, in hand) | Whether "increased to 275%" means 2.75x or 3.75x and against which baseline; group mean rates and tests; which SCAT product defined oiling; Isaac result; stated limits | FINDINGS section 11 table (Turner column) | Wanted (listed open access, CC BY-NC-ND, but every copy was blocked from here) |

Lower priority (cited through secondary sources only; not blocking):

| # | Paper | DOI | Why |
| --- | --- | --- | --- |
| L3 | Deis DR, Mendelssohn IA, Fleeger JW, Bourgoin SM, Lin Q (2019). Legacy effects of Hurricane Katrina influenced marsh shoreline erosion following the Deepwater Horizon oil spill. Sci Total Environ 672:456-467 | not checked | The other paper questioning DWH erosion studies (cyclones, exposure); citation taken from Zengel 2022 reference list |
| L4 | Hoff R, Michel J (eds) (2014). Oil Spills in Mangroves: Planning and Response Considerations. NOAA Office of Response and Restoration | not checked | Verify mangrove screening rows marked "to verify" (`data/knowledge/mangrove_screening.csv`); chapter 3 was cut off when read |

---

## Update 14 Nov 2026 (literature and data acquisition run)

Rules followed: open or official sources only; no paywall bypass; where an official host refused (403/503) one other official host was tried, then the item was recorded as not reached. Every URL tried is in `results/v5_literature/url_checks.csv`.
Pages and sizes were checked by opening each file. Index rows are in `docs/reference/REFERENCE_INDEX.csv`. Files in `docs/reference/restricted/` are git-ignored (held locally only).

Note: the index already lists several restricted PDFs (Challenger 2021, Deis 2019, Owens 2021, Silliman 2012, Rabalais 2016, Michel 2022 and others), but `docs/reference/restricted/` did not exist in this working tree at the start of the run, so those files are not on this machine. They have not been re-fetched (closed access or not requested).

### Obtained 14 Nov 2026

| Item | File | Licence | Pages | Committed? |
| --- | --- | --- | --- | --- |
| L2 Turner et al. 2016 MPB 110:316-323 (already in repo, verified) | `docs/reference/Turner_2016_MPB_oiled_islands_erosion.pdf` | CC BY-NC-ND 4.0 | 8 | yes |
| L4 Hoff and Michel 2014 Oil Spills in Mangroves (already in repo, verified) | `docs/reference/Oil_Spill_Mangrove.pdf` | US government work | 96 | yes |
| NOAA 2017 Characteristic Coastal Habitats (already in repo, not duplicated) | `docs/reference/literature/NOAA_2017_CharacteristicCoastalHabitats.pdf` | US government work | | yes |
| Michel et al. 2013 PLoS ONE 8:e65087 | `docs/reference/literature/Michel_2013_PLoSONE_DWH_ShorelineOiling.pdf` | CC0 | 9 | yes |
| Michel et al. 2013, supplementary S1 (only supporting file the article lists) | `docs/reference/literature/Michel_2013_PLoSONE_DWH_ShorelineOiling_S1.docx` | CC0 | docx | yes |
| Michel et al. 2017 MEPS 576:203-218 | `docs/reference/literature/Michel_2017_MEPS_SandBeach_ResponseInjuries.pdf` (from int-res.com) | CC BY | 16 | yes |
| Lindeberg et al. 2018, EVOSTC 16120114-S | `docs/reference/literature/Lindeberg_2018_EVOSTC_16120114-S_LingeringOil.pdf` | US government work (NOAA authors) | 318 | yes |
| Geng and Boufadel 2017 Sci Rep 7:40770 | `docs/reference/literature/Geng_2017_SciRep_GravelBeach_TidalSignals.pdf` | CC BY 4.0 | 8 | yes |
| Geng, Boufadel, Jackson 2016 Sci Rep 6:31486 | `docs/reference/literature/Geng_2016_SciRep_BeachSaltAccumulation.pdf` | CC BY 4.0 | 5 | yes |
| USGS OFR 2015-1057 (HTML only; partial: title, abstract, introduction, methods, list of figures) | `docs/reference/literature/USGS_OFR2015-1057_html/` | US government work | 5 pages | yes |
| NOAA/API 1994 Options for Minimizing Environmental Impacts of Freshwater Spill Response (GPO OCR text) | `docs/reference/literature/NOAA_API_1994_FreshwaterOptions_GPO/` | US government work | OCR htm | yes |
| Michel and Bambach 2020 Response Guide for Sunken Oil Mats (extra, related to OSAT-3 submerged oil mats) | `docs/reference/literature/Michel_Bambach_2020_NOAA_SunkenOilMats_ResponseGuide.pdf` | NOAA publication | 47 | yes |
| Venosa et al. 1996 ES&T 30:1764 (NRT copy) | `docs/reference/restricted/Venosa_1996_DelawareBay_NRTcopy.pdf` | ACS copyright, free on NRT site | 12 | no (local only) |
| API 2016 TR 425 Options for Minimizing Impacts of Inland Spill Response | `docs/reference/restricted/API_2016_TR425_OptionsMinimizingInlandSpills.pdf` | API copyright | 112 | no |
| Nixon et al. n.d. Categorization of Shoreline Oiling (DWH AR0270684) | `docs/reference/restricted/Nixon_nd_DWH_AR0270684_CategorizationShorelineOiling.pdf` | licence not stated | 5 | no |
| EVOSTC c.2010 Report on Recent Lingering Oil Studies (extra) | `docs/reference/restricted/EVOSTC_2010_ReportRecentLingeringOilStudies.pdf` | licence not stated | 47 | no |
| Bociu et al. 2019 Sci Rep (already in repo) | `docs/reference/literature/Bociu_2019_SedimentOilAgglomerates.pdf` | CC BY 4.0 | | yes |

Data obtained (each folder has a `SOURCE.md` with SHA-256):

| Dataset | Folder | Notes |
| --- | --- | --- |
| EVOS lingering oil 2015, DOI 10.24431/rw1k1h (survey, site, gravimetric, composition CSVs, SOPs) | `data/external/evos_lingering_oil/2015_survey/` (photos 78 MB in `data/raw/`) | script `scripts/download_evos_lingering_oil.sh`; MD5 checked |
| Lingering oil synthesis 2015-2025 (test-pit segment status CSV, Alaska DEC listing method), DOI 10.24431/rw1kaio | `data/external/evos_lingering_oil/synthesis_2015_2025/` (geodatabase 16 MB in `data/raw/`) | draft agency analysis; new find |
| EVTHD hydrocarbon database 2014, CSV export from Gulf of Alaska Data Portal | `data/external/evthd_goa/` (14 MB) | `scripts/download_evthd_goa.sh`; SHA-1 checked. Not the InPort 17283 Access file (InPort refused scripts) |
| PWS bioremediation pilot 2010-2011 (metadata only) | `data/external/evos_bioremediation_pilot/` | data tables returned HTTP 401, not obtained |

### Still to obtain

| Item | Citation and DOI / URL | Why not fetched | What it would settle | Easiest lawful route |
| --- | --- | --- | --- | --- |
| L1 Challenger et al. 2021 | Mar Pollut Bull 164:111983, doi:10.1016/j.marpolbul.2021.111983 | Closed access (not tried again this run) | Source studies, oiling definition, rates and uncertainty for the marsh erosion table | University library or author request |
| L3 Deis et al. 2019 | Sci Total Environ 672:456-467 (DOI not checked) | Closed access (not tried) | Hurricane Katrina legacy as an alternative explanation for DWH marsh erosion | Library or author request |
| NOAA TM NOS OR&R 42 (Zengel and Michel 2013), Salt Marsh Oiling Conditions, Treatment Testing and Treatment History in Northern Barataria Bay | https://repository.library.noaa.gov/view/noaa/380/noaa_380_DS1.pdf | NOAA repository returns Akamai "Access Denied" 403 to scripts; no second official host found (fws.gov DWH Administrative Record searched; the AR documents returned were other reports) | Marsh treatment records by method | Download in a normal browser from the NOAA repository, or email NOAA ORR; the repository blocks all scripted access |
| OSAT-2 and OSAT-3 reports and appendices | restorethegulf.gov (decommissioned: every path returns the same 122 KB shell page; old PDF URLs 404); USGS pubs 70058704 (Appendix D) is JavaScript only | Official host gone; only a University of Florida mirror was found and it failed TLS verification (not used) | Buried oil, surface residual balls and submerged oil mats on Gulf beaches (C3 in beach_evidence.md) | Ask NOAA ORR or the Unified Command archive; browser search of the Gulf Spill Restoration site |
| USGS OFR 2015-1057, remaining pages (data processing, data catalogue, references) | https://pubs.usgs.gov/of/2015/1057/ | Section page URLs are navigated by JavaScript; guessed URLs returned 404 | Agglomerate density/size data catalogue | Open the report in a browser and save the pages |
| Short et al. 2004 EST 38:19 (12 yr PWS estimate) and Short et al. 2007 EST 41:1245, doi:10.1021/es0620033 | ACS | Paywalled; USGS record is a JavaScript page; NOAA repository blocked | Mass of lingering oil and weathering rates (68% to 4% per year) | Library, or request from NOAA AFSC authors |
| Li and Boufadel 2010 Nature Geoscience 3:96-99, doi:10.1038/ngeo749 | Nature | Paywalled; no author copy found | Two-layer beach mechanism | Library or author request |
| Hayes and Michel 1999 MPB 38:92-101, doi:10.1016/S0025-326X(98)00103-0 | Elsevier | Paywalled; NOAA repository (noaa/15493) blocked | Geomorphic controls on gravel beach persistence | Library or NOAA ORR |
| Owens et al. 2003 Spill Sci Technol Bull 8:257-272, doi:10.1016/S1353-2561(03)00041-0 | Elsevier | Paywalled | Svalbard in situ treatment reduction rates | Library or author request (Owens) |
| Other Geng and Boufadel papers: Water Resour Res 2014, doi:10.1002/2014WR016870; J Geophys Res Oceans 2015, doi:10.1002/2015JC011221 (CC BY-NC-ND per Crossref); Curr Opin Chem Eng 2021, doi:10.1016/j.coche.2021.100751 | Wiley returned 403; NJIT repository record has no file; Elsevier paywall | Beach biodegradation model parameters (oxygen, nutrient limits) | Browser download of the open JGR paper; library for the other two |
| Exxon Valdez 2001, 2003, 2005 PWS pit-survey data | Not found as separate open datasets | DataONE searched; only the 2015 survey and the 2015-2025 synthesis are public | Pit-positive probability over time | Ask NOAA AFSC Auke Bay (Lindeberg) |
| PWS bioremediation pilot data 2010-2011 (11 CSV tables), DataONE df35f.14.20 | see `data/external/evos_bioremediation_pilot/SOURCE.md` | HTTP 401 for public | Treatment (oxygen plus nutrients) effect on TPAH in gravel | Ask EVOSTC / Gulf of Alaska Data Portal |
| EVTHD Access database, NOAA InPort 17283 | https://www.fisheries.noaa.gov/inport/item/17283 | HTTP 503 and Akamai 403 | Original Access file and lexicon (CSV export was obtained) | Browser download from InPort |
| Gulf of Alaska portal LTEMP hydrocarbon data (not asked) | doi:10.5063/F1CF9NK7 (132 MB CSV) | Not downloaded (size); optional | Long-term sediment/mussel hydrocarbon series | Run a DataONE download into `data/raw/` if wanted |
