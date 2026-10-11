"""Benchmark helpers: map LeSICiN label strings to IPC citations and check them against the index."""
import json
import re
import sqlite3
import sys

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
