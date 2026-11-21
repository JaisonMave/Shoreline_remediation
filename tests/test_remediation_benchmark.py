import pytest

from validation.remediation_benchmark import benchmark, next_surveys, process_key


def test_mapping_never_substitutes_an_untreated_arm_for_an_unknown_technique():
    assert process_key("natural_attenuation") == "no_cleanup"
    assert process_key("manual_removal") == "manual_removal"
    with pytest.raises(ValueError, match="explicit process parameter"):
        process_key("planting (after mechanical cleanup)")


def test_no_target_or_unpaired_date_leaks_into_regression():
    rows = []
    for year, difference in enumerate([2, 4, 6, 300], start=2011):
        for role, value in (("reference", 30), ("intervention", 30 + difference)):
            rows.append(dict(role=role, value=value, n_plots=5, date=str(year), decimal_year=year))
    rows.append(dict(role="reference", value=999, n_plots=5, date="2015", decimal_year=2015))
    pairs = next_surveys(rows)
    assert len(pairs) == 3 and "linear" not in pairs[1]["predictions"]
    assert pairs[-1]["predictions"] == pytest.approx({"zero": 0, "persistence": 6, "linear": 8})
    assert pairs[-1]["errors"]["linear"] == pytest.approx(-292)


def test_real_pair_counts_and_matched_comparison():
    outcomes = benchmark()["outcomes"]
    for key in ("soil_tpah", "total_vegetation_cover"):
        assert len(outcomes[key]["transitions"]) == 1
        assert outcomes[key]["common_scores"] == {}
        assert outcomes[key]["challenger_verdict"] == "insufficient_paired_dates"
    retreat = outcomes["cumulative_shoreline_retreat"]
    assert retreat["common_test_pairs"] == 4 and len(retreat["transitions"]) == 6
    assert retreat["common_scores"]["linear"]["mae"] == pytest.approx(.284542, abs=1e-6)
    assert retreat["challenger_verdict"] == "fails_temporal_comparison"
