# Rust workspace scaffolding evidence

Date: 2026-10-11. Branch: `agent/rust-workspace`. Local Ubuntu WSL, Python 3.12.3, Rust 1.94.1. Paths omitted from output excerpts to avoid committing local identities.

Before edits: `scripts/setup.sh && scripts/verify.sh` exited 0. Output included `Ran 36 tests`, `OK`, `test-case count 36 >= baseline 36`, and the legacy Rust `SKIP`.

Red test, before adding a manifest:

```text
$ .venv/bin/python -m unittest discover -s tests -p test_rust_workspace.py -v
test_core_has_no_ironrdp_dependency ... FAIL
AssertionError: 101 != 0 : error: could not find `Cargo.toml`
Ran 1 test
FAILED (failures=1)
```

The test uses Cargo metadata to guard edition 2021, no publication, and no direct IronRDP dependency in `blou-core`. It passed after the workspace was added.

`scripts/check-test-integrity.sh --update-baseline` printed `baseline updated: 37`.

After implementation: `scripts/setup.sh && scripts/verify.sh` exited 0. Output excerpts:

```text
All checks passed!
Ran 37 tests in 3.312s
OK
test-integrity: test-case count 37 >= baseline 37
test-integrity: OK.
wheel contains blou package: blou-0.1.0-py3-none-any.whl
== rust fmt
== rust clippy (-D warnings, locked, offline)
Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.31s
== rust tests (locked, offline)
test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
PASS: shell syntax + actionlint + ruff + unittest + test-integrity + offline demo + package build + rust fmt/clippy/test.
```

Zero Rust tests is intentional at this scaffold stage; no core behaviour has been implemented or claimed. All 36 original Python tests still ran.

`cargo deny check` (0.20.2) exited 0 with `advisories ok, bans ok, licenses ok, sources ok`. `cargo audit` (0.22.2) exited 0 with `Loaded 1296 security advisories` and `Scanning Cargo.lock for vulnerabilities (1 crate dependencies)`. The only lockfile package is the workspace core; these scans do not establish the security of future dependencies.

Existing non-blocking warning: mypy reports `src/blou/security.py:66: error: Incompatible types in assignment` and `Found 1 error in 1 file (checked 6 source files)`. R1 remains open.

UNVERIFIED: Rust parity, TLS pinning, RDP engine integration, Windows three-display acceptance, Android builds, phone/NLA connection, native capture and per-frame performance. Hardware gates remain open. No hosted CI was used.
