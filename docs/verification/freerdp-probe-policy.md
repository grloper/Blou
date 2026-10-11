# FreeRDP Phase 0 runner: offline preparation, live pinning block

Date: 2026-10-11. R11 remains incomplete. No real host connection was attempted.

## Source finding at the exact pin

Pinned source: `FreeRDP/FreeRDP@63b948ca5cb94307fd5444ee6e73927a41ccdab4`.
Inspected `libfreerdp/crypto/tls.c` lines 1798–1891 and
`client/common/cmdline.c` lines 3500–3550. Reproduce offline with:

```bash
sed -n '1798,1895p' FreeRDP/libfreerdp/crypto/tls.c
sed -n '3500,3555p' FreeRDP/client/common/cmdline.c
```

The parser stores `fingerprint:` entries in `CertificateAcceptedFingerprints`
and `deny` sets `AutoDenyCertificate`. TLS accepts a matching allowlisted
fingerprint before external management or normal chain validation. A mismatch
does not reject there: it falls through. The normal-validation branch accepts
when both `certificate_status` and `hostname_match` are true; AutoDeny handling
occurs on failed-validation paths later. Thus the CLI allowlist is insufficient
for Blou's mandatory pin semantics, even with `/cert:deny`.
This conclusion follows the actual control flow, not a native handshake test.
Native behaviour remains UNVERIFIED.

Primary source: [TLS certificate control flow](https://github.com/FreeRDP/FreeRDP/blob/63b948ca5cb94307fd5444ee6e73927a41ccdab4/libfreerdp/crypto/tls.c#L1798),
[certificate CLI parser](https://github.com/FreeRDP/FreeRDP/blob/63b948ca5cb94307fd5444ee6e73927a41ccdab4/client/common/cmdline.c#L3500).

The available upstream integration is `ExternalCertificateManagement` plus
`VerifyX509Certificate`. The built-in fingerprint allowlist must be empty, as
its early return would bypass that callback. Future integration must use upstream
certificate parsing and the existing Rust ring/subtle pin policy; no custom
crypto or modified protocol code. Require fixture tests with self-signed and
actually trusted-root leaves, missing/wrong pins, matching pins, TLS/NLA only,
and no user override before enabling host connections. Treat pin changes as a
new engine context so cached certificate acceptance cannot retain an old policy.

## Runner change and test evidence

The old runner defaulted the host/account, enabled clipboard, and passed
certificate-ignore. New code requires HOST, USERNAME, CERT_SHA256 (exactly
64 hex digits) and an executable FREERDP_BIN. It accepts `--help`/`--prepare`,
prints no endpoint/account/pin, takes no password argument, and never invokes
the client. Live execution exits 3 with the native pin integration blocker.
Preparation does not claim binary provenance, a build, or trust enforcement.

Six new tests use a fake executable that writes a marker if launched; the marker
must remain absent for help, missing configuration, invalid pins, preparation,
live invocation and unknown options. No network or real credentials are used.
All existing tests remain unchanged, including the placeholder-host assertion.

Before implementation:
`.venv/bin/python -m unittest tests.test_phase0_runner -v` exited 1:

```text
Ran 6 tests in 0.120s
FAILED (failures=6)
```

Failures proved the old runner launched the fake client even for help/malformed
configuration. After implementation the same command exited 0:

```text
Ran 6 tests in 0.067s
OK
```

The base gate exited 0 with 46 Python + 55 Rust tests, baseline 101. The updated
hardware checklist removes the CLI host-connect recipes and names the exact
callback prerequisite; topology queries/checks stay available for after that
prerequisite is proven. Windows Phase 0, native pinning/TLS/NLA and all Android
build/device results remain UNVERIFIED. IronRDP dependency policy remains failed,
with no exceptions or test removals.

After implementation, `scripts/verify.sh` exited 0 with `Ran 52 tests`, `OK`,
all 55 Rust tests passed, and `test-integrity: test-case count 107 >= baseline 107`.
The final gate output was:

```text
PASS: shell syntax + actionlint + ruff + unittest + test-integrity + offline demo + package build + rust fmt/clippy/test.
NOT CHECKED: Windows/Android builds, FreeRDP native submodule, real remote sessions, Windows screen capture.
```

The existing mypy warning at `src/blou/security.py:66` remains non-blocking under
the unchanged gate policy. `bash scripts/run_phase0_probe.sh --help` exited 0;
`git -C FreeRDP status --porcelain --untracked-files=no` produced no output.
