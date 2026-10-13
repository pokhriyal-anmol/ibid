"""Slice 3 ticket 01: `ibid charges validate`. Invented fixture only, no real case text."""
import contextlib
import copy
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from ibid import index
from ibid.cli import main
from ibid.parse import Provision

PROVS = [Provision(c, "text", None, ()) for c in ("IPC 302", "IPC 420", "IPC 379", "BNS 103", "BNS 318", "BNS 303")]


def item(n: int, charges: list, basis: str = "agent-drafted-skeptic-refuted") -> dict:
    return {"id": f"m{n}", "query": f"invented query {n}", "author_type": "judgment-excerpt", "source": f"invented-set case {n}",
            "anonymised": True, "charges": charges, "label_basis": basis, "reviewed_by": "skeptic-1"}


def charge(ipc: list, bns: list, name: str = "x") -> dict:
    return {"charge": name, "sections": {"ipc": ipc, "bns": bns}}


MURDER, CHEAT, THEFT = charge(["IPC 302"], ["BNS 103"]), charge(["IPC 420"], ["BNS 318"]), charge(["IPC 379"], ["BNS 303"])
ITEMS = [item(1, [MURDER]), item(2, [CHEAT]), item(3, [MURDER, CHEAT]), item(4, [MURDER, THEFT], "lawyer"),
         item(5, [MURDER, CHEAT, THEFT], "agent-checked-for-owner"), item(6, [charge(["IPC 379", "IPC 420"], []), THEFT, CHEAT, MURDER])]


class ChargesValidateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        index.build(str(self.tmp / "i.sqlite"), PROVS, []).close()

    def write(self, items: list, name: str = "set.json", pin: bool = True, **top) -> Path:
        data = {"version": "test", "created": "2026-10-12", "licence_note": "invented", "label_policy": "invented labels", **top, "items": items}
        p = self.tmp / name
        p.write_text(json.dumps(data))
        if pin:
            p.with_suffix(".sha256").write_text(hashlib.sha256(p.read_bytes()).hexdigest() + "\n")
        return p

    def run_validate(self, path: Path) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["charges", "validate", "--set", str(path), "--index", str(self.tmp / "i.sqlite")])
        return code, out.getvalue(), err.getvalue()

    def mutated(self, fn) -> list:
        items = copy.deepcopy(ITEMS)
        fn(items)
        return items

    def assert_refused(self, fn, iid: str, field: str):
        code, _, err = self.run_validate(self.write(self.mutated(fn)))
        self.assertEqual(code, 1)
        self.assertIn(f"item {iid} field {field}", err)

    def test_valid_fixture_passes_with_summary(self):
        code, out, _ = self.run_validate(self.write(ITEMS))
        self.assertEqual(code, 0)
        self.assertIn("items: 6", out)
        self.assertIn("1: 2, 2: 2, 3 or more: 2", out)
        self.assertIn("IPC 3, BNS 3", out)
        self.assertIn("label_basis: lawyer: 1, agent-drafted-skeptic-refuted: 4, agent-checked-for-owner: 1", out)

    def test_each_known_bad_field_is_named_with_its_item(self):
        cases = {
            "author model": (lambda i: i[0].update(author_type="model"), "m1", "author_type"),
            "author missing": (lambda i: i[0].pop("author_type"), "m1", "author_type"),
            "not anonymised": (lambda i: i[1].update(anonymised=False), "m2", "anonymised"),
            "empty charges": (lambda i: i[2].update(charges=[]), "m3", "charges"),
            "no sections": (lambda i: i[3]["charges"].append(charge([], [])), "m4", "charges[2].sections"),
            "not in index": (lambda i: i[0]["charges"][0]["sections"]["ipc"].append("IPC 999"), "m1", "charges[0].sections.ipc"),
            "ipc in bns list": (lambda i: i[0]["charges"][0]["sections"]["bns"].append("IPC 302"), "m1", "charges[0].sections.bns"),
            "empty query": (lambda i: i[4].update(query="  "), "m5", "query"),
            "source missing": (lambda i: i[4].pop("source"), "m5", "source"),
            "bad basis": (lambda i: i[5].update(label_basis="model"), "m6", "label_basis"),
            "reviewer missing": (lambda i: i[5].pop("reviewed_by"), "m6", "reviewed_by"),
            "duplicate id": (lambda i: i[1].update(id="m1"), "m1", "id"),
        }
        for label, (fn, iid, field) in cases.items():
            with self.subTest(label):
                self.assert_refused(fn, iid, field)

    def test_forum_post_with_answer_extracted_labels_is_valid_and_counted(self):
        def fn(items):
            items[0].update(author_type="forum-post", label_basis="lawyer-answer-extracted")
        code, out, _ = self.run_validate(self.write(self.mutated(fn)))
        self.assertEqual(code, 0)
        self.assertIn("lawyer-answer-extracted: 1", out)

    def test_empty_bns_list_with_ipc_is_valid(self):
        items = [item(1, [charge(["IPC 302"], [])])]
        self.assertEqual(self.run_validate(self.write(items))[0], 0)

    def test_changed_byte_is_a_pin_mismatch(self):
        p = self.write(ITEMS)
        p.write_text(p.read_text().replace("invented query 1", "invented query 7"))
        code, _, err = self.run_validate(p)
        self.assertEqual(code, 1)
        self.assertIn("does not match its pin", err)

    def test_missing_pin_is_refused(self):
        code, _, err = self.run_validate(self.write(ITEMS, pin=False))
        self.assertEqual(code, 1)
        self.assertIn("no pin file", err)

    def test_validate_does_not_rewrite_the_set_or_index(self):
        p, idx = self.write(ITEMS), self.tmp / "i.sqlite"
        before = [(f.read_bytes(), f.stat().st_mtime_ns) for f in (p, p.with_suffix(".sha256"), idx)]
        code, out, _ = self.run_validate(p)
        self.assertEqual(code, 0)
        self.assertIn("items: 6", out)
        self.assertEqual(before, [(f.read_bytes(), f.stat().st_mtime_ns) for f in (p, p.with_suffix(".sha256"), idx)])

    def test_missing_top_level_field_is_refused(self):
        code, _, err = self.run_validate(self.write(ITEMS, label_policy=""))
        self.assertEqual(code, 1)
        self.assertIn("field label_policy", err)


if __name__ == "__main__":
    unittest.main()
