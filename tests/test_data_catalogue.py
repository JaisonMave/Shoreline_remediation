"""P4: the catalogue matches the data on disk, and every dictionary variable exists and is within range."""
import glob
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_catalogue as bc  # noqa: E402

CATALOGUE = pd.read_csv(ROOT / "data" / "meta" / "catalogue.csv", dtype=str)
DICTIONARY = pd.read_csv(ROOT / "data" / "meta" / "variable_dictionary.csv", dtype=str).fillna("")


def test_every_data_file_is_catalogued_and_unchanged():
    current = bc.build().set_index("file")
    saved = CATALOGUE.set_index("file")
    assert set(current.index) == set(saved.index), "files added or removed: rerun scripts/build_catalogue.py"
    assert (current.dataset_id != "UNCATALOGUED").all(), current[current.dataset_id == "UNCATALOGUED"].index.tolist()
    changed = [f for f in current.index if current.at[f, "sha256"] != saved.at[f, "sha256"]]
    assert not changed, f"data changed without a catalogue rebuild: {changed}"


def test_every_dataset_with_patterns_has_files():
    for d in bc.DATASETS:
        if d["patterns"]:
            assert (CATALOGUE.dataset_id == d["id"]).any(), d["id"]


def _frames(spec: str):
    if "::" in spec:
        path, sheet = spec.split("::")
        yield path, pd.read_excel(ROOT / path, sheet_name=sheet)
        return
    paths = sorted(glob.glob(str(ROOT / spec)))
    assert paths, f"no file matches {spec}"
    for p in paths:
        yield p, pd.read_csv(p, low_memory=False)


@pytest.mark.parametrize("row", DICTIONARY.to_dict("records"), ids=lambda r: r["variable"])
def test_dictionary_variable_present_and_valid(row):
    for spec in row["files"].split(";"):
        for path, d in _frames(spec):
            assert row["variable"] in d.columns, f"{row['variable']} missing from {path}"
            col = d[row["variable"]]
            if row["allowed_values"]:
                allowed = set(row["allowed_values"].split("|"))
                bad = set(col.dropna().astype(str).str.strip()) - allowed
                assert not bad, f"{row['variable']} in {path}: unexpected values {sorted(bad)[:5]}"
            if row["valid_min"] or row["valid_max"]:
                x = pd.to_numeric(col, errors="coerce").dropna()
                if row["valid_min"]:
                    assert (x >= float(row["valid_min"]) - 1e-9).all(), f"{row['variable']} below range in {path}"
                if row["valid_max"]:
                    assert (x <= float(row["valid_max"]) + 1e-9).all(), f"{row['variable']} above range in {path}"
