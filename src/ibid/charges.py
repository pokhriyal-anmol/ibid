"""`ibid charges validate`: refuse a multi-charge test set file that breaks its format rules."""
import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from ibid import bench, bm25, index
from ibid.cli import pin_error

AUTHOR_TYPES = ("lawyer", "owner", "judgment-excerpt", "forum-post")
LABEL_BASES = ("lawyer", "agent-drafted-skeptic-refuted", "agent-checked-for-owner", "lawyer-answer-extracted")
TOP_FIELDS = ("version", "created", "licence_note", "label_policy")
ACTS = ("ipc", "bns")


def _text(v: object) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _citation_error(db: sqlite3.Connection, act: str, c: object) -> str | None:
    if not isinstance(c, str) or not c.startswith(act.upper() + " "):
        return f"{c!r} is not an {act.upper()} citation"
    return f"{c!r} is not in the index" if index.lookup(db, c) is None else None


def _item_errors(item: dict, db: sqlite3.Connection) -> list[tuple[str, str]]:
    """(field, message) for each rule the item breaks."""
    bad = []
    for f in ("query", "source", "reviewed_by"):
        if not _text(item.get(f)):
            bad.append((f, "missing or empty"))
    if item.get("author_type") not in AUTHOR_TYPES:
        bad.append(("author_type", f"must be one of {', '.join(AUTHOR_TYPES)}, got {item.get('author_type')!r}"))
    if item.get("label_basis") not in LABEL_BASES:
        bad.append(("label_basis", f"must be one of {', '.join(LABEL_BASES)}, got {item.get('label_basis')!r}"))
    if item.get("anonymised") is not True:
        bad.append(("anonymised", "must be true"))
    charges = item.get("charges")
    if not isinstance(charges, list) or not charges:
        return bad + [("charges", "must be a non-empty list")]
    for n, ch in enumerate(charges):
        where = f"charges[{n}]"
        if not isinstance(ch, dict) or not _text(ch.get("charge")):
            bad.append((f"{where}.charge", "missing or empty"))
        secs = ch.get("sections") if isinstance(ch, dict) else None
        if not isinstance(secs, dict) or any(not isinstance(secs.get(a), list) for a in ACTS):
            bad.append((f"{where}.sections", "must be an object with a list for ipc and for bns"))
            continue
        if not secs["ipc"] and not secs["bns"]:
            bad.append((f"{where}.sections", "no accepted section in either Act"))
        for act in ACTS:
            bad += [(f"{where}.sections.{act}", m) for c in secs[act] if (m := _citation_error(db, act, c))]
    return bad


def validate(set_path: str, index_path: str) -> int:
    try:
        raw, items, _ = _load_set(set_path, index_path)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    data = json.loads(raw)
    problems = [("<file>", f, "missing or empty") for f in TOP_FIELDS if not _text(data.get(f))]
    seen = Counter(i.get("id") for i in items)
    for n, item in enumerate(items):
        iid = item.get("id")
        if not _text(iid):
            problems.append((f"#{n}", "id", "missing or empty"))
        elif seen[iid] > 1:
            problems.append((iid, "id", "duplicate"))
    if problems:
        for iid, field, msg in problems:
            print(f"item {iid} field {field}: {msg}", file=sys.stderr)
        return 1
    hist = Counter(min(len(i["charges"]), 3) for i in items)
    cites = {a: {c for i in items for ch in i["charges"] for c in ch["sections"][a]} for a in ACTS}
    bases = Counter(i["label_basis"] for i in items)
    print(f"items: {len(items)}")
    print("charges per item: " + ", ".join(f"{k if k < 3 else '3 or more'}: {hist[k]}" for k in (1, 2, 3)))
    print("distinct sections: " + ", ".join(f"{a.upper()} {len(cites[a])}" for a in ACTS))
    print("label_basis: " + ", ".join(f"{b}: {bases[b]}" for b in LABEL_BASES))
    return 0


def _summary(rows: list[tuple[list[bool], int]]) -> dict:
    """rows: per scored item, (found flag per counted charge, predictions made). An empty group scores 0."""
    n, hit = len(rows), sum(sum(f) for f, _ in rows)
    charges = sum(len(f) for f, _ in rows)
    return {"items": n, "charges": charges, "recall": round(hit / charges, 6) if charges else 0.0,
            "all_charges_hit": round(sum(all(f) for f, _ in rows) / n, 6) if n else 0.0,
            "mean_predictions": round(sum(p for _, p in rows) / n, 6) if n else 0.0}


def _load_set(set_path: str, index_path: str) -> tuple[bytes, list, sqlite3.Connection]:
    """The pinned set's bytes and items, and a read-only index; every item is checked against the format rules."""
    raw = Path(set_path).read_bytes()
    if err := pin_error(set_path, raw):
        raise ValueError(err)
    if not Path(index_path).is_file():
        raise ValueError(f"no index {index_path}")
    try:
        items = json.loads(raw)["items"]
        if not (isinstance(items, list) and items and all(isinstance(i, dict) for i in items)):
            raise TypeError
    except (ValueError, KeyError, TypeError):
        raise ValueError("file is not an object with a non-empty `items` list of objects") from None
    db = sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)  # read-only: nothing here writes
    problems = [f"item {i.get('id')} field {f}: {m}" for i in items for f, m in _item_errors(i, db)]
    if problems:
        raise ValueError("\n".join(problems))
    return raw, items, db


def _load_rule(frozen_path: str) -> tuple[dict, dict]:
    fz = json.loads(Path(frozen_path).read_text())
    k, r, rollup, stop, knobs = fz["k"], fz["r"], fz["section_score"], fz["stop_words"], bench.knobs_of(fz.get("knobs"))
    bench.check_params(k, r, rollup)
    bench.check_knobs(knobs)
    if fz["rule"]["params_sha256"] != bench.rule_hash(k, r, rollup, stop, knobs):
        raise ValueError(f"{frozen_path} does not hold the rule it names")
    return fz, {"k": k, "r": r, "rollup": rollup, "stop": stop, "knobs": knobs}


def _space(ix: bm25.Index, act: str) -> set[str]:
    return {c for c, p in ix.parent.items() if p is None and c.startswith(act.upper() + " ")}  # every section of the Act


def _frozen_predict(ix: bm25.Index, rule: dict, space: set[str], query: str) -> dict[str, list[str]]:
    top_k, above = bench.predict(bench.rank_sections(ix, query, space, rule["rollup"], rule["stop"], rule["knobs"]), rule["k"], rule["r"])
    return {"top_k": top_k, "threshold": above}


def _score_output(items: list, act: str, preds: dict[str, list[str]], ix: bm25.Index) -> tuple[dict, int]:
    """The one scorer: figures for one output over one Act, and the charges left out. A missing item has no predictions."""
    def section(c: str) -> str:  # an accepted sub-provision is found when its section is predicted
        while ix.parent[c] is not None:
            c = ix.parent[c]
        return c

    excluded, rows, missed, kept = 0, [], [], {}
    for item in items:
        counted = [ch for ch in item["charges"] if ch["sections"][act]]
        excluded += len(item["charges"]) - len(counted)
        if not counted:
            continue
        pred = preds.get(item["id"], [])
        kept[item["id"]] = pred
        found = {section(c) for c in pred}
        flags = [any(section(c) in found for c in ch["sections"][act]) for ch in counted]
        rows.append((flags, len(pred)))
        missed += [{"id": item["id"], "charge": ch["charge"], "top_predicted": pred[:3]} for ch, f in zip(counted, flags) if not f]
    by_n = {lbl: _summary([x for x in rows if min(len(x[0]), 3) == n]) for lbl, n in (("1", 1), ("2", 2), ("3+", 3))}
    return {**_summary(rows), "by_charges_per_item": by_n, "missed": missed, "predictions": kept}, excluded


def _predictions_error(path: str, data: object, set_sha: str, item_ids: set, db: sqlite3.Connection) -> list[str]:
    """Each rule the predictions file breaks, naming the item and field."""
    if not isinstance(data, dict):
        return [f"{path} field <file>: not an object"]
    bad = [f"{path} field {f}: missing or empty" for f in ("layer", "layer_version") if not _text(data.get(f))]
    if data.get("set_sha256") != set_sha:
        bad.append(f"{path} field set_sha256: {data.get('set_sha256')!r} is not the hash of the set file")
    if not isinstance(data.get("inputs"), dict):
        bad.append(f"{path} field inputs: must be an object of name to sha256")
    items = data.get("items")
    if not isinstance(items, dict):
        return bad + [f"{path} field items: must be an object"]
    for iid, entry in items.items():
        if iid not in item_ids:
            bad.append(f"item {iid} field id: not in the set")
            continue
        for act in ACTS:
            cites = entry.get(act) if isinstance(entry, dict) else None
            if not isinstance(cites, list):
                bad.append(f"item {iid} field {act}: must be a list of citations")
                continue
            bad += [f"item {iid} field {act}: {m}" for c in cites if (m := _citation_error(db, act, c))]
    return bad


def _write_ledger(ledger_file: str, entry: dict) -> list:
    ledger = bench.read_ledger(ledger_file)
    if entry not in ledger:  # an identical rescoring adds nothing, so two identical runs write identical files
        ledger.append(entry)
        Path(ledger_file).write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")
    return ledger


CONVENTIONS = {
    "found": "a charge is found when any accepted section of the Act, rolled up to its section, is predicted",
    "excluded": "a charge with an empty list for the Act is left out; an item with none left is not scored",
    "by_charges_per_item": "grouped by the number of charges counted for the Act, not the total in the item",
    "mean_predictions": "mean number of predicted sections per scored item",
}
FIGURES = ("recall", "all_charges_hit", "mean_predictions")


def score_predictions(set_path: str, index_path: str, predictions_path: str, act: str, out_path: str, ledger_path: str | None = None) -> int:
    """`ibid charges score --predictions`: any layer's predictions file, scored by the same function as the frozen rule."""
    try:
        raw, items, db = _load_set(set_path, index_path)
        data = json.loads(Path(predictions_path).read_text())
        set_sha = hashlib.sha256(raw).hexdigest()
        if bad := _predictions_error(predictions_path, data, set_sha, {i["id"] for i in items}, db):
            raise ValueError("\n".join(bad))
    except (OSError, KeyError, ValueError, TypeError, AttributeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    ix = bm25.Index(db, bench.DEFAULT_KNOBS["levels"], bench.DEFAULT_KNOBS["stem"])
    out, excluded = _score_output(items, act, {i: e[act] for i, e in data["items"].items()}, ix)
    layer, version = data["layer"], data["layer_version"]
    entry = {"set_sha256": set_sha, "act": act.upper(), "index_sha256": bench.sha256(index_path), "layer": layer,
             "layer_version": version, "inputs": data["inputs"], "scores": {"output": {m: out[m] for m in FIGURES}}}
    ledger = _write_ledger(ledger_path or str(Path(set_path).with_suffix(".ledger.json")), entry)
    results = {
        "inputs": {"set_sha256": set_sha, "index_sha256": entry["index_sha256"], "layer": data["inputs"]},
        "act": act.upper(), "layer": layer, "layer_version": version, "parser_version": bench.PARSER_VERSION,
        "items_in_set": len(items), "items_scored": out["items"], "charges_excluded_no_counterpart": excluded,
        "label_basis": dict(sorted(Counter(i["label_basis"] for i in items).items())),
        "output": out, "layer_counts": data["counts"] if isinstance(data.get("counts"), dict) else {},
        "scorings_of_this_layer_version": [e for e in ledger if e.get("layer") == layer and e.get("layer_version") == version
                                           and e["set_sha256"] == set_sha and e["act"] == entry["act"]],
        "conventions": CONVENTIONS,
    }
    Path(out_path).write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    return 0


def export_baseline(set_path: str, index_path: str, frozen_path: str, out_path: str) -> int:
    """`ibid charges export-baseline`: the frozen rule's two output rules as two predictions files, <out stem>.<layer><suffix>."""
    try:
        raw, items, db = _load_set(set_path, index_path)
        fz, rule = _load_rule(frozen_path)
    except (OSError, KeyError, ValueError, TypeError, AttributeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    ix = bm25.Index(db, rule["knobs"]["levels"], rule["knobs"]["stem"])
    spaces = {a: _space(ix, a) for a in ACTS}
    out = {"top_k": {}, "threshold": {}}
    for item in items:
        for a in ACTS:
            for name, pred in _frozen_predict(ix, rule, spaces[a], item["query"]).items():
                out[name].setdefault(item["id"], {})[a] = pred
    o = Path(out_path)
    for name, layer in (("top_k", "baseline-topk"), ("threshold", "baseline-threshold")):
        doc = {"layer": layer, "layer_version": fz["rule"]["version"], "set_sha256": hashlib.sha256(raw).hexdigest(),
               "inputs": {"frozen_rule_params": fz["rule"]["params_sha256"], "index": bench.sha256(index_path)}, "items": out[name]}
        o.with_name(f"{o.stem}.{layer}{o.suffix}").write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    return 0


def score(set_path: str, index_path: str, frozen_path: str, act: str, out_path: str, ledger_path: str | None = None) -> int:
    """`ibid charges score`: the frozen rule, by charge, over one Act's sections (any index section can be predicted)."""
    try:
        raw, items, db = _load_set(set_path, index_path)
        fz, rule = _load_rule(frozen_path)
    except (OSError, KeyError, ValueError, TypeError, AttributeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    ix = bm25.Index(db, rule["knobs"]["levels"], rule["knobs"]["stem"])
    space = _space(ix, act)
    per_item = {i["id"]: _frozen_predict(ix, rule, space, i["query"]) for i in items if any(c["sections"][act] for c in i["charges"])}
    scored = {name: _score_output(items, act, {i: p[name] for i, p in per_item.items()}, ix) for name in ("top_k", "threshold")}
    outputs, excluded = {n: o for n, (o, _) in scored.items()}, scored["top_k"][1]
    version = fz["rule"]["version"]
    entry = {"set_sha256": hashlib.sha256(raw).hexdigest(), "act": act.upper(), "index_sha256": bench.sha256(index_path),
             "rule": {"name": fz["rule"]["name"], "version": version, "params_sha256": fz["rule"]["params_sha256"]},
             "scores": {n: {m: outputs[n][m] for m in FIGURES} for n in outputs}}
    ledger = _write_ledger(ledger_path or str(Path(set_path).with_suffix(".ledger.json")), entry)
    results = {
        "inputs": {k_: entry[k_] for k_ in ("set_sha256", "index_sha256")},
        "act": act.upper(), "rule": entry["rule"], "k": rule["k"], "r": rule["r"], "section_score": rule["rollup"], "knobs": rule["knobs"],
        "parser_version": bench.PARSER_VERSION,
        "items_in_set": len(items), "items_scored": outputs["top_k"]["items"], "charges_excluded_no_counterpart": excluded,
        "label_basis": dict(sorted(Counter(i["label_basis"] for i in items).items())),
        "top_k": outputs["top_k"], "threshold": outputs["threshold"],
        "scorings_of_this_rule_version": [e for e in ledger if e.get("rule", {}).get("version") == version
                                          and e["set_sha256"] == entry["set_sha256"] and e["act"] == entry["act"]],
        "conventions": CONVENTIONS,
    }
    Path(out_path).write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    return 0


def subquery(set_path: str, subq_path: str, index_path: str, frozen_path: str, per_subquery: int, out_path: str) -> int:
    """`ibid charges subquery` (route C): the frozen rule's top sections for each recorded sub-query, unioned per item."""
    try:
        raw, items, db = _load_set(set_path, index_path)
        fz, rule = _load_rule(frozen_path)
        sraw = Path(subq_path).read_bytes()
        if err := pin_error(subq_path, sraw):
            raise ValueError(err)
        data, set_sha = json.loads(sraw), hashlib.sha256(raw).hexdigest()
        if not isinstance(data, dict) or not isinstance(data.get("items"), dict):
            raise ValueError(f"{subq_path} field items: must be an object")
        if not _text(data.get("producer")):
            raise ValueError(f"{subq_path} field producer: missing or empty")
        if data.get("set_sha256") != set_sha:
            raise ValueError(f"{subq_path} field set_sha256: {data.get('set_sha256')!r} is not the hash of the set file")
        if isinstance(per_subquery, bool) or not isinstance(per_subquery, int) or per_subquery < 1:
            raise ValueError("--per-subquery must be a positive integer")
        ids = {i["id"] for i in items}
        for iid, qs in data["items"].items():
            if iid not in ids:
                raise ValueError(f"item {iid} field id: not in the set")
            if not isinstance(qs, list) or not all(_text(q) for q in qs):
                raise ValueError(f"item {iid} field subqueries: must be a list of non-empty strings")
    except (OSError, KeyError, ValueError, TypeError, AttributeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    ix = bm25.Index(db, rule["knobs"]["levels"], rule["knobs"]["stem"])
    spaces = {a: _space(ix, a) for a in ACTS}
    out = {iid: {a: sorted({c for q in qs for c, _ in bench.rank_sections(ix, q, spaces[a], rule["rollup"], rule["stop"], rule["knobs"])[:per_subquery]})
                 for a in ACTS} for iid, qs in data["items"].items()}  # no sub-queries, no predictions
    doc = {"layer": "decomposed", "layer_version": "v1", "set_sha256": set_sha,
           "inputs": {"producer": data["producer"], "subqueries_sha256": hashlib.sha256(sraw).hexdigest(), "per_subquery": per_subquery,
                      "frozen_rule_params": fz["rule"]["params_sha256"], "index": bench.sha256(index_path)},
           "counts": {"subqueries_per_item_mean": round(sum(map(len, data["items"].values())) / len(data["items"]), 2) if data["items"] else 0.0},
           "items": out}
    Path(out_path).write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    return 0


MIN_WORDS = 20
SECTION_NUMBER = re.compile(r"(\b(sections?|secs?|s|u/s|ipc|bns)\.?\s*\d+)|(\b\d+\s*(ipc|bns)\b)", re.I)  # shortcut: keyword-led numbers only, a bare "302" passes


def intake(queries_path: str, author_type: str, author: str, out_path: str) -> int:
    """`ibid charges intake`: turn person-written query blocks into a draft set that fails validate until labelled."""
    try:
        text = Path(queries_path).read_text()
    except (OSError, UnicodeDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    lines = text.splitlines()
    while lines and (lines[0].startswith("#") or not lines[0].strip()):
        lines.pop(0)  # header comment
    blocks = [b.strip() for b in re.split(r"(?m)^---[ \t]*$", "\n".join(lines))]
    problems, seen = [], set()
    for n, b in enumerate(blocks, 1):
        key = " ".join(b.lower().split())
        if not b:
            problems.append(f"block {n}: empty")
        elif len(b.split()) < MIN_WORDS:
            problems.append(f"block {n}: {len(b.split())} words, need at least {MIN_WORDS}")
        elif SECTION_NUMBER.search(b):
            problems.append(f"block {n}: contains what looks like a section number ({SECTION_NUMBER.search(b).group(0)!r})")
        elif key in seen:
            problems.append(f"block {n}: duplicate of an earlier block")
        seen.add(key)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    items = [{"id": f"d-{n:03d}", "query": b, "author_type": author_type, "source": f"{author_type}-written, author {author}",
              "anonymised": True, "charges": []} for n, b in enumerate(blocks, 1)]
    data = {"version": "draft", "created": date.today().isoformat(), "licence_note": f"queries written by {author}",
            "label_policy": "draft: charges, label_basis and reviewed_by are not set yet", "items": items}
    Path(out_path).write_text(json.dumps(data, indent=2) + "\n")
    print(f"wrote {len(items)} draft items to {out_path}")
    return 0
