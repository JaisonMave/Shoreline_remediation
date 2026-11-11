#!/usr/bin/env bash
# Download Deepwater Horizon SCAT layers for Louisiana from NCEI Accession 0163818 (DOI 10.7289/v53t9ffx).
# The landing page lists no file links and NCEI's download service returned 502 errors on 2026-11-11;
# the archive folder below works over HTTPS. FTP (ftp-oceans.ncei.noaa.gov) was blocked from the cloud session.
set -euo pipefail
OUT=${1:-data/raw/scat}
B=https://www.ncei.noaa.gov/data/oceans/archive/arc0110/0163818/1.1/data/0-data
get(){ mkdir -p "$OUT/$1"; for e in dbf prj shp shx shp.xml; do curl -fsS -o "$OUT/$1/$2.$e" "$B/$1/data/$2.$e"; done; }
get 18611 SCAT_Max_OilZones_Louisiana_2014_09_30Sorted     # maximum oiling per zone, Louisiana (Houma)
get 18612 SCAT_Shoreline_All_Surveys_Louisiana_2014_09_30  # every survey, incl. 'NOO' (no oil observed)
