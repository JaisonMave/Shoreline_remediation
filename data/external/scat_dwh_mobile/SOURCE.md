# DWH SCAT layer 18613 "SCAT All zones, Mobile" (Alabama, Mississippi, Florida panhandle)

- **Source**: NOAA NCEI Accession 0163818, "Shoreline Cleanup and Assessment Techniques (SCAT) Data", version 1.1,
  DOI 10.7289/v53t9ffx. Layer folder 18613 ("27-Sep-14 Cumulative Oiling Ground Observations"), file
  `SCAT_AllZones_Mobile_2014_0927Sorted` (.dbf 46,169,684 bytes, .shp, .shx, .prj, .cpg, .shp.xml, .html).
  Originator: MC252 Gulf Shores Incident Command Post Environmental Unit. Metadata date 2015-04-17.
- **URL**: https://www.ncei.noaa.gov/data/oceans/archive/arc0110/0163818/1.1/data/0-data/18613/data/
  (accession metadata in https://www.ncei.noaa.gov/data/oceans/archive/arc0110/0163818/1.1/about/)
- **Fetched**: 14 Nov 2026 by `bash scripts/download_scat_mobile.sh` (raw files in `data/raw/scat_mobile/`, not in
  git; SHA-256 checksums in `data/raw/scat_mobile/FETCHED.txt`; dbf sha256 eca46033...b8582).
- **How read**: `pyogrio.read_dataframe` (geopandas 1.2.0, pyogrio 0.13.0), CRS EPSG:4326; lengths in UTM 16N
  (EPSG:32616). 40,427 zone-survey records, 3,007 segments, 2010-05-05 to 2013-06-18. Team member name fields
  (Team1-Team8) are dropped on reading and never written.
- **Access constraints**: none ("Not for navigation").

## Field meanings (from the layer's FGDC metadata, `.html` / `.shp.xml`, read 14 Nov 2026)

| Field | Meaning |
|---|---|
| `Segment` (= `SegNum`) | Unique shoreline segment ID (operational division + number); `SegLength` its length (m) |
| `SurvDate` | Survey date |
| `Zone` | Zone ID, **unique only within a segment and date; IDs on different dates are unrelated** |
| `ESIType` | NOAA ESI shoreline type: 3A fine-to-medium sand beach, 4 coarse sand beach, 5 mixed sand and gravel, 6A gravel beach, 6B riprap, 10A salt/brackish marsh, etc. (3,959 records blank, 3,858 of them NOO) |
| `OilCatCode` / `OilingCat` | Summary oiling category: NOO (no oil observed), Neg_TB, Light_TB, Mod_TB, Heavy_TB (trace tarball categories), Very_Light, Light, Moderate, Heavy; 4 records "Undefined". Computed by the SCAT database from a lookup matrix (the Stage I/II Response Plan, not in the archive) |
| `oil_order` | Order of OilCatCode: NOO 1, Neg_TB 2, Light_TB 3, Mod_TB 4, Heavy_TB 5, Very_Light 6, Light 7, Moderate 8, Heavy 9 |
| `OilingChar` | Surface oil character: FR fresh, MS mousse, TB tarballs, PT patties, TC tar, SR surface residue, AP asphalt pavement, NOO |
| `SODistro` | Surface oil distribution, % (0 on all tarball-category records) |
| `SOThicknes` | Surface oil thickness: PO pooled >1 cm, CV cover 0.1-1 cm, CT coat 0.01-0.1 cm, ST stain <0.01 cm ("FL", 10 records, not in the domain) |
| `TidalZone` | SU upper shore (supratidal), UI upper, MI middle, LI lower intertidal (blank on most NOO records) |
| `TBCount`, `TBArea`, `TBAreaUnit`, `TBType`, `TBAvgSize`, `TBMaxSize` | Tarball count, area (units mixed: m2, m, "Segment", "Zone"), type (Weathered, Oil Residue, Sticky, Fresh, Emulsion), sizes |
| `IsPrimary` | Primary zone of the segment's survey |

No treatment fields exist in this layer.

## Derived files (built by `python scripts/build_beach_series.py`; definitions in docs/V5_BEACH_SAND_PLAN.md)

- `beach_visits.csv`: one row per segment x survey date (28,628): status (oiled / clear / partial_clear), top
  category, tidal zone, thickness, SODistro of the most oiled zone, summed tarball count, survey cover fraction.
- `beach_series.csv`: one row per segment (3,007): ESI class (3A if >= 80% of ESI-coded length is 3A, ASSUMED),
  exposure proxy, midpoint lon/lat, predictors at the first oiled visit, clearing interval `L_days`/`R_days`
  (R empty = right-censored), alternative interval with partial-clear visits counted as clear (`alt_*`),
  visit-gap statistics (sensitivity only), re-oiling fields.
- `counts_check.json`: structural counts, including the reproduction of the earlier agent's counts.
