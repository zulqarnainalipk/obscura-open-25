"""Can we tell in advance whether a satellite retrieval will exist for a sample?

A blank target means the satellite gave no usable reading. Methane is blank for about half of the samples even in
cloud-screened scenes. These helpers ask how well availability can be predicted for facilities the model has not seen.
"""
import numpy as np

from .validation import grouped_folds

WEATHER = ["temperature", "humidity", "wind_speed", "wind_direction", "precipitation", "solar_rad"]
SEASON = ["month_sin", "month_cos"]


def availability_auc(X, present, groups, n_folds=5, seed=0):
    """Area under the ROC curve (0.5 is chance) for predicting that a target is present, with facilities kept apart.

    ``X`` is the feature matrix, ``present`` is 1 where the target was measured, ``groups`` the facility of each row.
    Predictions for all rows come from models that never saw the row's facility, and the AUC is taken over all rows.
    """
    try:
        from sklearn.ensemble import HistGradientBoostingClassifier
        from sklearn.metrics import roc_auc_score
    except ImportError as err:                                        # pragma: no cover
        raise ImportError("this needs scikit-learn: pip install scikit-learn") from err
    X, y = np.asarray(X, dtype="float32"), np.asarray(present, dtype=int)
    folds = grouped_folds(groups, n_folds, seed)
    prob = np.zeros(len(y))
    for k in np.unique(folds):
        check = folds == k
        model = HistGradientBoostingClassifier(max_iter=120, learning_rate=0.06, max_depth=3, min_samples_leaf=20, random_state=0)
        model.fit(X[~check], y[~check])
        prob[check] = model.predict_proba(X[check])[:, 1]
    return float(roc_auc_score(y, prob))
