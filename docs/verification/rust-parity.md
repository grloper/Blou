# Portable Rust parity evidence

Date: 2026-10-11. Branch: `agent/rust-test-parity`, stacked on `agent/rust-workspace`. Local Ubuntu WSL, Rust 1.94.1, Python 3.12.3. Commands ran locally; local paths are omitted from excerpts.

Before changes, the workspace gate exited 0 with 37 Python tests and no Rust cases. All 27 portable test functions were written before implementation, then compiled against temporary API stubs. `cargo test --workspace --locked --offline --no-fail-fast` failed with these real output summaries:

```text
test result: FAILED. 0 passed; 2 failed; 0 ignored; 0 measured; 0 filtered out
test result: FAILED. 0 passed; 8 failed; 0 ignored; 0 measured; 0 filtered out
test result: FAILED. 0 passed; 7 failed; 0 ignored; 0 measured; 0 filtered out
test result: FAILED. 0 passed; 10 failed; 0 ignored; 0 measured; 0 filtered out
error: 4 targets failed:
    `--test dvc`
    `--test layout`
    `--test pin`
    `--test viewport`
```

Stubs were removed after this red run. The original Python files and assertions are unchanged.

The Python golden-file test first failed with `FileNotFoundError` and `FAILED (errors=1)` before the fixture existed. `.venv/bin/python scripts/gen_vectors.py` then printed `generated tests/vectors/portable-core.json`. Golden values cover row counts 1..4, a grid, viewport transforms and points for three phone sizes/all three monitors, damage clipping, swipe results, complete legacy DVC bytes and the synthetic SHA-256 digest.

`scripts/check-test-integrity.sh --update-baseline` printed `baseline updated: 68` (38 Python + 30 Rust). `scripts/verify.sh` exited 0 after implementation. Real output excerpts:

```text
All checks passed!
Ran 38 tests in 3.307s
OK
test-integrity: test-case count 68 >= baseline 68
test-integrity: OK.
== rust fmt
== rust clippy (-D warnings, locked, offline)
Finished `dev` profile [unoptimized + debuginfo] target(s) in 2.19s
== rust tests (locked, offline)
test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
test result: ok. 7 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
test python_golden_vectors_match_rust_outputs ... ok
test result: ok. 11 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
PASS: shell syntax + actionlint + ruff + unittest + test-integrity + offline demo + package build + rust fmt/clippy/test.
```

`cargo deny check` exited 0: `advisories ok, bans ok, licenses ok, sources ok`. `cargo audit` exited 0: `Loaded 1296 security advisories`, `Scanning Cargo.lock for vulnerabilities (32 crate dependencies)`. The original license check rejected ISC/BSD-3-Clause before those actual dependency licenses were reviewed and allowed; no advisory/lint exceptions were added.

Existing warning: the gate still prints the non-blocking mypy error at `security.py:66` (R1).

Limits: the DVC golden fixture deliberately preserves Python's known MonitorLayoutSize=0 defect and placeholder physical sizes. It proves reference parity, not usable protocol bytes; N5 must correct and cross-check against IronRDP. Synthetic pinning bytes are not a real certificate. X.509/TLS verification, trusted-root mismatch rejection, Windows displays, Android/NLA, Keystore enforcement and rendering remain UNVERIFIED. Python retirement has not been approved and no Python code/tests were removed.
