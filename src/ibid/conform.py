"""`ibid conform`: apply the declared text conventions to the agent-drafted gold. No model.

Conventions: amendment brackets are not text; a sub-provision starts at its own label, with no
section-number prefix; a provision's text includes its attached illustrations and explanations;
keyword answers are provision-level sets.

The system's text is never copied wholesale. Drafted text is extended only when it is an exact
prefix of the system text and the remainder (an illustration, explanation, exception or proviso)
is found, in order, on the cited PDF pages. Anything else is reported, not changed.
"""
import json
import re
from pathlib import Path

from ibid import index
from ibid.ipc import parse_ipc
from ibid.parse import parse_bns

REMAINDER_START = re.compile(r"(?:Illustrations?|Explanations?|Exceptions?|Provided)\b|\(\w+\)")
NEXT_SECTION = re.compile(r"\s\d{1,3}[A-Z]{0,2}\.\s+[A-Z]")
PAGE_SPAN = 3  # a section can run over a page break


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("[", "").replace("]", "")).strip()


def strip_section_prefix(query: str, text: str) -> str:
    return re.sub(r"^\d+[A-Z]*\.\s*", "", text) if "(" in query else text


def is_subsequence(needle: list[str], hay: list[str]) -> bool:
    it = iter(hay)
    return all(w in it for w in needle)


def can_extend(drafted: str, system: str, page_words: list[str]) -> bool:
    """True when `system` is `drafted` plus an illustration or explanation that is on the page."""
    if system == drafted or not system.startswith(drafted):
        return False
    rest = system[len(drafted):].strip()
    if not REMAINDER_START.match(rest) or NEXT_SECTION.search(" " + rest):
        return False
    return is_subsequence(rest.split(), page_words)


def page_words(pages_dir: str, act: str, page: int) -> list[str]:
    words = []
    for p in range(page, page + PAGE_SPAN):
        f = Path(pages_dir) / act.lower() / f"{p:03d}.txt"
        if f.is_file():
            words += norm(f.read_text()).split()
    return words


def top(citation: str) -> str:
    return re.match(r"(?:BNS|IPC) \d+[A-Z]*", citation).group(0)


def conform(gold_path: str, out_path: str, bns_pdf: str, ipc_pdf: str, pages_dir: str, index_path: str, sheet_path: str | None = None, drop: dict[str, str] | None = None) -> list[str]:
    provisions = parse_bns(bns_pdf) + parse_ipc(ipc_pdf)
    from ibid.xref import extract
    db = index.build(index_path, provisions, extract(provisions))
    # Dropped by name, with a reason a reader can check at the source; never by "the system fails it".
    drop = drop or {}
    items, report = [i for i in json.loads(Path(gold_path).read_text()) if i["id"] not in drop], []
    Path(out_path).with_suffix(".dropped.json").write_text(json.dumps(drop, indent=2, sort_keys=True) + "\n")
    for item in items:
        if "expected_text" in item:
            drafted = strip_section_prefix(item["query"], norm(item["expected_text"]))
            got = index.lookup(db, item["query"])
            system = norm(got[0]) if got else ""
            if system == drafted:
                item["expected_text"] = drafted
            elif can_extend(drafted, system, page_words(pages_dir, item["act"], item["page"])):
                item["expected_text"], item["conformed"] = system, "extended"
            else:
                report.append(f"{item['id']} {item['query']}: not conformed (drafted {len(drafted)} chars, system {len(system)})")
        elif item["category"] == "keyword":
            found = {c: t for c, t in index.search(db, item["query"], 100)}
            gold = set(item["expected_citations"])
            word = re.compile(rf"\b{re.escape(item['query'])}\b", re.I)
            extras = sorted(set(found) - gold)
            ok = [c for c in extras if top(c) in {top(g) for g in gold} and word.search(found[c])]
            if gold - set(found) or len(ok) != len(extras):
                report.append(f"{item['id']} {item['query']}: not conformed (missing {sorted(gold - set(found))}, unaccepted extras {sorted(set(extras) - set(ok))})")
            else:
                item["expected_citations"], item["conformed"] = sorted(gold | set(ok)), "provision-level"
    Path(out_path).write_text(json.dumps(items, indent=2, sort_keys=True) + "\n")
    if sheet_path:
        rewrite_sheet(sheet_path, items)
    return report


def rewrite_sheet(sheet_path: str, items: list[dict]) -> None:
    """Refresh each item's `- expected:` line from the conformed gold; marks are untouched."""
    by_id = {i["id"]: i for i in items}
    out, current = [], None
    for line in Path(sheet_path).read_text().splitlines():
        if line.startswith("## "):
            current = by_id.get(line[3:].strip())
        elif line.startswith("- expected:") and current is not None and "expected_text" in current:
            line = f"- expected: {json.dumps(current['expected_text'], ensure_ascii=False)}"
        out.append(line)
    Path(sheet_path).write_text("\n".join(out) + "\n")
