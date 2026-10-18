# Evaluation protocol

The exact design behind the case study in the data note (Table 1 and the text after it). The code is `obscura_open25.validation`, `obscura_open25.diagnostics` and `obscura_open25.observability`; `examples/reproduce_note.py` runs all of it.

## Data and targets

* One row per sample (1,355 rows, 25 facilities). Inputs are the 29 columns of `features.csv`, used as released (no scaling, no feature selection, no imputation; missing values are passed to the model, which handles them natively).
* Five targets, the z-scored `t_*` columns of `samples.csv`. A target is **eligible** on a row where it was measured. The same eligible rows are used for training and scoring in the random and in the grouped evaluation. Methane has 49% of rows eligible, nitrogen dioxide and carbon monoxide 99%, the aerosol index and fire 100%.
* The z-score constants (`scaling.json`) are the mean and standard deviation of every measured value of a target (after the log transform for fire) in a larger training collection that includes the 25 facilities here; they were fixed before this study and are given with the data. Because the collection contains the held-out facilities, the constants are **not independent of the test folds**. They are a single affine map applied to every row, so they do not change which rows a model sees, and a tree-based regressor's predictions follow an affine rescaling of the target; they therefore do not change the comparison between splits. They do decide where "zero" lies: zero is the mean of that collection, not the mean of a training fold. For that reason zero is labelled a **fixed-reference baseline**, not a leakage-free training baseline, and the **training-fold mean baseline**, computed from training rows only, is the primary baseline. The constants were computed once, from the measured values of each target (fire after the log transform), before any split in this study.

## Model

`sklearn.ensemble.HistGradientBoostingRegressor(max_iter=100, learning_rate=0.06, max_depth=3, min_samples_leaf=20, random_state=0)`, all other settings at the scikit-learn defaults (early stopping is off for fewer than 10,000 rows). Nothing was tuned. One model per target and fold, fitted on the eligible training rows only. Nothing is fitted outside the training rows, so no preprocessing step can see a test fold. There is no feature selection, scaling, imputation or tuning, and nothing in the code uses information from held-out facilities except the fixed z-score constants discussed above.

Z-scores are stored per row in `samples.csv`. A blank target stays blank (NaN) and the row is excluded for that target in training and scoring; held-out rows use the same constants as training rows.

## Splits

* **Grouped split.** The 25 facilities are put in a random order (set by the seed) and dealt out to 5 folds in turn, so every fold holds exactly 5 whole facilities. The order, and so which facilities share a fold, changes with the seed. Folds are not balanced by sample count (a facility has 34 to 72 samples).
* **Random split.** A random permutation of the 1,355 rows is cut into 5 folds by position (about 271 rows each), so a facility is spread over all folds.
* Each split type is repeated for seeds 0 to 4. That makes 5 seeds x 5 folds = 25 fits per target and split type, 250 fits in all for the table.

## Metric

For a seed, all out-of-fold predictions on eligible rows are pooled and `RMSE = sqrt(mean((y - prediction)^2))`, in z-score units. The table gives the mean over the 5 seeds. The five seeds are five different repeated five-fold partitions (not five folds of one partition). `grouped_sd` is the standard deviation (n in the denominator) of the five seed-level grouped RMSEs. It measures how much the answer moves with the fold assignment, not the sampling uncertainty of having 25 facilities.

**Uncertainty over facilities.** `diagnostics.bootstrap_understatement` averages each row's out-of-fold squared error over the five seeds (random split and grouped split), resamples the 25 facilities with replacement 2,000 times, and recomputes the RMSEs. It reports the 95% interval (2.5th and 97.5th percentile) of the understatement and of the grouped RMSE minus the RMSE of predicting zero (negative means the model beats zero). All bootstrap intervals in the repository (understatement, grouped minus zero, grouped minus fold mean, and the fire detection AUC) use the same procedure: facilities are resampled with replacement, the same resampled facilities are used for every quantity compared inside a replicate, and the interval is the percentile interval of the replicates. The intervals for every target are in EVALUATION.md and esults/note_results.json. The same resampled facilities are used for the random and the grouped split (paired), the understatement ratio is recomputed in every replicate, and the interval is the 2.5th to 97.5th percentile of the replicates. A facility with no measured value of a target contributes no rows to that target in a replicate. Three different things should not be confused: the seed spread (how the fold assignment matters), the bootstrap interval (how much the result depends on which of these 25 facilities are included), and generalisation to new industrial sites in the world (not measured here: the facilities were selected for quality, so grouped evaluation tests transfer to held-out facilities of this curated set).

The interval of the grouped RMSE minus the training-fold mean RMSE is the primary comparison with a baseline; the interval against zero is also stored (`grouped_minus_zero_*`). Only the aerosol index has an interval that excludes zero against either baseline. This is a statement about this model, this protocol and these facilities; it does not show that the other targets contain no information.

**Predict zero**: the RMSE of predicting z = 0 for every eligible row. It needs no fitting and uses the reference of `scaling.json`. **Training-fold mean**: for every fold, predict the mean of the measured values of the training rows of that fold (the facilities outside the fold in the grouped split, the other rows in the random split), pooled over folds and averaged over seeds. It is what a model that has learned only the average would do, so it is the baseline that a facility-grouped model has to beat; it differs from zero by how far the training mean lies from the reference. In the table the fold-mean column is the grouped split.

**Understated by** = 1 - RMSE(random) / RMSE(grouped), computed from the unrounded RMSEs and shown as a whole percent. The table shows the RMSEs rounded to two decimals, so recomputing the percentage from the table can differ by a point (for nitrogen dioxide 1 - 0.49 / 0.69 gives 29%, while the unrounded values 0.4887 and 0.6943 give 30%). `paper/check_note.py` recomputes every percentage from the unrounded values in `results/note_results.json`.

## Diagnostics (`diagnostics.robustness`)

* Leave-one-facility-out: 25 folds of one facility (deterministic).
* Fold by fold: the smallest and largest RMSE of a single grouped fold over all seeds; the number of facilities at which the model beats zero (seed 0 predictions).
* Is the gap caused by recognising the facility? Two models that know almost nothing but the facility. (1) The **facility-mean predictor**: for each held-out row, the mean of the measured values of the same facility's training rows (0 if the facility has none in training; it always does under a random split and never does under a grouped split), per seed and pooled like the other models. (2) A model that sees only elevation and slope. Both are constant within a facility, but together they take only 17 distinct values over the 25 facilities, so they do not identify every facility uniquely. If these models match the full model under a random split, the result is consistent with facility recognition; it does not prove it or exclude other explanations. Their grouped-split results are reported too (`grouped_static_only`, `grouped_facility_mean`): the elevation-and-slope model is no better than the baselines there, so it carries no transferable signal. The facility-mean predictor needs the facility to be in the training rows, so it is a diagnostic for the random split and cannot be used for a genuinely unseen facility.

## Availability of methane

Label: 1 if methane was measured. Model: `HistGradientBoostingClassifier(max_iter=120, learning_rate=0.06, max_depth=3, min_samples_leaf=20)`, grouped 5-fold split (seed 0), the same folds for all three feature sets: weather (6 features), chip surface statistics, and all 29 features with the chip statistics. The AUC is computed over all out-of-fold predictions together.

## What this does and does not show

It shows how much a random split changes the apparent skill of one small model on these 25 facilities. It does not show that a model measures emissions, that a target is predictable in general, or that the same gap occurs for other models and data.