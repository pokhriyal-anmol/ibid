"""linear-lr: one-vs-rest logistic regression on tf-idf, trained offline, predicted here with the standard library.

The weights file is built by .scratch/slice-13/export_linear.py (scikit-learn, outside the package). Nothing here imports it.
Tokenising and weighting copy scikit-learn's TfidfVectorizer(sublinear_tf=True) so the stored coefficients mean the same thing."""
import json
import math
import re
from collections import Counter
from pathlib import Path

from . import bench

LAYER = "linear-lr"
TOKEN = re.compile(r"(?u)\b\w\w+\b")


class LinearModel:
    def __init__(self, path: str):
        self.sha256 = bench.sha256(path)
        m = json.loads(Path(path).read_text())
        self.header, self.labels = m["header"], [bench.to_citation(label) for label in m["labels"]]
        self.cutoff = float(self.header["cutoff"])
        self.term = {t: i for i, t in enumerate(m["vocab"])}
        self.idf, self.coef, self.bias = m["idf"], m["coef"], m["intercept"]
        if len(self.coef) != len(self.labels) or any(len(row) != len(self.idf) for row in self.coef):
            raise ValueError("linear model: coefficient matrix does not match labels and vocabulary")

    def probabilities(self, text: str) -> dict[str, float]:
        counts = Counter(t for t in TOKEN.findall(text.lower()) if t in self.term)
        weight = {self.term[t]: (1 + math.log(n)) * self.idf[self.term[t]] for t, n in counts.items()}
        norm = math.sqrt(sum(w * w for w in weight.values())) or 1.0
        out = {}
        for label, row, b in zip(self.labels, self.coef, self.bias):
            z = b + sum(w * row[i] for i, w in weight.items()) / norm
            out[label] = 1 / (1 + math.exp(-z)) if z > -700 else 0.0
        return out

    def predict(self, text: str) -> list[str]:
        p = self.probabilities(text)
        return sorted((c for c in p if p[c] >= self.cutoff), key=lambda c: (-p[c], c))
