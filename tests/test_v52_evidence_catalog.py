"""V5.2 Evidence explorer data layer: traceability, provenance, filters, gaps and the read-only link to run_decision().

Run from the repository root:  python -m pytest tests/test_v52_evidence_catalog.py
These tests check that repository tables are shown faithfully and without invention; they are not scientific validation.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.shoreline_remediation import decision_pipeline as dp  # noqa: E402
from src.shoreline_remediation import evidence_catalog as EC  # noqa: E402

SOURCES = {"data/knowledge/literature_effects.csv": EC.KIND_STUDY, "data/knowledge/treatment_evidence_untested.csv": EC.KIND_LITERATURE,
           "data/knowledge/tables/evidence_effect.csv": EC.KIND_COMPOSER, "data/knowledge/mangrove_screening.csv": EC.KIND_SCREENING,
           "data/knowledge/tables/noaa_response_rating.csv": EC.KIND_SCREENING,
           "data/knowledge/tables/beach_literature_notes.csv": EC.KIND_SCREENING, "data/knowledge/evidence_verdicts.csv": EC.KIND_VERDICT}


@pytest.fixture(scope="module")
def cat():
    return EC.load_catalog()


def test_every_source_row_appears_once_and_no_extra_rows(cat):
    for rel in SOURCES:
        n_file = len(pd.read_csv(ROOT / rel, encoding="utf-8-sig", dtype=str, keep_default_na=False))
        assert (cat.source_file == rel).sum() == n_file, rel
    assert len(cat) == sum((cat.source_file == r).sum() for r in SOURCES)


def test_rows_are_traceable_to_a_file_and_identifier(cat):
    assert cat.record_id.is_unique and (cat.source_id != "").all()
    for rel in set(cat.source_file):
        assert (ROOT / rel).is_file(), rel
    assert set(cat.kind) <= set(EC.KINDS) and set(cat.kind) == set(EC.KINDS)
    for rel, kind in SOURCES.items():
        assert set(cat[cat.source_file == rel].kind) == {kind}, rel


def test_no_bom_in_ids_or_labels(cat):
    for col in ("source_id", "record_id", "option_code", "habitat_label"):
        assert not cat[col].str.contains("﻿").any(), col
    assert "A001" in set(cat.source_id)


def test_links_are_real_dois_or_urls_never_invented(cat):
    lit = pd.read_csv(ROOT / "data/knowledge/literature_effects.csv", encoding="utf-8-sig", dtype=str, keep_default_na=False)
    doi = dict(zip(lit.effect_id, lit.doi))
    rows = cat[cat.source_file == "data/knowledge/literature_effects.csv"]
    for r in rows.itertuples():
        if doi[r.source_id].strip():
            assert doi[r.source_id].strip() in r.link
        else:
            assert r.link == EC.NOT_IN_REPO
    assert ((cat.link.str.startswith("http")) | (cat.link == EC.NOT_IN_REPO)).all()
    assert (cat.citation != "").all()


def test_kinds_are_labelled_by_standing_and_never_merged(cat):
    assert "AI-extracted" in EC.KIND_STUDY and "Proposed" in EC.KIND_STUDY
    noaa = cat[cat.source_file == "data/knowledge/tables/noaa_response_rating.csv"]
    assert len(noaa) == 126 and noaa.status.str.contains("Proposed").all() and noaa.provenance.str.contains("AI").all()
    assert noaa.limitations.str.contains("not how well oil is removed").all()
    mang = cat[cat.source_file == "data/knowledge/mangrove_screening.csv"]
    assert mang.provenance.str.contains("AI-PROPOSED").all()
    assert "blanket owner attestation" in EC.KIND_NOTES[EC.KIND_STUDY]


def test_abstract_only_rows_carry_the_abstract_level_warning(cat):
    rows = cat[(cat.kind == EC.KIND_STUDY) & (cat.status == "abstract_only")]
    assert len(rows) == 19 and rows.provenance.str.contains("abstract level").all()
    assert not cat[(cat.kind == EC.KIND_STUDY) & (cat.status != "abstract_only")].provenance.str.contains("abstract level").any()


def test_habitat_class_mapping_agrees_with_the_pooling_script_and_the_pipeline(cat):
    from validation.literature_pooling import _habitat_class
    for label in set(cat.habitat_label) | {"salt marsh", "mangrove", "cobble beach", "bedrock", ""}:
        assert EC.habitat_class_of(label) == _habitat_class(label), label


def test_verdict_rows_are_shown_unchanged_and_not_called_pooled_or_effective(cat):
    v = cat[cat.kind == EC.KIND_VERDICT]
    src = pd.read_csv(ROOT / "data/knowledge/evidence_verdicts.csv", encoding="utf-8-sig", dtype=str, keep_default_na=False)
    assert len(v) == len(src) == 33
    assert set(re_verdict(x) for x in v.result) == set(src.verdict)
    assert not v.result.str.lower().str.contains("effective|recommend|benefit").any()
    assert "pool" not in EC.KIND_VERDICT.lower() and "no row is a meta-analytic pool" in EC.KIND_NOTES[EC.KIND_VERDICT]
    assert "not a measured null effect" in EC.KIND_NOTES[EC.KIND_VERDICT]
    assert not v.design.str.contains("pooled").any() and not v.location.str.contains("pooled").any()


def re_verdict(text):
    import re
    return re.match(r"verdict: ([^()]+)", text).group(1).strip()


def test_filters_and_search(cat):
    assert len(EC.filter_catalog(cat)) == len(cat)                                    # empty selection restricts nothing
    marsh = EC.filter_catalog(cat, habitat_classes=["marsh"])
    assert len(marsh) and (marsh.habitat_class == "marsh").all()
    study = EC.filter_catalog(cat, kinds=[EC.KIND_STUDY], esi=["1A"])
    assert len(study) and study.esi_codes.map(lambda v: "1A" in EC._tokens(v) or "ALL" in EC._tokens(v)).all()
    assert any("/" in c for c in study.esi_codes)                                       # multi-code values such as 1A/2A match a single code
    assert len(EC.filter_catalog(cat, text="Zengel")) > 0
    assert EC.filter_catalog(cat, text="zzz-no-such-text").empty
    assert EC.filter_catalog(cat, options=["No such option"]).empty
    both = EC.filter_catalog(cat, kinds=[EC.KIND_COMPOSER], habitat_classes=["rocky/hard"])
    assert both.empty                                                                 # a combination with no rows is empty, not an error


def test_gap_matrix_counts_match_the_catalog_and_do_not_call_a_gap_ineffective(cat):
    gm = EC.gap_matrix(cat)
    assert "oiling_effect" not in set(gm.option_code)
    for r in gm.itertuples():
        n = ((cat.kind == EC.KIND_STUDY) & (cat.option_code == r.option_code) & (cat.habitat_class == r.habitat_class)).sum()
        assert r.study_records == n and r.gap == (n == 0)
    assert gm.gap.any() and (~gm.gap).any()
    assert not gm.pipeline_verdicts.str.lower().str.contains("effective|recommend").any()
    hpw = gm[(gm.option_code == "high_pressure_heated_washing") & (gm.habitat_class == "rocky/hard")].iloc[0]
    assert hpw.study_records > 0 and "no clear difference" in hpw.pipeline_verdicts


@pytest.mark.parametrize("esi", ["1A", "8A", "10A"])
def test_pipeline_context_is_a_copy_of_run_decision(esi):
    ctx = EC.pipeline_context(esi)
    rep = dp.run_decision({}, habitat=esi, oiling_class="moderate", oil="medium").to_dict()
    assert ctx["decision_outcome_label"] == rep["decision_outcome_label"]
    assert [(o["option_code"], o["class"], o["category"]) for o in ctx["options"]] == \
        [(r["option"], r["recommendation_class"], r["recommendation_category"]) for r in rep["options"]]
    assert "no site record" in ctx["inputs"] and "moderate oiling, medium oil" in ctx["inputs"]


def test_pipeline_context_keeps_the_noaa_proposed_marker_and_unsupported_habitats_abstain():
    ctx = EC.pipeline_context("1A")
    rated = [o for o in ctx["options"] if o["rating"]]
    assert rated and all(o["rating_status"] == "Proposed, not human-verified" for o in rated)
    unsupported = EC.pipeline_context("3B")
    assert unsupported["options"] == [] and unsupported["scope_tier"] == "unsupported_habitat" and unsupported["abstentions"]


def test_esi_choices_come_from_the_habitat_table():
    codes = [c for c, _ in EC.esi_choices()]
    assert {"1A", "8A", "10A"} <= set(codes)


def test_composer_rows_keep_their_values_and_do_not_invent_a_location(cat):
    src = pd.read_csv(ROOT / "data/knowledge/tables/evidence_effect.csv", dtype=str, keep_default_na=False)
    rows = cat[cat.kind == EC.KIND_COMPOSER].set_index("source_id")
    assert len(rows) == len(src) == 10
    for r in src.itertuples():
        assert r.effect in rows.loc[r.effect_id].result and r.lo90 in rows.loc[r.effect_id].result
    assert rows.location.str.contains("location not a column").all()


def test_gap_matrix_reconciles_with_study_records_in_the_other_class(cat):
    """Study records whose habitat is not class-specific are not in the gap matrix; they stay findable under Habitat class 'other'."""
    gm = EC.gap_matrix(cat)
    studies = cat[(cat.kind == EC.KIND_STUDY) & (~cat.option_code.isin(EC.STUDY_OPTIONS_EXCLUDED))]
    in_matrix = int(gm.study_records.sum())
    other = int((studies.habitat_class == "other").sum())
    assert in_matrix + other == len(studies) and other == 4
    assert len(EC.filter_catalog(cat, habitat_classes=["other"], kinds=[EC.KIND_STUDY])) >= other


def test_multi_esi_beach_notes_get_a_deterministic_class(cat):
    notes = cat[cat.source_file == "data/knowledge/tables/beach_literature_notes.csv"]
    assert len(notes) == 8 and set(notes.habitat_class) == {"sand/gravel beach"}


def test_pipeline_context_reports_an_error_instead_of_raising(monkeypatch):
    def boom(*a, **k):
        raise ValueError("forced")
    monkeypatch.setattr(dp, "run_decision", boom)
    EC.pipeline_context.cache_clear()
    try:
        assert "forced" in EC.pipeline_context("1A")["error"]
    finally:
        EC.pipeline_context.cache_clear()
