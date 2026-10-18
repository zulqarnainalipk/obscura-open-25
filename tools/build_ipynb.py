"""Turn notebooks/quick_start.py (cells separated by '# %%') into notebooks/quick_start.ipynb.

    python tools/build_ipynb.py

Plain json, no extra packages. Markdown cells are the '# %% [markdown]' blocks with the leading '# ' removed.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "..", "notebooks", "quick_start.py")
TARGET = os.path.join(HERE, "..", "notebooks", "quick_start.ipynb")


def split_cells(text):
    """List of (kind, lines) in file order."""
    cells, kind, lines = [], None, []
    for line in text.splitlines():
        if line.startswith("# %%"):
            if kind is not None:
                cells.append((kind, lines))
            kind, lines = ("markdown" if "[markdown]" in line else "code"), []
        elif kind is not None:
            lines.append(line)
    if kind is not None:
        cells.append((kind, lines))
    return cells


def to_cell(kind, lines):
    """One notebook cell; blank edges are trimmed."""
    while lines and not lines[0].strip():
        lines = lines[1:]
    while lines and not lines[-1].strip():
        lines = lines[:-1]
    if kind == "markdown":
        lines = [ln[2:] if ln.startswith("# ") else ln.lstrip("#") for ln in lines]
    source = [ln + "\n" for ln in lines[:-1]] + ([lines[-1]] if lines else [])
    cell = {"cell_type": kind, "metadata": {}, "source": source}
    if kind == "code":
        cell.update({"execution_count": None, "outputs": []})
    return cell


with open(SOURCE, encoding="utf-8") as f:
    cells = split_cells(f.read())
notebook = {"cells": [to_cell(k, l) for k, l in cells],
            "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                         "language_info": {"name": "python"}},
            "nbformat": 4, "nbformat_minor": 5}
with open(TARGET, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1)
print(f"{len(notebook['cells'])} cells -> {os.path.normpath(TARGET)}")
