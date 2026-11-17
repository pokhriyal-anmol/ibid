"""Stage 3 grid: one-vs-rest logistic regression on tf-idf, scored on dev. Offline research script, not part of the package.
Run: uv run --no-project --with scikit-learn --with numpy --with scipy python train_linear.py <ilsi-format dir> <out dir>"""
import json, sys, time
import numpy as np
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.metrics import f1_score

D, OUT = sys.argv[1], sys.argv[2]
import os
GRID_FEATURES, GRID_C = (50_000, 150_000), (1, 4, 16)
CUTOFFS = tuple(float(c) for c in os.environ.get('IBID_CUTOFFS', '0.15,0.2,0.25,0.3,0.4,0.5').split(','))


def load(split):
    rows = [json.loads(l) for l in open(f"{D}/{split}.jsonl")]
    return [" ".join(r["text"]) for r in rows], [r["labels"] for r in rows]


vocab = list(json.load(open(f"{D}/label_vocab.json")))
index = {v: i for i, v in enumerate(vocab)}


def matrix(labels):
    y = np.zeros((len(labels), len(vocab)), dtype=np.int8)
    for i, ls in enumerate(labels):
        for l in ls:
            y[i, index[l]] = 1
    return y


xt, lt = load("train"); xd, ld = load("dev")
yt, yd = matrix(lt), matrix(ld)
for nf in GRID_FEATURES:
    t0 = time.time()
    vec = TfidfVectorizer(sublinear_tf=True, max_features=nf, lowercase=True, dtype=np.float32)
    at, ad = vec.fit_transform(xt), vec.transform(xd)
    for c in GRID_C:
        with joblib.parallel_config(max_nbytes=None):  # memmapped sparse input is read-only and liblinear needs to write
            clf = OneVsRestClassifier(LogisticRegression(C=c, solver="liblinear"), n_jobs=-1).fit(at, yt)
        p = clf.predict_proba(ad)
        np.save(f"{OUT}/dev-proba-f{nf}-C{c}.npy", p.astype(np.float32))
        for cut in CUTOFFS:
            pred = (p >= cut).astype(np.int8)
            print(json.dumps({"features": nf, "C": c, "cutoff": cut,
                              "macro_f1": round(f1_score(yd, pred, average="macro", zero_division=0), 4),
                              "micro_f1": round(f1_score(yd, pred, average="micro", zero_division=0), 4)}), flush=True)
        print(f"# f{nf} C{c} done {time.time()-t0:.0f}s", flush=True)
