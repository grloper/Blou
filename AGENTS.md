# AGENTS.md

Instructions for AI coding agents and contributors.

## Verification gate (required before claiming anything works)

Run exactly this and read the output (bash, python3 >= 3.10, internet for pip):

```
scripts/verify.sh
```

Exit code 0 = pass; anything else = not done. CI (`.github/workflows/gate.yml`) runs the same script (job `verify`) plus `scripts/check-test-integrity.sh` (job `test-integrity`). What it runs: creates a venv (.venv-verify), ruff check, mypy (non-blocking, pre-existing failures), unittest discover tests, offline demo, actionlint

**Not checked by the gate:** Windows/Android builds, FreeRDP native submodule, real remote sessions (scripts/*.ps1 / build_*).

Rules: never delete tests, add skip/ignore/xfail markers, remove assertions or loosen expected values to get green. `test-integrity` also fails if the number of test cases drops below `scripts/test-baseline.txt`; only the owner may approve a test change (PR label `test-change-approved`; refresh the baseline with `scripts/check-test-integrity.sh --update-baseline`). Do not edit `.github/`, `scripts/verify.sh` or `scripts/check-test-integrity.sh` to make a failing check pass; they are owned by @grloper (CODEOWNERS).
