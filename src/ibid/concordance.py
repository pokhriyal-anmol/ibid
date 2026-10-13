"""Concordance loader and two-way lookup. Only `verified: true` entries are served.

File format: a JSON list of {"ipc": [citation], "bns": [citation], "type": ..., "verified": bool}.
`removed` has an empty "bns" list and `new` has an empty "ipc" list.
"""
import json
import sqlite3

NONE = "no verified concordance"
TYPES = {"one-to-one", "split", "merged", "removed", "new"}
BASES = {"human-checked", "agent-checked-for-owner", "refuted-by-agent", "source-table-checked"}


def load(path: str, db: sqlite3.Connection) -> list[dict]:
    """Raises ValueError if any entry is malformed or names a citation absent from the index."""
    with open(path) as f:
        entries = json.load(f)
    known = {c for (c,) in db.execute("SELECT citation FROM provision")}
    for i, e in enumerate(entries):
        if e.get("type") not in TYPES or not isinstance(e.get("verified"), bool):
            raise ValueError(f"concordance entry {i}: bad type or verified flag")
        if e.get("basis", "human-checked") not in BASES:
            raise ValueError(f"concordance entry {i}: unknown basis {e['basis']!r}")
        if (e["type"] == "removed" and e["bns"]) or (e["type"] == "new" and e["ipc"]):
            raise ValueError(f"concordance entry {i}: {e['type']} entry names a successor or ancestor")
        if not all(c.startswith("IPC ") for c in e["ipc"]) or not all(c.startswith("BNS ") for c in e["bns"]):
            raise ValueError(f"concordance entry {i}: citation on the wrong side")
        for c in e["ipc"] + e["bns"]:
            if c not in known:
                raise ValueError(f"concordance entry {i}: {c!r} is not in the index")
    return entries


def lookup(entries: list[dict], citation: str, src: str, dst: str) -> list[dict] | str:
    """src/dst are "ipc"/"bns". Verified entries naming `citation`, in file order, else NONE."""
    hits = [{"type": e["type"], "citations": e[dst]} for e in entries if e["verified"] and citation in e[src]]
    return hits or NONE
