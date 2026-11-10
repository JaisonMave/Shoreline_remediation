"""Load the 70-incident hypothetical OSRM dataset (Appendix C of the UBC thesis).

The values are parsed from the supplied PDF, never retyped, and checked against the
Table 5 incident reported in Mohammadiun et al. (2022), J. Hazard. Mater. 436:129282.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
from PyPDF2 import PdfReader

PROJECT_ROOT = Path(__file__).resolve().parents[1]
THESIS_PDF = PROJECT_ROOT / "docs" / "reference" / "UBC_2023_november_mohammadiun_saeed.pdf.pdf"
DATASET_CSV = PROJECT_ROOT / "data" / "mohammadiun_appendixC_dataset.csv"
APPENDIX_C_PAGE = 210

# Thesis Appendix C labels A1..A6; A5 is floating sea ice and A6 is remoteness.
FEATURES = [
    "oil_api",
    "slick_thickness_mm",
    "slick_continuity_pct",
    "wave_height_m",
    "sea_ice_pct",
    "remoteness_km",
]
TARGETS = ["MCR", "ISB", "UCD"]
_COLUMNS = ["incident_id", *FEATURES, *TARGETS]
_HEADER = re.compile(r"(?:No\.\s+A1\s+A2\s+A3\s+A4\s+A5\s+A6\s+MCR\s+ISB\s+UCD\s*){2}")


def parse_appendix_c(pdf_path: Path = THESIS_PDF) -> pd.DataFrame:
    text = PdfReader(str(pdf_path)).pages[APPENDIX_C_PAGE - 1].extract_text() or ""
    header = _HEADER.search(text)
    if header is None:
        raise ValueError("Appendix C header not found; check APPENDIX_C_PAGE.")
    body = text[header.end(): text.index("Note:", header.end())]
    tokens = [float(token) for token in body.split()]
    if len(tokens) != 700:
        raise ValueError(f"Expected 700 numeric tokens, found {len(tokens)}.")

    rows = [tokens[i: i + 10] for i in range(0, 700, 10)]
    # The printed table interleaves incidents 1..35 with 36..70 side by side.
    expected_ids = [value for pair in zip(range(1, 36), range(36, 71)) for value in pair]
    if [int(row[0]) for row in rows] != expected_ids:
        raise ValueError("Incident numbering does not match the expected two-column layout.")

    frame = pd.DataFrame(rows, columns=_COLUMNS)
    frame["incident_id"] = frame["incident_id"].astype(int)
    return frame.sort_values("incident_id").reset_index(drop=True)


def verify_dataset(frame: pd.DataFrame) -> dict:
    """Return named checks; every value must be True for the dataset to be trusted."""
    row50 = frame.loc[frame["incident_id"] == 50].iloc[0]
    paper_table5 = [30, 1.6, 59, 0.5, 3, 460]  # paper Table 5 note: F1..F4, ice, remoteness
    scores = row50[TARGETS].astype(float)
    return {
        "70_rows": len(frame) == 70,
        "unique_ids_1_to_70": sorted(frame["incident_id"]) == list(range(1, 71)),
        "no_missing_values": not frame.isna().any().any(),
        "scores_within_0_10": bool(((frame[TARGETS] >= 0) & (frame[TARGETS] <= 10)).all().all()),
        "row50_matches_paper_table5": bool(np.allclose(row50[FEATURES].astype(float), paper_table5)),
        "row50_expert_choice_is_ISB": scores.idxmax() == "ISB",
    }


def load_dataset(refresh: bool = False) -> pd.DataFrame:
    if DATASET_CSV.exists() and not refresh:
        return pd.read_csv(DATASET_CSV)
    frame = parse_appendix_c()
    DATASET_CSV.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(DATASET_CSV, index=False)
    return frame


if __name__ == "__main__":
    data = load_dataset(refresh=True)
    checks = verify_dataset(data)
    for name, ok in checks.items():
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    print(data.describe().loc[["min", "max"]].round(2).to_string())
