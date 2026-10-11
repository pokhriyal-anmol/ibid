"""Slice 2 ticket 11: BM25 in Python, so k1, b, stemming and indexed levels can vary (standard library only, ADR 0002).

At the defaults it reproduces SQLite FTS5's bm25(): idf = ln((N - n + 0.5) / (n + 0.5)), floored at 1e-6, and
tf * (k1 + 1) / (tf + k1 * (1 - b + b * D / avgdl)), summed over query terms."""
import json
import math
import re
import sqlite3
import unicodedata
from functools import lru_cache

STEM_RULE = "suffix-v1"  # a change to STEM_TABLE is a new STEM_RULE, which is in the rule hash
STEM_TABLE = (("sses", "ss", 4), ("ies", "y", 3), ("ing", "", 3), ("ed", "", 3), ("s", "", 3))  # suffix, replacement, min stem
DOC_TOKEN = re.compile(r"[^\W_]+")  # letters and digits, as FTS5's unicode61 splits, so lengths match FTS5
QUERY_TOKEN = re.compile(r"[^\W\d_]+")  # letters only (ADR 0004)


def fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c))


@lru_cache(maxsize=None)
def stem_word(w: str) -> str:
    """One table rule (first that fits), undouble a final consonant after -ing/-ed, then drop a final -e on words over 4 letters."""
    for suf, rep, n in STEM_TABLE:
        if w.endswith(suf) and len(w) - len(suf) >= n and not (suf == "s" and w.endswith(("ss", "us", "is"))):
            w = w[: -len(suf)] + rep
            if suf in ("ing", "ed") and w[-1] == w[-2] and w[-1] not in "aeioulsz":
                w = w[:-1]  # stabbing -> stab
            break
    return w[:-1] if len(w) > 4 and w.endswith("e") else w


def query_terms(raw: str, stop_words, stem: str) -> list[str]:
    """Letters-only terms of the raw query minus stop words, stemmed when asked, repeats dropped, first-seen order."""
    terms = [t for t in QUERY_TOKEN.findall(fold(raw)) if t not in stop_words]
    return list(dict.fromkeys(stem_word(t) for t in terms) if stem == "suffix" else dict.fromkeys(terms))


class Index:
    """Term statistics of one index, built once: documents are the provisions kept by `levels`."""

    def __init__(self, db: sqlite3.Connection, levels: str, stem: str):
        self.parent: dict[str, str | None] = {}
        self.length: dict[str, int] = {}
        self.postings: dict[str, dict[str, int]] = {}
        for cite, text, parent, children in db.execute("SELECT citation, text, parent, children FROM provision ORDER BY rowid"):
            self.parent[cite] = parent
            if (levels == "top" and parent is not None) or (levels == "leaf" and json.loads(children)):
                continue
            tokens = DOC_TOKEN.findall(fold(text))
            self.length[cite] = len(tokens)
            for t in tokens:
                t = stem_word(t) if stem == "suffix" else t
                docs = self.postings.setdefault(t, {})
                docs[cite] = docs.get(cite, 0) + 1
        self.avgdl = sum(self.length.values()) / len(self.length) if self.length else 0.0

    def scores(self, terms: list[str], k1: float, b: float) -> dict[str, float]:
        """BM25 of every document holding at least one term."""
        out: dict[str, float] = {}
        for t in terms:
            docs = self.postings.get(t, {})
            idf = math.log((len(self.length) - len(docs) + 0.5) / (len(docs) + 0.5))
            idf = idf if idf > 0 else 1e-6
            for cite, tf in docs.items():
                norm = tf + k1 * (1 - b + b * self.length[cite] / self.avgdl)
                out[cite] = out.get(cite, 0.0) + idf * tf * (k1 + 1) / norm
        return out
