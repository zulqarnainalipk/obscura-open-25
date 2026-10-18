"""The diagnostics on small arrays (no download needed)."""
import numpy as np

from obscura_open25.diagnostics import fold_mean_baseline, facility_mean_predictor, per_facility_rmse


def test_fold_mean_baseline_uses_only_training_rows():
    y = np.array([1.0, 3.0, np.nan, 5.0, 7.0, 9.0])
    folds = np.array([0, 0, 0, 1, 1, 1])
    pred = fold_mean_baseline(y, folds)
    assert np.allclose(pred[:3], 7.0) and np.allclose(pred[3:], 2.0)


def test_facility_mean_predictor_random_and_grouped():
    y = np.array([1.0, 1.2, 5.0, 5.2])
    groups = np.array(["a", "a", "b", "b"])
    random = facility_mean_predictor(y, groups, np.array([0, 1, 0, 1]))
    assert np.allclose(random, [1.2, 1.0, 5.2, 5.0])               # each row gets the other row of its facility
    grouped = facility_mean_predictor(y, groups, np.array([0, 0, 1, 1]))
    assert np.allclose(grouped, 0.0)                                # the facility is never in training: falls back to zero


def test_per_facility_rmse_compares_with_zero():
    y = np.array([1.0, 1.0, 2.0, np.nan])
    pred = np.array([1.0, 1.0, 0.0, 0.0])
    out = per_facility_rmse(y, pred, np.array(["a", "a", "b", "b"]))
    assert out["a"] == (0.0, 1.0, 2) and out["b"][2] == 1 and out["b"][0] == 2.0