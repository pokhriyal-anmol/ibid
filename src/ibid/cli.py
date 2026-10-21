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


def missing_pdf(a: argparse.Namespace) -> bool:
    """True after printing the error and the setup hint if a source PDF this command reads is absent."""
    paths = [getattr(a, k) for k in ("bns", "ipc") if hasattr(a, k)]
    if a.cmd == "headings":  # reads one Act, or a layout text file instead of the BNS PDF
        paths = [a.ipc] if a.act == "ipc" else [] if a.layout else [a.bns]
    for path in paths:
        if not Path(path).is_file():
            print(f"error: no such file: {path}\nrun: ibid setup", file=sys.stderr)
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ibid")
    sub = ap.add_subparsers(dest="cmd", required=True)
    su = sub.add_parser("setup", help="check poppler tools and source PDFs, offline")
    su.add_argument("--sources", default="data/sources.json")
    su.add_argument("--raw-dir", default="data/raw")
    su.add_argument("--fetch", choices=["bns", "ipc"], help="download this source PDF, verified, never overwriting")
    su.add_argument("--url", help="direct https PDF url (required for --fetch ipc)")
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
    chs = sub.add_parser("charges").add_subparsers(dest="charges_cmd", required=True)
    chv = chs.add_parser("validate")
    chv.add_argument("--set", required=True)
    chv.add_argument("--index", default="data/index/ibid.sqlite")
    chi = chs.add_parser("intake", help="turn person-written query blocks into a draft set")
    chi.add_argument("--queries", required=True)
    chi.add_argument("--author-type", choices=("owner", "lawyer"), required=True)
    chi.add_argument("--author", required=True)
    chi.add_argument("--out", required=True)
    chc = chs.add_parser("score", help="score the frozen rule by charge on one Act")
    chc.add_argument("--set", required=True)
    chc.add_argument("--index", default="data/index/ibid.sqlite")
    chc.add_argument("--frozen-rule", default="results/frozen-rule.json")
    chc.add_argument("--predictions", default=None, help="a layer's predictions file, scored in place of --frozen-rule")
    chc.add_argument("--act", choices=("ipc", "bns"), required=True)
    chc.add_argument("--out", required=True)
    chc.add_argument("--ledger", default=None, help="default: <set>.ledger.json beside the set")
    chc.add_argument("--rescore", action="store_true", help="with --predictions: score a layer version again on a set and Act it was already scored on")
    che = chs.add_parser("export-baseline", help="write the frozen rule's two output rules as predictions files")
    che.add_argument("--set", required=True)
    che.add_argument("--index", default="data/index/ibid.sqlite")
    che.add_argument("--frozen-rule", default="results/frozen-rule.json")
    che.add_argument("--out", required=True, help="writes <stem>.baseline-topk<suffix> and <stem>.baseline-threshold<suffix>")
    cmp_ = chs.add_parser("compare", help="one report across layers and sets, from results files")
    cmp_.add_argument("--results", action="append", required=True)
    cmp_.add_argument("--set", action="append", required=True, help="every set the results files name, matched by hash")
    cmp_.add_argument("--ilsi", action="append", default=[], help="an ILSI test result, reported as a separate task")
    cmp_.add_argument("--out", required=True)
    mc = sub.add_parser("mcp", help="stdio MCP server over the deterministic lookups")
    mc.add_argument("--bns", default=os.environ.get("IBID_BNS_PDF", "data/raw/bns-prs.pdf"))
    mc.add_argument("--ipc", default=os.environ.get("IBID_IPC_PDF", "data/raw/ipc-wipo.pdf"))
    mc.add_argument("--concordance", default="concordance/v3.json")
    hd = sub.add_parser("headings").add_subparsers(dest="headings_cmd", required=True).add_parser(
        "list", help="section headings, one citation and heading per line")
    hd.add_argument("--act", choices=("bns", "ipc"), required=True)
    hd.add_argument("--bns", default=os.environ.get("IBID_BNS_PDF", "data/raw/bns-prs.pdf"))
    hd.add_argument("--ipc", default=os.environ.get("IBID_IPC_PDF", "data/raw/ipc-wipo.pdf"))
    hd.add_argument("--layout", default=None, help="BNS only: read this `pdftotext -layout` text file instead of the PDF")
    cc = sub.add_parser("concordance").add_subparsers(dest="conc_cmd", required=True).add_parser(
        "from-table", help="candidate entries from a published BNS to IPC correspondence table (pdftotext -layout text)")
    cc.add_argument("--table", required=True)
    cc.add_argument("--index", default="data/index/ibid.sqlite")
    cc.add_argument("--out", required=True)
    lsub = sub.add_parser("links").add_subparsers(dest="links_cmd", required=True)
    lk = lsub.add_parser("list", help="IPC definition-punishment links derived from headings")
    lk.add_argument("--index", default="data/index/ibid.sqlite")
    lk.add_argument("--concordance", default="concordance/v3.json")
    le = lsub.add_parser("expand", help="append linked partners to a baseline predictions file, as layer links v1")
    le.add_argument("--predictions", required=True)
    le.add_argument("--index", default="data/index/ibid.sqlite")
    le.add_argument("--concordance", default="concordance/v3.json")
    le.add_argument("--out", required=True)
    lb = lsub.add_parser("bench", help="score links v1 on an ILSI split; the test split once")
    lb.add_argument("--split", required=True)
    lb.add_argument("--labels", default="data/raw/lesicin/label_vocab.json")
    lb.add_argument("--index", default="data/index/ibid.sqlite")
    lb.add_argument("--manifest", default="data/lesicin.manifest.json")
    lb.add_argument("--frozen-rule", default="results/frozen-rule.json")
    lb.add_argument("--ledger", default="results/test-ledger-links.json")
    lb.add_argument("--rescore-test", action="store_true")
    lb.add_argument("--out", required=True)
    ci = sub.add_parser("cited").add_subparsers(dest="cited_cmd", required=True).add_parser(
        "extract", help="route A: sections a query names, mapped to the other Act through verified concordance")
    ci.add_argument("--set", required=True)
    ci.add_argument("--index", default="data/index/ibid.sqlite")
    ci.add_argument("--concordance", required=True)
    ci.add_argument("--out", required=True)
    asc = sub.add_parser("assoc").add_subparsers(dest="assoc_cmd", required=True)
    af = asc.add_parser("fit", help="route B: fit the naive-Bayes layer on a train split minus the held-out set's ids")
    af.add_argument("--source", choices=("ilsi", "ilsic-lay", "union"), default="ilsi")
    af.add_argument("--train", required=True)
    af.add_argument("--holdout-split", help="ilsic-lay: the Layman test split file")
    af.add_argument("--lay-train", help="union: the ILSIC-Lay train file (--train is the ILSI train file)")
    af.add_argument("--lay-holdout-set", help="union: the set v2 file")
    af.add_argument("--min-posts", type=int, default=5)
    af.add_argument("--index", default="data/index/ibid.sqlite")
    af.add_argument("--holdout-set", required=True)
    af.add_argument("--labels", default="data/raw/lesicin/label_vocab.json")
    af.add_argument("--out", required=True)
    apr = asc.add_parser("predict", help="write the layer's predictions file for a multi-charge set")
    apr.add_argument("--model", required=True)
    apr.add_argument("--set", required=True)
    apr.add_argument("--concordance", required=True)
    apr.add_argument("--index", default="data/index/ibid.sqlite")
    apr.add_argument("--out", required=True)
    ae = asc.add_parser("eval", help="score a split with the benchmark's micro-F1, macro-F1 and Jaccard")
    ae.add_argument("--model", required=True)
    ae.add_argument("--split", required=True)
    ae.add_argument("--manifest", default="data/lesicin.manifest.json")
    ae.add_argument("--ledger", default="results/test-ledger-assoc.json")
    ae.add_argument("--labels", default=None, help="ILSI label vocabulary: also report micro-F1 over this (v1's) label space")
    ae.add_argument("--rescore-test", action="store_true")
    ae.add_argument("--out", default=None)
    il = sub.add_parser("ilsic").add_subparsers(dest="ilsic_cmd", required=True).add_parser(
        "eval", help="score the frozen rule on an ILSIC split, paper's label space and vocabulary readings")
    il.add_argument("--split", required=True)
    il.add_argument("--train", required=True, help="the Lay train file, used only to fix the label space")
    il.add_argument("--index", default="data/index/ibid.sqlite")
    il.add_argument("--frozen-rule", default="results/frozen-rule.json")
    il.add_argument("--out", required=True)
    chq = chs.add_parser("subquery", help="route C: retrieve per recorded sub-query with the frozen rule and union")
    chq.add_argument("--set", required=True)
    chq.add_argument("--subqueries", required=True)
    chq.add_argument("--index", default="data/index/ibid.sqlite")
    chq.add_argument("--frozen-rule", default="results/frozen-rule.json")
    chq.add_argument("--per-subquery", type=int, default=2)
    chq.add_argument("--out", required=True)
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
    br.add_argument("--r", type=float, required=True, help="relative threshold in (0, 1]")
    br.add_argument("--rollup", choices=("max", "sum"), default="max")
    br.add_argument("--bm25-k1", type=float, default=1.2)
    br.add_argument("--bm25-b", type=float, default=0.75)
    br.add_argument("--stem", default="none", help="none or suffix")
    br.add_argument("--levels", default="all", help="all, top or leaf")
    br.add_argument("--out", required=True)
    br.add_argument("--sample", nargs="?", type=int, const=200, default=None, metavar="N")
    br.add_argument("--frozen-rule", default="results/frozen-rule.json")
    br.add_argument("--ledger", default="results/test-ledger.json")
    br.add_argument("--rescore-test", action="store_true")
    br.add_argument("--extra-stop-words", default=None, help="a df-stopwords file; its terms join the stop words (changes the rule hash)")
    bd = bsub.add_parser("df-stopwords", help="terms in at least --min-df of a split's fact paragraphs, from text only")
    bd.add_argument("--split", required=True)
    bd.add_argument("--min-df", type=float, required=True)
    bd.add_argument("--out", required=True)
    bv = bsub.add_parser("derive-rule", help="a frozen-rule record with a stop list added, under a new version")
    bv.add_argument("--from", dest="src", default="results/frozen-rule.json")
    bv.add_argument("--stopwords", required=True)
    bv.add_argument("--version", required=True)
    bv.add_argument("--out", required=True)
    bf = bsub.add_parser("freeze")
    bf.add_argument("--log", default="results/optimisation-log.json")
    bf.add_argument("--round", type=int, default=None, help="logged round to freeze, default the last")
    bf.add_argument("--out", default="results/frozen-rule.json")
    ro = bsub.add_parser("round", help="score train and dev with one declared change and append to the log")
    ro.add_argument("--train", required=True)
    ro.add_argument("--dev", required=True)
    ro.add_argument("--labels", default="data/raw/lesicin/label_vocab.json")
    ro.add_argument("--index", default="data/index/ibid.sqlite")
    ro.add_argument("--manifest", default="data/lesicin.manifest.json")
    ro.add_argument("--log", default="results/optimisation-log.json")
    ro.add_argument("--change", action="append", default=[], metavar="KNOB=VALUE")
    ro.add_argument("--k", type=int, help="round 0 only")
    ro.add_argument("--r", type=float, help="round 0 only")
    ro.add_argument("--rollup", choices=("max", "sum"), help="round 0 only, default max")
    rp = bsub.add_parser("report", help="write the report from the log, the test ledger and the test results file")
    rp.add_argument("--log", default="results/optimisation-log.json")
    rp.add_argument("--ledger", default="results/test-ledger.json")
    rp.add_argument("--results", required=True, help="the results file of the test run")
    rp.add_argument("--frozen-rule", default="results/frozen-rule.json", help="the frozen-rule record, names the frozen round")
    rp.add_argument("--out", default="results/report.md")
    a = ap.parse_args(argv)
    if a.cmd == "setup":
        from ibid import setup
        return setup.run(a.sources, a.raw_dir, a.fetch, a.url)
    if missing_pdf(a):
        return 1
    if a.cmd == "mcp":
        from ibid import mcp
        return mcp.serve(a.bns, a.ipc, a.concordance)
    if a.cmd == "headings":
        from ibid import headings
        pairs = (headings.ipc_headings(a.ipc) if a.act == "ipc" else headings.parse_layout(Path(a.layout).read_text())
                 if a.layout else headings.bns_headings(a.bns))
        print("\n".join(headings.report(pairs)))
        return 0
    if a.cmd == "concordance":
        from ibid import table
        return table.from_table(a.table, a.index, a.out)
    if a.cmd == "cited":
        from ibid import cited
        return cited.extract(a.set, a.index, a.concordance, a.out)
    if a.cmd == "charges":
        from ibid import charges
        if a.charges_cmd == "export-baseline":
            return charges.export_baseline(a.set, a.index, a.frozen_rule, a.out)
        if a.charges_cmd == "subquery":
            return charges.subquery(a.set, a.subqueries, a.index, a.frozen_rule, a.per_subquery, a.out)
        if a.charges_cmd == "score" and a.predictions:
            return charges.score_predictions(a.set, a.index, a.predictions, a.act, a.out, a.ledger, a.rescore)
        if a.charges_cmd == "score":
            return charges.score(a.set, a.index, a.frozen_rule, a.act, a.out, a.ledger)
        if a.charges_cmd == "compare":
            from ibid import compare
            return compare.compare(a.results, a.set, a.ilsi, a.out)
        if a.charges_cmd == "intake":
            return charges.intake(a.queries, a.author_type, a.author, a.out)
        return charges.validate(a.set, a.index)
    if a.cmd == "ilsic":
        from ibid import ilsic
        return ilsic.evaluate(a.split, a.train, a.index, a.frozen_rule, a.out)
    if a.cmd == "assoc":
        from ibid import assoc
        if a.assoc_cmd == "fit" and a.source == "union":
            if not (a.lay_train and a.lay_holdout_set and a.holdout_split):
                print("error: --lay-train, --lay-holdout-set and --holdout-split are required with --source union", file=sys.stderr)
                return 1
            return assoc.fit_union({"train": a.train, "holdout_set": a.holdout_set, "labels": a.labels},
                                   {"train": a.lay_train, "holdout_split": a.holdout_split, "holdout_set": a.lay_holdout_set, "index": a.index},
                                   a.min_posts, a.out)
        if a.assoc_cmd == "fit":
            if a.source == "ilsic-lay":
                if not a.holdout_split:
                    print("error: --holdout-split is required with --source ilsic-lay", file=sys.stderr)
                    return 1
                return assoc.fit_ilsic_lay(a.train, a.holdout_split, a.holdout_set, a.index, a.min_posts, a.out)
            return assoc.fit(a.train, a.holdout_set, a.labels, a.out)
        if a.assoc_cmd == "predict":
            return assoc.predict(a.model, a.set, a.concordance, a.index, a.out)
        return assoc.evaluate(a.model, a.split, a.manifest, a.ledger, a.rescore_test, a.out, a.labels)
    if a.cmd == "bench" and a.bench_cmd == "report":
        from ibid.report import run_report
        return run_report(a.log, a.ledger, a.results, a.out, a.frozen_rule)
    if a.cmd == "bench" and a.bench_cmd == "round":
        from ibid.optimise import run_round
        return run_round(a.train, a.dev, a.labels, a.index, a.manifest, a.log, a.change, a.k, a.r, a.rollup)
    if a.cmd == "bench" and a.bench_cmd == "df-stopwords":
        from ibid.bench import df_stopwords
        return df_stopwords(a.split, a.min_df, a.out)
    if a.cmd == "bench" and a.bench_cmd == "derive-rule":
        from ibid.bench import derive_rule
        return derive_rule(a.src, a.stopwords, a.version, a.out)
    if a.cmd == "bench" and a.bench_cmd == "run":
        from ibid.bench import run_bench
        return run_bench(a.split, a.labels, a.index, a.k, a.r, a.rollup, a.out, a.manifest, a.sample,
                         a.frozen_rule, a.ledger, a.rescore_test,
                         {"bm25_k1": a.bm25_k1, "bm25_b": a.bm25_b, "stem": a.stem, "levels": a.levels}, a.extra_stop_words)
    if a.cmd == "bench" and a.bench_cmd == "freeze":
        from ibid.bench import freeze_rule
        return freeze_rule(a.log, a.round, a.out)
    if a.cmd == "bench":
        from ibid.bench import check_labels
        return check_labels(a.data, a.index)
    if a.cmd == "links" and a.links_cmd == "bench":
        from ibid.links import bench
        return bench(a.split, a.labels, a.index, a.manifest, a.frozen_rule, a.ledger, a.rescore_test, a.out)
    if a.cmd == "links" and a.links_cmd == "expand":
        from ibid.links import expand_file
        return expand_file(a.predictions, a.index, a.concordance, a.out)
    if a.cmd == "links":
        from ibid.links import list_links
        import sqlite3
        if err := pin_error(a.concordance, Path(a.concordance).read_bytes()):
            print(err, file=sys.stderr)
            return 1
        db = sqlite3.connect(a.index)
        print("\n".join(list_links(db, concordance.load(a.concordance, db))))
        return 0
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
