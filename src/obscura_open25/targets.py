"""The five targets: names, units, and conversion between z-scores and physical values."""
import math

import numpy as np

TARGETS = ["t_ch4", "t_no2", "t_co", "t_aai", "t_firms"]
RAW_COLUMNS = {"t_ch4": "raw_ch4", "t_no2": "raw_no2", "t_co": "raw_co", "t_aai": "raw_aai", "t_firms": "raw_firms"}
NAMES = {"t_ch4": "Methane", "t_no2": "NO2", "t_co": "CO", "t_aai": "Smoke and dust", "t_firms": "Fire and flare"}
UNITS = {"t_ch4": "ppb", "t_no2": "micromol/m2", "t_co": "mmol/m2", "t_aai": "index", "t_firms": "kelvin (hottest anomaly)"}
FIRE_FLOOR_K = 300.0


def to_zscore(raw, target, scaling):
    """Raw physical values to z-scores. Fire values (kelvin, 0 meaning none) go through ln(1 + max(T - 300, 0)) first."""
    m = scaling[target]
    values = np.asarray(raw, dtype="float64")
    if target == "t_firms":
        values = np.log1p(np.clip(values - FIRE_FLOOR_K, 0, None))
    return (values - m["mean"]) / m["std"]


def to_physical(z, target, scaling):
    """z-scores back to physical values.

    For gases and the aerosol index the result is the raw value. For fire it is the transformed value
    ln(1 + max(T - 300, 0)); use :func:`fire_kelvin` to turn it into a temperature.
    """
    m = scaling[target]
    return np.asarray(z, dtype="float64") * m["std"] + m["mean"]


def fire_kelvin(transformed):
    """Hottest thermal-anomaly temperature in kelvin from the transformed fire value. Zero means no detection."""
    t = np.asarray(transformed, dtype="float64")
    return np.where(t > 1e-9, FIRE_FLOOR_K + np.expm1(t), 0.0)


def masked_rmse(truth, prediction):
    """Root mean squared error over the entries where the truth is not NaN."""
    truth, prediction = np.asarray(truth, dtype="float64"), np.asarray(prediction, dtype="float64")
    keep = ~np.isnan(truth)
    if not keep.any():
        return math.nan
    return float(np.sqrt(np.mean((truth[keep] - prediction[keep]) ** 2)))
