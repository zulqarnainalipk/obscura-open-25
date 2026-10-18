"""Reproduce every number in the data note from the Zenodo files.

    python examples/reproduce_note.py DATA_FOLDER [--quick] [--out results/note_results.json]

Computes the numbers from the files of the Zenodo record, prints each next to the value in ``docs/note_numbers.json``
(the values the note was written with) and exits with an error if any differs by more than the tolerance. It also
writes all computed values to ``results/note_results.json``; ``paper/check_note.py`` then checks the text of the
note against that file, so the note is tied to the code and not to typed-in numbers.

``--quick`` skips the steps that read every chip (georeferencing and methane availability).

One result is not computed here: the re-run of the collection for 15 samples. It needs Earth Engine and the
collection pipeline, which is released after the competition ends. Its outcome is stored in
``results/rerun_check_results.json`` (made by ``audit/rerun_check.py``) and is only read here.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

from obscura_open25 import Dataset, availability_auc, chip_table, compare_splits, verify_folder
from obscura_open25.observability import WEATHER
from obscura_open25.diagnostics import (bootstrap_understatement, fire_decomposition, per_facility_table, readable, robustness,
                                         static_feature_identification)
from obscura_open25.qc import run_qc
from obscura_open25.targets import TARGETS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
EXPECTED = json.load(open(os.path.join(ROOT, "docs", "note_numbers.json"), encoding="utf-8"))
RERUN = os.path.join(ROOT, "results", "rerun_check_results.json")


def _environment():
    """Versions of the software that produced the numbers (also written to results/environment.json)."""
    import platform

    import rasterio
    import sklearn
    env = {"python": platform.python_version(), "platform": platform.platform(), "numpy": np.__version__, "pandas": pd.__version__,
           "rasterio": rasterio.__version__, "gdal": rasterio.__gdal_version__, "scikit-learn": sklearn.__version__}
    json.dump(env, open(os.path.join(ROOT, "results", "environment.json"), "w", encoding="utf-8"), indent=1)
    return 1


def main(argv):
    folder = argv[1]
    quick = "--quick" in argv
    out = argv[argv.index("--out") + 1] if "--out" in argv else os.path.join(ROOT, "results", "note_results.json")
    ds = Dataset(folder)
    got = {}
    s, w = ds.samples, ds.windows
    got["facilities"] = len(ds.sites)
    got["samples"] = len(s)
    got["countries"] = int(ds.sites.country.nunique())
    got["regions"] = int(ds.sites.region.nunique())
    got["facility_types"] = int(ds.sites.facility_type.nunique())
    got["windows_attempted"] = len(w)
    got["windows_cloudy"] = int((w.status == "cloudy").sum())
    got["windows_no_scene"] = int((w.status == "no_s2").sum())
    got["windows_other_failed"] = int((~w.status.isin(["ok", "cloudy", "no_s2"])).sum())
    got["share_samples_percent"] = round(100 * len(s) / len(w))
    for t, name in (("t_ch4", "methane"), ("t_no2", "no2"), ("t_co", "co")):
        got[f"{name}_present_percent"] = round(100 * s[t].notna().mean())
    got["box_km_min"], got["box_km_max"] = float(ds.sites.box_km.min()), float(ds.sites.box_km.max())
    got["pixel_m_min"], got["pixel_m_max"] = round(float(s.gsd_m.min()), 1), round(float(s.gsd_m.max()), 1)
    got["download_problems"] = len(verify_folder(folder, chip_sample=40))
    files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
    got["files_in_record"] = len(files)
    got["record_gb"] = round(sum(os.path.getsize(os.path.join(folder, f)) for f in files) / 1e9, 1)
    got["chip_archives"] = sum(f.startswith("chips_") and f.endswith(".zip") for f in files)
    got["n_features"] = int(ds.features.shape[1] - 1)
    got["numeric_looking_ids"] = int(s.sample_id.str.fullmatch(r"\d+(e\d+)?", case=False).sum())

    cmp = compare_splits(ds)
    print(cmp.round(3).to_string())
    case = {}
    for key, name in zip(TARGETS, cmp.index):
        row = cmp.loc[name]
        case[key] = {"random": float(row.random), "grouped": float(row.grouped), "grouped_sd": float(row.grouped_sd), "zero": float(row.predict_zero)}
        for col, src in (("random", "random"), ("grouped", "grouped"), ("predict_zero", "predict_zero")):
            got[f"{key}_{col}"] = round(float(row[src]), 2)
    got["max_fold_spread"] = round(max(v["grouped_sd"] for v in case.values()), 3)
    share = s.groupby("site_id").t_ch4.apply(lambda x: x.notna().mean())
    got["ch4_site_share_min_percent"], got["ch4_site_share_max_percent"] = round(100 * share.min()), round(100 * share.max())
    month = pd.to_datetime(s.s2_date).dt.month
    season = s.t_ch4.notna().groupby(month.map(lambda m: (m % 12) // 3)).mean()      # 0 = Dec-Feb, 1 = Mar-May, 2 = Jun-Aug, 3 = Sep-Nov
    got["ch4_season_share_min_percent"], got["ch4_season_share_max_percent"] = round(100 * season.min()), round(100 * season.max())
    tercile = pd.qcut(s.s2_cloud_frac, 3, labels=False, duplicates="drop")
    by_cloud = s.t_ch4.notna().groupby(tercile).mean()
    got["ch4_clearest_third_percent"], got["ch4_cloudiest_third_percent"] = round(100 * by_cloud.iloc[0]), round(100 * by_cloud.iloc[-1])
    got["ch4_negative_percent"] = round(100 * (s.raw_ch4.dropna() < 0).mean())
    got["fire_zero_percent"] = round(100 * (s.raw_firms == 0).mean())
    got["windows_per_site"] = int(w.groupby("site_id").size().iloc[0])
    got["pair_days_max"] = int(s.pair_days.max())
    rob = robustness(ds)
    print(readable(rob).round(3).T.to_string())
    for key, v in rob.items():
        for k, x in v.items():
            if not isinstance(x, list):
                got[f"rob_{key}_{k}"] = round(x, 2) if isinstance(x, float) else x
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    per_facility_table(ds).round(4).to_csv(os.path.join(ROOT, "results", "per_facility_scores.csv"), index=False)
    n_sites, distinct, constant = static_feature_identification(ds)
    got["static_distinct_combinations"], got["static_constant_within_facility"] = distinct, int(constant)
    boot = bootstrap_understatement(ds)
    for key, v in boot.items():
        for k, x in v.items():
            got[f"boot_{key}_{k}"] = round(x, 3)
    fire = fire_decomposition(ds)
    for k, x in fire.items():
        got[f"fire_{k}"] = round(x, 3) if isinstance(x, float) else x
    _environment()

    if not quick:
        qc = run_qc(ds, signal=False)
        g = qc["georef"]
        got["chips_facility_inside"] = g["site_inside_chip"]
        got["georef_median_m"], got["georef_max_m"] = round(g["median_m"]), round(g["max_m"])
        got["consistency_checks_total"] = len(qc["checks"])
        got["consistency_checks_passed"] = int(sum(qc["checks"].values()))
        got["qc_issues"] = len(qc["issues"])
        surf = chip_table(ds)
        feats = ds.features.set_index("sample_id").loc[s.sample_id]
        data = pd.concat([feats.reset_index(drop=True), surf.set_index("sample_id").loc[s.sample_id].reset_index(drop=True)], axis=1)
        present, groups = s.t_ch4.notna().astype(int).to_numpy(), s.site_id.to_numpy()
        sets = {"availability_auc_weather": WEATHER, "availability_auc_chip": list(surf.columns[1:9]), "availability_auc_all": list(data.columns)}
        for key, cols in sets.items():
            got[key] = round(availability_auc(data[cols].to_numpy(), present, groups), 2)

    if os.path.exists(RERUN):
        rr = json.load(open(RERUN, encoding="utf-8"))
        got["rerun_total"] = len(rr)
        got["rerun_identical"] = sum(1 for r in rr if r["status"] == "ok" and not r.get("field_differences") and r.get("chip_identical"))

    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump({"numbers": got, "case_study": case, "robustness": rob, "bootstrap": boot, "fire": fire}, open(out, "w", encoding="utf-8"), indent=1)
    print(f"\nwrote {out}")

    bad = 0
    print(f"\n{'quantity':34s}{'reproduced':>14s}{'in the note':>14s}")
    for key, want in EXPECTED.items():
        if key not in got:
            continue
        tol = 0.011 if isinstance(want, float) and want < 5 else (1.0 if isinstance(want, float) else 0)
        ok = abs(got[key] - want) <= tol + 1e-9
        bad += not ok
        print(f"{key:34s}{got[key]:>14}{want:>14}   {'ok' if ok else 'DIFFERENT'}")
    print("\nall reproduced values match the note" if not bad else f"\n{bad} values differ from the note")
    return 1 if bad else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    raise SystemExit(main(sys.argv))
