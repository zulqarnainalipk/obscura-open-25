# Case study: how much does a random split overstate skill?

A small gradient-boosted model is fitted for each target on the 29 features. Its error is measured two ways. In the **random split**, rows are assigned to five folds at random. In the **facility-grouped split**, whole facilities are assigned to folds, so the model is always checked on facilities it has not seen. The error is the root mean squared error in z-score units over the samples where the target was measured. Predicting zero (the training mean) is the reference. Everything is averaged over five different fold assignments.

```python
from obscura_open25 import Dataset, compare_splits

ds = Dataset("data")
print(compare_splits(ds).round(3))
```

Result on the 25 facilities:

| Target | Random split | Grouped split | Predict zero | Random split understates the grouped error by |
|---|---|---|---|---|
| Methane | 0.888 | 1.001 | 0.985 | 11% |
| NO2 | 0.489 | 0.694 | 0.731 | 30% |
| CO | 0.670 | 0.750 | 0.750 | 11% |
| Smoke and dust (aerosol index) | 0.557 | 0.642 | 1.051 | 13% |
| Fire and flare | 0.645 | 1.042 | 0.909 | 38% |

## What it shows

* **Every target looks better under a random split.** The model recognises the facility from its terrain and chip statistics and recalls its typical values.
* **For fire the conclusion flips.** A random split says the model beats predicting zero (0.645 against 0.909). A facility-grouped split says it is worse than predicting zero (1.042). Only the second is the right answer for a new facility.
* **The aerosol index is the one target that is clearly predictable for unseen facilities** (0.642 against 1.051). Nitrogen dioxide is slightly better than zero (0.694 against 0.731). Methane and carbon monoxide are no better than zero with this model.
* **With 25 facilities the numbers are noisy.** The spread over the five fold assignments (the `grouped_sd` column) is small for most targets and larger for nitrogen dioxide (0.034).

## Related question: can the presence of a methane reading be predicted?

Methane is blank for about half of the samples. For facilities the model has not seen, the presence of a methane value is only weakly predictable: area under the ROC curve 0.63 from weather alone, 0.58 from chip surface statistics alone and 0.70 from everything (0.5 is chance). Most of the pattern is site-specific.

```python
from obscura_open25 import availability_auc, chip_table
surface = chip_table(ds, cache="surface.csv")          # reads each chip once
```

## Reproduce

`python examples/reproduce_note.py data` recomputes these numbers, and every other number in the data note, and compares them with `docs/note_numbers.json`.
