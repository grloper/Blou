# Roadmap / agent backlog

Prioritized. Each task has an acceptance test an agent can run without human input. Do them top to bottom. Always finish with `scripts/verify.sh` green. Tick the box and add a CHANGELOG line when done.

## P0: hygiene and correctness (offline, small)
- [ ] **R1 Fix mypy error** in `src/blou/security.py:66` (`str | None` assigned to `str`). Accept: `mypy --ignore-missing-imports src` reports 0 errors; then make mypy blocking in `scripts/verify.sh` (replace `warn_step "mypy"` with a plain `mypy` step).
- [ ] **R2 Remove ruff ignores `F401`,`F841`** from `ruff.toml` by cleaning the 7 findings (`ruff check --select F401,F841 src tests scripts`). Accept: `ruff check` passes with the ignores deleted; no test changes other than removing unused imports.
- [ ] **R3 Make `blou.desktop` importable on non-Windows** (Linux CI): guard Windows-only `ctypes.windll`/`wintypes` use behind a platform check; `monitors()`/`capture()` raise a clear `OSError("Windows only")` elsewhere. Accept: new test imports `blou.desktop` on Linux and asserts that error; existing tests unchanged.
- [ ] **R4 Python 3.10 compatibility check**: add `scripts/verify.sh` optional step (`PYTHON_MATRIX=1`) or a documented command running the unit tests under 3.10 and 3.12 via `uv run --python X`. Accept: tests pass on 3.10, 3.12 and 3.13; record result in README.

## P1: protocol core completeness
- [ ] **R5 DVC decode round-trip**: add `DisplayControlDecoder` (inverse of `DisplayControlEncoder` for caps and monitor-layout PDUs, MS-RDPEDISP). Accept: property-style tests encoding then decoding layouts from `LayoutBuilder` (1..16 monitors) return equal data; malformed/truncated input raises `ValueError`.
- [ ] **R6 Layout validation limits**: `LayoutBuilder.validate_layout` must reject >16 monitors, zero/negative sizes, overlapping monitors and no primary monitor (per MS-RDPBCGR TS_UD_CS_MONITOR). Accept: one test per rule, with the spec section cited in a comment.
- [ ] **R7 More layouts**: `create_vertical_column(count)` and `create_grid(rows, cols)`; negative-origin layouts supported by the mapper. Accept: tests for bounding boxes and `screen_to_server`/`server_to_screen` round trip.
- [ ] **R8 Viewport fuzz tests**: seeded random touches/damage rects never raise and `server_to_screen(screen_to_server(p))` is within 1 px. Accept: deterministic (fixed seed) tests, no new deps.
- [ ] **R9 Fingerprint API**: support SHA-256 and SHA-1 prefixes explicitly with constant-time compare; reject other lengths. Accept: tests for case/colon normalization and wrong-length rejection.

## P2: FreeRDP integration (needs `scripts/setup.sh --with-freerdp` and network)
- [ ] **R10 Rebase `patches/0002-android-cmake-cross-compile-fixes.patch`** onto FreeRDP `63b948ca5` (fails today at `client/Android/cmake/ExternalOpenSSL.cmake:26`). Accept: `git -C FreeRDP apply --check ../patches/*.patch` succeeds for both patches; add a script `scripts/check_patches.sh` that does this check and a test that it exists.
- [ ] **R11 Parameterize `scripts/run_phase0_probe.sh`**: usage/help flag, refuse to run without `HOST` argument (no default IP). Accept: `bash scripts/run_phase0_probe.sh --help` exits 0; test updated to match (do not weaken existing assertions).
- [ ] **R12 Document an end-to-end manual Phase 0 procedure** in `docs/PHASE0.md` with expected output and what counts as pass/fail; clearly marked as manual and unverified until someone runs it.

## P3: packaging and project
- [ ] **R13 Typed package**: add `src/blou/py.typed` and `[tool.setuptools.package-data]`. Accept: built wheel contains `blou/py.typed` (assert in `verify.sh` build step).
- [ ] **R14 CLI**: `python -m blou layout --monitors 3 --json` prints layout; console script `blou`. Accept: tests invoke `main(argv)` and check JSON.
- [ ] **R15 Windows workbench smoke test on Linux with fake capture**: dependency-inject the capture function so `serve()` can be tested end to end without Windows. Accept: test fetches a frame over loopback with a fake image source (after R3).

## Out of scope until a maintainer says otherwise
Android UI, PyPI publishing, hosted CI, changing the license.
