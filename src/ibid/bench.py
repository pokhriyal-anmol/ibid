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


SAMPLE_RULE = "first N cases by sorted id"


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


def label_counts(gold: list[set[str]], pred: list[set[str]], space: set[str]) -> dict[str, tuple[int, int, int]]:
    """Per label (tp, fp, fn) over the cases."""
    return {c: (sum(c in g and c in p for g, p in zip(gold, pred)),
                sum(c in p and c not in g for g, p in zip(gold, pred)),
                sum(c in g and c not in p for g, p in zip(gold, pred))) for c in space}


def score(gold: list[set[str]], pred: list[set[str]], space: set[str]) -> dict[str, float]:
    counts = label_counts(gold, pred, space).values()
    jac = [len(g & p) / len(g | p) if g | p else 0.0 for g, p in zip(gold, pred)]
    return {
        "micro_f1": round(f1(*(sum(col) for col in zip(*counts))), 6),
        "macro_f1": round(sum(f1(*c) for c in counts) / len(space), 6),
        "jaccard": round(sum(jac) / len(jac), 6) if jac else 0.0,  # an empty stratum scores 0
    }


def per_label(gold: list[set[str]], pred: list[set[str]], space: set[str]) -> dict:
    rows = []
    for c, (tp, fp, fn) in sorted(label_counts(gold, pred, space).items()):
        rows.append({"citation": c, "support": tp + fn, "tp": tp, "fp": fp, "fn": fn,
                     "precision": round(tp / (tp + fp), 6) if tp + fp else 0.0,  # nothing predicted scores 0
                     "recall": round(tp / (tp + fn), 6) if tp + fn else 0.0,  # no gold scores 0
                     "f1": round(f1(tp, fp, fn), 6)})
    return {"labels": rows, "never_found": [r["citation"] for r in rows if r["support"] and not r["tp"]]}


GOLD_BUCKETS = (("1", lambda n: n == 1), ("2", lambda n: n == 2), ("3+", lambda n: n >= 3))
WORD_BUCKETS = (("<=150", lambda n: n <= 150), ("151-500", lambda n: 151 <= n <= 500), (">500", lambda n: n > 500))


def strata(cases: list[dict], gold: list[set[str]], pred: list[set[str]], space: set[str]) -> dict:
    words = [len(" ".join(c["text"]).split()) for c in cases]
    out = {}
    for name, sizes, buckets in (("gold_label_count", [len(g) for g in gold], GOLD_BUCKETS), ("words", words, WORD_BUCKETS)):
        out[name] = {}
        for label, test in buckets:
            idx = [i for i, n in enumerate(sizes) if test(n)]
            out[name][label] = {"cases": len(idx), "scores": score([gold[i] for i in idx], [pred[i] for i in idx], space)}
    return out


def sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_pinned(paths: list[str], manifest_path: str) -> int:
    """Refuse (return 1) unless every file's SHA-256 equals its manifest entry, keyed by file name."""
    with open(manifest_path) as f:
        pinned = json.load(f)
    bad = 0
    for p in paths:
        name, got = Path(p).name, sha256(p)
        want = pinned.get(name, {}).get("sha256")
        if got != want:
            print(f"error: {name} does not match the manifest: pinned {want}, found {got}", file=sys.stderr)
            bad = 1
    return bad


def run_bench(split_path: str, labels_path: str, index_path: str, k: int, r: float, rollup: str, out_path: str,
              manifest_path: str, sample: int | None = None) -> int:
    if k < 1 or not 0 < r <= 1 or rollup not in ROLLUPS:
        print("error: need k >= 1, 0 < r <= 1 and a known roll-up", file=sys.stderr)
        return 1
    if sample is not None and sample < 1:
        print("error: --sample must be at least 1", file=sys.stderr)
        return 1
    if sample is not None and Path(split_path).stem == "test":  # shortcut: by file name, ticket 06/07 pin the hash
        print("error: --sample is refused on the test split; it is scored once, in full", file=sys.stderr)
        return 1
    if verify_pinned([split_path, labels_path], manifest_path):
        return 1
    with open(labels_path) as f:
        cites = [to_citation(label) for label in json.load(f)]
    if not cites or None in cites:
        print("error: label vocabulary is empty or has an unparseable label", file=sys.stderr)
        return 1
    space = set(cites)
    with open(split_path) as f:
        cases = [json.loads(line) for line in f if line.strip()]
    if sample is not None:
        cases = sorted(cases, key=lambda c: c["id"])[:sample]
    gold = [{to_citation(label) for label in c["labels"]} for c in cases]
    if not cases or any(not g <= space for g in gold):
        print("error: empty split, or a case has a label outside the label vocabulary", file=sys.stderr)
        return 1
    db = sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)
    ranked = [rank_sections(db, " ".join(c["text"]), space, rollup) for c in cases]
    top_k, above_r = zip(*(predict(x, k, r) for x in ranked)) if ranked else ((), ())
    k_sets, r_sets = [set(p) for p in top_k], [set(p) for p in above_r]
    results = {
        "inputs": {"split_sha256": sha256(split_path), "labels_sha256": sha256(labels_path), "index_sha256": sha256(index_path)},
        "rule": {"name": RULE_NAME, "version": RULE_VERSION, "params_sha256": rule_hash(k, r, rollup)},
        "parser_version": PARSER_VERSION,
        "k": k,
        "cases": len(cases),
        **({"sample": sample, "sample_rule": SAMPLE_RULE} if sample is not None else {}),
        "section_score": rollup,
        "scores": score(gold, k_sets, space),
        "per_label": per_label(gold, k_sets, space),
        "strata": strata(cases, gold, k_sets, space),
        "threshold": {
            "r": r,
            "scores": score(gold, r_sets, space),
            "per_label": per_label(gold, r_sets, space),
            "strata": strata(cases, gold, r_sets, space),
            "predictions": {c["id"]: p for c, p in zip(cases, above_r)},
        },
        "conventions": {
            "label_space": f"{len(space)} labels",
            "macro_f1": "mean of per-label F1 over the whole label space; a label with no gold and no prediction scores 0",
            "per_label": "precision is 0 when nothing is predicted for the label, recall is 0 when it has no gold, so "
                         "zero support and zero predictions gives 0 for all three; never_found lists labels with support "
                         "and no true positive; labels are sorted by citation string",
            "strata": "same three scores per stratum, macro F1 over the whole label space; words are whitespace tokens "
                      "of the joined sentences; an empty stratum scores 0",
            "jaccard": "mean over cases of |P and G| / |P or G|; an empty union scores 0",
        },
        "predictions": {c["id"]: p for c, p in zip(cases, top_k)},
    }
    with open(out_path, "w") as f:
        f.write(json.dumps(results, indent=2, sort_keys=True) + "\n")
    return 0
