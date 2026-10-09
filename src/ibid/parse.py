"""Layout-aware parser for the BNS Gazette PDF (PRS copy) into section-level provisions.

Needs the `pdftotext` binary (poppler). Margin notes sit in separate left/right blocks, so
each page is cropped to its body column using line coordinates.
"""
import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass

PARSER_VERSION = "3"
BNS_TOTAL = 358
HEADER_Y = 80  # lines above this are the running page header
WIDE = 250  # a body line wider than this (pt) fixes the page's body column
NS = "{http://www.w3.org/1999/xhtml}"


@dataclass(frozen=True)
class Provision:
    citation: str
    text: str
    parent: str | None
    children: tuple[str, ...]


def _page_lines(page: ET.Element) -> list[tuple[str, bool]]:
    lines = []
    for ln in page.iter(NS + "line"):
        x0, x1, y = (float(ln.get(k)) for k in ("xMin", "xMax", "yMin"))
        words = " ".join(w.text or "" for w in ln.iter(NS + "word"))
        if y >= HEADER_Y:
            lines.append((y, x0, x1, words))
    wide = [(x0, x1) for _, x0, x1, _ in lines if x1 - x0 > WIDE]
    if not wide:
        return []
    left, right = min(x0 for x0, _ in wide), max(x1 for _, x1 in wide)
    body = [ln for ln in lines if ln[1] >= left - 3 and ln[2] <= right + 3]
    return [(w, x0 - left > 30) for _, x0, x1, w in sorted(body)]


def body_lines(pdf_path: str) -> list[tuple[str, bool]]:
    xml = subprocess.run(
        ["pdftotext", "-bbox-layout", pdf_path, "-"], check=True, capture_output=True
    ).stdout
    root = ET.fromstring(xml)
    return [ln for page in root.iter(NS + "page") for ln in _page_lines(page)]


_SUB = re.compile(r"\((\d+[A-Z]*)\)\s")
_CLAUSE = re.compile(r"\(([a-z]+)\)\s")
_ATTACHED = {
    "proviso": re.compile(r"Provided\b"),
    "explanation": re.compile(r"Explanation\b"),
    "exception": re.compile(r"Exception\b"),
    "illustration": re.compile(r"Illustrations?\.?$"),
}
_ROMAN_SEQ = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"]
_ROMAN = set(_ROMAN_SEQ)


def _split(act: str, n: int | str, lines: list[tuple[str, bool]], texts: list[str] | None = None) -> list[Provision]:
    """One section into its provisions.

    Citations: `BNS 103(1)`, clause `BNS 8(5)(a)`, and `<parent> proviso|explanation|exception|
    illustration <k>` with k counted per parent, e.g. `BNS 2(8) explanation 1`.
    shortcut: clauses are only recognised when indented, so an inline `(6) (a) ...` clause stays
    in its subsection; upgrade when a ticket needs those clauses.
    """
    texts = texts or [re.sub(rf"^{n}\.\s*", "", ln) if i == 0 else ln for i, (ln, _) in enumerate(lines)]
    nodes = [[f"{act} {n}", None, 0, "root", len(lines)]]  # citation, parent, start, kind, end
    stack, seen, last_sub = [0], {nodes[0][0]}, 0

    def nearest(*kinds: str) -> int:
        return next(j for j in reversed(stack) if nodes[j][3] in kinds)

    for i, ((_, indented), text) in enumerate(zip(lines, texts)):
        kind = label = None
        m = _SUB.match(text)
        # a wrapped line like "(3) and (4) of section 309" is not a subsection: numbers must run on
        if m and int(re.match(r"\d+", m[1])[0]) in (last_sub + 1, last_sub if m[1][-1:].isalpha() else 0):
            kind, label = "sub", m[1]
            last_sub = int(re.match(r"\d+", m[1])[0])
        elif indented and (m := _CLAUSE.match(text)) and nodes[stack[-1]][3] != "illustration":
            kind, label = "clause", m[1]
        else:
            kind = next((k for k, rx in _ATTACHED.items() if rx.match(text)), None)
        if kind is None:
            continue
        if kind == "sub":
            parent = 0
        elif kind == "clause":
            outer = next((j for j in reversed(stack) if nodes[j][3] == "clause"), None)
            parent = nearest("root", "sub", *_ATTACHED)
            if outer is not None and label in _ROMAN:
                last = nodes[outer][0].rsplit("(", 1)[1][:-1]
                nxt = ({chr(ord(last) + 1)} if len(last) == 1 else set()) | ({_ROMAN_SEQ[_ROMAN_SEQ.index(last) + 1]} if last in _ROMAN_SEQ[:-1] else set())
                parent = nodes[outer][1] if label in nxt else outer
        elif kind == "illustration":
            parent = nearest("root", "sub", "explanation", "exception")
        else:
            parent = nearest("root", "sub")
        while stack[-1] != parent:
            nodes[stack.pop()][4] = i
        if kind in ("sub", "clause"):
            cite = f"{nodes[parent][0]}({label})"
        else:
            k = sum(1 for x in nodes if x[1] == parent and x[3] == kind) + 1
            cite = f"{nodes[parent][0]} {kind} {k}"
        if cite in seen:
            raise ValueError(f"duplicate citation {cite}")
        seen.add(cite)
        nodes.append([cite, parent, i, kind, len(lines)])
        stack.append(len(nodes) - 1)
    out = []
    for j, (cite, parent, start, _, end) in enumerate(nodes):
        src = [ln for ln, _ in lines] if j == 0 else texts
        kids = tuple(x[0] for x in nodes if x[1] == j)
        out.append(Provision(cite, " ".join(" ".join(src[start:end]).split()), nodes[parent][0] if parent is not None else None, kids))
    return out


def parse_bns(pdf_path: str) -> list[Provision]:
    """Provisions in order: each section followed by its sub-provisions. A section heading is the
    next expected number at the start of a body line."""
    sections: list[list[tuple[str, bool]]] = []
    between = False  # chapter and group headings sit between two sections, not inside one
    for line, indented in body_lines(pdf_path):
        n = len(sections) + 1
        if re.match(rf"{n}\.(\s|(?=[A-Z(]))", line):
            sections.append([])
            between = False
        elif line.startswith("CHAPTER ") or (indented and line.startswith("Of ")):
            between = True
        if sections and not between:
            if len(sections) == BNS_TOTAL and set(line) == {"—"}:  # rule after section 358
                break
            sections[-1].append((line, indented))
    return [p for i, s in enumerate(sections, 1) for p in _split("BNS", i, s)]
