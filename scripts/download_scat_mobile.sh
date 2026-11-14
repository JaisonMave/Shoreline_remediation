#!/usr/bin/env bash
# Download the Deepwater Horizon SCAT layer 18613 "SCAT All zones, Mobile" (Alabama, Mississippi, Florida
# panhandle; every zone-survey record, including 'NOO' = no oil observed) from NCEI Accession 0163818
# (DOI 10.7289/v53t9ffx), plus its metadata. Modelled on scripts/download_scat.sh (Louisiana layers).
#
# Raw files go to data/raw/scat_mobile/ (data/raw/ is git-ignored). The compact derived table that the
# analysis needs is built by scripts/build_beach_series.py and committed under data/external/scat_dwh_mobile/.
#
# Usage:  bash scripts/download_scat_mobile.sh [out_dir]
set -euo pipefail
OUT=${1:-data/raw/scat_mobile}
A=https://www.ncei.noaa.gov/data/oceans/archive/arc0110/0163818/1.1
B=$A/data/0-data
NAME=SCAT_AllZones_Mobile_2014_0927Sorted
mkdir -p "$OUT/18613/data" "$OUT/18613/documentation" "$OUT/about"
# Shapefile components and the per-layer metadata (.shp.xml, .html)
for e in dbf shp shx prj cpg shp.xml html; do
  curl -fsS --retry 3 -o "$OUT/18613/data/$NAME.$e" "$B/18613/data/$NAME.$e"
done
# Layer documentation (ArcGIS service JSON with field aliases and the layer description page)
curl -fsS --retry 3 -o "$OUT/18613/documentation/1.json" "$B/18613/documentation/1.json"
curl -fsS --retry 3 -o "$OUT/18613/documentation/SCATAllZonesMobile20140927Sorted.html" \
     "$B/18613/documentation/SCATAllZonesMobile20140927Sorted.html"
# Accession-level metadata
curl -fsS --retry 3 -o "$OUT/README.txt" "$B/README.txt"
for f in 0163818_Layer_Descriptions.txt Shoreline_Cleanup_and_Assessment_Techniques_SCAT_Data_metadata.xml journal.txt; do
  curl -fsS --retry 3 -o "$OUT/about/$f" "$A/about/$f"
done
curl -fsS --retry 3 -o "$OUT/NODC-Readme.txt" "$A/NODC-Readme.txt"
# Record what was fetched and when
( cd "$OUT" && date -u +"fetched %Y-%m-%dT%H:%M:%SZ" > FETCHED.txt && find . -type f ! -name FETCHED.txt -exec sha256sum {} + | sort -k2 >> FETCHED.txt )
echo "done: $OUT"
