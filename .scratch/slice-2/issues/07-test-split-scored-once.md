# Score the test split once after freezing, refuse a second score without a flag

Status: needs-triage
Blocked by: 02, 06

What to build: a frozen-rule record (rule version and hash) and a guard in the run command: the test split can be scored only against a frozen rule, and only once. A second test score is refused unless an explicit flag (for example `--rescore-test`) is passed; when it is, the first test score is kept and both are reported. The guard keys on the pinned test-file hash from ticket 6, not the path.

User stories: 9.

Acceptance criteria:
- On a fixture test split, scoring before a rule is frozen is refused.
- First scoring after freeze succeeds and is recorded; a second attempt without the flag exits non-zero and writes nothing (known-bad).
- With the flag, the second score is written and the first is still present and reported.
- Copying the test file to a new path does not bypass the guard.
