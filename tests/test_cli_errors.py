"""IB28: malformed input to the CLI is an `error:` line and exit 1, never a raw traceback.
Exception to AGENTS.md rule 5: calls cli.main directly with bad inputs."""
import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ibid import cli  # noqa: E402
from pdfs import BNS_PDF, BNSS_PDF  # noqa: E402


class CliErrorsTest(unittest.TestCase):
    def run_cli(self, *argv: str) -> tuple[int, str]:
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            return cli.main(list(argv)), err.getvalue()

    def refused(self, kind: str, *argv: str) -> None:
        rc, err = self.run_cli(*argv)
        self.assertEqual(rc, 1, argv)
        self.assertTrue(err.startswith("error: "), err)
        self.assertIn(kind, err)
        self.assertNotIn("Traceback", err)

    def test_a_sources_file_that_is_not_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text("{not json")
            self.refused("JSONDecodeError", "setup", "--sources", str(bad), "--raw-dir", tmp)

    def test_a_table_that_is_not_utf8_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            table = Path(tmp) / "table.txt"
            table.write_bytes(b"\xff\xfe\xff")
            self.refused("UnicodeDecodeError", "concordance", "from-table", "--table", str(table), "--out", f"{tmp}/o.json", "--index", f"{tmp}/i.sqlite")

    def test_a_truncated_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            trunc = Path(tmp) / "trunc.pdf"
            trunc.write_bytes(Path(BNS_PDF).read_bytes()[:300000])
            self.refused("CalledProcessError", "headings", "list", "--act", "bns", "--bns", str(trunc))

    def test_the_wrong_document_for_the_procedure_build(self):
        with tempfile.TemporaryDirectory() as tmp:  # the BNS PDF stands in for the CrPC one
            self.refused("StopIteration", "procedure", "build", "--crpc", BNS_PDF, "--bnss", BNSS_PDF, "--index", f"{tmp}/p.sqlite")

    def test_a_debug_run_keeps_the_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text("{not json")
            with mock.patch.dict(os.environ, {"IBID_DEBUG": "1"}), self.assertRaises(ValueError):
                self.run_cli("setup", "--sources", str(bad), "--raw-dir", tmp)

    def test_a_usage_error_and_a_good_run_are_unchanged(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cli.main(["setup", "--nope"])
        self.assertEqual(self.run_cli("setup", "--sources", "data/sources.json", "--raw-dir", "/nonexistent-ibid")[0], 1)  # missing PDFs: the existing exit 1


if __name__ == "__main__":
    unittest.main()
