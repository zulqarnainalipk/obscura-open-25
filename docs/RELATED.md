# Related resources

How OBSCURA-Open-25 compares with the closest open resources cited in the data note. The entries come from the abstracts and pages of the cited works. A cell says "not checked" where the source was not read for that point; do not read it as "absent". Check the entries against the papers before relying on them.

| | METER-ML (arXiv:2207.11166) | CH4Net (Vaughan et al., 2024) | MARS-S2L (arXiv:2511.21777) | Sentinel-2 and Sentinel-5P NO2 (Scheibenreif et al., 2022) | OBSCURA-Open-25 |
|---|---|---|---|---|---|
| Imagery | NAIP, Sentinel-1, Sentinel-2 | Sentinel-2 | Sentinel-2, Landsat | Sentinel-2 (with Sentinel-5P) | Sentinel-2 L2A, 14 layers |
| Targets | classes of methane-emitting facility types, plus negatives | methane plume masks at known super-emitters | verified methane plumes | ground-level NO2 estimated from Sentinel-5P NO2 | Sentinel-5P methane, NO2, CO enhancements, aerosol index, FIRMS fire detection, with weather, terrain and spectral features |
| Unit of analysis | image set at a facility location | image tile | image tile | not checked | image chip of one facility in one 5-day window |
| Coverage | United States | not checked | global | global | 25 facilities in 15 countries, 2022 to 2023 |
| Records of failed or empty attempts | not checked | not checked | not checked | not checked | yes: every attempted window with its outcome (`windows.csv`) |
| Facility-grouped evaluation support | not checked | not checked | not checked | not checked | yes: `compare_splits`, `grouped_folds` |
| Licence | not checked | not checked | CC BY-NC-SA 4.0 (code LGPL v3) | not checked | CC BY 4.0 (code MIT) |

What the table supports: among the resources above, the combination in the last column (several co-measured gas products, aerosol and fire detection at the facility chip level, a record of every attempted window, and built-in facility-grouped evaluation) is what the note claims. It claims no more than that. The other resources have larger scale or different goals (plume detection, source-type classification), and none of them is an emission-quantification benchmark; neither is this one.

The statement "to our knowledge none offers" in the note rests on a search of the literature and of data repositories on 18 October 2026 that was short and is not exhaustive.