# obscura-open25

Python tools and a quick-start notebook for **OBSCURA-Open-25**: an open dataset of 1,355 samples from 25 industrial facilities. Each sample pairs a 14-layer Sentinel-2 image chip with five satellite-derived targets (methane, NO2 and CO enhancements, an aerosol index, fire intensity), plus weather, terrain and spectral features.

* **Dataset (Zenodo):** https://doi.org/[ZENODO DOI]. This repository holds no data; download the files from Zenodo.
* **Description of the dataset:** the data note [DATA NOTE DOI OR URL].
* **Licences:** code MIT (this repository). Data CC BY 4.0 (Zenodo record). Source attributions are in `NOTICE.md` of the record.

## What the package does

* Reads the tables, the chips (straight from the zip files) and the targets.
* Gives each sample's image as an array, with helpers for reflectance, the cloud mask, true-colour and short-wave infrared views.
* Converts z-scored targets back to physical values.
* Checks your download against the published checksums.

It does not contain the collection pipeline. The pipeline that built the data will be released after the OBSCURA competition ends ([KAGGLE COMPETITION URL]).

## Install

```bash
git clone [GITHUB REPOSITORY URL]
cd obscura-open-25
pip install -e ".[notebook]"
```

Python 3.9 or newer. The package needs `numpy`, `pandas` and `rasterio`. The `notebook` extra adds `matplotlib`, `scikit-learn` and `jupyter`.

## Get the data

Download all files of the Zenodo record into one folder, for example `data/`. Keep the zip files as they are.

```bash
python -m obscura_open25 verify data            # check every file against SHA256SUMS.txt
python -m obscura_open25 verify data --chips 50 # same, but open only 50 random chips
```

## Quick start

```python
from obscura_open25 import Dataset, true_colour, swir_composite

ds = Dataset("data")
print(ds)                                     # Dataset(25 sites, 1355 samples, ...)

row = ds.samples.iloc[0]
chip = ds.read_chip(row.sample_id)            # array (14, 384, 384), unsigned 16-bit
rgb = true_colour(chip)                       # (384, 384, 3) image in 0..1

table = ds.merged()                           # samples + site columns + features, one row per sample
```

Read `sample_id` as text. A few identifiers look like numbers (for example `5e42214447929041`), and `Dataset` keeps them as strings. If you read the csv files yourself, use `dtype={"sample_id": str}`.

The notebook `notebooks/quick_start.ipynb` walks through the sites, the windows that gave no sample, the targets, a site time series, an image chip, and a small model checked with site-grouped cross-validation.

## Main pieces

| Piece | What it does |
|---|---|
| `Dataset(folder)` | `.sites`, `.samples`, `.features`, `.windows`, `.scaling`; `.read_chip(id)`, `.read_chip_with_meta(id)`, `.iter_chips(site_id)`, `.merged(precise=False)`, `.targets(physical=False)`, `.verify()` |
| `verify_folder(folder)` | Checks files against `SHA256SUMS.txt`, tables against each other, chips against their hashes |
| `reflectance`, `scene_class`, `valid_mask`, `true_colour`, `swir_composite`, `ndvi` | Chip helpers |
| `to_zscore`, `to_physical`, `fire_kelvin`, `masked_rmse` | Target helpers |

## A note on the targets

`t_*` columns are z-scores with constants from the whole OBSCURA training set (`scaling.json` in the record). `raw_*` columns hold physical values: ppb, micromol/m2, mmol/m2, an index, and kelvin. A blank target means the satellite could not measure it, which is not a zero. Small enhancements of either sign are mostly retrieval noise.

## Tests

```bash
pip install -e ".[test]"
python -m pytest -q
```

The tests build a tiny synthetic record, so they need no download. To also run the checks against the real record, set `OBSCURA_OPEN25_DIR` to the folder with the Zenodo files first.

## Cite

Please cite the dataset (see the Zenodo record) and, if you use the code, this repository (`CITATION.cff`).

## Author

Zulqarnain Ali, ORCID [0009-0009-0281-882X](https://orcid.org/0009-0009-0281-882X).
