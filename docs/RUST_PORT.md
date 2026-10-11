# Rust port plan

Status: all 27 portable Python cases have passing Rust counterparts and Python-generated golden vectors. Python in `src/blou/` remains the executable reference; retirement requires owner approval. Certificate fixture/TLS enforcement, upstream DVC correctness, RDP and Android integration remain pending. See `docs/ROADMAP.md` for the ordered tasks.

Rust is pinned to 1.94.1 (including rustfmt and Clippy) in `rust-toolchain.toml`. Install rustup before `scripts/setup.sh`; setup fetches locked dependencies and the gate uses `--offline --locked`. The Python wheelhouse does not include Rust: offline setup also needs the pinned Rust toolchain and Cargo cache provisioned beforehand.

Supply-chain configuration follows the [cargo-deny configuration](https://embarkstudios.github.io/cargo-deny/checks/cfg.html) and [cargo-audit example](https://github.com/rustsec/rustsec/blob/main/cargo-audit/audit.toml.example). Optional online review commands (not hermetic tests):

```bash
cargo install cargo-deny --version 0.20.2 --locked
cargo install cargo-audit --version 0.22.2 --locked
cargo deny check
cargo audit
```

Both tools are development utilities, not runtime dependencies. Dependency additions must justify their license/source allowances; there are no ignored advisories. The port uses exactly pinned `ring` 0.17.14 for SHA-256, `subtle` 2.6.1 for constant-time comparison and test-only `serde_json` 1.0.145 for the golden oracle. `Cargo.lock` pins transitive resolution. Security scans need a current advisory database and registry access; the local verification gate remains offline after setup.

API references: [ring digest](https://docs.rs/ring/0.17.14/ring/digest/), [subtle ConstantTimeEq](https://docs.rs/subtle/2.6.1/subtle/trait.ConstantTimeEq.html), [serde_json](https://docs.rs/serde_json/1.0.145/serde_json/). Local dependency review: none of these upstream repositories are archived; ring's last push was 2026-07-23, serde_json's 2026-10-11, subtle's 2024-08-03. Subtle has low recent activity; cargo-audit reported no advisories for this resolution, which does not constitute a code audit. Cargo-deny license policy adds only ISC (ring/untrusted) and BSD-3-Clause (subtle), based on downloaded manifests.

`scripts/gen_vectors.py` generates `tests/vectors/portable-core.json`; Python tests require it to be reproducible and Rust compares complete output values. The DVC reference contains a known MonitorLayoutSize defect (0 instead of 40), also visible by reading the spike test. This port deliberately preserves exact reference bytes for the parity test, with explicit warnings in the API. N5 must correct and cross-check them before session integration. The security reference uses synthetic bytes rather than an X.509 certificate; these tests prove fingerprint policy, while N4 must prove fixture-certificate/TLS behaviour.

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
