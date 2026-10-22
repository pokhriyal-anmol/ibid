"""`ibid concordance from-table`: candidate concordance entries from a published BNS to IPC table.

Source: the CAPT Bhopal correspondence table (a director's compilation, not an MHA publication). No model.
Input is `pdftotext -layout` output. Rows become section-level entries, typed from the counts. An entry
is served only when every cited provision is in the index and every provision shares a distinctive word
(one that under 10% of provisions use) with the text of the other side.
"""
import hashlib
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

SOURCE = "CAPT Bhopal correspondence table, June 2024: one director's compilation, not an official MHA publication"
ROW = re.compile(r"^\s{0,3}(\d{1,3}[A-Z]{0,2}(?:\s?\(\w+\))*)\s{2,}\S")
CELL = re.compile(r"New|-|\d+[A-Z]{0,2}(?:\(\w+\))*(?:\s*(?:,|&|and|to)\s*(?:\d+[A-Z]{0,2}(?:\(\w+\))*)?)*")
TRAILING_CELL = re.compile(r" (\d+[A-Z]{0,2}(?:\(\w+\))*)$")  # a section number ending a subject
PART = re.compile(r"\S+(?: \S+)*")  # a run of words with single spaces; two spaces end it
SECTION = re.compile(r"\d+[A-Z]{0,2}")
MAX_DF = 0.1
MIN_WORD = 4
TRIPWIRE = 0.80  # D-004: BNSS headings against the table subjects, which paraphrase them
PROCEDURE_SOURCE = "CAPT Bhopal correspondence table BNSS to CrPC: one director's compilation, not an official MHA publication"
TYPES = {(0, 1): "new", (1, 1): "one-to-one", (1, 2): "split", (2, 1): "merged"}


def _ipc_column(body: str) -> int | None:
    """The most common start of the IPC cell on a page, learned from rows whose cell is separated by two spaces."""
    starts = Counter()
    for line in body.splitlines():
        parts = [(m.start(), m.group()) for m in PART.finditer(line)]
        if ROW.match(line) and len(parts) > 2 and CELL.fullmatch(parts[2][1]):
            starts[parts[2][0]] += 1
    return starts.most_common(1)[0][0] if starts else None


def _split_row(line: str, col: int | None) -> tuple[str, str, str, str]:
    """(bns, subject, ipc cell, note). Cut at the IPC column when a word starts there, so a cell followed by
    one space and a note, or a subject that runs up to the column, still splits correctly."""
    parts = [(m.start(), m.group()) for m in PART.finditer(line)]
    if col is not None:
        for cut in sorted(range(col - 2, col + 3), key=lambda c: abs(c - col)):
            if 0 < cut < len(line) and line[cut - 1] == " " and line[cut] != " ":
                m, bns = CELL.match(line[cut:]), ROW.match(line)
                subject = line[bns.end(1):cut].strip() if bns and bns.end(1) < cut else ""
                if m and subject:
                    return bns.group(1), subject, m.group().strip(), line[cut + m.end():].strip()
    ipc = len(parts) > 2 and CELL.fullmatch(parts[2][1]) is not None
    subject, rest = parts[1][1], " ".join(p for _, p in parts[3 if ipc else 2:])
    tail = None if ipc else TRAILING_CELL.search(subject)
    if tail:  # the cell sits one space after a wrapped subject, off this page's column
        return parts[0][1], subject[:tail.start()].strip(), tail.group(1), " ".join(p for _, p in parts[2:])
    return parts[0][1], subject, parts[2][1] if ipc else "", rest


def parse_rows(text: str) -> list[dict]:
    """Rows of {bns, subject, ipc (cell text), note, page}. A wrapped cell is joined to its row by column.
    shortcut: columns are learned per page from each row line, so a wrapped cell at the very top of a page
    goes to the note. Upgrade if a real table needs it."""
    rows: list[dict] = []
    whole = _ipc_column(text)  # a page with too few clean rows falls back to the whole table's column
    for page, body in enumerate(text.split("\f"), 1):
        cols: tuple[int, int | None] | None = None
        col = _ipc_column(body) or whole
        for line in body.splitlines():
            if "©" in line or not line.strip():
                continue
            parts = [(m.start(), m.group()) for m in PART.finditer(line)]
            if ROW.match(line):
                bns, subject, ipc, note = _split_row(line, col)
                rows.append({"bns": bns, "subject": subject, "ipc": ipc, "note": note, "page": page})
                cols = (parts[1][0], col if ipc else None)
            elif rows:
                for start, p in parts:
                    kind = "subject" if cols and abs(start - cols[0]) <= 2 else \
                        "ipc" if cols and cols[1] is not None and abs(start - cols[1]) <= 2 and CELL.fullmatch(p) else "note"
                    rows[-1][kind] = f"{rows[-1][kind]} {p}".strip()
    return rows


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", text.lower()) if len(w) >= MIN_WORD}


def _components(rows: list[dict], old: str = "IPC", new: str = "BNS") -> list[dict]:
    """Union the BNS and IPC sections the rows tie together; one component is one candidate entry."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = x = parent[parent[x]]
        return x

    ranged: set[str] = set()
    for r in rows:
        b = new + " " + SECTION.match(r["bns"]).group()
        find(b)
        if re.search(r"\bto\b|[&,]$|^$", r["ipc"].strip()):  # a range, a cell cut off at a connector, or no cell read
            ranged.add(b)
        if r["ipc"] not in ("New", "-"):
            for s in SECTION.findall(re.sub(r"\(\w+\)", "", r["ipc"])):
                parent[find(old + " " + s)] = find(b)
    groups: dict[str, dict] = {}
    for node in list(parent):
        g = groups.setdefault(find(node), {"ipc": [], "bns": [], "ranged": False, "rows": []})
        g["ipc" if node.startswith(old) else "bns"].append(node)
        g["ranged"] = g["ranged"] or node in ranged
    for r in rows:
        groups[find(new + " " + SECTION.match(r["bns"]).group())]["rows"].append(f"{r['bns']} (p.{r['page']})")
    return list(groups.values())


def _refusal(g: dict, t: str | None, texts: dict[str, str], common: set[str]) -> str | None:
    if g["ranged"]:
        return "ipc cell is a range, cut off or unread"
    if t is None:
        return "many-to-many component"
    if any(c not in texts for c in g["ipc"] + g["bns"]):
        return "cited provision not in the index"
    if t == "new":
        return None
    for side, other in ((g["ipc"], g["bns"]), (g["bns"], g["ipc"])):
        theirs = set().union(*(_words(texts[c]) for c in other)) - common
        if any(not (_words(texts[c]) & theirs) for c in side):
            return "no shared distinctive word"
    return None


def candidates(rows: list[dict], db: sqlite3.Connection, old: str = "IPC", new: str = "BNS", source: str = SOURCE) -> tuple[list[dict], list[dict]]:
    """(served entries, refused entries with a reason). In the procedure index a heading is not part of a
    section's text, so it joins the text the skeptic rule reads."""
    texts = dict(db.execute("SELECT citation, text FROM provision"))
    if db.execute("SELECT 1 FROM sqlite_master WHERE name = 'heading'").fetchone():
        texts = {c: f"{h or ''} {t}" for c, t, h in db.execute("SELECT p.citation, p.text, h.heading FROM provision p LEFT JOIN heading h USING (citation)")}
    df = Counter(w for t in texts.values() for w in _words(t))
    common = {w for w, n in df.items() if n > MAX_DF * len(texts)}
    served, refused = [], []
    for g in _components(rows, old, new):
        g["ipc"], g["bns"] = sorted(g["ipc"]), sorted(g["bns"])
        t = TYPES.get((min(len(g["ipc"]), 2), min(len(g["bns"]), 2)))
        entry = {"ipc": g["ipc"], "bns": g["bns"], "type": t or "many-to-many"}
        reason = _refusal(g, t, texts, common)
        if reason:
            refused.append({**entry, "reason": reason, "rows": g["rows"]})
        else:
            served.append({**entry, "verified": True, "basis": "source-table-checked",
                           "evidence": f"{source}, rows {', '.join(g['rows'])}"})
    return served, refused


def _norm(s: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", s.lower()).split())


def tripwire(rows: list[dict], db: sqlite3.Connection) -> tuple[float, list[str]]:
    """Share of table BNSS sections whose heading equals a table subject, and one line per mismatch."""
    heads = dict(db.execute("SELECT citation, heading FROM heading"))
    subjects: dict[str, list[str]] = {}
    for r in rows:
        if re.fullmatch(r"\d+[A-Z]{0,2}", r["bns"]):
            subjects.setdefault(f"BNSS {r['bns']}", []).append(r["subject"])
    bad = [f"{c}\t{heads.get(c)}\t{' / '.join(s)}" for c, s in subjects.items()
           if _norm(heads.get(c) or "") not in map(_norm, s)]
    return (len(subjects) - len(bad)) / len(subjects), bad


def procedure(rows: list[dict], db: sqlite3.Connection, out: str) -> int:
    """CrPC to BNSS. Writes the entries and their pin, or nothing when the tripwire fails."""
    rate, bad = tripwire(rows, db)
    print(f"tripwire: BNSS headings against table subjects {rate:.1%}, floor {TRIPWIRE:.0%}; mismatches (citation, heading, subject):")
    print("\n".join(bad))
    if rate < TRIPWIRE:
        print("error: tripwire failed, nothing written")
        return 1
    served, refused = candidates(rows, db, "CrPC", "BNSS", PROCEDURE_SOURCE)
    seen = {c for e in served + refused for c in e["ipc"]}
    removed = [{"ipc": [c], "bns": [], "type": "removed", "reason": "no row in the table cites it", "rows": []}
               for (c,) in db.execute("SELECT citation FROM provision WHERE parent IS NULL AND citation LIKE 'CrPC %' ORDER BY rowid")
               if c not in seen]
    entries = [{"crpc": e["ipc"], "bnss": e["bns"], "type": e["type"], "verified": "reason" not in e, "basis": "source-table-checked",
                "evidence": e.get("evidence") or f"{PROCEDURE_SOURCE}: {e['reason']}, rows {', '.join(e['rows']) or 'none'}"}
               for e in sorted(served + refused + removed, key=lambda e: (e["type"], e["ipc"], e["bns"]))]
    counts = Counter(f"{e['type']} {'verified' if e['verified'] else 'unverified'}" for e in entries)
    print(json.dumps({"rows_parsed": len(rows), "entries": dict(sorted(counts.items()))}, indent=2))
    Path(out).write_text(json.dumps(entries, indent=2, sort_keys=True) + "\n")
    Path(out).with_suffix(".sha256").write_text(hashlib.sha256(Path(out).read_bytes()).hexdigest() + "\n")
    return 0


def from_table(table: str, index_path: str, out: str, acts: str = "ipc-bns") -> int:
    if acts == "crpc-bnss":
        return procedure(parse_rows(Path(table).read_text()), sqlite3.connect(index_path), out)
    rows = parse_rows(Path(table).read_text())
    served, refused = candidates(rows, sqlite3.connect(index_path))
    report = {"source": SOURCE, "rows_parsed": len(rows),
              "entries_produced": dict(sorted(Counter(e["type"] for e in served + refused).items())),
              "entries_served": len(served), "entries_refused": len(refused),
              "refused_reasons": dict(sorted(Counter(e["reason"] for e in refused).items()))}
    Path(out).write_text(json.dumps({"report": report, "entries": served, "refused": refused, "rows": rows},
                                    indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0
