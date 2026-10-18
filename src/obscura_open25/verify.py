"""Check a downloaded copy of the record against ``SHA256SUMS.txt`` and its own tables."""
import hashlib
from pathlib import Path

from .dataset import Dataset


def sha256_of(path, chunk=1 << 20):
    """SHA-256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def read_checksums(folder):
    """The mapping file name -> expected hash from ``SHA256SUMS.txt``."""
    sums = {}
    for line in (Path(folder) / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split("  ", 1)
            sums[name.strip()] = digest.strip()
    return sums


def verify_folder(folder, chip_sample=None):
    """Return a list of problems with a downloaded record (empty means everything is as published).

    Checks every file against ``SHA256SUMS.txt``, then that the tables agree with each other and with the
    chips. ``chip_sample`` limits the chip check to a number of random chips.
    """
    folder = Path(folder)
    problems = []
    if not (folder / "SHA256SUMS.txt").exists():
        return ["SHA256SUMS.txt is missing"]
    sums = read_checksums(folder)
    for name, want in sums.items():
        path = folder / name
        if not path.exists():
            problems.append(f"missing file: {name}")
        elif sha256_of(path) != want:
            problems.append(f"changed or damaged file: {name}")
    extra = {p.name for p in folder.iterdir() if p.is_file()} - set(sums) - {"SHA256SUMS.txt"}
    if extra:
        problems.append(f"files not in the checksum list: {sorted(extra)}")
    if problems:
        return problems
    ds = Dataset(folder)
    if set(ds.features.sample_id) != set(ds.samples.sample_id):
        problems.append("features.csv and samples.csv list different samples")
    ok = set(ds.windows[ds.windows.status == "ok"].sample_id)
    if ok != set(ds.samples.sample_id):
        problems.append("windows.csv and samples.csv disagree on which windows gave a sample")
    problems.extend(ds.verify(sample=chip_sample))
    return problems
