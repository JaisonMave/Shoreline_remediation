"""P3 helpers: pre-spill change per plot, contrasts and the bootstrap rank correlation, on made-up data."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from validation import p3_treatment_erosion as p3  # noqa: E402


def test_prespill_change_and_contrast():
    rows = []
    rng = np.random.default_rng(1)
    for pid in range(30):
        grp = ["Oiled, untreated", "Manual", "Reference (unoiled)"][pid % 3]
        pre = 1.0 + rng.normal(0, 0.05)
        post = pre + {"Oiled, untreated": 1.0, "Manual": 1.5, "Reference (unoiled)": 0.0}[grp] + rng.normal(0, 0.05)
        rows += [{"PLOT_ID": pid, "group": grp, "TIME_PERIOD": "2005-2010", "EROSION_RATE": pre},
                 {"PLOT_ID": pid, "group": grp, "TIME_PERIOD": "2010-2012", "EROSION_RATE": post}]
    w = p3.prespill_change(pd.DataFrame(rows), "2010-2012")
    c = p3.contrasts(w, "change", "t").set_index("contrast")
    assert abs(c.loc["Manual minus Oiled, untreated", "difference"] - 0.5) < 0.1
    assert abs(c.loc["Oiled, untreated minus Reference (unoiled)", "difference"] - 1.0) < 0.1
    assert c.loc["Manual minus Oiled, untreated", "excludes_zero"]


def test_spearman_boot_detects_monotone_relation():
    x = np.arange(20.0); y = x + np.random.default_rng(0).normal(0, 2, 20)
    rho, lo, hi = p3.spearman_boot(x, y, n=500)
    assert rho > 0.8 and lo > 0.5
