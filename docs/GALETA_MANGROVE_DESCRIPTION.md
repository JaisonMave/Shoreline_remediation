# Galeta (Bahia Las Minas, Panama) mangrove description, Phase C1

Status: descriptive only (plan: `docs/SCENARIO_PROGRAMME_PLAN.md`, Phase C1, added 12 Nov 2026). No model, no significance test and no recovery-time estimate appear here. Written 12 Nov 2026. Code: `scripts/galeta_description.py` (run as `python scripts/galeta_description.py <archive data folder>`; it was run on the session copy and produced everything in `results/galeta/`). Not independently re-checked against the printed report.

## 1. Source and licence position

- Source: NCEI/NODC accession 9400033, "Bahia Las Minas, Panama Oil Spill Assessment" files of the Smithsonian Tropical Research Institute oil spill project (MMS contracts 14-12-0001-30355 and -30393). Report: Keller and Jackson (eds.) 1993, OCS Study MMS 93-0048 (technical report). Files used here belong to two groups: MGF "Mangrove Forests" (cite: Duke, N. 1993, pp. 447-533) and MGR "Mangrove Fringe and Epibiota of Mangrove Roots" (cite: Garrity, S.D. and Levings, S.C. 1993, pp. 535-792). The `.doc` files ask users to include these citations.
- Where the files came from: the accession landing page and bulk download returned 503; the files were taken from the directory index https://www.ncei.noaa.gov/data/oceans/archive/arc0001/9400033/1.1/data/0-data (see `docs/MANGROVE_INVENTORY.md`, section 1). `journal.txt` says the accession is a verified copy of an old magneto-optical platter made in 2002. Checksums of the files are in `scripts/download_galeta.sh`.
- Licence: **unclear**. The catalogue record says CC0 1.0 Public Domain Dedication but also access level "non-public" and rights "otherRestrictions, unclassified" (recorded in the inventory; the landing page itself could not be retrieved, so this was not re-read here). Neither status was resolved with NCEI. For that reason the raw files are not committed; `scripts/download_galeta.sh` re-fetches them and `scripts/build_catalogue.py` has an entry EXT-GALETA (role "external (not committed)"). The derived tables and plots in `results/galeta/` contain only site-level summaries.
- Not in the data folder: `mgrl_m.txt` (long-term root percent cover, 229,762 records per `mgr.doc`; the journal lists it, but it was not downloaded), the grs/rfl/sna/sre data sets, and any chemistry (the archive says oil chemistry is hard copy only).

## 2. What the archive's own documentation says

- Missing numeric value is -1, missing character value is blank (`stri_os.doc`). Data were collected May 1986 to October 1991; the archive says data from before the spill and the one-year extension grant are not included (`stri_os.doc`).
- One record is one sampling unit (root, shoot, trap, seedling, bag). If nothing was found on a sampled unit, something is still entered; an unrecorded taxon is usually not written (`stri_os.doc`).
- Oiled vs unoiled (`mgr.doc`, site selection): "Definition of oiled vs. unoiled areas was based on examination of aerial photographs of oil slicks, followed by observations by boat"; oiling at sites was verified by percent cover and vertical extent of fresh oil on prop roots. Sites were chosen haphazardly, not randomised. Control sites include sites sampled before the spill that stayed unoiled, other sites inside the bay, and sites some distance away behind booms or by distance. This is a site classification made by the investigators, not an experimental treatment.
- COND codes: o = oiled, u = unoiled (field lists). The data also contain n in COND (MGRC, MGRR, MGRB, MGRQ, MGRT, and others where Hidden Channel appears), which the field lists do not define; the `mgr.doc` site-history text says Hidden Channel (HIDC) was "newly oiled just before CID12" and "its condition will now be entered as 'N'". That is the only documentation found; the meaning of n elsewhere is otherwise "not documented". Rows with n and rows with blank COND are excluded from both groups below.
- HAB codes: o = open coast, c = channel, r = river (drainage stream).
- MGR site history (`mgr.doc`): sites were changed over time (Pena Guapa channel sites were merged into Hidden Channel from CID 8, Largo Remo Channel South replaced Hidden Channel after it became newly oiled, Punta Galeta was dropped from quarterly sampling in August 1987 and re-sampled on the fourth and fifth anniversaries). So the set of sites differs by year, and the number of sites in each table row below is given for that reason.
- Site codes are four-letter acronyms listed in "Table 1.4 of the final report" (not in this archive; names appear in the site-history text only for the MGR sites). MGF site codes (for example ccpq, erja) and MGR site codes (for example pcs, hidr) are different code sets, and no crosswalk is in the archive.

## 3. File documentation

Rows are as read here (comma-separated, no header, column names taken from the field lists in `mgf.doc` and `mgr.doc`; every file read had exactly the number of columns the field list gives). Dates are 8-digit yyyymmdd. Per-file site counts and COND/HAB per site are in `results/galeta/galeta_file_inventory.csv` and `results/galeta/galeta_sites_by_file.csv`.

| File | Holds (per documentation) | Rows | Dates | Sites (oiled / unoiled) |
|---|---|---|---|---|
| mgf.doc, mgr.doc, stri_os.doc | field lists, methods excerpts, conventions | - | - | - |
| mgfd_m.txt | MGF seedling demography: tagged seedling status ST, species SP, origin PLANT (r = planted by refinery, n = natural), hypocotyl height H_HT (cm), seedling height T_HT (cm), girth GH (cm), tag numbers | 14,132 | 1990-02-20 to 1992-10-30 | 24 codes; no COND field |
| mgfl_m.txt | MGF litter traps: dry mass of leaves GML, stems GMS, wood GMW, debris GMD, reproductive parts GMR (g), counts of leaves, buds, flowers, fruits, hypocotyls; NUMDAYS deployed | 1,034 | 1989-07-11 to 1990-09-09 | 25 (12 / 13) |
| mgfs_mx.txt | MGF shoots: counts per tagged shoot (leaves LV, nodes ND, buds, flowers, fruits), new/dropped leaves; SP is rm only | 16,926 | 1989-06-08 to 1991-07-17 | 26 codes; no COND field |
| mgft_m.txt | MGF site surface salinity SURF_S (ppt) and temperature SURF_T (centigrade) | 624 | 1989-07-11 to 1991-07-17 | 26 (12 / 14); COND blank in 338 rows |
| mgr_s.txt | MGR species list (267 taxa, GROUP, GROUP2 codes, e.g. OI = oil, CL = barnacles-live) | 267 | - | - |
| mgrb_m.txt | biomass of organisms on dowels, NETGM (net weight g), NUMDAYS in water | 417 | 1988-03-01 to 1989-03-03 (1 blank date) | 25 (12 / 12, plus HIDC with n) |
| mgrc_m.txt | community development cohort: percent cover P_COV by taxon on individual roots, root condition RC, root length LCM (cm), diameter DMM (mm) | 24,227 | 1987-05-13 to 1991-09-02 | 23 + 387 rows with blank SITE (11 / 11, HIDC mixed u and n) |
| mgre_m.txt | root depth to bottom DEPTH_CM from high-water tag (documented as measured in 1989) | 1,447 | 1909-09-09 (apparent typo, not corrected) to 1990-03-09 | 26 |
| mgrg_m.txt | mussel gonads (sex, length LEN mm) from the mussel transplant | 320 | 1990-08-26 to 1990-11-22 | 8 (4 / 4), river habitat |
| mgrp_m.txt | mussel transplant (Mytilopsis in cages): LIVE and DEAD counts by length class, I_OR_F initial/final. 411 rows have SSID G (gonad) although `mgr.doc` describes G in mgrg | 2,508 | 1990-08-26 to 1991-02-06 | 8 (4 / 4) |
| mgrq_m.txt | light under canopy vs open (lux) and CANOPY_PCT = under canopy / open x 100 | 1,575 | 1988-12-05 to 1991-02-23 (20 blank dates) | 26 (13 / 12, HIDC n) |
| mgrr_m.txt | recruitment dowels: percent cover by taxon, root/dowel length and diameter | 11,753 | 1987-05-30 to 1991-08-30 | 27 (14 / 12, HIDC mixed) |
| mgrs_m.txt | salinity (ppt) and temperature (centigrade), surface and 1 m | 622 | 1988-12-14 to 1991-08-30 | 26 |
| mgrt_m.txt | Secchi depth SDDISM (m) | 468 (doc says 416) | 1989-11-18 to 1991-12-12 | 26 |
| mgrv_m.txt | mussel settlement, size class counts; bag treatment letters a, c, v, dd are "codes unknown" in the doc | 541 | 1990-11-22 to 1991-05-26 | 8 (4 / 4) |
| mgrw_m.txt | water movement, direct measurement (DIS_M m, SPD_CMSC cm/s) | 546 | 1990-03-09 to 1991-08-30 | 26 |
| mgrz_m.txt | water movement by plaster clods, PC_LEFT (percent of clod left) | 104 | 1989-08-31 to 1989-11-30 | 26 |
| sto.doc, stoa..stod_m.txt, tableofcon | stomatopod (reef flat) files and the table of contents; not mangrove, not read | - | - | - |

Documentation gaps found: MGFD and MGFS have no COND or HAB field; MGFD status codes include combinations (a, na, nt, nta, ta, sa, st, ot) not in the ST code list (code "a" is not documented). The RC code list does not cover every RC code in the data (codes such as nb, no, n0, n1 are not documented; 28 percent of roots with an RC code carry such a code). `mgr.doc` says RC starts at CID 9, but RC is filled in earlier rows too. The `mgrt_m.txt` row count differs from the field list. Unit of GML etc. is g (field list); litter rate per day below is derived here as g / NUMDAYS. Units of P_COV are percent (field list). The unit of LV (leaves per shoot) is a count.

## 4. How the tables were made

- Unit = site. Row-level units are averaged to a site-visit (date) mean, the visit means within a calendar year are averaged to a site-year mean, and the site-year means are averaged across the sites of the group. "n sites" is the number of sites with at least one value in that year and group. Year = calendar year of the collection date. The tables hold the mean of site means only; ranges and between-site SD are in `results/galeta/galeta_group_year.csv`. Site-year values: `results/galeta/galeta_site_year.csv`.
- MGFD and MGFS have no COND field; COND was taken from the same site code in MGFL/MGFT (inferred, not documented as the same site). 10 of 24 MGFD site codes are not in MGFL/MGFT and are excluded from the tables.
- Root-level oil cover (MGRC, MGRR): percent cover of rows with GROUP2 = OI per root per date, taking 0 when the root has other rows but none for oil (ASSUMED, from the convention in `stri_os.doc` that something is entered for every sampled unit). Roots with blank SITE (387 MGRC rows) are excluded.
- Root documented-dead share: among roots whose RC code is labelled "(dead)" or "(live)" in the RC table of `mgr.doc`, the share labelled dead. Roots with other codes are left out (not documented).
- Seedling height: seedlings with status x (dead) or m (missing) are dropped, -1 dropped, natural and planted shown separately. Seedling dead-flag share: records with status x, all origins.
- Litter: traps with TLOST = T dropped; leaf and reproductive dry mass per trap record divided by NUMDAYS (g per trap per day, derived). Rows pool species (rm, lr, ag, pr, xx). Leaves per shoot: R. mangle only, shoots flagged missing or bad dropped.
- Caged mussel survival: SSID P final rows (I_OR_F = f), per cage LIVE / (LIVE + DEAD) summed over length classes. This is a transplant experiment with adults from an unoiled river, not natural population change.
- Dowel biomass: rows with DATAABBR = total; deployment lengths (NUMDAYS) vary and one MGRB COND is n.
- Environmental covariates (salinity, temperature, Secchi, flow, clods, depth, mussel gonads and settlement) are documented above but not tabulated: they are not outcomes.

## 5. Outcome tables (site-level; mean of site means)

Plots: `results/galeta/galeta_<outcome>.png` (one per outcome, oiled in red, unoiled in blue, legend lists n sites per year).

**caged_mytilopsis_survival** - unit: share live of live + dead, final count per cage (transplant experiment, not natural)

| Year | Oiled: n sites | Oiled: mean of site means | Unoiled: n sites | Unoiled: mean of site means |
|---|---|---|---|---|
| 1990 | 4 | 0.665 | 4 | 0.67 |
| 1991 | 4 | 0.531 | 4 | 0.683 |

**canopy_light_ratio** - unit: % (under canopy lux / open lux x 100)

| Year | Oiled: n sites | Oiled: mean of site means | Unoiled: n sites | Unoiled: mean of site means |
|---|---|---|---|---|
| 1988 | 12 | 49.9 | 12 | 21.1 |
| 1989 | 12 | 49.6 | 12 | 29 |
| 1991 | 13 | 55.1 | 12 | 31.8 |

**dowel_oil_cover** - unit: % cover of recruitment dowel by oil (GROUP2 = OI)

| Year | Oiled: n sites | Oiled: mean of site means | Unoiled: n sites | Unoiled: mean of site means |
|---|---|---|---|---|
| 1987 | 8 | 6.37 | 7 | 0 |
| 1988 | 12 | 22.6 | 13 | 0.0627 |
| 1989 | 13 | 19.7 | 12 | 0 |
| 1990 | 13 | 5.99 | 12 | 0 |
| 1991 | 13 | 0.692 | 12 | 0 |

**dowel_total_biomass** - unit: g (NETGM, 'total' rows; deployment days vary, NUMDAYS)

| Year | Oiled: n sites | Oiled: mean of site means | Unoiled: n sites | Unoiled: mean of site means |
|---|---|---|---|---|
| 1988 | 12 | 2.51 | 13 | 18.9 |
| 1989 | 5 | 5.49 | 6 | 59.9 |

**leaves_per_shoot** - unit: leaves per tagged shoot (LV; R. mangle)

| Year | Oiled: n sites | Oiled: mean of site means | Unoiled: n sites | Unoiled: mean of site means |
|---|---|---|---|---|
| 1989 | 12 | 7.37 | 14 | 8.22 |
| 1990 | 12 | 6.44 | 14 | 7.6 |
| 1991 | 12 | 5.75 | 14 | 7.4 |

**litter_leaf_dry_mass_rate** - unit: g per trap per day (GML / NUMDAYS, derived)

| Year | Oiled: n sites | Oiled: mean of site means | Unoiled: n sites | Unoiled: mean of site means |
|---|---|---|---|---|
| 1989 | 12 | 1.37 | 13 | 1.54 |
| 1990 | 12 | 1.35 | 13 | 1.53 |

**litter_reproductive_dry_mass_rate** - unit: g per trap per day (GMR / NUMDAYS, derived)

| Year | Oiled: n sites | Oiled: mean of site means | Unoiled: n sites | Unoiled: mean of site means |
|---|---|---|---|---|
| 1989 | 12 | 0.117 | 13 | 0.15 |
| 1990 | 12 | 0.114 | 13 | 0.154 |

**root_documented_dead_share** - unit: share of roots whose RC code is labelled (dead) among codes labelled (dead) or (live)

| Year | Oiled: n sites | Oiled: mean of site means | Unoiled: n sites | Unoiled: mean of site means |
|---|---|---|---|---|
| 1987 | 11 | 0 | 12 | 0 |
| 1988 | 11 | 0.0865 | 12 | 0.0156 |
| 1989 | 11 | 0.169 | 11 | 0.0457 |
| 1990 | 11 | 0.291 | 11 | 0.119 |
| 1991 | 11 | 0.32 | 11 | 0.14 |

**root_oil_cover** - unit: % cover of root by oil (GROUP2 = OI)

| Year | Oiled: n sites | Oiled: mean of site means | Unoiled: n sites | Unoiled: mean of site means |
|---|---|---|---|---|
| 1987 | 11 | 8.44 | 12 | 0 |
| 1988 | 11 | 15.4 | 12 | 0.00421 |
| 1989 | 11 | 14 | 11 | 0 |
| 1990 | 11 | 10.1 | 11 | 0.00455 |
| 1991 | 11 | 5.58 | 11 | 0 |

**seedling_dead_flag_share** - unit: share of seedling records with status x (dead)

| Year | Oiled: n sites | Oiled: mean of site means | Unoiled: n sites | Unoiled: mean of site means |
|---|---|---|---|---|
| 1990 | 12 | 0 | 2 | 0 |
| 1991 | 12 | 0.0515 | 2 | 0.0602 |
| 1992 | 12 | 0.0263 | 2 | 0.136 |

**seedling_height** (stratum: natural) - unit: cm

| Year | Oiled: n sites | Oiled: mean of site means | Unoiled: n sites | Unoiled: mean of site means |
|---|---|---|---|---|
| 1990 | 12 | 75.2 | 2 | 54.8 |
| 1991 | 12 | 106 | 2 | 109 |
| 1992 | 12 | 137 | 2 | 168 |

**seedling_height** (stratum: planted by refinery) - unit: cm

| Year | Oiled: n sites | Oiled: mean of site means | Unoiled: n sites | Unoiled: mean of site means |
|---|---|---|---|---|
| 1990 | 8 | 77.6 | - | - |
| 1991 | 8 | 134 | - | - |
| 1992 | 8 | 210 | - | - |

Reading the tables: these are descriptions of the group means as computed, not comparisons tested for difference. Groups differ in habitat mix (open, channel, river), species mix and sites by year, so differences between oiled and unoiled means are not an effect estimate.

## 6. What cannot be done with these files

- No pre-spill data: `stri_os.doc` says data collected before the spill are not included (`mgr.doc` repeats this for the 1981-1982 roots). The earliest value here is May 1987, about a year after the April 1986 spill; no before-after change, and no recovery relative to a pre-spill baseline, can be computed.
- No cleanup variable: no cleanup, dispersant, cutting or flushing field was found in any file read. The only treatment-like field is PLANT (planted by the refinery vs natural seedlings), which is not a cleanup of the shoreline. Cleanup effects cannot be separated from oiling.
- No coordinates in any data file; site maps are in the printed report, which was not obtained. Habitat is only the o/c/r code.
- Oiled vs unoiled was assigned from visible oil (aerial photographs, boat observation), site by site, with sites differing in habitat and location; no randomisation, no paired design documented, and some sites changed status or were merged over time (HIDC).
- Site sets differ between files and years, and the MGF and MGR site codes cannot be matched with each other from this archive.
- Seedling outcomes have only 2 unoiled sites with a COND available by code (erja, nrme) against 12 oiled; the other seedling site codes have no COND in any file read.
- Hydrocarbon chemistry is not in the data folder (hard copy in the report only); oil exposure is only the percent of root or dowel surface covered by oil. "Sites at some distance" vs "inside the bay" is not coded.
- Recovery cannot be tied to time since an intervention; years here are calendar years of a monitoring programme, with different sites in different years.
- Nothing here estimates recovery time, and none should be read from the tables.
- Not verified here: whether the counts in the file inventory agree with the archive's printed tables (not obtained), and the meaning of the n and blank COND values beyond the Hidden Channel note.

## 7. Answer to the plan's question

Does a usable oiled-versus-unoiled series exist at three or more sites per group? Yes for these outcomes: root oil cover, recruitment-dowel oil cover and root documented-dead share (1987-1991, 11-14 oiled and 11-13 unoiled sites per year), canopy light ratio (1988, 1989, 1991; 12-13 per group), leaves per shoot of R. mangle (1989-1991; 12 oiled, 14 unoiled), leaf and reproductive litter rate (1989-1990; 12 and 13), dowel total biomass (1988 only with 12 and 13 sites; 1989 has 5 and 6) and caged mussel survival (1990-1991; 4 and 4, an experiment); no for seedling height and seedling dead-flag share (2 unoiled sites). All series start at least a year after the spill and none has a pre-spill value, so each describes a post-spill contrast over 2 to 5 years, not recovery from a baseline.
