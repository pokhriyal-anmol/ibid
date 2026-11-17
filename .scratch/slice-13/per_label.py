"""Test 5: per-label F1 of the frozen linear-lr v1 on IL-TUR test, beside the frozen rule. Statistics of the one test look, no refit."""
import json, sys
import numpy as np
sys.path.insert(0, "src")
from ibid.bench import to_citation
from ibid.linear import LinearModel

D = "/Users/anmolpokhriyal/data/il-tur"
m = LinearModel(f"{D}/models/linear-lr-v1.json"); cit = m.labels; ix = {c: i for i, c in enumerate(cit)}
rows = [json.loads(l) for l in open(f"{D}/ilsi-format/test.jsonl")]
y = np.zeros((len(rows), len(cit)), bool); p = np.zeros_like(y)
for i, r in enumerate(rows):
    for l in r["labels"]: y[i, ix[to_citation(l)]] = True
    for c in m.predict(" ".join(r["text"])): p[i, ix[c]] = True
tp, fp, fn = (p & y).sum(0), (p & ~y).sum(0), (~p & y).sum(0)
f1 = 2 * tp / np.maximum(2 * tp + fp + fn, 1); prec = tp / np.maximum(tp + fp, 1); rec = tp / np.maximum(tp + fn, 1)
base = json.load(open("results/iltur-lsi-test-baseline.json"))["per_label"]
bf = {to_citation(k) if not k.startswith("IPC") else k: v for k, v in (base.items() if isinstance(base, dict) else {})}
sup = y.sum(0)
order = np.argsort(f1)
def row(i): return {"label": cit[i], "support": int(sup[i]), "f1": round(float(f1[i]), 3), "p": round(float(prec[i]), 3), "r": round(float(rec[i]), 3)}
out = {"macro_f1": round(float(f1.mean()), 4), "macro_precision": round(float(prec.mean()), 4), "macro_recall": round(float(rec.mean()), 4),
       "labels_f1_below": {t: int((f1 < t).sum()) for t in (0.1, 0.2, 0.3, 0.5)}, "labels_f1_at_least_0.5": int((f1 >= 0.5).sum()),
       "never_found": [cit[i] for i in range(len(cit)) if tp[i] == 0],
       "support_vs_f1_corr": round(float(np.corrcoef(np.log(sup), f1)[0, 1]), 3),
       "weakest": [row(i) for i in order[:8]], "strongest": [row(i) for i in order[::-1][:8]]}
json.dump(out, open("results/iltur-lsi-test-linear-lr-v1-per-label.json", "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k not in ("weakest", "strongest")}))
print("weakest", [(r["label"], r["support"], r["f1"]) for r in out["weakest"]])
print("strongest", [(r["label"], r["support"], r["f1"]) for r in out["strongest"]])
