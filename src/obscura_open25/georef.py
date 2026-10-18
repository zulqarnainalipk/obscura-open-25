"""Check that every chip sits where its facility is."""
import math

import numpy as np


def haversine_m(lat1, lon1, lat2, lon2):
    """Great-circle distance in metres between two points given in degrees."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371000.0 * math.asin(math.sqrt(h))


def georeference_offsets(ds):
    """Distance in metres from each chip's centre to its facility centre, and whether the facility lies inside the chip.

    Returns a DataFrame with ``sample_id``, ``offset_m``, ``inside`` and ``extent_km`` (side of the chip). Reads every chip's header and coordinates only.
    """
    import pandas as pd
    from rasterio.warp import transform

    xy = ds.sites.set_index("site_id")[["latitude", "longitude"]]
    rows = []
    for row in ds.samples.itertuples():
        _, meta = ds.read_chip_with_meta(row.sample_id)
        b = meta["bounds"]
        lon, lat = transform(meta["crs"], "EPSG:4326", [(b.left + b.right) / 2], [(b.bottom + b.top) / 2])
        s = xy.loc[row.site_id]
        sx, sy = transform("EPSG:4326", meta["crs"], [s.longitude], [s.latitude])
        inside = bool(b.left <= sx[0] <= b.right and b.bottom <= sy[0] <= b.top)
        rows.append({"sample_id": row.sample_id, "offset_m": haversine_m(s.latitude, s.longitude, lat[0], lon[0]), "inside": inside, "extent_km": (b.right - b.left) / 1000})
    return pd.DataFrame(rows)
