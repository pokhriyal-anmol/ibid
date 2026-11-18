"""IB34: malformed input files are an `error:` line and exit 1, never a traceback or a stray file.
Exception to AGENTS.md rule 5: calls `cli.main` and `cli.score_gold` directly, because `ibid eval` needs both PDFs."""
import contextlib
import io
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ibid import cli, index  # noqa: E402
from ibid.parse import Provision  # noqa: E402


def run(*argv: str) -> tuple[int, str]:
    err = io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
        code = cli.main(list(argv))
    return code, err.getvalue()


class CliInputGuardsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def refused(self, code_and_err: tuple[int, str], *wanted: str) -> None:
        code, err = code_and_err
        self.assertEqual(code, 1, err)
        self.assertTrue(err.startswith("error: "), err)
        self.assertNotIn("Traceback", err)
        for w in wanted:
            self.assertIn(w, err)

    def test_a_sources_file_of_the_wrong_shape_is_refused(self):
        for body in ('{"bns": 1}', "[]", '{"bns": {"url": "u"}}', '{"bns": {"url": "u", "sha256": "s", "bytes": "9"}}',
                     '{"bns": {"url": "u", "sha256": "s", "sections": true}}'):
            (self.tmp / "s.json").write_text(body)
            self.refused(run("setup", "--sources", str(self.tmp / "s.json"), "--raw-dir", str(self.tmp)), "map each source")

    def test_a_missing_index_is_refused_and_no_file_is_created(self):
        (self.tmp / "t.txt").write_text("")
        for acts in ("ipc-bns", "crpc-bnss"):
            self.refused(run("concordance", "from-table", "--acts", acts, "--table", str(self.tmp / "t.txt"),
                             "--index", str(self.tmp / "nope.sqlite"), "--out", str(self.tmp / "o.json")), "no such index")
        self.assertFalse((self.tmp / "nope.sqlite").exists())

    def test_an_empty_crpc_bnss_table_is_refused(self):
        db = index.build(str(self.tmp / "i.sqlite"), [Provision("CrPC 1", "1. x.", None, ())], [])
        db.execute("CREATE TABLE heading (citation TEXT PRIMARY KEY, heading TEXT)")
        db.commit()
        db.close()
        (self.tmp / "t.txt").write_text("")
        self.refused(run("concordance", "from-table", "--acts", "crpc-bnss", "--table", str(self.tmp / "t.txt"),
                         "--index", str(self.tmp / "i.sqlite"), "--out", str(self.tmp / "o.json")), "no BNSS rows")
        self.assertFalse((self.tmp / "o.json").exists())

    def test_an_index_without_the_expected_tables_is_an_error_line(self):
        sqlite3.connect(self.tmp / "empty.sqlite").close()
        (self.tmp / "t.txt").write_text("")
        self.refused(run("concordance", "from-table", "--table", str(self.tmp / "t.txt"),
                         "--index", str(self.tmp / "empty.sqlite"), "--out", str(self.tmp / "o.json")), "OperationalError")

    def test_a_gold_item_without_a_category_is_refused(self):
        db = index.build(str(self.tmp / "g.sqlite"), [Provision("BNS 1", "1. x.", None, ())], [])
        with self.assertRaisesRegex(ValueError, "no id or category"):
            cli.score_gold(db, [], [{"id": "g1", "query": "BNS 1"}])
        db.close()


if __name__ == "__main__":
    unittest.main()
