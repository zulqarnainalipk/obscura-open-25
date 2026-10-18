"""Optional checks against the real record. Set OBSCURA_OPEN25_DIR to the folder with the downloaded Zenodo files."""
import os

import pytest

from obscura_open25 import Dataset, verify_folder

FOLDER = os.environ.get("OBSCURA_OPEN25_DIR")
pytestmark = pytest.mark.skipif(not FOLDER, reason="OBSCURA_OPEN25_DIR is not set")


def test_real_record_counts_and_integrity():
    ds = Dataset(FOLDER)
    assert len(ds.sites) == 25 and len(ds) == 1355
    assert verify_folder(FOLDER, chip_sample=40) == []


def test_real_record_chip_layout():
    ds = Dataset(FOLDER)
    chip, meta = ds.read_chip_with_meta(ds.samples.sample_id.iloc[0])
    assert chip.shape == (14, 384, 384) and meta["crs"] is not None


def test_real_record_validation_passes():
    from obscura_open25.qc import run_qc

    result = run_qc(Dataset(FOLDER), signal=False)
    assert result["issues"] == []
    assert len(result["checks"]) == 14 and all(result["checks"].values())
    assert result["georef"]["n"] == 1355 and result["georef"]["site_inside_chip"] == 1355