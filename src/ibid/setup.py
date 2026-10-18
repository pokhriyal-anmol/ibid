"""`ibid setup`: offline checklist of poppler tools and source PDFs. Makes no network call."""
import hashlib
import http.client
import json
import os
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

TOOLS = ["pdftotext", "pdftohtml", "pdfseparate", "pdfunite"]
INSTALL = ["  run: brew install poppler          (macOS)", "  run: apt install poppler-utils     (Debian)"]


def _fetch_hint(name: str) -> str:
    return "ibid setup --fetch bns" if name == "bns" else "ibid setup --fetch ipc --url <direct https PDF url>"


CAP = 200 * 1024 * 1024
IPC_NEEDS_URL = ("error: --fetch ipc needs --url. The WIPO link is signed and expires, so get a direct PDF URL "
                 "from the WIPO Lex page ({page}) and pass it with --url.")


def _allowed(url: str) -> bool:
    u = urlparse(url)
    return u.scheme == "https" and bool(u.hostname) or u.scheme == "http" and u.hostname in ("127.0.0.1", "localhost")


def _download(url: str, target: Path, size: int, sha256: str) -> str | None:
    """Stream to a temp file beside target, check size then hash, rename. Returns the failed check or None."""
    cap = min(CAP, size)
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=target.name + ".")
    try:
        got, h = 0, hashlib.sha256()
        with os.fdopen(fd, "wb") as f, urllib.request.urlopen(url, timeout=60) as r:
            while chunk := r.read(65536):
                got += len(chunk)
                if got > cap:
                    return f"size check failed: body exceeds {cap} bytes"
                h.update(chunk)
                f.write(chunk)
        if got != size:
            return f"size check failed: got {got} bytes, expected {size}"
        if h.hexdigest() != sha256:
            return f"hash check failed: got {h.hexdigest()}, expected {sha256}"
        os.replace(tmp, target)
        return None
    except http.client.IncompleteRead:
        return "size check failed: body truncated"
    except Exception as e:  # HTTPError, URLError, IncompleteRead, timeouts
        return f"download failed (HTTP/network error): {e}"
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def fetch(manifest: dict, raw_dir: str, name: str, url: str | None) -> int:
    src = manifest[name]
    if url is None and name == "ipc":
        print(IPC_NEEDS_URL.format(page=src["url"]), file=sys.stderr)
        return 1
    url = url or src["url"]
    target = Path(raw_dir) / src["file"]
    if target.exists():
        print(f"error: {target.resolve()} already exists; refusing to overwrite. Move it away to fetch again.", file=sys.stderr)
        return 1
    if not _allowed(url):
        print(f"error: url refused (only https, or http to 127.0.0.1/localhost): {url}", file=sys.stderr)
        return 1
    failed = _download(url, target, src["bytes"], src["sha256"])
    if failed:
        print(f"error: {name}: {failed}", file=sys.stderr)
        return 1
    print(f"fetched {name}: {target.resolve()} (hash ok)")
    return 0


def run(sources: str, raw_dir: str, fetch_name: str | None = None, url: str | None = None) -> int:
    manifest = json.loads(Path(sources).read_text())
    if fetch_name:
        if fetch(manifest, raw_dir, fetch_name, url):
            return 1
        run(sources, raw_dir)
        return 0
    ok = True
    for tool in TOOLS:
        found = shutil.which(tool)
        print(f"{'pass' if found else 'FAIL'}  tool {tool}" + (f" ({found})" if found else " not on PATH"))
        if not found:
            ok = False
            print("\n".join(INSTALL))
    for name, src in manifest.items():
        path = (Path(raw_dir) / src["file"]).resolve()
        if not path.is_file():
            ok = False
            print(f"FAIL  {name}: missing\n  get: {src['url']}\n  save as: {path}\n  or run: {_fetch_hint(name)}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != src["sha256"]:
            ok = False
            print(f"FAIL  {name}: present, hash differs (file not touched)\n  expected: {src['sha256']}\n  actual:   {actual}")
        else:
            print(f"pass  {name}: {path} hash ok")
    return 0 if ok else 1
