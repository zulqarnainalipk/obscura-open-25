import shutil

import numpy as np
import pandas as pd
import pytest
from rasterio.warp import transform

from obscura_open25 import Dataset, chip_summary, chip_table, georeference_offsets, surface_stats


def _chip(seed=0, size=40):
    rng = np.random.default_rng(seed)
    chip = rng.integers(300, 4000, size=(14, size, size)).astype("uint16")
    chip[12] = 5
    chip[12, :5] = 8                      # cloud
    chip[12, 5:9] = 6                     # water
    chip[13] = 20
    return chip


def test_surface_stats_keys_and_ranges():
    s = surface_stats(_chip())
    assert {"swir12_mean", "swir12_p95", "nir_mean", "water_share", "veg_share", "cloud_share"} <= set(s)
    assert 0 < s["swir12_mean"] < 1 and s["swir12_p95"] >= s["swir12_mean"]
    assert s["water_share"] == pytest.approx(4 / 40) and s["cloud_share"] == pytest.approx(5 / 40)


def test_chip_summary_has_the_documented_features():
    s = chip_summary(_chip(size=60))
    assert len(s) == 54 and "c_B12_p99" in s and "c_scl_6" in s and "c_hot12_gt_0.4" in s
    assert all(np.isfinite(v) for v in s.values())


def test_chip_table_one_row_per_sample_and_cache(record, tmp_path):
    folder, _ = record
    ds = Dataset(folder)
    cache = tmp_path / "surface.csv"
    table = chip_table(ds, workers=2, cache=str(cache))
    assert list(table.sample_id) == list(ds.samples.sample_id) and cache.exists()
    again = chip_table(ds, cache=str(cache))                 # second call reads the cache
    assert again.shape == table.shape and again.sample_id.dtype == object


def test_georeference_offsets_zero_when_site_is_at_the_chip_centre(record, tmp_path):
    folder, _ = record
    copy = tmp_path / "rec"
    shutil.copytree(folder, copy)
    ds = Dataset(copy)
    _, meta = ds.read_chip_with_meta(ds.samples.sample_id.iloc[0])
    b = meta["bounds"]
    lon, lat = transform(meta["crs"], "EPSG:4326", [(b.left + b.right) / 2], [(b.bottom + b.top) / 2])
    sites = pd.read_csv(copy / "sites.csv")
    sites["latitude"], sites["longitude"] = lat[0], lon[0]       # every chip in the fixture has the same footprint
    sites.to_csv(copy / "sites.csv", index=False)
    off = georeference_offsets(Dataset(copy))
    assert len(off) == 5 and off.inside.all() and off.offset_m.max() < 1.0


def test_georeference_offsets_flag_a_misplaced_site(record):
    folder, _ = record
    off = georeference_offsets(Dataset(folder))               # fixture sites are far from the chips
    assert not off.inside.any() and off.offset_m.min() > 1000
