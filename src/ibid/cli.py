"""`ibid eval`: parse, index, answer the gold set, score, write the results file."""
import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from ibid import concordance, index
from ibid.ipc import IPC_TOTAL, parse_ipc
from ibid.parse import BNS_TOTAL, PARSER_VERSION, parse_bns
from ibid.xref import extract


DIRECTIONS = {"ipc_to_bns": ("ipc", "bns"), "bns_to_ipc": ("bns", "ipc")}


def pin_error(gold_path: str, gold_bytes: bytes) -> str | None:
    """Scored mode: the pin file `<gold>.sha256` beside the gold file must hold its SHA-256."""
    pin = Path(gold_path).with_suffix(".sha256")
    if not pin.is_file():
        return f"no pin file {pin}"
    if pin.read_text().strip() != hashlib.sha256(gold_bytes).hexdigest():
        return f"{gold_path} does not match its pin {pin}"
    return None


def run_eval(gold_path: str, bns_pdf: str, ipc_pdf: str, index_path: str, out_path: str, concordance_path: str | None = None, mode: str = "scored") -> int:
    gold_bytes = Path(gold_path).read_bytes()
    if mode == "scored" and (err := pin_error(gold_path, gold_bytes)):
        print(f"error: scored mode refused: {err}", file=sys.stderr)
        return 1
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
    db = index.build(index_path, provisions, extract(provisions))
    try:
        entries = concordance.load(concordance_path, db) if concordance_path else []
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    outcomes, cats = [], defaultdict(lambda: {"passed": 0, "total": 0})
    for item in json.loads(gold_bytes):
        outcome = {"id": item["id"], "category": item["category"]}
        if item["category"] == "keyword":
            packet = index.search(db, item["query"], index.KEYWORD_LIMIT)
            # Scored as a set: the order is BM25 rank and cannot be authored independently of the system.
            ok = {c for c, _ in packet} == set(item["expected_citations"])
            outcome["packet"] = packet
        elif item["category"] in DIRECTIONS:
            got = concordance.lookup(entries, item["query"], *DIRECTIONS[item["category"]])
            ok = got == item["expected"]
            outcome["packet"] = got
        else:
            got = index.lookup(db, item["query"])
            ok = got is not None and got[0] == item["expected_text"] and got[1] == item.get("expected_children", got[1])
            if item["category"] == "cross_reference_chain":
                ok = ok and got[2] == item["expected_refs"]
                outcome["packet"] = [(c, index.lookup(db, c)[0]) for c in got[2]]
        if "conformed" in item:  # system-conformed, not independently authored
            outcome["conformed"] = item["conformed"]
        outcomes.append({**outcome, "pass": ok})
        cats[item["category"]]["total"] += 1
        cats[item["category"]]["passed"] += ok
    results = {
        "mode": mode,
        "gold_version": Path(gold_path).stem,
        "gold_sha256": hashlib.sha256(gold_bytes).hexdigest(),
        "concordance": {"file": Path(concordance_path).name, "sha256": hashlib.sha256(Path(concordance_path).read_bytes()).hexdigest()} if concordance_path else None,
        "parser_version": PARSER_VERSION,
        "sections": counts,
        "categories": cats,
        "outcomes": outcomes,
        "xref": {act: index.ref_counts(db, act) for act in ("BNS", "IPC")},
        "unresolved_xref": index.unresolved(db),
    }
    with open(out_path, "w") as f:
        f.write(json.dumps(results, indent=2, sort_keys=True) + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ibid")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ev = sub.add_parser("eval")
    ev.add_argument("--gold", default="gold/v2.json")
    ev.add_argument("--bns", default=os.environ.get("IBID_BNS_PDF", "data/raw/bns-prs.pdf"))
    ev.add_argument("--ipc", default=os.environ.get("IBID_IPC_PDF", "data/raw/ipc-wipo.pdf"))
    ev.add_argument("--mode", choices=["scored", "draft"], default="scored")
    ev.add_argument("--index", default="data/index/ibid.sqlite")
    ev.add_argument("--out", default="results.json")
    ev.add_argument("--concordance", default=None)
    fz = sub.add_parser("freeze")
    fz.add_argument("--sheet", default=".scratch/slice-1/review-sheet.md")
    fz.add_argument("--draft-gold", default="gold/v1.conformed.json")
    fz.add_argument("--draft-conc", default="concordance/draft.json")
    fz.add_argument("--out-gold", default="gold/v2.json")
    fz.add_argument("--out-conc", default="concordance/v2.json")
    fz.add_argument("--bns", default=os.environ.get("IBID_BNS_PDF", "data/raw/bns-prs.pdf"))
    fz.add_argument("--ipc", default=os.environ.get("IBID_IPC_PDF", "data/raw/ipc-wipo.pdf"))
    fz.add_argument("--drop-failed", action="store_true")
    cf = sub.add_parser("conform")
    cf.add_argument("--gold", default="gold/v1.draft.json")
    cf.add_argument("--out", default="gold/v1.conformed.json")
    cf.add_argument("--sheet", default=".scratch/slice-1/review-sheet.md")
    cf.add_argument("--bns", default=os.environ.get("IBID_BNS_PDF", "data/raw/bns-prs.pdf"))
    cf.add_argument("--ipc", default=os.environ.get("IBID_IPC_PDF", "data/raw/ipc-wipo.pdf"))
    cf.add_argument("--pages", default="data/raw/pages")
    cf.add_argument("--index", default="data/index/conform.sqlite")
    cf.add_argument("--drop", action="append", default=[], metavar="ID=REASON")
    bsub = sub.add_parser("bench").add_subparsers(dest="bench_cmd", required=True)
    bn = bsub.add_parser("check-labels")
    bn.add_argument("--data", default="data/raw/lesicin/label_vocab.json")
    bn.add_argument("--index", default="data/index/ibid.sqlite")
    br = bsub.add_parser("run")
    br.add_argument("--split", required=True)
    br.add_argument("--labels", default="data/raw/lesicin/label_vocab.json")
    br.add_argument("--index", default="data/index/ibid.sqlite")
    br.add_argument("--manifest", default="data/lesicin.manifest.json")
    br.add_argument("--k", type=int, required=True)
    br.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "bench" and a.bench_cmd == "run":
        from ibid.bench import run_bench
        return run_bench(a.split, a.labels, a.index, a.k, a.out, a.manifest)
    if a.cmd == "bench":
        from ibid.bench import check_labels
        return check_labels(a.data, a.index)
    if a.cmd == "conform":
        from ibid.conform import conform
        report = conform(a.gold, a.out, a.bns, a.ipc, a.pages, a.index, a.sheet, dict(d.split("=", 1) for d in a.drop))
        print("\n".join(report) or "all items conform")
        return 1 if report else 0
    if a.cmd == "freeze":
        from ibid.freeze import freeze
        sources = {act: hashlib.sha256(Path(p).read_bytes()).hexdigest() for act, p in (("BNS", a.bns), ("IPC", a.ipc))}
        return freeze(a.sheet, a.draft_gold, a.draft_conc, a.out_gold, a.out_conc, a.drop_failed, sources)
    return run_eval(a.gold, a.bns, a.ipc, a.index, a.out, a.concordance, a.mode)


if __name__ == "__main__":
    sys.exit(main())
