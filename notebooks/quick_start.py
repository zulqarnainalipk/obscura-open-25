# %% [markdown]
# # OBSCURA-Open-25: quick start
#
# This notebook shows how to read the dataset, look at its tables and images, and run a small first model.
# It uses the `obscura_open25` package from this repository.
#
# **Get the data first.** Download the files of the Zenodo record into one folder and set `OBSCURA_OPEN25_DIR` to it
# (or put them in a folder called `data` next to this notebook). The record is at https://doi.org/[ZENODO DOI].
#
# **What is in the data.** 1,355 samples from 25 industrial facilities. Each sample is one facility over one
# 5-day window: a 14-layer Sentinel-2 chip, 29 weather, terrain and spectral features, and five satellite-derived
# targets (methane, NO2 and CO enhancements, an aerosol index, and fire intensity). A blank target means the
# satellite could not measure it. A blank is not a zero.

# %%
import os
import warnings

import matplotlib
import numpy as np
import pandas as pd

if "get_ipython" not in globals():          # plain python: no pop-up windows
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

from obscura_open25 import (Dataset, NAMES, TARGETS, UNITS, SCL_NAMES, masked_rmse, scene_class, swir_composite,
                            true_colour, valid_mask, verify_folder)

warnings.filterwarnings("ignore")
plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False, "font.size": 9})
MAIN, GREY = "#1F4E79", "#9AA5B1"

# %% [markdown]
# ## Load and check
#
# `Dataset` reads the tables and opens chips from the zip files on demand. `verify_folder` checks your download
# against the published checksums. Checking a sample of chips is quick; leave `chip_sample` out to check all of them.

# %%
DATA_DIR = os.environ.get("OBSCURA_OPEN25_DIR", "data")
problems = verify_folder(DATA_DIR, chip_sample=20)
print("download matches the published checksums" if not problems else problems)
ds = Dataset(DATA_DIR)
print(ds)

# %% [markdown]
# ## The sites
#
# One row per facility, with its verified centre and the size of its image box.

# %%
ds.sites[["site_name", "country", "region", "facility_type", "latitude", "longitude", "box_km", "n_samples"]].head(10)

# %%
def plot_sites(sites):
    """Sites on a longitude and latitude grid, sized by number of samples."""
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.set_facecolor("#F3F6FA")
    for t, c in zip(sorted(sites.facility_type.unique()), plt.cm.tab20.colors):
        d = sites[sites.facility_type == t]
        ax.scatter(d.longitude, d.latitude, s=d.n_samples * 2.2, color=c, edgecolor="white", label=t, zorder=3)
    ax.grid(color="white", lw=1)
    ax.set_xlabel("longitude"); ax.set_ylabel("latitude"); ax.set_xlim(-130, 150); ax.set_ylim(-45, 62)
    ax.legend(fontsize=7, ncol=2, loc="lower left", frameon=True)
    ax.set_title("The 25 sites (marker size = number of samples). No coastlines drawn.", loc="left", fontweight="bold")
    plt.tight_layout(); plt.show()


plot_sites(ds.sites)

# %% [markdown]
# ## Every attempted window
#
# The dataset keeps a record of all the windows that were tried, including the ones that gave no sample. This is
# useful for studying why data are missing.

# %%
ds.windows.status.value_counts().to_frame("windows")

# %% [markdown]
# ## The five targets
#
# `t_*` columns are z-scores and match the competition files. `raw_*` columns hold physical values. The table shows
# how often each target is measured and its spread in physical units.

# %%
def target_summary(samples):
    """How often each target is measured, and its spread in physical units."""
    from obscura_open25 import RAW_COLUMNS
    rows = []
    for t in TARGETS:
        raw = samples[RAW_COLUMNS[t]]
        rows.append({"target": NAMES[t], "unit": UNITS[t], "measured": f"{100 * samples[t].notna().mean():.0f}%",
                     "median": round(raw.median(), 2), "p5": round(raw.quantile(.05), 2), "p95": round(raw.quantile(.95), 2)})
    return pd.DataFrame(rows).set_index("target")


target_summary(ds.samples)

# %%
def plot_target_distributions(samples):
    """Histograms of the z-scored targets, extremes clipped."""
    fig, axes = plt.subplots(1, 5, figsize=(13, 2.5))
    for ax, t in zip(axes, TARGETS):
        v = samples[t].dropna()
        lo, hi = np.percentile(v, [0.5, 99.5])
        ax.hist(v.clip(lo, hi), bins=35, color=MAIN)
        ax.set_title(NAMES[t]); ax.set_yticks([]); ax.set_xlabel("z-score")
    plt.tight_layout(); plt.show()


plot_target_distributions(ds.samples)

# %% [markdown]
# ## One site over time
#
# Samples are about ten days apart. Here are NO2 and the aerosol index at the best-covered site.

# %%
def plot_site_series(ds, site_id):
    """NO2 and aerosol index over time at one site."""
    d = ds.samples_of(site_id).sort_values("s2_date")
    when = pd.to_datetime(d.s2_date)
    fig, axes = plt.subplots(2, 1, figsize=(9, 4.2), sharex=True)
    axes[0].plot(when, d.raw_no2, "o-", color=MAIN, ms=3); axes[0].set_ylabel("NO2 enhancement\n(micromol/m2)")
    axes[1].plot(when, d.raw_aai, "o-", color="#E08A1E", ms=3); axes[1].set_ylabel("aerosol index")
    name = ds.sites.set_index("site_id").loc[site_id, "site_name"]
    axes[0].set_title(name, loc="left", fontweight="bold")
    plt.tight_layout(); plt.show()


plot_site_series(ds, ds.sites.sort_values("n_samples").site_id.iloc[-1])

# %% [markdown]
# ## An image chip
#
# A chip has 14 layers. Two useful views: true colour (B4, B3, B2) and short-wave infrared (B12, B11, B4), where hot
# and bare surfaces glow orange. The scene classification layer says what each pixel is, including cloud.

# %%
def show_sample(ds, sample_id):
    """True colour, short-wave infrared and scene classes of one chip."""
    chip = ds.read_chip(sample_id)
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.4))
    axes[0].imshow(true_colour(chip)); axes[0].set_title("true colour")
    axes[1].imshow(swir_composite(chip)); axes[1].set_title("short-wave infrared")
    scl = scene_class(chip)
    axes[2].imshow(scl, cmap="tab20", vmin=0, vmax=19); axes[2].set_title("scene classes")
    present = ", ".join(SCL_NAMES[c] for c in np.unique(scl) if c in SCL_NAMES)
    fig.suptitle(f"{sample_id}   (classes present: {present})", fontsize=8)
    for a in axes:
        a.axis("off")
    plt.tight_layout(); plt.show()
    return chip


row = ds.samples.sort_values("s2_cloud_frac").iloc[len(ds) // 2]
chip = show_sample(ds, row.sample_id)
print("chip shape:", chip.shape, "| cloud-free share:", round(float(valid_mask(chip).mean()), 2))

# %% [markdown]
# ## A first model
#
# A small model on the 29 tabular features, checked the honest way: every site is either in the fitting part or in the
# checking part, never both. `masked_rmse` ignores blank targets. Predicting zero scores about 1.0 because the targets are
# z-scores, so anything lower means the model learned something that carries over to new sites.
#
# This is only a demonstration. With 25 sites the numbers are noisy.

# %%
def grouped_cv(ds, target, n_folds=5):
    """Out-of-fold RMSE of a small gradient-boosted model, with sites kept apart."""
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.model_selection import GroupKFold

    data = ds.merged()
    cols = [c for c in ds.features.columns if c != "sample_id" and c in data.columns]
    X, y, groups = data[cols].to_numpy("float32"), data[target], data.site_id.to_numpy()
    pred = np.full(len(data), np.nan)
    for fit, check in GroupKFold(n_folds).split(X, groups=groups):
        keep = y.iloc[fit].notna().to_numpy()
        model = HistGradientBoostingRegressor(max_iter=100, learning_rate=0.06, max_depth=3, min_samples_leaf=20, random_state=0)
        pred[check] = model.fit(X[fit][keep], y.iloc[fit][keep]).predict(X[check])
    return masked_rmse(y, pred), masked_rmse(y, np.zeros(len(y)))


rows = {NAMES[t]: dict(zip(["model", "predict zero"], grouped_cv(ds, t))) for t in TARGETS}
pd.DataFrame(rows).T.round(3)

# %% [markdown]
# ## Where to go next
#
# * Read the chips for all samples of a site with `ds.iter_chips(site_id)`.
# * Convert z-scores to physical values with `to_physical` and `fire_kelvin`.
# * Join everything into one table with `ds.merged(precise=True)`, which uses the unrounded features.
# * The full description of every column is in `DATA_DICTIONARY.md` in the Zenodo record, and the methods are in `METHODS.md`.
# * Cite the dataset and, if you use the code, this repository (see `CITATION.cff`).
