"""Slice 2 ticket 01: benchmark labels map to IPC citations present in the index. Seam: `ibid bench check-labels`."""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from ibid import index
from ibid.cli import main
from ibid.parse import Provision


def prov(cite, parent=None):
    return Provision(cite, f"text of {cite}", parent, ())


class CheckLabelsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        index.build(str(self.tmp / "i.sqlite"), [prov("IPC 34"), prov("IPC 120B"), prov("IPC 120B(1)", "IPC 120B"), prov("IPC 294"), prov("IPC 294(b)", "IPC 294"), prov("BNS 3")], []).close()

    def run_check(self, labels):
        vocab = self.tmp / "vocab.json"
        vocab.write_text(json.dumps({label: i for i, label in enumerate(labels)}))
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["bench", "check-labels", "--data", str(vocab), "--index", str(self.tmp / "i.sqlite")])
        return code, out.getvalue(), err.getvalue()

    def test_all_present_exits_zero_and_counts_mapped(self):
        code, out, _ = self.run_check(["Section 34 in The Indian Penal Code", "Section 120B in The Indian Penal Code"])
        self.assertEqual(code, 0)
        self.assertIn("2 mapped, 0 missing, 0 unparseable", out)

    def test_subsection_label_maps_to_its_own_provision(self):
        code, out, _ = self.run_check(["Section 294(b) in The Indian Penal Code"])
        self.assertEqual(code, 0)
        self.assertIn("1 mapped", out)

    def test_subsection_absent_from_index_is_missing_even_if_section_exists(self):
        code, _, err = self.run_check(["Section 294(c) in The Indian Penal Code"])
        self.assertNotEqual(code, 0)
        self.assertIn("IPC 294(c)", err)

    def test_label_absent_from_index_exits_nonzero_and_is_named(self):
        code, out, err = self.run_check(["Section 34 in The Indian Penal Code", "Section 999 in The Indian Penal Code"])
        self.assertNotEqual(code, 0)
        self.assertIn("Section 999 in The Indian Penal Code", err)
        self.assertNotIn("Section 34 in The Indian Penal Code", err)

    def test_bns_provision_does_not_satisfy_an_ipc_label(self):
        code, _, err = self.run_check(["Section 3 in The Indian Penal Code"])
        self.assertNotEqual(code, 0)
        self.assertIn("Section 3 in The Indian Penal Code", err)

    def test_unexpected_shape_is_reported_unparseable_not_dropped(self):
        code, _, err = self.run_check(["Section 34 in The Indian Penal Code", "Article 21 of the Constitution"])
        self.assertNotEqual(code, 0)
        self.assertIn("unparseable", err)
        self.assertIn("Article 21 of the Constitution", err)

    def test_empty_vocabulary_is_an_error(self):
        code, _, _ = self.run_check([])
        self.assertNotEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
