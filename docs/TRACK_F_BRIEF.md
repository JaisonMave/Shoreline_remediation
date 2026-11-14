# Track F brief for agents (14 November 2026)

Every agent working on Track F reads this first. Plan: `docs/V4_PROGRAMME_PLAN.md` (Track F, F0-F12) and
`docs/ARCHITECTURE_FOUNDATION.md` (D14-D20). Jaison delegated Track F decisions to the orchestrator (14 Nov);
everything is left for his review afterwards.

## Environment
- Repo root: `C:\Users\Jaison.M\OneDrive - Shell\Desktop\New_oppurtunity\Shoreline remediation\model\Model_v3`
- Windows PowerShell 5.1: no `&&`; chain with `;` and `if ($?) { }`.
- Python: `& "C:\Program Files\Python311\python.exe"`; run modules from the repo root (`-m validation.x`).
  If console output is swallowed, write it to a file and read the file.
- Tests: `& "C:\Program Files\Python311\python.exe" -m pytest -q -p no:cacheprovider <files>`.
- Local data (git-ignored, present): DIVER `data/external/diver_dwh/extracted_csv/`, SCAT `data/raw/scat/`.

## Rules (same as v3/V4)
1. **Plan before run.** Write your plan file (`docs/<ID>_PLAN.md`) with question, data, method, baseline, gate
   and pass/fail rule BEFORE computing any outcome. Gated checks run ONCE; keep originals; reruns get a new label.
2. **Baseline always**; hold out whole units (spills, basins, stations, studies), never rows.
3. **Label everything**: SOURCED/ASSUMED parameters; evidence MEASURED / LITERATURE (AI-extracted) /
   AI-PROPOSED / NO EVIDENCE; models experimental or validated. Never invent numbers or sources.
4. **Numbers in reports come from your results files.** Report nulls and failures plainly.
5. Comments only where code cannot show the reason, one short line. Keep changes surgical; keep public
   function signatures (add optional arguments only).
6. Write results to `results/<your_id>/`; tests to `tests/test_<your_id>.py` (focused, few).
7. **Do NOT edit**: `CHANGELOG.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`, `docs/REVIEW_NOTES.md`,
   `docs/FINDINGS_*.md`, `docs/V4_PROGRAMME_PLAN.md`, this brief. Do NOT run `scripts/build_catalogue.py`.
   Do NOT git commit or push. Only touch the files your task names (other agents work in parallel).
8. Ignore `tests/test_data_catalogue.py` failures caused by new or changed data files (rebuilt centrally).
9. Return a concise report: files created/changed (exact paths), key numbers with their result file, gate
   outcomes, deviations, what is left for Jaison, test results.
