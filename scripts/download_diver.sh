#!/usr/bin/env bash
# Re-fetch the NOAA DIVER Deepwater Horizon sample tar files catalogued as EXT-DIVER-WETLAND and EXT-DIVER-NEARSHORE.
# URLs are the ones used on 2026-11-12 (HTTP 200 then). About 0.5 GB in total; the tars are git-ignored
# (data/external/diver_dwh/) and not catalogued. Each tar holds one long-format CSV plus a data-spec PDF and ISO XML.
# Not covered: ERMA accession 0163814 (download timed out), FieldObservations, Photographs and RelatedFiles tars.
# Usage: scripts/download_diver.sh [outdir]   (default data/external/diver_dwh)
set -euo pipefail
OUT=${1:-data/external/diver_dwh}
S=https://www.ncei.noaa.gov/data/deepwater-horizon-diver-system/archive/Shoreline
N=https://www.ncei.noaa.gov/data/deepwater-horizon-diver-system/archive/NearshoreSedimentandWater
get(){ # base subpath
  local f="${2##*/}"; mkdir -p "$OUT/$3"
  curl -fsSL --connect-timeout 30 --max-time 1500 -o "$OUT/$3/$f" "$1/$2"; echo "$3/$f"
}
# Shoreline: Coastal Wetland Vegetation Plan, Rapid Marsh Oiling Assessment, Shoreline Baseline 2010
for p in \
 "RapidMarshOilingAssessment/DWH_DIVER_Shoreline_RapidMarshOilingAssessment_Samples_Part0001_s20100919_e20100919_c20171128.tar" \
 "Shoreline-Baseline-2010/DWH_DIVER_Shoreline_Shoreline-Baseline-2010_Samples_Part0001_s20100524_e20100528_c20171128.tar" \
 "CoastalWetlandVegetationPlanFall2010/DWH_DIVER_Shoreline_CoastalWetlandVegetationPlanFall2010_ArchivePackageContents_c20181114.txt" \
 "CoastalWetlandVegetationPlanFall2010/DWH_DIVER_Shoreline_CoastalWetlandVegetationPlanFall2010_Samples_Part0001_s20100916_e20110107_c20171128.tar" \
 "CoastalWetlandVegetationPlanSpring2011/DWH_DIVER_Shoreline_CoastalWetlandVegetationPlanSpring2011_Samples_Part0001_s20110409_e20110608_c20171128.tar" \
 "CoastalWetlandVegetationPlanFall2011/DWH_DIVER_Shoreline_CoastalWetlandVegetationPlanFall2011_Samples_Part0001_s20110917_e20111102_c20171128.tar" \
 "CoastalWetlandVegetationPlanFall2012/DWH_DIVER_Shoreline_CoastalWetlandVegetationPlanFall2012_Samples_Part0001_s20120926_e20121209_c20171128.tar" \
 "CoastalWetlandVegetationPlanFall2013/DWH_DIVER_Shoreline_CoastalWetlandVegetationPlanFall2013_Samples_Part0001_s20130923_e20131211_c20171128.tar"; do
  get "$S" "$p" shoreline
done
# Nearshore Sediment and Water: Baseline and Preassessment Louisiana, Blank Study 2011
for p in \
 "NearshoreSedimentandWaterBaselineSamplingforLouisiana/DWH_DIVER_NearshoreSedimentandWater_NearshoreSedimentandWaterBaselineSamplingforLouisiana_Samples_Part0001_s20100621_e20100716_c20171128.tar" \
 "NearshoreSedimentandWaterPreassessmentSamplingforLouisiana/DWH_DIVER_NearshoreSedimentandWater_NearshoreSedimentandWaterPreassessmentSamplingforLouisiana_Samples_Part0001_s20100723_e20110324_c20171128.tar" \
 "NearshoreSedimentandWaterBaselineSamplingforLouisiana/DWH_DIVER_NearshoreSedimentandWater_NearshoreSedimentandWaterBaselineSamplingforLouisiana_ArchivePackageContents_c20181114.txt" \
 "NearshoreSedimentandWaterPreassessmentSamplingforLouisiana/DWH_DIVER_NearshoreSedimentandWater_NearshoreSedimentandWaterPreassessmentSamplingforLouisiana_ArchivePackageContents_c20181114.txt" \
 "NearshoreSedWater-BlankStudy-2011/DWH_DIVER_NearshoreSedimentandWater_NearshoreSedWater-BlankStudy-2011_Samples_Part0001_s20110218_e20110221_c20171128.tar" \
 "NearshoreSedWater-BlankStudy-2011/DWH_DIVER_NearshoreSedimentandWater_NearshoreSedWater-BlankStudy-2011_ArchivePackageContents_c20181114.txt"; do
  get "$N" "$p" nearshore
done
echo "Done. Compare tar SHA-256 values with the Stage 2 inventory (docs/STAGE2_INVENTORY.md or inventory_noaa_beach.md)."
