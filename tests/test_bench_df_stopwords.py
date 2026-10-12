"""Slice 3 ticket 05: df stop list, derived rule v3, --extra-stop-words. Invented fixtures only."""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from ibid import bench, index
from ibid.cli import main
from ibid.parse import Provision

# 20 cases: "court" in 2 (0.10), "bail" in 1 (0.05, exactly at the cut), "theft" in 1 of 20 as well; "rare" absent from the cut.
TEXTS = [["The court heard it."], ["court order, Court!"]] + [["alpha"]] * 16 + [["bail granted"], ["rare", "Theft; 12 times"]]
LABELS = [["Section 1 in The Indian Penal Code"]] * 20


def write_split(path, texts=TEXTS, labels=LABELS):
    rows = [{"id": f"c{i:02d}", "text": t, **({} if labels is None else {"labels": labels[i]})} for i, t in enumerate(texts)]
    Path(path).write_text("".join(json.dumps(r) + "\n" for r in rows))


class DfStopwordsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.split = str(self.tmp / "train.jsonl")
        write_split(self.split)

    def df(self, min_df, split=None, out="df.json"):
        with contextlib.redirect_stderr(io.StringIO()):
            code = main(["bench", "df-stopwords", "--split", split or self.split, "--min-df", str(min_df), "--out", str(self.tmp / out)])
        return code, (self.tmp / out)

    def test_list_is_terms_at_or_above_min_df_sorted(self):
        code, out = self.df(0.05)
        rec = json.loads(out.read_text())
        self.assertEqual(code, 0)
        # alpha 16/20, court 2/20, bail, granted, rare, theft, times at exactly 1/20; "12" is not a letters-only term.
        self.assertEqual(rec["terms"], ["alpha", "bail", "court", "granted", "heard", "it", "order", "rare", "the", "theft", "times"])
        self.assertEqual((rec["cases"], rec["min_df"], rec["term_count"], rec["split_sha256"]),
                         (20, 0.05, 11, bench.sha256(self.split)))

    def test_term_just_below_the_cut_is_absent(self):
        _, out = self.df(0.06)  # 1/20 = 0.05 is below 0.06
        self.assertEqual(json.loads(out.read_text())["terms"], ["alpha", "court"])

    def test_labels_are_never_read(self):
        _, base = self.df(0.05)
        for name, labels in (("shuffled.jsonl", [[f"L{i}"] for i in range(20)]), ("removed.jsonl", None)):
            p = str(self.tmp / name)
            write_split(p, labels=labels)
            _, out = self.df(0.05, p, name + ".out")
            a, b = json.loads(base.read_text()), json.loads(out.read_text())
            self.assertEqual({**b, "split_sha256": None}, {**a, "split_sha256": None})

    def test_two_runs_are_byte_identical(self):
        _, a = self.df(0.05, out="a.json")
        _, b = self.df(0.05, out="b.json")
        self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_bad_min_df_and_empty_split_are_refused(self):
        self.assertEqual(self.df(0)[0], 1)
        empty = self.tmp / "empty.jsonl"
        empty.write_text("")
        self.assertEqual(self.df(0.05, str(empty))[0], 1)


class DeriveRuleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        knobs = {"bm25_b": 1.0, "bm25_k1": 4.0, "levels": "leaf", "stem": "suffix"}
        stop = ["a", "the"]
        self.src = {"k": 5, "r": 0.7, "round": 11, "section_score": "sum", "stop_words": stop, "knobs": knobs,
                    "rule": {"name": "query-rule", "version": "v2.11", "params_sha256": bench.rule_hash(5, 0.7, "sum", stop, knobs)}}
        (self.tmp / "src.json").write_text(json.dumps(self.src))
        (self.tmp / "sw.json").write_text(json.dumps({"terms": ["court", "the"]}))

    def derive(self):
        self.assertEqual(main(["bench", "derive-rule", "--from", str(self.tmp / "src.json"), "--stopwords", str(self.tmp / "sw.json"),
                               "--version", "v3", "--out", str(self.tmp / "v3.json")]), 0)
        return json.loads((self.tmp / "v3.json").read_text())

    def test_only_stop_words_version_and_hash_change(self):
        v3 = self.derive()
        for key in ("k", "r", "round", "section_score", "knobs"):
            self.assertEqual(v3[key], self.src[key])
        self.assertEqual(v3["stop_words"], ["a", "court", "the"])
        self.assertEqual(v3["rule"]["version"], "v3")
        self.assertNotEqual(v3["rule"]["params_sha256"], self.src["rule"]["params_sha256"])
        self.assertEqual(v3["rule"]["params_sha256"], bench.rule_hash(5, 0.7, "sum", ["a", "court", "the"], self.src["knobs"]))
        self.assertEqual(v3["derived_from"], {"rule_params_sha256": self.src["rule"]["params_sha256"],
                                              "stopwords_sha256": bench.sha256(str(self.tmp / "sw.json"))})


class ExtraStopWordsTest(unittest.TestCase):
    def test_run_drops_the_terms_and_changes_the_hash(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        index.build(str(tmp / "i.sqlite"), [Provision("IPC 1", "theft of property", None, ()),
                                            Provision("IPC 2", "murder causing death", None, ())], []).close()
        labels = {f"Section {n} in The Indian Penal Code": i for i, n in enumerate((1, 2))}
        (tmp / "labels.json").write_text(json.dumps(labels))
        write_split(tmp / "dev.jsonl", [["theft murder murder"]], [[next(iter(labels))]])
        (tmp / "sw.json").write_text(json.dumps({"terms": ["murder"]}))
        names = ("dev.jsonl", "labels.json")
        (tmp / "m.json").write_text(json.dumps({n: {"sha256": bench.sha256(str(tmp / n))} for n in names}))
        base = ["bench", "run", "--split", str(tmp / "dev.jsonl"), "--labels", str(tmp / "labels.json"), "--index", str(tmp / "i.sqlite"),
                "--manifest", str(tmp / "m.json"), "--k", "1", "--r", "0.5"]
        outs = []
        for name, extra in (("a.json", []), ("b.json", ["--extra-stop-words", str(tmp / "sw.json")])):
            self.assertEqual(main(base + ["--out", str(tmp / name)] + extra), 0)
            outs.append(json.loads((tmp / name).read_text()))
        self.assertNotEqual(outs[0]["rule"]["params_sha256"], outs[1]["rule"]["params_sha256"])
        # "murder" appears twice in the query but is one term; with it dropped only "theft" is left, so IPC 1 wins.
        self.assertEqual(outs[1]["predictions"], {"c00": ["IPC 1"]})
        self.assertEqual(outs[1]["rule"]["params_sha256"], bench.rule_hash(1, 0.5, "max", sorted(set(bench.STOP_WORDS) | {"murder"})))


if __name__ == "__main__":
    unittest.main()
