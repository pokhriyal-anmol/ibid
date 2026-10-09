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
    db.commit()
    return db


def lookup(db: sqlite3.Connection, citation: str) -> str | None:
    """Verbatim text for a citation. TEXT equality is BINARY collation, i.e. a byte comparison."""
    row = db.execute("SELECT text FROM provision WHERE citation = ?", (citation,)).fetchone()
    return row[0] if row else None
