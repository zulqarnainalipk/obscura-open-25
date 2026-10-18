# Changelog

## 1.0.0

First release, matching version 1.0.0 of the dataset.

* `Dataset` class to read the tables, chips, targets and windows.
* Chip helpers: reflectance, scene classes, cloud mask, true-colour and short-wave infrared views.
* Target helpers: z-score to physical value conversion, fire temperature, masked RMSE.
* `verify_folder` and `python -m obscura_open25 verify` to check a download against the published checksums.
* Quick-start notebook.
