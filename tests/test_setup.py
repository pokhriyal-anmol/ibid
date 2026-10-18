"""`ibid setup` through main(): offline checklist. Fixtures are tiny invented non-PDF files."""
import contextlib
import hashlib
import io
import json
import os
import re
import socket
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ibid import setup
from ibid.cli import main
from ibid.parse import Provision

ROOT = Path(__file__).resolve().parent.parent


def run_setup(*args: str, path: str) -> tuple[int, str]:
    out = io.StringIO()
    with mock.patch.dict(os.environ, {"PATH": path}), contextlib.redirect_stdout(out):
        code = main(["setup", *args])
    return code, out.getvalue()


class SetupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raw = Path(self.tmp.name) / "raw"
        self.raw.mkdir()
        self.files = {"bns": b"fake bns bytes", "ipc": b"fake ipc bytes"}
        manifest = {n: {"file": f"{n}.bin", "url": f"https://example.org/{n}", "sections": 3, "bytes": len(b),
                        "sha256": hashlib.sha256(b).hexdigest()} for n, b in self.files.items()}
        self.sources = Path(self.tmp.name) / "sources.json"
        self.sources.write_text(json.dumps(manifest))
        for n, b in self.files.items():
            (self.raw / f"{n}.bin").write_bytes(b)
        fake = lambda _: [Provision(f"s{i}", "", None, ()) for i in range(self.parsed)]  # noqa: E731
        self.parsed = 3
        patcher = mock.patch.dict(setup.PARSERS, {"bns": fake, "ipc": fake})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.bindir = Path(self.tmp.name) / "bin"
        self.bindir.mkdir()
        for t in ("pdftotext", "pdftohtml", "pdfseparate", "pdfunite"):
            (self.bindir / t).write_text("#!/bin/sh\n")
            (self.bindir / t).chmod(0o755)

    def run_it(self, path=None):
        return run_setup("--sources", str(self.sources), "--raw-dir", str(self.raw), path=path or str(self.bindir))

    def test_all_present_passes_without_network(self):
        with mock.patch.object(socket.socket, "connect", side_effect=AssertionError("network")):
            code, out = self.run_it()
        self.assertEqual(code, 0, out)
        self.assertNotIn("FAIL", out)
        self.assertEqual(out.count("pass "), 6)

    def test_missing_file_names_url_and_absolute_target(self):
        (self.raw / "ipc.bin").unlink()
        code, out = self.run_it()
        self.assertNotEqual(code, 0)
        self.assertIn("https://example.org/ipc", out)
        self.assertIn(str((self.raw / "ipc.bin").resolve()), out)
        self.assertIn("ibid setup --fetch ipc --url", out)

    def test_prints_counts_and_absolute_mcp_line(self):
        code, out = self.run_it()
        self.assertEqual(code, 0, out)
        self.assertIn("BNS 3 sections, IPC 3 sections", out)
        line = next(x for x in out.splitlines() if x.startswith("claude mcp add ibid -- "))
        self.assertIn(str((self.raw / "bns.bin").resolve()), line)
        self.assertIn(str((self.raw / "ipc.bin").resolve()), line)
        self.assertTrue(Path(line.split("--directory ")[1].split()[0]).is_absolute())

    def test_wrong_count_fails(self):
        self.parsed = 2
        code, out = self.run_it()
        self.assertNotEqual(code, 0)
        self.assertRegex(out, r"FAIL\s+bns: parsed 2 sections, expected 3")
        self.assertNotIn("claude mcp add", out)

    def test_failed_check_skips_parse(self):
        (self.raw / "ipc.bin").unlink()
        with mock.patch.dict(setup.PARSERS, {"bns": self.boom, "ipc": self.boom}):
            code, out = self.run_it()
        self.assertNotEqual(code, 0)
        self.assertIn("parse not run", out)
        self.assertNotIn("claude mcp add", out)

    @staticmethod
    def boom(_):
        raise AssertionError("parse attempted")

    def test_wrong_bytes_reported_and_untouched(self):
        p = self.raw / "bns.bin"
        p.write_bytes(b"other")
        os.utime(p, (1_000_000, 1_000_000))
        before = (p.read_bytes(), p.stat().st_mtime)
        code, out = self.run_it()
        self.assertNotEqual(code, 0)
        self.assertIn("present, hash differs", out)
        self.assertIn(hashlib.sha256(self.files["bns"]).hexdigest(), out)
        self.assertIn(hashlib.sha256(b"other").hexdigest(), out)
        self.assertEqual((p.read_bytes(), p.stat().st_mtime), before)

    def test_missing_tool_gives_both_install_commands(self):
        code, out = self.run_it(path=self.tmp.name + "/empty")
        self.assertNotEqual(code, 0)
        self.assertRegex(out, r"FAIL\s+tool pdftotext")
        self.assertIn("brew install poppler", out)
        self.assertIn("apt install poppler-utils", out)


class RealPdfTest(unittest.TestCase):
    def test_real_pdfs_parse_to_expected_counts(self):
        from pdfs import BNS_PDF, IPC_PDF
        with tempfile.TemporaryDirectory() as d:
            for n, p in (("bns-prs.pdf", BNS_PDF), ("ipc-wipo.pdf", IPC_PDF)):
                (Path(d) / n).symlink_to(p)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(["setup", "--sources", str(ROOT / "data/sources.json"), "--raw-dir", d])
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn("BNS 358 sections, IPC 575 sections", out.getvalue())
        line = next(x for x in out.getvalue().splitlines() if x.startswith("claude mcp add ibid -- "))
        self.assertIn(str(Path(BNS_PDF).resolve()), line)


class ManifestTest(unittest.TestCase):
    def md_hashes(self) -> dict:
        md = (ROOT / "data" / "SOURCES.md").read_text()
        return {n: re.search(rf"`{f}`.*?`([0-9a-f]{{64}})`", md).group(1)
                for n, f in (("bns", "bns-prs.pdf"), ("ipc", "ipc-wipo.pdf"))}

    def manifest(self) -> dict:
        return json.loads((ROOT / "data" / "sources.json").read_text())

    def test_sources_json_matches_sources_md(self):
        m = self.manifest()
        self.assertEqual({n: s["sha256"] for n, s in m.items()}, self.md_hashes())

    def test_altered_hash_is_detected(self):
        m = self.manifest()
        m["ipc"]["sha256"] = "0" * 64
        self.assertNotEqual({n: s["sha256"] for n, s in m.items()}, self.md_hashes())


if __name__ == "__main__":
    unittest.main()
