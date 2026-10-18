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
from obscura_open25.qc import run_qc
from obscura_open25.targets import TARGETS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
EXPECTED = json.load(open(os.path.join(ROOT, "docs", "note_numbers.json"), encoding="utf-8"))
RERUN = os.path.join(ROOT, "results", "rerun_check_results.json")


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
    json.dump({"numbers": got, "case_study": case}, open(out, "w", encoding="utf-8"), indent=1)
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
