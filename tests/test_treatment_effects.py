import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.shoreline_remediation import treatment_effects as te  # noqa: E402


def test_table_matches_s1_spreadsheet_counts():
    df = te.load()
    assert len(df) == 86
    nt = df[(df.study == "main") & (df.year == 2012) & (df.treatment == "No Treatment")
            & (df.metric == "Total Vegetation Cover (%)")].iloc[0]
    assert (nt["mean"], nt.se, nt.n) == (18.0, 3.0, 9)


def test_welch_contrast_equal_groups_matches_pooled_t():
    # equal n and SE: Welch df equals 2(n-1)
    c = te.welch_contrast(10, 1, 5, 0, 1, 5)
    assert c["df"] == pytest.approx(8)
    assert c["se"] == pytest.approx(math.sqrt(2))


def test_manual_effect_on_vegetation_year2():
    e = te.effect_table()
    r = e[(e.comparison == "Manual Treatment vs No Treatment") & (e.year == 2012)
          & (e.metric == "Total Vegetation Cover (%)")].iloc[0]
    assert r.effect == pytest.approx(52 - 18)
    assert r.lo > 0


def test_planting_contrast_is_flagged_randomized():
    e = te.effect_table()
    p = e[e.comparison.str.startswith("Planting")]
    assert set(p.design) == {"randomized"} and len(p) == 2


def test_prior_scope_and_no_extrapolation():
    p = te.treatment_prior("manual", 2, habitat="sand beach")
    assert not p.in_scope
    with pytest.raises(ValueError):
        te.treatment_prior("manual", 5)
