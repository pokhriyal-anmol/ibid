"""`ibid cited extract`: route A, the sections a raw query names, mapped to the other Act.

Code only (ADR 0001). Reads each item's `id` and `query` and nothing else: no label from any set and no
retrieval output is read. A number is returned only when the text names its Act in the same sentence;
otherwise it is counted as ambiguous and dropped. Mapping to the other Act uses verified concordance
entries only, and a citation with none is counted as unmapped and gives no prediction.
"""
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

from ibid import bench, concordance, index

_KEYWORD = r"(?:sections?|secs?\.?|ss\.?|s\.|u/ss?\.?)\s*"
_NUM = r"\d{1,3}(?:-?[A-Za-z](?![A-Za-z0-9]))?(?:\(\w{1,4}\))*(?![\d])"
_LIST = rf"{_NUM}(?:\s*(?:,|/|&|\band\b|\bor\b)\s*{_NUM})*"
_ACT = (r"(?P<ipc>\bI\.?P\.?C\.?(?![A-Za-z])|\bIndian\s+Penal\s+Code(?:,?\s*1860)?)"
        r"|(?P<bns>\bB\.?N\.?S\.?(?![A-Za-z])|\bBharatiya\s+Nyaya\s+Sanhita(?:,?\s*2023)?)"
        r"|(?P<other>\bCr\.?\s?P\.?\s?C\.?(?![A-Za-z])|\bCode\s+of\s+Criminal\s+Procedure|\bBNSS\b|\bPOCSO\b|\bNDPS\b"
        r"|\bBharatiya\s+Nagarik\s+Suraksha\s+Sanhita|(?-i:\b(?:[A-Z][\w.&-]*\s+){1,6}Act\b))")
GROUP = re.compile(rf"\b{_KEYWORD}(?P<nums>{_LIST})", re.I)
ACT = re.compile(_ACT, re.I)
DIRECT = re.compile(rf"\s*,?\s*(?:of\s+(?:the\s+)?)?(?:{_ACT})", re.I)
JOIN = re.compile(r"\s*(?:,|&|and|read\s+with|r/w|along\s+with|with)\s*", re.I)
SENTENCE = re.compile(r"[.;]\s+(?=[A-Z])")
NUM_PART = re.compile(r"(\d{1,3})(?:-?([A-Za-z]))?")


def _numbers(nums: str) -> list[str]:
    return [a + (b.upper() if b else "") for a, b in NUM_PART.findall(re.sub(r"\(\w+\)", "", nums))]


def _sentence_mentions(s: str) -> list[tuple[str, list[str]]]:
    """(act kind or None, section numbers) per group in one sentence, in text order. Attribution is by the text only."""
    groups = list(GROUP.finditer(s))
    acts = list(ACT.finditer(s))
    kinds: list[str | None] = [None] * len(groups)
    taken = set()
    for n, g in enumerate(groups):
        if d := DIRECT.match(s, g.end()):
            kinds[n] = d.lastgroup
            taken.update(a.start() for a in acts if g.end() <= a.start() < d.end())  # that Act belongs to this group
    for n in range(len(groups) - 2, -1, -1):  # "Section 420 read with Section 34 IPC": the chain shares the last Act
        if kinds[n] is None and JOIN.fullmatch(s[groups[n].end():groups[n + 1].start()]):
            kinds[n] = kinds[n + 1]
    for n, g in enumerate(groups):
        if kinds[n] is None:
            free = [a for a in acts if a.start() not in taken]
            if free:
                kinds[n] = min(free, key=lambda a: min(abs(a.start() - g.end()), abs(g.start() - a.end()))).lastgroup
    return [(k, _numbers(g.group("nums"))) for k, g in zip(kinds, groups)]


def parse_query(text: str) -> list[tuple[str | None, str]]:
    """(act kind 'ipc'|'bns'|'other'|None, section number such as '304B') for every number the text cites."""
    return [(k, n) for s in SENTENCE.split(text) for k, nums in _sentence_mentions(s) for n in nums]


def _section(c: str) -> str:
    return c.split("(")[0]


def _map(entries: list[dict], c: str, src: str, dst: str) -> list[str]:
    return [d for e in entries if e["verified"] and any(_section(x) == c for x in e[src]) for d in e[dst]]


def extract(set_path: str, index_path: str, concordance_path: str, out_path: str) -> int:
    try:
        raw = Path(set_path).read_bytes()
        items = [(i["id"], i["query"]) for i in json.loads(raw)["items"]]
        db = sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)
        entries = concordance.load(concordance_path, db)
    except (OSError, KeyError, ValueError, TypeError, sqlite3.Error) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    counts, out = Counter(), {}
    for iid, query in items:
        got = {"ipc": set(), "bns": set()}
        for kind, num in parse_query(query):
            if kind is None:
                counts["ambiguous_mentions"] += 1
            elif kind == "other":
                counts["other_act_dropped"] += 1
            elif index.lookup(db, c := f"{kind.upper()} {num}") is None:
                counts["not_in_act_dropped"] += 1
            else:
                got[kind].add(c)
                other = "bns" if kind == "ipc" else "ipc"
                if mapped := _map(entries, c, kind, other):
                    got[other].update(mapped)
                else:
                    counts["unmapped_citations"] += 1
        out[iid] = {a: sorted(v) for a, v in got.items()}
    doc = {"layer": "cited", "layer_version": "v1", "set_sha256": bench.sha256(set_path),
           "inputs": {"concordance": bench.sha256(concordance_path), "index": bench.sha256(index_path)},
           "items": out,
           "counts": {k: counts[k] for k in ("ambiguous_mentions", "other_act_dropped", "not_in_act_dropped", "unmapped_citations")}}
    Path(out_path).write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    return 0
