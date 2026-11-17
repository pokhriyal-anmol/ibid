"""`ibid setup` through main(): offline checklist. Fixtures are tiny invented non-PDF files."""
import contextlib
import http.server
import hashlib
import io
import json
import os
import re
import socket
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from ibid import setup
from ibid.cli import main
from ibid.parse import Provision
from pdfs import _main_checkout
from pdfs import needs_ipc

ROOT = Path(__file__).resolve().parent.parent
MAIN_RAW = _main_checkout() / "data/raw"
NEW_FILES = {"bnss": "bnss-prs.pdf", "crpc": "crpc-indiacode.pdf",
             "bnss_crpc_table": "capt/comparison_summary_BNSS_to_CrPC.pdf"}


def setUpModule() -> None:
    # the developer's shell exports these for the other tests; setup must see only what each test sets
    patcher = mock.patch.dict(os.environ)
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)
    for name in ("IBID_BNS_PDF", "IBID_IPC_PDF", "IBID_BNSS_PDF", "IBID_CRPC_PDF", "IBID_BNSS_CRPC_TABLE_PDF"):
        os.environ.pop(name, None)


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
        self.model = Path(self.tmp.name) / "assoc-nb-v3.json"
        patcher = mock.patch.object(setup, "MODEL", self.model)
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

    def test_absent_model_is_an_optional_line_and_exits_zero(self):
        code, out = self.run_it()
        self.assertEqual(code, 0, out)
        line = next(x for x in out.splitlines() if x.startswith("optional"))
        self.assertIn("absent", line)
        self.assertIn("ibid assoc fit --source union", line)
        self.assertEqual(out.count("pass "), 6)

    def test_present_model_prints_its_hash_and_exits_zero(self):
        self.model.write_bytes(b"invented model")
        code, out = self.run_it()
        self.assertEqual(code, 0, out)
        line = next(x for x in out.splitlines() if x.startswith("optional"))
        self.assertIn("present", line)
        self.assertIn(hashlib.sha256(b"invented model").hexdigest(), line)

    def test_required_failure_still_fails_with_the_model_line(self):
        (self.raw / "ipc.bin").unlink()
        for present in (False, True):
            if present:
                self.model.write_bytes(b"m")
            code, out = self.run_it()
            self.assertNotEqual(code, 0)
            self.assertIn("optional", out)

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

    def test_the_pdf_env_vars_override_the_raw_dir_like_every_other_command(self):
        elsewhere = Path(self.tmp.name) / "elsewhere.bin"
        elsewhere.write_bytes(b"not the recorded bytes")
        with mock.patch.dict(os.environ, {"IBID_BNS_PDF": str(elsewhere)}):
            code, out = self.run_it()
        self.assertNotEqual(code, 0)
        self.assertIn("present, hash differs", out)

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


@needs_ipc
class RealPdfTest(unittest.TestCase):
    def test_real_pdfs_parse_to_expected_counts(self):
        from pdfs import BNS_PDF, IPC_PDF
        with tempfile.TemporaryDirectory() as d:
            for n, p in (("bns-prs.pdf", BNS_PDF), ("ipc-wipo.pdf", IPC_PDF)):
                (Path(d) / n).symlink_to(p)
            (Path(d) / "capt").mkdir()
            for f in NEW_FILES.values():
                (Path(d) / f).symlink_to(MAIN_RAW / f)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(["setup", "--sources", str(ROOT / "data/sources.json"), "--raw-dir", d])
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn("BNS 358 sections, IPC 575 sections", out.getvalue())
        for n in NEW_FILES:
            self.assertRegex(out.getvalue(), rf"pass\s+{n}: .*hash ok")
        line = next(x for x in out.getvalue().splitlines() if x.startswith("claude mcp add ibid -- "))
        self.assertIn(str(Path(BNS_PDF).resolve()), line)


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.hits.append(self.path)
        body, declared = self.server.body, self.server.declared
        if body is None:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(body) if declared is None else declared))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


class FetchTest(unittest.TestCase):
    GOOD = b"good bns bytes"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raw = Path(self.tmp.name) / "raw"
        self.raw.mkdir()
        self.sources = Path(self.tmp.name) / "sources.json"
        self.write_manifest(self.GOOD)
        self.srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        self.srv.hits, self.srv.body, self.srv.declared = [], self.GOOD, None
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)
        self.url = f"http://127.0.0.1:{self.srv.server_port}/x.pdf"

    def write_manifest(self, good: bytes):
        m = {n: {"file": f"{n}.bin", "url": self.url_for(n), "bytes": len(good),
                 "sha256": hashlib.sha256(good).hexdigest()} for n in ("bns", "ipc")}
        self.sources.write_text(json.dumps(m))

    def url_for(self, n):
        return "https://example.org/" + n

    def fetch(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["setup", "--sources", str(self.sources), "--raw-dir", str(self.raw), *args])
        return code, out.getvalue() + err.getvalue()

    def assert_clean_failure(self, code, out, check):
        self.assertNotEqual(code, 0, out)
        self.assertIn(check, out)
        self.assertEqual(os.listdir(self.raw), [])

    def test_good_body_lands_with_manifest_hash(self):
        code, out = self.fetch("--fetch", "ipc", "--url", self.url)
        self.assertTrue((self.raw / "ipc.bin").read_bytes() == self.GOOD, out)
        self.assertEqual(os.listdir(self.raw), ["ipc.bin"])
        self.assertEqual(code, 0, out)
        self.assertIn("fetched", out)
        self.assertEqual(self.srv.hits, ["/x.pdf"])

    def test_bns_uses_manifest_url(self):
        m = json.loads(self.sources.read_text())
        m["bns"]["url"] = self.url
        self.sources.write_text(json.dumps(m))
        self.fetch("--fetch", "bns")
        self.assertEqual((self.raw / "bns.bin").read_bytes(), self.GOOD)

    def test_wrong_hash_leaves_nothing(self):
        self.srv.body = b"evil bns bytes"
        code, out = self.fetch("--fetch", "ipc", "--url", self.url)
        self.assert_clean_failure(code, out, "hash")

    def test_truncated_body_leaves_nothing(self):
        self.srv.body, self.srv.declared = self.GOOD[:5], len(self.GOOD)
        code, out = self.fetch("--fetch", "ipc", "--url", self.url)
        self.assert_clean_failure(code, out, "size")

    def test_oversized_body_leaves_nothing(self):
        self.srv.body = self.GOOD * 10
        code, out = self.fetch("--fetch", "ipc", "--url", self.url)
        self.assert_clean_failure(code, out, "exceeds")

    def test_cap_applies_when_manifest_size_is_larger(self):
        self.write_manifest(b"x" * 1000)
        self.srv.body = b"x" * 50
        with mock.patch.object(setup, "CAP", 10):
            code, out = self.fetch("--fetch", "ipc", "--url", self.url)
        self.assert_clean_failure(code, out, "exceeds 10 bytes")

    def test_http_error_leaves_nothing(self):
        self.srv.body = None
        code, out = self.fetch("--fetch", "ipc", "--url", self.url)
        self.assert_clean_failure(code, out, "404")

    def test_existing_file_refused_without_request(self):
        p = self.raw / "ipc.bin"
        p.write_bytes(b"precious wrong")
        code, out = self.fetch("--fetch", "ipc", "--url", self.url)
        self.assertNotEqual(code, 0)
        self.assertIn("already exists", out)
        self.assertEqual(p.read_bytes(), b"precious wrong")
        self.assertEqual(self.srv.hits, [])

    def test_disallowed_urls_refused_before_connecting(self):
        for bad in ("http://example.com/x.pdf", "file:///etc/passwd", "http://127.0.0.1.evil.com/x.pdf"):
            with mock.patch.object(socket.socket, "connect", side_effect=AssertionError("network")):
                code, out = self.fetch("--fetch", "ipc", "--url", bad)
            self.assertNotEqual(code, 0, bad)
            self.assertIn("refused", out)
            self.assertEqual(os.listdir(self.raw), [])

    def test_ipc_without_url_explains(self):
        code, out = self.fetch("--fetch", "ipc")
        self.assertNotEqual(code, 0)
        self.assertIn("signed", out)
        self.assertIn("--url", out)
        self.assertEqual(self.srv.hits, [])


class NewSourcesTest(unittest.TestCase):
    """The three slice 15 entries have no parser: setup checks presence, size and hash only."""
    BODIES = {"bnss": b"b1", "crpc": b"c22", "bnss_crpc_table": b"t333"}
    FILES = {"bnss": "bnss.bin", "crpc": "crpc.bin", "bnss_crpc_table": "capt/t.bin"}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raw = Path(self.tmp.name) / "raw"
        (self.raw / "capt").mkdir(parents=True)
        m = {n: {"file": self.FILES[n], "url": "https://example.org/" + n, "bytes": len(b),
                 "sha256": hashlib.sha256(b).hexdigest()} for n, b in self.BODIES.items()}
        for n in ("bns", "ipc"):
            m[n] = {"file": f"{n}.bin", "url": "https://example.org/" + n, "sections": 1, "bytes": 1,
                    "sha256": hashlib.sha256(b"x").hexdigest()}
            (self.raw / f"{n}.bin").write_bytes(b"x")
        self.sources = Path(self.tmp.name) / "sources.json"
        self.sources.write_text(json.dumps(m))
        for n, b in self.BODIES.items():
            (self.raw / self.FILES[n]).write_bytes(b)
        fake = lambda _: [Provision("s", "", None, ())]  # noqa: E731
        patcher = mock.patch.dict(setup.PARSERS, {"bns": fake, "ipc": fake})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.bindir = Path(self.tmp.name) / "bin"
        self.bindir.mkdir()
        for t in setup.TOOLS:
            (self.bindir / t).write_text("#!/bin/sh\n")
            (self.bindir / t).chmod(0o755)

    def run_it(self):
        return run_setup("--sources", str(self.sources), "--raw-dir", str(self.raw), path=str(self.bindir))

    def serve(self, body: bytes) -> str:
        srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        srv.hits, srv.body, srv.declared = [], body, None
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        return f"http://127.0.0.1:{srv.server_port}/t"

    def fetch_table(self, url: str) -> tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["setup", "--sources", str(self.sources), "--raw-dir", str(self.raw),
                         "--fetch", "bnss_crpc_table", "--url", url])
        return code, out.getvalue() + err.getvalue()

    def test_present_and_matching_offline(self):
        with mock.patch.object(socket.socket, "connect", side_effect=AssertionError("network")):
            code, out = self.run_it()
        self.assertEqual(code, 0, out)
        for n in self.BODIES:
            self.assertRegex(out, rf"pass\s+{n}: .*hash ok")

    def test_each_missing_file_is_reported(self):
        for n, f in self.FILES.items():
            with self.subTest(n):
                (self.raw / f).rename(self.raw / "gone")
                code, out = self.run_it()
                (self.raw / "gone").rename(self.raw / f)
                self.assertNotEqual(code, 0)
                self.assertRegex(out, rf"FAIL\s+{n}: missing")

    def test_wrong_hash_is_a_mismatch_not_ok(self):
        (self.raw / "capt/t.bin").write_bytes(b"T333")
        code, out = self.run_it()
        self.assertNotEqual(code, 0)
        self.assertRegex(out, r"FAIL\s+bnss_crpc_table: present, hash differs")
        self.assertNotRegex(out, r"pass\s+bnss_crpc_table")

    def test_fetch_wrong_hash_is_rejected_and_leaves_no_file(self):
        (self.raw / "capt/t.bin").unlink()
        code, out = self.fetch_table(self.serve(b"T333"))
        self.assertNotEqual(code, 0)
        self.assertIn("hash check failed", out)
        self.assertEqual(list((self.raw / "capt").iterdir()), [])

    def test_fetch_good_body_lands_in_a_missing_subdirectory(self):
        (self.raw / "capt/t.bin").unlink()
        (self.raw / "capt").rmdir()
        code, out = self.fetch_table(self.serve(b"t333"))
        self.assertEqual((self.raw / "capt/t.bin").read_bytes(), b"t333", out)


class ManifestTest(unittest.TestCase):
    def md_hashes(self) -> dict:
        md = (ROOT / "data" / "SOURCES.md").read_text()
        files = {"bns": "bns-prs.pdf", "ipc": "ipc-wipo.pdf", **NEW_FILES}
        return {n: re.search(rf"`{f}`.*?`([0-9a-f]{{64}})`", md).group(1) for n, f in files.items()}

    def manifest(self) -> dict:
        return json.loads((ROOT / "data" / "sources.json").read_text())

    def test_sources_json_matches_sources_md(self):
        m = self.manifest()
        self.assertEqual({n: s["sha256"] for n, s in m.items()}, self.md_hashes())

    def test_slice_15_entries_are_recorded_with_reuse_unconfirmed(self):
        m = self.manifest()
        for n, f in NEW_FILES.items():
            self.assertEqual(m[n]["file"], f)
            self.assertEqual(m[n]["reuse"], "unconfirmed")
            self.assertTrue(m[n]["url"].startswith("https://"))
            self.assertEqual(m[n]["bytes"], (MAIN_RAW / f).stat().st_size)

    def test_no_raw_file_is_tracked(self):
        out = subprocess.run(["git", "ls-files", "data/raw"], cwd=ROOT, capture_output=True, text=True, check=True)
        self.assertEqual(out.stdout, "")

    def test_altered_hash_is_detected(self):
        m = self.manifest()
        m["ipc"]["sha256"] = "0" * 64
        self.assertNotEqual({n: s["sha256"] for n, s in m.items()}, self.md_hashes())


if __name__ == "__main__":
    unittest.main()
