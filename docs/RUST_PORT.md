# Rust port plan

Status: workspace scaffolding implemented; the core modules have no behaviour yet. Python in `src/blou/` stays the executable reference until Rust passes the same cases (parity). See `docs/ROADMAP.md` for the ordered tasks.

Rust is pinned to 1.94.1 (including rustfmt and Clippy) in `rust-toolchain.toml`. Install rustup before `scripts/setup.sh`; setup fetches locked dependencies and the gate uses `--offline --locked`. The Python wheelhouse does not include Rust: offline setup also needs the pinned Rust toolchain and Cargo cache provisioned beforehand.

Supply-chain configuration follows the [cargo-deny configuration](https://embarkstudios.github.io/cargo-deny/checks/cfg.html) and [cargo-audit example](https://github.com/rustsec/rustsec/blob/main/cargo-audit/audit.toml.example). Optional online review commands (not hermetic tests):

```bash
cargo install cargo-deny --version 0.20.2 --locked
cargo install cargo-audit --version 0.22.2 --locked
cargo deny check
cargo audit
```

Both tools are development utilities, not runtime dependencies. Dependency additions must justify their license/source allowances; there are no ignored advisories. The skeleton has no external Rust dependencies. Security scans need a current advisory database and registry access; the local verification gate remains offline after setup.

## Workspace layout (proposed)

```
Cargo.toml                 # [workspace] resolver = "2", shared lints (clippy -D warnings), edition 2021
rust-toolchain.toml        # pinned stable (IronRDP master currently pins 1.94.1; Blou must be >= that)
crates/
  blou-core/               # no_std-friendly where practical; NO network, NO IronRDP
    src/layout.rs          # LayoutBuilder, MonitorLayout, validation (<=16, one primary at 0,0, no overlap)
    src/viewport.rs        # CoordinateMapper, SwipeNavigationController, damage-rect clipping
    src/dvc.rs             # display-control PDU encoding independent of IronRDP (cross-check oracle)
    src/pin.rs             # SHA-256 fingerprint normalisation + constant-time compare, pin policy (no TOFU)
  blou-rdp/                # depends on blou-core + pinned IronRDP crates
    src/config.rs          # blou layout -> ironrdp_connector::Config (monitor_layout, desktop_size)
    src/tls.rs             # ironrdp-tls Strict + pin callback / custom rustls verifier
    src/session.rs         # connect (NLA), frame callback, input events, DISPLAYCONTROL updates
  blou-android/            # cdylib; UniFFI (control plane) + JNI/ANativeWindow (pixels). crate-type = ["cdylib"]
android/                   # Gradle app shell: Kotlin UI only (SurfaceView host, swipe gestures, indicator dots,
                          #   Keystore/biometric credential storage). No protocol or geometry logic.
spike/ironrdp-multimon/    # stays out of the workspace (own [workspace]); delete once blou-rdp supersedes it
```

Dependency rule: `blou-core` must not depend on IronRDP; `blou-rdp` converts core types to IronRDP types and is where upstream API churn is absorbed. Keep the IronRDP dependency as a git rev (or a crates.io version once `Config::monitor_layout` ships in a release; see `docs/IRONRDP_FEASIBILITY.md` #4).

Android toolchain (not installed/verified on the dev box): rustup targets `aarch64-linux-android` (+ `x86_64-linux-android` for emulator), NDK, `cargo-ndk`, UniFFI bindgen in library mode.

## Mapping the 36 Python tests

Count: `scripts/test-baseline.txt` = 36 = 6 layout + 10 viewport + 2 dvc + 7 security + 6 desktop + 5 phase0.

Portable to `blou-core` (27 tests, port these FIRST, byte/number-for-number, no loosened expectations):

| Python file (cases) | Rust target | Notes |
|---|---|---|
| `tests/test_layout.py` (6) | `blou-core/tests/layout.rs` | horizontal row defaults, 2x2 grid, reject primary-not-at-origin / multiple primaries / overlap / negative coords |
| `tests/test_viewport.py` (10) | `blou-core/tests/viewport.rs` | coordinate mapping (monitor 0/1/2), server->screen, damage-rect clipping, swipe controller (4) |
| `tests/test_dvc.py` (2) | `blou-core/tests/dvc.rs` | caps PDU and 3-monitor layout PDU bytes; add a cross-check against `ironrdp-displaycontrol` output in `blou-rdp` tests (header added by the DVC wrapper; see feasibility doc #5) |
| `tests/test_phase0.py` geometry classes (2) | `blou-core/tests/layout.rs` | `test_three_monitor_bounding_box`, `test_non_overlapping_contiguous_span` (5760x1080 bounding box) |
| `tests/test_security.py` (7) | `blou-core/tests/pin.rs` (6) + keystore-manifest invariant stays as data test | fingerprint exact match, colon-normalisation, single-bit mismatch, unpinned = reject, invalid format error, malformed cert rejected without panic |

Stay in Python (9 tests, not ported): `tests/test_desktop.py` (6, Windows workbench) and the 3 `TestPatchIntegrity` cases in `tests/test_phase0.py` (check FreeRDP patch/script contents). They keep running in `scripts/verify.sh` while the FreeRDP fallback and workbench exist.

Method per module: (1) write the Rust test file mirroring the Python case names (`test_screen_to_server_monitor_one` -> `fn screen_to_server_monitor_one`); (2) make it compile against stubs and see it fail; (3) implement; (4) add golden vectors emitted by the Python implementation (JSON under `tests/vectors/`, generated by a script and checked in) so parity is mechanical, not hand-copied; (5) when all 27 pass in both languages and vectors agree, mark parity in ROADMAP. Do not delete Python tests until the owner approves; `scripts/check-test-integrity.sh` counts `#[test]` too, so the baseline only rises.
