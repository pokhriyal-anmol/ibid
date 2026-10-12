"""Slice 3 ticket 08, route B: multinomial naive Bayes over the ILSI labels, an opt-in layer under ADR 0005 (standard library only)."""
import hashlib
import json
import math
import sys
from pathlib import Path

from ibid import bench, bm25, concordance
from ibid.charges import _load_set

LAYER, LAYER_VERSION, TOP_K = "assoc-nb", "v1", 5  # a change to tokenisation, smoothing or k is a new LAYER_VERSION


def tokens(text: str) -> list[str]:
    """Lower-cased letters-only terms minus the 44 base stop words; repeats kept, no stemming."""
    return [t for t in bm25.QUERY_TOKEN.findall(bm25.fold(text)) if t not in bench.STOP_WORDS]


def fit(train_path: str, holdout_path: str, labels_path: str, out_path: str) -> int:
    """Count terms per label over the train split minus the held-out ids; the model file is a pure function of its inputs."""
    try:
        space = bench.load_space(labels_path)
        held = {i["id"] for i in json.loads(Path(holdout_path).read_text())["items"]}
        docs = dict.fromkeys(sorted(space), 0)
        counts: dict[str, dict[str, int]] = {c: {} for c in docs}
        used = dropped = 0
        with open(train_path) as f:
            for line in filter(str.strip, f):
                case = json.loads(line)
                if case["id"] in held:
                    dropped += 1
                    continue
                cites = {bench.to_citation(x) for x in case["labels"]}
                if not cites <= space:
                    raise ValueError(f"case {case['id']}: a label outside the label vocabulary")
                used += 1
                terms = tokens(" ".join(case["text"]))
                for c in cites:
                    docs[c] += 1
                    for t in terms:
                        counts[c][t] = counts[c].get(t, 0) + 1
    except (OSError, KeyError, ValueError, TypeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    header = {"layer": LAYER, "layer_version": LAYER_VERSION, "top_k": TOP_K, "train_sha256": bench.sha256(train_path),
              "holdout_ids_sha256": hashlib.sha256(json.dumps(sorted(held)).encode()).hexdigest(), "holdout_ids": len(held),
              "holdout_ids_dropped_from_train": dropped, "cases_fitted": used,
              "tokenisation": "lower-case, letters only, 44 base stop words, no stemming"}
    model = {"header": header, "docs": docs, "counts": counts}
    Path(out_path).write_text(json.dumps(model, sort_keys=True, separators=(",", ":")) + "\n")
    return 0


class Model:
    def __init__(self, path: str):
        self.sha256 = bench.sha256(path)
        m = json.loads(Path(path).read_text())
        self.header, self.counts = m["header"], m["counts"]
        self.labels = sorted(m["docs"])
        n = sum(m["docs"].values())
        self.prior = {c: math.log(d / n) for c, d in m["docs"].items() if d}  # a label never seen in training cannot be ranked
        self.total = {c: sum(v.values()) for c, v in self.counts.items()}
        self.vocab = {t for v in self.counts.values() for t in v}

    def predict(self, text: str) -> list[str]:
        terms = [t for t in tokens(text) if t in self.vocab]  # a term the training never saw is the same for every label
        v = len(self.vocab)
        score = {c: p + sum(math.log((self.counts[c].get(t, 0) + 1) / (self.total[c] + v)) for t in terms) for c, p in self.prior.items()}
        return sorted(score, key=lambda c: (-score[c], c))[:TOP_K]


def predict(model_path: str, set_path: str, concordance_path: str, index_path: str, out_path: str) -> int:
    """IPC citations from the model; BNS citations only from verified concordance entries of those."""
    try:
        raw, items, db = _load_set(set_path, index_path)
        model, entries = Model(model_path), concordance.load(concordance_path, db)
    except (OSError, KeyError, ValueError, TypeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    out = {}
    for item in items:
        ipc = model.predict(item["query"])
        hits = [h for c in ipc for h in entries if h["verified"] and c in h["ipc"]]
        out[item["id"]] = {"ipc": ipc, "bns": list(dict.fromkeys(b for h in hits for b in h["bns"]))}
    doc = {"layer": LAYER, "layer_version": LAYER_VERSION, "set_sha256": hashlib.sha256(raw).hexdigest(),
           "inputs": {"model": model.sha256, "concordance": bench.sha256(concordance_path)}, "items": out}
    Path(out_path).write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    return 0


def evaluate(model_path: str, split_path: str, manifest_path: str, ledger_path: str, rescore: bool, out_path: str | None) -> int:
    """Score a split with the benchmark's own scorer. The pinned test split is scored once per layer version, in its own ledger."""
    try:
        model = Model(model_path)
        sha = bench.sha256(split_path)
        try:
            pinned = bench.pinned_test_hash(manifest_path)
        except (OSError, ValueError):
            pinned = None
        on_test = Path(split_path).stem == "test" or sha == pinned
        prior = [e for e in bench.read_ledger(ledger_path)
                 if e["layer"] == LAYER and e["layer_version"] == LAYER_VERSION and e["split_sha256"] == sha]
        if on_test and prior and not rescore:
            raise ValueError("the test split was already scored for this layer version; pass --rescore-test to score it again")
        space = set(model.labels)
        cases, gold = bench.load_cases(split_path, space)
    except (OSError, KeyError, ValueError, TypeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    preds = [set(model.predict(" ".join(c["text"]))) for c in cases]
    res = {"layer": LAYER, "layer_version": LAYER_VERSION, "k": TOP_K, "model_sha256": model.sha256, "split_sha256": sha,
           "cases": len(cases), "scores": bench.score(gold, preds, space)}
    if on_test:
        entry = {k: res[k] for k in ("layer", "layer_version", "model_sha256", "split_sha256", "cases", "scores")}
        Path(ledger_path).write_text(json.dumps(bench.read_ledger(ledger_path) + [entry], indent=2, sort_keys=True) + "\n")
        res["test_scores"] = prior + [entry]
    text = json.dumps(res, indent=2, sort_keys=True) + "\n"
    if out_path:
        Path(out_path).write_text(text)
    print(text, end="")
    return 0
