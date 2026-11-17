"""The SQLite index: one file, rebuilt from source on every run."""
import json
import os
import re
import sqlite3

from ibid.parse import Provision
from ibid.xref import Edge, chains


KEYWORD_LIMIT = 100  # the result size a keyword item is judged on, shared by eval and conform


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


def _match(db: sqlite3.Connection, query: str, limit: int, act: str | None) -> list[tuple[str, str]]:
    return db.execute(
        "SELECT citation, text FROM fts WHERE fts MATCH ?" + (" AND citation LIKE ?" if act else "") + " ORDER BY rank, citation LIMIT ?",
        (query, *([act + " %"] if act else []), limit),
    ).fetchall()


def search(db: sqlite3.Connection, raw_query: str, limit: int = 10, act: str | None = None) -> list[tuple[str, str]]:
    """FTS5 keyword search on the raw query only (ADR 0001). Ties on score break by citation, so order is total."""
    try:
        return _match(db, raw_query, limit, act)
    except sqlite3.OperationalError:  # query is not valid FTS5 syntax: no hits, never rewritten
        return []


def search_explained(db: sqlite3.Connection, raw_query: str, limit: int = 10, act: str | None = None) -> tuple[list[tuple[str, str]], dict[str, str]]:
    """`search` for the MCP tool, which never answers with a silent empty list (ADR 0011). The eval path keeps `search`.
    A query that is not valid FTS5 syntax is retried once with each word quoted, and `searched_as` says what ran."""
    extra: dict[str, str] = {}
    try:
        hits = _match(db, raw_query, limit, act)
    except sqlite3.OperationalError:
        extra["searched_as"] = " ".join(f'"{w}"' for w in re.findall(r"\w+", raw_query))
        hits = _match(db, extra["searched_as"], limit, act) if extra["searched_as"] else []
    if not hits:
        extra["notice"] = ("No section contains every word of the query. Keyword search needs every word to match: use fewer or more specific words."
                           if extra.get("searched_as", raw_query) else "The query has no words to search for.")
    return hits, extra


def neighbours(db: sqlite3.Connection, citation: str) -> tuple[tuple[str, str] | None, tuple[str, str] | None]:
    """(citation, heading line) of the previous and next section of the same Act in document order, None at an end.
    A sub-provision gets the neighbours of its section."""
    row = db.execute("SELECT rowid, parent FROM provision WHERE citation = ?", (citation,)).fetchone()
    if row is None:
        return None, None
    while row[1]:  # nested sub-provisions walk up to their section
        row = db.execute("SELECT rowid, parent FROM provision WHERE citation = ?", (row[1],)).fetchone()
    rowid = row[0]
    act = citation.split(" ")[0] + " %"
    q = "SELECT citation, text FROM provision WHERE parent IS NULL AND citation LIKE ? AND rowid {} ? ORDER BY rowid {} LIMIT 1"
    pair = [db.execute(q.format(op, order), (act, rowid)).fetchone() for op, order in (("<", "DESC"), (">", "ASC"))]
    return tuple(None if r is None else (r[0], r[1].split("\n")[0].split("\u2014")[0][:100]) for r in pair)
