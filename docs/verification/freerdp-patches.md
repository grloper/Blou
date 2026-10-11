# FreeRDP fallback patch repair (R10)

Date: 2026-10-11. Owner prioritized the FreeRDP fallback. Rust core and thin Kotlin
direction stay fixed.

Pinned source: `FreeRDP/FreeRDP@63b948ca5cb94307fd5444ee6e73927a41ccdab4`
(3.31.1). `scripts/setup.sh --with-freerdp` exited 0:

```text
Submodule path 'FreeRDP': checked out '63b948ca5cb94307fd5444ee6e73927a41ccdab4'
setup: done. Activate with: source .venv/bin/activate   Gate: scripts/verify.sh
```

Before changes, `scripts/verify.sh` exited 0: 41 Python tests, 55 Rust tests,
test-integrity 96 >= 96. Mypy retains its existing non-blocking assignment error
in `src/blou/security.py:66`; this task does not change the gate.

`git -C FreeRDP apply --check ../patches/0002-android-cmake-cross-compile-fixes.patch`
exited 1 before repair:

```text
error: patch failed: client/Android/cmake/ExternalOpenSSL.cmake:26
error: client/Android/cmake/ExternalOpenSSL.cmake: patch does not apply
```

Five new cases were written first. `.venv/bin/python -m unittest
tests.test_freerdp_patches -v` exited 1, `Ran 5 tests`, `FAILED (failures=5)`.
After implementation the same command exited 0, `Ran 5 tests`, `OK`.
These use exact upstream fixtures and temporary directories; no network,
optional submodule, or crypto/compiler build is needed by the tests.

`bash scripts/check_patches.sh` exited 0:

```text
check-patches: 0001-xfreerdp-fabricated-multimon-layout.patch applies
check-patches: 0002-android-cmake-cross-compile-fixes.patch applies
check-patches: PASS against 63b948ca5cb94307fd5444ee6e73927a41ccdab4; checkout unchanged
```

The checker rejects missing/wrong-revision/dirty tracked source. It exports only
the files touched by the two patches, applies them in order in a temporary tree,
and removes that tree on exit. It never applies changes to the submodule.

## Actual source diff and limits

The complete source diff is `patches/0002-android-cmake-cross-compile-fixes.patch`;
it touches only `client/Android/cmake/ExternalDeps.cmake` and
`ExternalOpenSSL.cmake`. There are no C protocol or OpenSSL source changes.
The original patch referenced two absent helpers and mismatched upstream lines.
The repair preserves the existing cJSON policy minimum and forwards
`CMAKE_POLICY_DEFAULT_CMP0057=NEW` for older third-party policy scopes.
[CMake documents the policy-default cache mechanism](https://cmake.org/cmake/help/latest/manual/cmake-policies.7.html).

The OpenSSL command retains explicit architecture/API configuration, normalizes
and quotes all three NDK environment aliases in configure/build/install, and
uses colon PATH on Unix and LIST_SEPARATOR-restored semicolons on Windows.
It lets upstream Configure choose its compiler from NDK PATH rather than forcing
CC. This follows the [pinned OpenSSL Android guidance](https://github.com/openssl/openssl/blob/openssl-4.0.1/NOTES-ANDROID.md)
for PATH, ANDROID_NDK_ROOT and explicit target selection. That upstream document
also says only Linux was tested; Windows shell/build support remains UNVERIFIED.

UNVERIFIED: Android NDK build/link, Windows command execution, release signature,
FreeRDP native pin enforcement, NLA, real Windows display creation, phone runs.
At this R10 checkpoint the probe still used its certificate-ignore option. The subsequent
[R11 preparation change](freerdp-probe-policy.md) removes that launch; native
strict pin integration is still required before the human checklist can connect.
These changes touch no Rust code or dependencies.

After repair, `scripts/verify.sh` exited 0: `Ran 46 tests`, `OK`, all Rust
tests passed, `test-integrity: test-case count 92 >= baseline 92`, and:

```text
PASS: shell syntax + actionlint + ruff + unittest + test-integrity + offline demo + package build + rust fmt/clippy/test.
NOT CHECKED: Windows/Android builds, FreeRDP native submodule, real remote sessions, Windows screen capture.
```

Fixture SHA-256 comparison against the initialized pinned submodule matched:
ExternalDeps `d19e75ee01e55b48cd997810d271d067546bc3350e7e75cbd022cb8b1cb1ae86`,
ExternalOpenSSL `e5e6edeca454af86e78763218ac2281c4f4745254dff0c4e208a34e58ee18437`.
