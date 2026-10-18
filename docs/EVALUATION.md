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

## Fold mean baseline and diagnostics

"Predict zero" is the mean of the z-score reference (`scaling.json`), not the mean of the 25 facilities or of a training fold. The table above is therefore repeated with the mean of the training folds as the baseline, together with the diagnostics of `obscura_open25.diagnostics.robustness` (full protocol in [PROTOCOL.md](PROTOCOL.md)).

| Target | Grouped | Predict zero | Fold mean | Leave-one-facility-out | Smallest and largest fold | Facilities beating zero |
|---|---|---|---|---|---|---|
| Methane | 1.00 | 0.98 | 1.00 | 0.99 | 0.76 to 1.19 | 12 of 25 |
| NO2 | 0.69 | 0.73 | 0.71 | 0.68 | 0.32 to 1.04 | 19 of 25 |
| CO | 0.75 | 0.75 | 0.76 | 0.74 | 0.55 to 0.96 | 13 of 25 |
| Smoke and dust | 0.64 | 1.05 | 1.02 | 0.64 | 0.57 to 0.75 | 22 of 25 |
| Fire and flare | 1.04 | 0.91 | 0.93 | 1.06 | 0.44 to 1.59 | 15 of 25 |

Is the gap between the splits facility recognition? Under a random split, a model that sees only elevation and slope (constant within a facility) and a predictor that returns the mean of the same facility's training rows give:

| Target | Full model | Elevation and slope only | Facility mean |
|---|---|---|---|
| Methane | 0.89 | 0.89 | 0.84 |
| NO2 | 0.49 | 0.57 | 0.52 |
| CO | 0.67 | 0.69 | 0.65 |
| Smoke and dust | 0.56 | 0.81 | 0.72 |
| Fire and flare | 0.64 | 0.65 | 0.63 |

For methane, carbon monoxide and fire, knowing only the facility is as good as the full model, so the random-split score reflects facility recognition. The aerosol index gains beyond facility identity. This holds for these data and this model; it does not show that random splitting has the same effect elsewhere.
## Uncertainty from having 25 facilities

The spread over seeds only shows how the answer moves with the fold assignment. A bootstrap over facilities (2,000 resamples of the 25 facilities, see [PROTOCOL.md](PROTOCOL.md)) gives intervals that reflect the small number of facilities:

| Target | Understated by, percent (95% interval) | Grouped RMSE minus zero RMSE (95% interval) |
|---|---|---|
| Methane | 11 (5 to 17) | -0.04 to 0.07 |
| NO2 | 30 (21 to 37) | -0.12 to 0.05 |
| CO | 11 (7 to 16) | -0.04 to 0.04 |
| Smoke and dust | 13 (8 to 18) | -0.58 to -0.25 |
| Fire and flare | 38 (12 to 57) | -0.01 to 0.34 |

Every understatement interval is above zero: a random split flatters every target. Only the aerosol index beats predicting zero with an interval that excludes zero; for the other four targets the model cannot be told apart from zero, and the fire result (grouped worse than zero) is a point estimate whose interval includes zero. Per-facility scores are in `results/per_facility_scores.csv`.

Against the primary baseline (the training-fold mean) the interval of grouped minus fold-mean RMSE is -0.06 to 0.06 for methane, -0.09 to 0.07 for NO2, -0.05 to 0.03 for CO, -0.49 to -0.27 for the aerosol index and -0.01 to 0.34 for fire; see `results/note_results.json` for the exact values.

## Fire as detection and as brightness

The stored fire value is 0 for no detection and the highest detected brightness temperature otherwise (see `CONSTRUCTION.md`). Splitting it: 14.8% of samples have a detection; predicting a detection for held-out facilities gives a grouped AUC of 0.41 (95% bootstrap interval over facilities 0.27 to 0.53, not distinguishable from chance), an exploratory result for this classifier and these facilities; on the 200 detected samples the grouped RMSE is 2.33 (model), 2.25 (training-fold mean) and 2.12 (zero).