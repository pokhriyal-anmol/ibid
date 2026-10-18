"""A missing source PDF gives one error line and 'run: ibid setup', exit non-zero, no traceback."""
import subprocess
import sys
import unittest

from mcp_harness import ENV, ROOT
from pdfs import BNS_PDF, IPC_PDF

GONE = "/nonexistent/dir/missing.pdf"
EVAL = ["eval", "--gold", "gold/v2.json", "--concordance", "concordance/v2.json", "--out", "/dev/null"]
COMMANDS = [["mcp"], EVAL, ["freeze"], ["conform"]]


def run(cmd: list[str], bns: str, ipc: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "ibid.cli", *cmd, "--bns", bns, "--ipc", ipc],
                          cwd=ROOT, env=ENV, text=True, capture_output=True, timeout=60)


class MissingPdfTest(unittest.TestCase):
    def check(self, cmd: list[str], bns: str, ipc: str):
        r = run(cmd, bns, ipc)
        self.assertNotEqual(r.returncode, 0, cmd)
        self.assertEqual(r.stderr.splitlines(), [f"error: no such file: {GONE}", "run: ibid setup"], cmd)

    def test_missing_bns(self):
        for cmd in COMMANDS + [["headings", "list", "--act", "bns"]]:
            self.check(cmd, GONE, IPC_PDF)

    def test_missing_ipc(self):
        for cmd in COMMANDS + [["headings", "list", "--act", "ipc"]]:
            self.check(cmd, BNS_PDF, GONE)


if __name__ == "__main__":
    unittest.main()
