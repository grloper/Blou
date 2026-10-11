# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow [SemVer](https://semver.org/); 0.x means the API may change at any time.

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
