"""Parser for the WIPO Lex IPC PDF into the same provision tree as the BNS.

Needs `pdftohtml` (poppler). Section headings are the bold runs; footnotes sit below a rule line;
chapter and group headings are centred; state amendments run from a bold "STATE AMENDMENT(S)"
line to the next real section. Only a heading that moves forward in the printed table of
contents counts as a section, so quoted state-amendment headings cannot masquerade as one.

shortcut: square brackets and *** (amendment marks) and footnote numerals are dropped from the text;
upgrade if a ticket needs amendment history.
"""
import re
import subprocess
import xml.etree.ElementTree as ET

from ibid.parse import Provision, _split

IPC_TOTAL = 575  # entries in the printed table of contents, counted by hand once
PAGE_NUMBER_Y = 1160
INDENT = 125  # a paragraph's first line starts here; wrapped lines start at the 108 margin
CENTRED = 200  # chapter and group headings start further right than this
BAR = 150  # the footnote rule is a blank run wider than this (pt)
MARK = 10  # footnote numerals are set at this size or smaller
KEY = re.compile(r"^\s*\[?\s*(\d+)-?([A-Z]{0,2})(?:\.|\s)")
ILLUSTRATION = re.compile(r"^\[?I+l+ustrations?\]?\.?$")
STATE = re.compile(r"^STATE AMENDMENTS?$")


def _pages(pdf_path: str) -> list[tuple[int, list[list[tuple[int, str, bool]]]]]:
    """Per page, its body lines; each line is (left, text, bold) elements left to right."""
    xml = subprocess.run(["pdftohtml", "-xml", "-i", "-stdout", pdf_path], check=True, capture_output=True).stdout
    sizes: dict[str, int] = {}  # font ids are numbered across the whole file
    pages = []
    for page in ET.fromstring(xml).iter("page"):
        sizes.update({f.get("id"): int(f.get("size")) for f in page.iter("fontspec")})
        els = [(int(t.get("top")) + int(t.get("height")), int(t.get("left")), "".join(t.itertext()),
                t.find("b") is not None, sizes[t.get("font")], int(t.get("width"))) for t in page.iter("text")]
        cut = min((e[0] for e in els if not e[2].strip() and e[5] > BAR), default=PAGE_NUMBER_Y)
        body = sorted(e for e in els if e[0] < min(cut, PAGE_NUMBER_Y) and not (e[4] <= MARK and e[2].strip().isdigit()))
        lines: list[list] = []
        for e in body:
            if lines and e[0] - lines[-1][0][0] <= 5:
                lines[-1].append(e)
            else:
                lines.append([e])
        pages.append((int(page.get("number")), [[(x[1], x[2], x[3]) for x in sorted(ln, key=lambda x: x[1])] for ln in lines]))
    return pages


def _key(text: str) -> str | None:
    m = KEY.match(text)
    return f"{m[1]}{m[2]}" if m else None


def _head(texts: list[str]) -> list[str]:
    """Drop the `N. Title.—` run-in heading (up to three lines) so a first subsection can be seen."""
    for i, t in enumerate(texts[:3]):
        if "—" in t:
            return [""] * i + [t.split("—", 1)[1].lstrip()] + texts[i + 1:]
    return texts


def parse_ipc(pdf_path: str) -> list[Provision]:
    """Provisions in order: each section followed by its sub-provisions."""
    toc: list[str] = []
    sections: list[tuple[str, list[tuple[str, bool]]]] = []
    in_body = skipping = False
    for _, lines in _pages(pdf_path):
        for ln in lines:
            text = "".join(t for _, t, _ in ln).replace("[", "").replace("]", "").replace("***", "")
            text = re.sub(r"\s+([,;.])", r"\1", " ".join(text.split()))  # no gap left where a mark was removed
            if not in_body:
                in_body = text.startswith("ACT NO. 45")
                if (k := _key(text)) and re.match(r"\s*\d+-?[A-Z]{0,2}\.", text):
                    toc.append(k)
                continue
            first = next((e for e in ln if e[1].strip() not in ("", "[")), ln[0])
            cur = toc.index(sections[-1][0]) if sections else -1
            if first[2] and (k := _key(text)) in toc and toc.index(k) > cur:
                sections.append((k, []))
                skipping = False
            elif first[2] and STATE.match(text):
                skipping = True
            if not sections or skipping or not text:
                continue
            if ILLUSTRATION.match(text):
                text = "Illustrations"
            elif first[0] >= CENTRED:  # chapter and group headings
                continue
            sections[-1][1].append((text, first[0] >= INDENT))
    return [p for n, s in sections for p in _split("IPC", n, s, _head([t for t, _ in s]))]
