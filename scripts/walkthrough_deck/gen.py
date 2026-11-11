"""Generate the walkthrough deck's slide files (project/slides/*.html) and project/deck.json."""
import json
from html import escape
from pathlib import Path

ROOT = Path("/home/claude/out/walk")
SL = ROOT / "project" / "slides"
SL.mkdir(parents=True, exist_ok=True)

DARK, LIGHT, ALT, CARD, BORDER = "#14262E", "#F5F3EC", "#E8EDE9", "#FDFCF8", "#D9DED9"
BODY, MUTED, ACC, ACC_D, TINT, ACC_ON_DARK, SOFT_ON_DARK = "#3D4B51", "#5E6B70", "#9A531A", "#9A531A", "#F1E3D3", "#E3A869", "#BFD0CC"
SERIF = "'Source Serif 4', Georgia, serif"
SANS = "'IBM Plex Sans', Arial, sans-serif"

IMG = {
    "naip_pair": "578e7eb0b8ec3cca2c7ea5e150e5eb87", "naip_nir": "687c9965670992a7dbfd8503ca273bb9",
    "study_area": "37df64d96f474486e9f0ee39c05f76d9", "oiling_map": "e74e646edc6cc294f2ca60c8ba9ea838",
    "by_class": "eec3644f3035e979524a457459668146", "p1_checks": "a78f15d87ad2d77066ee1a2d126e4ac2",
    "p2_errors": "07942e19d4bb341470365a2c6d8f7d01", "p3_methods": "c8dd0ee5dce03236e5b5677a91285a93",
    "qa_plume": "6d46eb5c3921233f59afe42040dc02ab", "qa_landsat": "0ddf3fea7d880e84a6817ace1fca71fb",
    "dash_open": "ed45dd67b3a0cfd2f3d5919959ae746b", "dash_map": "3583ae7277f31988e8dc6b82a994c7e6",
    "dash_expected": "756d1a682c7edce6141fb064a4e076c5", "dash_options": "6f5f73154fb92972cb99e998278e79c2",
    "dash_expanders": "4d412ef43149d2f8669df0c29cfae662", "dash_oil": "c9e5b71dd0b7a3c4ea7f1576ef124b2f",
    "dash_pick": "7cb1418072fe40bcc06d656624182192", "dash_out": "b9556eeb90222c76d2bd648b34e2f21f",
    "dash_new": "82474ca7741e6a78e4d36eba59a172e1", "dash_scen_before": "a6b7b4b7038624ab64f21bbd116678b4",
    "dash_scen_after": "acd56a4fe94424f9aa5d23ca4338881a", "dash_scen_plots": "5241f8383a380396fa84a435a2948d52",
    "dash_method": "ec64679b4fcf1e7826e298c2d80f0ebf",
}

slides = []  # (id, html)
import math
from PIL import Image as _I
FIG = {k: v for k, v in [("naip_pair", "naip_pair"), ("naip_nir", "naip_nir_pair"), ("study_area", "study_area"), ("oiling_map", "oiling_map"),
       ("by_class", "by_class"), ("p1_checks", "p1_checks"), ("p2_errors", "p2_errors"), ("p3_methods", "p3_methods"), ("qa_plume", "qa_plume"),
       ("qa_landsat", "qa_landsat")]}
def aspect(key):
    f = FIG.get(key, key)
    w, h = _I.open(f"/home/claude/out/figs/{f}.png").size
    return w / h
def title_h(t):
    lines = math.ceil(len(t) * 0.55 * 60 / 1664)
    return lines * 60 * 1.15
def text_h(ps, size, width):
    h = 0
    for p in ps:
        items = p if isinstance(p, list) else [p]
        for it in items:
            plain = it.replace("<b>", "").replace("</b>", "")
            h += max(1, math.ceil(len(plain) * 0.56 * size / max(width - 40 if isinstance(p, list) else width, 200))) * size * 1.45 + (6 if isinstance(p, list) else 0)
        h += 20
    return h


def e(t):
    """Escape text but keep <b> and <i> tags written in the content."""
    s = escape(t, quote=False)
    for tag in ("b", "i"):
        s = s.replace(f"&lt;{tag}&gt;", f"<{tag}>").replace(f"&lt;/{tag}&gt;", f"</{tag}>")
    return s


def sec(sid, inner, bg=LIGHT, footer=None, notes=None, dark=False, layout="display:flex;flex-direction:column;gap:40px"):
    color = LIGHT if dark else BODY
    pad = "128px 128px 160px" if footer else "128px"
    h = f'<section id="{sid}" data-transition="fade" style="background:{bg};color:{color};font-family:{SANS};padding:{pad};{layout}">\n'
    h += inner
    if footer:
        fc = SOFT_ON_DARK if dark else MUTED
        h += f'<p style="position:absolute;left:128px;bottom:64px;width:1664px;font-size:24px;color:{fc}">{e(footer)}</p>\n'
    if notes:
        h += f"<aside>{e(notes)}</aside>\n"
    h += "</section>\n"
    slides.append((sid, h))


def title(t, dark=False, eyebrow=None):
    s = ""
    if eyebrow:
        s += f'<p style="font-size:26px;font-weight:600;color:{ACC_ON_DARK if dark else ACC};letter-spacing:2px;text-transform:uppercase">{e(eyebrow)}</p>\n'
    s += f'<h2 style="font-family:{SERIF};font-size:60px;font-weight:600;line-height:1.15;color:{LIGHT if dark else DARK}">{e(t)}</h2>\n'
    return s


def paras(ps, size=30, color=BODY, gap=20):
    out = f'<div style="display:flex;flex-direction:column;gap:{gap}px">\n'
    for p in ps:
        if isinstance(p, list):
            out += f'<ul style="font-size:{size}px;line-height:1.4;color:{color}">' + "".join(f"<li>{e(i)}</li>" for i in p) + "</ul>\n"
        else:
            out += f'<p style="font-size:{size}px;line-height:1.45;color:{color}">{e(p)}</p>\n'
    return out + "</div>\n"


def img(key, alt, w, h, bg=CARD):
    return (f'<img src="/_blob/{IMG[key]}" alt="{escape(alt)}" style="width:{w}px;height:{h}px;object-fit:contain;'
            f'background:{bg};border:1px solid {BORDER};border-radius:12px">\n')


def cards(items, cols=2, size=28, hsize=34, bg=CARD, dark=False):
    out = f'<div style="display:grid;grid-template-columns:{" ".join(["1fr"] * cols)};gap:28px">\n'
    for h3, p in items:
        if dark:
            out += (f'<div style="display:flex;flex-direction:column;gap:10px;border-left:4px solid {ACC_ON_DARK};padding:8px 0 8px 28px">'
                    f'<h3 style="font-size:{hsize}px;font-weight:600;color:{LIGHT}">{e(h3)}</h3>'
                    f'<p style="font-size:{size}px;line-height:1.4;color:{SOFT_ON_DARK}">{e(p)}</p></div>\n')
        else:
            out += (f'<div style="display:flex;flex-direction:column;gap:10px;background:{bg};padding:32px 36px;border:1px solid {BORDER};border-radius:16px">'
                    f'<h3 style="font-size:{hsize}px;font-weight:600;color:{DARK}">{e(h3)}</h3>'
                    f'<p style="font-size:{size}px;line-height:1.4">{e(p)}</p></div>\n')
    return out + "</div>\n"


def table(header, rows, widths, size=26, highlight=None, align=None):
    align = align or ["left"] * len(header)
    out = f'<table style="font-size:{size}px;color:{BODY}">\n<tr>' + "".join(
        f'<th style="width:{w}%;text-align:{a}">{e(h)}</th>' for h, w, a in zip(header, widths, align)) + "</tr>\n"
    for i, r in enumerate(rows):
        bg = f' style="background:{TINT}"' if highlight is not None and i == highlight else ""
        out += f"<tr{bg}>" + "".join(f'<td style="text-align:{a}">{e(c)}</td>' for c, a in zip(r, align)) + "</tr>\n"
    return out + "</table>\n"


def img_side(sid, t, key, alt, w, h, text, footer=None, notes=None, bg=LIGHT, image_first=True, size=28, eyebrow=None):
    avail = (792 if footer else 824) - title_h(t) - 40 - 6
    a = aspect(key)
    h = min(h, avail); w = h * a
    if w > 1664 - 48 - 420:
        w = 1664 - 48 - 420; h = w / a
    while text_h(text, size, 1664 - 48 - w) > avail and w > 480:
        w -= 30; h = w / a
    w, h = int(w), int(h)
    col = f'<div style="flex:1;display:flex;flex-direction:column;gap:20px">\n' + paras(text, size=size) + "</div>\n"
    im = img(key, alt, w, h)
    row = f'<div style="display:flex;gap:48px;align-items:start">\n' + (im + col if image_first else col + im) + "</div>\n"
    sec(sid, title(t, eyebrow=eyebrow) + row, bg=bg, footer=footer, notes=notes)


def img_wide(sid, t, key, alt, w, h, text, footer=None, notes=None, bg=LIGHT, size=28):
    avail = (792 if footer else 824) - title_h(t) - 32 - 32 - text_h(text, size, 1664) - 6
    a = aspect(key)
    h = min(h, avail); w = min(1664, h * a); h = w / a
    sec(sid, title(t) + img(key, alt, int(w), int(h)) + paras(text, size=size), bg=bg, footer=footer, notes=notes,
        layout="display:flex;flex-direction:column;gap:32px")


def divider(sid, n, name, lines, notes=None):
    inner = (f'<p style="font-size:30px;font-weight:600;color:{ACC_ON_DARK};letter-spacing:2px;text-transform:uppercase">Part {n} of 6</p>\n'
             f'<h1 style="font-family:{SERIF};font-size:104px;font-weight:600;line-height:1.08;color:{LIGHT};width:1500px">{e(name)}</h1>\n'
             + paras(lines, size=34, color=SOFT_ON_DARK))
    sec(sid, inner, bg=DARK, dark=True, notes=notes, layout="display:flex;flex-direction:column;justify-content:center;gap:40px")


def text_slide(sid, t, text, footer=None, notes=None, bg=LIGHT, size=32, eyebrow=None):
    sec(sid, title(t, eyebrow=eyebrow) + paras(text, size=size), bg=bg, footer=footer, notes=notes)


def big_number(sid, t, number, label, text, footer=None, notes=None, bg=LIGHT):
    left = (f'<div style="width:600px;display:flex;flex-direction:column;gap:12px">'
            f'<p style="font-size:30px;color:{MUTED}">{e(label)}</p>'
            f'<p style="font-family:{SERIF};font-size:104px;font-weight:600;line-height:1.05;color:{ACC}">{e(number)}</p></div>\n')
    row = f'<div style="display:flex;gap:72px;align-items:start">\n{left}<div style="flex:1">{paras(text, size=30)}</div></div>\n'
    sec(sid, title(t) + row, bg=bg, footer=footer, notes=notes)


# =============================================================================== slides
sec("cover",
    f'<p style="font-size:30px;font-weight:600;color:{ACC_ON_DARK};letter-spacing:2px;text-transform:uppercase">The full walkthrough · November 2026</p>\n'
    f'<h1 style="font-family:{SERIF};font-size:104px;font-weight:600;line-height:1.08;color:{LIGHT};width:1560px">How the Shoreline Remediation Model works, step by step</h1>\n'
    + paras(["What we set out to do, every dataset we used, every step we took (including the ones that failed), and how to use the dashboard. Written for readers who are new to the subject.",
             "Jaison · Shoreline Remediation Model"], size=36, color=SOFT_ON_DARK),
    bg=DARK, dark=True, layout="display:flex;flex-direction:column;justify-content:end;gap:40px",
    notes="This pack explains the proof of concept from the ground up. A shorter 12-slide summary exists for project leads; this one is for anyone who wants to understand every step.")

sec("contents", title("How this pack is organised") + cards([
    ("1. The problem", "What happens when oil reaches a salt marsh, and why choosing a cleanup method is hard."),
    ("2. Ideas in plain words", "Six ideas used throughout: model, baseline, interval, held-out test, planning first, and cause versus association."),
    ("3. The data", "Every dataset we collected: who made it, what it measures, and what we used it for."),
    ("4. The steps", "What we did, in order, including three attempts that did not work and what each one taught us."),
    ("5. The dashboard", "A screen-by-screen tour of the tool, with screenshots."),
    ("6. What it means", "What the tool can and cannot claim, what failed, what is missing, and what comes next; a glossary at the end."),
], cols=3, size=26, hsize=32), notes="Each part starts with a dark divider slide. Every number in the pack comes from a results file in the project repository.")

# ---------------------------------------------------------------- Part 1
divider("part1", 1, "The problem", ["Oil on a salt marsh, and the hard choice of how, or whether, to clean it."])

sec("marsh", title("What a salt marsh is, and why its edge matters") + cards([
    ("A grassland that floods", "Salt marshes are coastal wetlands covered by tough grasses (in Louisiana mostly smooth cordgrass, Spartina alterniflora) that are flooded by the tide."),
    ("Roots hold the soil", "The grass roots bind the soft marsh soil together. Where plants die, the soil loses that grip."),
    ("The edge faces the waves", "Along open water, waves keep eating into the marsh edge. Even healthy marsh in Louisiana loses some edge every year."),
    ("Why it matters", "Marsh shelters fish and birds, buffers storms and stores carbon. Marsh that erodes into open water does not come back by itself."),
], cols=2), notes="The key physical idea for the whole pack: the marsh edge is held together by living roots. Anything that kills the plants at the edge can speed up erosion.")

sec("oil-hits", title("What happens when oil reaches the marsh") + paras([
    "Oil washes onto the first few metres of marsh at the shoreline and coats the grass stems and the soil surface.",
    "Field studies after Deepwater Horizon found heavy oiling harmed marsh vegetation and small animals such as periwinkle snails, and sped up erosion of the oiled edge (Zengel et al. 2015, 2022).",
    "So there are three kinds of damage to recover from, and this pack keeps them separate:",
    ["Chemical: oil left in the soil", "Physical: marsh edge lost to erosion", "Biological: plants and animals coming back"],
    "The tool in this pack predicts the physical one (edge loss) and shows evidence on the biological one (vegetation). It does not yet predict the chemical one.",
], size=30), footer="Zengel et al. 2015, PLoS ONE 10(7): e0132324; Zengel et al. 2022, Scientific Reports 12: 13802.")

sec("dilemma", title("The responder’s dilemma: cleaning can help or harm") + cards([
    ("Leave it (natural recovery)", "No disturbance, but thick oil can stay for years and keep plants from growing back."),
    ("Manual cleanup", "Crews with hand tools rake oil and cut oiled vegetation. Gentle, but slow and needs many people on soft ground."),
    ("Mechanical cleanup", "Machines on barges or airboats scrape oiled material. Fast, but can churn the soil and damage roots."),
    ("Planting", "Replanting marsh grass after cleanup, to rebuild the roots that hold the edge."),
], cols=2, size=27), footer="Descriptions follow the treatment groups in Zengel et al. (2015, 2022).",
    notes="The question responders face: which of these is best for this particular stretch of shoreline? Today that is decided by expert judgement and rule-based tools.")

sec("fast", title("What exists today, and what this project adds") + cards([
    ("Today: rule-based screening", "Tools such as FAST (fastshores.com) and NOAA guidance say which methods are feasible for a shoreline type and oil, using expert rules. They do not predict what will happen afterwards."),
    ("This project adds: predictions from data", "Using records from a real spill, it estimates how much marsh edge a site is likely to lose, shows field evidence for each cleanup method, and says honestly how uncertain that is."),
], cols=2, size=28) + paras(["The aim is not to replace expert rules but to put measured outcomes beside them."], size=30),
    notes="FAST answers: can we do this here? This project starts to answer: what is likely to happen if we do?")

sec("dwh", title("Why Deepwater Horizon (2010) is the test case") + paras([
    "In April 2010 the Deepwater Horizon well blew out in the Gulf of Mexico. Oil reached the Louisiana coast from late spring 2010.",
    "Shoreline survey teams recorded about 796 km of oiled marsh shoreline, 135 km of it heavily oiled (as reported by Zengel et al. 2015).",
    "It is the best-documented marsh oil spill: the oiling of every surveyed stretch, years of aerial photos and satellite images, and controlled field plots comparing cleanup methods are all public.",
    "That makes it the one place where a data-based tool can be built and tested with open data alone.",
], size=30), footer="Figures for oiled shoreline: Zengel et al. 2015, citing the response’s shoreline surveys.")

sec("goal", title("The goal of this proof of concept", dark=True, eyebrow="One sentence") +
    f'<h2 style="font-family:{SERIF};font-size:56px;font-weight:500;line-height:1.25;color:{LIGHT};width:1620px">For oiled salt marsh in the northern Gulf of Mexico, screen cleanup options, predict marsh-edge loss with honest intervals, and show that the prediction holds up on marsh it was not built from.</h2>\n'
    + paras(["Deliberately narrow: one spill, one oil, one habitat. Doing one thing properly comes before doing everything."], size=32, color=SOFT_ON_DARK),
    bg=DARK, dark=True, layout="display:flex;flex-direction:column;justify-content:center;gap:48px")

# ---------------------------------------------------------------- Part 2
divider("part2", 2, "Ideas in plain words", ["Six ideas that come up on almost every slide. Each is explained once here."])

text_slide("idea-model", "Idea 1: a “model” is a recipe for a prediction", [
    "A model takes measurements about a place and turns them into a prediction. Ours is a simple weighted sum:",
    "expected edge loss = a starting value + (weight × open water nearby) + (weight × wave reach) + (weight × how fast this edge eroded before the spill)",
    "The weights are learned from thousands of real places where we know what happened. Then the same recipe is applied to a new place.",
    "We tried a more complex machine-learning method (boosted trees) too. It did worse, so the simple recipe was kept.",
], notes="Linear regression is a weighted sum. Using the simplest model that works makes it easier to check and explain.")

text_slide("idea-baseline", "Idea 2: always compare with a simple guess (the “baseline”)", [
    "The laziest possible prediction is to guess the average for every place. Any model worth using must do better than that.",
    "Example from this project: guessing the average edge loss everywhere is off by 1.47 m/yr on average. Our model is off by 1.33 m/yr on marsh it had never seen.",
    "That is better, but not by a lot. Reporting the baseline keeps us honest about how much the model really adds.",
], footer="Pooled leave-one-basin-out errors: results/p2_basin_holdout/pooled.csv.")

text_slide("idea-interval", "Idea 3: every prediction comes with a range (an “interval”)", [
    "Nature is noisy. Two stretches of marsh that look alike can lose very different amounts of edge.",
    "So the tool never gives a single number alone. It says, for example: expected 1.42 m/yr, and 90% likely to fall between −1.7 and 4.3 m/yr.",
    "“90%” means: of all the places where we tested this, about 9 out of 10 actually fell inside their range. We checked this: in the held-out test, 89% did.",
    "A wide range is not a failure; it is the tool being honest about what a single 100 m stretch can tell us.",
], footer="Interval coverage 89% on held-out cells: results/p2_basin_holdout/pooled.csv.")

text_slide("idea-holdout", "Idea 4: test on places the model has never seen", [
    "A model can look good simply by memorising the places it learned from. The real test is new places.",
    "So we split the Louisiana coast into large areas (basins), drawn on the map before we looked at their results. The model learns from all but one basin and is scored on the one it never saw.",
    "This is like an exam with questions the student has not seen before, rather than the practice questions.",
    "We never mix single rows from the same area into both learning and testing, because neighbouring stretches of marsh behave alike and would make the model look better than it is.",
])

text_slide("idea-planfirst", "Idea 5: write the plan first, then run it once", [
    "With enough tries, any analysis can be bent to show what you hoped. To avoid fooling ourselves, every analysis followed the same routine:",
    ["Write down the question, the data, the method and how to judge the result", "Save that plan in the project’s version history, with a date", "Run the analysis once", "Report the result, including when it shows nothing"],
    "Changes after a quality check were allowed only if they did not depend on which places were oiled, and each one is recorded.",
])

text_slide("idea-cause", "Idea 6: “associated with” is not the same as “caused by”", [
    "Oil did not land at random. It washed onto shores that face open water, and those shores erode faster anyway, oil or not.",
    "So a simple comparison of oiled and clean shore would blame the oil for some erosion that the waves would have caused regardless.",
    "We reduce this by comparing places with similar wave exposure and by checking how fast each edge was eroding before the spill. But we still say “associated with”: heavy oiling and the cleanup that followed it are mixed together in the data.",
    "Only one comparison here is a true experiment: planting, where plots were assigned at random.",
])

# ---------------------------------------------------------------- Part 3
divider("part3", 3, "The data", ["Every dataset, who made it, what it measures, and what we used it for. All of it is publicly available."])

sec("data-overview", title("Eight datasets, at a glance") + table(
    ["Dataset", "What it records", "Used for"],
    [["SCAT shoreline surveys", "How oiled each stretch of shore was, 2010 on", "Which places were oiled, how heavily"],
     ["NAIP aerial photos", "1 m photos of the coast, 2010–2017", "Measuring marsh edge lost"],
     ["Landsat satellite images", "30 m images back to the 1980s", "Erosion before the spill"],
     ["CRMS marsh stations", "Vegetation at 341 sites, 2006–2025", "First test (did not work)"],
     ["Zengel field plots", "Erosion, plants, oil by cleanup method", "Evidence for each method"],
     ["NOAA ADIOS oil library", "Measured properties of 1,460 oils", "Choosing the oil type"],
     ["Published spill cases", "Recovery at 63 past marsh spills", "Recovery model (did not work)"],
     ["Synthetic scenarios", "Computer-generated examples", "Testing code only; not evidence"]],
    [28, 38, 34], size=25), footer="Who made each, licences, dates and checksums: docs/DATA_CATALOGUE.md.")

img_side("data-scat", "SCAT: who checked each stretch of shore for oil", "oiling_map",
         "Map of Barataria Bay marsh-edge cells coloured by maximum oiling: most no oil observed, with heavy oiling concentrated in the northern bay",
         880, 628, [
             "SCAT (Shoreline Cleanup Assessment Technique) teams walked or boated along the shore during the response and classed each stretch as Heavy, Moderate, Light, Very light, or No oil observed.",
             "We used two Louisiana layers: the worst oiling ever recorded for each of 5,721 shoreline zones, and all 15,984 survey records, including 7,077 “no oil observed”.",
             "The “no oil observed” records matter: they give a real clean comparison, shoreline that was checked and found clean.",
         ], footer="NCEI Accession 0163818 (public). Map: Barataria Bay salt-marsh edge cells.", size=26)

img_side("data-naip", "Aerial photos: seeing the marsh edge from above", "naip_pair",
         "Two aerial photos of the same 600 m by 600 m area at Bay Jimmy in July 2010 and May 2015, with a 100 m grid and the example cell outlined",
         1150, 618, [
             "NAIP photos cover the whole coast at about 1 m detail, flown in 2010, 2013, 2015 and 2017.",
             "Left: July 2010, with oil booms (yellow lines) on the water. Right: May 2015. Bright and dark water is sun glare.",
             "The orange square is one 100 m cell, our unit of study. White dots are the Zengel field plots.",
         ], footer="USDA NAIP via Microsoft Planetary Computer. Same area, same scale in both photos.", size=26)

img_side("data-nir", "Near-infrared: why plants are easy to tell from water", "naip_nir",
         "The same two photos shown in near-infrared false colour: marsh plants appear red, water appears blue or white; the red strip inside the orange square is narrower in 2015",
         1150, 618, [
             "The photos also record near-infrared light, which healthy plants reflect strongly and water absorbs.",
             "Shown this way, marsh is red and water is blue. That contrast is what lets a computer separate land from water.",
             "Look inside the orange square: the red strip of marsh is narrower in 2015 than in 2010. That loss is what we measure.",
         ], footer="Same images as the previous slide, near-infrared shown as red.", size=26)

img_wide("data-landsat", "Landsat satellites: a long memory, but blurrier eyes", "qa_landsat",
         "Three Landsat land maps of the Barataria study area for 1998–2000, 2007–2009 and 2014–2016",
         1500, 500, [
             "Landsat has photographed the Earth since the 1980s, at 30 m detail: each pixel is about the size of a tennis court. Too coarse to see the narrow oiled band, but it goes back long before the spill.",
             "We built three land maps from about 50 to 70 summer images each: 1998–2000, 2007–2009 and 2014–2016. Comparing the first two shows how fast each edge eroded before any oil arrived.",
         ], footer="USGS Landsat Collection 2 via Microsoft Planetary Computer. White = land, black = water.", size=27)

text_slide("data-crms", "CRMS: Louisiana’s marsh monitoring stations", [
    "The Coastwide Reference Monitoring System (CRMS) is a network of fixed marsh sites where Louisiana’s coastal agency records vegetation every year.",
    "We used 341 sites with records from 2006 to 2025 (a compiled copy, not yet checked against the original database).",
    "It looked ideal for a before-and-after comparison. The catch, found when we measured distances: the stations sit a median of about 200 m inland from the shoreline, while the oil sat in the first 10–20 m. Only 4 of 20 oiled stations were within 50 m of the edge.",
    "So these stations mostly could not see the oil. Part 4 shows what happened when we tried.",
], footer="CRMS data compiled from CPRA; distances from scripts/match_crms_scat.py.")

sec("data-zengel", title("Zengel field plots: the cleanup-method evidence") + cards([
    ("Where and what", "Bay Jimmy, northern Barataria Bay: heavily oiled marsh plots left untreated, cleaned by hand, cleaned by machine, or machine-cleaned then planted, plus unoiled reference plots."),
    ("2015 study (published tables)", "Two years of plant cover, oil cover, oil in the soil (total PAH) and snails, for each group. We used the authors’ own spreadsheet."),
    ("2022 study (plot-level data)", "Erosion of each of 33 plots measured from aerial photos 1956–2018, plus soil strength. Public on GRIIDC (CC0 licence)."),
    ("Limits", "One site; 5 to 9 plots per group; only planting was assigned at random. Mechanically treated plots were the most heavily oiled."),
], cols=2, size=26), footer="Zengel et al. 2015, doi:10.1371/journal.pone.0132324; Zengel et al. 2022, doi:10.1038/s41598-022-18102-1; data doi:10.7266/VF524143.")

img_side("data-oils", "The oil library: choosing the oil by name", "dash_oil",
         "Dashboard sidebar: search box for NOAA oils, a tick box to include other products, the chosen oil and its measured properties",
         470, 521, [
             "NOAA’s ADIOS library holds measured properties for 1,460 oils: density (API gravity), how runny it is (viscosity) and the temperature at which it stops flowing (pour point).",
             "In the dashboard you search an oil by name. The tool then sets its category (light, medium, heavy, solid) from the measurements, not from a guess.",
             "A check found the library also holds things that are not spill oils, such as a fuel additive. These are now hidden unless you tick the box.",
         ], footer="github.com/NOAA-ORR-ERD/noaa-oil-data. Deepwater Horizon oil was a light crude (South Louisiana-type).", size=27)

sec("data-other", title("Two more datasets, and why they are not evidence") + cards([
    ("63 published marsh spill cases", "Recovery times read from a NOAA report on oil in marshes. We fitted a recovery model to them; it did no better than guessing the average, so it is not used to rank anything."),
    ("Synthetic scenarios", "Computer-generated examples labelled by rules. Useful for testing code, but a model trained on them can only copy the rules that made them. The dashboard now labels these clearly."),
], cols=2, size=28), notes="Keeping these in the project is fine, as long as nobody mistakes them for real outcomes. The dashboard and the catalogue both mark them.")

sec("data-tracking", title("How the data are kept traceable") + cards([
    ("Data catalogue", "19 datasets and 51 files, each with source, licence, date obtained, how it was read, and a fingerprint (checksum) that changes if the file changes."),
    ("Variable dictionary", "45 variables, each with its meaning, unit, valid range and how it was calculated. Automated tests fail if a value falls outside its range."),
    ("Missing-variable list", "15 soil, sediment and water-chemistry variables the project brief asks for but the proof of concept lacks, with where they might come from."),
    ("Decision log", "13 numbered decisions (D1 to D13), each with its date, reason and status, so nobody has to remember why something was done."),
], cols=2, size=27), footer="docs/DATA_CATALOGUE.md, docs/VARIABLE_DICTIONARY.md, data/meta/planned_variables.csv, docs/ROADMAP.md.")

# ---------------------------------------------------------------- Part 4
divider("part4", 4, "The steps", ["What we did, in order. Three early attempts failed; each failure pointed to the next step."])

sec("journey", title("The route, from first attempt to dashboard") + table(
    ["Step", "What we did", "Outcome"],
    [["1", "Marsh stations before and after the spill (CRMS)", "No effect seen: stations too far from the oil"],
     ["2", "Satellite greenness of oiled vs clean shore (Landsat)", "No clear drop: pixels too coarse"],
     ["3", "Recovery model from 63 published spills", "No better than guessing the average"],
     ["4", "Marsh-edge loss from 1 m aerial photos", "Heavy oiling linked to faster edge loss"],
     ["5 (P1)", "Was oiled shore eroding faster before the spill?", "Partly; estimate revised to 0.85 m/yr"],
     ["6 (P2)", "Does the prediction work on unseen marsh?", "Yes, modestly, with honest ranges"],
     ["7 (P3)", "What did each cleanup method do to erosion?", "Manual neutral, mechanical unclear, planting helped"],
     ["8 (P4–P6)", "Document data, build dashboard, write report", "Done; awaiting scientific review"]],
    [12, 48, 40], size=25, highlight=3), notes="Steps 1 to 3 are the failures; step 4 is where the approach changed. P1 to P6 are the six proof-of-concept milestones.")

text_slide("try1", "Step 1: marsh stations before and after the spill", [
    "Idea: compare vegetation at CRMS stations near oiled shore with stations near clean shore, before and after 2010.",
    "We matched 20 stations to oiled shore and 24 to clean shore, using the SCAT surveys.",
    "Result: no detectable effect of oil on vegetation. The largest difference, +7.9 points of plant cover, had a range from −2.5 to +18.4 that includes zero.",
    "Why: the stations mostly sit about 200 m inland, beyond the oiled band. The monitoring network could not see the spill; that does not mean the spill had no effect.",
    "Lesson: we needed measurements right at the edge.",
], footer="validation/oil_event_study.py; docs/FINDINGS_2026-11-11.md section 2.", size=30)

text_slide("try2", "Step 2: satellite greenness of oiled shore", [
    "Idea: track how green the marsh edge looked in Landsat images, 2006–2016, along 34 heavily oiled stretches and 4 clean ones.",
    "We used 1,044 satellite images, with clouds removed.",
    "Result: no clear drop after the spill (+0.025 on the greenness scale, range −0.057 to +0.113). A “placebo” check, pretending the spill happened in 2008, found shifts just as large, so the method could not separate the spill from normal ups and downs.",
    "Why: a 30 m pixel mixes oiled marsh, clean marsh and water; and only 4 clean stretches qualified.",
    "Lesson: we needed finer detail than satellites give.",
], footer="scripts/landsat_ndvi.py; docs/FINDINGS_2026-11-11.md section 3.", size=29)

text_slide("try3", "Step 3: a recovery model from past spills", [
    "Idea: learn recovery times from 63 published marsh oil spills, then predict recovery for a new spill.",
    "Result: tested on cases it had not seen, the model was no better than guessing the average recovery time, with or without season, latitude and wetland type.",
    "Why: too few cases, measured in too many different ways, from too many different places.",
    "Lesson: a few dozen mixed cases cannot carry a model. We needed thousands of comparable measurements, which is what the aerial photos give.",
], footer="src/shoreline_remediation/marsh_recovery_model.py; docs/PROCESS_MODEL_AUDIT.md.", size=30)

sec("edge-cells", title("Step 4: cut the shoreline into 100 m cells") + cards([
    ("1. Lay a grid", "A grid of 100 m by 100 m squares is laid over the coast (the orange square on the photos is one of them)."),
    ("2. Keep shoreline cells", "Only squares crossed by shoreline that the SCAT teams surveyed are kept: 39,320 salt-marsh edge cells along the Louisiana coast."),
    ("3. Label each cell", "Each cell takes the worst oiling ever recorded in it, from Heavy to No oil observed."),
    ("4. Measure each year", "For each aerial-photo year, count how much of the cell is marsh and how much is water."),
], cols=2, size=27), footer="scripts/build_edge_cells.py. The first analysis used 4,779 cells in Barataria Bay.",
    notes="Working in cells turns a map into a table: one row per cell, with its oiling, its surroundings and how much marsh it lost.")

img_side("land-water", "How the computer tells marsh from water", "qa_plume",
         "Quality-check images from the Mississippi delta: top row near-infrared photos, bottom row the computed land mask, where muddy river water in the left tile is wrongly marked as land",
         780, 520, [
             "For each photo tile, the computer learns what marsh and water look like there, using the plant signal in near-infrared, then labels every 2 m spot as land or water.",
             "We checked the results by eye. The 2013 photos were too hazy and were dropped.",
             "Where the photo is almost all water, or muddy river water glows like land (left), the method fails. Those areas, including the Mississippi delta, were excluded and are flagged as out of scope.",
         ], footer="scripts/naip_edge_extract.py. Bottom row: white = land, black = water.", size=27)

big_number("rate", "Turning land share into metres of edge lost per year", "1.54 m/yr", "Example cell at Bay Jimmy", [
    "July 2010: 59.4% of the cell was marsh. May 2015: 52.0%.",
    "The cell lost 7.4% of its area, which along a 100 m cell is about 7.4 m of edge.",
    "Spread over the 4.8 years between the two photos, that is 1.54 m of edge lost per year.",
    "Doing this for every cell gives thousands of measured outcomes: the raw material for everything that follows.",
], footer="Cell 8018_32612: data/external/p2/barataria/cell_land_by_year.csv.")

img_side("first-result", "Step 4 result: more oil, more edge lost", "by_class",
         "Bar chart: extra edge loss compared with clean edge in the same 2 km block: very light 0.31, light 0.20, moderate 0.69, heavy 1.00 m/yr, with 90% intervals",
         1050, 525, [
             "Compared with clean edge in the same 2 km neighbourhood, heavily oiled edge lost 1.00 m/yr more (range 0.58 to 1.43), 2010–2015.",
             "The extra loss grows with oiling: clear for Moderate and Heavy, unclear for the lighter classes.",
             "4,779 cells in Barataria Bay.",
         ], footer="results/naip_edge_loss/coefficients.csv (2010–2015). Bars show the estimate; lines show the 90% range.", size=27)

text_slide("doubt", "Why we did not stop at 1.00 m/yr", [
    "The aerial photos start in July 2010, after the oil arrived. So we could not see how fast each edge was eroding before.",
    "And oil landed mostly on shores facing open water, which erode faster anyway (Idea 6).",
    "If heavily oiled shore was already eroding faster, part of the 1.00 m/yr would have nothing to do with oil.",
    "Two checks were planned before looking: measure the erosion before the spill with Landsat, and measure wave exposure more finely.",
], notes="This is the most important scientific step in the project: challenging our own first result before anyone else does.")

img_side("p1", "Step 5 (P1): checking the erosion before the spill", "p1_checks",
         "Range plot of five estimates: aerial 1.00, Landsat after spill 1.15, Landsat before spill 0.30, after minus before 0.85 highlighted, with finer exposure 0.62",
         1080, 540, [
             "Landsat confirmed the gap after the spill (1.15 m/yr) with a second, independent sensor.",
             "But before any oil, heavily oiled shore was already eroding 0.30 m/yr faster.",
             "Subtracting that gives the headline: 0.85 m/yr (range 0.49 to 1.22). With finer exposure measures: 0.62.",
         ], footer="results/p1_prespill/checks.csv and exploratory.csv. 5,950 Barataria cells, 525 heavily oiled.", size=27)

sec("exposure", title("What “exposure to waves” means here") + cards([
    ("Open water within 1 km", "The share of the area within 1 km of the cell that is open water. More water around means bigger waves can build up."),
    ("Open water within 250 m", "The same, closer in: is the cell on a sheltered creek or an open shore?"),
    ("Fetch", "How far wind can blow over open water before reaching the cell, measured in 16 compass directions and averaged (capped at 10 km). The median cell has about 770 m."),
    ("Pre-spill trend", "How fast the cell’s edge was eroding between about 1999 and 2008, from Landsat. The past is a good guide to the future."),
], cols=2, size=26), footer="scripts/exposure_metrics.py (from the 2010 aerial land map); scripts/landsat_edge_fraction.py.",
    notes="Exposure explains most of the erosion differences between places. Once it is measured finely, the gap that existed before the spill disappears.")

img_side("p2-setup", "Step 6 (P2): the test on unseen marsh", "study_area",
         "Map of the Louisiana coast: edge cells used in Terrebonne, Barataria and Breton in shades of blue; excluded river delta in brown; other excluded cells in grey",
         880, 628, [
             "The coast was split into basins by fixed lines drawn before their results were measured.",
             "12,696 cells passed every quality check: Terrebonne 4,104, Barataria 5,386, Breton 3,206.",
             "The Mississippi delta (brown) and water-dominated areas (grey) were excluded because the photos cannot be read reliably there.",
         ], footer="data/demo/p5_sites.csv; scripts/assign_basins.py.", size=26)

img_side("p2-result", "Step 6 result: better than guessing, with honest ranges", "p2_errors",
         "Bar chart of average prediction error: Barataria 1.50 for the baseline vs 1.31 for the model; Breton 1.42 vs 1.37; pooled 1.47 vs 1.33",
         1050, 525, [
             "Each basin was predicted by a model that never saw it.",
             "The model beat the guess-the-average baseline in both test basins.",
             "Its 90% ranges held: 90% of Barataria cells and 88% of Breton cells fell inside them (89% overall).",
         ], footer="results/p2_basin_holdout/per_basin.csv and pooled.csv. Terrebonne had too few heavily oiled cells to be a test basin.", size=27)

sec("p2-oil", title("Step 6, the surprise: knowing the oiling adds little per cell") + cards([
    ("Oil matters on average…", "Across many cells, heavy oiling is clearly linked to extra edge loss (Step 5)."),
    ("…but not for one cell", "Adding the oiling class did not make single-cell predictions more accurate. Each cell’s own noise is bigger than the oil effect."),
    ("The size moved around", "Learned from different basins, the extra loss for heavy oiling came out anywhere from 0.34 to 0.83 m/yr."),
    ("So the tool shows it separately", "The dashboard gives the exposure-based prediction, with the heavy-oil extra shown beside it as a range, not folded in."),
], cols=2, size=27), footer="results/p2_basin_holdout/oil_effect_transfer.csv. Boosted trees were also tried and did worse than the simple model.")

text_slide("p3-search", "Step 7 (P3): looking for records of who cleaned what", [
    "To compare cleanup methods across the whole coast, we needed to know which stretches were cleaned, and how.",
    "We searched the shoreline survey layers, NOAA’s DIVER data archive, a NOAA technical memorandum and the spill’s administrative record.",
    "Result: no public, machine-readable record links cleanup methods to shoreline stretches. The memorandum shows treated areas only as map figures.",
    "So the method comparison had to rest on the Zengel field plots at one site, with that limit stated plainly.",
], footer="docs/P3_TREATMENT_PLAN.md; docs/FINDINGS_2026-11-11.md section 9.")

img_side("p3-result", "Step 7 result: what each cleanup method did to erosion", "p3_methods",
         "Range plot of change in erosion against untreated oiled marsh: manual −0.63, mechanical +0.28, mechanical plus planting −1.47 m/yr in years 0–2, with fainter years 2–8 values near zero",
         1080, 504, [
             "Each plot’s own erosion rate before the spill was subtracted first.",
             "Oiling itself: untreated oiled plots eroded 1.88 m/yr faster than unoiled plots in 2010–2012, fading to 0.21 by 2012–2018.",
             "Manual cleanup did not add erosion; mechanical was no better than leaving it; planting clearly cut erosion.",
         ], footer="results/p3_treatment/A_prespill_adjusted.csv. 33 plots: 5 reference, 9 untreated, 5 manual, 9 mechanical, 5 planted.", size=26)

text_slide("p3-check", "Step 7, a cross-check: do the aerial photos agree with the field?", [
    "17 of Zengel’s field plots fall inside 7 of our 100 m cells. That lets us compare our photo-based measure with the field measurements.",
    "They rank places the same way: the Spearman rank correlation is 0.68 (range 0.30 to 0.91), passing the test set in advance.",
    "But our photo-based rates read about 1.2 m/yr lower than the field values. Comparisons between places are trustworthy; absolute rates are on the low side.",
    "The dashboard says this beside every rate it shows.",
], footer="results/p3_treatment/C_naip_check.csv. The range is optimistic because several plots share a cell.")

sec("p4p5", title("Steps 8 to 10 (P4–P6): document, build, report") + cards([
    ("P4: documentation", "Data catalogue, variable dictionary and decision log, all checked by automated tests (slide on keeping data traceable)."),
    ("P5: the dashboard", "The model refitted on all 12,696 cells and frozen as a versioned file with its weights, ranges and data fingerprints. Its held-out error is 1.30 m/yr against 1.42 for guessing the average."),
    ("P5: checks", "108 automated tests. The dashboard was installed from scratch on a clean computer and runs; that check found a missing package, now fixed."),
    ("P6: report and slides", "A written report and a 12-slide summary for project leads, every number checked against the results files."),
], cols=2, size=26), footer="models/p5_edge_loss_v1.json; docs/P5_WORKED_EXAMPLE.md; docs/P6_POC_REPORT.md.")

# ---------------------------------------------------------------- Part 5
divider("part5", 5, "The dashboard", ["A screen-by-screen tour. Every screenshot is from the working tool."])

img_wide("dash-open", "Opening screen: two tabs", "dash_open",
         "Dashboard opening screen: dark title banner, two tabs, an explanation line and three ways to choose a site",
         1664, 560, [
             "<b>Site evidence (real data)</b>, the first tab, uses only real measurements. <b>Scenario screening</b>, the second, is the older rule-based view and is labelled as not validated. The dark panel on the left drives only the second tab.",
         ], size=28)

img_side("dash-map", "Choosing a site and seeing it on the map", "dash_map",
         "Map of Barataria Bay edge cells coloured by oiling with the selected cell marked, beside a table of the site's inputs",
         1180, 560, [
             "Three ways to choose: the worked example, any Louisiana edge cell, or a new site you type in.",
             "The map colours each cell by its worst oiling: dark red Heavy, through orange and yellow, to blue for no oil observed. The black dot is your site.",
             "The table lists the site’s inputs: oiling, open water nearby, fetch and the pre-spill trend.",
         ], size=26)

img_side("dash-expected", "Reading the expected edge loss", "dash_expected",
         "Expected marsh-edge loss panel: four numbers and a chart placing the site's prediction and range over the spread of all measured rates",
         1080, 582, [
             "Four numbers: the expected rate; its 90% range; the extra linked to heavy oiling (a range, shown separately); and what was actually measured at this cell, if known.",
             "The chart puts the site in context: grey bars are all measured cells, the green line is this site’s expectation, the shaded band its range, the red dashed line the measured value.",
         ], size=26)

img_side("dash-options", "Cleanup options: rules and field evidence side by side", "dash_options",
         "Table of 15 cleanup methods with rule screening result, utility score, and field evidence on erosion and vegetation for manual and mechanical methods",
         1080, 582, [
             "<b>Rule screening</b>: eligible, conditional or ineligible, from FAST-style rules.",
             "<b>Evidence columns</b>: change in erosion and plant cover against natural recovery, from the field plots, with ranges.",
             "Most methods say “no outcome evidence”: an honest gap. Where rules and evidence disagree (mechanical), both are shown.",
         ], size=26)

img_side("dash-expanders", "Every assumption is listed", "dash_expanders",
         "Two opened panels: the rule-screening inputs with the basis for each, several marked ASSUMED, and the limits of the evidence",
         1000, 590, [
             "Open “Rule-screening inputs” to see what the rules were told about the site, and where each value came from. Values marked ASSUMED are judgement calls, not measurements.",
             "Open “Limits of this evidence” for the plain-language list of what the tool cannot claim.",
         ], size=27)

img_side("dash-pick", "Picking any edge cell on the coast", "dash_pick",
         "Pick-a-cell mode: menus for basin, oiling class, in-scope only, SCAT segment and cell, with the map and site table below",
         960, 620, [
             "Choose a basin, an oiling class, a SCAT survey segment and a cell.",
             "“In-scope cells only” hides cells the model was not built for. Untick it to see them and the reason they are excluded.",
         ], size=27)

img_side("dash-out", "When a site is out of scope, the tool says so", "dash_out",
         "Birdfoot delta cell selected: missing inputs in the site table, a red out-of-scope message about the active river delta, and no prediction shown",
         800, 635, [
             "Here a cell in the Mississippi delta is chosen. A red message explains why it is out of scope: the photos cannot separate land from muddy river water there.",
             "No prediction is shown at all. A tool that refuses to guess outside what it knows is safer than one that always answers.",
         ], size=28)

img_side("dash-new", "A new site, and the extrapolation warning", "dash_new",
         "New-site mode with typed values; a yellow warning that the pre-spill trend of 9 m/yr is outside the training range; the prediction is still shown",
         760, 644, [
             "You can type in values for a site not on the map.",
             "Here the pre-spill erosion is set to 9 m/yr, far outside anything in the training data. A yellow warning says the prediction is an extrapolation.",
             "The number is still shown, so you can see it, but it should not be trusted the way an in-range prediction is.",
         ], size=27)

img_wide("dash-scen", "The second tab: the older rule-based view", "dash_scen_before",
         "Scenario screening tab before running: a blue note saying the view uses rules and synthetic data and is not validated, with scenario inputs in the left panel",
         1560, 556, [
             "This view ranks cleanup methods from the inputs in the left panel. A note at the top says plainly that it uses rules, a model trained on synthetic labels, and a process model with assumed rates.",
         ], size=28)

img_side("dash-scen-after", "Running the scenario view", "dash_scen_after",
         "Scenario results: a recommended treatment with eligibility, utility, confidence and uncertainty cards, and key decision drivers",
         1100, 529, [
             "After pressing “Run scenario analysis”, it shows a leading option, its feasibility, a utility score and an uncertainty signal.",
             "Useful for exploring how the rules respond to different inputs. Not evidence of what will happen in the field.",
         ], size=27)

img_side("dash-scen-plots", "Its recovery curves come from assumed rates", "dash_scen_plots",
         "Recovery trajectory chart for several treatments from the process model",
         860, 597, [
             "These curves come from a simple simulation of oil moving and breaking down in the shore, using rates that are assumed, not measured.",
             "They show the shape the rules imply, not a forecast. Calibrating them needs repeated field surveys of real sites.",
         ], size=27)

img_side("dash-method", "The method-test tab is labelled as not evidence", "dash_method",
         "Method test tab: a yellow warning that every model was trained on synthetic data, above bar charts of model scores",
         1080, 545, [
             "Scores here show how well different machine-learning methods copy the rules behind the synthetic data.",
             "Good scores mean the code works, not that cleanup outcomes are predicted. The warning says so.",
         ], size=27)

# ---------------------------------------------------------------- Part 6
divider("part6", 6, "What it means", ["What the tool can claim, what it cannot, what is missing, and what comes next."])

sec("summary", title("Three results carry the claim") + cards([
    ("Oil and edge loss", "After checking the erosion before the spill, heavily oiled edge lost 0.85 m/yr more than clean edge nearby (range 0.49 to 1.22)."),
    ("Unseen marsh", "On basins it never saw, the model beat guessing the average (1.33 vs 1.47 m/yr error) and its 90% ranges held (89%)."),
    ("Cleanup methods", "Against leaving oiled marsh untreated, in the first two years: manual −0.63 m/yr erosion, mechanical +0.28 (unclear), planting −1.47 (randomized)."),
], cols=3, size=27), footer="results/p1_prespill, results/p2_basin_holdout, results/p3_treatment.")

sec("failed", title("Seven things that did not work, and what each changed") + table(
    ["Attempt", "Result", "What it changed"],
    [["Recovery model from 63 published spills", "No better than the average", "Not used for ranking"],
     ["Ranking learned from synthetic scenarios", "Only copies its rules", "Tab labelled not validated"],
     ["CRMS stations, 2010 before and after", "No effect seen", "Moved to measuring at the edge"],
     ["Landsat greenness of oiled shore", "No clear drop", "Moved to 1 m aerial photos"],
     ["Records of who cleaned what", "None public", "Method evidence from one field site"],
     ["Land/water on water-dominated photos", "Water read as land", "Delta and two areas excluded"],
     ["2013 aerial photos", "Too hazy", "Dropped before analysis"]],
    [40, 26, 34], size=25), bg=ALT, footer="Every analysis was planned before its results were seen; failures are reported, not dropped.")

sec("limits", title("What the tool cannot claim yet") + cards([
    ("One spill", "One oil and one habitat. Shown to work between Louisiana basins, not yet on another spill or coast."),
    ("Not proof of cause", "Heavy oiling and the cleanup that followed are mixed together. Only planting was randomized."),
    ("Thin method evidence", "One field site, 5 to 9 plots per group."),
    ("Single sites are noisy", "One 100 m cell’s range spans about 6 m/yr. Predictions for whole survey segments would be much tighter."),
    ("Photos read low", "Aerial rates are about 1.2 m/yr below field values. Differences between places are firmer than absolute rates."),
    ("No chemistry", "No soil or sediment chemistry in any model, so chemical recovery is not predicted."),
], cols=3, size=25, hsize=31), bg=ALT, footer="Scientific review of each step and a user test of the dashboard are still to do.")

sec("chemistry", title("The biggest gap: soil and sediment chemistry") + cards([
    ("What we hold", "Oil in the soil (total PAH) only as group averages from the 2015 study, and soil strength per plot from the 2022 study, not yet analysed."),
    ("Why it matters", "Total PAH is not what plants and animals actually take up; that depends on the soil’s organic matter. Without chemistry, “recovery” here means physical and plant recovery only."),
    ("First to add", "Soil organic matter and bulk density (CRMS stations measure them), then porewater salinity."),
    ("Needs a partner", "Redox, sulfide and root biomass explain the mechanism but no open data covers these sites: a field or lab partner is needed."),
], cols=2, size=26), footer="Full list of 15 missing variables: data/meta/planned_variables.csv; reasoning in docs/REVIEW_NOTES.md (E0).")

sec("path", title("What comes next, in four phases") + table(
    ["Phase", "What", "Opens when"],
    [["0 · now", "Proof of concept: one spill, salt marsh, open data", "Built; scientific review pending"],
     ["1", "Predictions for whole survey segments; cleanup labels digitised from NOAA maps; soil organic matter and bulk density", "Review signs off (open data only, could start now)"],
     ["2", "Second and third spills, validation leaving out whole spills, expert scoring of 30 scenarios", "A data partner gives access to a second spill"],
     ["3", "Other shorelines and contaminants, chemical recovery, monitoring that updates predictions", "The model beats the baseline on a spill it has not seen"]],
    [12, 54, 34], size=26, highlight=0), footer="Second-spill candidates, availability unverified: Exxon Valdez, Prestige, Hebei Spirit, Wakashio.")

sec("asks", title("What the next phase needs", dark=True) + cards([
    ("Analyst time", "For Phase 1, which uses open data only and could start now."),
    ("A data partner", "With oiling, cleanup and outcome records for a second spill. This gate sets the timeline."),
    ("Three or more response experts", "To score the 30 blind scenarios already prepared, as a check on the rules."),
    ("A field or lab partner", "For sediment and porewater chemistry, which no open source covers at these sites."),
], cols=2, size=28, dark=True), bg=DARK, dark=True)

sec("glossary1", title("Glossary (1 of 2)") + table(
    ["Term", "Meaning"],
    [["Salt marsh", "Coastal grassland flooded by the tide"],
     ["Marsh edge", "The boundary between marsh and open water, where erosion happens"],
     ["SCAT", "Shoreline Cleanup Assessment Technique: field surveys that classed each stretch’s oiling"],
     ["ESI 10A", "The shoreline-sensitivity code for salt marsh (the most sensitive class)"],
     ["NAIP", "US aerial photo programme, about 1 m detail"],
     ["Landsat", "US satellite series, 30 m detail, back to the 1980s"],
     ["Near-infrared", "Light just beyond red; plants reflect it strongly, water absorbs it"],
     ["Edge cell", "A 100 m by 100 m square crossed by surveyed shoreline: our unit of study"],
     ["Edge-loss rate", "Metres of marsh edge lost per year, from the change in land share"]],
    [24, 76], size=25))

sec("glossary2", title("Glossary (2 of 2)") + table(
    ["Term", "Meaning"],
    [["Exposure, fetch", "How open to waves a cell is; fetch is how far wind blows over water to reach it"],
     ["Model", "A recipe that turns measurements into a prediction"],
     ["Baseline", "The simplest guess (the average); a model must beat it"],
     ["90% interval", "The range a prediction falls in about 9 times out of 10"],
     ["Held-out test", "Scoring a model on places it never learned from"],
     ["Association", "Two things go together; not proof that one causes the other"],
     ["Randomized", "Treatments assigned by chance, which allows conclusions about cause"],
     ["Natural recovery", "Leaving oiled marsh untreated"],
     ["PAH", "Polycyclic aromatic hydrocarbons, the toxic part of oil measured in soil"]],
    [24, 76], size=25))

sec("sources", title("Sources") + paras([[
    "NOAA SCAT shoreline oiling, Deepwater Horizon: NCEI Accession 0163818",
    "USDA NAIP aerial photos and USGS Landsat Collection 2, via Microsoft Planetary Computer",
    "Zengel S, Bernik BM, Rutherford N, Nixon Z, Michel J (2015) Heavily oiled salt marsh following the Deepwater Horizon oil spill, ecological comparisons of shoreline cleanup treatments and recovery. PLoS ONE 10(7): e0132324",
    "Zengel S, Nixon Z, Weaver J, Rutherford N, Bernik BM, Michel J (2022) Accelerated marsh erosion following the Deepwater Horizon oil spill confirmed, ameliorated by planting. Scientific Reports 12: 13802; data on GRIIDC, doi:10.7266/VF524143",
    "Louisiana CRMS marsh monitoring (CPRA), compiled copy",
    "NOAA ADIOS oil library (github.com/NOAA-ORR-ERD/noaa-oil-data)",
]], size=26) + paras(["Project records: docs/FINDINGS_2026-11-11.md (every analysis), docs/ROADMAP.md (milestones and decisions), docs/REVIEW_NOTES.md (open concerns), docs/DATA_CATALOGUE.md, docs/VARIABLE_DICTIONARY.md, docs/P6_POC_REPORT.md."], size=24, color=MUTED))

# ---------------------------------------------------------------- write
for sid, h in slides:
    (SL / f"{sid}.html").write_text(h)
order = [s for s, _ in slides]
sections = {
    "s0": {"description": "Cover and contents", "start": "cover"},
    "s1": {"description": "The problem: oil on salt marsh and the cleanup dilemma", "start": "part1"},
    "s2": {"description": "Six ideas used throughout, in plain words", "start": "part2"},
    "s3": {"description": "Every dataset, who made it and what it was used for", "start": "part3"},
    "s4": {"description": "The steps, including the attempts that failed", "start": "part4"},
    "s5": {"description": "A screen-by-screen tour of the dashboard", "start": "part5"},
    "s6": {"description": "What it means, limits, next steps, glossary and sources", "start": "part6"},
}
deck = {"v": 4, "createdOnFiles": {"v": 1, "at": "2026-11-11T09:50:00Z"}, "lists": "css",
        "title": "Shoreline Remediation Model: the full walkthrough", "order": order, "cover": "cover", "sections": sections,
        "faces": {"source-serif-4": {"family": "Source Serif 4", "href": "https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400..700&display=swap"},
                  "ibm-plex-sans": {"family": "IBM Plex Sans", "href": "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap"}},
        "designSystems": []}
(ROOT / "project" / "deck.json").write_text(json.dumps(deck))
print(len(slides), "slides")
