"""Regenerate .scratch/slice-7/report.md from the committed results files. Run from the repo root:

  uv run python .scratch/slice-7/report.py > .scratch/slice-7/report.md

Stdlib only, no clock, no randomness: two runs give identical bytes. It asserts its own recall against the
recall stored in every committed results file, so a wrong roll-up or a stale file stops it instead of printing."""
import json
import sys
from pathlib import Path

SETS = {"v1": "gold/multicharge/v1.json", "v2": "gold/multicharge/v2.json"}
ACTS = ("IPC", "BNS")
RULES = (("top-k", "top_k", "topk"), ("threshold", "threshold", "threshold"))
TEST_SHA = "9fc141a94b51febe3e3cd06494f13c587098afcda175fc2e3e4d6213a88b60d1"


def sec(c: str) -> str:
    return c.split("(")[0]  # an accepted sub-provision counts as its section


def load(p: str) -> dict:
    return json.loads(Path(p).read_text())


def cell(gold: list[dict], act: str, base: dict, links: dict) -> dict:
    """Per-charge figures for one set, Act and output rule. A charge is found when any accepted section is predicted."""
    out = dict(charges=0, base_found=0, links_found=0, new=0, added=0, added_ok=0)
    for item in gold:
        counted = [{sec(s) for s in c["sections"][act.lower()]} for c in item["charges"] if c["sections"][act.lower()]]
        if not counted:
            continue
        b, l = base[item["id"]], links[item["id"]]
        assert l[:len(b)] == b, f"originals are not first and in order for {item['id']}"
        pb, pl = {sec(x) for x in b}, {sec(x) for x in l}
        accepted = set().union(*counted)
        out["charges"] += len(counted)
        out["base_found"] += sum(bool(c & pb) for c in counted)
        out["links_found"] += sum(bool(c & pl) for c in counted)
        out["new"] += sum(bool(c & pl) and not c & pb for c in counted)
        out["added"] += len(pl - pb)
        out["added_ok"] += len((pl - pb) & accepted)
    return out


def pct(a: int, b: int) -> str:
    return f"{100 * a / b:.1f}" if b else "-"


def multicharge() -> tuple[list[str], dict]:
    rows, cells = [], {}
    for sname, spath in SETS.items():
        gold = load(spath)["items"]
        for act in ACTS:
            base_doc = load(f"results/multicharge-{sname}-{act.lower()}.json")
            for rule, key, file_key in RULES:
                links_doc = load(f"results/multicharge-{sname}-links-{file_key}-{act.lower()}.json")
                c = cell(gold, act, base_doc[key]["predictions"], links_doc["output"]["predictions"])
                for name, recall, found in (("baseline", base_doc[key]["recall"], c["base_found"]), ("links", links_doc["output"]["recall"], c["links_found"])):
                    assert round(found / c["charges"], 6) == recall, f"{name} {sname} {act} {rule}: recomputed {found}/{c['charges']} != stored {recall}"
                cells[(sname, act, rule)] = c
                rows.append(f"| {sname} | {act} | {rule} | {c['charges']} | {c['base_found']} | {c['links_found']} | {c['new']} | {c['added']} | {c['added_ok']} | {pct(c['added_ok'], c['added'])} |")
    return rows, cells


def ilsi() -> tuple[list[str], dict]:
    base = next(e for e in load("results/test-ledger.json") if e["split_sha256"] == TEST_SHA)
    links = [e for e in load("results/test-ledger-links.json") if e["split_sha256"] == TEST_SHA]
    assert len(links) == 1, "links v1 must be scored on the test split exactly once"
    f = {"top-k": (base["scores"]["micro_f1"], links[0]["outputs"]["top-k"]["scores"]["micro_f1"]),
         "threshold": (base["threshold_scores"]["micro_f1"], links[0]["outputs"]["threshold"]["scores"]["micro_f1"])}
    rows = [f"| {r} | {100 * b:.2f} | {100 * l:.2f} | {100 * (l - b):+.2f} | {'rises' if l > b else 'equal' if l == b else 'falls'} |" for r, (b, l) in f.items()]
    return rows, f


def main() -> None:
    rows, cells = multicharge()
    irows, f = ilsi()
    # Owner decision D-002 (2026-10-17): recall is compared per set and Act, summed over the two output rules.
    pooled = {(s, a): (sum(c["base_found"] for k, c in cells.items() if k[:2] == (s, a)), sum(c["links_found"] for k, c in cells.items() if k[:2] == (s, a))) for s in SETS for a in ACTS}
    kept = all(l > b for b, l in pooled.values()) and all(l >= b for b, l in f.values())
    flat = sum(c["links_found"] <= c["base_found"] for c in cells.values())
    tot = {k: sum(c[k] for c in cells.values()) for k in ("new", "added", "added_ok")}
    o = ["# Slice 7: the verdict on `links v1`", "",
         f"**Verdict: {'KEPT as an opt-in output only' if kept else 'NEGATIVE'}.** The owner chose the reading on 2026-10-17 (D-002): per-charge recall is compared per set and Act, as `CONTEXT.md` defines the Baseline, summed over the two output rules. The spec left the level open and the first report pooled over Acts, after scores existed; that reading is withdrawn. Nothing is wired into `src/ibid/mcp.py`.", "",
         "## The rule applied", "",
         "Kept only if per-charge recall rises on both multi-charge sets (v1 and v2) and ILSI test micro-F1 does not fall. "
         "Recall is the charges found for one set and Act, summed over both output rules, against the same count for the baseline.", "",
         "| set | Act | baseline found | links v1 found | recall rises |", "| --- | --- | --- | --- | --- |"]
    o += [f"| {s} | {a} | {b} | {l} | {'yes' if l > b else 'no'} |" for (s, a), (b, l) in pooled.items()]
    o += ["", "| output rule | baseline test micro-F1 % | links v1 % | change (points) | micro-F1 |", "| --- | --- | --- | --- | --- |"] + irows
    o += ["", "## Per set, Act and output rule", "",
          "Added predictions are the sections links v1 appends that the baseline did not predict. An added prediction is correct when it is an accepted section of any charge of its item. Set v2 labels are incomplete, so the correct share there is a floor.", "",
          "| set | Act | output | charges | found, baseline | found, links v1 | newly found | predictions added | added, correct | correct share % |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"] + rows
    o += ["", f"All eight cells together: {tot['new']} charges newly found by {tot['added']} added predictions, of which {tot['added_ok']} ({pct(tot['added_ok'], tot['added'])} %) are correct.",
          f"Cells where links v1 finds no more charges than the baseline: {flat} of {len(cells)}. A stricter reading of the rule, where every cell must rise, would change the verdict if this count is above zero.", ""]
    sys.stdout.write("\n".join(o))


main()
