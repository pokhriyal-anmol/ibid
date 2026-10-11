"""Benchmark helpers: map LeSICiN label strings to IPC citations and check them against the index."""
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

from ibid.parse import PARSER_VERSION

LABEL = re.compile(r"Section (\d+[A-Z]{0,2}(?:\([0-9a-z]+\))*) in The Indian Penal Code")


def to_citation(label: str) -> str | None:
    m = LABEL.fullmatch(label)
    return f"IPC {m[1]}" if m else None


def check_labels(vocab_path: str, index_path: str) -> int:
    with open(vocab_path) as f:
        labels = list(json.load(f))
    if not labels:
        print("error: empty label vocabulary", file=sys.stderr)
        return 1
    db = sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)
    mapped, missing, unparseable = 0, [], []
    for label in labels:
        cite = to_citation(label)
        if cite is None:
            unparseable.append(label)
        elif db.execute("SELECT 1 FROM provision WHERE citation = ?", (cite,)).fetchone():
            mapped += 1
        else:
            missing.append(f"{label} -> {cite}")
    print(f"{mapped} mapped, {len(missing)} missing, {len(unparseable)} unparseable")
    for kind, items in (("missing from index", missing), ("unparseable", unparseable)):
        for item in items:
            print(f"{kind}: {item}", file=sys.stderr)
    return 1 if missing or unparseable else 0


# Query rule v1 (ADR 0004). A change to any of these is a new rule version, never an edit.
RULE_NAME, RULE_VERSION = "query-rule", "v1"
STOP_WORDS = (
    "a an and are as at be been but by for from had has have he her his i in is it its of on or she so that the their "
    "them there they this to was were which who will with you your"
).split()
ROLLUPS = {"max": max, "sum": sum}  # how a section scores from the BM25 of its retrieved provisions


def rule_hash(k: int, r: float, rollup: str) -> str:
    params = {"stop_words": sorted(STOP_WORDS), "split": "non-letters", "join": "OR", "section_score": rollup,
              "top_k": k, "relative_threshold": r}
    return hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()


def to_fts_query(raw: str) -> str:
    seen = dict.fromkeys(t for t in re.findall(r"[^\W\d_]+", raw.lower()) if t not in STOP_WORDS)
    return " OR ".join(f'"{t}"' for t in seen)  # quoted so a word like "near" is never an FTS operator


def rank_sections(db: sqlite3.Connection, raw: str, space: set[str], rollup: str) -> list[tuple[str, float]]:
    """Section citations inside the label space with their roll-up score, best first, ties by citation string."""
    query = to_fts_query(raw)
    if not query:
        return []
    parent = dict(db.execute("SELECT citation, parent FROM provision WHERE citation LIKE 'IPC %'"))
    hits: dict[str, list[float]] = {}
    for cite, rank in db.execute("SELECT citation, rank FROM fts WHERE fts MATCH ? AND citation LIKE 'IPC %'", (query,)):
        while parent[cite] is not None:
            cite = parent[cite]
        if cite in space:
            hits.setdefault(cite, []).append(-rank)
    return sorted(((c, ROLLUPS[rollup](v)) for c, v in hits.items()), key=lambda cs: (-cs[1], cs[0]))


def predict(ranked: list[tuple[str, float]], k: int, r: float) -> tuple[list[str], list[str]]:
    """Top-k sections, and every section scoring at least r times the top score (scores are not comparable across queries)."""
    top = [c for c, _ in ranked[:k]]
    return top, [c for c, s in ranked if s >= r * ranked[0][1]]


def f1(tp: int, fp: int, fn: int) -> float:
    return 2 * tp / (2 * tp + fp + fn) if tp else 0.0  # no gold and no prediction scores 0


def score(gold: list[set[str]], pred: list[set[str]], space: set[str]) -> dict[str, float]:
    def count(c: str) -> tuple[int, int, int]:
        return (sum(c in g and c in p for g, p in zip(gold, pred)),
                sum(c in p and c not in g for g, p in zip(gold, pred)),
                sum(c in g and c not in p for g, p in zip(gold, pred)))
    counts = [count(c) for c in space]
    jac = [len(g & p) / len(g | p) if g | p else 0.0 for g, p in zip(gold, pred)]
    return {
        "micro_f1": round(f1(*(sum(col) for col in zip(*counts))), 6),
        "macro_f1": round(sum(f1(*c) for c in counts) / len(space), 6),
        "jaccard": round(sum(jac) / len(jac), 6),
    }


def sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_bench(split_path: str, labels_path: str, index_path: str, k: int, r: float, rollup: str, out_path: str) -> int:
    if k < 1 or not 0 < r <= 1 or rollup not in ROLLUPS:
        print("error: need k >= 1, 0 < r <= 1 and a known roll-up", file=sys.stderr)
        return 1
    with open(labels_path) as f:
        cites = [to_citation(label) for label in json.load(f)]
    if not cites or None in cites:
        print("error: label vocabulary is empty or has an unparseable label", file=sys.stderr)
        return 1
    space = set(cites)
    with open(split_path) as f:
        cases = [json.loads(line) for line in f if line.strip()]
    gold = [{to_citation(label) for label in c["labels"]} for c in cases]
    if not cases or any(not g <= space for g in gold):
        print("error: empty split, or a case has a label outside the label vocabulary", file=sys.stderr)
        return 1
    db = sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)
    ranked = [rank_sections(db, " ".join(c["text"]), space, rollup) for c in cases]
    top_k, above_r = zip(*(predict(x, k, r) for x in ranked)) if ranked else ((), ())
    results = {
        "inputs": {"split_sha256": sha256(split_path), "labels_sha256": sha256(labels_path), "index_sha256": sha256(index_path)},
        "rule": {"name": RULE_NAME, "version": RULE_VERSION, "params_sha256": rule_hash(k, r, rollup)},
        "parser_version": PARSER_VERSION,
        "k": k,
        "cases": len(cases),
        "section_score": rollup,
        "scores": score(gold, [set(p) for p in top_k], space),
        "threshold": {
            "r": r,
            "scores": score(gold, [set(p) for p in above_r], space),
            "predictions": {c["id"]: p for c, p in zip(cases, above_r)},
        },
        "conventions": {
            "label_space": f"{len(space)} labels",
            "macro_f1": "mean of per-label F1 over the whole label space; a label with no gold and no prediction scores 0",
            "jaccard": "mean over cases of |P and G| / |P or G|; an empty union scores 0",
        },
        "predictions": {c["id"]: p for c, p in zip(cases, top_k)},
    }
    with open(out_path, "w") as f:
        f.write(json.dumps(results, indent=2, sort_keys=True) + "\n")
    return 0
