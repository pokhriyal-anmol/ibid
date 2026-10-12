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

AUTHOR_TYPES = ("lawyer", "owner", "judgment-excerpt")
LABEL_BASES = ("lawyer", "agent-drafted-skeptic-refuted", "agent-checked-for-owner")
TOP_FIELDS = ("version", "created", "licence_note", "label_policy")
ACTS = ("ipc", "bns")


def _text(v: object) -> bool:
    return isinstance(v, str) and bool(v.strip())


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
            for c in secs[act]:
                if not isinstance(c, str) or not c.startswith(act.upper() + " "):
                    bad.append((f"{where}.sections.{act}", f"{c!r} is not an {act.upper()} citation"))
                elif index.lookup(db, c) is None:
                    bad.append((f"{where}.sections.{act}", f"{c!r} is not in the index"))
    return bad


def validate(set_path: str, index_path: str) -> int:
    raw = Path(set_path).read_bytes()
    if err := pin_error(set_path, raw):
        print(f"error: {err}", file=sys.stderr)
        return 1
    if not Path(index_path).is_file():
        print(f"error: no index {index_path}", file=sys.stderr)
        return 1
    try:
        data = json.loads(raw)
        items = data["items"]
        assert isinstance(items, list) and items
    except (ValueError, KeyError, TypeError, AssertionError):
        print("error: file is not an object with a non-empty `items` list", file=sys.stderr)
        return 1
    db = sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)  # read-only: validate never writes
    problems = [("<file>", f, "missing or empty") for f in TOP_FIELDS if not _text(data.get(f))]
    seen = Counter(i.get("id") if isinstance(i, dict) else None for i in items)
    for n, item in enumerate(items):
        if not isinstance(item, dict):
            problems.append((f"#{n}", "<item>", "not an object"))
            continue
        iid = item.get("id")
        name = iid if _text(iid) else f"#{n}"
        if not _text(iid):
            problems.append((name, "id", "missing or empty"))
        elif seen[iid] > 1:
            problems.append((name, "id", "duplicate"))
        problems += [(name, f, m) for f, m in _item_errors(item, db)]
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


def score(set_path: str, index_path: str, frozen_path: str, act: str, out_path: str, ledger_path: str | None = None) -> int:
    """`ibid charges score`: the frozen rule, by charge, over one Act's sections (any index section can be predicted)."""
    raw = Path(set_path).read_bytes()
    if err := pin_error(set_path, raw):
        print(f"error: {err}", file=sys.stderr)
        return 1
    try:
        if not Path(index_path).is_file():
            raise ValueError(f"no index {index_path}")
        items = json.loads(raw)["items"]
        fz = json.loads(Path(frozen_path).read_text())
        k, r, rollup, stop, knobs = fz["k"], fz["r"], fz["section_score"], fz["stop_words"], bench.knobs_of(fz.get("knobs"))
        bench.check_params(k, r, rollup)
        bench.check_knobs(knobs)
        if fz["rule"]["params_sha256"] != bench.rule_hash(k, r, rollup, stop, knobs):
            raise ValueError(f"{frozen_path} does not hold the rule it names")
        db = sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)
        problems = [(i.get("id"), f, m) for i in items for f, m in _item_errors(i, db)]
    except (OSError, KeyError, ValueError, TypeError, AttributeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if problems:
        for iid, field, msg in problems:
            print(f"item {iid} field {field}: {msg}", file=sys.stderr)
        return 1
    ix = bm25.Index(db, knobs["levels"], knobs["stem"])
    space = {c for c, p in ix.parent.items() if p is None and c.startswith(act.upper() + " ")}  # every section of the Act

    def section(c: str) -> str:  # an accepted sub-provision is found when its section is predicted
        while ix.parent[c] is not None:
            c = ix.parent[c]
        return c

    excluded, rows, missed, preds = 0, {"top_k": [], "threshold": []}, {"top_k": [], "threshold": []}, {"top_k": {}, "threshold": {}}
    for item in items:
        counted = [ch for ch in item["charges"] if ch["sections"][act]]
        excluded += len(item["charges"]) - len(counted)
        if not counted:
            continue
        top_k, above = bench.predict(bench.rank_sections(ix, item["query"], space, rollup, stop, knobs), k, r)
        for name, pred in (("top_k", top_k), ("threshold", above)):
            preds[name][item["id"]] = pred
            flags = [any(section(c) in pred for c in ch["sections"][act]) for ch in counted]
            rows[name].append((flags, len(pred)))
            missed[name] += [{"id": item["id"], "charge": ch["charge"], "top_predicted": pred[:3]}
                             for ch, f in zip(counted, flags) if not f]
    outputs = {}
    for name in rows:
        by_n = {lbl: _summary([x for x in rows[name] if min(len(x[0]), 3) == n]) for lbl, n in (("1", 1), ("2", 2), ("3+", 3))}
        outputs[name] = {**_summary(rows[name]), "by_charges_per_item": by_n, "missed": missed[name], "predictions": preds[name]}
    version = fz["rule"]["version"]
    entry = {"set_sha256": hashlib.sha256(raw).hexdigest(), "act": act.upper(), "index_sha256": bench.sha256(index_path),
             "rule": {"name": fz["rule"]["name"], "version": version, "params_sha256": fz["rule"]["params_sha256"]},
             "scores": {n: {m: outputs[n][m] for m in ("recall", "all_charges_hit", "mean_predictions")} for n in outputs}}
    ledger_file = ledger_path or str(Path(set_path).with_suffix(".ledger.json"))
    ledger = bench.read_ledger(ledger_file)
    if entry not in ledger:  # an identical rescoring adds nothing, so two identical runs write identical files
        ledger.append(entry)
        Path(ledger_file).write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")
    results = {
        "inputs": {k_: entry[k_] for k_ in ("set_sha256", "index_sha256")},
        "act": act.upper(), "rule": entry["rule"], "k": k, "r": r, "section_score": rollup, "knobs": knobs,
        "parser_version": bench.PARSER_VERSION,
        "items_in_set": len(items), "items_scored": len(rows["top_k"]), "charges_excluded_no_counterpart": excluded,
        "label_basis": dict(sorted(Counter(i["label_basis"] for i in items).items())),
        "top_k": outputs["top_k"], "threshold": outputs["threshold"],
        "scorings_of_this_rule_version": [e for e in ledger if e["set_sha256"] == entry["set_sha256"]
                                          and e["act"] == entry["act"] and e["rule"]["version"] == version],
        "conventions": {
            "found": "a charge is found when any accepted section of the Act, rolled up to its section, is predicted",
            "excluded": "a charge with an empty list for the Act is left out; an item with none left is not scored",
            "by_charges_per_item": "grouped by the number of charges counted for the Act, not the total in the item",
            "mean_predictions": "mean number of predicted sections per scored item",
        },
    }
    Path(out_path).write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    return 0


MIN_WORDS = 20
SECTION_NUMBER = re.compile(r"(\b(section|sec|s|u/s|ipc|bns)\.?\s*\d+)|(\b\d+\s*(ipc|bns)\b)", re.I)  # shortcut: keyword-led numbers only, a bare "302" passes


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
