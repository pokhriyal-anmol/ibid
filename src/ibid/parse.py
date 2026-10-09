"""Layout-aware parser for the BNS Gazette PDF (PRS copy) into section-level provisions.

Needs the `pdftotext` binary (poppler). Margin notes sit in separate left/right blocks, so
each page is cropped to its body column using line coordinates.
"""
import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass

PARSER_VERSION = "1"
BNS_TOTAL = 358
HEADER_Y = 80  # lines above this are the running page header
WIDE = 250  # a body line wider than this (pt) fixes the page's body column
NS = "{http://www.w3.org/1999/xhtml}"


@dataclass(frozen=True)
class Provision:
    citation: str
    text: str
    parent: str | None  # section level only for now; subsections come with a later ticket
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


def parse_bns(pdf_path: str) -> list[Provision]:
    """Sections in order. A heading is the next expected number at the start of a body line."""
    sections: list[list[str]] = []
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
            sections[-1].append(line)
    return [
        Provision(f"BNS {i}", " ".join(" ".join(s).split()), None, ())
        for i, s in enumerate(sections, 1)
    ]
