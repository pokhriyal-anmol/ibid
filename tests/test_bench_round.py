"""Slice 2 ticket 08: optimisation rounds, the log and the stopping rule. Invented fixture only."""
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


def prov(cite, text):
    return Provision(cite, text, None, ())


PROVISIONS = [prov("IPC 1", "theft of movable property"), prov("IPC 2", "murder causing death"),
              prov("IPC 3", "cheating deceiving by personation"), prov("IPC 4", "kidnapping from lawful guardianship")]
L = {n: f"Section {n} in The Indian Penal Code" for n in (1, 2, 3, 4)}
CASES = [
    {"id": "s1", "text": ["theft of movable property murder"], "labels": [L[1]]},
    {"id": "m1", "text": ["cheating deceiving personation kidnapping"], "labels": [L[3], L[4]]},
    {"id": "s2", "text": ["murder causing death"], "labels": [L[2]]},
]


def quiet(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class RoundTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        index.build(str(self.tmp / "i.sqlite"), PROVISIONS, []).close()
        (self.tmp / "labels.json").write_text(json.dumps({label: i for i, label in enumerate(L.values())}))
        self.log = self.tmp / "log.json"
        self.write("train.jsonl", CASES)
        self.write("dev.jsonl", CASES)

    def write(self, name, cases):
        (self.tmp / name).write_text("".join(json.dumps(c) + "\n" for c in cases))

    def manifest(self, extra=()):
        names = ("train.jsonl", "dev.jsonl", "labels.json", *extra)
        path = self.tmp / "manifest.json"
        path.write_text(json.dumps({n: {"sha256": bench.sha256(str(self.tmp / n))} for n in names}))
        return str(path)

    def round(self, *changes, k=None, r=None, train="train.jsonl", dev="dev.jsonl", manifest=None):
        argv = ["bench", "round", "--train", str(self.tmp / train), "--dev", str(self.tmp / dev),
                "--labels", str(self.tmp / "labels.json"), "--index", str(self.tmp / "i.sqlite"),
                "--manifest", manifest or self.manifest(), "--log", str(self.log)]
        for c in changes:
            argv += ["--change", c]
        for flag, v in (("--k", k), ("--r", r)):
            argv += [flag, str(v)] if v is not None else []
        return quiet(argv)

    def rounds(self):
        return json.loads(self.log.read_text())["rounds"]

    def start(self, k=1, r=0.5):
        self.assertEqual(self.round(k=k, r=r)[0], 0)

    def single_run(self, k, r, rollup="max"):
        out = self.tmp / "single.json"
        code, _, _ = quiet(["bench", "run", "--split", str(self.tmp / "dev.jsonl"), "--labels", str(self.tmp / "labels.json"),
                            "--index", str(self.tmp / "i.sqlite"), "--k", str(k), "--r", str(r), "--rollup", rollup,
                            "--out", str(out), "--manifest", self.manifest()])
        self.assertEqual(code, 0)
        return json.loads(out.read_text())

    def test_logged_rounds_match_independent_single_runs(self):
        self.start()
        for change in ("k=2", "r=0.9", "rollup=sum"):
            self.assertEqual(self.round(change)[0], 0)
        entries = self.rounds()
        self.assertEqual([e["round"] for e in entries], [0, 1, 2, 3])
        self.assertEqual([e["knob"] for e in entries], [None, "k", "r", "rollup"])
        self.assertEqual([e["rule"]["version"] for e in entries], ["v2", "v2.1", "v2.2", "v2.3"])
        for e in entries:
            p = e["params"]
            single = self.single_run(p["k"], p["r"], p["rollup"])
            self.assertEqual(e["dev"]["top_k"]["scores"], single["scores"])
            self.assertEqual(e["dev"]["top_k"]["strata"], single["strata"])
            self.assertEqual(e["dev"]["threshold"]["scores"], single["threshold"]["scores"])
            self.assertEqual(e["rule"]["params_sha256"], single["rule"]["params_sha256"])
            self.assertEqual(e["gap"]["macro_f1"], round(e["train"]["top_k"]["scores"]["macro_f1"]
                                                         - e["dev"]["top_k"]["scores"]["macro_f1"], 6))
        self.assertEqual(len({e["rule"]["params_sha256"] for e in entries}), 4)
        self.assertEqual(entries[1]["dev"]["top_k"]["scores"]["macro_f1"], round(11 / 12, 6))  # hand-computed: k=2 adds one false IPC 2 for s1

    def use(self, provisions, cases):
        (self.tmp / "i.sqlite").unlink()
        index.build(str(self.tmp / "i.sqlite"), provisions, []).close()
        self.write("train.jsonl", cases)
        self.write("dev.jsonl", cases)

    def test_one_stop_word_change_alters_query_score_and_hash(self):
        self.use(PROVISIONS, [{"id": "t", "text": ["theft"], "labels": [L[1]]}])
        self.start(k=1)
        before = self.rounds()[0]
        self.assertEqual(before["dev"]["top_k"]["scores"]["micro_f1"], 1.0)
        self.assertEqual(self.round("stop_words=+theft")[0], 0)
        after = self.rounds()[1]
        self.assertEqual(after["dev"]["top_k"]["scores"]["micro_f1"], 0.0)  # the query is now empty
        self.assertIn("theft", after["params"]["stop_words"])
        self.assertEqual(len(after["params"]["stop_words"]), len(before["params"]["stop_words"]) + 1)
        self.assertEqual(after["rule"]["params_sha256"], bench.rule_hash(1, 0.5, "max", after["params"]["stop_words"]))
        self.assertEqual(self.round("stop_words=-theft")[0], 0)
        back = self.rounds()[2]
        self.assertEqual(back["rule"]["params_sha256"], before["rule"]["params_sha256"])
        self.assertEqual(back["dev"]["top_k"]["scores"], before["dev"]["top_k"]["scores"])

    def test_rollup_round_changes_the_logged_score(self):
        # sections 6 and 7 tie under max (top-1 is the lowest citation, 6); under sum 7 scores twice 6
        provisions = [prov("IPC 6", "robbery violence"), Provision("IPC 7", "violence", None, ("IPC 7(a)", "IPC 7(b)")),
                      Provision("IPC 7(a)", "robbery violence", "IPC 7", ()),
                      Provision("IPC 7(b)", "robbery violence", "IPC 7", ())]
        labels = {f"Section {n} in The Indian Penal Code": n for n in (6, 7)}
        (self.tmp / "labels.json").write_text(json.dumps(labels))
        self.use(provisions, [{"id": "t", "text": ["robbery"], "labels": ["Section 7 in The Indian Penal Code"]}])
        self.start(k=1)
        self.assertEqual(self.round("rollup=sum")[0], 0)
        r0, r1 = self.rounds()
        self.assertEqual((r0["dev"]["top_k"]["scores"]["micro_f1"], r1["dev"]["top_k"]["scores"]["micro_f1"]), (0.0, 1.0))

    def test_refused_rounds_leave_the_log_untouched(self):
        self.start()
        raw = self.log.read_bytes()
        bad = [("k=2", "r=0.9"), ("label_prior=on",), ("tokenisation=letters",), ("stop_words=+a,b",),
               ("stop_words=the,of",), ("k=1",), ("k=0",), ("r=2",), ("rollup=median",), ("k",)]
        for changes in bad:
            code, _, err = self.round(*changes)
            self.assertEqual((changes, code), (changes, 1))
            self.assertIn("error:", err)
            if changes == ("label_prior=on",):
                self.assertIn("not a declared knob", err)
            self.assertEqual(self.log.read_bytes(), raw, changes)
        self.assertEqual(self.round()[0], 1)  # a later round with no change at all

    def test_round_zero_is_the_unmodified_rule(self):
        self.assertEqual(self.round("k=2", k=1, r=0.5)[0], 1)
        self.assertEqual(self.round()[0], 1)  # no k and r
        self.assertFalse(self.log.exists())

    def test_three_sub_bar_dev_gains_report_saturation(self):
        self.start()
        flags = []
        for word in ("foo", "bar", "baz"):
            self.assertEqual(self.round(f"stop_words=+{word}")[0], 0)
            flags.append(self.rounds()[-1]["status"]["saturated"])
        self.assertEqual(flags, [False, False, True])
        self.assertIn("'saturated': True", self.round("stop_words=+qux")[1])

    def test_cap_is_reached_after_twenty_rounds_beyond_round_zero(self):
        self.start()
        words = [a + b for a in "xy" for b in "abcdefghij"]  # 20 distinct lower-case stop words
        for word in words:
            self.assertEqual(self.round(f"stop_words=+{word}")[0], 0)
        caps = [e["status"]["cap_reached"] for e in self.rounds()]
        self.assertEqual((len(caps), caps.count(True), caps[19], caps[20]), (21, 1, False, True))

    def test_overfitting_needs_dev_to_stop_while_train_keeps_rising(self):
        case = lambda i, text, label: {"id": i, "text": [text], "labels": [L[label]]}  # noqa: E731
        rising = [case("t1", "murder theft movable", 2), case("t2", "murder cheating deceiving", 2), case("t3", "murder kidnapping lawful", 2)]
        falling = [case("d1", "theft", 1), case("d2", "cheating", 3), case("d3", "kidnapping", 4)]  # each stop word empties one query
        flat = [case("f", "murder", 2)]
        cases = {"train rises, dev falls": (rising, falling, True), "train flat": (flat, falling, False), "dev rises": (falling, rising, False)}
        for name, (train, dev, expected) in cases.items():
            with self.subTest(name):
                self.log.unlink(missing_ok=True)
                self.use(PROVISIONS, train)
                self.write("dev.jsonl", dev)
                self.start(k=1, r=1.0)
                for word in ("theft", "cheating", "kidnapping"):
                    self.assertEqual(self.round(f"stop_words=+{word}")[0], 0)
                flags = [e["status"]["overfitting"] for e in self.rounds()]
                self.assertEqual(flags, [False, False, expected, expected])  # needs two rounds of dev change to be read

    def test_threshold_only_gains_are_not_saturation(self):
        both = lambda i, text: {"id": i, "text": [text], "labels": [L[1], L[2]]}  # noqa: E731
        # second-section scores are 0.89, 0.56 and 0.45 of the top one, so each lower r lets one more case add a true section
        cases = [both("a", "theft murder"), both("b", "theft movable murder"), both("c", "theft murder causing")]
        for name, rs, expected in (("r reaches a new section each round", ("0.85", "0.5", "0.4"), False),
                                   ("r changes nothing", ("0.95", "0.93", "0.91"), True)):
            with self.subTest(name):
                self.log.unlink(missing_ok=True)
                self.use(PROVISIONS, cases)
                self.start(k=1, r=1.0)
                for r in rs:
                    self.assertEqual(self.round(f"r={r}")[0], 0)
                rounds = self.rounds()
                top = [e["dev"]["top_k"]["scores"]["macro_f1"] for e in rounds]
                thr = [e["dev"]["threshold"]["scores"]["macro_f1"] for e in rounds]
                self.assertEqual(len(set(top)), 1)  # the top-k output is flat in both
                self.assertEqual(thr[-1] > thr[0], not expected)
                self.assertEqual(rounds[-1]["status"]["saturated"], expected)

    def test_threshold_rule_alone_hurting_single_label_cases_is_flagged_over_the_bar(self):
        for clean, noisy, flags in ((98, 2, ["hurts-simple"]), (99, 1, [])):  # one false section in 100 is a 0.5 point drop, just under the bar
            with self.subTest(noisy=noisy):
                self.log.unlink(missing_ok=True)
                cases = [{"id": f"c{i}", "text": ["murder"], "labels": [L[2]]} for i in range(clean)]
                cases += [{"id": f"n{i}", "text": ["theft murder"], "labels": [L[2]]} for i in range(noisy)]
                self.use(PROVISIONS, cases)
                self.start(k=1, r=1.0)
                self.assertEqual(self.round("r=0.85")[0], 0)  # lets IPC 1 into the threshold output of "theft murder" only
                r0, r1 = self.rounds()
                self.assertEqual(r0["dev"]["top_k"]["strata"], r1["dev"]["top_k"]["strata"])  # only the threshold rule moved
                self.assertEqual(r1["flags"], flags)

    def test_round_that_hurts_single_label_cases_is_flagged(self):
        self.start(k=1)
        self.assertEqual(self.round("k=2")[0], 0)
        r0, r1 = self.rounds()
        self.assertGreater(r1["dev"]["top_k"]["scores"]["macro_f1"], r0["dev"]["top_k"]["scores"]["macro_f1"])
        single = lambda e: e["dev"]["top_k"]["strata"]["label_count"]["1"]["scores"]["micro_f1"]
        self.assertGreater(single(r0) - single(r1), 0.005)
        self.assertEqual((r0["flags"], r1["flags"]), ([], ["hurts-simple"]))
        frozen = self.tmp / "frozen.json"
        freeze = lambda n: quiet(["bench", "freeze", "--log", str(self.log), "--round", str(n), "--out", str(frozen)])
        code, _, err = freeze(1)
        self.assertEqual(code, 1)
        self.assertIn("owner_approved", err)
        self.assertFalse(frozen.exists())
        self.assertEqual(freeze(0)[0], 0)
        log = json.loads(self.log.read_text())
        log["rounds"][1]["owner_approved"] = True
        self.log.write_text(json.dumps(log))
        self.assertEqual(freeze(1)[0], 0)
        self.assertEqual(json.loads(frozen.read_text())["rule"], r1["rule"])
        self.assertEqual(freeze(9)[0], 1)  # a round that was never logged

    def test_test_split_is_never_read(self):
        self.write("test.jsonl", CASES)
        by_name = self.round(k=1, r=0.5, dev="test.jsonl")  # not pinned in the manifest: only the name can refuse it
        self.assertEqual(by_name[0], 1)
        self.assertIn("never read", by_name[2])
        # renamed copy of the pinned test file is caught by its hash
        shutil.copy(self.tmp / "test.jsonl", self.tmp / "renamed.jsonl")
        mf = json.loads(Path(self.manifest(("test.jsonl", "renamed.jsonl"))).read_text())
        mf["test.jsonl"]["sha256"] = bench.sha256(str(self.tmp / "renamed.jsonl"))
        (self.tmp / "m2.json").write_text(json.dumps(mf))
        by_hash = self.round(k=1, r=0.5, dev="renamed.jsonl", manifest=str(self.tmp / "m2.json"))
        self.assertEqual(by_hash[0], 1)
        self.assertIn("never read", by_hash[2])
        self.assertFalse(self.log.exists())

    def test_changed_data_byte_is_refused(self):
        manifest = self.manifest()
        self.write("dev.jsonl", CASES[:2])
        code, _, err = self.round(k=1, r=0.5, manifest=manifest)
        self.assertEqual(code, 1)
        self.assertIn("dev.jsonl", err)
        self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()
