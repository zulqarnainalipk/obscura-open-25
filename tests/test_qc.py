"""The validation checks, on a small hand-made table (no download needed)."""
import numpy as np
import pandas as pd

from obscura_open25.qc import consistency_checks, georeference_summary, value_ranges


def _good():
    sm = pd.DataFrame({
        "sample_id": ["a", "b"], "site_id": ["s1", "s1"], "window_start": ["2022-03-01", "2022-04-01"], "window_end": ["2022-03-06", "2022-04-06"],
        "s2_date": ["2022-03-03", "2022-04-02"], "raw_ch4": [5.0, np.nan], "raw_no2": [20.0, 30.0], "raw_co": [1.0, 2.0], "raw_aai": [0.1, -0.3],
        "raw_firms": [0.0, 320.0], "t_ch4": [0.1, np.nan], "t_no2": [0.0, 0.1], "t_co": [0.0, 0.1], "t_aai": [0.0, 0.1], "t_firms": [0.0, 0.1],
        "gsd_m": [10.0, 10.0], "box_km": [3.84, 3.84], "n_gas_observed": [4, 3], "ch4_site_count": [10, 0], "no2_site_count": [5, 5],
        "co_site_count": [5, 5], "aai_site_count": [5, 5], "null_reasons": ["{}", '{"ch4": "no_pixels"}'], "s2_cloud_frac": [0.0, 0.1]})
    win = pd.DataFrame({"site_id": ["s1", "s1"], "window_start": ["2022-03-01", "2022-04-01"], "status": ["ok", "ok"]})
    return sm, win


def test_good_table_passes_all_14_checks():
    checks = consistency_checks(*_good())
    assert len(checks) == 14 and all(checks.values())


def test_each_kind_of_fault_is_caught():
    sm, win = _good()
    bad = sm.copy()
    bad.loc[0, "raw_ch4"] = 99.0
    assert not consistency_checks(bad, win)["raw_ch4 within the configured limit"]
    bad = sm.copy()
    bad.loc[0, "s2_date"] = "2022-05-01"
    assert not consistency_checks(bad, win)["scene date inside its window"]
    bad = sm.copy()
    bad.loc[1, "null_reasons"] = "{}"
    assert not consistency_checks(bad, win)["every blank target has a reason"]
    bad = sm.copy()
    bad.loc[0, "ch4_site_count"] = 0
    assert not consistency_checks(bad, win)["every present gas has valid pixels behind it"]
    assert not consistency_checks(sm, pd.concat([win, win]))["no duplicate site and window"]


def test_value_ranges():
    sm, _ = _good()
    assert value_ranges(sm)["raw_aai"] == [-0.3, 0.1]


def test_georeference_summary_flags_far_and_outside_chips():
    sm, _ = _good()
    ok = pd.DataFrame({"sample_id": ["a", "b"], "offset_m": [40.0, 80.0], "inside": [True, True], "extent_km": [3.84, 3.84]})
    summary, issues = georeference_summary(ok, None, sm)
    assert summary["max_m"] == 80.0 and issues == []
    far = ok.assign(offset_m=[40.0, 500.0], inside=[True, False], extent_km=[3.84, 5.0])
    _, issues = georeference_summary(far, None, sm)
    assert len(issues) == 3
