"""Concordance loader and two-way lookup. Only `verified: true` entries are served.

File format: a JSON list of {"ipc": [citation], "bns": [citation], "type": ..., "verified": bool}.
`removed` has an empty "bns" list and `new` has an empty "ipc" list.
"""
import json
import sqlite3

NONE = "no verified concordance"
TYPES = {"one-to-one", "split", "merged", "removed", "new"}
BASES = {"human-checked", "agent-checked-for-owner", "refuted-by-agent", "source-table-checked"}
PREFIX = {"ipc": "IPC ", "bns": "BNS ", "crpc": "CrPC ", "bnss": "BNSS "}


def load(path: str, db: sqlite3.Connection, old: str = "ipc", new: str = "bns") -> list[dict]:
    """`old` and `new` name the two sides: ipc and bns, or crpc and bnss. Raises ValueError if any entry is malformed or names a citation absent from the index."""
    with open(path) as f:
        entries = json.load(f)
    known = {c for (c,) in db.execute("SELECT citation FROM provision")}
    for i, e in enumerate(entries):
        if not isinstance(e, dict) or not all(isinstance(e.get(side), list) for side in (old, new)):
            raise ValueError(f"concordance entry {i}: not an object with {old} and {new} lists")
        if e.get("type") in ("one-to-one", "split", "merged") and not (e[old] and e[new]):
            raise ValueError(f"concordance entry {i}: a {e['type']} entry needs both {old} and {new} citations")
        if e.get("type") not in TYPES or not isinstance(e.get("verified"), bool):
            raise ValueError(f"concordance entry {i}: bad type or verified flag")
        if e.get("basis", "human-checked") not in BASES:
            raise ValueError(f"concordance entry {i}: unknown basis {e['basis']!r}")
        if (e["type"] == "removed" and e[new]) or (e["type"] == "new" and e[old]):
            raise ValueError(f"concordance entry {i}: {e['type']} entry names a successor or ancestor")
        if not all(c.startswith(PREFIX[old]) for c in e[old]) or not all(c.startswith(PREFIX[new]) for c in e[new]):
            raise ValueError(f"concordance entry {i}: citation on the wrong side")
        for c in e[old] + e[new]:
            if c not in known:
                raise ValueError(f"concordance entry {i}: {c!r} is not in the index")
    return entries


def lookup(entries: list[dict], citation: str, src: str, dst: str) -> list[dict] | str:
    """src/dst are "ipc"/"bns" or "crpc"/"bnss". Verified entries naming `citation`, in file order, else NONE."""
    hits = [{"type": e["type"], "citations": e[dst]} for e in entries if e["verified"] and citation in e[src]]
    return hits or NONE
