# Changelog

## 1.2.0

Makes the validation and the data note reproducible from the repository.

* `qc` module and `python -m obscura_open25 qc`: georeferencing, 14 consistency checks, value ranges, coverage figure.
* `audit/rerun_check.py` and `results/rerun_check_results.json`: the re-run of the collection (15 of 15 identical).
* `paper/`: the data note source, `make_figure.py` and `check_note.py`, which checks the text against the computed numbers.
* `examples/reproduce_note.py` now writes `results/note_results.json` and covers every number in the note.
* `references/`: list of cited works with DOIs and the tool to highlight cited passages.
* `diagnostics` module: fold-mean baseline, leave-one-facility-out, per-facility scores, facility-identity and elevation-and-slope-only models.
* `docs/`: VALIDATION, PROTOCOL, CONSTRUCTION, SELECTION, FILES, REPRODUCIBILITY and an index; EVALUATION extended with the fold-mean baseline and the diagnostics.
* `results/`: per-facility scores and the software versions of the run.
* `diagnostics.bootstrap_understatement` (facility bootstrap, paired, against zero and against the training-fold mean), `fire_decomposition` (detection and brightness), `static_feature_identification`.
* `docs/RELATED.md`; fire, resampling, quality-filter and missing-feature details in `docs/CONSTRUCTION.md`; baseline roles and bootstrap in `docs/PROTOCOL.md`.
* Tests grew to 41.

## 1.1.0

Adds the evaluation tools and documentation behind the data note.

* `validation`: `grouped_folds`, `random_folds`, `cv_predictions`, `compare_splits` and `compare_splits_arrays` (random split against facility-grouped split).
* `observability`: `availability_auc` for predicting whether a satellite reading exists.
* `chipstats`: `surface_stats`, `chip_summary` and `chip_table` (cached).
* `georef`: `georeference_offsets` checks every chip against its facility.
* `examples/reproduce_note.py` and `docs/note_numbers.json` reproduce every number in the data note.
* `docs/GUIDELINES.md` and `docs/EVALUATION.md`; README and quick-start notebook rewritten around them.
* `CONTRIBUTING.md`. Tests grew from 21 to 33.

## 1.0.0

First release, matching version 1.0.0 of the dataset.

* `Dataset` class to read the tables, chips, targets and windows.
* Chip helpers: reflectance, scene classes, cloud mask, true-colour and short-wave infrared views.
* Target helpers: z-score to physical value conversion, fire temperature, masked RMSE.
* `verify_folder` and `python -m obscura_open25 verify` to check a download against the published checksums.
* Quick-start notebook.
