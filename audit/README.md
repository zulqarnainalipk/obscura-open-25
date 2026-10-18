# Audit scripts

* `rerun_check.py`: re-runs the documented collection for a random sample of released samples and compares the result with the Zenodo files. It needs the collection pipeline (released after the OBSCURA competition ends) and Earth Engine access. Usage is in the docstring. The result reported in the data note is in `../results/rerun_check_results.json`.

The checks that need only the Zenodo files are in the package: `python -m obscura_open25 qc DATA`. See `../docs/VALIDATION.md`.