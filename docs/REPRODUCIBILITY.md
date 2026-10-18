# Reproducibility

What is needed to repeat the results, what was used, and what is and is not demonstrated.

## Software that produced the numbers

`examples/reproduce_note.py` writes `results/environment.json` next to its results. The values below are from the run that matches the data note.

| Software | Version |
|---|---|
| Python | 3.12.10 |
| numpy | 2.5.4 |
| pandas | 2.3.3 |
| rasterio (GDAL) | 1.5.2 (3.12.2) |
| scikit-learn | 1.9.1 |
| matplotlib | 3.11.2 (figures only) |
| pytest | 9.1.1 |

The package asks for numpy 1.24, pandas 2.0, rasterio 1.3 and scikit-learn 1.3 or newer. Results of the gradient-boosting models can differ in the last digits between scikit-learn versions; the numbers in the note are rounded to two decimals. `reproduce_note.py` accepts a difference of 0.011 for the error values and none for counts.

## Repeat the results from the Zenodo files

```bash
pip install -e ".[analysis]"
python -m obscura_open25 verify data --chips 60          # the download is the published record
python examples/reproduce_note.py data                   # every number; about 10 minutes
python paper/check_note.py                               # the note's text matches those numbers
python -m obscura_open25 qc data --out qc_out            # the validation of the record
```

Nothing else is needed: no account, no key, no network. `data` is the folder with all files of the Zenodo record.

## Check that a release is the one described

A published Zenodo record is the described release when `python -m obscura_open25 verify DATA` reports no problems (all files match `SHA256SUMS.txt` and the tables) and `examples/reproduce_note.py DATA` ends with "all reproduced values match the note". The version of the code is in `pyproject.toml`, `CITATION.cff` and `CHANGELOG.md`; tag the GitHub release with the same number.

## Rebuilding the data from upstream products

The collection pipeline is released later. These are the upstream products it reads, as Earth Engine collection identifiers:

| Use | Identifier |
|---|---|
| Sentinel-2 surface reflectance | `COPERNICUS/S2_SR_HARMONIZED` |
| Sentinel-2 cloud probability | `COPERNICUS/S2_CLOUD_PROBABILITY` |
| Methane, nitrogen dioxide, carbon monoxide, aerosol index | `COPERNICUS/S5P/OFFL/L3_CH4`, `L3_NO2`, `L3_CO`, `L3_AER_AI` |
| Fire | `FIRMS` |
| Weather | `ECMWF/ERA5_LAND/DAILY_AGGR`, `ECMWF/ERA5_LAND/HOURLY` |
| Elevation | `COPERNICUS/DEM/GLO30_2024_1` |
| Water mask | `MODIS/006/MOD44W` |

The identifiers of the Sentinel-2 products and Sentinel-5P granules behind every sample are in `samples.csv` (`s2_product_ids`, `ch4_granule_ids`).

If an upstream product is reprocessed, renamed or withdrawn, a rebuild can give different values or fail. The released files do not depend on it: the chips, the values and the checksums are in the record. The re-run reported in the note (15 samples at 15 facilities, identical in every field and pixel) shows that the values could be rebuilt when it was done. It is a re-run of the same code, not an independent implementation, and it was not run for all 1,355 samples. `audit/rerun_check.py` repeats it with the pipeline.

## What is and is not demonstrated

* Demonstrated: the numbers in the note follow from the files of the record (`reproduce_note.py`, `check_note.py`); the files are intact; the chips are where the facilities are; the values can be rebuilt for the 15 tested samples.
* Not demonstrated: rebuilding all samples; agreement with ground measurements; an independent implementation of the collection.

## Continuous checks

`.github/workflows/tests.yml` runs the unit tests on Python 3.10 to 3.12 for every push. They use a tiny synthetic record and need no download. The tests on the real record run when `OBSCURA_OPEN25_DIR` points to the Zenodo files.