"""The SQLite index: one file, rebuilt from source on every run."""
import json
import os
import sqlite3

from ibid.parse import Provision


def build(path: str, provisions: list[Provision]) -> sqlite3.Connection:
    if os.path.exists(path):
        os.remove(path)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE provision (citation TEXT PRIMARY KEY, text TEXT, parent TEXT, children TEXT)")
    db.executemany(
        "INSERT INTO provision VALUES (?, ?, ?, ?)",
        [(p.citation, p.text, p.parent, json.dumps(p.children)) for p in provisions],
    )
    db.execute("CREATE VIRTUAL TABLE fts USING fts5(citation UNINDEXED, text)")
    db.executemany("INSERT INTO fts VALUES (?, ?)", [(p.citation, p.text) for p in provisions])
    db.commit()
    return db


def lookup(db: sqlite3.Connection, citation: str) -> tuple[str, list[str]] | None:
    """Verbatim text and child citations. TEXT equality is BINARY collation, i.e. a byte comparison."""
    row = db.execute("SELECT text, children FROM provision WHERE citation = ?", (citation,)).fetchone()
    return (row[0], json.loads(row[1])) if row else None


def search(db: sqlite3.Connection, raw_query: str, limit: int = 10) -> list[tuple[str, str]]:
    """FTS5 keyword search on the raw query only (ADR 0001). Ties on score break by citation, so order is total."""
    try:
        rows = db.execute(
            "SELECT citation, text FROM fts WHERE fts MATCH ? ORDER BY rank, citation LIMIT ?", (raw_query, limit)
        ).fetchall()
    except sqlite3.OperationalError:  # query is not valid FTS5 syntax: no hits, never rewritten
        return []
    return [(c, t) for c, t in rows]
