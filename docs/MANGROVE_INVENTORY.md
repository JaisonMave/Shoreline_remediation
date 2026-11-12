# Mangrove oil-spill outcomes-over-time: feasibility inventory (no modelling)

Prepared 2026-11-12. Local folder: /home/claude/work/phaseC/. Nothing from the downloaded folders was executed; files were only read (python3 -I with pandas/csv, pdftotext, grep).
Status words: "not found" = looked, nothing found; "not checked" = not looked at. ASSUMED = my inference, not confirmed by a source.
Tool budget was limited, so web checks are shallow; several search results returned titles only, no text.

Field order per section: what it is / source / variables+units / sites-plots / years / treatment variable / unoiled reference / coordinates / licence / bytes+sha256 / usefulness.

---------------------------------------------------------------
## 1. NCEI/NODC Accession 9400033 - Bahia Las Minas (Galeta), Panama, 1986 refinery spill (LOCAL, usable)

- What: Digital files of the MMS "Long-term assessment of the oil spill at Bahia Las Minas, Panama" (Keller and Jackson eds. 1993, OCS Study MMS 93-0048). Local data/ folder holds comma-separated text files (.txt, dBASE-derived, no header row) plus .doc field descriptions. Mangrove content = two groups: MGF (Mangrove Forests, Duke 1993) and MGR (mangrove fringe and prop-root epibiota, Garrity and Levings 1993). Also present: STO files (stoa-stod, not mangrove-specific, not read), stri_os.doc (conventions), tableofcon (which also lists grs, rfl, sna, sre sets NOT downloaded). The landing page and bulk accession download returned 503; files came from the directory index https://www.ncei.noaa.gov/data/oceans/archive/arc0001/9400033/1.1/data/0-data (path taken from idx0.html title). The folder's journal.txt says the accession is a verified copy of an old magneto-optical platter (2002).
- Source: NCEI accession 9400033, "Bahia Las Minas, Panama Oil Spill Assessment, 1986-1991 (NODC Accession 9400033)"; https://www.ncei.noaa.gov/archive/accession/9400033. DOI: none in the catalogue record. Citation requested in the .doc files: Duke, N. 1993 (MGF, pp. 447-533) and Garrity, S.D. and Levings, S.C. 1993 (MGR, pp. 535-792), in Keller and Jackson eds., MMS 93-0048.
- Variables (from .doc; columns follow .doc order):
  - MGFD seedling demography (14,132 records): per tagged seedling: status (dead, new recruit, missing, tip damaged, new shoot), species (R. mangle, L. racemosa, A. germinans, P. rhizophorae), origin (r = planted by refinery, n = natural), hypocotyl height, seedling height (cm), girth (cm).
  - MGFL litterfall (1,034): dry mass of leaves, stems, wood, debris (g), counts, days deployed.
  - MGFS (16,926) and MGFT (624): further forest sub-studies; content NOT fully read.
  - MGRC (24,227): percent cover of root epibiota by taxon code (includes OI = oil cover). MGRP (2,508) per the doc relates to oil cover on roots (partly read). MGRR (11,753), MGRB, MGRE, MGRG, MGRQ, MGRS, MGRT, MGRV, MGRW, MGRZ: root recruitment, survival, growth, mussel transplants etc.; per-file meaning only partly mapped. Read mgr.doc/mgf.doc before use.
  - Mostly percent cover, counts, lengths, masses. No hydrocarbon chemistry seen in the mangrove files (ASSUMED; chemistry was a separate subproject, not downloaded).
- Sites/plots: SITE (4-char code), SITEN, REPL, PLT; HAB (o = open coast, c = channel, r = river); COND (o = oiled, u = unoiled; "n" also occurs in MGRC, meaning not confirmed). MGRC row counts: oiled 11,305, unoiled 12,119, n 803. Number of sites not enumerated.
- Years (from 8-digit dates in files): MGF 1989-1992 (mgfd 1990-02 to 1992-10; mgfs 1989-06 to 1991-07). MGR 1987-05 to 1991-12 (mgrc 202 distinct dates). One 1909 date in mgre is a typo. Catalogue temporal coverage 1986-05-01 to 1991-10-31; catalogue states pre-spill data are excluded.
- Treatment/cleanup variable: no cleanup, dispersant, cutting or flushing variable found. Only PLANT = r vs n (seedlings planted by the refinery vs natural) in MGFD, a planting contrast. Oiled/unoiled is a site condition, not a treatment.
- Unoiled reference: yes (COND = u, across open/channel/river habitats).
- Coordinates: none in the data files or the field lists I read; bounding box in catalogue unlabelled ("-79.0,9.2,-80.0,10.0"). Site maps are in the printed report (not obtained).
- Licence: catalogue record says CC0 1.0 Public Domain Dedication but also access level "non-public" and rights "otherRestrictions, unclassified" (conflict; ask NCEI). The .doc files request citation of the report.
- Bytes/sha256: see end of file (data folder about 7.7 MB).
- Usefulness: best local source for recovery trajectories (multi-date, oiled vs unoiled, tag-level seedling follow-up). Limits: about 5 years, no pre-spill, no coordinates, no chemistry.

---------------------------------------------------------------
## 2. Smithsonian Research Online - "Galeta Oil Spill Project - Documentation" (LOCAL but FAILED download)

- What: si_galeta/ holds two files of 24,681 bytes each (landing.html, bitstream.bin). Both are Smithsonian "Temporary service interruption" error pages. No data obtained.
- Source: https://repository.si.edu/items/5c889c7f-92f8-43f7-8fb8-c68c318f502b ; handle http://hdl.handle.net/10088/119 ; no DOI listed. Per the record (WebFetch): Karl Kaufmann, issued 1993-11, available 2006-03-07, MMS 93-0048; "documentation only, not the full datasets"; data from May 1986 to Oct 1991. This is the documentation companion of Source 1.
- Variables, sites, years, treatment, reference, coordinates: see Source 1; not available independently here.
- Licence: no rights statement in the record; a file license.txt (1.91 KB) is listed, its text not seen.
- Bytes/sha256: landing.html 24,681 B, 529500ddc0473ccfbcd73ef46a2f5ce76447ef02a468b0f317421c56b7058ce8; bitstream.bin 24,681 B, 76d18605ac5cc06fb1ee06e4b0cc9a9ca2fe66cc205275b5ef730780224b339e (error pages; ignore).
- Usefulness: low; redundant with Source 1.

---------------------------------------------------------------
## 3. TROPICS (Bocas del Toro, Panama) - 1984 oil vs dispersed-oil experiment, 40-year report (LOCAL PDF; no data files)

- What: Final report PDF (6,187,471 bytes) of the TROPICS field experiment: Site R (reference), Site O (oil only), Site D (dispersed oil), Cayo Fresca, Bahia Almirante. Only the report and BSEE landing page (55,162 B) were obtained. Numbers are in report figures and appendix tables (sediment moisture, biomarkers, n-alkanes, PAHs; Appendices B-C by CEDRE and Texas A&M), not as a data file.
- Source: Renegar, D.A. and Schuler, P.A. 2026. TROPICS: Longitudinal study in support of shoreline spill response NEBA. BSEE Report 1169, Contract 140E0124C0005. https://doi.org/10.70149/000000328578 (DOI printed in the PDF). Report also names BSEE oil-spill-response-research page, DOI library and NTRL as sources.
- Variables (from report): live adult mangrove tree and seedling counts, canopy density %, tree height (m), DBH, leaf width/length, herbivory, tree-snail and oyster abundance, basal area; sediment hydrocarbons from cores; 2024 drone multispectral NDVI maps. Units mainly in figures.
- Sites/plots: 3 sites (R, O, D); adult trees individually tagged with GPS positions per report.
- Years: exposure 1984; visits at 10, 17, 20, 25, 29 and 40 years (last in Dec 2024); report summary also cites research visits between 1994 and 2016. Individual visit years not all verified.
- Treatment variable: yes. Oil only vs chemically dispersed oil vs reference (the only treatment contrast found). Report also mentions experimentally planted juveniles at Site O, none survived (minor).
- Unoiled reference: yes, Site R (report notes adult tree decline at R as well, so not a perfect control).
- Coordinates: tree GPS recorded in the field; coordinates not seen in the text I read.
- Licence: not found (US Government report; disclaimer only).
- Bytes/sha256: TROPICS40_final.pdf 6,187,471 B, 18e9ffe82be1198079dfed4662017932f20cabcd95a0b5af817087a0486395da; landing.html 55,162 B, 1452701bc097e5a33040df242d688a9b6dfc2f44d1b4482798ca8fdd52fb5dd0.
- Usefulness: longest record (40 y) and only treatment contrast, but one site per treatment (pseudoreplicated) and values only in figures/tables unless the authors supply files (not found).

---------------------------------------------------------------
## 4. GRIIDC Chandeleur Islands (Louisiana) - Deepwater Horizon oiled vs non-oiled, 2015-2016 (LOCAL, 4 datasets)

- What: four zips (d1913, d1914, d1915, d3033; extracted in x1913 etc.). Response headers saved show the zip names: dataset 1913 = R4.x262.212.0001 (macrofauna 2015), 1914 = R4.x262.212.0002 (site characteristics/cover 2015), 1915 = R4.x262.212.0003 (plant production 2015), 3033 = R4.x262.000.0018 (macrofauna 2016). Download pattern https://data.griidc.org/api/datasets/zip/<id>. Dataset titles, PIs and DOIs were not recovered; re-fetching data.griidc.org timed out twice at 40 s: not found.
- Source: GRIIDC (Gulf of Mexico Research Initiative). UDIs as inferred from zip names (ASSUMED to be the identifiers).
- Variables: black mangrove: mangrove_density.csv (Leaves, New Leaves per tree), mangrove_ag_production.csv (leaf area, Leaf Health score, grazing y/n; 445 rows), mangrove_bg_production.csv (pneumatophores per 10 cm2). Also Spartina density/production, % cover by species/bare (x1914), macrofauna abundance, biomass, length, plant density, salinity (ppt), temperature (C), water depth (cm), DO (mg/L) (x1913, x3033). Units listed in Macrofauna_metadata_Parameters file.
- Sites/plots: 4 sites; A and B oiled, C1-S and C2-N non-oiled (stated in metadata file). Habitats Mangrove / Marsh / Mixed; mangrove_density has 48 rows.
- Years: 2015 (30 Jun; 20-21 Sep) for production/density/cover; macrofauna 2015 and 2016 (13 Jun, 16 Sep). About 5-6 years after the 2010 spill: residual difference snapshot, not a recovery trajectory.
- Treatment variable: none (Oiling? = Oiled/Non only).
- Unoiled reference: yes.
- Coordinates: yes, lat/long per site and habitat (site_location.csv, abiotics). Degree sign mis-encoded; read as latin-1.
- Licence: not found (landing pages not retrieved). GoMRI data policy ASSUMED, not verified.
- Bytes/sha256: d1913.bin 117,447 B f693d11b5581252b02106f3937a1d97579b419f2878108707148e721867fe2d4; d1914.bin 2,861 B 3232fa4fd0ab7ec617e62ec8fd34b34b0ec98080bdd00e6741ddd5349737935f; d1915.bin 42,173 B 0ead26fc9d9c312c6f4461bc12b89916f940d2846b400458ab39bd438b20cf70; d3033.bin 88,791 B 5c90db3dd21ea88a9e155a85e9c5e1ccf65a1b8f3da3a8b49a77104d9113644d.
- Usefulness: small (2 oiled sites, 2 years), mangrove part tiny; a georeferenced oiled-vs-reference example only.

---------------------------------------------------------------
## 5. Candidates checked on the web (shallow)

| Source | Citation / DOI | Data file? |
|---|---|---|
| Duke 2016 global review | Duke, N.C. 2016. Oil spill impacts on mangroves: recommendations for operational planning and action based on a global review. Mar. Pollut. Bull. 109(2):700-715. DOI 10.1016/j.marpolbul.2016.06.082 (from JCU ResearchOnline record) | JCU record shows no supplementary data and restricts full text. Publisher supplement: not checked. Treat as paper tables only. |
| Wakashio 2020, Mauritius | Rajendran, S. et al. 2022, "History of a disaster: a baseline assessment of the Wakashio oil spill on the coast of Mauritius, Indian Ocean" (QSpace record; journal and DOI not on the page: not found). Satellite-based baseline. | No dataset mentioned. Mangrove outcomes over time: not found. |
| Niger Delta / Bodo | UNEP 2011, Environmental Assessment of Ogoniland (unep.org resource page found by search). | Report and site factsheets (PDF); numeric mangrove time series not found; not opened. |
| Duke and Burns / Era 1992 / Gladstone | Search returned "Oil spill from the Era: Mangroves taking eons to recover" (Griffith repository; JCU records JCU158962, JCU158951). Authors, year, DOI not read. | Not checked beyond titles. Gladstone: nothing found. |
| Guanabara Bay 2000 | Search returned Brazilian papers (Springer doi 10.1007/s11270-010-0536-4, title not read; a SciELO record) and a NOAA "Oil Spill Mangrove" PDF. | Not checked; paper tables/figures only (ASSUMED). |
| Sundarbans 2014 (Shela River) | Banglajol JASBS article 46193 "Study of impacts of oil spill on the Sundarbans mangrove forest of Bangladesh"; Cedre sheet "Southern Star 7". | Not checked; likely paper tables only (ASSUMED). |

---------------------------------------------------------------
## Ranking

| Source | (1) Recovery trajectories | (2) Treatment comparison | Notes |
|---|---|---|---|
| NCEI 9400033 Galeta (MGF/MGR) | 1 (about 5 y, many dates, oiled vs unoiled, tagged seedlings) | 3 (planted vs natural seedlings only) | no coordinates, no pre-spill |
| TROPICS 2026 report | 2 (40 y, but figures/tables only, 3 sites) | 1 (oil vs dispersed vs reference) | need author data or digitising |
| GRIIDC Chandeleur | 3 (2 years, 5+ y post-spill) | 4 (none) | georeferenced, small |
| SI Galeta documentation | not usable (failed download; redundant) | not usable | |
| Duke 2016, Era, Guanabara, Sundarbans, Wakashio, Bodo | not assessed | not assessed | papers/reports only so far |

## What a person must fetch by hand
1. NCEI 9400033: ask NCEI to clarify licence/access ("non-public" vs CC0); get the printed MMS 93-0048 vol. II (Duke pp. 447-533; Garrity and Levings pp. 535-792) for site maps, coordinates, any cleanup description and per-file meaning; fetch non-mangrove files if wanted.
2. Smithsonian repository: retry the item URL (server error at fetch time) for license.txt and documentation pages.
3. GRIIDC: open the four dataset pages on data.griidc.org for titles, DOIs, PIs and licence/restriction wording (all timed out here).
4. TROPICS: ask BSEE / NSU (Renegar) for tabular data behind the figures; look for earlier TROPICS papers (the report cites Renegar et al. 2022) for 10-30 y tables.
5. Duke 2016: get the full text from Elsevier to see whether a supplementary spill table exists.
6. Wakashio, Bodo/UNEP, Era/Gladstone, Guanabara, Sundarbans: read the papers/reports and look for data tables; not checked in depth.

## Bytes and sha256 of main local files (computed locally)
```
1269845 mgfd_m.txt
 130710 mgfl_m.txt
1734079 mgfs_mx.txt
  36994 mgft_m.txt
  20352 mgr_s.txt
  35743 mgrb_m.txt
2145359 mgrc_m.txt
  69293 mgre_m.txt
  20710 mgrg_m.txt
 197604 mgrp_m.txt
  97453 mgrq_m.txt
 974481 mgrr_m.txt
  49467 mgrs_m.txt
  25338 mgrt_m.txt
  43020 mgrv_m.txt
  38018 mgrw_m.txt
   5930 mgrz_m.txt
  62195 mgr.doc
  14182 mgf.doc
6970773 total
c4a333916ffbdaceb7af259130626b0cb3c8a3009b438d00fc5ca1ee62ad0992  mgfd_m.txt
1399bbfdde99180bde980b22d07617b1baa3b7fe65144c98d0a72447321b1bc8  mgfl_m.txt
59270ae2d67ee696f8908091d1894d8ea0ac2658f24ec4db5d744a226b399d8c  mgfs_mx.txt
dc0969abe5c275f3255af5f15a41b9a6788cc955fe98e1ec6b82bcc7c7d36160  mgft_m.txt
1b7e1c201cac7139ceb3f0f91da02adeb34acda014f85de13294111caa2cab69  mgr_s.txt
ec93febe9bb9e5f52fda0e79085ae02a0cdf59e26600741231b2121a95287132  mgrb_m.txt
6dbd4c865eb3c2283af7d4530c62b6d628ef874521882cf3079a1ecd8d291a8d  mgrc_m.txt
d6a29209a9f258594aeb834d2423eda43d1d96ee2c7273107d20977c3a6817e8  mgre_m.txt
03e7460a6fee087b5af41818d6328f555d5b3c653e2c3bd9bf3b95ce45fdf368  mgrg_m.txt
697ea54cee737b9df55fb254ac688c9646afbf045d146d66cefc0927dba39e58  mgrp_m.txt
63096336de7c9ffbfe38a5b5628eb542b3eb7b92265f93b256b503b192f120af  mgrq_m.txt
3b6c30b5e0187c15991548cec1e58529e081c42fcc641cb7e52938f3ddac82bc  mgrr_m.txt
0fa04d94632ce3029e9905570368ec2c80b9a8f20baa6761296007c0268bc477  mgrs_m.txt
36f4193db5d1400e8e25a910fd4d2c3a2e8eafda665126a0fd1af6b2672653a6  mgrt_m.txt
810e43546f7cdd7a9901f3a17a2e836464ef8749e60c49cf01853c3c8ec5bb76  mgrv_m.txt
e8e84416a1d5015fa92cced79139a74b9b6c94374ac00d3fefcc391d0a87df96  mgrw_m.txt
9d360541c4896ff7f4ef89252fd5efbcd7cef4ad4a34a41cec030e285e66f8c9  mgrz_m.txt
3daa9e2a56a4fb60dc92c29bf4a61019f76e034dfad9b4656e02e0c541bdca2f  mgr.doc
450209a9157f0b66887076b94bd5479271e952c96452e66e8f97b823fe5d687a  mgf.doc
21449 x1915/mangrove_ag_production.csv
 1576 x1915/mangrove_bg_production.csv
 1640 x1915/mangrove_density.csv
 2617 x1914/site_characteristics_Chandeleur_metadata_2015.csv
27282 total
f7ff0c107c2d834ef44f459037ed3afdafcb90410488253ed7e848f571e74c2b  x1915/mangrove_ag_production.csv
5480c9eb34c4cc0839c78b25949c3a67d664ba7b7d1b373135852fd0fcedf03b  x1915/mangrove_bg_production.csv
378826cd09aa16c082e55800518de6c0702406a01405e1d64d61709824e5928e  x1915/mangrove_density.csv
408aa33b9d70bf8a19939a7b29f2b2460aa73a7261f573a42e80a8d0c99e345a  x1914/site_characteristics_Chandeleur_metadata_2015.csv
```
