"""`ibid setup` through main(): offline checklist. Fixtures are tiny invented non-PDF files."""
import contextlib
import http.server
import hashlib
import io
import json
import os
import re
import socket
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from ibid.cli import main

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
        manifest = {n: {"file": f"{n}.bin", "url": f"https://example.org/{n}", "bytes": len(b),
                        "sha256": hashlib.sha256(b).hexdigest()} for n, b in self.files.items()}
        self.sources = Path(self.tmp.name) / "sources.json"
        self.sources.write_text(json.dumps(manifest))
        for n, b in self.files.items():
            (self.raw / f"{n}.bin").write_bytes(b)
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

    def test_http_error_leaves_nothing(self):
        self.srv.body = None
        code, out = self.fetch("--fetch", "ipc", "--url", self.url)
        self.assert_clean_failure(code, out, "HTTP")

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
