"""Figure 1 of the data note: the 25 sites on a world map, one chip, and the random-versus-grouped comparison.

    python paper/make_figure.py DATA_FOLDER

Needs the Zenodo files and results/note_results.json (made by examples/reproduce_note.py). The land outline is
Natural Earth (public domain). Writes paper/fig1.png.
"""
import json
import os
import sys
import zipfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from matplotlib.patches import Polygon as MplPolygon

HERE = os.path.dirname(os.path.abspath(__file__))
REC = sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__)
LAND = os.path.join(HERE, "assets", "ne_110m_land.geojson")
SAMPLE = "39719ba02892f650"          # a refinery with all five targets measured, almost no cloud

sites = pd.read_csv(os.path.join(REC, "sites.csv"))
samples = pd.read_csv(os.path.join(REC, "samples.csv"), dtype={"sample_id": str})
GROUPS = {"refinery": "Refinery", "refinery_cluster": "Refinery", "petrochemical": "Chemical", "chemical": "Chemical",
          "power_chemical": "Chemical", "gas_chemical": "Chemical", "lng": "Gas, LNG, oilfield", "gas_plant": "Gas, LNG, oilfield",
          "gas_processing": "Gas, LNG, oilfield", "oilfield": "Gas, LNG, oilfield", "oil_processing": "Gas, LNG, oilfield"}
sites["group"] = sites.facility_type.map(lambda t: GROUPS.get(t, "Power, mining, metals"))
COLORS = {"Refinery": "#1F4E79", "Chemical": "#C0504D", "Gas, LNG, oilfield": "#E08A1E", "Power, mining, metals": "#4F8F5B"}
print("facility types:", sorted(sites.facility_type.unique()))
print("groups:", sites.group.value_counts().to_dict())

# chip and targets of the example sample
row = samples[samples.sample_id == SAMPLE].iloc[0]
with zipfile.ZipFile(os.path.join(REC, row.chip_archive)) as z, rasterio.MemoryFile(z.read(row.chip_file)) as mem, mem.open() as ds:
    chip = ds.read().astype("float32")


def stretch(img):
    out = np.zeros_like(img)
    for k in range(3):
        lo, hi = np.percentile(img[..., k], [2, 98])
        out[..., k] = np.clip((img[..., k] - lo) / max(hi - lo, 1e-6), 0, 1)
    return out


rgb = stretch(np.stack([chip[3], chip[2], chip[1]], -1))        # B4, B3, B2
swir = stretch(np.stack([chip[11], chip[10], chip[3]], -1))     # B12, B11, B4
site_name = sites.set_index("site_id").loc[row.site_id, "site_name"]

plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False, "font.family": "DejaVu Sans"})
fig = plt.figure(figsize=(6.6, 6.7))
gs = fig.add_gridspec(2, 3, height_ratios=[1.12, 1.0], width_ratios=[1.0, 1.0, 1.45], hspace=0.32, wspace=0.34, left=0.095, right=0.985, top=0.97, bottom=0.085)

# (a) map
ax = fig.add_subplot(gs[0, :])
ax.set_facecolor("#EAF1F8")
land = json.load(open(LAND, encoding="utf-8"))
for feat in land["features"]:
    g = feat["geometry"]
    polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    for poly in polys:
        ax.add_patch(MplPolygon(np.array(poly[0]), closed=True, facecolor="#F6F4EE", edgecolor="#B9B5A8", linewidth=0.4, zorder=1))
for grp, col in COLORS.items():
    d = sites[sites.group == grp]
    ax.scatter(d.longitude, d.latitude, s=22 + d.n_samples * 0.9, color=col, edgecolor="white", linewidth=0.7, alpha=0.95, zorder=3, label=f"{grp} ({len(d)})")
ax.set_xlim(-125, 150); ax.set_ylim(-45, 62)
ax.set_xlabel("Longitude (degrees)"); ax.set_ylabel("Latitude (degrees)")
ax.legend(loc="lower left", bbox_to_anchor=(0.40, 0.0), fontsize=7, frameon=True, framealpha=0.95, title="Facility group (sites)", title_fontsize=7)
ax.text(0.005, 1.0, "(a)", transform=ax.transAxes, fontweight="bold", va="bottom", fontsize=9)
ax.text(0.99, 0.03, "Marker size: number of samples", transform=ax.transAxes, ha="right", fontsize=7, color="#555")

# (b), (c) chip views
for k, (img, title, tag) in enumerate(((rgb, "True colour", "(b)"), (swir, "Short-wave infrared", "(c)"))):
    a = fig.add_subplot(gs[1, k])
    a.imshow(img); a.axis("off"); a.set_title(title, fontsize=8, pad=2)
    a.text(-0.02, 1.16, tag, transform=a.transAxes, fontweight="bold", fontsize=9)

# (d) case study: random split against facility-grouped split
res = json.load(open(os.path.join(HERE, "..", "results", "note_results.json"), encoding="utf-8"))["case_study"]
a = fig.add_subplot(gs[1, 2])
a.text(0.0, 1.07, "(d)", transform=a.transAxes, fontweight="bold", fontsize=9)
tg = ["t_ch4", "t_no2", "t_co", "t_aai", "t_firms"]
x = np.arange(5); w = 0.27
a.bar(x - w, [res[t]["random"] for t in tg], w, color="#9AA5B1", label="Random split")
a.bar(x, [res[t]["grouped"] for t in tg], w, color="#1F4E79", yerr=[res[t]["grouped_sd"] for t in tg], capsize=1.5, error_kw={"linewidth": 0.6}, label="Facility-grouped split")
a.bar(x + w, [res[t]["zero"] for t in tg], w, color="#E08A1E", label="Predict zero")
a.set_xticks(x); a.set_xticklabels(["CH$_4$", "NO$_2$", "CO", "Aerosol\nindex", "Fire"], fontsize=6.5)
a.tick_params(axis="y", labelsize=6.5); a.set_ylabel("RMSE (z-score units)", fontsize=7)
a.set_ylim(0, 1.5); a.legend(fontsize=6, loc="upper left", frameon=False)
fig.savefig(os.path.join(HERE, "fig1.png"), dpi=300)
print("sample:", site_name, row.s2_date, "box", row.box_km, "| cloud", round(row.s2_cloud_frac, 3))
print("wrote fig1.png")
