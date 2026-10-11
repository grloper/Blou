# AGENTS.md

Instructions for AI coding agents (OpenAI Codex cloud/CLI, and any other) and human contributors. Read this fully before changing anything.

## What this project is
Blou: pre-alpha Python library exploring virtual multi-monitor display geometry for a phone-sized RDP client, plus a Windows-only local desktop workbench. No Android/RDP client exists yet. Do not write docs or code comments that claim otherwise.

Direction (DR-001 in `SPEC.md`, proposed): Rust-first. Rust core + thin Android UI, IronRDP as preferred RDP engine, FreeRDP kept as fallback until gates pass. The Python package is the executable reference until Rust parity. Read `docs/IRONRDP_FEASIBILITY.md` (evidence, UNVERIFIED items) and `docs/RUST_PORT.md` (layout, test mapping) first. The Phase 0 gate (Windows accepts a fabricated multi-monitor layout) is still UNVERIFIED; never claim it.

## Setup (once per clean sandbox)
```
scripts/setup.sh
```
Needs Python >= 3.10 and network once. Creates `.venv`, installs `pip install -c constraints-dev.txt -e ".[dev]"` (exact pins). After that everything works **offline**.
Fully offline sandbox: while online run `scripts/setup.sh --prefetch /path/wheels`, later `scripts/setup.sh --wheelhouse /path/wheels`.
Cloud-sandbox tip: put `scripts/setup.sh` in the environment's setup script; run `scripts/verify.sh` as the maintenance/check command. The `FreeRDP` submodule is NOT needed for the gate; skip it unless a task says otherwise (`scripts/setup.sh --with-freerdp`).

## Commands
| Purpose | Command |
|---------|---------|
| Setup | `scripts/setup.sh` |
| **The gate (single source of truth)** | `scripts/verify.sh` |
| Tests only | `.venv/bin/python -m unittest discover -s tests -v` |
| One test file | `.venv/bin/python -m unittest tests.test_layout -v` |
| Lint | `.venv/bin/ruff check src tests scripts` |
| Types (non-blocking) | `.venv/bin/mypy --ignore-missing-imports src` |
| Build sdist+wheel | `.venv/bin/python -m build --no-isolation` |
| Offline demo | `.venv/bin/python scripts/demo_local.py` |
| Rust format (once root `Cargo.toml` exists) | `cargo fmt --all -- --check` |
| Rust lint | `cargo clippy --workspace --all-targets -- -D warnings` |
| Rust tests | `cargo test --workspace --locked --offline` |
| Rust Android target check (needs `rustup target add aarch64-linux-android`) | `cargo check --workspace --target aarch64-linux-android` |

`scripts/verify.sh` runs: shell syntax, actionlint, ruff, mypy (warn only), unittest, test-integrity, demo fixture unchanged, package build, then mandatory Rust fmt/clippy/test (`--locked --offline` for lint/tests). Missing cargo fails the gate. Exit 0 = pass. Read the whole output; do not infer success from partial output.

## Repo map
- `src/blou/` library: `layout.py` (monitor layouts), `viewport.py` (touch<->desktop mapping, swipe), `dvc.py` (display-control PDU encoding), `security.py` (fingerprint pinning), `desktop.py` (Windows workbench; needs Pillow, uses Windows APIs at runtime).
- `tests/` unittest suites, one per module (+ `test_phase0.py` which checks FreeRDP patch/script contents).
- `scripts/` `setup.sh`, `verify.sh`, `check-test-integrity.sh`, `demo_local.py`, Windows/Android helpers (`*.ps1`), FreeRDP Phase 0 helpers.
- `patches/` FreeRDP patches; `FreeRDP/` optional submodule (upstream 3.31.1).
- `docs/` design + evidence; `docs/ROADMAP.md` is the prioritized backlog: pick the top unchecked task.

## Definition of done
1. `scripts/verify.sh` exits 0 and you read its output.
2. New/changed behaviour has tests that fail without your change.
3. Test count did not drop below `scripts/test-baseline.txt`. If you added tests, raise it: `scripts/check-test-integrity.sh --update-baseline`.
4. Docs and README claims match what you actually ran. If something was not run, say so.
5. `CHANGELOG.md` updated under `[Unreleased]` for user-visible changes; the ROADMAP item ticked.
6. No personal data added (real IPs, hostnames, usernames, absolute home paths, credentials, emails). Use placeholders and env vars.

## Forbidden
- Deleting tests, adding `skip`/`xfail`/`expectedFailure`, removing assertions, or loosening expected values to make a check pass.
- Skipping or editing `scripts/verify.sh`, `scripts/check-test-integrity.sh`, `scripts/test-baseline.txt` (except the documented `--update-baseline` after adding tests) or `ruff.toml` rules to hide failures. Fixing a genuine bug in a gate script is allowed only as its own clearly described change.
- Claiming Android, FreeRDP-native, real-RDP-session or Windows-capture behaviour works without actually running it.
- Network calls at test time; tests must be hermetic (loopback only).
- Publishing to PyPI, pushing tags/releases, force-pushing, or changing repo settings without explicit maintainer instruction.
- Adding GitHub Actions workflows or triggering CI: hosted CI is not part of the workflow; the local gate is. Put `[skip ci]` at the end of commit subjects.

## Running offline
After `scripts/setup.sh`, `verify.sh` and all tests need no network. Tests only use loopback sockets and synthetic fixtures. If `.venv` is missing and there is no network, use the wheelhouse flow above.

## Rust rules
- Port tests first: write the Rust test from the Python case (same name, same numbers), see it fail, then implement. Use Python-generated golden vectors for parity. Keep Python until the owner approves retiring it.
- `blou-core` must not depend on IronRDP; pin IronRDP by exact version or git rev (no branches). Never use `CertificateValidation::DangerouslyAcceptInvalidCertificate`; never add TOFU.
- `cargo clippy ... -D warnings` and `cargo fmt` must be clean. No `unwrap()` on network/untrusted input paths. Minimise `unsafe` (JNI/FFI only, each block commented).
- Do not run `cargo publish`. Commit `Cargo.lock` for bins/cdylib workspaces. `target/` is never committed.
- Android/Windows steps marked `[human]` in `docs/ROADMAP.md` cannot be completed by an agent; stop and report.

## Style
Python 3.10+ compatible syntax (no 3.11+-only features in `src/`). Rust: `rustfmt` defaults, edition 2021, workspace lints. Standard library only in the protocol core (`layout`, `viewport`, `dvc`, `security`). Keep commits small; subjects imperative, ending in `[skip ci]`.

## Codex notes
Codex reads this file automatically. Suggested environment config: setup script `scripts/setup.sh`; check command `scripts/verify.sh`; internet may be disabled after setup. Work from `docs/ROADMAP.md`, one task per PR/branch.
