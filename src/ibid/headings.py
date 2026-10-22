"""Section headings as a sidecar (slice 8). Nothing here touches the index, the provision text or a pin.

BNS: the gazette prints each heading in a margin column beside the section's first line, on the
right of the body on some pages and on the left on others. IPC: the text before the first em dash.
"""
import re
import subprocess
from collections import Counter

from ibid.ipc import parse_ipc
from ibid.parse import BNS_TOTAL

SEGMENT = re.compile(r"\S+(?: {1,3}\S+)*")  # a gap of four spaces or more separates columns
LEFT_NOTE = re.compile(r"(\S+(?: \S+)*)(?:\s+(.*))?$")  # a line that starts at column 0
LEFT_ROW = re.compile(r"\S.*?\s{3,}\d{1,3}\.(?!\d)")
RIGHT_ROW = re.compile(r"\s{0,12}\d{1,3}\.(?!\d)")
START = re.compile(r"(\d+)\.(?!\d)")
TOL = 3  # the cut sits this many columns before the margin's first column
RIGHT_FROM = 60  # a right margin starts beyond this column
NOTE_MAX = 20  # a left margin note is at most this wide
JUSTIFIED_MAX = 16  # a stray margin word of three letters or fewer, left of this column, is margin
HEADER_ROWS = 12  # the running page header ends at a rule line within this many lines


def _segments(line: str) -> list[tuple[int, str]]:
    return [(m.start(), m.group()) for m in SEGMENT.finditer(line)]


def _side(lines: list[str]) -> tuple[str | None, int]:
    """Which side the page's headings are on and, for the right, the column they start at.

    A section's number line says it: the number is at the line start (margin on the right) or after
    a note at column 0 (margin on the left). Sub-provision notes such as "24 of 1958." can sit on
    either side, so the side of the page's body or its stray columns is no evidence.
    """
    left = sum(1 for ln in lines if LEFT_ROW.match(ln))
    right = sum(1 for ln in lines if RIGHT_ROW.match(ln))
    cols = Counter(r[-1][0] for r in map(_segments, lines) if r and r[-1][0] >= RIGHT_FROM)
    if left > right or (not right and not cols):
        return ("left", 0) if left else (None, 0)
    return ("right", cols.most_common(1)[0][0]) if cols else (None, 0)


def _cut(line: str, side: str | None, col: int) -> tuple[str, str]:
    """(body, margin) of one line, cut by column because a margin note can sit under four spaces from the body."""
    if side == "right":
        cut = col - TOL
        if line[cut - 1:cut].strip() and line[cut:cut + 1].strip():  # the cut fell inside a body word: skip its tail
            cut = line.find(" ", cut) if " " in line[cut:] else len(line)
        return line[:cut], line[cut:].strip()
    if side == "left" and (m := LEFT_NOTE.match(line)) and len(m[1]) <= NOTE_MAX:  # body columns drift, the margin does not
        if m[2] and len(m[2]) <= 3 and m.start(2) < JUSTIFIED_MAX:  # a justified margin line ends in a stray word: "property    in"
            return "", " ".join(line.split())
        return m[2] or "", m[1]
    if side == "left" and line[:1].strip() and (m := re.match(rf"(\S.{{0,{NOTE_MAX - 1}}})(?= )", line)):  # note and body share one space
        return line[m.end():].strip(), m[1]
    return line, ""


def walk_layout(layout: str, act: str, total: int, end: str | None = None) -> list[tuple[str, list[str], list[tuple[str, int]]]]:
    """(citation, heading parts, body lines as (text, column)) for sections 1..total, from `pdftotext -layout` text.
    A line that equals `end` once stripped stops the walk."""
    found: list[tuple[str, list[str], list[tuple[str, int]]]] = []
    closed = True  # a heading ends at its first full stop; later margin text is a note or the next heading
    above: list[str] = []  # margin-only lines since the last body line, once the heading is closed
    between = False  # a chapter heading and its title sit between two sections, not inside one
    for page in layout.split("\f"):
        lines = page.split("\n")
        rule = max((i for i, ln in enumerate(lines[:HEADER_ROWS]) if "____" in ln), default=-1)
        lines = lines[rule + 1:]
        side, col = _side(lines)
        placed: list[tuple[list, str, int]] = []  # this page's body lines, columns made relative to the page's leftmost
        for line in lines:
            if end and line.strip() == end:
                break
            body, margin = _cut(line, side, col)
            m = START.match(body.lstrip())
            if m and int(m[1]) == len(found) + 1 <= total:
                found.append((f"{act} {m[1]}", above, []))
                above, closed, between = [], False, False
            between = between or re.fullmatch(r"CHAPTER [IVXLC]+", body.strip()) is not None
            if margin:
                (above if closed else found[-1][1]).append(margin)
                closed = closed or margin.endswith(".")
            if body.strip():
                above = []
                if found and not between:
                    placed.append((found[-1][2], body.strip(), len(line) - len(line.lstrip()) if side != "left" else line.rfind(body.strip())))
        base = min((c for _, _, c in placed), default=0)
        for into, text, c in placed:
            into.append((text, c - base))
        if end and any(ln.strip() == end for ln in lines):
            break
    return found


def parse_layout(layout: str) -> list[tuple[str, str | None]]:
    """(citation, heading or None) for BNS sections 1..358 in order, from `pdftotext -layout` text."""
    return [(c, " ".join(parts) or None) for c, parts, _ in walk_layout(layout, "BNS", BNS_TOTAL)]


def bns_headings(pdf_path: str) -> list[tuple[str, str | None]]:
    text = subprocess.run(["pdftotext", "-layout", pdf_path, "-"], check=True, capture_output=True, text=True).stdout
    return parse_layout(text)


def ipc_headings(pdf_path: str) -> list[tuple[str, str | None]]:
    out = []
    for p in parse_ipc(pdf_path):
        if p.parent is None:
            head, dash, _ = p.text.partition("—")
            out.append((p.citation, " ".join(re.sub(r"^\S+\s+", "", head).split()) or None if dash else None))
    return out


def report(pairs: list[tuple[str, str | None]]) -> list[str]:
    missing = [c for c, h in pairs if h is None]
    return ([f"{c}\t{h or ''}" for c, h in pairs] + [f"with heading: {len(pairs) - len(missing)}",
            f"without heading: {len(missing)}"] + missing)
