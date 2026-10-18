"""Diagnostics that go with the random-versus-grouped comparison.

They answer: is the grouped result stable (leave-one-facility-out, fold by fold, facility by facility), is "predict
zero" a fair baseline (compare with the mean of the training folds), and is the gap between the splits caused by
the model recognising the facility (a model that knows only the facility, and one that sees only two
facility-constant features).
"""
import numpy as np

from .targets import NAMES, TARGETS, masked_rmse
from .validation import DEFAULT_SEEDS, cv_predictions, grouped_folds, random_folds

# Elevation and slope are averaged over the whole image box, so every sample of a facility has (almost) the same
# value: a model that sees only these can do little but recognise the facility.
STATIC_FEATURES = ("elevation", "slope")


def fold_mean_baseline(y, folds):
    """Out-of-fold prediction of the mean of the measured training rows (the fair version of "predict zero")."""
    y, folds = np.asarray(y, dtype="float64"), np.asarray(folds)
    pred = np.full(len(y), np.nan)
    for k in np.unique(folds):
        fit = (folds != k) & ~np.isnan(y)
        pred[folds == k] = y[fit].mean()
    return pred


def facility_mean_predictor(y, groups, folds):
    """Out-of-fold prediction of the mean of the same facility's measured training rows (zero where there are none).

    It uses nothing but the facility identity. Under a random split it shows how far recognising the facility alone
    can go; under a grouped split the facility is never in the training rows, so it falls back to zero.
    """
    y, groups, folds = np.asarray(y, dtype="float64"), np.asarray(groups), np.asarray(folds)
    pred = np.zeros(len(y))
    for k in np.unique(folds):
        fit = (folds != k) & ~np.isnan(y)
        means = {g: y[fit & (groups == g)].mean() for g in np.unique(groups[fit])}
        for i in np.where(folds == k)[0]:
            pred[i] = means.get(groups[i], 0.0)
    return pred


def per_facility_rmse(y, pred, groups):
    """RMSE of a prediction at each facility (over measured rows). Returns {facility: (model, zero, n)}."""
    y, pred, groups = np.asarray(y, dtype="float64"), np.asarray(pred), np.asarray(groups)
    out = {}
    for g in np.unique(groups):
        m = (groups == g) & ~np.isnan(y)
        if m.sum():
            out[g] = (masked_rmse(y[m], pred[m]), masked_rmse(y[m], np.zeros(m.sum())), int(m.sum()))
    return out


def robustness(ds, seeds=DEFAULT_SEEDS, n_folds=5):
    """All diagnostics for the five targets. Returns ``{target: {...}}`` with plain numbers.

    * ``lofo``: leave-one-facility-out RMSE (each facility predicted by a model fitted on the other 24).
    * ``grouped_fold_min`` and ``grouped_fold_max``: smallest and largest RMSE of a single fold, over all seeds.
    * ``grouped_train_mean`` and ``random_train_mean``: RMSE of predicting the training-fold mean.
    * ``sites_beating_zero`` out of ``sites_with_target``: facilities where the grouped model beats zero (seed 0).
    * ``random_facility_mean`` and ``grouped_facility_mean``: RMSE of the facility-identity-only predictor.
    * ``random_static_only`` and ``grouped_static_only``: RMSE of the model that sees only elevation and slope.
    * ``grouped_fold_scores``: RMSE of every single grouped fold (5 seeds x 5 folds), in seed order.
    """
    from .validation import default_model

    samples = ds.samples.set_index("sample_id").loc[ds.samples.sample_id]
    feats = ds.features.set_index("sample_id").loc[ds.samples.sample_id]
    X, static = feats.to_numpy("float32"), feats[list(STATIC_FEATURES)].to_numpy("float32")
    groups = ds.samples.site_id.to_numpy()
    n = len(groups)
    sites = len(np.unique(groups))
    out = {}
    for t in TARGETS:
        y = samples[t].to_numpy("float64")
        r = {}
        lofo = cv_predictions(X, y, grouped_folds(groups, sites, 0), default_model)
        r["lofo"] = masked_rmse(y, lofo)
        fold_scores, g_mean, r_mean, g_fac, r_fac, g_sta, r_sta = [], [], [], [], [], [], []
        for seed in seeds:
            gf, rf = grouped_folds(groups, n_folds, seed), random_folds(n, n_folds, seed)
            pred = cv_predictions(X, y, gf, default_model)
            for k in range(n_folds):
                m = gf == k
                fold_scores.append(masked_rmse(y[m], pred[m]))
            g_mean.append(masked_rmse(y, fold_mean_baseline(y, gf)))
            r_mean.append(masked_rmse(y, fold_mean_baseline(y, rf)))
            g_fac.append(masked_rmse(y, facility_mean_predictor(y, groups, gf)))
            r_fac.append(masked_rmse(y, facility_mean_predictor(y, groups, rf)))
            g_sta.append(masked_rmse(y, cv_predictions(static, y, gf, default_model)))
            r_sta.append(masked_rmse(y, cv_predictions(static, y, rf, default_model)))
            if seed == seeds[0]:
                per = per_facility_rmse(y, pred, groups)
                r["sites_with_target"] = len(per)
                r["sites_beating_zero"] = int(sum(1 for model, zero, _ in per.values() if model < zero))
        r.update({"grouped_fold_min": float(np.nanmin(fold_scores)), "grouped_fold_max": float(np.nanmax(fold_scores)),
                  "grouped_train_mean": float(np.mean(g_mean)), "random_train_mean": float(np.mean(r_mean)),
                  "grouped_facility_mean": float(np.mean(g_fac)), "random_facility_mean": float(np.mean(r_fac)),
                  "grouped_static_only": float(np.mean(g_sta)), "random_static_only": float(np.mean(r_sta))})
        r["grouped_fold_scores"] = [round(float(x), 3) for x in fold_scores]
        out[t] = {k: (v if isinstance(v, (int, list)) else float(v)) for k, v in r.items()}
    return out


def static_feature_identification(ds):
    """How well elevation and slope identify a facility: ``(facilities, distinct combinations, constant within each facility)``."""
    feats = ds.features.set_index("sample_id").loc[ds.samples.sample_id][list(STATIC_FEATURES)].reset_index(drop=True)
    feats["site_id"] = ds.samples.site_id.to_numpy()
    per_site = feats.groupby("site_id")[list(STATIC_FEATURES)]
    constant = bool((per_site.nunique() == 1).all().all())
    distinct = len(per_site.first().round(6).drop_duplicates())
    return int(feats.site_id.nunique()), int(distinct), constant


def bootstrap_understatement(ds, n_boot=2000, seeds=DEFAULT_SEEDS, n_folds=5, rng_seed=0):
    """Uncertainty that reflects having only 25 facilities: a bootstrap over facilities.

    Out-of-fold squared errors are averaged over the seeds for each row (random split and grouped split). Facilities are
    then resampled with replacement ``n_boot`` times and the RMSEs recomputed. Returns, for every target, the 95% interval
    (2.5th and 97.5th percentile) of ``understated`` (1 - random / grouped RMSE) and of ``grouped_minus_zero`` (grouped
    RMSE minus the RMSE of predicting zero, and ``grouped_minus_foldmean`` against the training-fold mean; negative means the\n    model beats the baseline). Facilities are resampled together for the random and the grouped split (paired), the ratio is\n    recomputed in every replicate, and a facility without measured values of a target contributes nothing to it.
    """
    from .validation import default_model

    samples = ds.samples.set_index("sample_id").loc[ds.samples.sample_id]
    X = ds.features.set_index("sample_id").loc[ds.samples.sample_id].to_numpy("float32")
    groups = ds.samples.site_id.to_numpy()
    sites, inv = np.unique(groups, return_inverse=True)
    rng = np.random.default_rng(rng_seed)
    draws = rng.integers(0, len(sites), size=(n_boot, len(sites)))
    counts = np.stack([np.bincount(d, minlength=len(sites)) for d in draws])            # (n_boot, n_sites)
    out = {}
    for t in TARGETS:
        y = samples[t].to_numpy("float64")
        ok = ~np.isnan(y)
        se_r, se_g, se_m = np.zeros(len(y)), np.zeros(len(y)), np.zeros(len(y))
        for seed in seeds:
            se_r += (y - cv_predictions(X, y, random_folds(len(y), n_folds, seed), default_model)) ** 2 / len(seeds)
            gf = grouped_folds(groups, n_folds, seed)
            se_g += (y - cv_predictions(X, y, gf, default_model)) ** 2 / len(seeds)
            se_m += (y - fold_mean_baseline(y, gf)) ** 2 / len(seeds)

        def per_site(v):
            return np.bincount(inv[ok], weights=v[ok], minlength=len(sites))

        sr, sg, sz, sm, n = per_site(se_r), per_site(se_g), per_site(y ** 2), per_site(se_m), np.bincount(inv[ok], minlength=len(sites))

        def rmse(s):
            return np.sqrt((counts @ s) / (counts @ n))

        understated = 1 - rmse(sr) / rmse(sg)
        diff = rmse(sg) - rmse(sz)
        diff_mean = rmse(sg) - rmse(sm)
        out[t] = {"understated_lo": float(np.percentile(understated, 2.5)), "understated_hi": float(np.percentile(understated, 97.5)),
                  "grouped_minus_zero_lo": float(np.percentile(diff, 2.5)), "grouped_minus_zero_hi": float(np.percentile(diff, 97.5)),
                  "grouped_minus_foldmean_lo": float(np.percentile(diff_mean, 2.5)), "grouped_minus_foldmean_hi": float(np.percentile(diff_mean, 97.5))}
    return out


def fire_decomposition(ds, seeds=DEFAULT_SEEDS, n_folds=5):
    """Fire as detection and as brightness: the stored fire value mixes the two (0 means no detection).

    The classifier is a ``HistGradientBoostingClassifier`` (100 iterations, learning rate 0.06, depth 3) on the 29 features; the label\n    is ``raw_firms > 0`` (a detection), the positive class; folds are the grouped folds of each seed. The interval is a 95% percentile\n    bootstrap over facilities of the AUC of the seed-averaged probabilities (exploratory).\n    Returns the share of samples with a detection, the grouped-split AUC of predicting a detection (mean over seeds), and,
    on the detected samples only, the grouped RMSE (z-score units) of the model, of the training-fold mean and of zero.
    """
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import roc_auc_score

    from .validation import default_model

    s = ds.samples.set_index("sample_id").loc[ds.samples.sample_id]
    X = ds.features.set_index("sample_id").loc[ds.samples.sample_id].to_numpy("float32")
    groups = ds.samples.site_id.to_numpy()
    y = s["t_firms"].to_numpy("float64")
    det = s["raw_firms"].to_numpy() > 0
    aucs, m_model, m_mean, m_zero = [], [], [], []
    prob_mean = np.zeros(len(y))
    for seed in seeds:
        folds = grouped_folds(groups, n_folds, seed)
        prob = np.zeros(len(y))
        for k in range(n_folds):
            chk = folds == k
            clf = HistGradientBoostingClassifier(max_iter=100, learning_rate=0.06, max_depth=3, min_samples_leaf=20, random_state=0)
            prob[chk] = clf.fit(X[~chk], det[~chk]).predict_proba(X[chk])[:, 1]
        aucs.append(roc_auc_score(det, prob))
        prob_mean += prob / len(seeds)
        pred = cv_predictions(X, y, folds, default_model)
        m_model.append(masked_rmse(y[det], pred[det]))
        m_mean.append(masked_rmse(y[det], fold_mean_baseline(y, folds)[det]))
        m_zero.append(masked_rmse(y[det], np.zeros(det.sum())))
    sites, inv = np.unique(groups, return_inverse=True)
    rng = np.random.default_rng(0)
    boot = []
    for _ in range(1000):
        pick = rng.integers(0, len(sites), len(sites))
        rows = np.concatenate([np.where(inv == k)[0] for k in pick])
        if 0 < det[rows].sum() < len(rows):
            boot.append(roc_auc_score(det[rows], prob_mean[rows]))
    return {"detected_share": float(det.mean()), "detected_samples": int(det.sum()), "detection_auc_grouped": float(np.mean(aucs)),
            "detection_auc_lo": float(np.percentile(boot, 2.5)), "detection_auc_hi": float(np.percentile(boot, 97.5)),
            "detected_rmse_model": float(np.mean(m_model)), "detected_rmse_fold_mean": float(np.mean(m_mean)), "detected_rmse_zero": float(np.mean(m_zero))}


def per_facility_table(ds, seed=0, n_folds=5):
    """Grouped-split RMSE of the model and of predicting zero at every facility, for every target.

    Returns a DataFrame with one row per facility and target: ``site_id``, ``target``, ``model``, ``zero``, ``n``.
    """
    import pandas as pd
    from .validation import default_model

    samples = ds.samples.set_index("sample_id").loc[ds.samples.sample_id]
    X = ds.features.set_index("sample_id").loc[ds.samples.sample_id].to_numpy("float32")
    groups = ds.samples.site_id.to_numpy()
    folds = grouped_folds(groups, n_folds, seed)
    rows = []
    for t in TARGETS:
        y = samples[t].to_numpy("float64")
        for site, (model, zero, n) in per_facility_rmse(y, cv_predictions(X, y, folds, default_model), groups).items():
            rows.append({"site_id": site, "target": t, "model": model, "zero": zero, "n": n})
    return pd.DataFrame(rows)


def readable(table):
    """The ``robustness`` result as a DataFrame with the target names as rows."""
    import pandas as pd

    df = pd.DataFrame({t: {k: v for k, v in d.items() if k != "grouped_fold_scores"} for t, d in table.items()}).T
    df.index = [NAMES[t] for t in df.index]
    return df
