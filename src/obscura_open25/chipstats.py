"""Summary numbers for image chips, and a cached table for a whole dataset."""
import os
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

from .chips import CLOUD_CLASSES, band, scene_class, valid_mask

SCL_CLASSES = (2, 3, 4, 5, 6, 7, 8, 9, 10, 11)
STAT_BANDS = ("B2", "B3", "B4", "B8", "B11", "B12")


def surface_stats(chip):
    """Ten numbers that describe the surface of a chip: short-wave infrared and near-infrared brightness, and cover shares.

    Computed over pixels that have data and are not cloud or cloud shadow.
    """
    ok = valid_mask(chip)
    r = lambda name: (band(chip, name)[ok] * 1e-4) if ok.any() else np.zeros(1)
    scl = scene_class(chip)
    b12 = r("B12")
    return {"swir12_mean": float(b12.mean()), "swir12_p95": float(np.percentile(b12, 95)), "swir11_mean": float(r("B11").mean()),
            "nir_mean": float(r("B8").mean()), "red_mean": float(r("B4").mean()), "water_share": float((scl == 6).mean()),
            "veg_share": float((scl == 4).mean()), "bare_share": float((scl == 5).mean()),
            "cirrus_share": float((scl == 10).mean()), "cloud_share": float(np.isin(scl, CLOUD_CLASSES).mean())}


def chip_summary(chip):
    """About 54 summary numbers for a chip: band statistics, hot-pixel shares, vegetation spread, scene-class shares."""
    ok = valid_mask(chip, min_pixels=500)
    scl = scene_class(chip)
    out = {}
    for name in STAT_BANDS:
        v = band(chip, name)[ok] * 1e-4 if ok.any() else np.zeros(1)
        p50, p95, p99 = np.percentile(v, [50, 95, 99])
        out.update({f"c_{name}_mean": v.mean(), f"c_{name}_std": v.std(), f"c_{name}_p50": p50, f"c_{name}_p95": p95,
                    f"c_{name}_p99": p99, f"c_{name}_max": v.max()})
    b4, b8, b11, b12 = (band(chip, n)[ok] * 1e-4 for n in ("B4", "B8", "B11", "B12"))
    ndvi = (b8 - b4) / (b8 + b4 + 1e-6)
    out.update({"c_ndvi_std": ndvi.std() if ndvi.size else 0.0, "c_ndvi_p95": np.percentile(ndvi, 95) if ndvi.size else 0.0,
                "c_b12_b11_p95": np.percentile(b12 / (b11 + 1e-6), 95) if b11.size else 0.0,
                "c_hot12_gt_0.2": float((b12 > 0.2).mean()) if b12.size else 0.0, "c_hot12_gt_0.4": float((b12 > 0.4).mean()) if b12.size else 0.0,
                "c_hot11_gt_0.4": float((b11 > 0.4).mean()) if b11.size else 0.0})
    for cls in SCL_CLASSES:
        out[f"c_scl_{cls}"] = float((scl == cls).mean())
    out["c_cloudprob"] = float(band(chip, "CLDPRB").mean())
    out["c_valid_frac"] = float(ok.mean())
    return {k: float(v) for k, v in out.items()}


def chip_table(ds, func=surface_stats, workers=4, cache=None):
    """One row of chip statistics per sample, as a DataFrame with ``sample_id``. Reads every chip once.

    If ``cache`` is a file path, the table is read from it when it exists and written to it otherwise.
    """
    if cache and os.path.exists(cache):
        return pd.read_csv(cache, dtype={"sample_id": str})

    def one(sample_id):
        return {"sample_id": sample_id, **func(ds.read_chip(sample_id))}

    with ThreadPoolExecutor(workers) as pool:
        table = pd.DataFrame(list(pool.map(one, ds.samples.sample_id)))
    if cache:
        table.to_csv(cache, index=False)
    return table
