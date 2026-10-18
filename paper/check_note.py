"""Check the data note against the invitation limits and against the numbers computed by the code.

    python paper/check_note.py

Run ``python examples/reproduce_note.py DATA_FOLDER`` first. It computes every number from the Zenodo files and
writes results/note_results.json. This script then reads data_note.tex and fails if

* the note has more than 1,500 words (abstract and body, without title, authors and references), more than one
  figure or more than 12 references, or a cited key without a reference,
* a number printed in the note is not the number in results/note_results.json.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = open(os.path.join(HERE, "data_note.tex"), encoding="utf-8").read()
RES = json.load(open(os.path.join(HERE, "..", "results", "note_results.json"), encoding="utf-8"))
N, CASE = RES["numbers"], RES["case_study"]


def words(s):
    s = re.sub(r"%.*", "", s)
    s = re.sub(r"\\begin\{verbatim\}.*?\\end\{verbatim\}", lambda m: " " + m.group(0).split("\n", 1)[1].rsplit("\\end", 1)[0] + " ", s, flags=re.S)
    s = re.sub(r"\\(cite|label|ref|url|includegraphics|begin|end)(\[[^\]]*\])?\{[^}]*\}", " ", s)
    s = re.sub(r"\\[a-zA-Z]+\*?", " ", s)
    s = re.sub(r"[{}$~\\&]|\[labelsep=2mm\]", " ", s)
    return len([w for w in s.split() if re.search(r"[A-Za-z0-9]", w)])


head, rest = TEX.split(r"\begin{document}")
body = rest.split(r"\reftitle")[0]
abstract = re.search(r"\\abstract\{(.*?)\}\n\n\\keyword", head, re.S).group(1)
w_total = words(abstract) + words(body)
n_fig = len(re.findall(r"\\includegraphics", body))
n_ref = len(re.findall(r"\\bibitem", TEX))
cited = {k for g in re.findall(r"\\cite\{([^}]*)\}", body) for k in g.split(",")}
bib = set(re.findall(r"\\bibitem\[[^\]]*\]\{([^}]*)\}", TEX))
print(f"words {w_total} (limit 1500; the compiled PDF counts about 200 more because of headers and line numbers) | figures {n_fig} (limit 1) | references {n_ref} (limit 12)")

problems = []
if w_total > 1500:
    problems.append("word limit")
if n_fig != 1:
    problems.append("figure count")
if n_ref > 12 or cited != bib:
    problems.append(f"references: missing {sorted(cited - bib)}, uncited {sorted(bib - cited)}")
if "\u2014" in TEX:
    problems.append("em dash in the text")


def need(label, text):
    if text not in TEX:
        problems.append(f"not in the note: {label} = {text}")


need("samples", f"{N['samples']} samples")
need("windows attempted", f"({N['windows_attempted']})")
need("windows cloudy", f"{N['windows_cloudy']} windows were too cloudy")
need("windows no scene", f"{N['windows_no_scene']} had no scene")
need("windows failed", f"{N['windows_other_failed']} failed other checks")
need("share", f"({N['share_samples_percent']}\\%)")
need("methane share", f"{N['methane_present_percent']}\\% of samples")
need("other gases share", f"the other gases for {N['no2_present_percent']}\\%")
need("pixel range", f"{N['pixel_m_min']} to {N['pixel_m_max']} m")
need("box range", f"{N['box_km_min']} to {N['box_km_max']} km")
need("facilities", f"{N['facilities']} industrial facilities")
need("countries", f"{N['countries']} countries")
need("regions", "eight world regions" if N["regions"] == 8 else f"{N['regions']} world regions")
need("features", f"The {N['n_features']} features")
need("files", f"{N['files_in_record']} files ({N['record_gb']} GB)")
need("chip archives", f"{N['chip_archives']} chip archives")
need("numeric ids", "four identifiers" if N["numeric_looking_ids"] == 4 else f"{N['numeric_looking_ids']} identifiers")
need("chips", f"{N['samples']} chips exist for {N['samples']} samples")
need("georef median", f"median of {N['georef_median_m']} m")
need("georef max", f"at most {N['georef_max_m']} m")
need("georef inside", "In all chips the facility centre lies inside" if N["chips_facility_inside"] == N["samples"] else "(inside count differs)")
need("consistency checks", ("Fourteen" if N["consistency_checks_total"] == 14 else str(N["consistency_checks_total"])) + " consistency checks")
if N["consistency_checks_passed"] != N["consistency_checks_total"]:
    problems.append("not all consistency checks passed, but the note says they did")
need("re-run", "Fifteen samples at 15 facilities" if N["rerun_total"] == 15 else str(N["rerun_total"]))
if N["rerun_identical"] != N["rerun_total"]:
    problems.append("re-run was not identical, but the note says it was")
need("re-run in abstract", f"reproduced {N['rerun_identical']} of {N['rerun_total']} sampled windows")
need("weather AUC", f"{N['availability_auc_weather']:.2f} from weather")
need("chip AUC", f"{N['availability_auc_chip']:.2f} from chip statistics")
need("all AUC", f"{N['availability_auc_all']:.2f} from all features")
need("fold spread", f"at most {N['max_fold_spread']:.3f}")

names = {"t_ch4": "Methane", "t_no2": "Nitrogen dioxide", "t_co": "Carbon monoxide", "t_aai": "Aerosol index", "t_firms": "Fire"}
pcts = []
for t, name in names.items():
    r = CASE[t]
    pct = round(100 * (1 - r["random"] / r["grouped"]))
    pcts.append(pct)
    need(f"table row {name}", f"{name} & {r['random']:.2f} & {r['grouped']:.2f} & {r['zero']:.2f} & {pct}\\%")
need("range in abstract", f"{min(pcts)}\\% to {max(pcts)}\\%")
f = CASE["t_firms"]
need("fire in abstract", f"({f['random']:.2f} against {f['zero']:.2f})")
need("fire grouped in abstract", f"({f['grouped']:.2f})")

print("PROBLEMS:" if problems else "All checks passed: limits met, and every number in the note matches the code's results.")
for p in problems:
    print(" -", p)
sys.exit(1 if problems else 0)
