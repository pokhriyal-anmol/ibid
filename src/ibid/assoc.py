"""Slice 3 ticket 08, route B: multinomial naive Bayes over the ILSI labels, an opt-in layer under ADR 0005 (standard library only)."""
import hashlib
import json
import lzma
import math
import re
import sqlite3
import sys
from pathlib import Path

from ibid import bench, bm25, concordance, index
from ibid.charges import _load_set

LAYER, LAYER_VERSION, TOP_K = "assoc-nb", "v1", 5  # a change to tokenisation, smoothing or k is a new LAYER_VERSION


def tokens(text: str) -> list[str]:
    """Lower-cased letters-only terms minus the 44 base stop words; repeats kept, no stemming."""
    return [t for t in bm25.QUERY_TOKEN.findall(bm25.fold(text)) if t not in bench.STOP_WORDS]


def _add(docs: dict[str, int], counts: dict[str, dict[str, int]], cites: set[str], terms: list[str]) -> None:
    for c in cites:
        docs[c] += 1
        for t in terms:
            counts[c][t] = counts[c].get(t, 0) + 1


def _vocab(cite_sets, minimum: int) -> tuple[set[str], dict[str, int], dict[str, dict[str, int]]]:
    """Sections cited by at least `minimum` examples, with empty doc and count tables for them."""
    posts: dict[str, int] = {}
    for cites in cite_sets:
        for c in cites:
            posts[c] = posts.get(c, 0) + 1
    vocab = {c for c, k in posts.items() if k >= minimum}
    docs = dict.fromkeys(sorted(vocab), 0)
    return vocab, docs, {c: {} for c in docs}


def _ilsi_read(train_path: str, held: set[str], space: set[str]) -> tuple[list[tuple[set[str], list[str]]], int]:
    """ILSI train cases minus the held-out ids, as (citations, terms); and how many ids were dropped."""
    out, dropped = [], 0
    with open(train_path) as f:
        for line in filter(str.strip, f):
            case = json.loads(line)
            if case["id"] in held:
                dropped += 1
                continue
            cites = {bench.to_citation(x) for x in case["labels"]}
            if not cites <= space:
                raise ValueError(f"case {case['id']}: a label outside the label vocabulary")
            out.append((cites, tokens(" ".join(case["text"]))))
    return out, dropped


def fit(train_path: str, holdout_path: str, labels_path: str, out_path: str) -> int:
    """Count terms per label over the train split minus the held-out ids; the model file is a pure function of its inputs."""
    try:
        space = bench.load_space(labels_path)
        held = {i["id"] for i in json.loads(Path(holdout_path).read_text())["items"]}
        docs = dict.fromkeys(sorted(space), 0)
        counts: dict[str, dict[str, int]] = {c: {} for c in docs}
        examples, dropped = _ilsi_read(train_path, held, space)
        used = len(examples)
        for cites, terms in examples:
            _add(docs, counts, cites, terms)
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


IPC_CITE = re.compile(r"Section (\d+[A-Z]?) of The Indian Penal Code, 1860")
SOURCE_ROW = re.compile(r"row (\d+)$")
NOT_OFFENCES = {"IPC 34", "IPC 149", "IPC 120B"}  # common intention, common object, conspiracy: not offence sections (set v2's rule)


def _rows(path: str) -> list[dict]:
    with (lzma.open(path, "rt") if path.endswith(".xz") else open(path)) as f:
        return [json.loads(line) for line in f if line.strip()]


def _same_post(text: str) -> str:
    return " ".join(bm25.fold(text).split())


def _lay_read(train_path: str, split_path: str, holdout_set: str, index_path: str):
    """ILSIC-Lay train posts minus those equal to a Layman test post: (rows, kept (row no, citations), drops, other-Act count, absent count)."""
    split, train = _rows(split_path), _rows(train_path)
    for i in json.loads(Path(holdout_set).read_text())["items"]:
        m = SOURCE_ROW.search(i["source"])
        if not m or int(m[1]) >= len(split):
            raise ValueError(f"set item {i['id']}: its source row is not in the holdout split file")
    test_posts = {_same_post(r["instruction"]) for r in split}
    db = sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)
    drop = dict.fromkeys(("held_out", "no_offence_section", "none_above_threshold"), 0)
    other_act = absent = 0
    kept: list[tuple[int, set[str]]] = []
    for n, row in enumerate(train):
        if _same_post(row["instruction"]) in test_posts:
            drop["held_out"] += 1
            continue
        other_act += len({a for a in row["answer"] if not IPC_CITE.fullmatch(a)})
        cites = {f"IPC {s}" for a in row["answer"] for s in IPC_CITE.findall(a)} - NOT_OFFENCES
        present = {c for c in cites if index.lookup(db, c)}  # a Citation absent from the index is dropped and counted
        absent += len(cites) - len(present)
        cites = present
        if cites:
            kept.append((n, cites))
        else:
            drop["no_offence_section"] += 1
    return train, kept, drop, other_act, absent


def fit_ilsic_lay(train_path: str, split_path: str, holdout_set: str, index_path: str, min_posts: int, out_path: str) -> int:
    """assoc-nb v2: term counts per IPC section over ILSIC-Lay train posts, minus posts equal to a Layman test split post."""
    try:
        train, kept, drop, other_act, absent = _lay_read(train_path, split_path, holdout_set, index_path)
        vocab, docs, counts = _vocab((c for _, c in kept), min_posts)
        fitted = 0
        for n, cites in kept:
            cites &= vocab
            if not cites:
                drop["none_above_threshold"] += 1
                continue
            fitted += 1
            _add(docs, counts, cites, tokens(train[n]["instruction"]))
    except (OSError, KeyError, ValueError, TypeError, sqlite3.Error, lzma.LZMAError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    header = {"layer": LAYER, "layer_version": "v2", "top_k": TOP_K, "train_sha256": bench.sha256(train_path),
              "holdout_split_sha256": bench.sha256(split_path), "min_posts": min_posts, "posts_read": len(train),
              "posts_fitted": fitted, "posts_dropped": drop, "other_act_citations_dropped": other_act,
              "index_absent_citations_dropped": absent,
              "vocabulary_size": len(vocab), "tokenisation": "lower-case, letters only, 44 base stop words, no stemming"}
    Path(out_path).write_text(json.dumps({"header": header, "docs": docs, "counts": counts}, sort_keys=True, separators=(",", ":")) + "\n")
    return 0


def fit_union(a: dict, b: dict, min_examples: int, out_path: str) -> int:
    """assoc-nb v3: raw counts of the ILSI fit (a) and the ILSIC-Lay fit (b) added, no weighting; sections with min_examples or more in the union."""
    try:
        held = {i["id"] for i in json.loads(Path(a["holdout_set"]).read_text())["items"]}
        space = bench.load_space(a["labels"])
        ilsi, ilsi_held = _ilsi_read(a["train"], held, space)
        train, kept, drop, other_act, absent = _lay_read(b["train"], b["holdout_split"], b["holdout_set"], b["index"])
        ilsi = [(c - NOT_OFFENCES, t) for c, t in ilsi]
        ilsi_drop = {"held_out": ilsi_held, "no_offence_section": sum(not c for c, _ in ilsi)}
        lay = [(c, tokens(train[n]["instruction"])) for n, c in kept]
        ilsi = [(c, t) for c, t in ilsi if c]
        vocab, docs, counts = _vocab((c for c, _ in ilsi + lay), min_examples)
        fitted = []
        for examples, dropped in ((ilsi, ilsi_drop), (lay, drop)):
            dropped["none_above_threshold"] = used = 0
            for c, t in examples:
                if kept_c := c & vocab:
                    used += 1
                    _add(docs, counts, kept_c, t)
                else:
                    dropped["none_above_threshold"] += 1
            fitted.append(used)
    except (OSError, KeyError, ValueError, TypeError, sqlite3.Error, lzma.LZMAError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    header = {"layer": LAYER, "layer_version": "v3", "top_k": TOP_K, "min_examples": min_examples, "vocabulary_size": len(vocab),
              "sources": {"ilsi": {"train_sha256": bench.sha256(a["train"]), "examples_used": fitted[0], "examples_dropped": ilsi_drop},
                          "ilsic-lay": {"train_sha256": bench.sha256(b["train"]), "holdout_split_sha256": bench.sha256(b["holdout_split"]),
                                        "examples_used": fitted[1], "examples_dropped": drop,
                                        "other_act_citations_dropped": other_act, "index_absent_citations_dropped": absent}},
              "tokenisation": "lower-case, letters only, 44 base stop words, no stemming"}
    Path(out_path).write_text(json.dumps({"header": header, "docs": docs, "counts": counts}, sort_keys=True, separators=(",", ":")) + "\n")
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
    h = model.header
    union = h["layer_version"] == "v3"  # the union header holds one train hash per source
    train = {f"train_sha256_{k}": v["train_sha256"] for k, v in h["sources"].items()} if union else {"train_sha256": h["train_sha256"]}
    doc = {"layer": LAYER, "layer_version": h["layer_version"], "set_sha256": hashlib.sha256(raw).hexdigest(),
           "inputs": {"model": model.sha256, **train, "concordance": bench.sha256(concordance_path),
                      "train_source": "ilsi+ilsic-lay" if union else {"v2": "ilsic-lay"}.get(h["layer_version"], "ilsi")}, "items": out}
    Path(out_path).write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    return 0


def evaluate(model_path: str, split_path: str, manifest_path: str, ledger_path: str, rescore: bool, out_path: str | None,
             labels_path: str | None = None) -> int:
    """Score a split with the benchmark's own scorer. The pinned test split is scored once per layer version, in its own ledger.

    With labels_path (ILSI's full label vocabulary, v1's space) the micro-F1 is also given over that space beside the model's own."""
    try:
        model = Model(model_path)
        version = model.header["layer_version"]
        sha = bench.sha256(split_path)
        try:
            pinned = bench.pinned_test_hash(manifest_path)
        except (OSError, ValueError):
            pinned = None
        on_test = Path(split_path).stem == "test" or sha == pinned
        prior = [e for e in bench.read_ledger(ledger_path)
                 if e["layer"] == LAYER and e["layer_version"] == version and e["split_sha256"] == sha]
        if on_test and prior and not rescore:
            raise ValueError("the test split was already scored for this layer version; pass --rescore-test to score it again")
        space = set(model.labels)
        wide = bench.load_space(labels_path) if labels_path else space
        cases, gold = bench.load_cases(split_path, wide)
    except (OSError, KeyError, ValueError, TypeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    preds = [set(model.predict(" ".join(c["text"]))) for c in cases]
    res = {"layer": LAYER, "layer_version": version, "k": TOP_K, "model_sha256": model.sha256, "split_sha256": sha,
           "cases": len(cases), "scores": bench.score(gold, preds, space)}
    if labels_path:
        res["micro_f1_by_label_space"] = {"own": {"labels": len(space), "micro_f1": res["scores"]["micro_f1"]},
                                          "v1": {"labels": len(wide), "micro_f1": bench.score(gold, preds, wide)["micro_f1"]}}
    if on_test:
        entry = {k: res[k] for k in ("layer", "layer_version", "model_sha256", "split_sha256", "cases", "scores", "micro_f1_by_label_space") if k in res}
        Path(ledger_path).write_text(json.dumps(bench.read_ledger(ledger_path) + [entry], indent=2, sort_keys=True) + "\n")
        res["test_scores"] = prior + [entry]
    text = json.dumps(res, indent=2, sort_keys=True) + "\n"
    if out_path:
        Path(out_path).write_text(text)
    print(text, end="")
    return 0
