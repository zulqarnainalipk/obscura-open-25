"""Helpers for the 14-layer Sentinel-2 chips of OBSCURA-Open-25.

A chip is an array of shape (14, height, width), unsigned 16-bit. The layers are
B1 B2 B3 B4 B5 B6 B7 B8 B8A B9 B11 B12 (surface reflectance times 10,000), then SCL
(scene classification) and CLDPRB (cloud probability, 0 to 100).
"""
import numpy as np

BAND_ORDER = ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B9", "B11", "B12", "SCL", "CLDPRB"]
N_REFLECTANCE_BANDS = 12
SCALE = 1e-4

#: Scene classification classes, as numbered in the SCL layer.
SCL_NAMES = {0: "no data", 1: "saturated or defective", 2: "dark area or topographic shadow", 3: "cloud shadow",
             4: "vegetation", 5: "not vegetated", 6: "water", 7: "unclassified", 8: "cloud, medium probability",
             9: "cloud, high probability", 10: "thin cirrus", 11: "snow or ice"}
#: Classes treated as cloud or cloud shadow by default.
CLOUD_CLASSES = (3, 8, 9, 10)


def band_index(name):
    """Position of a band in the chip array, for example band_index("B11") is 10."""
    try:
        return BAND_ORDER.index(name)
    except ValueError:
        raise KeyError(f"unknown band {name!r}; choose from {BAND_ORDER}") from None


def band(chip, name):
    """One layer of the chip as given (not rescaled)."""
    return chip[band_index(name)]


def reflectance(chip):
    """The 12 reflectance bands as floats between 0 and about 1, shape (12, height, width)."""
    return chip[:N_REFLECTANCE_BANDS].astype("float32") * SCALE


def scene_class(chip):
    """The scene classification layer as integers."""
    return chip[band_index("SCL")].astype("int16")


def cloud_probability(chip):
    """The cloud probability layer, 0 to 100."""
    return chip[band_index("CLDPRB")].astype("float32")


def valid_mask(chip, cloud_classes=CLOUD_CLASSES, min_pixels=1):
    """True where a pixel has data and is not cloud or cloud shadow.

    If fewer than ``min_pixels`` pixels would remain, the mask of pixels with data is returned instead.
    """
    has_data = band(chip, "B4") > 0
    clear = ~np.isin(scene_class(chip), cloud_classes)
    mask = has_data & clear
    return mask if mask.sum() >= min_pixels else has_data


def stretch(rgb, low=2, high=98):
    """Rescale each colour channel of an (height, width, 3) array to 0..1 between two percentiles."""
    out = np.zeros(rgb.shape, dtype="float32")
    for k in range(3):
        lo, hi = np.percentile(rgb[..., k], [low, high])
        out[..., k] = np.clip((rgb[..., k] - lo) / max(hi - lo, 1e-6), 0, 1)
    return out


def composite(chip, bands, do_stretch=True):
    """Three named bands as an image array of shape (height, width, 3)."""
    if len(bands) != 3:
        raise ValueError("a composite needs exactly three bands")
    img = np.stack([band(chip, b).astype("float32") for b in bands], axis=-1)
    return stretch(img) if do_stretch else img


def true_colour(chip):
    """Red, green and blue (B4, B3, B2)."""
    return composite(chip, ["B4", "B3", "B2"])


def swir_composite(chip):
    """Short-wave infrared view (B12, B11, B4). Hot and bare surfaces glow orange, vegetation looks green."""
    return composite(chip, ["B12", "B11", "B4"])


def ndvi(chip, mask=None):
    """Normalised difference vegetation index per pixel, optionally restricted to a mask (others become NaN)."""
    b8, b4 = band(chip, "B8").astype("float32"), band(chip, "B4").astype("float32")
    out = (b8 - b4) / (b8 + b4 + 1e-6)
    if mask is not None:
        out = np.where(mask, out, np.nan)
    return out
