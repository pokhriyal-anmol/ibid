"""`ibid concordance from-table`: candidate concordance entries from a published BNS to IPC table.

Source: the CAPT Bhopal correspondence table (a director's compilation, not an MHA publication). No model.
Input is `pdftotext -layout` output. Rows become section-level entries, typed from the counts. An entry
is served only when every cited provision is in the index and every provision shares a distinctive word
(one that under 10% of provisions use) with the text of the other side.
"""
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

SOURCE = "CAPT Bhopal correspondence table, June 2024: one director's compilation, not an official MHA publication"
ROW = re.compile(r"^\s{0,3}(\d{1,3}[A-Z]{0,2}(?:\s?\(\w+\))*)\s{2,}\S")
CELL = re.compile(r"New|\d+[A-Z]{0,2}(?:\(\w+\))*(?:\s*(?:,|&|and|to)\s*(?:\d+[A-Z]{0,2}(?:\(\w+\))*)?)*")
TRAILING_CELL = re.compile(r" (\d+[A-Z]{0,2}(?:\(\w+\))*)$")  # a section number ending a subject
PART = re.compile(r"\S+(?: \S+)*")  # a run of words with single spaces; two spaces end it
SECTION = re.compile(r"\d+[A-Z]{0,2}")
MAX_DF = 0.1
MIN_WORD = 4
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
    for page, body in enumerate(text.split("\f"), 1):
        cols: tuple[int, int | None] | None = None
        col = _ipc_column(body)
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


def _components(rows: list[dict]) -> list[dict]:
    """Union the BNS and IPC sections the rows tie together; one component is one candidate entry."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = x = parent[parent[x]]
        return x

    ranged: set[str] = set()
    for r in rows:
        b = "BNS " + SECTION.match(r["bns"]).group()
        find(b)
        if re.search(r"\bto\b", r["ipc"]):
            ranged.add(b)
        if r["ipc"] != "New":
            for s in SECTION.findall(re.sub(r"\(\w+\)", "", r["ipc"])):
                parent[find("IPC " + s)] = find(b)
    groups: dict[str, dict] = {}
    for node in list(parent):
        g = groups.setdefault(find(node), {"ipc": [], "bns": [], "ranged": False, "rows": []})
        g["ipc" if node.startswith("IPC") else "bns"].append(node)
        g["ranged"] = g["ranged"] or node in ranged
    for r in rows:
        groups[find("BNS " + SECTION.match(r["bns"]).group())]["rows"].append(f"{r['bns']} (p.{r['page']})")
    return list(groups.values())


def _refusal(g: dict, t: str | None, texts: dict[str, str], common: set[str]) -> str | None:
    if g["ranged"]:
        return "ipc cell holds a range"
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


def candidates(rows: list[dict], db: sqlite3.Connection) -> tuple[list[dict], list[dict]]:
    """(served entries, refused entries with a reason)."""
    texts = dict(db.execute("SELECT citation, text FROM provision"))
    df = Counter(w for t in texts.values() for w in _words(t))
    common = {w for w, n in df.items() if n > MAX_DF * len(texts)}
    served, refused = [], []
    for g in _components(rows):
        g["ipc"], g["bns"] = sorted(g["ipc"]), sorted(g["bns"])
        t = TYPES.get((min(len(g["ipc"]), 2), min(len(g["bns"]), 2)))
        entry = {"ipc": g["ipc"], "bns": g["bns"], "type": t or "many-to-many"}
        reason = _refusal(g, t, texts, common)
        if reason:
            refused.append({**entry, "reason": reason, "rows": g["rows"]})
        else:
            served.append({**entry, "verified": True, "basis": "source-table-checked",
                           "evidence": f"{SOURCE}, rows {', '.join(g['rows'])}"})
    return served, refused


def from_table(table: str, index_path: str, out: str) -> int:
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
