"""Parser for the BNSS Gazette PDF (PRS copy) into the same provision tree as the BNS, plus its check.

Reads `pdftotext -layout` text (a `.txt` path is read as that text). Headings are the Gazette's margin
notes, found by the BNS margin method (`headings.walk_layout`). The real Gazette prints no Arrangement of
Sections, so the section count is checked against the Act's published 531 and the headings cannot be
cross-checked; a file that does print an Arrangement (the test fixture) is checked against it, as the CrPC is.

shortcut: margin notes that the column cut misses stay in the body text, and a clause is any line set 10
columns right of its page's leftmost, and a section whose clause labels repeat keeps no clause children; upgrade if a ticket needs exact clause children.
"""
import os
import re

from ibid.crpc import HEADING_MATCH_FLOOR, _norm, arrangement, layout_text
from ibid.headings import walk_layout
from ibid.parse import Provision, _split

BNSS_PARSER_VERSION = "1"
BNSS_TOTAL = int(os.environ.get("IBID_BNSS_TOTAL", 531))  # sections of Act 46 of 2023 as gazetted; the env var lets a test use a small file
CLAUSE_INDENT = 10  # columns right of the page's leftmost body line
_ENACTED = re.compile(r"\s*BE it enacted")
_PART = re.compile(r"[A-Z]\.—")  # a Part heading ("B.—Warrant of arrest") between sections


def parse_bnss(path: str) -> tuple[list[Provision], list[tuple[str, str | None]], list[tuple[str, str]]]:
    """(provisions in order, (citation, heading) per section, Arrangement entries; empty if the file has none)."""
    lines = layout_text(path).split("\n")
    start = next(i for i, ln in enumerate(lines) if _ENACTED.match(ln))
    arr = arrangement(lines[:start])
    walked = walk_layout("\n".join(lines[start:]), "BNSS", len(arr) or BNSS_TOTAL, "THE FIRST SCHEDULE")
    provisions, heads = [], []
    for cite, parts, body in walked:
        rows = [(t, c >= CLAUSE_INDENT) for t, c in body if not t.isdigit() and not _PART.match(t)]  # a bare number is a page number
        try:
            provisions += _split("BNSS", cite.split()[1], rows)
        except ValueError:  # nested clauses repeat a label, which a Citation cannot tell apart
            provisions += _split("BNSS", cite.split()[1], [(t, False) for t, _ in rows])
        heads.append((cite, " ".join(parts) or None))
    return provisions, heads, arr


def check(heads: list[tuple[str, str | None]], arr: list[tuple[str, str]]) -> tuple[bool, list[str]]:
    """Section count equals the Arrangement's (or 531), and headings equal the Arrangement's (or are all present).
    Neither confirms the body text itself is right."""
    want = {f"BNSS {k}": h for k, h in arr} or {f"BNSS {i}": None for i in range(1, BNSS_TOTAL + 1)}
    got = dict(heads)
    bad = [f"{c}: arrangement {w!r}, body {got.get(c)!r}" if w else f"{c}: no heading, body {got.get(c)!r}"
           for c, w in want.items() if not got.get(c) or (w and _norm(got[c]) != _norm(w))]
    rate = 1 - len(bad) / len(want)
    note = [] if arr else ["BNSS has no Arrangement of Sections in this file: headings are margin notes, only their presence was checked"]
    report = [f"BNSS sections: {len(got)}/{len(want)}", f"BNSS heading match: {rate:.2%} ({len(want) - len(bad)}/{len(want)})", *note, *bad]
    return len(got) == len(want) and rate >= HEADING_MATCH_FLOOR, report
