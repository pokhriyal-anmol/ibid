import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from ibid.cli import main, pin_error


def corr(i: int) -> dict:
    return {"id": f"ipc_to_bns-{i}", "category": "ipc_to_bns", "query": f"IPC {i}", "expected_citations": [f"BNS {i}"],
            "expected_type": "one-to-one", "ipcPage": 1, "bnsPage": 1, "correspondence": True}


def other(i: int) -> dict:
    return {"id": f"section_lookup-{i}", "category": "section_lookup", "query": f"BNS {i}", "expected_text": f"{i}. x", "act": "BNS", "page": 1}


class FreezeTest(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.gold = [corr(i) for i in range(1, 13)] + [other(i) for i in range(1, 5)]
        (self.d / "g.json").write_text(json.dumps(self.gold))
        conc = [{"ipc": [f"IPC {i}"], "bns": [f"BNS {i}"], "type": "one-to-one", "verified": False} for i in range(1, 13)]
        (self.d / "c.json").write_text(json.dumps(conc))

    def run_freeze(self, marks: dict[str, str], *extra: str, delegated: tuple[str, ...] = ()) -> int:
        note = lambda i: "- checked by: agent, at the owner's instruction\n" if i in delegated else ""
        sheet = "".join(f"## {i}\n\n{note(i)}- result: [{'x' if m == 'pass' else ' '}] pass  [{'x' if m == 'fail' else ' '}] fail\n\n" for i, m in marks.items())
        (self.d / "s.md").write_text(sheet)
        for name in ("b.pdf", "i.pdf"):
            (self.d / name).write_bytes(name.encode())
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = main(["freeze", "--sheet", str(self.d / "s.md"), "--draft-gold", str(self.d / "g.json"), "--draft-conc", str(self.d / "c.json"),
                     "--out-gold", str(self.d / "v1.json"), "--out-conc", str(self.d / "cv1.json"),
                         "--bns", str(self.d / "b.pdf"), "--ipc", str(self.d / "i.pdf"), *extra])
        self.err = err.getvalue()
        return code

    def all_pass(self) -> dict[str, str]:
        # margin above MIN_CHECKED and MIN_CORR so one bad mark cannot trip the count rule
        return {g["id"]: "pass" for g in self.gold[:10] + self.gold[12:16]}

    def test_complete_sheet_freezes_with_a_pin_that_scored_mode_accepts(self):
        self.assertEqual(self.run_freeze(self.all_pass()), 0)
        gold_bytes = (self.d / "v1.json").read_bytes()
        self.assertIsNone(pin_error(str(self.d / "v1.json"), gold_bytes))
        self.assertEqual((self.d / "v1.sha256").read_text().strip(), hashlib.sha256(gold_bytes).hexdigest())
        item = json.loads(gold_bytes)[0]
        self.assertEqual(item["expected"], [{"type": "one-to-one", "citations": ["BNS 1"]}])
        basis = {e["ipc"][0]: e["basis"] for e in json.loads((self.d / "cv1.json").read_text())}
        self.assertEqual(basis["IPC 1"], "human-checked")
        self.assertEqual(basis["IPC 12"], "refuted-by-agent")
        verified = {e["ipc"][0]: e["verified"] for e in json.loads((self.d / "cv1.json").read_text())}
        self.assertEqual((verified["IPC 1"], verified["IPC 12"]), (True, False))
        self.assertEqual(item["correspondence"], True)
        self.assertEqual(set(item["source_sha256"]), {"BNS", "IPC"})

    def test_an_agent_check_done_for_the_owner_is_labelled_as_such_and_still_served(self):
        self.assertEqual(self.run_freeze(self.all_pass(), delegated=("ipc_to_bns-2",)), 0)
        entries = {e["ipc"][0]: e for e in json.loads((self.d / "cv1.json").read_text())}
        self.assertEqual(entries["IPC 2"]["basis"], "agent-checked-for-owner")
        self.assertTrue(entries["IPC 2"]["verified"])
        self.assertEqual(entries["IPC 1"]["basis"], "human-checked")
        review = json.loads((self.d / "v1.review.json").read_text())
        self.assertEqual(review["agent_checked_for_owner"], ["ipc_to_bns-2"])

    def test_one_changed_byte_breaks_the_pin(self):
        self.run_freeze(self.all_pass())
        tampered = (self.d / "v1.json").read_bytes().replace(b"BNS 1", b"BNS 9", 1)
        self.assertIsNotNone(pin_error(str(self.d / "v1.json"), tampered))

    def test_refuses_an_unmarked_item_and_writes_nothing(self):
        marks = self.all_pass()
        marks["ipc_to_bns-1"] = "unmarked"
        self.assertEqual(self.run_freeze(marks), 1)
        self.assertFalse((self.d / "v1.json").exists())
        self.assertIn("ipc_to_bns-1: unmarked", self.err)

    def test_refuses_too_few_checked_items(self):
        marks = dict(list(self.all_pass().items())[:6])
        self.assertEqual(self.run_freeze(marks), 1)
        self.assertFalse((self.d / "v1.json").exists())

    def test_a_failed_item_refuses_unless_dropped_and_is_then_recorded(self):
        marks = self.all_pass()
        marks["ipc_to_bns-2"] = "fail"
        self.assertEqual(self.run_freeze(marks), 1)
        self.assertFalse((self.d / "v1.json").exists())
        self.assertEqual(self.run_freeze(marks, "--drop-failed"), 0)
        ids = [i["id"] for i in json.loads((self.d / "v1.json").read_text())]
        self.assertNotIn("ipc_to_bns-2", ids)
        self.assertEqual(json.loads((self.d / "v1.review.json").read_text())["dropped"], ["ipc_to_bns-2"])


if __name__ == "__main__":
    unittest.main()
