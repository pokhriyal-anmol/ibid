"""`ibid freeze`: apply the human review sheet to the drafts, write v1 gold, concordance and pin.

No model is called. Refuses unless the sheet has enough marked items, every sampled item is
marked once, and nothing failed (or `--drop-failed` is given, which drops and records them).
"""
import hashlib
import json
import re
import sys
from pathlib import Path

CORR = ("ipc_to_bns", "bns_to_ipc")
MIN_CHECKED, MIN_CORR = 12, 8


def parse_sheet(text: str) -> dict[str, str]:
    """id -> 'pass' | 'fail' | 'unmarked' from `## id` blocks holding `[x] pass` or `[x] fail`."""
    marks = {}
    for block in re.split(r"^## ", text, flags=re.M)[1:]:
        item_id, _, body = block.partition("\n")
        if "result:" not in body:
            continue
        p, f = (bool(re.search(rf"\[[xX]\]\s*{w}\b", body)) for w in ("pass", "fail"))
        marks[item_id.strip()] = "pass" if p and not f else "fail" if f and not p else "unmarked"
    return marks


def delegated_ids(text: str) -> set[str]:
    """Sheet ids whose block says `- checked by: agent`: the owner delegated the check to an agent."""
    return {b.partition("\n")[0].strip() for b in re.split(r"^## ", text, flags=re.M)[1:]
            if re.search(r"^- checked by: agent\b", b, re.M)}


def to_eval_item(item: dict, sources: dict[str, str]) -> dict:
    """Draft shape -> the shape `ibid eval` reads; provenance fields are kept."""
    out = {k: v for k, v in item.items() if k not in ("expected_targets", "expected_citations", "expected_type")}
    out["source_sha256"] = sources  # the pinned PDFs the page numbers refer to
    if item["category"] in CORR:
        out["expected"] = [{"type": item["expected_type"], "citations": item["expected_citations"]}]
    elif item["category"] == "keyword":
        out["expected_citations"] = item["expected_citations"]
    elif item["category"] == "cross_reference_chain":
        out["expected_refs"] = item["expected_targets"]
    return out


def freeze(sheet: str, draft_gold: str, draft_conc: str, out_gold: str, out_conc: str, drop_failed: bool = False, sources: dict[str, str] | None = None) -> int:
    marks = parse_sheet(Path(sheet).read_text())
    gold = json.loads(Path(draft_gold).read_text())
    problems = [f"{i}: {m}" for i, m in marks.items() if m == "unmarked"]
    unknown = [i for i in marks if i not in {g["id"] for g in gold}]
    checked = {i for i, m in marks.items() if m != "unmarked"}
    corr = {i for i in checked if i.startswith(CORR)}
    if unknown:
        problems.append(f"sheet ids not in the draft gold: {unknown}")
    if len(checked) < MIN_CHECKED or len(corr) < MIN_CORR:
        problems.append(f"need at least {MIN_CHECKED} checked items, {MIN_CORR} correspondence; have {len(checked)}, {len(corr)}")
    failed = sorted(i for i, m in marks.items() if m == "fail")
    if failed and not drop_failed:
        problems.append(f"failed items (fix them or pass --drop-failed): {failed}")
    if problems:
        print("error: freeze refused:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    kept = [g for g in gold if g["id"] not in failed]
    # Unsampled entries rest on agent refutation only; the file says so.
    delegated = delegated_ids(Path(sheet).read_text())

    def passed_item(e: dict) -> str | None:
        for g in kept:
            if g["id"] not in corr:
                continue
            src, dst = (e["ipc"], e["bns"]) if g["category"] == "ipc_to_bns" else (e["bns"], e["ipc"])
            if g["query"] in src and sorted(dst) == sorted(g["expected_citations"]) and e["type"] == g["expected_type"]:
                return g["id"]
        return None

    def basis(item_id: str | None) -> str:
        if item_id is None:
            return "refuted-by-agent"
        return "agent-checked-for-owner" if item_id in delegated else "human-checked"

    # Only an entry matched by a passed sheet item is served; the rest stay verified:false.
    # An entry the correspondence-table check already served keeps its basis; the sheet does not demote it.
    conc = [e if e.get("basis") == "source-table-checked" and e["verified"] else
            {**e, "verified": (i := passed_item(e)) is not None, "basis": basis(i)}
            for e in json.loads(Path(draft_conc).read_text())]
    gold_bytes = (json.dumps([to_eval_item(g, sources or {}) for g in kept], indent=2, sort_keys=True) + "\n").encode()
    Path(out_gold).write_bytes(gold_bytes)
    Path(out_gold).with_suffix(".sha256").write_text(hashlib.sha256(gold_bytes).hexdigest() + "\n")
    Path(out_gold).with_suffix(".review.json").write_text(json.dumps({"marks": marks, "dropped": failed, "agent_checked_for_owner": sorted(delegated & set(marks))}, indent=2, sort_keys=True) + "\n")
    conc_bytes = (json.dumps(conc, indent=2, sort_keys=True) + "\n").encode()
    Path(out_conc).write_bytes(conc_bytes)
    Path(out_conc).with_suffix(".sha256").write_text(hashlib.sha256(conc_bytes).hexdigest() + "\n")
    print(f"frozen {len(kept)} gold items, {len(conc)} concordance entries ({sum(e["verified"] for e in conc)} verified), {len(failed)} dropped")
    return 0
