"""A tiny synthetic record with the same file layout as the real Zenodo record, built in a temporary folder."""
import hashlib
import json
import zipfile

import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin

SIZE = 16
IDS = {"s1": ["5e42214447929041", "0a1b2c3d4e5f6071", "ffeeddccbbaa9988"], "s2": ["1234567890123456", "abcdef0123456789"]}


def _chip(seed):
    rng = np.random.default_rng(seed)
    data = rng.integers(200, 4000, size=(14, SIZE, SIZE)).astype("uint16")
    data[12] = rng.choice([4, 5, 6, 8], size=(SIZE, SIZE)).astype("uint16")      # scene classes
    data[13] = rng.integers(0, 100, size=(SIZE, SIZE)).astype("uint16")          # cloud probability
    return data


def _tif_bytes(data):
    with rasterio.MemoryFile() as mem:
        with mem.open(driver="GTiff", width=SIZE, height=SIZE, count=14, dtype="uint16", crs="EPSG:32638",
                      transform=from_origin(500000, 2800000, 10, 10)) as ds:
            ds.write(data)
        return mem.read()


@pytest.fixture(scope="session")
def record(tmp_path_factory):
    folder = tmp_path_factory.mktemp("record")
    rows, chips = [], {}
    for k, (site, ids) in enumerate(IDS.items()):
        with zipfile.ZipFile(folder / f"chips_{site}.zip", "w", zipfile.ZIP_STORED) as z:
            for j, sid in enumerate(ids):
                data = _chip(10 * k + j)
                raw = _tif_bytes(data)
                z.writestr(f"{sid}.tif", raw)
                chips[sid] = data
                rows.append({"sample_id": sid, "site_id": site, "site_key": f"key{k}", "month": 1 + j, "chip_archive": f"chips_{site}.zip",
                             "chip_file": f"{sid}.tif", "chip_sha256": hashlib.sha256(raw).hexdigest(),
                             "raw_ch4": 5.0 * j if j else np.nan, "raw_no2": 10.0 + j, "raw_co": 0.5 * j, "raw_aai": 0.2 * j,
                             "raw_firms": 0.0 if j == 0 else 320.0 + j, "t_ch4": 0.1 * j if j else np.nan, "t_no2": 0.2 * j,
                             "t_co": -0.1 * j, "t_aai": 0.05 * j, "t_firms": -0.4 if j == 0 else 1.0, "s2_cloud_frac": 0.01 * j})
    pd.DataFrame(rows).to_csv(folder / "samples.csv", index=False)
    pd.DataFrame({"site_id": ["s1", "s2"], "site_key": ["key0", "key1"], "site_name": ["Site one", "Site two"], "country": ["SA", "AU"],
                  "region": ["middle_east", "oceania"], "facility_type": ["refinery", "mining"], "latitude": [25.0, -30.0],
                  "longitude": [49.0, 140.0], "box_km": [3.0, 4.0]}).to_csv(folder / "sites.csv", index=False)
    pd.DataFrame({"sample_id": [r["sample_id"] for r in rows], "temperature": 25.0, "wind_speed": 3.0, "s2_cloud_frac": 0.0}).to_csv(
        folder / "features.csv", index=False)
    pd.DataFrame({"sample_id": [r["sample_id"] for r in rows], "month": [r["month"] for r in rows], "temperature": 25.1}).to_csv(
        folder / "features_full_precision.csv", index=False)
    pd.DataFrame({"site_id": [r["site_id"] for r in rows] + ["s1"], "window_start": ["2022-01-01"] * 6, "window_end": ["2022-01-06"] * 6,
                  "status": ["ok"] * 5 + ["cloudy"], "sample_id": [r["sample_id"] for r in rows] + [np.nan]}).to_csv(
        folder / "windows.csv", index=False)
    scaling = {"t_ch4": {"transform": "identity", "mean": 1.0, "std": 10.0, "n_train": 5}, "t_no2": {"transform": "identity", "mean": 30.0, "std": 40.0, "n_train": 5},
               "t_co": {"transform": "identity", "mean": 0.8, "std": 2.0, "n_train": 5}, "t_aai": {"transform": "identity", "mean": 0.2, "std": 0.6, "n_train": 5},
               "t_firms": {"transform": "ln(1+max(T21-300,0))", "mean": 0.5, "std": 1.1, "n_train": 5}}
    (folder / "scaling.json").write_text(json.dumps(scaling), encoding="utf-8")
    names = sorted(p.name for p in folder.iterdir())
    (folder / "SHA256SUMS.txt").write_text("".join(f"{hashlib.sha256((folder / n).read_bytes()).hexdigest()}  {n}\n" for n in names), encoding="utf-8")
    return folder, chips
