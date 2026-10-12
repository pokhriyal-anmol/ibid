"""Slice 2 ticket 09: the report. Invented fixture only; the files are produced by the real commands."""
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

L = {n: f"Section {n} in The Indian Penal Code" for n in (1, 2, 3)}
SPLIT = [{"id": "s1", "text": ["theft of property"], "labels": [L[1]]},
         {"id": "m1", "text": ["murder cheating"], "labels": [L[2], L[3]]}]
PROVS = [Provision("IPC 1", "theft of property", None, ()), Provision("IPC 2", "murder", None, ()),
         Provision("IPC 3", "cheating", None, ()), Provision("IPC 4", "zebra", None, ())]


class ReportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        index.build(str(self.tmp / "i.sqlite"), PROVS, []).close()
        (self.tmp / "labels.json").write_text(json.dumps({v: i for i, v in enumerate(L.values())}))
        for n, cases in (("train", SPLIT), ("dev", SPLIT[:1]), ("test", SPLIT[::-1])):  # distinct bytes, distinct hashes
            (self.tmp / f"{n}.jsonl").write_text("".join(json.dumps(c) + "\n" for c in cases))
        names = ("train.jsonl", "dev.jsonl", "test.jsonl", "labels.json")
        self.manifest = self.tmp / "manifest.json"
        self.manifest.write_text(json.dumps({n: {"sha256": bench.sha256(str(self.tmp / n))} for n in names}))
        self.log, self.ledger = self.tmp / "log.json", self.tmp / "ledger.json"
        self.frozen, self.results = self.tmp / "frozen.json", self.tmp / "results.json"

    def cli(self, *argv):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return main(["bench", *argv])

    def round(self, *extra):
        return self.cli("round", "--train", str(self.tmp / "train.jsonl"), "--dev", str(self.tmp / "dev.jsonl"),
                        "--labels", str(self.tmp / "labels.json"), "--index", str(self.tmp / "i.sqlite"),
                        "--manifest", str(self.manifest), "--log", str(self.log), *extra)

    def score_test(self, *extra, k="1"):
        return self.cli("run", "--split", str(self.tmp / "test.jsonl"), "--labels", str(self.tmp / "labels.json"),
                        "--index", str(self.tmp / "i.sqlite"), "--k", k, "--r", "0.5", "--out", str(self.results),
                        "--manifest", str(self.manifest), "--frozen-rule", str(self.frozen),
                        "--ledger", str(self.ledger), *extra)

    def build(self, rescore=False):
        self.assertEqual(self.round("--k", "1", "--r", "0.5"), 0)
        self.assertEqual(self.round("--change", "k=2"), 0)
        self.assertEqual(self.round("--change", "k=1"), 0)  # final round runs the round-0 rule again
        self.assertEqual(self.cli("freeze", "--log", str(self.log), "--out", str(self.frozen)), 0)
        self.assertEqual(self.score_test(), 0)
        if rescore:
            self.assertEqual(self.score_test("--rescore-test"), 0)

    def report(self, out="report.md"):
        code = self.cli("report", "--log", str(self.log), "--ledger", str(self.ledger),
                        "--results", str(self.results), "--frozen-rule", str(self.frozen),
                        "--out", str(self.tmp / out))
        return code, (self.tmp / out)

    def test_report_numbers_are_read_from_the_files(self):
        self.build()
        code, path = self.report()
        self.assertEqual(code, 0)
        text = path.read_text()
        rounds = json.loads(self.log.read_text())["rounds"]
        d0 = rounds[0]["dev"]["top_k"]["scores"]
        self.assertIn(f"| top-k | round 0 dev | {d0['micro_f1'] * 100:.2f} / {d0['macro_f1'] * 100:.2f} /", text)
        self.assertIn("frozen round (2) dev", text)
        test = json.loads(self.ledger.read_text())[0]["scores"]
        self.assertIn(f"| top-k | test score 1, k 1, r 0.5 | {test['micro_f1'] * 100:.2f}", text)
        # known-bad: a log whose dev macro F1 was edited must change the report (a hand-typed report would not)
        log = json.loads(self.log.read_text())
        log["rounds"][0]["dev"]["top_k"]["scores"]["macro_f1"] = 0.123456
        self.log.write_text(json.dumps(log))
        _, edited = self.report("edited.md")
        self.assertIn("12.35", edited.read_text())
        self.assertNotIn("12.35", text)

    def test_all_test_scores_in_the_ledger_are_shown(self):
        self.build(rescore=True)
        _, path = self.report()
        text = path.read_text()
        self.assertEqual(len(json.loads(self.ledger.read_text())), 2)
        self.assertIn("test score 1,", text)
        self.assertIn("test score 2,", text)

    def test_strata_for_round_0_and_final_and_never_found(self):
        self.build()
        text = self.report()[1].read_text()
        for stratum in ("label_count 1", "label_count 2", "label_count 3+", "words <=150", "words >500"):
            self.assertIn(f"| {stratum} |", text)
        self.assertIn("dev round 0", text)
        self.assertIn("dev frozen", text)
        never = json.loads(self.results.read_text())["per_label"]["never_found"]
        self.assertIn(", ".join(never) if never else "none", text)

    def test_comparison_names_sources_and_every_caveat(self):
        self.build()
        text = self.report()[1].read_text()
        for needle in ("28.08", "IL-TUR", "28.45", "LeSICiN paper", "Different models", "different dataset copy",
                       "Split counts", "NyayGraph", "Llama 3.1 8B", "Metric protocol", "our own implementation", "No rank is claimed"):
            self.assertIn(needle, text)

    def test_hashes_rule_version_and_rule_hash_are_carried(self):
        self.build()
        text = self.report()[1].read_text()
        entry = json.loads(self.log.read_text())["rounds"][-1]
        for needle in (*entry["inputs"].values(), entry["rule"]["params_sha256"], entry["rule"]["version"],
                       bench.sha256(str(self.tmp / "test.jsonl"))):
            self.assertIn(needle, text)
        self.assertIn("ledger rule matches the frozen round (2): yes", text)

    def test_ledger_rule_is_checked_against_the_frozen_round_not_the_last(self):
        self.assertEqual(self.round("--k", "1", "--r", "0.5"), 0)
        self.assertEqual(self.round("--change", "k=2"), 0)
        self.assertEqual(self.round("--change", "k=1"), 0)
        self.assertEqual(self.cli("freeze", "--log", str(self.log), "--round", "1", "--out", str(self.frozen)), 0)
        self.assertEqual(self.score_test(k="2"), 0)
        self.assertIn("ledger rule matches the frozen round (1): yes", self.report()[1].read_text())
        ledger = json.loads(self.ledger.read_text())  # known-bad: a ledger scored under another rule
        ledger[0]["rule"]["params_sha256"] = "0" * 64
        self.ledger.write_text(json.dumps(ledger))
        self.assertIn("ledger rule matches the frozen round (1): NO", self.report("bad.md")[1].read_text())

    def test_headline_is_the_frozen_round_not_the_last_logged_round(self):
        self.assertEqual(self.round("--k", "1", "--r", "0.5"), 0)
        self.assertEqual(self.round("--change", "k=2"), 0)
        self.assertEqual(self.round("--change", "k=1"), 0)
        self.assertEqual(self.round("--change", "k=2"), 0)  # round 3 is logged after the freeze point
        self.assertEqual(self.cli("freeze", "--log", str(self.log), "--round", "2", "--out", str(self.frozen)), 0)
        self.assertEqual(self.score_test(), 0)
        text = self.report()[1].read_text()
        rounds = json.loads(self.log.read_text())["rounds"]
        for split in ("train", "dev"):
            sc = rounds[2][split]["top_k"]["scores"]
            self.assertIn(f"| top-k | frozen round (2) {split} | {sc['micro_f1'] * 100:.2f}", text)
        self.assertIn("| top-k | test score 1, k 1, r 0.5 |", text)
        self.assertIn("last logged round (3) dev", text)
        self.assertNotIn("final round", text)

    def test_last_round_frozen_has_one_row_and_no_duplicate(self):
        self.build()
        text = self.report()[1].read_text()
        self.assertIn("frozen round (2) dev", text)
        self.assertNotIn("last logged round", text)
        self.assertEqual(text.count("| top-k | frozen round (2) dev |"), 1)

    def test_two_runs_are_byte_identical(self):
        self.build()
        self.assertEqual(self.report("a.md")[1].read_bytes(), self.report("b.md")[1].read_bytes())

    def test_report_without_a_scored_test_split_is_refused(self):
        self.build()
        self.ledger.write_text("[]")
        code, path = self.report()
        self.assertNotEqual(code, 0)
        self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
