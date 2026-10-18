# References of the data note

The ten works cited in the data note, with the DOI, where in the note each is cited and what it supports. The same list is machine-readable in `citations.json`.

| Key | DOI | Cited in | Supports |
|---|---|---|---|
| veefkind | 10.1016/j.rse.2011.09.027 | Summary; Targets | Sentinel-5P measures methane, NO2, CO and the aerosol index with near-daily global coverage |
| scheibenreif | 10.1109/TGRS.2022.3160827 | Summary | earlier pairing of Sentinel-2 with Sentinel-5P for ground-level NO2 |
| vaughan | 10.5194/amt-17-2583-2024 | Summary | labelled methane plumes at known super-emitters |
| drusch | 10.1016/j.rse.2011.11.026 | Chips | the Sentinel-2 mission and bands |
| giglio | 10.1016/j.rse.2016.02.054 | Targets | thermal anomaly detection behind the FIRMS values |
| gorelick | 10.1016/j.rse.2017.06.031 | Targets | Google Earth Engine, the platform used to read the products |
| carroll | 10.1080/17538940902951401 | Targets | global water mask used for the land-only background ring |
| munoz | 10.5194/essd-13-4349-2021 | Features | ERA5-Land weather variables |
| dem | 10.5270/ESA-c5d3d65 | Features | Copernicus 30 m elevation model (a dataset) |
| roberts | 10.1111/ecog.02881 | Summary | validation must respect spatial and hierarchical structure |

## Putting the papers here

Place each paper as `references/pdfs/<key>.pdf` (for example `pdfs/munoz.pdf`). Then add to `highlight_phrases` in `citations.json` the exact wording of the passage the note relies on, and run

```bash
pip install pymupdf
python references/highlight_references.py
```

Highlighted copies are written to `references/highlighted/`. A phrase that is not found in the PDF is reported.

## Copyright

Most of these papers are published under a journal's copyright, and publishing them in a public repository is not allowed unless the paper is open access under a licence that permits it (for example CC BY). Check the licence on the publisher's page before you commit a PDF. For the others, keep the PDF locally (`references/pdfs/` is where the script looks) and commit only `citations.json` and the highlight phrases.