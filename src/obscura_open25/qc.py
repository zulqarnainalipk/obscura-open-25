"""Validation of the OBSCURA-Open-25 record, using nothing but the files of the record.

``run_qc`` checks that every chip sits at its facility, that values and counts are internally consistent, and how
much a random split overstates skill. ``coverage_figure`` draws what happened to every attempted window.

    python -m obscura_open25 qc FOLDER --out qc_output

The limits in ``LIMITS`` are the plausibility limits that were applied when the data were collected (they are
listed in METHODS.md of the record). They are written out here so the check needs nothing besides the record.
"""
import json

import numpy as np
import pandas as pd

LIMITS = {"ch4": (-50.0, 50.0), "no2": (-100.0, 400.0), "co": (-30.0, 40.0), "max_cloud": 0.30, "chip_px": 384,
          "period": ("2022-01-01", "2023-12-27"), "max_centre_offset_m": 150.0, "box_tolerance_km": 0.05}
RAW_COLUMNS = ("raw_ch4", "raw_no2", "raw_co", "raw_aai", "raw_firms")


def consistency_checks(samples, windows, limits=LIMITS):
    """The 14 internal consistency checks, as ``{description: True or False}``.

    ``samples`` and ``windows`` are the tables ``samples.csv`` and ``windows.csv``.
    """
    sm, win = samples, windows
    scene, start, end = pd.to_datetime(sm.s2_date), pd.to_datetime(sm.window_start), pd.to_datetime(sm.window_end)
    gas = ["t_ch4", "t_no2", "t_co", "t_aai"]
    count = {"t_ch4": "ch4_site_count", "t_no2": "no2_site_count", "t_co": "co_site_count", "t_aai": "aai_site_count"}
    checks = {
        "raw_ch4 within the configured limit": sm.raw_ch4.dropna().between(*limits["ch4"]).all(),
        "raw_no2 within the configured limit": sm.raw_no2.dropna().between(*limits["no2"]).all(),
        "raw_co within the configured limit": sm.raw_co.dropna().between(*limits["co"]).all(),
        "raw_aai between -6 and 10": sm.raw_aai.between(-6, 10).all(),
        "raw_firms is 0 or at least 300 K": ((sm.raw_firms == 0) | (sm.raw_firms >= 300)).all(),
        "scene date inside its window": ((scene >= start) & (scene <= end + pd.Timedelta(days=1))).all(),
        "pixel size equals box size / 384": ((sm.gsd_m - sm.box_km * 1000 / limits["chip_px"]).abs() < 0.01).all(),
        "n_gas_observed matches the blanks": (sm[gas].notna().sum(axis=1) == sm.n_gas_observed).all(),
        "every present gas has valid pixels behind it": all(((sm[t].notna()) <= (sm[c] > 0)).all() for t, c in count.items()),
        "every blank target has a reason": ((sm[["t_ch4", "t_no2", "t_co"]].isna().any(axis=1)) <= (sm.null_reasons.fillna("{}") != "{}")).all(),
        "no duplicate site and window": not win.duplicated(["site_id", "window_start"]).any(),
        "sample ids unique": sm.sample_id.is_unique,
        "chip cloud fraction within 0 and the configured limit": sm.s2_cloud_frac.between(0, limits["max_cloud"] + 1e-9).all(),
        "all dates inside the collection period": start.between(*limits["period"]).all(),
    }
    return {k: bool(v) for k, v in checks.items()}


def value_ranges(samples):
    """Smallest and largest raw value of each target."""
    return {c: [float(samples[c].min()), float(samples[c].max())] for c in RAW_COLUMNS}


def georeference_summary(offsets, sites, samples, limits=LIMITS):
    """Summary of ``georeference_offsets`` and the problems it shows."""
    d = offsets.offset_m.to_numpy()
    summary = {"n": int(len(d)), "median_m": float(np.median(d)), "p95_m": float(np.percentile(d, 95)), "max_m": float(d.max()),
               "site_inside_chip": int(offsets.inside.sum())}
    issues = []
    if d.max() > limits["max_centre_offset_m"]:
        issues.append(f"chip centre up to {d.max():.0f} m from the site centre")
    if summary["site_inside_chip"] != len(d):
        issues.append("site centre outside some chips")
    box = samples.set_index("sample_id").box_km.reindex(offsets.sample_id).to_numpy()
    wrong = np.abs(offsets.extent_km.to_numpy() - box) > limits["box_tolerance_km"]
    if wrong.any():
        issues.append(f"{int(wrong.sum())} chips whose extent differs from the box size")
    return summary, issues


def signal_check(ds):
    """Random split against facility-grouped split for the five targets (see ``compare_splits``)."""
    from .targets import TARGETS
    from .validation import compare_splits

    table = compare_splits(ds)
    return {t: {"random": float(table.iloc[i].random), "model": float(table.iloc[i].grouped), "grouped_sd": float(table.iloc[i].grouped_sd),
                "zero": float(table.iloc[i].predict_zero)} for i, t in enumerate(TARGETS)}


def run_qc(ds, signal=True):
    """All checks on a :class:`Dataset`. Returns a dictionary that can be written as JSON.

    Reads the header of every chip (about a minute for the full record). ``signal=False`` skips the model fits.
    """
    from .georef import georeference_offsets

    result = {"issues": []}
    offsets = georeference_offsets(ds)
    result["georef"], issues = georeference_summary(offsets, ds.sites, ds.samples)
    result["issues"] += issues
    result["checks"] = consistency_checks(ds.samples, ds.windows)
    result["issues"] += [f"failed: {k}" for k, v in result["checks"].items() if not v]
    result["ranges"] = value_ranges(ds.samples)
    if signal:
        result["signal"] = signal_check(ds)
    return result


def coverage_figure(ds, path):
    """Four panels: what happened to every window, samples by month, gas availability per site, cloud per chip."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sm, win = ds.samples, ds.windows
    order = list(win.groupby("site_id").size().sort_values().index)
    cats = ["ok", "cloudy", "no_s2", "cloudy_mosaic", "low_valid", "chip_nodata"]
    cols = {"ok": "#1F4E79", "cloudy": "#9AA5B1", "no_s2": "#E08A1E", "cloudy_mosaic": "#C9D3DD", "low_valid": "#C0504D", "chip_nodata": "#7B3F00"}
    fig, ax = plt.subplots(2, 2, figsize=(14, 9.5))
    cnt = win.groupby(["site_id", "status"]).size().unstack(fill_value=0).reindex(index=order, columns=cats, fill_value=0)
    left = np.zeros(len(order))
    for c in cats:
        ax[0, 0].barh(range(len(order)), cnt[c].values, left=left, color=cols[c], label=c)
        left += cnt[c].values
    ax[0, 0].set_yticks(range(len(order)))
    ax[0, 0].set_yticklabels([s[:26] for s in order], fontsize=7)
    ax[0, 0].set_xlabel("attempted windows")
    ax[0, 0].legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=6, frameon=False)
    ax[0, 0].set_title("What happened to every attempted window", loc="left", fontweight="bold")
    m = pd.to_datetime(sm.s2_date).dt.month.value_counts().reindex(range(1, 13)).fillna(0)
    ax[0, 1].bar(m.index, m.values, color="#1F4E79")
    ax[0, 1].set_xticks(range(1, 13))
    ax[0, 1].set_title("Samples by month of the year", loc="left", fontweight="bold")
    ax[0, 1].set_xlabel("month")
    ax[0, 1].set_ylabel("samples")
    avail = sm.groupby("site_id")[["t_ch4", "t_no2", "t_co"]].agg(lambda s: s.notna().mean()).reindex(order)
    im = ax[1, 0].imshow(avail.values, aspect="auto", cmap="YlGnBu", vmin=0, vmax=1)
    ax[1, 0].set_xticks(range(3))
    ax[1, 0].set_xticklabels(["methane", "NO2", "CO"])
    ax[1, 0].set_yticks(range(len(order)))
    ax[1, 0].set_yticklabels([s[:26] for s in order], fontsize=7)
    ax[1, 0].set_title("Share of samples with each gas measured", loc="left", fontweight="bold")
    plt.colorbar(im, ax=ax[1, 0], fraction=0.04)
    ax[1, 1].hist(sm.s2_cloud_frac, bins=30, color="#9AA5B1", label="cloud share of the chip")
    ax[1, 1].hist(1 - sm.s2_valid_frac, bins=30, color="#1F4E79", alpha=0.7, label="share without valid pixels")
    ax[1, 1].set_title("Cloud and invalid pixels per chip", loc="left", fontweight="bold")
    ax[1, 1].legend(fontsize=8)
    ax[1, 1].set_xlabel("share of the chip")
    for a in ax.ravel():
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
    plt.tight_layout()
    plt.savefig(path, dpi=110)
    plt.close(fig)


def write_qc(ds, out_dir, signal=True):
    """Run everything and write ``qc_results.json`` and ``qc_coverage.png`` into ``out_dir``."""
    from pathlib import Path

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    result = run_qc(ds, signal=signal)
    (out / "qc_results.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    coverage_figure(ds, out / "qc_coverage.png")
    return result
