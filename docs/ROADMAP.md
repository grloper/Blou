# Roadmap / agent backlog

Direction (DR-001 in `SPEC.md`): Rust-first product. Rust core + thin Android UI, IronRDP preferred engine, FreeRDP fallback. Python in `src/blou/` is the reference until Rust parity.

Rules: do tasks top to bottom; each has a runnable acceptance check. Finish with `scripts/verify.sh` green and read all of its output. No CI (billing blocked): merge with `[skip ci]`; never force-push `main`. Tick the box + CHANGELOG line when done. `[human]` = needs a person/hardware; an agent must stop and report, not simulate.

## P0: Rust-first foundation
- [x] **N1 Spike results**: offline IronRDP multi-monitor spike on branch `spike/ironrdp-multimon`, findings in `docs/IRONRDP_FEASIBILITY.md`. Accept: `cd spike/ironrdp-multimon && cargo test` = 6 passed (on that branch).
- [x] **N2 Rust workspace skeleton**: root `Cargo.toml` workspace with `crates/blou-core` (empty modules), Rust 1.94.1, workspace lints, lockfile, cargo-deny/audit policies. `scripts/verify.sh` requires fmt, Clippy `-D warnings` and locked offline tests (Python steps unchanged). Evidence: `docs/verification/rust-workspace.md`; baseline raised to 37 for the workspace boundary test.
- [ ] **N3 Port geometry tests first** (`docs/RUST_PORT.md` table): `tests/layout.rs` (6 + 2 phase0 geometry cases) and `tests/viewport.rs` (10) written before implementation, see them fail, then implement `layout.rs`/`viewport.rs`. Accept: 18 Rust tests pass; golden vectors generated from Python (`scripts/gen_vectors.py`, checked in) match Rust output. Python tests untouched.
- [ ] **N4 Certificate pinning in Rust**: `blou-core::pin` with the 7 security cases (6 + keystore manifest data test); SHA-256, constant-time compare, no TOFU. Accept: tests pass incl. malformed-cert-no-panic; a `blou-rdp` test drives `ironrdp-tls` Strict + callback with a fixture self-signed cert: match accepted, single-bit mismatch rejected (confirm the callback semantics in `docs/IRONRDP_FEASIBILITY.md` #7 or document the needed custom verifier).
- [ ] **N5 Display-control encoder**: `blou-core::dvc` caps + monitor-layout PDUs (the 2 DVC cases) and a `blou-rdp` cross-check test vs `ironrdp-displaycontrol` bytes for 1..16 monitors. Accept: byte-equal tests; odd widths handled explicitly (adjust before encode).
- [ ] **N6 `blou-rdp` config builder**: `LayoutBuilder` -> `ironrdp_connector::Config { monitor_layout, desktop_size }`, NLA only, TLS Strict. Pin IronRDP by git rev (or release once #1675 ships). Accept: the spike's GCC byte tests re-run inside the workspace; spike dir then removable.
- [ ] **N7 [human] Phase 0 gate on a real Windows 11 host**: run the checklist in `docs/IRONRDP_FEASIBILITY.md` with FreeRDP, record evidence under `docs/verification/` (redacted). Gate: Windows reports 3 displays. Agents must not mark this done without that evidence.
- [ ] **N8 [human] IronRDP connect with NLA to the Windows host**: small `blou-rdp` example bin using `ironrdp-tokio` + `perform_credssp` + pinned cert; same display checks as N7. Decision point: if it fails, record why and keep FreeRDP (hybrid, see DR-001).

## P1: Android
- [ ] **N9 Android toolchain proof**: install NDK + `cargo-ndk`, `rustup target add aarch64-linux-android x86_64-linux-android`, build `blou-core` and `blou-rdp` for both. Accept: `.so` produced for arm64-v8a; record rustc/NDK versions; confirm rustls crypto provider (ring/aws-lc) builds with NDK clang.
- [ ] **N10 Android bridge `blou-android`**: UniFFI control plane (connect, disconnect, set layout, key/touch events, state callbacks) + frame path via shared buffer/`ANativeWindow`. Accept: instrumented/JVM test calls through bindings against a loopback fake; frame path benchmark recorded.
- [ ] **N11 Viewport UI shell** (`android/`, Kotlin): SurfaceView crops the active monitor rect, swipe between monitors, indicator dots, touch -> `blou-core` mapping, `FLAG_SECURE`. No geometry in Kotlin. Accept: emulator screenshot test; mapping covered by N3 tests.
- [ ] **N12 Credential storage** (Android Keystore EC P-256 + biometric, per SPEC 5b) [human: device].
- [ ] **N13 Dynamic layout updates**: DISPLAYCONTROL mid-session via `blou-rdp` (SPEC phase 4). [human: Windows host]

## P2: parity and cleanup
- [ ] **N14 Parity declaration**: all 27 portable cases pass in Rust with vector parity; owner approves retiring the Python equivalents (`tests/test_desktop.py`, `tests/test_phase0.py` stay until the workbench/FreeRDP are retired).
- [ ] **N15 Retire FreeRDP** only after G0, G1, G2 (DR-001) pass; otherwise keep it as the engine behind `blou-core`.

## Python reference track (demoted; do only when needed for parity or hygiene)
These are the previous backlog items; unchanged and still unticked unless stated.

### Hygiene and correctness (offline, small)
- [ ] **R1 Fix mypy error** in `src/blou/security.py:66` (`str | None` assigned to `str`). Accept: `mypy --ignore-missing-imports src` reports 0 errors; then make mypy blocking in `scripts/verify.sh`.
- [ ] **R2 Remove ruff ignores `F401`,`F841`** from `ruff.toml` by cleaning the 7 findings. Accept: `ruff check` passes with the ignores deleted.
- [ ] **R3 Make `blou.desktop` importable on non-Windows**: guard Windows-only `ctypes.windll`/`wintypes`; `monitors()`/`capture()` raise `OSError("Windows only")` elsewhere. Accept: new test on Linux; existing tests unchanged.
- [ ] **R4 Python 3.10 compatibility check** under 3.10, 3.12 and 3.13; record in README.

### Protocol core completeness (feeds Rust parity vectors)
- [ ] **R5 DVC decode round-trip** (`DisplayControlDecoder`); malformed input raises `ValueError`.
- [ ] **R6 Layout validation limits** (>16 monitors, zero/negative sizes, overlap, no primary; cite MS-RDPBCGR TS_UD_CS_MONITOR). One test per rule. Note: Rust N3 must include these.
- [ ] **R7 More layouts** (`create_vertical_column`, `create_grid`, negative-origin mapping).
- [ ] **R8 Viewport fuzz tests** (seeded; round trip within 1 px).
- [ ] **R9 Fingerprint API** (SHA-256/SHA-1 prefixes, constant-time compare, reject other lengths).

### FreeRDP integration (fallback engine; needs `scripts/setup.sh --with-freerdp` and network)
- [ ] **R10 Rebase `patches/0002-android-cmake-cross-compile-fixes.patch`** onto FreeRDP `63b948ca5`; add `scripts/check_patches.sh`.
- [ ] **R11 Parameterize `scripts/run_phase0_probe.sh`** (`--help`, require `HOST`, no default IP).
- [ ] **R12 Document the manual Phase 0 procedure** in `docs/PHASE0.md` (superseded in part by the checklist in `docs/IRONRDP_FEASIBILITY.md`; reconcile).

### Packaging and project
- [ ] **R13 Typed package** (`py.typed`). 
- [ ] **R14 CLI** (`python -m blou layout --monitors 3 --json`).
- [ ] **R15 Workbench smoke test on Linux with fake capture** (after R3).

## Out of scope until a maintainer says otherwise
Publishing to PyPI or crates.io, hosted CI, changing the license, Android UI beyond N11.
