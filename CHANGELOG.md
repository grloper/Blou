# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow [SemVer](https://semver.org/); 0.x means the API may change at any time.

## [Unreleased]

### Added
- FreeRDP fallback R10: rebased Android CMake patch on the exact 3.31.1 gitlink, removed absent helper references and OpenSSL source patching, retained cJSON's policy minimum, forwarded CMP0057 and quoted NDK environment paths. Added a non-mutating patch checker and five offline fixture regression tests. Owner prioritized fallback work; native Android build remains UNVERIFIED.
- NLA-only connector configuration prototype with checked geometry and mandatory pin config, reusing all six IronRDP spike cases. Adoption is blocked by RSA's unpatched advisory, unmaintained atomic-polyfill and duplicate dependency families; no waivers or engine patches. Added hardware gate checklists and recorded Android core preflight failure (Rust targets installed, Android Clang unavailable to WSL).
- Display-control adapter using unmodified pinned IronRDP, with complete byte cross-checks for 1–4 monitors, grid and protocol dimension boundaries. Corrected the Rust/Python MonitorLayoutSize field and physical-size placeholders; reject odd widths and out-of-range layouts. Existing tests preserved and golden vectors regenerated from the corrected reference. Cargo-deny duplicate-family policy remains failing and documented without exceptions.
- Always-on Rustls certificate pin verifier and client config in `blou-rdp`: no TOFU/override, no resumption or key logging, upstream X.509 parsing and TLS signatures. Added synthetic certificate fixtures, 256 single-bit mismatch controls, trusted-root rejection and in-memory TLS 1.2/1.3 tests. Rustls pinned to patched 0.23.45 after the advisory scan rejected 0.23.41.
- Ported all 27 portable Python cases to Rust before implementation; added validated geometry, viewport transforms/swipes, SHA-256 fingerprint policy using ring/subtle, and offline DVC-reference serialization. Added Python-generated golden vectors and reproducibility checks; all original Python tests remain active. The legacy DVC header defect is documented and pending N5 correction before session use.
- Rust workspace scaffolding with `blou-core`, Rust 1.94.1, committed lockfile and shared lints (unsafe code forbidden). The verification gate now requires offline, locked Rust lint and tests; Python tests remain active.
- Dependency policies in `deny.toml` and `.cargo/audit.toml`, with no advisory exceptions; workspace metadata test guards the core/engine boundary.
- Docs: Rust-first decision record DR-001 (`SPEC.md`), IronRDP feasibility findings (`docs/IRONRDP_FEASIBILITY.md`), Rust port plan (`docs/RUST_PORT.md`), reprioritized `docs/ROADMAP.md`, Rust commands in `AGENTS.md`.
- `scripts/verify.sh` runs Rust fmt/clippy/test only when a root `Cargo.toml` exists.

## [0.1.0] - 2026-10-11

First open-source release. Pre-alpha.

### Added
- Pure-Python core: virtual monitor layouts, viewport/coordinate mapping, RDP display-control PDU encoding, certificate fingerprint pinning check.
- Windows local loopback desktop workbench (`blou.desktop`, `scripts/blou_desktop.py`).
- FreeRDP experiments: monitor-layout patch and Phase 0 probe scripts.
- Apache-2.0 `LICENSE`, `pyproject.toml` (`python -m build` produces sdist and wheel), `scripts/setup.sh`, `scripts/verify.sh`, `AGENTS.md`, devcontainer, `docs/ROADMAP.md`, `SECURITY.md`, `CONTRIBUTING.md`.

### Changed
- Repository history was rewritten before publication to remove personal data (author email, local paths, a private network address). Commit SHAs differ from any earlier private copy.
- Hard-coded local paths and IPs in scripts and docs replaced with environment variables / placeholders (`FREERDP_PHASE0_DIR`, `$env:LOCALAPPDATA`, `100.64.0.10`).
- `FreeRDP` submodule now points at upstream tag 3.31.1 (`63b948ca5`); the previous pin referenced a commit that does not exist upstream.

### Known issues
- `patches/0002-android-cmake-cross-compile-fixes.patch` does not apply to the pinned FreeRDP commit.
- No Android/RDP client exists yet.

[0.1.0]: https://github.com/grloper/Blou/releases/tag/v0.1.0
