#!/usr/bin/env bash
# Rebuild the P2 per-basin measurement tables (docs/P2_BASIN_HOLDOUT_PLAN.md), as run on 2026-11-11.
# Usage: scripts/run_p2_measurements.sh WORK_DIR
#   WORK_DIR/<basin>/cells.gpkg must exist (from build_edge_cells.py --louisiana + assign_basins.py, split by basin).
# Steps per basin: NAIP land fraction 2010/2015 -> 2010 exposure -> Landsat pre-spill fractions (epochs A, B).
# Breton and Barataria need the quadrant split (memory, about 4 GB per whole basin): scripts/landsat_split.sh.
# Runs one basin at a time; running two at once exceeded 7 GB on the development machine.
set -uo pipefail
W=${1:?work dir}; S=$(cd "$(dirname "$0")" && pwd)
for b in terrebonne birdfoot breton barataria; do
  d=$W/$b
  echo "== $b NAIP $(date +%T)"
  python3 -I -u "$S/naip_edge_extract.py" "$d/cells.gpkg" "$d" --years 2010,2015 > "$d/naip_log.txt" 2>&1 || echo "NAIP FAILED $b"
  echo "== $b exposure $(date +%T)"
  python3 -I -u "$S/exposure_metrics.py" "$d/cells_10A.csv" "$d" > "$d/exposure_log.txt" 2>&1 || echo "EXPOSURE FAILED $b"
  if [ "$b" = breton ] || [ "$b" = barataria ]; then
    "$S/landsat_split.sh" "$d"
  else
    python3 -I -u "$S/landsat_edge_fraction.py" "$d/cells_10A.csv" "$d/naip2010_land16.tif" "$d" --epochs AB > "$d/landsat_log.txt" 2>&1 || echo "LANDSAT FAILED $b"
  fi
done
echo "Then apply the validity rule (plan amendment 3): keep only quadrants where >= 50% of scenes in each epoch"
echo "pass the contrast check (scene_endmembers.csv 'used'), and copy the kept quadrants' rows into the basin's"
echo "landsat_cell_fraction.csv. Kept on 2026-11-11: breton q0,q1; barataria q1,q2,q3; birdfoot none."
