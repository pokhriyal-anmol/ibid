"""Slice 3 ticket 10: `ibid charges intake`. Invented fixture queries only."""
import contextlib
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

WORDS = "a man was shouting at his neighbour over a fence and then he broke the gate and kept the money owed to him by someone"
BLOCKS = [f"Case {w} {WORDS}" for w in ("alpha", "bravo", "charlie", "delta")]


class IntakeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def intake(self, blocks: list[str], header: str = "# header\\n") -> tuple[int, str, dict | None]:
        q, out = self.tmp / "q.txt", self.tmp / "draft.json"
        out.unlink(missing_ok=True)
        q.write_text(header.replace("\\n", "\n") + "\n---\n".join(blocks) + "\n")
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = main(["charges", "intake", "--queries", str(q), "--author-type", "owner", "--author", "o1", "--out", str(out)])
        return code, err.getvalue(), json.loads(out.read_text()) if out.exists() else None

    def test_four_blocks_make_four_draft_items(self):
        code, _, data = self.intake(BLOCKS)
        self.assertEqual(code, 0)
        self.assertEqual([i["id"] for i in data["items"]], ["d-001", "d-002", "d-003", "d-004"])
        self.assertEqual(data["items"][0]["query"], BLOCKS[0])
        self.assertEqual(data["items"][0]["author_type"], "owner")
        self.assertEqual(data["items"][0]["charges"], [])
        self.assertNotIn("label_basis", data["items"][0])

    def test_each_known_bad_block_is_refused_with_its_reason(self):
        cases = {"empty": ("", "block 2: empty"), "short": ("too few words here", "block 2: 4 words"),
                 "section": (BLOCKS[1] + " under Section 302", "block 2: contains what looks like a section number"),
                 "u/s": (BLOCKS[1] + " u/s 420", "section number"), "duplicate": ("  " + BLOCKS[0].upper(), "block 2: duplicate")}
        for name, (bad, msg) in cases.items():
            with self.subTest(name):
                code, err, data = self.intake([BLOCKS[0], bad, BLOCKS[2]])
                self.assertEqual(code, 1)
                self.assertIn(msg, err)
                self.assertIsNone(data)  # nothing written

    def test_draft_fails_validate_and_labelled_copy_passes(self):
        index.build(str(self.tmp / "i.sqlite"), [Provision("IPC 302", "t", None, ()), Provision("BNS 103", "t", None, ())], []).close()
        _, _, data = self.intake(BLOCKS)

        def validate(d: dict) -> int:
            p = self.tmp / "set.json"
            p.write_text(json.dumps(d))
            p.with_suffix(".sha256").write_text(hashlib.sha256(p.read_bytes()).hexdigest() + "\n")
            with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                return main(["charges", "validate", "--set", str(p), "--index", str(self.tmp / "i.sqlite")])

        self.assertEqual(validate(data), 1)
        for i in data["items"]:
            i.update(charges=[{"charge": "murder", "sections": {"ipc": ["IPC 302"], "bns": ["BNS 103"]}}],
                     label_basis="lawyer", reviewed_by="r1")
        self.assertEqual(validate(data), 0)


if __name__ == "__main__":
    unittest.main()
