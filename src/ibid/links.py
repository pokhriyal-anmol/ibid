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


def ipc_pairs(db: sqlite3.Connection) -> list[tuple[str, str]]:
    rows = db.execute("SELECT citation, text FROM provision WHERE parent IS NULL AND citation LIKE 'IPC %'").fetchall()
    by_heading: dict[str, list[str]] = {}
    for c, t in rows:
        by_heading.setdefault(_heading(t), []).append(c)
    pairs = {tuple(sorted((c, d), key=_order))
             for c, t in rows if (h := _heading(t)).startswith(PREFIX)
             for d in by_heading.get(h[len(PREFIX):], []) if d != c}
    return sorted(pairs, key=lambda p: (_order(p[0]), _order(p[1])))


def bns_pairs(entries: list[dict], ipc: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Carry each IPC pair to the BNS through verified entries only (`lookup` serves nothing else)."""
    def served(c: str) -> set[str]:
        hits = concordance.lookup(entries, c, "ipc", "bns")
        return set() if hits == concordance.NONE else {b for h in hits for b in h["citations"]}
    pairs = {tuple(sorted((a, b), key=_order)) for x, y in ipc for a in served(x) for b in served(y) if a != b}
    return sorted(pairs, key=lambda p: (_order(p[0]), _order(p[1])))


def list_links(db: sqlite3.Connection, entries: list[dict]) -> list[str]:
    ipc = ipc_pairs(db)
    bns = bns_pairs(entries, ipc)
    return ([f"{a} <-> {b}" for a, b in ipc] + [f"IPC pairs: {len(ipc)}"]
            + [f"{a} <-> {b}" for a, b in bns] + [f"BNS pairs: {len(bns)}"])
