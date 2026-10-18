# Contributing

Thank you for looking at this. The repository is small on purpose.

## Report a problem

Open an issue with what you ran, what you expected and what happened. For a problem with the data itself, name the `sample_id` or `site_id` and the file. Please do not report coordinates or dates from other sources for facilities that are not in the dataset.

## Suggest or make a change

* Keep each function small, documented, and covered by a test that needs no download. The synthetic record in `tests/conftest.py` is there for this.
* Run `python -m pytest -q` before you send a change. Tests that need the real record are skipped unless `OBSCURA_OPEN25_DIR` is set.
* Keep the numbers in `docs/note_numbers.json` in step with the data note. If a change alters a reproduced number, say so in the change.
* Use plain language in documentation. Describe what the data are and what they are not.

## What will not be added here

The collection pipeline and the release audit are published separately, after the OBSCURA competition ends. Chips, tables and other data files are not committed to this repository; they live in the Zenodo record.
