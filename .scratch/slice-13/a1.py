"""Amendment A1: lower cutoffs and bootstrap SE on saved dev probabilities. numpy only."""
import json, sys
import numpy as np
D, L = sys.argv[1], sys.argv[2]
vocab = list(json.load(open(f"{D}/label_vocab.json"))); ix = {v: i for i, v in enumerate(vocab)}
rows = [json.loads(l) for l in open(f"{D}/dev.jsonl")]
y = np.zeros((len(rows), len(vocab)), dtype=bool)
for i, r in enumerate(rows):
    for l in r["labels"]: y[i, ix[l]] = True


def macro(pred, y):
    tp = (pred & y).sum(0); fp = (pred & ~y).sum(0); fn = (~pred & y).sum(0)
    den = 2 * tp + fp + fn
    return float(np.mean(np.where(den > 0, 2 * tp / np.maximum(den, 1), 0)))


rng = np.random.default_rng(0)
for nf, c in ((50000, 4), (150000, 16)):
    p = np.load(f"{L}/dev-proba-f{nf}-C{c}.npy")
    for cut in (0.05, 0.10, 0.15, 0.20):
        pred = p >= cut
        boots = [macro(pred[s], y[s]) for s in (rng.integers(0, len(y), len(y)) for _ in range(200))]
        print(json.dumps({"features": nf, "C": c, "cutoff": cut, "macro_f1": round(macro(pred, y), 4), "boot_se": round(float(np.std(boots)), 4)}))
