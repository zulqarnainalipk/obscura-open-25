# The data note

* `data_note.tex`: the text, in the MDPI LaTeX template (journal not yet chosen, generic option). The template files (`Definitions/mdpi.cls` and others) are not copied here; download them from MDPI and put them in a folder `Definitions/` next to the `.tex` file to compile.
* `fig1.png`: the one figure. Made by `make_figure.py` from the Zenodo files and `results/note_results.json`.
* `check_note.py`: checks the text against the numbers computed by the code and against the limits (at most 1,500 words, one figure, 12 references).
* `assets/ne_110m_land.geojson`: land outline from Natural Earth (public domain), used for the map.

To rebuild everything from the data:

```bash
python examples/reproduce_note.py DATA     # computes every number
python paper/make_figure.py DATA           # redraws Figure 1
python paper/check_note.py                 # the text matches the numbers
```