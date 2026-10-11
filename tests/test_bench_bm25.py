"""Slice 2 ticket 11: Python BM25 and the bm25_k1, bm25_b, stem and levels knobs. Invented fixture only."""
import contextlib
import io
import json
import re
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ibid import bench, bm25, index
from ibid.cli import main
from ibid.parse import Provision


def prov(cite, text, parent=None, children=()):
    return Provision(cite, text, parent, tuple(children))


# Digits, repeats, a nested section, a BNS row and an outside-the-label-space section, so lengths and idf all matter.
PROVISIONS = [
    prov("IPC 1", "theft of movable property under section 378 theft theft", children=["IPC 1(a)"]),
    prov("IPC 1(a)", "movable property taken dishonestly", "IPC 1"),
    prov("IPC 2", "murder causing death with intention of 1860"),
    prov("IPC 3", "cheating and dishonestly inducing delivery of property"),
    prov("IPC 4", "kidnapping from lawful guardianship"),
    prov("IPC 5", "forgery of a valuable security"),
    prov("IPC 9", "zebra property"),
    prov("BNS 5", "theft of movable property murder"),
]
L = {n: f"Section {n} in The Indian Penal Code" for n in (1, 2, 3, 4, 5)}
SPACE = {f"IPC {n}" for n in (1, 2, 3, 4, 5)}
QUERIES = ["theft of property", "murder, property and cheating dishonestly", "kidnapping 378 zebra", "nothing here at all",
           "the property of movable theft; dishonestly"]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def build(self, provisions, space_ns=None):
        index.build(str(self.tmp / "i.sqlite"), provisions, []).close()
        space_ns = space_ns or sorted({int(p.citation.split()[1].split("(")[0]) for p in provisions if p.citation.startswith("IPC")})
        (self.tmp / "labels.json").write_text(json.dumps({f"Section {n} in The Indian Penal Code": i for i, n in enumerate(space_ns)}))

    def run_bench(self, cases, out="out.json", k=1, r=0.5, extra=(), expect=0):
        split = self.tmp / "split.jsonl"
        split.write_text("".join(json.dumps(c) + "\n" for c in cases))
        (self.tmp / "manifest.json").write_text(json.dumps({n: {"sha256": bench.sha256(str(self.tmp / n))}
                                                           for n in ("split.jsonl", "labels.json")}))
        with contextlib.redirect_stderr(io.StringIO()):
            code = main(["bench", "run", "--split", str(split), "--labels", str(self.tmp / "labels.json"),
                         "--index", str(self.tmp / "i.sqlite"), "--k", str(k), "--r", str(r), "--out", str(self.tmp / out),
                         "--manifest", str(self.tmp / "manifest.json"), *extra])
        self.assertEqual(code, expect)
        return json.loads((self.tmp / out).read_text()) if expect == 0 else None


class EquivalenceTest(Base):
    def fts5_sections(self, db, raw, rollup="max"):
        """The slice 2 FTS5 path, as it stood before ticket 11, kept here as the reference."""
        terms = dict.fromkeys(t for t in re.findall(r"[^\W\d_]+", raw.lower()) if t not in bench.STOP_WORDS)
        if not terms:
            return []
        parent = dict(db.execute("SELECT citation, parent FROM provision"))
        hits = {}
        q = " OR ".join(f'"{t}"' for t in terms)
        for cite, rank in db.execute("SELECT citation, rank FROM fts WHERE fts MATCH ?", (q,)):
            while parent[cite] is not None:
                cite = parent[cite]
            if cite in SPACE:
                hits.setdefault(cite, []).append(-rank)
        return sorted(((c, bench.ROLLUPS[rollup](v)) for c, v in hits.items()), key=lambda cs: (-cs[1], cs[0]))

    def test_defaults_reproduce_fts5_scores_and_predictions(self):
        self.build(PROVISIONS)
        db = sqlite3.connect(self.tmp / "i.sqlite")
        ix = bm25.Index(db, bench.DEFAULT_KNOBS["levels"], bench.DEFAULT_KNOBS["stem"])
        for raw in QUERIES:
            for rollup in ("max", "sum"):
                want = self.fts5_sections(db, raw, rollup)
                got = bench.rank_sections(ix, raw, SPACE, rollup)
                self.assertEqual([c for c, _ in got], [c for c, _ in want], raw)
                for (_, a), (_, b) in zip(got, want):
                    self.assertAlmostEqual(a, b, delta=1e-9, msg=raw)
                self.assertEqual(bench.predict(got, 2, 0.5)[0], bench.predict(want, 2, 0.5)[0])
                self.assertEqual(bench.predict(got, 2, 0.5)[1], bench.predict(want, 2, 0.5)[1])
        self.assertTrue(self.fts5_sections(db, QUERIES[0]))  # the reference is not vacuously empty

    def test_a_changed_k1_or_b_moves_the_scores(self):
        self.build(PROVISIONS)
        ix = bm25.Index(sqlite3.connect(self.tmp / "i.sqlite"), "all", "none")
        base = bench.rank_sections(ix, "theft of property", SPACE, "max")
        for knobs in ({"bm25_k1": 2.0}, {"bm25_b": 0.3}):
            self.assertNotEqual(bench.rank_sections(ix, "theft of property", SPACE, "max", knobs=knobs), base)


class KnobTest(Base):
    def test_each_knob_changes_the_rule_hash_and_is_recorded(self):
        self.build(PROVISIONS)
        cases = [{"id": "a", "text": ["theft"], "labels": [L[1]]}]
        base = self.run_bench(cases)
        self.assertEqual(base["knobs"], {"bm25_k1": 1.2, "bm25_b": 0.75, "stem": "none", "levels": "all"})
        flags = [("--bm25-k1", "1.5"), ("--bm25-b", "0.5"), ("--stem", "suffix"), ("--levels", "top")]
        hashes = {base["rule"]["params_sha256"]}
        for flag, value in flags:
            r = self.run_bench(cases, extra=[flag, value])
            hashes.add(r["rule"]["params_sha256"])
            self.assertEqual(r["knobs"][flag[2:].replace("-", "_")], {"1.5": 1.5, "0.5": 0.5}.get(value, value))
        self.assertEqual(len(hashes), 5)

    def test_invalid_values_are_refused_without_a_results_file(self):
        self.build(PROVISIONS)
        cases = [{"id": "a", "text": ["theft"], "labels": [L[1]]}]
        for flags in (["--bm25-k1", "0"], ["--bm25-k1", "-1"], ["--bm25-b", "1.5"], ["--bm25-b", "-0.1"],
                      ["--stem", "porter"], ["--levels", "middle"]):
            self.run_bench(cases, out="bad.json", extra=flags, expect=1)
            self.assertFalse((self.tmp / "bad.json").exists(), flags)

    def test_stem_finds_a_plural_only_under_suffix(self):
        self.build(PROVISIONS)
        cases = [{"id": "a", "text": ["he was charged with murders"], "labels": [L[2]]}]
        self.assertEqual(self.run_bench(cases)["predictions"], {"a": []})
        self.assertEqual(self.run_bench(cases, extra=["--stem", "suffix"])["predictions"], {"a": ["IPC 2"]})

    def test_stem_table_examples(self):
        got = [bm25.stem_word(w) for w in ("murders", "murdered", "murdering", "stabbing", "causes", "cause", "injuries", "class", "was")]
        self.assertEqual(got, ["murder", "murder", "murder", "stab", "caus", "caus", "injury", "class", "was"])

    def test_levels_all_leaf_and_top(self):
        # "lantern" is only in IPC 6(a); the section text holds its children, as the parser's does. "preamble" is only
        # in the section's own opening words, so it exists in IPC 6 and nowhere else.
        provs = [prov("IPC 6", "preamble then lantern", children=["IPC 6(a)"]), prov("IPC 6(a)", "lantern", "IPC 6"),
                 prov("IPC 7", "other words"), prov("IPC 8", "more words")]
        self.build(provs)
        pred = lambda word, levels: self.run_bench([{"id": "q", "text": [word], "labels": ["Section 6 in The Indian Penal Code"]}], k=3,
                                                   extra=["--levels", levels])["predictions"]["q"]
        self.assertEqual([pred("lantern", lv) for lv in ("all", "leaf", "top")], [["IPC 6"]] * 3)
        self.assertEqual([pred("preamble", lv) for lv in ("all", "leaf", "top")], [["IPC 6"], [], ["IPC 6"]])
        # under top the section is retrieved by its own text; under leaf by its child's, so the scores differ
        db = sqlite3.connect(self.tmp / "i.sqlite")
        s = lambda lv: bench.rank_sections(bm25.Index(db, lv, "none"), "lantern", {"IPC 6"}, "max")[0][1]
        self.assertEqual(len({s("all"), s("leaf"), s("top")}), 3)

    def test_identical_runs_are_byte_identical_and_ties_break_by_citation(self):
        provs = [prov(f"IPC {n}", "theft") for n in (1, 2, 3)] + [prov("IPC 4", "zebra"), prov("IPC 5", "cheating")]
        self.build(provs)
        cases = [{"id": "a", "text": ["theft"], "labels": [L[1]]}]
        extra = ["--bm25-k1", "1.7", "--bm25-b", "0.4", "--stem", "suffix", "--levels", "leaf"]
        a = self.run_bench(cases, "a.json", extra=extra)
        self.run_bench(cases, "b.json", extra=extra)
        self.assertEqual((self.tmp / "a.json").read_bytes(), (self.tmp / "b.json").read_bytes())
        self.assertEqual(a["predictions"]["a"], ["IPC 1"])


class RoundTest(Base):
    def setUp(self):
        super().setUp()
        self.build(PROVISIONS)
        cases = [{"id": "a", "text": ["theft"], "labels": [L[1]]}, {"id": "b", "text": ["murders cheating"], "labels": [L[2], L[3]]}]
        for n in ("train", "dev", "test"):
            (self.tmp / f"{n}.jsonl").write_text("".join(json.dumps(c) + "\n" for c in cases[: 1 if n == "test" else 2]))
        names = ("train.jsonl", "dev.jsonl", "test.jsonl", "labels.json")
        (self.tmp / "manifest.json").write_text(json.dumps({n: {"sha256": bench.sha256(str(self.tmp / n))} for n in names}))
        self.log = self.tmp / "log.json"

    def cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            return main(list(argv)), err.getvalue()

    def round(self, *argv):
        return self.cli("bench", "round", "--train", str(self.tmp / "train.jsonl"), "--dev", str(self.tmp / "dev.jsonl"),
                        "--labels", str(self.tmp / "labels.json"), "--index", str(self.tmp / "i.sqlite"),
                        "--manifest", str(self.tmp / "manifest.json"), "--log", str(self.log), *argv)

    def test_every_knob_round_is_logged_and_hashes_differ(self):
        self.assertEqual(self.round("--k", "1", "--r", "0.5")[0], 0)
        for change in ("bm25_k1=1.5", "bm25_b=0.5", "stem=suffix", "levels=top"):
            self.assertEqual(self.round("--change", change)[0], 0, change)
        rounds = json.loads(self.log.read_text())["rounds"]
        self.assertEqual([e["knob"] for e in rounds], [None, "bm25_k1", "bm25_b", "stem", "levels"])
        self.assertEqual(len({e["rule"]["params_sha256"] for e in rounds}), 5)
        self.assertEqual(rounds[1]["params"]["bm25_k1"], 1.5)
        self.assertEqual((rounds[2]["params"]["bm25_k1"], rounds[2]["params"]["bm25_b"]), (1.5, 0.5))  # changes accumulate
        # a logged round equals an independent run with the same knobs
        for e in rounds:
            p = e["params"]
            dev = [json.loads(line) for line in (self.tmp / "dev.jsonl").read_text().splitlines()]
            r = self.run_bench(dev, k=p["k"], r=p["r"], extra=["--bm25-k1", str(p["bm25_k1"]), "--bm25-b", str(p["bm25_b"]),
                                                          "--stem", p["stem"], "--levels", p["levels"]])
            self.assertEqual(e["dev"]["top_k"]["scores"], r["scores"])
            self.assertEqual(e["rule"]["params_sha256"], r["rule"]["params_sha256"])

    def test_two_knobs_or_invalid_values_are_refused_and_the_log_is_untouched(self):
        self.round("--k", "1", "--r", "0.5")
        raw = self.log.read_bytes()
        bad = [("bm25_k1=1.5", "stem=suffix"), ("bm25_k1=0",), ("bm25_k1=-2",), ("bm25_k1=abc",), ("bm25_b=1.1",), ("bm25_b=-0.1",),
               ("stem=porter",), ("levels=middle",), ("stem=none",), ("levels=all",), ("bm25_b=0.75",), ("bm25=1",), ("levels=top", "levels=leaf")]
        for changes in bad:
            code, err = self.round(*[a for c in changes for a in ("--change", c)])
            self.assertEqual((changes, code), (changes, 1))
            self.assertIn("error:", err)
            self.assertEqual(self.log.read_bytes(), raw, changes)

    def test_freeze_carries_the_knobs_into_the_test_run(self):
        self.round("--k", "1", "--r", "0.5")
        self.round("--change", "stem=suffix")
        frozen = self.tmp / "frozen.json"
        self.assertEqual(self.cli("bench", "freeze", "--log", str(self.log), "--out", str(frozen))[0], 0)
        self.assertEqual(json.loads(frozen.read_text())["knobs"]["stem"], "suffix")
        code, _ = self.cli("bench", "run", "--split", str(self.tmp / "test.jsonl"), "--labels", str(self.tmp / "labels.json"),
                           "--index", str(self.tmp / "i.sqlite"), "--k", "1", "--r", "0.5", "--out", str(self.tmp / "t.json"),
                           "--manifest", str(self.tmp / "manifest.json"), "--frozen-rule", str(frozen),
                           "--ledger", str(self.tmp / "ledger.json"))
        self.assertEqual(code, 0)
        out = json.loads((self.tmp / "t.json").read_text())
        self.assertEqual(out["knobs"]["stem"], "suffix")  # the CLI default is none; the frozen rule wins
        self.assertEqual(out["rule"]["params_sha256"], json.loads(frozen.read_text())["rule"]["params_sha256"])


if __name__ == "__main__":
    unittest.main()
