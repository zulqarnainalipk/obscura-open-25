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
WORD_LIMIT = 1215          # the compiled PDF counts about 200 more words (headers, footers), so 1,215 here is about 1,500 there (checked against the compiled PDF)
print(f"words {w_total} (limit {WORD_LIMIT} here, 1500 in the PDF count) | figures {n_fig} (limit 1) | references {n_ref} (limit 12)")

problems = []
if w_total > WORD_LIMIT:
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


R = RES["robustness"]
f2 = lambda x: f"{x:.2f}"
need("samples", f"{N['samples']} samples")
need("windows attempted", f"{N['windows_attempted']} in all)")
need("windows per site", f"({N['windows_per_site']} per facility")
need("windows cloudy", f"({N['windows_cloudy']})")
need("windows no scene", f"no scene ({N['windows_no_scene']})")
need("windows failed", f"({N['windows_other_failed']})")
need("windows not used", f"The other {N['windows_attempted'] - N['samples']} windows")
need("share", f"({N['share_samples_percent']}\\%)")
need("pair days", "from one day before to one day after" if N["pair_days_max"] == 1 else "pair days differ")
need("methane share", f"Methane is present in {N['methane_present_percent']}\\% of samples")
need("other gases share", f"the other gases in {N['no2_present_percent']}\\%")
need("fire zero share", f"({N['fire_zero_percent']}\\% of samples)")
need("negative methane", f"({N['ch4_negative_percent']}\\% of methane values are negative)")
need("pixel range", f"{N['pixel_m_min']} to {N['pixel_m_max']} m")
need("box range", f"{N['box_km_min']} to {N['box_km_max']} km")
need("facilities", f"{N['facilities']} industrial facilities")
need("facility count in text", f"The {N['facilities']} facilities (Figure")
need("countries", f"{N['countries']} countries")
need("features", f"The {N['n_features']} features")
need("files", f"{N['files_in_record']} files ({N['record_gb']} GB)")
need("chip archives", f"{N['chip_archives']} chip archives")
need("numeric ids", "four identifiers" if N["numeric_looking_ids"] == 4 else f"{N['numeric_looking_ids']} identifiers")
need("chips", f"the {N['samples']} samples and {N['samples']} chips correspond one to one")
need("georef median", f"median {N['georef_median_m']} m")
need("georef max", f"largest {N['georef_max_m']} m")
if N["chips_facility_inside"] != N["samples"]:
    problems.append("facility centre not inside every chip, but the note says it is")
need("consistency checks", ("Fourteen" if N["consistency_checks_total"] == 14 else str(N["consistency_checks_total"])) + " consistency checks passed")
if N["consistency_checks_passed"] != N["consistency_checks_total"]:
    problems.append("not all consistency checks passed, but the note says they did")
need("re-run", "Fifteen samples at 15 facilities" if N["rerun_total"] == 15 else str(N["rerun_total"]))
if N["rerun_identical"] != N["rerun_total"]:
    problems.append("re-run was not identical, but the note says it was")
need("re-run in abstract", f"reproduced {N['rerun_identical']} of {N['rerun_total']} sampled windows")
need("fold spread", f"at most {N['max_fold_spread']:.3f}")

names = {"t_ch4": "Methane", "t_no2": "Nitrogen dioxide", "t_co": "Carbon monoxide", "t_aai": "Aerosol index", "t_firms": "Fire"}
pcts = []
for t, name in names.items():
    r, b = CASE[t], R[t]
    pct = round(100 * (1 - r["random"] / r["grouped"]))
    pcts.append(pct)
need("range in abstract", f"{min(pcts)}\\% to {max(pcts)}\\%")
a, nn, f_, m_, c_ = (R[k] for k in ("t_aai", "t_no2", "t_firms", "t_ch4", "t_co"))
need("fire random vs zero", f"({f2(CASE['t_firms']['random'])} against {f2(CASE['t_firms']['zero'])}), the grouped split does not ({f2(CASE['t_firms']['grouped'])})")
need("static-only methane", f"for methane ({f2(CASE['t_ch4']['random'])} against {f2(m_['random_static_only'])})" if False else f"matches the full model for methane ({f2(m_['random_static_only'])} against {f2(CASE['t_ch4']['random'])})")
need("static-only fire", f"fire ({f2(f_['random_static_only'])} against {f2(CASE['t_firms']['random'])})")
need("facility mean", f"({f2(m_['random_facility_mean'])}, {f2(c_['random_facility_mean'])}, {f2(f_['random_facility_mean'])})")
if not (m_["random_facility_mean"] <= CASE["t_ch4"]["random"] and c_["random_facility_mean"] <= CASE["t_co"]["random"] + 0.01 and f_["random_facility_mean"] <= CASE["t_firms"]["random"]):
    problems.append("facility-mean predictor is not as good as the full model, but the note says it is")
if not (a["grouped_train_mean"] - CASE["t_aai"]["grouped"] > 0.3 and abs(m_["grouped_train_mean"] - CASE["t_ch4"]["grouped"]) < 0.01):
    problems.append("grouped comparison statements no longer hold")

B = RES["bootstrap"]
for t, name in names.items():
    r, b, bt = CASE[t], R[t], B[t]
    pct = round(100 * (1 - r["random"] / r["grouped"]))
    lo, hi = round(100 * bt["understated_lo"]), round(100 * bt["understated_hi"])
    need(f"table row {name}", f"{name} & {f2(r['random'])} & {f2(r['grouped'])} & {f2(r['zero'])} & {f2(b['grouped_train_mean'])} & {pct} ({lo} to {hi})")
need("aerosol interval vs fold mean", f"$-{abs(B['t_aai']['grouped_minus_foldmean_lo']):.2f}$ to $-{abs(B['t_aai']['grouped_minus_foldmean_hi']):.2f}$")
need("fire detection auc", f"(AUC {N['fire_detection_auc_grouped']:.2f}, interval {N['fire_detection_auc_lo']:.2f} to {N['fire_detection_auc_hi']:.2f})")
if N["fire_detection_auc_lo"] > 0.5 or N["fire_detection_auc_hi"] < 0.5:
    problems.append("the detection AUC interval excludes 0.5, but the note says no better than chance")
for t in ("t_ch4", "t_no2", "t_co", "t_firms"):
    if B[t]["grouped_minus_foldmean_lo"] > 0 or B[t]["grouped_minus_foldmean_hi"] < 0:
        problems.append(f"the interval for {t} excludes zero, but the note says only the aerosol index does")
if not B["t_aai"]["grouped_minus_foldmean_hi"] < 0:
    problems.append("the aerosol index interval no longer excludes zero")
need("facility combinations", f"taking only {N['static_distinct_combinations']} distinct combinations over {N['facilities']} facilities")
need("static grouped", f"under a grouped split it is no better than the baselines ({f2(m_['grouped_static_only'])} for both)")
if f2(m_["grouped_static_only"]) != f2(f_["grouped_static_only"]):
    problems.append("static-only grouped values for methane and fire differ")
if not N["static_constant_within_facility"]:
    problems.append("elevation and slope are not constant within a facility, but the note says they are")
low = TEX.lower()
for word in ("competition", "kaggle", "tool paper", "curator", "larger collection", "remaining facilities", "other facilities of the", "81 ", "held back", "after it ends"):
    if word in low:
        problems.append(f"the note must not mention: {word}")
print("PROBLEMS:" if problems else "All checks passed: limits met, and every number in the note matches the code's results.")
for p in problems:
    print(" -", p)
sys.exit(1 if problems else 0)
