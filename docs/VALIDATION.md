# Validation of the record

Everything that was checked before release, and the code that does it. All checks read only the files of the Zenodo record (doi:10.5281/zenodo.23450639), except the re-run of the collection, which needs the pipeline.

| Check | Code | Result reported in the note |
|---|---|---|
| Files match their checksums; sample of chips opened and hashed | `python -m obscura_open25 verify DATA --chips 60` | no problems |
| Every chip sits at its facility; extent equals box size | `georeference_offsets`, `obscura_open25.qc` | all 1,355 chips contain the facility centre; median offset 48 m, largest 84 m |
| 14 internal consistency checks | `obscura_open25.qc.consistency_checks` | 14 of 14 pass |
| Value ranges of the raw targets | `obscura_open25.qc.value_ranges` | in `qc_results.json` |
| Coverage figure (windows, months, gas availability, cloud) | `obscura_open25.qc.coverage_figure` | `qc_coverage.png` in the record |
| Random split against facility-grouped split | `compare_splits` | see `EVALUATION.md` |
| Can a methane reading be predicted to exist? | `availability_auc` | AUC 0.63, 0.58, 0.70 |
| Re-run of the collection for 15 samples | `audit/rerun_check.py` | 15 of 15 identical in every field and chip pixel |

## Run it

```bash
python -m obscura_open25 qc DATA --out qc_output       # georeferencing, 14 checks, coverage figure, split comparison
python examples/reproduce_note.py DATA                 # every number in the note, written to results/note_results.json
python paper/check_note.py                             # the note's text against those numbers and the journal limits
```

## The 14 consistency checks

Raw methane, NO2 and CO are inside the plausibility limits used in the collection (`qc.LIMITS`); aerosol index between -6 and 10; fire is 0 or at least 300 K; the scene date is inside its window; pixel size equals box size divided by 384; `n_gas_observed` matches the blanks; every present gas has valid pixels behind it; every blank gas target has a reason; no duplicate site and window; sample identifiers are unique; chip cloud share is within the limit; all dates are inside the collection period.

## The re-run of the collection

`audit/rerun_check.py` runs the documented collection again for samples picked at random (some with blank targets) and compares every numeric field, the scene and granule identifiers and every pixel of the chip with the Zenodo files. It needs Earth Engine and the collection pipeline, which is released after the OBSCURA competition ends, so the script is not part of the tests. The outcome that the note reports is stored in `results/rerun_check_results.json`. It shows that the values can be rebuilt from the public archives, not that the procedure is correct: it is a re-run of the same code.

## What was not checked

The satellite products were not compared with ground measurements or other retrievals. The weather and elevation values were not independently verified. An independent re-implementation of the collection was not done. Chip positions are accurate to about 100 m.