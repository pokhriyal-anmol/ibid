"""Parser for the India Code CrPC PDF into the same provision tree as the IPC, plus its independent check.

Reads `pdftotext -layout` text (a `.txt` path is read as that text, which is how the tests feed it).
The Arrangement of Sections before the Act supplies every section number and heading (decision 7);
the body supplies the text. Footnotes sit below the first column-0 `N. ` line of a page; centred lines
are chapter and part headings; amendment marks and footnote numerals are dropped.

shortcut: an inline footnote numeral with no bracket or star after it stays in the text, and a footnote
that runs onto the next page is not cut; upgrade if the heading check or a ticket shows either.
"""
import re
import subprocess
import sys
from pathlib import Path

from ibid import index

from ibid.parse import Provision, _split
from ibid.ipc import _head
from ibid.xref import extract

CRPC_PARSER_VERSION = "1"
HEADING_MATCH_FLOOR = 0.98  # both lists come from one document, so stricter than D-004's 80%
CENTRED = 20  # leading spaces: chapter and part headings
CLAUSE_INDENT = 7  # leading spaces: a clause, as against a sub-section
_ARR = re.compile(r"\s+(\d+)-?([A-Z]{0,2})\.\s+(\S.*)")  # the Arrangement prints 265-I, the body 265-I too: the key is 265I
_START = re.compile(r"(\d+)-?([A-Z]{0,2})\.\s")


def layout_text(path: str) -> str:
    if path.endswith(".txt"):
        return Path(path).read_text()
    return subprocess.run(["pdftotext", "-layout", path, "-"], check=True, capture_output=True, text=True).stdout


def arrangement(lines: list[str]) -> list[tuple[str, str]]:
    """(key, heading) per entry; a heading may wrap onto indented lines."""
    out: list[list[str]] = []
    for ln in lines:
        if m := _ARR.match(ln):
            out.append([m[1] + m[2], m[3].strip()])
        elif out and not out[-1][1].endswith(".") and re.match(r"\s{4,}\S", ln) and not re.match(r"\s*(CHAPTER|[A-Z]\.[–-])", ln) and ln.strip() != ln.strip().upper():
            out[-1][1] += " " + ln.strip()
    return [tuple(x) for x in out]


def _clean(text: str) -> str:
    text = re.sub(r"(?<!\d)\d{1,3}(?=\[)", "", text)  # footnote numeral before an opening bracket
    text = re.sub(r"\d*\*+", "", text).replace("[", "").replace("]", "")
    return re.sub(r"\s+([,;.:])", r"\1", " ".join(text.split()))


def _body_lines(body: list[str]) -> list[tuple[str, bool]]:
    out = []
    for page in "\n".join(body).split("\f"):
        lines = page.split("\n")
        cut = next((i for i, ln in enumerate(lines) if re.match(r"\d{1,3}\.\s", ln)), len(lines))
        for ln in lines[:cut]:
            lead = len(ln) - len(ln.lstrip())
            if ln.strip().isdigit() or lead >= CENTRED or not (text := _clean(ln)):
                continue
            out.append((text, lead >= CLAUSE_INDENT))
    return out


def parse_crpc(path: str) -> tuple[list[Provision], list[tuple[str, str]]]:
    """(provisions in order, Arrangement entries). Each section is followed by its sub-provisions."""
    lines = layout_text(path).split("\n")
    start = next(i for i, ln in enumerate(lines) if re.match(r"\s*ACT NO\. ", ln))
    end = next((i for i in range(start, len(lines)) if re.match(r"\s*THE FIRST SCHEDULE\s*$", lines[i])), len(lines))
    schedules = next((i for i in range(start) if re.match(r"\s*THE FIRST SCHEDULE\.", lines[i])), start)
    arr = arrangement(lines[:schedules])
    keys = [k for k, _ in arr]
    sections: list[tuple[str, list[tuple[str, bool]]]] = []
    for text, indented in _body_lines(lines[start:end]):
        m = _START.match(text)
        key = m[1] + m[2] if m else None
        cur = keys.index(sections[-1][0]) if sections else -1
        if key in keys and keys.index(key) > cur:
            sections.append((key, []))
        if sections:
            sections[-1][1].append((text, indented))
    provisions = [p for n, s in sections for p in _split("CrPC", n, s, _head([t for t, _ in s]))]
    return provisions, arr


def _norm(s: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", s.lower()).split())  # punctuation is a gap, so "set-off" equals "set off"


def body_heading(text: str) -> str:
    return re.sub(r"^\S+\s+", "", text).partition("—")[0]


def check(provisions: list[Provision], arr: list[tuple[str, str]]) -> tuple[bool, list[str]]:
    """Decision 4: section count equals the Arrangement's, and body headings equal its headings.
    Neither confirms the body text itself is right."""
    tops = {p.citation: p.text for p in provisions if p.parent is None}
    bad = []
    for k, h in arr:
        body = tops.get(f"CrPC {k}")
        if body is None or _norm(body_heading(body)) != _norm(h):
            bad.append(f"CrPC {k}: arrangement {h!r}, body {body_heading(body) if body else None!r}")
    rate = 1 - len(bad) / len(arr)
    report = [f"CrPC sections: {len(tops)}/{len(arr)}", f"CrPC heading match: {rate:.2%} ({len(arr) - len(bad)}/{len(arr)})", *bad]
    return len(tops) == len(arr) and rate >= HEADING_MATCH_FLOOR, report


def build(path: str, index_path: str, bnss_path: str | None = None) -> int:
    """Check, then write the second index. A failed check writes nothing."""
    provisions, arr = parse_crpc(path)
    ok, report = check(provisions, arr)
    heads = [(f"CrPC {k}", h) for k, h in arr]  # the Arrangement's, decision 7
    versions = [("crpc_parser_version", CRPC_PARSER_VERSION)]
    if bnss_path:
        from ibid import bnss
        more, more_heads, more_arr = bnss.parse_bnss(bnss_path)
        bok, brep = bnss.check(more_heads, more_arr)
        provisions, heads, ok, report = provisions + more, heads + more_heads, ok and bok, report + brep
        versions.append(("bnss_parser_version", bnss.BNSS_PARSER_VERSION))
    print("\n".join(report))
    if not ok:
        print("error: procedure Act check failed, nothing written", file=sys.stderr)
        return 1
    db = index.build(index_path, provisions, extract(provisions))
    db.execute("CREATE TABLE heading (citation TEXT PRIMARY KEY, heading TEXT)")
    db.executemany("INSERT INTO heading VALUES (?, ?)", heads)
    db.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    db.executemany("INSERT INTO meta VALUES (?, ?)", versions)
    db.commit()
    db.close()
    return 0
