# Walkthrough deck: figure and slide generators

Scripts that produced the 69-slide plain-language walkthrough deck
(https://claude.ai/artifact/C2YHim6F847wJDt2BRTfXd). Paths inside point to a scratch folder
(`/home/claude/out/...`); edit them before rerunning.

- `charts.py`: study-area map, oiling map and step charts, from `results/` and `data/demo/p5_sites.csv`.
- `naip_pair2.py`: 2010 and 2015 NAIP photos (true colour and near-infrared) of the worked-example cell, read
  live from Microsoft Planetary Computer.
- `shots.py`: dashboard screenshots with Playwright (dashboard running on port 8599).
- `gen.py`: writes the slide HTML files and `deck.json` for the Slides artifact (image asset ids are specific
  to that artifact).
