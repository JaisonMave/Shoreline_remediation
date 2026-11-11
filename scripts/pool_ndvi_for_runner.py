"""Turn per-scene, per-segment Landsat NDVI (scripts/landsat_ndvi.py) into the input of
validation.satellite_recovery: columns date, site ('oiled' / 'reference'), ndvi, pixels.

Fixed before any NDVI was inspected (2026-11-11):
  pooled          every oiled segment vs every reference segment, combined per scene as a pixel-weighted mean
  by_reference_k  oiled segments paired to reference segment k, against that segment only
Usage: python scripts/pool_ndvi_for_runner.py scenes.csv out_dir
"""
import sys
from pathlib import Path

import pandas as pd


def pool(df: pd.DataFrame) -> pd.DataFrame:
    df = df.assign(w=df.ndvi * df.n_pixels)
    g = df.groupby(["date", "group"]).agg(w=("w", "sum"), pixels=("n_pixels", "sum")).reset_index()
    g["ndvi"] = g.w / g.pixels
    return g.rename(columns={"group": "site"})[["date", "site", "ndvi", "pixels"]]


def main(scenes: str, out_dir: str) -> None:
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(scenes)
    # Two overlapping WRS rows can image the same site on the same day: average those first.
    df = df.groupby(["date", "pair", "group", "segment"], as_index=False).agg(ndvi=("ndvi", "mean"), n_pixels=("n_pixels", "max"))
    pool(df).to_csv(out / "ndvi_pooled.csv", index=False)
    ref_of_pair = df[df.group == "reference"].drop_duplicates("pair").set_index("pair").segment
    df["ref_segment"] = df.pair.map(ref_of_pair)
    for ref, sub in df.groupby("ref_segment"):
        sub = sub.drop_duplicates(["date", "group", "segment"])
        pool(sub).to_csv(out / f"ndvi_by_reference_{ref}.csv", index=False)
        print(ref, "oiled segments:", sub[sub.group == "oiled"].segment.nunique())


if __name__ == "__main__":
    main(*sys.argv[1:3])
