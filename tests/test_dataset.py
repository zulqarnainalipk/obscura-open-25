import numpy as np
import pytest

from obscura_open25 import Dataset, verify_folder


def test_identifiers_stay_text(record):
    folder, _ = record
    ds = Dataset(folder)
    assert ds.samples.sample_id.dtype == object
    assert "5e42214447929041" in set(ds.samples.sample_id)      # looks like a number, must stay text
    assert "5e42214447929041" in set(ds.features.sample_id)
    assert len(ds) == 5 and len(ds.sites) == 2


def test_missing_files_are_reported(tmp_path):
    with pytest.raises(FileNotFoundError, match="samples.csv"):
        Dataset(tmp_path)


def test_read_chip_matches_what_was_written(record):
    folder, chips = record
    ds = Dataset(folder)
    for sid, want in chips.items():
        got = ds.read_chip(sid)
        assert got.shape == (14, 16, 16) and got.dtype == np.uint16
        assert np.array_equal(got, want)


def test_chip_meta_carries_georeference(record):
    folder, _ = record
    ds = Dataset(folder)
    _, meta = ds.read_chip_with_meta("5e42214447929041")
    assert meta["crs"].to_epsg() == 32638
    assert meta["width"] == 16 and abs(meta["transform"].a - 10) < 1e-9


def test_unknown_sample_gives_clear_error(record):
    folder, _ = record
    with pytest.raises(KeyError, match="unknown sample_id"):
        Dataset(folder).read_chip("nope")


def test_samples_of_site_and_iter_chips(record):
    folder, _ = record
    ds = Dataset(folder)
    assert len(ds.samples_of("s1")) == 3
    assert [sid for sid, _ in ds.iter_chips("s2")] == ["1234567890123456", "abcdef0123456789"]
    with pytest.raises(KeyError):
        ds.samples_of("missing")


def test_merged_has_one_row_per_sample_and_site_columns(record):
    folder, _ = record
    merged = Dataset(folder).merged()
    assert len(merged) == 5 and merged.sample_id.is_unique
    assert {"site_name", "latitude", "temperature"} <= set(merged.columns)
    assert len(Dataset(folder).merged(precise=True)) == 5


def test_targets_tables(record):
    folder, _ = record
    ds = Dataset(folder)
    assert list(ds.targets().columns) == ["sample_id", "t_ch4", "t_no2", "t_co", "t_aai", "t_firms"]
    assert list(ds.targets(physical=True).columns)[1] == "raw_ch4"


def test_verify_passes_on_a_clean_record(record):
    folder, _ = record
    assert Dataset(folder).verify() == []
    assert verify_folder(folder) == []


def test_verify_detects_a_damaged_chip(record, tmp_path):
    import shutil

    folder, _ = record
    copy = tmp_path / "copy"
    shutil.copytree(folder, copy)
    raw = bytearray((copy / "chips_s1.zip").read_bytes())
    raw[200] ^= 0xFF
    (copy / "chips_s1.zip").write_bytes(bytes(raw))
    problems = verify_folder(copy)
    assert problems and "chips_s1.zip" in problems[0]


def test_verify_detects_missing_and_extra_files(record, tmp_path):
    import shutil

    folder, _ = record
    copy = tmp_path / "copy2"
    shutil.copytree(folder, copy)
    (copy / "chips_s2.zip").unlink()
    assert any("missing file" in p for p in verify_folder(copy))
    (copy / "stray.txt").write_text("x")
    shutil.copy(folder / "chips_s2.zip", copy / "chips_s2.zip")
    assert any("not in the checksum list" in p for p in verify_folder(copy))
