"""The SQLite index: one file, rebuilt from source on every run."""
import json
import os
import sqlite3

from ibid.parse import Provision
from ibid.xref import Edge, chains


def build(path: str, provisions: list[Provision], edges: list[Edge]) -> sqlite3.Connection:
    if os.path.exists(path):
        os.remove(path)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE provision (citation TEXT PRIMARY KEY, text TEXT, parent TEXT, children TEXT, refs TEXT)")
    refs = chains(provisions, edges)
    db.executemany(
        "INSERT INTO provision VALUES (?, ?, ?, ?, ?)",
        [(p.citation, p.text, p.parent, json.dumps(p.children), json.dumps(refs[p.citation])) for p in provisions],
    )
    db.execute("CREATE TABLE xref (source TEXT, matched TEXT, target TEXT, reason TEXT)")
    db.executemany("INSERT INTO xref VALUES (?, ?, ?, ?)", [(e.source, e.matched, e.target, e.reason) for e in edges])
    db.execute("CREATE VIRTUAL TABLE fts USING fts5(citation UNINDEXED, text)")
    db.executemany("INSERT INTO fts VALUES (?, ?)", [(p.citation, p.text) for p in provisions])
    db.commit()
    return db


def lookup(db: sqlite3.Connection, citation: str) -> tuple[str, list[str], list[str]] | None:
    """Verbatim text, child citations and the resolved cross-reference chain, in fixed order.
    TEXT equality is BINARY collation, i.e. a byte comparison."""
    row = db.execute("SELECT text, children, refs FROM provision WHERE citation = ?", (citation,)).fetchone()
    return (row[0], json.loads(row[1]), json.loads(row[2])) if row else None


def unresolved(db: sqlite3.Connection) -> list[dict[str, str]]:
    rows = db.execute("SELECT source, matched, reason FROM xref WHERE target IS NULL ORDER BY rowid").fetchall()
    return [{"source": s, "matched": m, "reason": r} for s, m, r in rows]


def ref_counts(db: sqlite3.Connection, act: str) -> dict[str, int]:
    q = "SELECT count(*) FROM xref WHERE source LIKE ? AND target IS "
    return {"resolved": db.execute(q + "NOT NULL", (act + " %",)).fetchone()[0],
            "unresolved": db.execute(q + "NULL", (act + " %",)).fetchone()[0]}


def search(db: sqlite3.Connection, raw_query: str, limit: int = 10) -> list[tuple[str, str]]:
    """FTS5 keyword search on the raw query only (ADR 0001). Ties on score break by citation, so order is total."""
    try:
        return db.execute(
            "SELECT citation, text FROM fts WHERE fts MATCH ? ORDER BY rank, citation LIMIT ?", (raw_query, limit)
        ).fetchall()
    except sqlite3.OperationalError:  # query is not valid FTS5 syntax: no hits, never rewritten
        return []
