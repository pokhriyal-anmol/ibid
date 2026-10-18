"""Write the assoc-nb v3 decision report (markdown to stdout). Run from the repo root:

  uv run python .scratch/slice-9/v3-report.py [root] > .scratch/slice-9/v3-report.md

root defaults to "."; it holds results/ and data/assoc-nb-v3.json (the refitted model).
Every figure is read from a results file or the model header. Stdlib only."""
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
load = lambda p: json.loads((root / p).read_text())
pct = lambda x: round(100 * x, 1)
recall = lambda p: pct(load(p)["output"]["recall"])

model_path = root / "data/assoc-nb-v3.json"
model = json.loads(model_path.read_text())["header"]
for s in ("v1", "v2"):  # the model must be the one that made the scored results
    got = load(f"results/multicharge-{s}-assoc-v3-ipc.json")["inputs"]["layer"]["model"]
    assert hashlib.sha256(model_path.read_bytes()).hexdigest() == got, f"{model_path} is not the model behind set {s}"

rows = []  # label, reference, threshold text, v3 figure, passes
for s, name in (("v1", "judgment text"), ("v2", "forum posts")):
    for act in ("ipc", "bns"):
        ref = recall(f"results/multicharge-{s}-assoc-v2-{act}.json")
        v3 = recall(f"results/multicharge-{s}-assoc-v3-{act}.json")
        if s == "v1":
            rows.append((f"Set {s} ({name}), {act.upper()} recall", f"v2 {ref}", f"above {ref}", v3, v3 > ref))
        else:
            floor = round(ref - 5, 1)
            rows.append((f"Set {s} ({name}), {act.upper()} recall", f"v2 {ref}", f"at least {floor}", v3, v3 >= floor))
v1_f1 = pct(load("results/layers/assoc-nb-v1-test.json")["scores"]["micro_f1"])
floor = round(v1_f1 - 2, 1)
t = load("results/layers/assoc-nb-v3-test.json")  # score the ILSI test split first (ibid assoc eval); a missing file is an error, not a verdict
v3_f1 = pct(t["scores"]["micro_f1"])
rows.append(("ILSI test micro-F1", f"v1 {v1_f1}", f"at least {floor}", v3_f1, v3_f1 >= floor))

print("# assoc-nb v3 against the ADR 0008 decision rule\n")
print("| # | Comparison | Reference | v3 must be | v3 | Result |\n|---|---|---|---|---|---|")
for n, (label, ref, need, v3, ok) in enumerate(rows, 1):
    print(f"| {n} | {label} | {ref} | {need} | {v3} | {'pass' if ok else 'fail'} |")
v1_space = t.get("micro_f1_by_label_space", {}).get("v1")
waived = rows[-1][-1] and v1_space is not None and pct(v1_space["micro_f1"]) < floor
if all(ok for *_, ok in rows) and waived:
    print(f"\nVerdict: **kept as opt-in, by owner waiver (D-005)**. All five comparisons hold in v3's own label space, but over v1's 100-label space the ILSI micro-F1 is {pct(v1_space['micro_f1'])}, {round(floor - pct(v1_space['micro_f1']), 1)} below the {floor} floor. The owner (Q-005, 2026-10-18) chose to report both and keep v3 as opt-in on the strength of its wins on both multi-charge sets. The pre-registered floor is not claimed as passed under the like-for-like reading.")
elif all(ok for *_, ok in rows):
    print("\nVerdict: **kept**. All five comparisons hold, so v3 stays an opt-in layer.")
else:
    print("\nVerdict: **negative**. Not every comparison holds, so v1 and v2 remain the two options.")
print("\nADR 0008 names five comparisons (the spec's \"six\" counts to five). Recall is in percent, per set and Act, never pooled.")

used = {k: v["examples_used"] for k, v in model["sources"].items()}
total = sum(used.values())
print(f"\nVocabulary: {model['vocabulary_size']} IPC sections (at least {model['min_examples']} training examples).")
print("Training examples fitted: " + ", ".join(f"{k} {n} ({100 * n / total:.1f}%)" for k, n in used.items()) + f", {total} in all.")
if "micro_f1_by_label_space" in t:
    print("\nILSI test micro-F1 by label space (one test run):")
    for k, v in t["micro_f1_by_label_space"].items():
        print(f"- {k} space, {v['labels']} labels: {pct(v['micro_f1'])}")
    print(f"- reference v1 (its own space): {v1_f1}")
print("\nThese are benchmark figures on labels that are incomplete for forum posts. No lawyer reviewed any label; nothing here is a claim of legal accuracy.")
