"""Habitat table keyed to ESI (D36): alias resolution, NOAA transcription check, table provenance."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.shoreline_remediation import habitat as hab  # noqa: E402
from src.shoreline_remediation import knowledge  # noqa: E402

ALIASES = {"sand_beach": "3A", "sandy_beach": "3A", "coarse_sand_beach": "4", "mixed_sediment": "5", "mixed": "5",
           "gravel_beach": "6A", "cobble": "6A", "marsh": "10A", "salt_marsh": "10A", "salt marsh": "10A", "Salt-Marsh": "10A",
           "rock": "1A", "bedrock": "1A", "rocky_shore": "1A", "boulder": "1A", "mangrove": "10D", "mudflat": "9A",
           "peat": "8E", "tundra": "10E"}


@pytest.mark.parametrize("name,esi", ALIASES.items())
def test_normalise_every_string_in_use(name, esi):
    assert hab.normalise(name) == esi


def test_normalise_unknown_and_strict():
    assert hab.normalise("lava field") == "unknown" and hab.habitat_class("lava field") == "other"
    with pytest.raises(KeyError):
        hab.normalise("lava field", strict=True)


def test_cobble_is_a_gravel_beach_everywhere():
    assert hab.rule_key("cobble") == "gravel_beach" and hab.habitat_class("cobble") == "sand/gravel beach"


def test_rocky_exposure_split():
    assert hab.normalise("bedrock", "low") == "8A" and hab.normalise("bedrock", "high") == "1A"
    assert hab.normalise("sand_beach", "low") == "3A"


def test_required_habitats_and_descriptors():
    t = hab.table()
    assert {"3A", "4", "5", "6A", "10A", "10D", "1A", "8A"} <= set(t)
    assert t["3A"].tier == t["4"].tier == t["5"].tier == t["6A"].tier == "rules_and_literature"
    assert "50 cm" in t["5"].oil_penetration_depth and "asphalt" in t["5"].asphalt_pavement_risk
    assert "storm berms" in t["6A"].burial_risk


def test_habitat_tables_have_source_and_status():
    for path in (knowledge.HABITAT_CSV, knowledge.NOAA_RATING_CSV, knowledge.NOAA_MAPPING_CSV, knowledge.NOAA_OIL_CSV, knowledge.BEACH_NOTES_CSV):
        df = pd.read_csv(path, dtype=str)
        assert df.source.notna().all() and df.status.notna().all(), path.name


def test_noaa_mapping_matches_d36():
    m = knowledge.load_noaa_mapping()
    assert [m[x]["verdict"] for x in "ABCD"] == ["eligible", "eligible", "conditional", "ineligible"] and m["-"]["verdict"] == "ineligible"
    assert m["I"]["verdict"] == "conditional"


def test_spot_values_from_noaa_tables():
    r = knowledge.noaa_rating
    assert r("3A", "high_pressure_heated_washing", "heavy")["rating"] == "-"
    assert r("3A", "low_pressure_heated_flushing", "medium")["rating"] == "C"
    assert r("5", "high_pressure_washing", "heavy")["rating"] == "D" and r("5", "high_pressure_heated_washing", "medium")["rating"] == "D"
    assert r("6A", "mechanical_removal", "light")["rating"] == "D" and r("6A", "high_pressure_heated_washing", "heavy")["rating"] == "C"
    assert r("1A", "high_pressure_heated_washing", "heavy")["rating"] == "C" and r("8A", "high_pressure_heated_washing", "heavy")["rating"] == "D"


@pytest.mark.skipif(shutil.which("pdftotext") is None, reason="pdftotext not installed")
def test_transcription_matches_the_pdf_text():
    pdf = ROOT / "docs" / "reference" / "literature" / "NOAA_2017_CharacteristicCoastalHabitats.pdf"
    if not pdf.exists():
        pytest.skip("PDF not present")
    pages = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout.split("\f")
    df = knowledge.load_noaa_ratings()
    for r in df.itertuples():
        txt = pages[int(r.page) - 1]
        m = re.search(re.escape(r.noaa_method) + r"\s+(\S)\s+(\S)\s+(\S)\s+(\S)\s+(\S)", txt)
        got = [x.replace("–", "-") for x in m.groups()]
        assert got == [r.cat_I, r.cat_II, r.cat_III, r.cat_IV, r.cat_V], (r.rating_id, got)
