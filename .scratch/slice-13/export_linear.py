"""Fit the frozen stage 3 candidate on IL-TUR train only and write the weights as JSON for src/ibid/linear.py.
Run: uv run --no-project --with scikit-learn --with numpy --with scipy python export_linear.py <ilsi-format dir> <out json>"""
import hashlib, json, sys
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier

D, OUT = sys.argv[1], sys.argv[2]
LAYER_VERSION = sys.argv[6] if len(sys.argv) > 6 else 'v1'
FEATURES, C, CUTOFF = (int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5])) if len(sys.argv) > 5 else (50_000, 4, 0.15)  # default frozen on IL-TUR dev, see strategy.md
vocab = list(json.load(open(f"{D}/label_vocab.json"))); index = {v: i for i, v in enumerate(vocab)}
rows = [json.loads(l) for l in open(f"{D}/train.jsonl")]
y = np.zeros((len(rows), len(vocab)), dtype=np.int8)
for i, r in enumerate(rows):
    for l in r["labels"]: y[i, index[l]] = 1
vec = TfidfVectorizer(sublinear_tf=True, max_features=FEATURES, lowercase=True, dtype=np.float32)
x = vec.fit_transform([" ".join(r["text"]) for r in rows])
with joblib.parallel_config(max_nbytes=None):
    clf = OneVsRestClassifier(LogisticRegression(C=C, solver="liblinear"), n_jobs=-1).fit(x, y)
terms = vec.get_feature_names_out().tolist()
r6 = lambda a: [float(f"{v:.7g}") for v in a]
doc = {"header": {"layer": "linear-lr", "layer_version": LAYER_VERSION, "cutoff": CUTOFF, "features": FEATURES, "C": C,
                  "train_sha256": hashlib.sha256(open(f"{D}/train.jsonl", "rb").read()).hexdigest(), "train_cases": len(rows),
                  "method": "one-vs-rest logistic regression (liblinear, L2) on sublinear tf-idf unigrams, scikit-learn, offline",
                  "tokenisation": "scikit-learn default token pattern, lower-cased"},
       "labels": vocab, "vocab": terms, "idf": r6(vec.idf_),
       "coef": [r6(e.coef_[0]) for e in clf.estimators_], "intercept": r6([e.intercept_[0] for e in clf.estimators_])}
json.dump(doc, open(OUT, "w"), separators=(",", ":"))
