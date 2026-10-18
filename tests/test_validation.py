import numpy as np
import pandas as pd
import pytest

from obscura_open25 import availability_auc, compare_splits_arrays, cv_predictions, grouped_folds, random_folds


def test_grouped_folds_keep_every_group_in_one_fold():
    groups = np.repeat([f"site{i}" for i in range(12)], 7)
    folds = grouped_folds(groups, n_folds=4, seed=3)
    assert set(folds) == {0, 1, 2, 3}
    for g in np.unique(groups):
        assert len(set(folds[groups == g])) == 1                      # a facility is never split
    assert np.array_equal(folds, grouped_folds(groups, n_folds=4, seed=3))      # same seed, same folds
    assert not np.array_equal(folds, grouped_folds(groups, n_folds=4, seed=4))  # another seed deals them differently


def test_grouped_folds_need_enough_groups():
    with pytest.raises(ValueError, match="cannot fill"):
        grouped_folds(["a", "a", "b"], n_folds=5)


def test_random_folds_cover_all_folds_evenly():
    folds = random_folds(100, n_folds=5, seed=1)
    assert sorted(np.bincount(folds)) == [20] * 5


def test_cv_predictions_skip_blank_targets_when_fitting_but_predict_every_row():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(120, 3))
    y = X[:, 0] + rng.normal(scale=0.1, size=120)
    y[::4] = np.nan
    folds = random_folds(120, 4, 0)
    pred = cv_predictions(X, y, folds)
    assert not np.isnan(pred).any()
    k = ~np.isnan(y)
    assert np.corrcoef(pred[k], y[k])[0, 1] > 0.8


def _leaky_data(n_sites=15, per_site=30, seed=0):
    """Each facility has its own offset in the target and a marker in the features, so a random split can recognise it."""
    rng = np.random.default_rng(seed)
    offsets = rng.normal(size=n_sites)
    groups = np.repeat(np.arange(n_sites), per_site)
    marker = offsets[groups] + rng.normal(scale=0.01, size=len(groups))        # identifies the facility
    X = np.column_stack([marker, rng.normal(size=len(groups))])
    y = offsets[groups] + rng.normal(scale=0.2, size=len(groups))
    return X, pd.DataFrame({"t_a": y}), groups


def test_random_split_overstates_skill_when_facilities_leak():
    X, targets, groups = _leaky_data()
    res = compare_splits_arrays(X, targets, groups, n_folds=5, seeds=(0, 1))
    row = res.loc["t_a"]
    assert row.random < 0.6 * row.grouped
    assert row.overstatement > 0.4
    assert set(res.columns) == {"random", "grouped", "grouped_sd", "predict_zero", "overstatement"}


def test_no_gap_when_there_is_nothing_to_recognise():
    rng = np.random.default_rng(1)
    groups = np.repeat(np.arange(12), 25)
    X = rng.normal(size=(len(groups), 3))
    targets = pd.DataFrame({"t_a": rng.normal(size=len(groups))})
    row = compare_splits_arrays(X, targets, groups, n_folds=4, seeds=(0, 1)).loc["t_a"]
    assert abs(row.random - row.grouped) < 0.1


def test_availability_auc_detects_a_predictive_feature_and_chance():
    rng = np.random.default_rng(2)
    groups = np.repeat(np.arange(10), 40)
    signal = rng.normal(size=len(groups))
    present = (signal + rng.normal(scale=0.5, size=len(groups)) > 0).astype(int)
    assert availability_auc(signal.reshape(-1, 1), present, groups) > 0.8
    noise = rng.normal(size=(len(groups), 2))
    assert 0.35 < availability_auc(noise, present, groups) < 0.65
