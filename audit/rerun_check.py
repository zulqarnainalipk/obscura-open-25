"""Reproducibility check against the Zenodo record: re-run the documented collection for released samples and compare.

    python audit/rerun_check.py DATA_FOLDER --pipeline PIPELINE_DIR --static-cache FILE [--n 15] [--out results/rerun_check_results.json]

This needs the collection pipeline (released after the OBSCURA competition ends) and Earth Engine access, so it
is not part of the tests. The result of the run that the data note reports is stored in
results/rerun_check_results.json. ``--static-cache`` is the pipeline's cache of terrain values per site and box.

What is compared with the re-run is only what is in the Zenodo files: samples.csv, features_full_precision.csv
and the chips in the zip archives. The facility centres and box sizes also come from sites.csv. The re-run itself
needs the collection pipeline and Earth Engine (and the list of neighbouring facilities, which the ring estimate
leaves out). It writes into a throw-away folder.

This shows the released numbers can be rebuilt from the public archives with the documented procedure. It is a
re-run of the same procedure, not an independent re-implementation. Results: the file given by --out.
"""
import io
import json
import math
import os
import shutil
import sys
import tempfile
import zipfile

import numpy as np
import pandas as pd
import rasterio

HERE = os.path.dirname(os.path.abspath(__file__))


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


if len(sys.argv) < 2 or not arg("--pipeline") or not arg("--static-cache"):
    sys.exit(__doc__)
REC = sys.argv[1]
sys.path.insert(0, arg("--pipeline"))
import pipeline as P  # noqa: E402  (the collection procedure being re-run)

N = int(arg("--n", 15))
OUT = arg("--out", os.path.join(HERE, "..", "results", "rerun_check_results.json"))
sm = pd.read_csv(os.path.join(REC, "samples.csv"), dtype={"sample_id": str}).set_index("sample_id")
ff = pd.read_csv(os.path.join(REC, "features_full_precision.csv"), dtype={"sample_id": str}).set_index("sample_id")
sites = pd.read_csv(os.path.join(REC, "sites.csv")).set_index("site_id")

rng = np.random.default_rng(7)
picked = []
for k, sid in enumerate(rng.permutation(sorted(sites.index))[:N]):
    rows = sm[sm.site_id == sid]
    miss = rows[rows.t_ch4.isna() | rows.t_no2.isna() | rows.t_co.isna()]
    pool = miss if (k % 3 == 0 and len(miss)) else rows
    picked.append(pool.index[int(rng.integers(len(pool)))])

out_root = os.path.join(tempfile.gettempdir(), "obscura_rerun_check")
if os.path.isdir(out_root):
    shutil.rmtree(out_root)
paths = P.setup_dirs_and_logging(out_root)
salt = "rerun-check"                      # only used to name the temporary chip files; not compared
roster, _ = P.load_sites(os.path.join(arg("--pipeline"), "sites.json"))
by_id = {s["id"]: s for s in roster}
P.init_earth_engine()
neighbor_map = P.compute_neighbor_map(roster)
ch4_band = P.choose_ch4_band()
static_cache = json.load(open(arg("--static-cache"), encoding="utf-8"))


def close(a, b, rel=1e-4, abs_=1e-6):
    if (a is None or (isinstance(a, float) and math.isnan(a))) and (b is None or (isinstance(b, float) and math.isnan(b))):
        return True
    if a is None or b is None or (isinstance(a, float) and math.isnan(a)) or (isinstance(b, float) and math.isnan(b)):
        return False
    return math.isclose(float(a), float(b), rel_tol=rel, abs_tol=abs_)


def compare(sample_id, rec):
    """Differences between a re-run record and the Zenodo row of the same sample."""
    z, f = sm.loc[sample_id], ff.loc[sample_id]
    diffs = []
    raw = {"raw_ch4": rec.get("ch4_delta"), "raw_no2": rec.get("no2_delta"), "raw_co": rec.get("co_delta"),
           "raw_aai": rec["targets_raw"].get("aai"), "raw_firms": rec["targets_raw"].get("firms")}
    for k, v in raw.items():
        if not close(v, z[k]):
            diffs.append(f"{k}: {v} vs {z[k]}")
    for k in ("ch4_site_count", "ch4_bg_count", "no2_site_count", "no2_bg_count", "co_site_count", "co_bg_count", "aai_site_count", "firms_px",
              "n_gas_observed", "orbit", "utm_epsg", "s2_cloud_frac", "s2_valid_frac", "chip_zero_frac"):
        if not close(rec.get(k), z[k]):
            diffs.append(f"{k}: {rec.get(k)} vs {z[k]}")
    if rec.get("s2_date") != z.s2_date:
        diffs.append(f"s2_date: {rec.get('s2_date')} vs {z.s2_date}")
    if sorted(rec.get("product_ids", [])) != sorted(json.loads(z.s2_product_ids)):
        diffs.append("s2_product_ids differ")
    if sorted(rec.get("ch4_granule_ids", [])) != sorted(json.loads(z.ch4_granule_ids)):
        diffs.append("ch4_granule_ids differ")
    names = {"temperature": "temperature_c", "humidity": "humidity_pct", "wind_speed": "wind_speed", "wind_direction": "wind_dir",
             "precipitation": "precipitation_m", "solar_rad": "solar_rad_mj", "elevation": "elevation", "slope": "slope"}
    for k, rk in names.items():
        if not close(rec.get(rk), f[k]):
            diffs.append(f"{k}: {rec.get(rk)} vs {f[k]}")
    for k, v in rec["indices"].items():
        if not close(v, f[k]):
            diffs.append(f"{k}: {v} vs {f[k]}")
    return diffs


results = []
for sid in picked:
    z = sm.loc[sid]
    site = dict(by_id[z.site_id])
    s = sites.loc[z.site_id]
    site["center"], site["box_km"] = [float(s.latitude), float(s.longitude)], float(s.box_km)      # from sites.csv
    grid = P.chip_grid(*site["center"], site["box_km"])
    static = static_cache[f"{z.site_id}|{site['box_km']}"]
    row = {"sample_id": sid, "site_id": z.site_id, "window_start": z.window_start}
    try:
        rec = P.process_window(paths, salt, ch4_band, site, grid, static, z.window_start, z.window_end, neighbor_map.get(z.site_id, []))
        row["status"] = rec.get("status")
        if rec.get("status") == "ok":
            row["field_differences"] = compare(sid, rec)
            with zipfile.ZipFile(os.path.join(REC, z.chip_archive)) as zf, rasterio.MemoryFile(zf.read(z.chip_file)) as mem, mem.open() as ds:
                a = ds.read()
            b = rasterio.open(os.path.join(paths["geo"], rec["chip_private_geo"])).read()
            row["chip_identical"] = bool(a.shape == b.shape and np.array_equal(a, b))
    except Exception as e:
        row["status"] = f"error: {type(e).__name__}: {str(e)[:120]}"
    results.append(row)
    print(sid, z.site_id[:24], row["status"], "| differences:", row.get("field_differences") or "none", "| chip identical:", row.get("chip_identical"), flush=True)

os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
json.dump(results, open(OUT, "w", encoding="utf-8"), indent=1, default=str)
n_ok = sum(1 for r in results if r["status"] == "ok")
n_same = sum(1 for r in results if r["status"] == "ok" and not r["field_differences"] and r.get("chip_identical"))
print(f"\nre-run {len(results)} samples: {n_ok} reproduced as ok, {n_same} identical to the Zenodo files in every compared field and every chip pixel")
shutil.rmtree(out_root, ignore_errors=True)
