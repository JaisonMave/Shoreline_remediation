"""V5.1: machine comparison of the AI-transcribed NOAA habitat-impact ratings with the text layer of the source PDF.

What it does. For every row of data/knowledge/tables/noaa_response_rating.csv it finds the same response-method line in the
ratings table printed on the cited page of NOAA OR&R (2017) "Characteristic Coastal Habitats" (the local copy in
docs/reference/literature/) and compares the five oil-category letters (I to V).

What it is NOT. This is a transcription check by software against the PDF text layer. It is not a human review, it does not
check that the D36 letter-to-verdict mapping (noaa_rating_mapping.csv) is appropriate, and it does not check that the pipeline
option assigned to each NOAA method is the right crosswalk. The table status therefore stays "Proposed" until the owner
signs it off.

Run: python -m validation.noaa_rating_source_check        (needs the `pdftotext` program from poppler)
Writes results/v5_1/noaa_rating_source_check.csv and noaa_rating_source_check_summary.txt.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RATINGS_CSV = ROOT / "data" / "knowledge" / "tables" / "noaa_response_rating.csv"
PDF = ROOT / "docs" / "reference" / "literature" / "NOAA_2017_CharacteristicCoastalHabitats.pdf"
OUT = ROOT / "results" / "v5_1"
CATS = ("cat_I", "cat_II", "cat_III", "cat_IV", "cat_V")
_DASHES = {"–": "-", "—": "-", "−": "-"}
_LETTERS = re.compile(r"((?:\s+[ABCDI\-]){5})\s*$")


def available() -> bool:
    return PDF.exists() and shutil.which("pdftotext") is not None


def page_text(page: int) -> str:
    out = subprocess.run(["pdftotext", "-f", str(page), "-l", str(page), "-layout", str(PDF), "-"],
                         check=True, capture_output=True, text=True).stdout
    for k, v in _DASHES.items():
        out = out.replace(k, v)
    return out


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def parse_page(text: str) -> tuple[str, dict]:
    """(table title, {normalised method name: [five letters]}) for one ratings page."""
    lines = text.splitlines()
    title = next((ln.split(":", 1)[1].strip() for ln in lines if ":" in ln and ln.strip().isupper() is False
                  and ln.split(":", 1)[0].strip().isupper()), "")
    table = {}
    for ln in lines:
        m = _LETTERS.search(ln)
        if not m:
            continue
        letters = m.group(1).split()
        head = ln[:m.start()]
        # The method name is the last run of text on the line (the left column holds the oil-category key).
        method = re.split(r"\s{3,}", head.rstrip())[-1].strip()
        if method:
            table[_norm(method)] = letters
    return title, table


def check() -> pd.DataFrame:
    df = pd.read_csv(RATINGS_CSV, dtype=str, keep_default_na=False)
    pages = {int(p): parse_page(page_text(int(p))) for p in sorted(df.page.unique(), key=int)}
    rows = []
    for r in df.itertuples():
        title, table = pages[int(r.page)]
        csv_letters = [getattr(r, c) for c in CATS]
        pdf_letters = table.get(_norm(r.noaa_method))
        if pdf_letters is None:
            result = "method_not_found_on_page"
        elif pdf_letters == csv_letters:
            result = "match"
        else:
            result = "MISMATCH"
        rows.append({"rating_id": r.rating_id, "esi_code": r.esi_code, "page": r.page, "noaa_table_csv": r.noaa_table,
                     "noaa_table_pdf": title, "table_title_matches": _norm(r.noaa_table) == _norm(title),
                     "noaa_method": r.noaa_method, "pipeline_option": r.pipeline_option,
                     "csv_ratings": " ".join(csv_letters), "pdf_ratings": " ".join(pdf_letters) if pdf_letters else "",
                     "result": result})
    return pd.DataFrame(rows)


def summarise(res: pd.DataFrame) -> str:
    counts = res.result.value_counts().to_dict()
    used = res[res.pipeline_option != ""]
    lines = [
        "NOAA rating transcription check (V5.1): software comparison with the PDF text layer, NOT a human review.",
        f"Source: {PDF.relative_to(ROOT)}; table: {RATINGS_CSV.relative_to(ROOT)}.",
        f"Rows checked: {len(res)}. match: {counts.get('match', 0)}; MISMATCH: {counts.get('MISMATCH', 0)}; "
        f"method not found on the cited page: {counts.get('method_not_found_on_page', 0)}.",
        f"Rows that feed the decision pipeline (pipeline_option set): {len(used)}; of these match: "
        f"{int((used.result == 'match').sum())}.",
        f"Table title on the cited page agrees with the CSV for {int(res.table_title_matches.sum())} of {len(res)} rows.",
        "Not checked: the letter-to-verdict mapping (D36, Proposed), the method-to-option crosswalk, and whether one NOAA table "
        "may stand for two ESI codes (3A and 4). These remain owner decisions.",
    ]
    bad = res[res.result != "match"]
    if not bad.empty:
        lines.append("Rows needing attention:")
        lines += [f"  {r.rating_id} p.{r.page} {r.noaa_method}: csv [{r.csv_ratings}] pdf [{r.pdf_ratings}] ({r.result})"
                  for r in bad.itertuples()]
    return "\n".join(lines) + "\n"


def main() -> int:
    if not available():
        print("NOAA PDF or pdftotext not available; nothing checked.")
        return 2
    res = check()
    OUT.mkdir(parents=True, exist_ok=True)
    res.to_csv(OUT / "noaa_rating_source_check.csv", index=False)
    text = summarise(res)
    (OUT / "noaa_rating_source_check_summary.txt").write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
