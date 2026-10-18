# ibid setup --fetch bns|ipc: verified, non-overwriting download

Status: done
Blocked by: 01

What to build:
- `ibid setup --fetch bns` downloads from the manifest URL; `ibid setup --fetch ipc --url <url>` downloads from the user-supplied URL. Without `--url`, `--fetch ipc` exits non-zero and explains that the WIPO link is signed and expires, so the user must obtain a direct PDF URL from the WIPO Lex page and pass it.
- Only `https://` URLs are accepted, plus `http://127.0.0.1` and `http://localhost` (for tests). Any other scheme or host is refused before connecting. Standard library only (`urllib.request`).
- If the target file already exists (even with a wrong hash), refuse, say so, and stop without a network call.
- Stream to a temporary file in the same directory as the target, abort once the body exceeds the 200 MB cap (or the manifest size, if a test manifest sets a smaller one), check the SHA-256, and only then rename into place. Any failure deletes the temporary file, leaves `data/raw/` as it was, and names the check that failed (size or hash or HTTP error).
- After a successful fetch, report success and run the ticket 1 checklist.

User stories: 4, 5, 6 (and Decisions 3, 4, 5).

Acceptance criteria (tests through `ibid setup` against an `http.server` bound to 127.0.0.1 serving known files, with a test manifest via `--sources` and a temp `--raw-dir`):
- Correct body: file lands at the target with the manifest hash, exit 0.
- Wrong-hash body, truncated body, oversized body: each exits non-zero, names the failed check, and the raw dir contains exactly what it held before (no target, no temp file).
- Existing file at the target: refused, the file is byte-identical afterwards, and the test server records no request.
- `--url http://example.com/x.pdf` (non-local http) and a `file://` URL: refused before any connection.
- `--fetch ipc` without `--url`: non-zero exit and the explanation.
- Each of these tests was seen failing once against known-bad code (e.g. rename before hash check) before being reported green.
