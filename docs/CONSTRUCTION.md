# How a sample is built

A longer version of the data description in the note. The record's `METHODS.md` and `DATA_DICTIONARY.md` are the primary documents; this page adds the rules in one place. Values were taken from the collection pipeline settings (released after the OBSCURA competition ends).

## From a window to a sample

1. Time is cut into 5-day windows. Every second window from 2022-01-01 to 2023-12-27 is attempted at each facility: 73 windows per facility, 1,825 in all.
2. Sentinel-2 L2A scenes (Earth Engine `COPERNICUS/S2_SR_HARMONIZED`) over the image box are scored for cloud (the s2cloudless probability at 40% or more counts as cloud) and the scene date with the least cloud over the box is chosen. All tiles of that date are mosaicked.
3. The window is rejected if the box has more than 30% cloud (`cloudy`, 441), if there is no scene (`no_s2`, 11), if less than 95% of the box is covered (`low_valid`, 5), or if the mosaic is cloudier than the limit (`cloudy_mosaic`, 6) or the exported chip is empty (`chip_nodata`, 7). The last three make the 18 "other" windows.
4. Gas products and fire are paired with the scene date: every Sentinel-5P granule or FIRMS detection from one day before to one day after the scene date is used (`pair_days` is 1 in every released sample; the pipeline could widen it to 2 once, which no released sample needed). Granules in this range are averaged per pixel; fire takes the maximum.
5. If no gas target can be measured, the window is rejected. Otherwise a sample is written: 1,355 of 1,825 (74%).

## Targets

All gas products are the Earth Engine Level-3 offline (OFFL) Sentinel-5P collections. Earth Engine converts the Level-2 orbits with HARP to a 0.01 degree grid (1113.2 m pixels) and applies a quality-value filter before we see the data. We add no filter of our own. Quote the Earth Engine page of each collection when you cite a value.

| Target | Collection and band | Stored unit | Quality filter of the collection |
|---|---|---|---|
| methane | `COPERNICUS/S5P/OFFL/L3_CH4`, `CH4_column_volume_mixing_ratio_dry_air_bias_corrected` (the plain `..._dry_air` band if the corrected one is missing for the period) | ppb | Level-2 `qa_value` above 0.5 |
| nitrogen dioxide | `COPERNICUS/S5P/OFFL/L3_NO2`, `tropospheric_NO2_column_number_density` (mol/m2, times 1e6) | micromol/m2 | `qa_value` above 0.75 by the collection's description (its HARP command shows a validity filter of 50) |
| carbon monoxide | `COPERNICUS/S5P/OFFL/L3_CO`, `CO_column_number_density` (mol/m2, times 1e3) | mmol/m2 | `qa_value` above 0.5 |
| aerosol index | `COPERNICUS/S5P/OFFL/L3_AER_AI`, `absorbing_aerosol_index` | unitless | `qa_value` above 0.8 by the collection's description |
| fire | `FIRMS`, band `T21` | kelvin | none beyond the collection |

**Gas enhancement.** For the days from one day before to one day after the Sentinel-2 date, every image of the collection that touches the 75 km ring is taken and the images are averaged per pixel (`mean` of the collection, so granules that overlap in time or space are averaged, not mosaicked by recency). Pixels whose water fraction (MODIS MOD44W, 250 m averaged onto the 1.1 km grid) is 0.2 or more are masked. The value is the mean of the remaining pixels in a fixed 10 km window around the facility centre minus the median of the remaining pixels in the 30 to 75 km ring, with the parts of the ring near other facilities of the collection removed. The numbers of pixels behind both are in `samples.csv` (`*_site_count`, `*_bg_count`). If the collection has no image in the range, the window has no valid pixel, or the ring has none, the value is blank (`no_ch4_pixels`, `no_pixels`, `no_background`); an enhancement outside the plausibility limits is blank (`out_of_range_delta`).

**Aerosol index.** The mean of the unitless UV absorbing aerosol index (354 and 388 nm) over the 10 km window, with no ring and no land mask. Positive values indicate absorbing aerosol such as smoke or dust, negative values indicate non-absorbing particles; values near zero carry no information. A sample has an aerosol value when the window has at least one valid pixel.

**Fire.** The Earth Engine `FIRMS` collection is the near-real-time MODIS (MOD14 and MYD14 collection 6) active fire product of NASA LANCE, which its documentation describes as not of science quality. `T21` is the brightness temperature of the fire pixel in MODIS channel 21 and 22, in kelvin. The stored value `raw_firms` is the highest `T21` of any detection inside the 10 km window within the paired days (images combined by per-pixel maximum, reduced at 1 km), and is **0 when the collection has no detection there**. `firms_px` counts the detection pixels. Consequences:

* A zero means "no detection in this product, window and period". It does not establish that no fire occurred. A flare or fire that was small, short or hidden by cloud, or an overpass that missed it, also gives zero, and the data cannot say how many such cases there are. About 85% of the samples are zero.
* A non-zero value is a brightness temperature of 300 K or more (the product reports only pixels above this) and not a fire radiative power or an emission. The stored variable is a detection brightness temperature, not a fire intensity in a physical sense; `t_firms` is its transformed z-score.
* The z-score is taken after `ln(1 + max(T21 - 300, 0))`, so a detection of 300 K and no detection both map to the same transformed value before standardisation.
* No filter on the product's confidence band is applied: all detections of every confidence level count. Several detections in the window and paired days are reduced by the per-pixel and then window maximum.
* The stored value therefore mixes two things: whether a detection exists (`firms_px > 0`, 14.8% of samples) and, if so, how bright the hottest pixel is. For modelling it is clearer to treat them separately. On the released files, the grouped-split AUC of predicting a detection from the 29 features is 0.41 (95% bootstrap interval over facilities 0.27 to 0.53, so not distinguishable from chance), and on the 200 detected samples the grouped RMSE is 2.33 for the model, 2.25 for the training-fold mean and 2.12 for zero (`obscura_open25.diagnostics.fire_decomposition`).
* Name: the column `raw_firms` is the maximum detected MODIS brightness temperature (K), 0 if none, and the target `t_firms` is its transformed z-score. They are not fire intensity, radiative power or emissions.

Blank reasons in the released samples: methane `no_ch4_pixels` (684), `no_background` (3), `out_of_range_delta` (1); nitrogen dioxide `no_pixels` (15); carbon monoxide `no_pixels` (8). Methane is present in 49% of the samples. That share is the number of samples of a facility with methane divided by the number of samples of that facility (28% to 83% over the 25 facilities); for seasons it is the share within the samples of Dec-Feb, Mar-May, Jun-Aug or Sep-Nov by Sentinel-2 date (40% to 56%); for cloud it is the share within thirds of the chip cloud share (60%, 54% and 33% from the clearest to the cloudiest third; correlation of presence with cloud share -0.19). Denominators are samples, not attempted windows.

## Chips

384 x 384 pixels, 14 layers in this order: B1, B2, B3, B4, B5, B6, B7, B8, B8A, B9, B11, B12 (surface reflectance x 10,000), SCL (scene classification), CLDPRB (cloud probability, 0 to 100). B10 is not part of L2A. Unsigned 16-bit, nodata filled with 0. The native band resolutions (10, 20 and 60 m) are placed on the chip grid by Earth Engine at export. No resampling method is set in the export request, so Earth Engine's default (nearest neighbour) applies; no separate resampling step was applied by the authors. Pixels without data are filled with 0 (`unmask(0)`) and the share of zero pixels is `chip_zero_frac` in `samples.csv`. The box is exported in the local UTM zone. The ground size of a pixel is `box_km * 1000 / 384`.

**Box sizes.** The side (1.5 to 7.75 km) was set per facility so that the facility fits in the chip with some surroundings: a compact plant gets a small box, a large oilfield or mine a larger one. The centre and box were checked by hand against satellite imagery.

**Positions.** Three different quantities should not be mixed up. (1) The chip grid origin is shifted by a random amount below 60 m in each of x and y (60 m is the coarsest Sentinel-2 band grid), so the facility is not always at the centre; the largest possible shift is about 85 m. (2) The measured distance from the chip centre to the facility centre is 48 m median and 84 m at most (`georeference_offsets`); this is the shift of (1) plus the snapping to whole pixels, and the largest value (84 m) is close to the largest possible shift. (3) The positional accuracy of the facility centre itself, and of Sentinel-2, is about 100 m or better (the note states about 100 m as a conservative figure).

## Features

29 columns. Weather from ERA5-Land: 2 m temperature (degrees C), humidity from the dew point (%), 10 m wind speed and direction averaged over the three hours around the local Sentinel-5P overpass (about 13:30), daily precipitation (m) and solar radiation (MJ/m2), taken on the ERA5-Land grid (about 11 km) around the facility. Wind direction is the direction the wind comes from. Elevation (mean) and slope from the Copernicus GLO-30 model, averaged over the image box at 90 m. The cloud share of the chip, the month as sine and cosine, and 18 spectral indices computed on cloud-free pixels (cloud probability below 40 and not a cloud class in SCL) and averaged over the chip:

| Index | Formula (reflectance) |
|---|---|
| ndvi | (B8 - B4) / (B8 + B4) |
| evi | 2.5 (B8 - B4) / (B8 + 6 B4 - 7.5 B2 + 1) |
| savi | 1.5 (B8 - B4) / (B8 + B4 + 0.5) |
| ndre | (B8A - B5) / (B8A + B5) |
| ndwi | (B3 - B8) / (B3 + B8) |
| mndwi | (B3 - B11) / (B3 + B11) |
| awei | 4 (B3 - B11) - (0.25 B8 + 2.75 B12) |
| nmdi | (B8 - (B11 - B12)) / (B8 + (B11 - B12)) |
| nbri | (B8 - B12) / (B8 + B12) |
| nbr2 | (B11 - B12) / (B11 + B12) |
| bsi | ((B11 + B4) - (B8 + B2)) / ((B11 + B4) + (B8 + B2)) |
| bi | sqrt((B4^2 + B3^2 + B2^2) / 3) |
| swir_ratio | B11 / B12 |
| ndii | (B8 - B11) / (B8 + B11) |
| hsfi | B12 / B8 |
| ohi | (B12 - B3) / (B12 + B3) |
| b11_mean, b12_mean | B11 and B12 |

Each index is clamped per pixel to a fixed range before averaging (evi -1 to 3, savi -1.5 to 1.5, awei -2 to 2, nmdi -5 to 5, bi 0 to 1.5, swir_ratio and hsfi 0 to 10, b11 and b12 0 to 1.5, all others -1 to 1) because ratio indices explode where a denominator is near zero. Pixels that are masked as cloud are left out of the average.

## Missing feature values

All 29 features are present for 1,354 of the 1,355 samples. One sample has no cloud-free pixel, so its 18 spectral indices are blank. Models in this repository pass blanks to the gradient-boosting regressor, which handles them natively; nothing is imputed.

## Rebuilding

The values can be rebuilt with the pipeline, Earth Engine access and the same upstream products. The note demonstrates this for 15 samples at 15 facilities (all identical in every field and pixel). It was not run for all 1,355 samples. If an upstream product is reprocessed, rebuilt values can differ; the record's checksums and the stored scene and granule identifiers show what the released values were built from.