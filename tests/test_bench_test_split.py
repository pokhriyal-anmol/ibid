"""Slice 2 ticket 07: the test split is scored once, against a frozen rule. Invented fixture only."""
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

L = {n: f"Section {n} in The Indian Penal Code" for n in (1, 2)}
CASES = [{"id": "c1", "text": ["theft of property"], "labels": [L[1]]},
         {"id": "c2", "text": ["murder"], "labels": [L[2]]}]
PROVS = [Provision("IPC 1", "theft of property", None, ()), Provision("IPC 2", "murder", None, ()),
         Provision("IPC 3", "zebra", None, ()), Provision("IPC 4", "cheating", None, ())]


class TestSplitOnceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        index.build(str(self.tmp / "i.sqlite"), PROVS, []).close()
        (self.tmp / "labels.json").write_text(json.dumps({v: i for i, v in enumerate(L.values())}))
        for d in ("a", "b"):
            (self.tmp / d).mkdir()
            (self.tmp / d / "test.jsonl").write_text("".join(json.dumps(c) + "\n" for c in CASES))
        self.dev = self.tmp / "dev.jsonl"
        self.dev.write_text(json.dumps(CASES[0]) + "\n")  # different bytes from test.jsonl, so a different hash
        self.frozen, self.ledger, self.log = self.tmp / "frozen.json", self.tmp / "ledger.json", self.tmp / "log.json"
        self.manifest = self.tmp / "manifest.json"
        self.write_manifest()

    def write_manifest(self, extra=None):
        names = {"test.jsonl": self.tmp / "a" / "test.jsonl", "dev.jsonl": self.dev, "labels.json": self.tmp / "labels.json"}
        names.update(extra or {})
        self.manifest.write_text(json.dumps({n: {"sha256": bench.sha256(str(p))} for n, p in names.items()}))

    def cli(self, *argv):
        with contextlib.redirect_stderr(io.StringIO()):
            return main(list(argv))

    def log_round(self, *argv):
        self.assertEqual(self.cli("bench", "round", "--train", str(self.dev), "--dev", str(self.dev),
                                  "--labels", str(self.tmp / "labels.json"), "--index", str(self.tmp / "i.sqlite"),
                                  "--manifest", str(self.manifest), "--log", str(self.log), *argv), 0)

    def freeze(self, k=1, r=0.5):
        self.log_round("--k", str(k), "--r", str(r))
        self.assertEqual(self.cli("bench", "freeze", "--log", str(self.log), "--out", str(self.frozen)), 0)

    def run_split(self, split, out="out.json", k=1, r=0.5, *extra):
        return self.cli("bench", "run", "--split", str(split), "--labels", str(self.tmp / "labels.json"),
                        "--index", str(self.tmp / "i.sqlite"), "--k", str(k), "--r", str(r), "--out", str(self.tmp / out),
                        "--manifest", str(self.manifest), "--frozen-rule", str(self.frozen),
                        "--ledger", str(self.ledger), *extra)

    def split_path(self):
        return self.tmp / "a" / "test.jsonl"

    def entries(self):
        return json.loads(self.ledger.read_text())

    def test_scoring_before_freeze_is_refused_and_writes_nothing(self):
        self.assertNotEqual(self.run_split(self.split_path()), 0)
        self.assertFalse((self.tmp / "out.json").exists() or self.ledger.exists())

    def test_rule_other_than_the_frozen_one_is_refused(self):
        self.freeze(k=1)
        self.assertNotEqual(self.run_split(self.split_path(), k=2), 0)
        self.assertFalse(self.ledger.exists())

    def test_first_score_after_freeze_is_recorded(self):
        self.freeze()
        self.assertEqual(self.run_split(self.split_path()), 0)
        [e] = self.entries()
        self.assertEqual(e["split_sha256"], bench.sha256(str(self.split_path())))
        self.assertEqual(e["rule"]["params_sha256"], bench.rule_hash(1, 0.5, "max"))
        self.assertEqual(json.loads((self.tmp / "out.json").read_text())["test_scores"], [e])

    def test_second_score_without_the_flag_is_refused_and_writes_nothing(self):
        self.freeze()
        self.assertEqual(self.run_split(self.split_path()), 0)
        before = self.ledger.read_bytes()
        self.assertNotEqual(self.run_split(self.split_path(), "second.json"), 0)
        self.assertEqual(self.ledger.read_bytes(), before)
        self.assertFalse((self.tmp / "second.json").exists())

    def test_rescore_flag_keeps_the_first_and_reports_both(self):
        self.freeze()
        self.assertEqual(self.run_split(self.split_path()), 0)
        first = self.entries()[0]
        self.assertEqual(self.run_split(self.split_path(), "second.json", 1, 0.5, "--rescore-test"), 0)
        self.assertEqual(len(self.entries()), 2)
        self.assertEqual(self.entries()[0], first)
        self.assertEqual(len(json.loads((self.tmp / "second.json").read_text())["test_scores"]), 2)

    def test_copy_at_a_new_path_does_not_bypass_the_guard(self):
        self.freeze()
        self.assertEqual(self.run_split(self.split_path()), 0)
        self.assertNotEqual(self.run_split(self.tmp / "b" / "test.jsonl", "copy.json"), 0)
        self.assertEqual(len(self.entries()), 1)

    def test_copy_under_a_new_name_pinned_in_the_manifest_does_not_bypass_the_guard(self):
        self.freeze()
        self.assertEqual(self.run_split(self.split_path()), 0)
        renamed = self.tmp / "b" / "renamed.jsonl"
        renamed.write_bytes(self.split_path().read_bytes())
        self.write_manifest({"renamed.jsonl": renamed})
        self.assertNotEqual(self.run_split(renamed, "copy.json"), 0)
        self.assertEqual(len(self.entries()), 1)

    def test_tuned_stop_words_are_frozen_and_scored_with_the_logged_version(self):
        self.freeze()
        self.log_round("--change", "stop_words=+theft")
        self.assertEqual(self.cli("bench", "freeze", "--log", str(self.log), "--out", str(self.frozen)), 0)
        self.assertEqual(self.run_split(self.split_path()), 0)
        [e] = self.entries()
        stop = sorted(bench.STOP_WORDS + ["theft"])
        self.assertEqual((e["rule"]["version"], e["rule"]["params_sha256"]), (f"{bench.RULE_VERSION}.1", bench.rule_hash(1, 0.5, "max", stop)))
        self.assertEqual(json.loads((self.tmp / "out.json").read_text())["rule"], e["rule"])

    def test_dev_scoring_never_touches_the_ledger_or_needs_a_freeze(self):
        self.assertEqual(self.run_split(self.dev), 0)
        self.assertEqual(self.run_split(self.dev, "again.json"), 0)
        self.assertFalse(self.ledger.exists())
