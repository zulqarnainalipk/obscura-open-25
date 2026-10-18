# Files of the Zenodo record

The record (doi:10.5281/zenodo.23450639) has 40 files, 2.2 GB, under CC BY 4.0. Put them all in one folder and point `Dataset` at it.

| Files | Content | Table or archive key |
|---|---|---|
| `sites.csv` | one row per facility: name, country, region, type, centre, box side, counts | `site_id` |
| `samples.csv` | one row per sample: dates, orbit, raw and z-scored targets, pixel counts behind each value, blank reasons, scene and granule identifiers, chip location and hash | `sample_id`, `site_id` |
| `features.csv` | the 29 features, rounded | `sample_id` |
| `features_full_precision.csv` | the same features without rounding (month given as 1 to 12) | `sample_id` |
| `windows.csv` | one row per attempted window (1,825) with its outcome, so missing samples can be studied | `site_id`, `window_start`, `sample_id` |
| `scaling.json` | mean, standard deviation and transform per target for the z-scores | target name |
| `chips_<site_id>.zip` (25) | the chips of one facility, one 14-layer GeoTIFF per sample, stored without compression | `chip_archive`, `chip_file` in `samples.csv` |
| `README.md`, `DATA_DICTIONARY.md`, `METHODS.md`, `NOTICE.md`, `LICENSE.md`, `CITATION.cff` | documentation, notices of the source data, licence, citation | |
| `QC_REPORT.md`, `qc_coverage.png` | what was checked before release, and the coverage figure | |
| `SHA256SUMS.txt` | SHA-256 of every file | |

How the tables relate: `windows.csv` lists every attempt; the windows with status `ok` are the rows of `samples.csv` (joined on `sample_id`); each sample belongs to one site (`site_id`) and has one row in `features.csv` and one chip file. Empty cells mean missing. Read `sample_id` as text.