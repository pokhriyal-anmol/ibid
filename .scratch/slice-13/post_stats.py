"""Post-score statistics for the frozen linear-lr v1 on IL-TUR test: bootstrap interval and the score without train duplicates.
Run from the repo root: uv run --no-project --with numpy python .scratch/slice-13/post_stats.py [model test train out]; defaults are the IL-TUR files."""
import hashlib, json, sys
import numpy as np
sys.path.insert(0, "src")
from ibid.linear import LinearModel

D = "/Users/anmolpokhriyal/data/il-tur"
A = sys.argv[1:] or [f"{D}/models/linear-lr-v1.json", f"{D}/ilsi-format/test.jsonl", f"{D}/lsi/train.jsonl", "results/iltur-lsi-test-linear-lr-v1-stats.json"]
m = LinearModel(A[0])
cit = m.labels
ix = {c: i for i, c in enumerate(cit)}
h = lambda t: hashlib.sha256(" ".join(t).encode()).hexdigest()
train = {h(json.loads(l)["text"]) for l in open(A[2])}
rows = [json.loads(l) for l in open(A[1])]
y = np.zeros((len(rows), len(cit)), bool); pred = np.zeros_like(y); dup = np.zeros(len(rows), bool)
from ibid.bench import to_citation
for i, r in enumerate(rows):
    dup[i] = h(r["text"]) in train
    for l in r["labels"]: y[i, ix[to_citation(l)]] = True
    for c in m.predict(" ".join(r["text"])): pred[i, ix[c]] = True


def scores(p, g):
    tp = (p & g).sum(0); fp = (p & ~g).sum(0); fn = (~p & g).sum(0); d = 2 * tp + fp + fn
    return float(np.mean(np.where(d > 0, 2 * tp / np.maximum(d, 1), 0))), float(2 * tp.sum() / max(2 * tp.sum() + fp.sum() + fn.sum(), 1)), float(np.mean(tp / np.maximum(tp + fp, 1))), float(np.mean(tp / np.maximum(tp + fn, 1)))


rng = np.random.default_rng(0)
macro, micro, mprec, mrec = scores(pred, y)
boots = np.array([scores(pred[s], y[s]) for s in (rng.integers(0, len(y), len(y)) for _ in range(1000))])
keep = ~dup
nd = scores(pred[keep], y[keep])
out = {"cases": len(rows), "macro_f1": round(macro, 6), "micro_f1": round(micro, 6), "macro_precision": round(mprec, 4), "macro_recall": round(mrec, 4),
       "macro_f1_95ci": [round(float(np.percentile(boots[:, 0], q)), 4) for q in (2.5, 97.5)],
       "micro_f1_95ci": [round(float(np.percentile(boots[:, 1], q)), 4) for q in (2.5, 97.5)],
       "without_train_duplicates": {"cases": int(keep.sum()), "removed": int(dup.sum()), "macro_f1": round(nd[0], 6), "micro_f1": round(nd[1], 6)}}
json.dump(out, open(A[3], "w"), indent=2, sort_keys=True)
print(json.dumps(out, indent=2))
