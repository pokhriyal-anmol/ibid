# Handoff: run wf-ship on Ibid slice 4

Paste this into a new Claude Code chat opened in `/Users/anmolpokhriyal/projects/ibid`.

## Your job

Take Ibid slice 4 from an approved spec to a built, reviewed v1 using the `wf-ship` workflow, then bring me the report. Do not stop to ask me things in the middle: that is what `wf-ship` is for.

## State (2026-10-14)

- Ibid `main` is at `38812b8` on https://github.com/pokhriyal-anmol/ibid (private). Slices 1 to 3 are merged. 198 tests pass. Read `AGENTS.md`, `CONTEXT.md` and `docs/adr/` first.
- The toolkit is `/Users/anmolpokhriyal/projects/workflow` (private, pushed, HEAD `044e586`). `wf-ship` is the parent workflow, `wf-owner` is the question queue. Read `docs/owner-proxy.md` there before running anything.
- `wf-ship` and `wf-owner` are symlinked into `.claude/workflows/` of this repo. They are only visible in a fresh session. Confirm with the Workflow tool's "Available" list; if they are missing, ask me, do not copy scripts around.
- No lawyer review is possible (personal project). Do not claim one anywhere. Scores stay private.

## Step 1: write and approve the slice 4 spec, in conversation

`wf-ship` needs `.scratch/slice-4/spec.md`. It does not exist. A workflow cannot ask questions, so this part is done with me.

Candidate scope, my default if I say "go": an **MCP server** in `src/ibid/` exposing the existing deterministic lookups (provision by citation, keyword search, cross-references, concordance) as tools, stdlib only, with no model in retrieval (ADR 0001). Test seam: the server's tool calls, driven through a stdio harness in `unittest`. Out of scope: any chat UI, any change to the frozen rule, gold sets or concordance files.

Grill me briefly on it (at most 5 questions), write `.scratch/slice-4/spec.md` with numbered user stories, one test seam and an "out of scope" list, and wait for my "approved". If I would rather pick a different slice, I will say so.

## Step 2: run it

Run from this directory, in this session:

```
Workflow  name: "wf-ship"  args: {"slug": "slice-4"}
```

Use `{"slug": "slice-4", "gates": "tickets"}` instead only if I ask to read the tickets first.

What it does: decomposes the spec, has a proxy approve or hold each ticket, builds in worktree waves, reviews, then writes `.scratch/slice-4/v1-report.md`. Questions it cannot settle go to `.scratch/_owner/questions/`.

## Step 3: report back

Read `.scratch/slice-4/v1-report.md` and tell me, in the executive-brief style: status, what v1 does, the test result as measured, every assumption made for me, what was held, and how many questions are queued. Check that every spec story has a done ticket; the report must say `partial` if not.

If it says a session is ready, `.scratch/_owner/session-NNN.md` is the answer sheet. I fill in the `Answer:` lines, then you run `wf-owner` with `{"mode": "learn"}`, then `wf-ship` again for the same slug.

## Things that will bite

- Tests: `IBID_BNS_PDF=$PWD/data/raw/bns-prs.pdf IBID_IPC_PDF=$PWD/data/raw/ipc-wipo.pdf uv run python -m unittest discover -s tests` (about 30 s). Worktrees have no `data/raw/`; the test helpers find the PDFs through the git common dir.
- A hook rejects `git commit` when a heredoc is in the same Bash call. Use `-m $'subject\n\nbody'` or separate calls. Commits are Conventional Commits.
- Do not read the Act PDFs into context. Use `pdftotext -f N -l N`.
- Do not open or merge a PR without my explicit go. The PR base is `main`.
- `wf-review` is expensive (about 1M tokens). `wf-ship` runs it once; do not run it again by hand unless I ask.
- Writing style: no em dashes, no AI-sounding patterns, short.

## Verify, because these are untested

1. After the build, `testsGreen` in the report comes from the build's own merge test (a new fallback). Check it is true or false, not null.
2. Check `partial` appears if a spec story has no done ticket.
3. If a session is offered, check it holds only questions that are mine (preference, product, credentials, irreversible), not craft questions.

Tell me which of these held and which did not.
