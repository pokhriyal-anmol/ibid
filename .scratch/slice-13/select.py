"""Pre-registered selection on dev: best cutoff per fit, bootstrap SE of the overall best, tie-break (smallest features, then smallest C)
among fits within one SE of the best. numpy only. Run: uv run --no-project --with numpy python select.py <data dir> <stage dir>"""
import json, sys
import numpy as np
D, L = sys.argv[1], sys.argv[2]
vocab = list(json.load(open(f"{D}/label_vocab.json"))); ix = {v: i for i, v in enumerate(vocab)}
rows = [json.loads(l) for l in open(f"{D}/dev.jsonl")]
y = np.zeros((len(rows), len(vocab)), bool)
for i, r in enumerate(rows):
    for l in r["labels"]: y[i, ix[l]] = True
def macro(p, g):
    tp, fp, fn = (p & g).sum(0), (p & ~g).sum(0), (~p & g).sum(0); d = 2 * tp + fp + fn
    return float(np.mean(np.where(d > 0, 2 * tp / np.maximum(d, 1), 0)))
CUTS = (0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5)
best = {}
for nf in (50000, 150000):
    for c in (1, 4, 16):
        p = np.load(f"{L}/dev-proba-f{nf}-C{c}.npy")
        s = {cut: macro(p >= cut, y) for cut in CUTS}; cut = max(s, key=s.get); best[(nf, c)] = (s[cut], cut)
        print(nf, c, "best cutoff", cut, "macro", round(s[cut], 4), "edge" if cut in (CUTS[0], CUTS[-1]) else "")
top = max(best, key=lambda k: best[k][0]); p = np.load(f"{L}/dev-proba-f{top[0]}-C{top[1]}.npy") >= best[top][1]
rng = np.random.default_rng(0)
se = float(np.std([macro(p[s], y[s]) for s in (rng.integers(0, len(y), len(y)) for _ in range(200))]))
ok = sorted(k for k, v in best.items() if v[0] >= best[top][0] - se)
print("overall best", top, round(best[top][0], 4), "SE", round(se, 4), "within one SE:", ok, "-> frozen", ok[0], "cutoff", best[ok[0]][1])
