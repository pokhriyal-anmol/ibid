"""Benchmark helpers: map LeSICiN label strings to IPC citations and check them against the index."""
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

from ibid import bm25
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


DEFAULT_KNOBS = {"bm25_k1": 1.2, "bm25_b": 0.75, "stem": "none", "levels": "all"}  # FTS5's own k1 and b, no stemming, every provision


def check_params(k: int, r: float, rollup: str) -> None:
    if k < 1 or not 0 < r <= 1 or rollup not in ROLLUPS:
        raise ValueError("need k >= 1, 0 < r <= 1 and a known roll-up")


def knobs_of(params: dict | None) -> dict:
    """The four ticket 11 knobs of a params dict or frozen record, defaults filling what an older log lacks."""
    return {n: (params or {}).get(n, d) for n, d in DEFAULT_KNOBS.items()}


def check_knobs(knobs: dict) -> None:
    if not 0 < knobs["bm25_k1"] < float("inf") or not 0 <= knobs["bm25_b"] <= 1:
        raise ValueError("need bm25_k1 > 0 and 0 <= bm25_b <= 1")
    if knobs["stem"] not in ("none", "suffix") or knobs["levels"] not in ("all", "top", "leaf"):
        raise ValueError("need stem none or suffix, and levels all, top or leaf")


def rule_hash(k: int, r: float, rollup: str, stop_words=None, knobs: dict | None = None) -> str:
    params = {"stop_words": sorted(STOP_WORDS if stop_words is None else stop_words), "split": "non-letters", "join": "OR", "section_score": rollup,
              "dedup": True, "quote": True, "top_k": k, "relative_threshold": r, **knobs_of(knobs), "stem_rule": bm25.STEM_RULE}
    return hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()


def rank_sections(ix: bm25.Index, raw: str, space: set[str], rollup: str, stop_words=None,
                  knobs: dict | None = None) -> list[tuple[str, float]]:
    """Section citations inside the label space with their roll-up score, best first, ties by citation string."""
    kn = knobs_of(knobs)
    terms = bm25.query_terms(raw, STOP_WORDS if stop_words is None else stop_words, kn["stem"])
    hits: dict[str, list[float]] = {}
    for cite, score in ix.scores(terms, kn["bm25_k1"], kn["bm25_b"]).items():
        while ix.parent[cite] is not None:
            cite = ix.parent[cite]
        if cite in space:
            hits.setdefault(cite, []).append(score)
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


def pinned_test_hash(manifest_path: str) -> str | None:
    with open(manifest_path) as f:
        return json.load(f).get("test.jsonl", {}).get("sha256")


def load_space(labels_path: str) -> set[str]:
    with open(labels_path) as f:
        cites = [to_citation(label) for label in json.load(f)]
    if not cites or None in cites:
        raise ValueError("label vocabulary is empty or has an unparseable label")
    return set(cites)


def load_cases(path: str, space: set[str], sample: int | None = None) -> tuple[list[dict], list[set[str]]]:
    with open(path) as f:
        cases = [json.loads(line) for line in f if line.strip()]
    if sample is not None:
        cases = sorted(cases, key=lambda c: c["id"])[:sample]
    gold = [{to_citation(label) for label in c["labels"]} for c in cases]
    if not cases or any(not g <= space for g in gold):
        raise ValueError(f"{Path(path).name}: empty split, or a label outside the label vocabulary")
    return cases, gold


def read_ledger(path: str) -> list:
    return json.loads(Path(path).read_text()) if Path(path).is_file() else []


def freeze_rule(log_path: str, round_no: int | None, out_path: str) -> int:
    """Record, from a logged round (default the last), the rule that the test split may be scored against."""
    from ibid.optimise import freezable  # optimise imports this module
    try:
        rounds = json.loads(Path(log_path).read_text())["rounds"]
        entry = rounds[-1 if round_no is None else round_no]
    except (OSError, KeyError, ValueError, IndexError):
        print(f"error: {log_path} is missing or has no such round", file=sys.stderr)
        return 1
    if not freezable(entry):
        print(f"error: round {entry['round']} is flagged {entry['flags']}; the owner must set owner_approved in the log",
              file=sys.stderr)
        return 1
    p = entry["params"]
    rec = {"rule": entry["rule"], "round": entry["round"], "k": p["k"], "r": p["r"], "section_score": p["rollup"],
           "stop_words": p["stop_words"], "knobs": knobs_of(p)}
    Path(out_path).write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    return 0


def test_guard(split_path: str, manifest_path: str, k: int, r: float, rollup: str, frozen_path: str, ledger_path: str,
               rescore: bool) -> tuple[bool, dict | None, list, int]:
    """(is the test split, its frozen record, prior ledger entries, 1 if refused).

    Keyed on the file hash so a copy at another path is still the test split."""
    sha = sha256(split_path)
    if Path(split_path).stem != "test" and sha != pinned_test_hash(manifest_path):
        return False, None, [], 0
    try:
        frozen = json.loads(Path(frozen_path).read_text())
        held = frozen["rule"]["params_sha256"] == rule_hash(k, r, rollup, frozen["stop_words"], frozen.get("knobs"))
    except (OSError, KeyError, ValueError):
        held = False
    if not held:
        print(f"error: the test split is scored only against a frozen rule; {frozen_path} is missing or holds another rule",
              file=sys.stderr)
        return True, None, [], 1
    prior = [e for e in read_ledger(ledger_path) if e["split_sha256"] == sha]
    if prior and not rescore:
        print("error: the test split was already scored; pass --rescore-test to score it again", file=sys.stderr)
        return True, None, prior, 1
    return True, frozen, prior, 0


def run_bench(split_path: str, labels_path: str, index_path: str, k: int, r: float, rollup: str, out_path: str,
              manifest_path: str, sample: int | None = None, frozen_path: str = "results/frozen-rule.json",
              ledger_path: str = "results/test-ledger.json", rescore: bool = False, knobs: dict | None = None) -> int:
    try:
        check_params(k, r, rollup)
        check_knobs(knobs_of(knobs))
        if sample is not None and sample < 1:
            raise ValueError("--sample must be at least 1")
        if verify_pinned([split_path, labels_path], manifest_path):
            return 1
        on_test, frozen, prior, refused = test_guard(split_path, manifest_path, k, r, rollup, frozen_path, ledger_path, rescore)
        if refused:
            return 1
        if on_test and sample is not None:
            raise ValueError("--sample is refused on the test split; it is scored once, in full")
        space = load_space(labels_path)
        cases, gold = load_cases(split_path, space, sample)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    stop_words = frozen["stop_words"] if frozen else None  # the test split is scored with the frozen round's rule
    knobs = knobs_of(frozen.get("knobs") if frozen else knobs)
    rule = {"name": RULE_NAME, "version": frozen["rule"]["version"] if frozen else RULE_VERSION,
            "params_sha256": rule_hash(k, r, rollup, stop_words, knobs)}
    db = sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)
    ix = bm25.Index(db, knobs["levels"], knobs["stem"])
    ranked = [rank_sections(ix, " ".join(c["text"]), space, rollup, stop_words, knobs) for c in cases]
    top_k, above_r = zip(*(predict(x, k, r) for x in ranked))
    k_sets, r_sets = [set(p) for p in top_k], [set(p) for p in above_r]
    results = {
        "inputs": {"split_sha256": sha256(split_path), "labels_sha256": sha256(labels_path), "index_sha256": sha256(index_path)},
        "rule": rule,
        "parser_version": PARSER_VERSION,
        "k": k,
        "cases": len(cases),
        **({"sample": sample, "sample_rule": SAMPLE_RULE} if sample is not None else {}),
        "section_score": rollup,
        "knobs": knobs,
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
    if on_test:  # dev and train never reach the ledger; the first score stays, and is reported beside the new one
        entry = {"split_sha256": results["inputs"]["split_sha256"], "rule": results["rule"], "k": k, "r": r,
                 "section_score": rollup, "cases": len(cases), "scores": results["scores"],
                 "threshold_scores": results["threshold"]["scores"]}
        Path(ledger_path).write_text(json.dumps(read_ledger(ledger_path) + [entry], indent=2, sort_keys=True) + "\n")
        results["test_scores"] = prior + [entry]
    with open(out_path, "w") as f:
        f.write(json.dumps(results, indent=2, sort_keys=True) + "\n")
    return 0
