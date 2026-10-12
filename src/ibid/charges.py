"""`ibid charges validate`: refuse a multi-charge test set file that breaks its format rules."""
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

from ibid import index
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
