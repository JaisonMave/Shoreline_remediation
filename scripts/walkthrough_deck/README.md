# Walkthrough deck: figure and slide generators

These scripts support the plain-language walkthrough deck and figures. The project handoff and evidence status are maintained in `docs/HANDOFF.md`, `docs/ROADMAP_STATUS.md`, and `docs/FINDINGS_V4.md`; this generator README is not the current project handoff.

- The current handoff describes a 92-slide deck artifact: https://claude.ai/artifact/MeLp9tsyde7PwAHsnVCd8S
- Number sources are indexed in `docs/deck/NUMBER_SOURCES.md` and chart helpers are under `docs/deck/chart_scripts/`.
- `charts.py`: study-area map, oiling map and step charts, from results and demo data.
- `naip_pair2.py`: 2010 and 2015 NAIP photos (true colour and near-infrared) of the worked-example cell, read live from Microsoft Planetary Computer.
- `shots.py`: dashboard screenshots with Playwright (dashboard expected on port 8599).
- `gen.py`: writes slide HTML and `deck.json`; image asset IDs are specific to the generated Slides artifact.

## Reproduction caveat

The scripts were created in a scratch environment and may contain paths such as `/home/claude/out/...`. Inspect and update those paths before running; do not assume the deck can be rebuilt unchanged on another machine. The artifact link is an external presentation, not a substitute for source files, result artifacts, citations, or the current handoff. Five dashboard views were previously described without screenshots; see `CHANGELOG.md` and the handoff before representing deck coverage as complete.
