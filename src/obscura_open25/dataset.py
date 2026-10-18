"""Reading OBSCURA-Open-25 from the folder that holds the Zenodo files."""
import hashlib
import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

TABLES = ["sites.csv", "samples.csv", "features.csv", "windows.csv", "scaling.json"]
TEXT_COLUMNS = {"sample_id": str}


class Dataset:
    """The 25-site dataset.

    Point it at the folder that contains the files downloaded from Zenodo (``samples.csv``,
    ``chips_*.zip`` and so on). Identifiers are always read as text.

    >>> ds = Dataset("path/to/record")           # doctest: +SKIP
    >>> chip = ds.read_chip(ds.samples.sample_id.iloc[0])   # doctest: +SKIP
    """

    def __init__(self, folder):
        self.folder = Path(folder)
        missing = [n for n in TABLES if not (self.folder / n).exists()]
        if missing:
            raise FileNotFoundError(f"{self.folder} is missing: {', '.join(missing)}")
        self.sites = pd.read_csv(self.folder / "sites.csv")
        self.samples = pd.read_csv(self.folder / "samples.csv", dtype=TEXT_COLUMNS)
        self.features = pd.read_csv(self.folder / "features.csv", dtype=TEXT_COLUMNS)
        self.windows = pd.read_csv(self.folder / "windows.csv", dtype=TEXT_COLUMNS)
        with open(self.folder / "scaling.json", encoding="utf-8") as f:
            self.scaling = json.load(f)
        precise = self.folder / "features_full_precision.csv"
        self.features_full_precision = pd.read_csv(precise, dtype=TEXT_COLUMNS) if precise.exists() else None
        self._index = self.samples.set_index("sample_id")

    def __len__(self):
        return len(self.samples)

    def __repr__(self):
        return f"Dataset({len(self.sites)} sites, {len(self)} samples, folder={str(self.folder)!r})"

    # ------------------------------------------------------------------ tables
    def sample(self, sample_id):
        """One row of ``samples.csv`` as a Series."""
        try:
            return self._index.loc[sample_id]
        except KeyError:
            raise KeyError(f"unknown sample_id {sample_id!r}") from None

    def merged(self, precise=False):
        """Samples joined with their site and feature columns, one row per sample."""
        feats = self.features_full_precision if (precise and self.features_full_precision is not None) else self.features
        feats = feats.drop(columns=[c for c in ("month",) if c in feats.columns and c in self.samples.columns])
        site_cols = ["site_id", "site_name", "country", "region", "facility_type", "latitude", "longitude"]
        out = self.samples.merge(feats, on="sample_id", how="left", suffixes=("", "_feature"))
        return out.merge(self.sites[site_cols], on="site_id", how="left")

    def samples_of(self, site_id):
        """The samples of one site."""
        if site_id not in set(self.sites.site_id):
            raise KeyError(f"unknown site_id {site_id!r}")
        return self.samples[self.samples.site_id == site_id]

    # ------------------------------------------------------------------ chips
    def _zip(self, name):
        return zipfile.ZipFile(self.folder / name)

    def read_chip_bytes(self, sample_id):
        """The GeoTIFF file of a sample, as bytes."""
        row = self.sample(sample_id)
        with self._zip(row.chip_archive) as z:
            return z.read(row.chip_file)

    def read_chip(self, sample_id):
        """The chip as an array of shape (14, height, width), unsigned 16-bit."""
        array, _ = self.read_chip_with_meta(sample_id)
        return array

    def read_chip_with_meta(self, sample_id):
        """The chip and a dictionary with its coordinate system, transform and bounds."""
        import rasterio

        with rasterio.MemoryFile(self.read_chip_bytes(sample_id)) as mem, mem.open() as ds:
            array = ds.read()
            meta = {"crs": ds.crs, "transform": ds.transform, "bounds": ds.bounds, "width": ds.width, "height": ds.height}
        return array, meta

    def iter_chips(self, site_id=None):
        """Yield (sample_id, chip) pairs, optionally for one site."""
        frame = self.samples if site_id is None else self.samples_of(site_id)
        for sample_id in frame.sample_id:
            yield sample_id, self.read_chip(sample_id)

    # ------------------------------------------------------------------ targets
    def targets(self, physical=False):
        """The five targets with ``sample_id``, as z-scores or (physical=True) in physical units."""
        from .targets import RAW_COLUMNS, TARGETS

        if physical:
            out = self.samples[["sample_id"] + [RAW_COLUMNS[t] for t in TARGETS]].copy()
            return out
        return self.samples[["sample_id"] + TARGETS].copy()

    # ------------------------------------------------------------------ integrity
    def verify(self, sample=None, seed=0):
        """Check the chips against the hashes in ``samples.csv``. Returns a list of problems (empty if fine).

        ``sample`` limits the check to that many random chips; None checks all of them.
        """
        problems = []
        frame = self.samples if sample is None else self.samples.sample(min(sample, len(self.samples)), random_state=seed)
        for _, row in frame.iterrows():
            try:
                data = self.read_chip_bytes(row.sample_id)
            except (KeyError, FileNotFoundError, zipfile.BadZipFile) as err:
                problems.append(f"{row.sample_id}: cannot read chip ({type(err).__name__})")
                continue
            if hashlib.sha256(data).hexdigest() != row.chip_sha256:
                problems.append(f"{row.sample_id}: hash does not match")
        return problems
