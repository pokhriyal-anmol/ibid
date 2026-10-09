"""`ibid eval`: parse, index, answer the gold set, score, write the results file."""
import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from ibid import index
from ibid.ipc import IPC_TOTAL, parse_ipc
from ibid.parse import BNS_TOTAL, PARSER_VERSION, parse_bns


def run_eval(gold_path: str, bns_pdf: str, ipc_pdf: str, index_path: str, out_path: str) -> int:
    provisions, counts = [], {}
    for act, parse, total, pdf in (("BNS", parse_bns, BNS_TOTAL, bns_pdf), ("IPC", parse_ipc, IPC_TOTAL, ipc_pdf)):
        parsed = parse(pdf)
        recovered = sum(p.parent is None for p in parsed)
        print(f"{act}: {recovered}/{total}")
        if recovered != total:
            print(f"error: {act} section count does not match the known total", file=sys.stderr)
            return 1
        provisions += parsed
        counts[act] = {"recovered": recovered, "expected": total}
    gold_bytes = Path(gold_path).read_bytes()
    db = index.build(index_path, provisions)
    outcomes, cats = [], defaultdict(lambda: {"passed": 0, "total": 0})
    for item in json.loads(gold_bytes):
        got = index.lookup(db, item["query"])
        ok = got is not None and got[0] == item["expected_text"] and got[1] == item.get("expected_children", got[1])
        outcomes.append({"id": item["id"], "category": item["category"], "pass": ok})
        cats[item["category"]]["total"] += 1
        cats[item["category"]]["passed"] += ok
    results = {
        "gold_sha256": hashlib.sha256(gold_bytes).hexdigest(),
        "parser_version": PARSER_VERSION,
        "sections": counts,
        "categories": cats,
        "outcomes": outcomes,
    }
    with open(out_path, "w") as f:
        f.write(json.dumps(results, indent=2, sort_keys=True) + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ibid")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ev = sub.add_parser("eval")
    ev.add_argument("--gold", default="gold/draft.json")
    ev.add_argument("--bns", default=os.environ.get("IBID_BNS_PDF", "data/raw/bns-prs.pdf"))
    ev.add_argument("--ipc", default=os.environ.get("IBID_IPC_PDF", "data/raw/ipc-wipo.pdf"))
    ev.add_argument("--index", default="data/index/ibid.sqlite")
    ev.add_argument("--out", default="results.json")
    a = ap.parse_args(argv)
    return run_eval(a.gold, a.bns, a.ipc, a.index, a.out)


if __name__ == "__main__":
    sys.exit(main())
