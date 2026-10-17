"""Definition-punishment links derived from IPC section headings (slice 7, ADR 0007).

A section headed "Punishment for X" links, both ways, to every other top-level section headed exactly X
after lowercasing, trimming and stripping one trailing full stop. Nothing else makes a link.
"""
import re
import sqlite3

from ibid import concordance

PREFIX = "punishment for "


def _heading(text: str) -> str:
    """The title of `N. Title.—body`: the first line up to the em dash, number dropped, normalised."""
    title = re.sub(r"^\S+\s+", "", text.split("\n")[0].split("—")[0]).strip().lower()
    return title[:-1] if title.endswith(".") else title


def _order(citation: str) -> tuple[int, str]:
    m = re.match(r"\w+ (\d+)(.*)", citation)
    return int(m[1]), m[2]


def _pairs(ab) -> list[tuple[str, str]]:
    pairs = {tuple(sorted(p, key=_order)) for p in ab}
    return sorted(pairs, key=lambda p: (_order(p[0]), _order(p[1])))


def ipc_pairs(db: sqlite3.Connection) -> list[tuple[str, str]]:
    rows = db.execute("SELECT citation, text FROM provision WHERE parent IS NULL AND citation LIKE 'IPC %'").fetchall()
    by_heading: dict[str, list[str]] = {}
    for c, t in rows:
        by_heading.setdefault(_heading(t), []).append(c)
    return _pairs((c, d) for c, t in rows if (h := _heading(t)).startswith(PREFIX)
                  for d in by_heading.get(h[len(PREFIX):], []) if d != c)


def bns_pairs(entries: list[dict], ipc: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Carry each IPC pair to the BNS through verified entries only (`lookup` serves nothing else)."""
    def served(c: str) -> set[str]:
        hits = concordance.lookup(entries, c, "ipc", "bns")
        return set() if hits == concordance.NONE else {b for h in hits for b in h["citations"]}
    return _pairs((a, b) for x, y in ipc for a in served(x) for b in served(y) if a != b)


def list_links(db: sqlite3.Connection, entries: list[dict]) -> list[str]:
    ipc = ipc_pairs(db)
    bns = bns_pairs(entries, ipc)
    return ([f"{a} <-> {b}" for a, b in ipc] + [f"IPC pairs: {len(ipc)}"]
            + [f"{a} <-> {b}" for a, b in bns] + [f"BNS pairs: {len(bns)}"])


def partners(pairs: list[tuple[str, str]]) -> dict[str, list[str]]:
    """Linked partners of each section, in citation order."""
    out: dict[str, list[str]] = {}
    for a, b in pairs:
        out.setdefault(a, []).append(b)
        out.setdefault(b, []).append(a)
    return {c: sorted(v, key=_order) for c, v in out.items()}


def expand(predicted: list[str], links: dict[str, list[str]]) -> list[str]:
    """The originals in their order, then each one's partners in rank order, none twice."""
    out = list(predicted)
    for c in predicted:
        out += [p for p in links.get(c, []) if p not in out]
    return out


def bench(split_path: str, labels_path: str, index_path: str, manifest_path: str, frozen_path: str,
          ledger_path: str, rescore: bool, out_path: str) -> int:
    """Score `links v1` on an ILSI split with the frozen rule's ranking and the benchmark's scorer.

    The pinned test split is scored once per layer version, in its own ledger."""
    import hashlib
    import json
    import sys
    from pathlib import Path

    from ibid import bench as b, bm25
    try:
        frozen_bytes = Path(frozen_path).read_bytes()
        fr = json.loads(frozen_bytes)
        k, r, rollup, stop, knobs = fr["k"], fr["r"], fr["section_score"], fr["stop_words"], b.knobs_of(fr.get("knobs"))
        if fr["rule"]["params_sha256"] != b.rule_hash(k, r, rollup, stop, knobs):
            raise ValueError(f"{frozen_path} does not hash to the rule it records")
        if b.verify_pinned([split_path, labels_path], manifest_path):
            return 1
        sha = b.sha256(split_path)
        on_test = Path(split_path).stem == "test" or sha == b.pinned_test_hash(manifest_path)
        prior = [e for e in b.read_ledger(ledger_path)
                 if e["layer"] == "links" and e["layer_version"] == "v1" and e["split_sha256"] == sha]
        if on_test and prior and not rescore:
            raise ValueError("the test split was already scored for this layer version; pass --rescore-test to score it again")
        space = b.load_space(labels_path)
        cases, gold = b.load_cases(split_path, space)
    except (OSError, KeyError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    db = sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)
    pairs = ipc_pairs(db)
    links = partners(pairs)
    ix = bm25.Index(db, knobs["levels"], knobs["stem"])
    ranked = [b.rank_sections(ix, " ".join(c["text"]), space, rollup, stop, knobs) for c in cases]
    base = dict(zip(("top-k", "threshold"), zip(*(b.predict(x, k, r) for x in ranked))))
    outputs = {}
    for name, preds in base.items():
        expanded = [expand(p, links) for p in preds]
        outputs[name] = {"scores": b.score(gold, [set(p) for p in expanded], space),
                         "mean_predictions": round(sum(map(len, expanded)) / len(cases), 4)}
    res = {"layer": "links", "layer_version": "v1", "k": k, "r": r, "cases": len(cases), "split_sha256": sha,
           "frozen_rule_sha256": hashlib.sha256(frozen_bytes).hexdigest(), "rule_params_sha256": fr["rule"]["params_sha256"],
           "link_set_sha256": hashlib.sha256(json.dumps(pairs).encode()).hexdigest(), "outputs": outputs}
    if on_test:
        entry = {x: res[x] for x in ("layer", "layer_version", "frozen_rule_sha256", "link_set_sha256", "split_sha256", "cases", "outputs")}
        Path(ledger_path).write_text(json.dumps(b.read_ledger(ledger_path) + [entry], indent=2, sort_keys=True) + "\n")
        res["test_scores"] = prior + [entry]
    Path(out_path).write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
    return 0


def expand_file(predictions_path: str, index_path: str, concordance_path: str, out_path: str) -> int:
    """`ibid links expand`: a baseline predictions file in, a `links v1` predictions file out. Reads the file; never ranks."""
    import json
    import sys
    from pathlib import Path

    from ibid import bench
    try:
        data = json.loads(Path(predictions_path).read_bytes())
        db = sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)
        ipc = ipc_pairs(db)
        links = {"ipc": partners(ipc), "bns": partners(bns_pairs(concordance.load(concordance_path, db), ipc))}
        items = {i: {a: expand(p, links[a]) for a, p in acts.items()} for i, acts in data["items"].items()}
        doc = {"layer": "links", "layer_version": "v1", "set_sha256": data["set_sha256"],
               "inputs": {"baseline": bench.sha256(predictions_path), "baseline_layer": data["layer"], "index": bench.sha256(index_path),
                          "concordance": bench.sha256(concordance_path)}, "items": items}
    except (OSError, KeyError, ValueError, TypeError, AttributeError, sqlite3.Error) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    Path(out_path).write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    return 0
