"""Evaluation helpers: facility-grouped validation and the random-versus-grouped comparison.

Rows from one facility resemble each other (same terrain, same layout, similar weather). A model checked on
random rows can recognise the facility and look much better than it will on a new one. These helpers keep every
facility wholly on one side of each split, and measure how much a random split would have overstated skill.
"""
import numpy as np
import pandas as pd

from .targets import NAMES, TARGETS, masked_rmse

DEFAULT_SEEDS = (0, 1, 2, 3, 4)


def grouped_folds(groups, n_folds=5, seed=0):
    """Fold number of every row, with each group (facility) entirely in one fold.

    Groups are dealt out to folds in a random order that depends on ``seed``.
    """
    groups = np.asarray(groups)
    unique = np.unique(groups)
    if len(unique) < n_folds:
        raise ValueError(f"{len(unique)} groups cannot fill {n_folds} folds")
    order = np.random.default_rng(seed).permutation(unique)
    fold_of = {g: i % n_folds for i, g in enumerate(order)}
    return np.array([fold_of[g] for g in groups])


def random_folds(n_rows, n_folds=5, seed=0):
    """Fold number of every row from a plain random split (this one leaks the facility)."""
    return np.random.default_rng(seed).permutation(n_rows) % n_folds


def default_model():
    """The small gradient-boosted regressor used throughout the documentation."""
    try:
        from sklearn.ensemble import HistGradientBoostingRegressor
    except ImportError as err:                                        # pragma: no cover
        raise ImportError("this needs scikit-learn: pip install scikit-learn") from err
    return HistGradientBoostingRegressor(max_iter=100, learning_rate=0.06, max_depth=3, min_samples_leaf=20, random_state=0)


def cv_predictions(X, y, folds, model_factory=default_model):
    """Out-of-fold predictions. Fitting uses only rows where ``y`` is measured; every row gets a prediction."""
    X, y, folds = np.asarray(X, dtype="float32"), np.asarray(y, dtype="float64"), np.asarray(folds)
    pred = np.full(len(y), np.nan)
    for k in np.unique(folds):
        check = folds == k
        fit = (~check) & ~np.isnan(y)
        if fit.sum() < 5:
            continue
        pred[check] = model_factory().fit(X[fit], y[fit]).predict(X[check])
    return pred


def compare_splits_arrays(X, targets, groups, n_folds=5, seeds=DEFAULT_SEEDS, model_factory=default_model):
    """Error of one model under a random split and under a grouped split, against predicting zero.

    ``targets`` is a DataFrame of z-scored targets (NaN where not measured). Returns one row per target with the
    mean error over the seeds for the random split (``random``) and the grouped split (``grouped``), the spread of
    the grouped error (``grouped_sd``), the error of predicting zero (``predict_zero``) and ``overstatement``,
    the share by which the random split understates the grouped error.
    """
    rows = {}
    for t in targets.columns:
        y = targets[t].to_numpy(dtype="float64")
        rnd, grp = [], []
        for seed in seeds:
            rnd.append(masked_rmse(y, cv_predictions(X, y, random_folds(len(y), n_folds, seed), model_factory)))
            grp.append(masked_rmse(y, cv_predictions(X, y, grouped_folds(groups, n_folds, seed), model_factory)))
        rows[t] = {"random": float(np.mean(rnd)), "grouped": float(np.mean(grp)), "grouped_sd": float(np.std(grp)),
                   "predict_zero": masked_rmse(y, np.zeros(len(y)))}
        rows[t]["overstatement"] = 1.0 - rows[t]["random"] / rows[t]["grouped"]
    return pd.DataFrame(rows).T


def compare_splits(ds, targets=TARGETS, n_folds=5, seeds=DEFAULT_SEEDS, model_factory=default_model):
    """The comparison for a :class:`Dataset`: 29 features, one model per target, facilities as groups."""
    feats = ds.features.set_index("sample_id").loc[ds.samples.sample_id]
    out = compare_splits_arrays(feats.to_numpy("float32"), ds.samples.set_index("sample_id").loc[ds.samples.sample_id, list(targets)].reset_index(drop=True),
                                ds.samples.site_id.to_numpy(), n_folds, seeds, model_factory)
    out.index = [NAMES[t] for t in out.index]
    return out
