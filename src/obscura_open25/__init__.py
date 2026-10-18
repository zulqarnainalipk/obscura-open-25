"""Tools for reading OBSCURA-Open-25: Sentinel-2 chips paired with Sentinel-5P targets at 25 industrial facilities."""
from .chips import (BAND_ORDER, CLOUD_CLASSES, SCL_NAMES, band, band_index, cloud_probability, composite, ndvi,
                    reflectance, scene_class, stretch, swir_composite, true_colour, valid_mask)
from .chipstats import chip_summary, chip_table, surface_stats
from .dataset import Dataset
from .georef import georeference_offsets
from .observability import availability_auc
from .targets import NAMES, RAW_COLUMNS, TARGETS, UNITS, fire_kelvin, masked_rmse, to_physical, to_zscore
from .validation import compare_splits, compare_splits_arrays, cv_predictions, grouped_folds, random_folds
from .verify import verify_folder

__version__ = "1.2.0"
__all__ = ["Dataset", "verify_folder", "TARGETS", "NAMES", "UNITS", "RAW_COLUMNS", "to_zscore", "to_physical", "fire_kelvin",
           "masked_rmse", "BAND_ORDER", "SCL_NAMES", "CLOUD_CLASSES", "band", "band_index", "reflectance", "scene_class",
           "cloud_probability", "valid_mask", "stretch", "composite", "true_colour", "swir_composite", "ndvi",
           "chip_summary", "chip_table", "surface_stats", "georeference_offsets", "availability_auc",
           "compare_splits", "compare_splits_arrays", "cv_predictions", "grouped_folds", "random_folds"]
