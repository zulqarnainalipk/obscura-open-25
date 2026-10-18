# obscura-open25

Python tools, guidelines and a worked case study for **OBSCURA-Open-25**: an open dataset of 1,355 samples from 25 industrial facilities. Each sample pairs a 14-layer Sentinel-2 image chip with five satellite-derived targets (methane, NO2 and CO enhancements, an aerosol index, fire intensity), plus weather, terrain and spectral features.

* **Dataset (Zenodo):** https://doi.org/10.5281/zenodo.23450639. This repository holds no data; download the files from Zenodo.
* **Data note:** [DATA NOTE DOI OR URL]. This repository is the code behind it. Every number in the note is computed from the Zenodo files and can be reproduced with `examples/reproduce_note.py`.
* **Licences:** code MIT (this repository). Data CC BY 4.0 (Zenodo record). Source attributions are in `NOTICE.md` of the record.

## What is here

| Part | What it does |
|---|---|
| `Dataset` | Reads the tables, the chips (straight from the zip files), the targets and the attempted windows |
| `validation` | Facility-grouped validation, and the comparison of a random split with a grouped split |
| `diagnostics` | Fold-mean baseline, leave-one-facility-out, per-facility scores, and tests of whether a random split only recognises the facility |
| `chips`, `chipstats` | Reflectance, cloud mask, true-colour and short-wave infrared views, summary numbers for each chip |
| `observability` | Can the presence of a satellite reading be predicted for unseen facilities? |
| `georef`, `verify` | Check that every chip sits at its facility, and that a download matches the published checksums |
| `qc` | The validation of the record: georeferencing, 14 consistency checks, coverage figure (`python -m obscura_open25 qc DATA`) |
| `audit/rerun_check.py` | Re-runs the collection for random samples and compares with the record (needs the pipeline) |
| `paper/` | The data note source, Figure 1 code, and `check_note.py` that ties the text to the computed numbers |
| `references/` | The cited works with DOIs, and a tool to highlight the cited passages in the PDFs |
| `results/` | Numbers computed by the code (`note_results.json`), per-facility scores, software versions, the stored re-run result |
| `docs/` | Guidelines, file inventory, construction, selection, protocol, evaluation, validation, reproducibility (index: `docs/README.md`) |
| `examples/reproduce_note.py` | Recomputes every number in the data note and compares it with the note |
| `notebooks/quick_start.ipynb` | A guided tour with plots |

The collection pipeline that built the data is not here. It will be released later; `audit/rerun_check.py` needs it.
## Repository layout

```
src/obscura_open25/   the package: dataset, chips, chipstats, targets, validation, diagnostics,
                      observability, georef, qc, verify (one concern per module)
tests/                unit tests on a synthetic record; real-record tests when OBSCURA_OPEN25_DIR is set
examples/             reproduce_note.py: recomputes every number in the data note
paper/                the data note source, Figure 1 code, check_note.py
audit/                rerun_check.py: re-run of the collection (needs the pipeline)
results/              numbers computed by the code, environment versions, stored re-run result
docs/                 guidelines, file inventory, construction, selection, protocol, evaluation, validation, reproducibility
notebooks/ tools/     the quick-start notebook and the script that builds it
references/           cited works with DOIs; tool to highlight cited passages in PDFs
```

The documentation index is [docs/README.md](docs/README.md).
## Install

```bash
git clone https://github.com/zulqarnainalipk/obscura-open-25
cd obscura-open-25
pip install -e ".[analysis]"          # numpy, pandas, rasterio and scikit-learn
pip install -e ".[notebook]"          # adds matplotlib and jupyter
```

Python 3.9 or newer.

## Get the data and check it

Download all files of the Zenodo record into one folder, for example `data/`, and keep the zip files as they are.

```bash
python -m obscura_open25 verify data              # every file against SHA256SUMS.txt
python -m obscura_open25 verify data --chips 50   # also open 50 random chips and check their hashes
```

## Quick start

```python
from obscura_open25 import Dataset, compare_splits, true_colour

ds = Dataset("data")                            # Dataset(25 sites, 1355 samples, ...)
chip = ds.read_chip(ds.samples.sample_id.iloc[0])   # array (14, 384, 384), unsigned 16-bit
rgb = true_colour(chip)                         # (384, 384, 3) image in 0..1

table = ds.merged()                             # samples + site columns + features, one row per sample
print(compare_splits(ds).round(3))              # random split against facility-grouped split, five targets
```

Read `sample_id` as text. Four identifiers look like numbers (for example `5e42214447929041`), and `Dataset` keeps them as strings. If you read the csv files yourself, use `dtype={"sample_id": str}`.

## Guidelines in short

1. Identifiers are text.
2. A blank target is not a zero. Fit and score each target on the rows where it exists.
3. `t_*` are z-scores, `raw_*` are physical values (ppb, micromol/m2, mmol/m2, index, kelvin).
4. **Validate by facility, not by row.** A random split understates the error by 11 to 38 percent here, and for fire it reverses the conclusion.
5. Chips are not cloud-masked, and their positions are accurate to about 100 m.
6. The 25 facilities were chosen for data quality: they are clearer and better covered than typical.

The full list, with code, is in [docs/GUIDELINES.md](docs/GUIDELINES.md).

## Reproduce the data note

```bash
python examples/reproduce_note.py data           # every number, from the Zenodo files; writes results/note_results.json
python paper/make_figure.py data                 # redraws Figure 1
python paper/check_note.py                       # the note's text against those numbers, and the journal limits
python -m obscura_open25 qc data --out qc_out    # the validation of the record
```

`reproduce_note.py` prints each computed value next to the value the note was written with and exits with an error if any differs. `check_note.py` then fails if a number in `paper/data_note.tex` is not the number the code computed, or if the note exceeds 1,500 words, one figure or 12 references. The one result the code cannot recompute here is the re-run of the collection (15 of 15 samples identical), which needs Earth Engine and the pipeline; its stored outcome is `results/rerun_check_results.json`. See `docs/VALIDATION.md`.
## Tests

```bash
pip install -e ".[test]"
python -m pytest -q                              # unit tests on a tiny synthetic record, no download needed
OBSCURA_OPEN25_DIR=data python -m pytest -q      # also runs the checks on the real Zenodo files
```

The synthetic record only checks that the code does what it says. The checks on the real files, and every number in the note, use the real Zenodo files. Without `OBSCURA_OPEN25_DIR` the two real-data tests are skipped.

## Cite

Please cite the dataset (see the Zenodo record) and, if you use the code, this repository (`CITATION.cff`).

## Author

Zulqarnain Ali, ORCID [0009-0009-0281-882X](https://orcid.org/0009-0009-0281-882X). Issues and suggestions are welcome on GitHub; see `CONTRIBUTING.md`.
