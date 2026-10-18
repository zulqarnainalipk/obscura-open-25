import math

import numpy as np
import pytest

from obscura_open25 import (BAND_ORDER, SCL_NAMES, band, band_index, composite, fire_kelvin, masked_rmse, ndvi, reflectance,
                            scene_class, stretch, swir_composite, to_physical, to_zscore, true_colour, valid_mask)

SCALING = {"t_ch4": {"mean": 1.0, "std": 10.0}, "t_firms": {"mean": 0.5, "std": 1.1}}


def test_zscore_round_trip_for_gases():
    raw = np.array([-20.0, 0.0, 33.3])
    z = to_zscore(raw, "t_ch4", SCALING)
    assert np.allclose(to_physical(z, "t_ch4", SCALING), raw)
    assert math.isclose(z[1], -0.1)


def test_fire_transform_and_inverse():
    kelvin = np.array([0.0, 299.0, 300.0, 330.0, 400.0])
    z = to_zscore(kelvin, "t_firms", SCALING)
    assert np.isclose(z[0], z[1]) and np.isclose(z[0], z[2])                  # no detection and below the floor are the same
    back = fire_kelvin(to_physical(z, "t_firms", SCALING))
    assert np.allclose(back[[0, 1, 2]], 0.0) and np.allclose(back[[3, 4]], [330.0, 400.0])


def test_masked_rmse_ignores_missing_truth():
    assert masked_rmse([1.0, np.nan, 3.0], [0.0, 100.0, 3.0]) == pytest.approx(math.sqrt(0.5))
    assert math.isnan(masked_rmse([np.nan], [1.0]))


def test_band_lookup():
    assert BAND_ORDER[band_index("B11")] == "B11" and band_index("B11") == 10 and band_index("SCL") == 12
    with pytest.raises(KeyError):
        band_index("B13")
    assert 4 in SCL_NAMES and SCL_NAMES[6] == "water"


def _chip():
    rng = np.random.default_rng(0)
    chip = rng.integers(500, 3000, size=(14, 12, 12)).astype("uint16")
    chip[12] = 4
    chip[12, :3] = 8              # three rows of cloud
    chip[13] = 10
    return chip


def test_reflectance_scale_and_shape():
    chip = _chip()
    r = reflectance(chip)
    assert r.shape == (12, 12, 12) and r.dtype == np.float32
    assert np.allclose(r[0], chip[0] * 1e-4)


def test_valid_mask_removes_cloud_and_falls_back():
    chip = _chip()
    mask = valid_mask(chip)
    assert not mask[:3].any() and mask[3:].all()
    all_cloud = chip.copy()
    all_cloud[12] = 9
    assert valid_mask(all_cloud, min_pixels=5).all()                          # falls back to pixels with data
    assert scene_class(chip).dtype == np.int16


def test_composites_are_images_in_range():
    chip = _chip()
    for img in (true_colour(chip), swir_composite(chip)):
        assert img.shape == (12, 12, 3) and img.min() >= 0 and img.max() <= 1
    with pytest.raises(ValueError):
        composite(chip, ["B4", "B3"])
    flat = np.ones((4, 4, 3), dtype="float32")
    assert np.all(stretch(flat) == 0)                                           # no spread, no division blow-up


def test_ndvi_and_mask():
    chip = _chip()
    v = ndvi(chip)
    assert v.shape == (12, 12) and np.all(np.abs(v) <= 1.0)
    masked = ndvi(chip, valid_mask(chip))
    assert np.isnan(masked[:3]).all() and not np.isnan(masked[3:]).any()
    assert band(chip, "B8").shape == (12, 12)
