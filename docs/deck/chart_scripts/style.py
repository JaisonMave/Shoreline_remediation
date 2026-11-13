"""Shared chart style for the deck. Source files are read from the repository results folders (read-only)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import glob
for f in glob.glob("/usr/share/fonts/opentype/inter/Inter-*.otf") + glob.glob("/usr/share/fonts/truetype/inter/*.ttf"):
    try: fm.fontManager.addfont(f)
    except Exception: pass
BG, INK = "#F3F0E8", "#14262E"
OIL, WATER, MARSH, GREY = "#D9692B", "#2C6E9B", "#3E7A4F", "#5B6A70"
REPO = "/home/claude/work/repo/Shoreline_remediation/"
OUT = "/home/claude/work/deck/charts/"
fam = "Inter" if any("Inter" == f.name for f in fm.fontManager.ttflist) else "DejaVu Sans"
plt.rcParams.update({"font.family": fam, "font.size": 22, "text.color": INK, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK, "axes.edgecolor": GREY, "figure.facecolor": BG, "axes.facecolor": BG,
    "savefig.facecolor": BG, "axes.spines.top": False, "axes.spines.right": False, "axes.titlesize": 26,
    "axes.titleweight": "bold", "axes.titlelocation": "left", "legend.frameon": False, "legend.fontsize": 19,
    "axes.grid": True, "grid.color": "#D8D2C2", "grid.linewidth": 0.8, "axes.axisbelow": True})
def fig(w=16, h=9):
    return plt.subplots(figsize=(w, h), dpi=100)
def save(f, name):
    f.tight_layout(); f.savefig(OUT + name + ".png", dpi=100); plt.close(f); print("wrote", name)
