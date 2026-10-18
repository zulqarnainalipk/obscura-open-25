"""Highlight, in the reference papers, the passages that the data note cites them for.

    python references/highlight_references.py

Reads references/citations.json. For every key that has a PDF at references/pdfs/<key>.pdf, each phrase in its
``highlight_phrases`` list is searched in the paper and highlighted in yellow; the result is written to
references/highlighted/<key>.pdf. A phrase that is not found is reported, never skipped silently.
Needs PyMuPDF: pip install pymupdf
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    import pymupdf

    cites = json.load(open(os.path.join(HERE, "citations.json"), encoding="utf-8"))
    os.makedirs(os.path.join(HERE, "highlighted"), exist_ok=True)
    missing = 0
    for key, info in cites.items():
        src = os.path.join(HERE, "pdfs", key + ".pdf")
        if not os.path.exists(src):
            print(f"{key:14s} no PDF at references/pdfs/{key}.pdf")
            continue
        doc = pymupdf.open(src)
        found = 0
        for phrase in info["highlight_phrases"]:
            hits = [(page, page.search_for(phrase)) for page in doc]
            hits = [(p, r) for p, r in hits if r]
            if not hits:
                print(f"{key:14s} NOT FOUND: {phrase[:70]}")
                missing += 1
            for page, rects in hits:
                page.add_highlight_annot(rects).update()
                found += len(rects)
        doc.save(os.path.join(HERE, "highlighted", key + ".pdf"))
        print(f"{key:14s} {found} highlights for {len(info['highlight_phrases'])} phrases")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())