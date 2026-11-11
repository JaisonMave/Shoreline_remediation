#!/usr/bin/env bash
# Run landsat_edge_fraction.py on four spatial quadrants of a basin (split at the median cell ix, iy) to
# fit in memory. Water and marsh calibration values are then taken per quadrant (P2 plan, amendment 3).
# Usage: scripts/landsat_split.sh BASIN_DIR    (needs BASIN_DIR/cells_10A.csv and naip2010_land16.tif)
# Output: BASIN_DIR/q0..q3/{landsat_cell_fraction.csv, scene_endmembers.csv, landsat_log.txt}.
# Combining quadrants is a separate step because the validity rule decides which quadrants are kept.
set -uo pipefail
d=${1:?basin dir}; S=$(cd "$(dirname "$0")" && pwd)
python3 -I - "$d" <<'P'
import sys, os, pandas as pd
d = sys.argv[1]; c = pd.read_csv(f"{d}/cells_10A.csv")
mx, my = c.ix.median(), c.iy.median()
for q, (sx, sy) in enumerate([(0, 0), (0, 1), (1, 0), (1, 1)]):
    sub = c[((c.ix >= mx) == bool(sx)) & ((c.iy >= my) == bool(sy))]
    os.makedirs(f"{d}/q{q}", exist_ok=True); sub.to_csv(f"{d}/q{q}/cells_10A.csv", index=False); print(q, len(sub))
P
for q in 0 1 2 3; do
  python3 -I -u "$S/landsat_edge_fraction.py" "$d/q$q/cells_10A.csv" "$d/naip2010_land16.tif" "$d/q$q" --epochs AB \
    > "$d/q$q/landsat_log.txt" 2>&1 || echo "Q$q FAILED (no scene passed the contrast check, or out of memory)"
done
