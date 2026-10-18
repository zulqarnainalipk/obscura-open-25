# Guidelines for using OBSCURA-Open-25

Short rules that prevent the usual mistakes. Each one comes with the code that follows it.

## 1. Read identifiers as text

Four `sample_id` values look like numbers (for example `5e42214447929041`). A reader that guesses types turns them into floats and the link to the chip is lost.

```python
import pandas as pd
samples = pd.read_csv("samples.csv", dtype={"sample_id": str})
```

`Dataset` already does this. If you open the files another way, pass `dtype={"sample_id": str}`.

## 2. A blank is not a zero

A blank target means the satellite could not measure it. Do not fill blanks with zero, and do not drop the whole row because one target is blank. Fit each target on the rows where it exists, and score only on rows where it exists.

```python
from obscura_open25 import masked_rmse
masked_rmse(truth, prediction)        # ignores NaN truths
```

Methane is blank for about half of the samples, nitrogen dioxide and carbon monoxide for about one percent, the aerosol index and fire intensity for none. Fire is 0 when FIRMS detected nothing. That cannot be told apart from a fire that was missed (small, short or under cloud), so treat 0 as no detection and not as a measured low temperature.

## 3. Know which scale you are on

* `t_*` columns are z-scores, with constants from the whole OBSCURA training set (`scaling.json`). They match the competition files.
* `raw_*` columns are physical values: ppb (methane), micromol per square metre (NO2), mmol per square metre (CO), an index (aerosol), kelvin (fire, 0 means none detected).
* Convert with `to_zscore`, `to_physical` and `fire_kelvin`. For fire, the z-score is taken after `ln(1 + max(T - 300, 0))`.

Gas values are enhancements: the average over a 10 km window around the facility minus the median of a 30 to 75 km ring. A negative value means less than the surroundings and, for small values, is mostly retrieval noise.

## 4. Validate by facility, not by row

Rows from one facility resemble each other. A random split lets a model recognise the facility, and the error looks much better than it will on a new facility. Compare against a baseline fitted on the training folds as well as against zero (see [PROTOCOL.md](PROTOCOL.md)). In this dataset a random split understates the error of a small model by 11 to 38 percent, and for fire it reverses the conclusion (see [EVALUATION.md](EVALUATION.md)).

```python
from obscura_open25 import grouped_folds, cv_predictions
folds = grouped_folds(ds.samples.site_id, n_folds=5, seed=0)    # each facility in one fold only
pred = cv_predictions(X, y, folds)                              # out-of-fold predictions
```

## 5. Treat chips as plain images with a small position error

* Shape (14, 384, 384), unsigned 16-bit. Layers 1 to 12 are surface reflectance times 10,000. Layer 13 is the scene classification and layer 14 the cloud probability.
* Chips are not cloud-masked. Use `valid_mask(chip)` or the scene classes.
* Pixel size differs between facilities (3.9 to 20.2 m) because each box was sized to its facility.
* The grid carries a random offset of below about 60 m, so chip positions are accurate to about 100 m. Do not use chips to measure anything finer than that.

## 6. Remember how the facilities were chosen

The 25 facilities were picked for data quality, so they are better covered and clearer than a typical facility. They are also few. Results here show what the data can support, not global performance.

## 7. Features come in two precisions

`features.csv` holds the rounded values used in the competition. `features_full_precision.csv` holds the same weather, terrain and index values before rounding. Use the first to match competition results and the second for new work.

## 8. Cite, and keep the notices

Cite the dataset (DOI in the README) and, if you use the code, this repository. The notices that come with the data (Copernicus Sentinel, ERA5-Land, the Copernicus elevation model, NASA FIRMS) are in `NOTICE.md` of the Zenodo record and apply to anything you redistribute.

## 9. Check your download

```bash
python -m obscura_open25 verify data
```

This compares every file with the published checksums and opens chips to check their hashes.
