"""Test 4 (exploratory, not ledgered): AILA 2019 task 2 statutes that map to an IPC section by exact heading match.
Recall of the relevant mapped statutes for the frozen rule (k=5, r=0.7, raw query) and for linear-lr v1 (IL-TUR fit, 100 labels).
Run: uv run python .scratch/slice-13/aila_check.py   (needs /tmp/aila unzipped and /tmp/ipc-headings.tsv)"""
import collections, glob, json, os, re, sqlite3, sys
sys.path.insert(0, "src")
from ibid import bench, bm25
from ibid.linear import LinearModel

norm = lambda s: re.sub(r"[^a-z0-9 ]", "", s.lower().replace("-", " ")).strip()
head = {}
for l in open("/tmp/ipc-headings.tsv"):
    p = l.rstrip("\n").split("\t")
    if len(p) == 2 and p[0].startswith("IPC"): head.setdefault(norm(p[1]), []).append(p[0])
mapped = {}
for f in glob.glob("/tmp/aila/Object_statutes/S*.txt"):
    t = open(f, errors="ignore").readline().replace("Title:", "").strip()
    if norm(t) in head: mapped[os.path.basename(f)[:-4]] = set(head[norm(t)])
rel = collections.defaultdict(set)
for l in open("/tmp/aila/relevance_judgments_statutes.txt"):
    q, _, s, r = l.split()
    if r == "1" and s in mapped: rel[q] |= mapped[s]
queries = dict(l.rstrip("\n").split("||", 1) for l in open("/tmp/aila/Query_doc.txt"))
frozen = json.load(open("results/frozen-rule.json")); kn = frozen["knobs"]
db = sqlite3.connect("file:data/index/ibid.sqlite?mode=ro", uri=True); ix = bm25.Index(db, kn["levels"], kn["stem"])
space = {c for c in ix.parent if ix.parent[c] is None and c.startswith("IPC")}
lin = LinearModel("/Users/anmolpokhriyal/data/il-tur/models/linear-lr-v1.json"); reachable = set(lin.labels)
def run(name, pred):
    tp = tot = hit = n = 0; preds = 0
    for q, gold in rel.items():
        p = pred(queries[q]); preds += len(p); n += 1
        tp += len(gold & p); tot += len(gold); hit += bool(gold & p)
    print(json.dumps({"layer": name, "queries": n, "mapped_relevant_pairs": tot, "found": tp, "recall": round(tp / tot, 3),
                      "queries_with_a_hit": hit, "mean_predictions": round(preds / n, 2)}))
def baseline(text, k=5, r=0.7):
    ranked = bench.rank_sections(ix, text, space, frozen["section_score"], frozen["stop_words"], kn)
    return set(bench.predict(ranked, k, r)[0])
run("frozen rule v2.11, top-5", baseline)
run("linear-lr v1", lambda t: set(lin.predict(t)))
inreach = sum(len(g & reachable) for g in rel.values()); tot = sum(len(g) for g in rel.values())
print(json.dumps({"mapped_relevant_pairs": tot, "of_which_inside_the_linear_models_100_labels": inreach}))
