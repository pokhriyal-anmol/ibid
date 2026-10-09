"""Rule-based cross-reference detection and resolution inside one Act (ADR 0001: no model).

A reference is a chain such as `clause (a) of sub-section (1) of section 5`, a bare
`sub-section (2)` or `this section`. Absolute ones name a section; relative ones resolve
against the containing section of the provision the text came from.

shortcut: a range such as `clauses (a) to (d)` resolves its two ends, not the middle; a bare
`clause (a)` is recorded unresolved; bare numbers in a "namely, 103, 105" list are not detected;
upgrade when a ticket needs any of these.
"""
import itertools
import re
from dataclasses import dataclass

from ibid.parse import Provision

_Q = r"(?:sub-sections?|clauses?)\s+\(\w+\)(?:(?:,|\s+and|\s+or|\s+to)\s+(?:(?:sub-sections?|clauses?)\s+)?\(\w+\))*"
_NUM = r"\d+[A-Z]*(?:\(\w+\))*"
_SEC = rf"sections?\s+{_NUM}(?:(?:,|\s+and|\s+or)\s+(?:sections?\s+)?{_NUM})*"
_REF = re.compile(rf"\b(?:{_Q}\s+of\s+)*(?:{_Q}|{_SEC}|this section)")
_OTHER = re.compile(r"\s+of\s+(?:the\s+(?:(?:\(?[A-Z][\w’]*\)?|of)\s+){0,8}?(?:Act|Code|Sanhita)\b(?:\s+of\s+(?:[A-Z]\w*\s*)+)?|that\s+section)")
_ROOT = re.compile(r"(?:IPC|BNS) \d+[A-Z]*")


@dataclass(frozen=True)
class Edge:
    source: str
    matched: str
    target: str | None  # None when unresolved
    reason: str | None


def _labels(text: str) -> list[str]:
    return re.findall(r"\((\w+)\)", text)


def _paths(act: str, root: str, matched: str) -> list[str]:
    """Candidate citations a matched reference points to."""
    segs = re.split(r"\s+of\s+", matched)
    quals = [s for s in segs if re.match(r"(?:sub-section|clause)", s)]
    anchor = segs[-1]
    if anchor.startswith("section"):
        starts = [(f"{act} {re.match(r'[0-9]+[A-Z]*', t)[0]}", _labels(t)) for t in re.findall(_NUM, anchor)]
    else:
        starts = [(root, [])]
    levels = [_labels(q) for q in reversed(quals)]
    # a qualifier binds the first section of a list only: "sub-section (2) of section 310, 311"
    return [b + "".join(f"({x})" for x in pre + list(combo))
            for i, (b, pre) in enumerate(starts) for combo in (itertools.product(*levels) if i == 0 else [()])]


def extract(provisions: list[Provision]) -> list[Edge]:
    """One edge per reference target, in document order; each reference belongs to the deepest
    provision containing it (a child's text is cut out of its parent's)."""
    by_cite = {p.citation: p for p in provisions}
    edges: list[Edge] = []
    for p in provisions:
        own = p.text
        for c in p.children:
            own = own.replace(by_cite[c].text, " ", 1)
        act, root = p.citation[:3], _ROOT.match(p.citation)[0]
        for m in _REF.finditer(own):
            matched = m[0]
            other = _OTHER.match(own, m.end())
            if other:
                why = "names an earlier section" if "that" in other[0] else "other Act"
                edges.append(Edge(p.citation, matched, None, f"{why}:{other[0]}"))
            elif re.fullmatch(r"clauses?\s+.*", matched) and " of " not in matched:
                edges.append(Edge(p.citation, matched, None, "clause without a section"))
            else:
                for cite in _paths(act, root, matched):
                    ok = cite in by_cite
                    edges.append(Edge(p.citation, matched, cite if ok else None, None if ok else f"no such provision {cite}"))
    return edges


def chains(provisions: list[Provision], edges: list[Edge]) -> dict[str, list[str]]:
    """Per provision, the resolved targets of its own text and its descendants', first appearance first."""
    own: dict[str, list[str]] = {}
    for e in edges:
        if e.target:
            own.setdefault(e.source, []).append(e.target)
    kids = {p.citation: p.children for p in provisions}

    def walk(c: str) -> list[str]:
        return own.get(c, []) + [t for k in kids[c] for t in walk(k)]

    return {p.citation: list(dict.fromkeys(walk(p.citation))) for p in provisions}
