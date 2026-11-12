# DIVER coastal wetland vegetation campaigns: soil-row structure

Structure inspection only. No concentrations were summarised, and no results were compared by year, campaign or oiling status. All numbers below are row, sample, station, or label counts.

## Scope and method

- Input: the five campaign files `cwvp_Fall2010_samples.csv`, `cwvp_Spring2011_samples.csv`, `cwvp_Fall2011_samples.csv`, `cwvp_Fall2012_samples.csv`, `cwvp_Fall2013_samples.csv` in `/home/claude/work/stage2/coastal_wetland_veg/extracted_csv/`. Read with `python3 -I`, pandas, latin-1, `low_memory=False`, all columns as strings.
- The same folder also holds `rapid_marsh_oiling_samples.csv` and `shoreline_baseline_2010_samples.csv`. They are not campaign files and were excluded.
- Filter: `Collection_Matrix == "Soil"` (exact label). Result: 330,464 rows, 14,926 distinct `Sample_ID`.
- Soil rows per campaign file: Fall2010 19,278; Spring2011 124,603; Fall2011 85,884; Fall2012 64,416; Fall2013 36,283.
- Scripts are in `/home/claude/work/phaseD/scripts/`. The filtered soil rows are in `/home/claude/work/phaseD/soil_rows.pkl`.
- Cross-check: the sample counts match `verify_counts.txt` (Soil 14,926 samples in the WETLAND group; per-file soil sample counts agree).

Exact `Collection_Matrix` labels in the five files: `Sediment`, `Soil`, `Tissue`, `Tarball`. Only `Soil` was kept.

## 1. Full column list with one example value each

The file has 60 columns. Example = first non-null value in file order on the soil rows. Non-null counts are out of 330,464 soil rows.

| # | Column | Non-null | Distinct | Example value |
|---|---|---|---|---|
| 1 | Date | 330464 | 211 | 2010-09-16 |
| 2 | Case-Activity | 330464 | 1 | Deepwater Horizon |
| 3 | QM_Site_ID | 330464 | 2 | Not Defined |
| 4 | Collection_Study_Name | 330464 | 5 | Shoreline-Coastal Wetland Vegetation Plan--2010 |
| 5 | QM_Study_ID | 330464 | 5 | Ma |
| 6 | Station-Site | 330464 | 202 | 1367 |
| 7 | Station_Group_List | 330464 | 1 | Deepwater Horizon (NRDA Trustee) |
| 8 | QM_Sample_ID | 330464 | 5 | Not Defined |
| 9 | Sample_ID | 330464 | 14926 | LAAP39-A0916-LJ401 |
| 10 | Collection_Matrix | 330464 | 1 | Soil |
| 11 | Species_Group | 330464 | 1 | Not Defined |
| 12 | Common_Name:_Species | 330464 | 1 | Not Defined |
| 13 | Latin_Name:_Genus | 330464 | 1 | Not Defined |
| 14 | Latin_Name:_Species | 330464 | 1 | Not Defined |
| 15 | Collection_Form | 330464 | 1 | Field Sample Form |
| 16 | Workspace_Name | 330464 | 1 | Not Defined |
| 17 | Data_Classification | 330464 | 1 | NRDA |
| 18 | Data_Source | 330464 | 1 | Shoreline Technical Workgroup |
| 19 | Source_Type | 330464 | 1 | DWH Trustee NRDA |
| 20 | Sharing_Status | 330464 | 2 | Publicly Available |
| 21 | Workgroup | 330464 | 1 | Shoreline |
| 22 | Collection_Workplan | 330464 | 5 | Coastal Wetland Vegetation Plan Fall 2010 |
| 23 | Habitat_Type | 330464 | 2 | Marsh |
| 24 | Organism_ID | 330464 | 1 | Not Defined |
| 25 | Results_Status | 330464 | 3 | Results Reported |
| 26 | DIVER_Dataset | 330464 | 1 | Samples - Southeast - DWH NOAA NRDA |
| 27 | File_Collection_ID | 330464 | 596 | 8006BEBF4838C6DB862577A8006D64F3 |
| 28 | Analysis_Category | 330464 | 3 | Composition |
| 29 | Analysis_Type | 330464 | 10 | Chemical Composition |
| 30 | Analysis | 330464 | 232 | Aluminum |
| 31 | Lab_Replicate | 330464 | 3 | Not Defined |
| 32 | Analysis_Result | 330464 | 14837 | 500 |
| 33 | Analysis_Result_Unit | 330464 | 13 | ug/L |
| 34 | Measurement_Basis | 330464 | 4 | Not Defined |
| 35 | QM_Matrix | 330464 | 3 | Not Applicable |
| 36 | Lab-Result_Matrix | 330464 | 5 | Other |
| 37 | Lab-Result_Matrix_Detailed | 330464 | 3 | Soil |
| 38 | Analysis_Method | 330464 | 52 | Aluminum Total EPA 200.7/6010 (ICP), SOP-MET-019-Rev-02 |
| 39 | Qualifier_Code | 330464 | 41 | U |
| 40 | Detection_Extent | 330464 | 6 | No Detection Limit Available |
| 41 | Review_Status | 330464 | 3 | Validated |
| 42 | Analysis_Detail | 330464 | 330464 | AEL Gainesville \| LAAP39-A0916-LJ401 \| 1009463-13 \| Aluminum \| Not Defined |
| 43 | Collection_Method | 330464 | 2 | Core |
| 44 | Depth_Category | 330464 | 3 | Not Applicable |
| 45 | Sample_Upper_Depth | 330464 | 3 | 0 |
| 46 | Sample_Lower_Depth | 330464 | 6 | 10 |
| 47 | Sample_Depth_Unit | 330464 | 2 | cm |
| 48 | Lab_ID | 330464 | 17325 | 1009463-13 |
| 49 | Sample_Type | 330464 | 2 | Not Defined |
| 50 | Result_Type | 330464 | 3 | Result |
| 51 | Lab_Name | 330464 | 4 | AEL Gainesville |
| 52 | Sample_Delivery_Group | 330464 | 319 | 1009463 |
| 53 | QM_Sample_Details | 330464 | 2534 | Not Defined-Ma-Not Defined-Not Defined |
| 54 | Tissue_Type | 330464 | 1 | Not Defined |
| 55 | Sex | 330464 | 2 | Not Applicable |
| 56 | Data_Category | 330464 | 1 | Samples |
| 57 | Start_Latitude | 330464 | 1064 | 29.47013 |
| 58 | Start_Longitude | 330464 | 1111 | -89.92517 |
| 59 | End_Latitude | 0 | 0 | (all null) |
| 60 | End_Longitude | 0 | 0 | (all null) |

## 2. Analytes

**Columns.** The analyte name is in `Analysis` (232 distinct names). The analyte group is in `Analysis_Type` (10 distinct values). The category is in `Analysis_Category` (3 distinct values). `Analysis_Detail` is a per-row composite string (330,464 distinct values, one per row) and is not an analyte field.

**Analysis_Category (rows):**
- Contaminant Chemistry: 239,366
- Composition: 84,093
- Not Defined: 7,005

**Analysis_Type within category (rows):**
- Contaminant Chemistry: PAH 126,280; ORGANIC 44,290; SVOL 33,388; Total PAH 23,452; CONVENT 11,130; GEOTECH 826
- Composition: Chemical Composition 69,250; Physical Composition 14,428; Organics Screening 415
- Not Defined: Not Defined 7,005

**PAH-type analytes, `Analysis_Type = PAH` (72 names, 126,280 rows).** Most names have 1,804 rows. Exceptions are listed in the table.

| Analyte | Rows |
|---|---|
| 2-Methylphenanthrene | 1,655 |
| 4/9-Methylphenanthrene | 1,655 |
| 9-Methylphenanthrene | 149 |
| 2/4-Methylphenanthrene | 149 |
| All other 68 names | 1,804 each |

The 68 names at 1,804 rows: 1-Methyldibenzothiophene; 1-Methylnaphthalene; 1-Methylphenanthrene; 2,3,5-Trimethylnaphthalene; 2,6-Dimethylnaphthalene; 2-Methylanthracene; 2-Methylnaphthalene; 2/3-Methyldibenzothiophene; 3-Methylphenanthrene; 4-Methyldibenzothiophene; Acenaphthylene; Acenaphthene; Benzo(a)fluoranthene; Benzo(a)anthracene; Anthracene; Benzo(b)fluoranthene; Benzo(b)fluorene; Benzo(b)thiophene; Benzo(a)pyrene; Benzo(e)pyrene; Biphenyl; Benzo(j+k)fluoranthene; Benzo(g,h,i)perylene; C1-Naphthalenes; C1-Naphthobenzothiophenes; C1-Phenanthrenes/anthracenes; C1-Benzo(b)thiophenes; C1-Chrysenes; C1-Dibenzothiophenes; C1-Fluoranthenes/pyrenes; C1-Fluorenes; C2-Chrysenes; C2-Dibenzothiophenes; C2-Fluoranthenes/pyrenes; C2-Benzo(b)thiophenes; C2-Fluorenes; C2-Phenanthrenes/anthracenes; C2-Naphthobenzothiophenes; C2-Naphthalenes; Fluorene; C4-Phenanthrenes/anthracenes; Carbazole; C3-Benzo(b)thiophenes; C3-Chrysenes; C3-Dibenzothiophenes; C3-Fluoranthenes/pyrenes; C3-Fluorenes; C3-Naphthalenes; C3-Naphthobenzothiophenes; C3-Phenanthrenes/anthracenes; C4-Benzo(b)thiophenes; C4-Chrysenes; C4-Dibenzothiophenes; C4-Fluoranthenes/pyrenes; C4-Naphthalenes; Perylene; Indeno(1,2,3-c,d)pyrene; Naphthalene; Chrysene + Triphenylene; Dibenzo(a,h+a,c)anthracene; Dibenzofuran; Dibenzothiophene; Fluoranthene; Retene; Phenanthrene; Pyrene; Naphthobenzothiophene.

**Total PAH, `Analysis_Type = Total PAH` (13 names, 23,452 rows, 1,804 each):** CROSS_TPAH; HPAH1; LPAH1; PAH16; PAH17; PAH34; PAH44; PAH45; PAH51; PAH52; PAH_SUMW; TOTAL_PAH; TOXPAH50.

**Ready-made totals (name search for Total, TPAH, Sum, TPH, Hopane, C30):**
- Total PAH type, all 13 names above (CROSS_TPAH, PAH_SUMW, TOTAL_PAH contain the matched substrings; 1,804 rows each). Their `Analysis_Result` is text, not a number (see section 7).
- `Total Extractable Hydrocarbons (C9-C44) (silca treated)`, ORGANIC, 975 rows, numeric, unit PPM.
- `Total Extractable Matter (C9-C44)`, ORGANIC, 7 rows.
- `Organic carbon, total`, CONVENT, 1,802 rows (not a hydrocarbon total).
- `Total Phosphorus`, Chemical Composition, 4,069 rows (not a hydrocarbon total).
- Hopane-named analytes: 20 names. `17a(H),21b(H)-Hopane (Hopane)` has 1,804 rows. The other 19 have 547 rows each (ORGANIC).
- C30-named analytes: `C30 Tricyclic Terpane-22R` (547), `C30 Tricyclic Terpane-22S` (547), `Triacontane (C30)` (SVOL, 982).
- TPH: not found as a name token. The only TPH-like name is the "Total Extractable Hydrocarbons" row above.

## 3. Units and measurement basis

**Analysis_Result_Unit (soil rows, all):** PPB 226,428; ug/L 31,630; mg/L 25,421; PCT 11,130; % by Weight 8,154; Not Available 7,005; % 6,696; Salinity units 4,064; pH Units 4,058; g/cubic cm 2,829; g/cm3 1,652; PPM 982; mg/kg wet 415.

**Units by Analysis_Category:**
- Contaminant Chemistry: PPB 226,428; PCT 11,130; PPM 982; g/cm3 826.
- Composition: ug/L 31,630; mg/L 25,421; % by Weight 8,154; % 6,696; Salinity units 4,064; pH Units 4,058; g/cubic cm 2,829; g/cm3 826; mg/kg wet 415.
- Not Defined: Not Available 7,005.

**Units by Analysis_Type (selected):** PAH = PPB (126,280); Total PAH = PPB (23,452); ORGANIC = PPB 43,308 and PPM 982; SVOL = PPB (33,388); CONVENT = PCT (11,130); GEOTECH = g/cm3 (826); Organics Screening = mg/kg wet (415).

**Measurement_Basis (soil rows, all):** Dry Weight 236,121; Not Defined 90,566; Wet Weight 3,245; dry 532 (lowercase label, Physical Composition only).

**Measurement_Basis by Analysis_Type (selected):** PAH = Dry Weight 125,790, Wet Weight 490; Total PAH = Dry Weight 23,361, Wet Weight 91; ORGANIC = Dry Weight 43,842, Wet Weight 448; Chemical Composition = Not Defined 69,250 (all rows).

**mg/L and ug/L on soil rows.** 57,051 rows, all in Analysis_Category = Composition and Analysis_Type = Chemical Composition. These are water-type units on rows labelled Soil.

- mg/L (25,421 rows), 8 analytes, example lab methods:
  - Total Phosphorus: "Total Phosphorus, Total EPA 365.3, SOP-059-Rev-01, Spectrophotometer" (4,069 rows)
  - Ammonia as N: "Ammonia, Total (as N) EPA 350.1, , SOP WC-019-Rev-05, Flow Analyzer" (4,066 rows)
  - Sulfate as SO4: "Sulfate, EPA 300.0, SOP-054-Rev-06, IC" (4,058 rows)
  - Nitrate/Nitrite as N: "Nitrate-Nitrite, Total EPA 353.2/SM4500 NO3-F, SOP-WC-012-Rev-10, Autoanalyzer" (2,654 rows)
  - Calcium, Magnesium, Potassium, Sodium: "... EPA 200.7/6010 (ICP) ..." (2,604 to 2,664 rows each, including minor method-string variants)
- ug/L (31,630 rows), 12 analytes, all "EPA 200.7/6010 (ICP)": Aluminum, Barium, Boron, Cadmium, Chromium, Copper, Iron, Lead, Manganese, Molybdenum, Nickel, Zinc (roughly 2,600 rows each, with variant method strings).
- Unit of the mg/L and ug/L rows has Measurement_Basis = Not Defined.

## 4. Censoring

**Numeric detection or reporting limit column:** not found. Column names were searched for limit, MDL, RL, DL, and detect. Only `Detection_Extent` matched. No value in `Analysis_Result` begins with "<" or ">" (0 rows).

**Detection_Extent, all soil rows (330,464):**
- Above Reporting Limit: 93,432
- No Detection Limit Available: 76,583
- At or Below Detection Limit: 73,590
- Between Detection Limit and Reporting Limit: 56,402
- See Analyte Level Details: 23,452
- No Results Available: 7,005

**Detection_Extent, PAH-type rows (149,732 = PAH 126,280 + Total PAH 23,452):**
- Above Reporting Limit: 50,604
- Between Detection Limit and Reporting Limit: 41,704
- At or Below Detection Limit: 33,972
- See Analyte Level Details: 23,452
- No Detection Limit Available: not present in PAH-type rows.

**Qualifier_Code, all soil rows (41 distinct values):** Not Available 116,736; J 93,164; U 68,500; F 11,257; FJ 10,037; UJ 4,797; CALC_050 3,602; CALC_016 1,803; CALC_044 1,803; CALC_051 1,803; CALC_017 1,803; CALC_015 1,803; CALC_045 1,799; CALC_052 1,799; CALC_018 1,799; CALC_031 1,799; CALC_008 1,798; CALC_010 1,792; Q-A 1,264; CALC 837; Not Defined 415; UCALC_010 10; CALC_049 8; UCALC_008 4; R 4; CALC_043 4; CALC_014 4; CALC_030 4; UCALC_050 2; CALC_007 2; CALC_009 2; UCALC_016 1; UCALC_044 1; UCALC_045 1; UCALC_051 1; UCALC_052 1; UCALC_017 1; UCALC_018 1; UCALC_015 1; UCALC_031 1; D-RNG 1.

**Qualifier_Code, PAH-type rows:** Not Available 41,753; J 50,732; U 26,621; FJ 3,585; F 3,484; UJ 101; R 4; CALC_050 3,602; CALC_016 1,803; CALC_044 1,803; CALC_051 1,803; CALC_017 1,803; CALC_015 1,803; CALC_045 1,799; CALC_052 1,799; CALC_018 1,799; CALC_031 1,799; CALC_008 1,798; CALC_010 1,792; CALC_049 8; CALC_043 4; CALC_014 4; CALC_030 4; CALC_007 2; CALC_009 2; UCALC_010 10; UCALC_008 4; UCALC_050 2; UCALC_016 1; UCALC_044 1; UCALC_045 1; UCALC_051 1; UCALC_052 1; UCALC_017 1; UCALC_018 1; UCALC_015 1; UCALC_031 1.

## 5. Sampling structure

**Stations.**
- `Station-Site` has 202 distinct values, including `Not Defined`. Excluding `Not Defined`, there are 201 station identifiers. Identifier formats vary (for example `1367`, `B-06`, `LA048`, `AL1095`, `SP-LA-M-MESS-1314`).
- Fall2013 soil rows: `Station-Site` = `Not Defined` on all 36,283 rows (2,558 samples). Fall2012 has 7 `Not Defined` rows.
- Distinct stations per campaign (excluding `Not Defined`): Fall2010 149; Spring2011 186; Fall2011 186; Fall2012 175; Fall2013 0.

**Stations by number of campaigns (excluding `Not Defined`, 201 stations):**
- 1 campaign: 14
- 2 campaigns: 3
- 3 campaigns: 60
- 4 campaigns: 124
- 5 campaigns: 0

If `Not Defined` is counted as one pseudo-station, the 2-campaign count becomes 4. Fall2013 cannot contribute to any station-level count as recorded.

**Station-campaign pairs:** 696 (excluding `Not Defined`); 698 including the `Not Defined` pairs.

**Soil samples per station-campaign (distinct `Sample_ID`, 696 pairs, excluding `Not Defined`).** Minimum 1, median 19, maximum 54.

| Samples | Pairs | Samples | Pairs | Samples | Pairs |
|---|---|---|---|---|---|
| 1 | 2 | 10 | 4 | 19 | 9 |
| 2 | 22 | 11 | 4 | 20 | 12 |
| 3 | 20 | 12 | 7 | 21 | 78 |
| 4 | 14 | 13 | 2 | 22 | 6 |
| 5 | 4 | 14 | 12 | 23 | 4 |
| 6 | 80 | 15 | 2 | 24 | 1 |
| 7 | 1 | 16 | 5 | 25 | 12 |
| 8 | 5 | 17 | 6 | 26 | 3 |
| 9 | 63 | 18 | 90 | 27 | 222 |

Sample counts 29, 34, 48, and 54 each have 2, 2, 1, and 1 pairs.

**Soil samples by campaign (distinct `Sample_ID`):** Fall2010 783; Spring2011 4,086; Fall2011 3,991; Fall2012 3,508; Fall2013 2,558. Total 14,926. Of these, 12,367 samples have a station identifier and 2,559 do not.

**Sample_ID linkage.** Each `Sample_ID` maps to exactly one campaign and exactly one `Station-Site`.

**Depth columns.**
- `Depth_Category`: Surface Sediment 238,096 rows; Not Applicable 92,003; Subsurface Sediment 365.
- `Sample_Upper_Depth`: 0 (329,135); -999 (905); 1 (424).
- `Sample_Lower_Depth`: 2 (236,813); 10 (92,430); -999 (905); 5 (270); 12 (26); 11 (20).
- `Sample_Depth_Unit`: cm (329,559); Not Defined (905).
- Upper/lower combinations present: 0-2 (7,256 Not Applicable plus 229,188 Surface Sediment); 0-10 (83,477 Not Applicable plus 8,898 Surface Sediment); 0-5 (270); 0-11 (10); 0-12 (26); 1-2 (365 Subsurface Sediment plus 4 Not Applicable); 1-10 (55); -999/-999 (905).
- `Collection_Method`: Grab 238,401; Core 92,063.

**Replicate and QC indicators.**
- `Lab_Replicate`: 1A 226,139; 2A 13,227; Not Defined 91,098. Each 2A row shares a (Sample_ID, Analysis) key with a 1A row (see section 7).
- `QM_Sample_ID`: L001 225,910; L002 12,551; B001 724; B002 181; Not Defined 91,098. The file does not define these labels.
- `Sample_Type`: Sample 239,366; Not Defined 91,098.
- `QM_Matrix`: Sediment 238,461; Not Applicable 91,098; Oil 905.
- `Lab-Result_Matrix`: Soil 263,364; Other 65,170; Tarball 905; Not Defined 614; Sediment 411.
- `Lab-Result_Matrix_Detailed`: Soil 322,749; Not Defined 6,810; Tarball 905.
- `Result_Type`: Result 300,007; Calculation 23,452; Status Information Only 7,005.
- Field-duplicate column: not found.
- Lab QC sample-type column (method blank, spike, duplicate): not found. Only the `Status Information Only` rows (7,005, Analysis_Type Not Defined) are non-result rows.
- Sample_ID substrings DUP, REP, BLANK, QC, SPK, RPD, FD: none found. "MS" occurs in 1,446 IDs, but as a site prefix (for example `MSAL42-...`), not as a QC flag.
- Composite suffix `_COMP`: 1,174 samples (all in Fall2013).

**Coordinates.**
- `Start_Latitude` and `Start_Longitude`: 330,464 of 330,464 rows (100%); 14,926 of 14,926 samples.
- `End_Latitude` and `End_Longitude`: present as columns, 0 non-null.
- Range: latitude 28.99769 to 30.3876; longitude -91.11186 to -87.45784.
- Fall2013: 2,558 samples have 447 distinct start coordinate pairs. This does not resolve the station gap.

## 6. Oiling descriptors at the station

**Oiling-related column names:** not found. Pattern search on column names (oil, SCAT, exposure, plot, reference, control, zone, design, treatment, strata, group) matched only `Station_Group_List` and `Sample_Delivery_Group`, `Species_Group`, and `Workgroup`.

**Oiling-related values:** not found. A keyword search (oiled, unoiled, reference, control, SCAT, exposure, zone, plot, study design, oiling) across all column values returned no hits. This search excluded `Analysis_Detail`, `Sample_ID`, `Lab_ID`, `QM_Sample_Details`, `Analysis`, and `Analysis_Method`.

**Columns that carry group-like labels (values and counts):**
- `Station_Group_List`: Deepwater Horizon (NRDA Trustee) 330,464 (one value).
- `Habitat_Type`: Marsh 329,732; Not Provided 732.
- `QM_Site_ID`: 0600 239,366; Not Defined 91,098.
- `QM_Study_ID` (one code per campaign file): Ma 19,278 (Fall2010); Mb 124,603 (Spring2011); M9 85,884 (Fall2011); Mn 64,416 (Fall2012); Mp 36,283 (Fall2013).
- `Collection_Study_Name`: Shoreline-Coastal Wetland Vegetation Plan--2010 (19,278); Spring 2011 (124,603); Fall 2011 (85,884); Fall 2012 (64,416); Fall 2013 (36,283).
- `Sharing_Status`: Publicly Available 323,459; Trustee and RP 7,005.

**Oil-labelled rows:** `QM_Matrix` = Oil on 905 rows (all Fall2013, `Lab-Result_Matrix` = Tarball, `Analysis_Category` = Contaminant Chemistry, depth -999). These are sample-matrix labels, not a station oiling class.

## 7. Issues that would block per-sample totals

1. **Duplicate sample-analyte rows.** 21,071 (Sample_ID, Analysis) keys have more than one row, covering 42,195 rows (21,018 keys with 2 rows; 53 keys with 3).
   - 13,227 of these keys are the 1A/2A `Lab_Replicate` pairs.
   - 7,844 keys have the same `Lab_Replicate` and still repeat. Every duplicate key has more than one `Lab_ID`.
   - 174 keys span two labs (Alpha Analytical and Columbia Analytical Services).
   - 5,932 keys have identical `Analysis_Result` across rows; 15,139 keys have differing `Analysis_Result` values; 4,358 keys have differing `Qualifier_Code`.
   - Adding `Analysis_Method` to the key does not reduce the duplicate count.
   - Replicate choice and lab choice must be decided before summing.

2. **Multiple methods for one analyte.** 177 of 232 analyte names have more than one `Analysis_Method` string. Example: alkylated PAHs appear under "8270 M - Alkylated PAHs" with Rev2, Rev4, Rev5, Rev6, and "RevO6" variants. Method strings also contain typos, for example "SOP-Met-)19-Rev-02" and a Manganese row carrying a Magnesium method string (29 rows). Method strings need normalising before grouping.

3. **Mixed units for one analyte.** Bulk Density has two unit strings: g/cm3 (826 rows, Fall2011) and g/cubic cm (2,829 rows, other campaigns). Within Contaminant Chemistry, units are PPB (PAH, ORGANIC, SVOL, Total PAH), PPM (ORGANIC TEH, 982 rows), and PCT (CONVENT). Units must be converted before any cross-type sum.

4. **Mixed dry and wet basis.** Measurement_Basis differs within totals: PAH rows have 490 Wet Weight rows; Total PAH rows have 91. Wet and dry must be harmonised before summing.

5. **Ready-made totals have no numeric result.** All 23,452 Total PAH rows (13 names) have `Analysis_Result` = "See Results for Specific Detection Limit Handling Methods", Result_Type = Calculation, Analysis_Method = Not Defined. They cannot be used as numeric totals and must not be added to analyte rows (double-count risk). The 126,280 PAH analyte rows contain no total.

6. **Censoring cannot be resolved from the file.** No numeric DL or RL column. Non-detect status is carried only as categories in `Detection_Extent` and `Qualifier_Code`. "No Detection Limit Available" appears on 76,583 rows overall (none on PAH-type rows). The file does not state the value to use for non-detects.

7. **Non-soil rows labelled Soil.** 57,051 mg/L or ug/L rows (water-type analytes) and 905 Tarball/Oil rows (QM_Matrix = Oil, depth -999) are inside `Collection_Matrix` = Soil. They must be excluded or handled separately.

8. **Station gap.** All 2,558 Fall2013 samples and 7 Fall2012 rows have `Station-Site` = Not Defined. Station-level aggregation cannot include them as recorded.

9. **PAH coverage.** 1,703 of 14,926 soil samples have any PAH-type row (Fall2010: none; Fall2011 471; Fall2012 413; Fall2013 307; Spring2011 512 sample-campaign counts, summing to 1,703 distinct samples).

10. **Non-result rows.** 7,005 rows are `Status Information Only` with Analysis = Not Defined, Analysis_Result = Not Available. These must be dropped before any count of analytes.
