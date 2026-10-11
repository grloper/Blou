# Rust certificate pinning evidence

Date: 2026-10-11. Branch: `agent/rust-certificate-pinning`, stacked on `agent/rust-test-parity`. Local Ubuntu WSL, Rust 1.94.1, Python 3.12.3. No remote host, phone, network handshake or system trust-store mutation.

Before changes, `scripts/verify.sh` exited 0 with 38 Python and 30 Rust tests, baseline 68.

New fixture tests were written before implementation. A temporary verifier stub ignored pins, allowing the rejection controls to fail. `cargo test -p blou-rdp --locked --offline --test tls_pin --no-fail-fast` failed with real output:

```text
test malformed_certificate_with_matching_hash_is_rejected_without_panic ... FAILED
test missing_pin_is_rejected ... FAILED
test every_single_bit_pin_mismatch_is_rejected ... FAILED
test any_changed_certificate_is_rejected ... FAILED
test trusted_root_never_bypasses_pin_mismatch ... FAILED
test in_memory_tls_accepts_matching_fixtures_and_rejects_mismatches ... FAILED
test result: FAILED. 2 passed; 6 failed; 0 ignored; 0 measured; 0 filtered out
```

The stub was replaced before committing. The custom verifier first compares the leaf DER SHA-256 pin, then uses Rustls X.509 parsing. Signature verification is delegated to rustls/ring. Matching pins are the explicit trust authority; CA/name validation is not a fallback acceptance path. Pin configuration is immutable for the verifier; absent pins reject. The client config disables resumption and key logging.

Fixtures were generated with OpenSSL 3.0.13. `openssl verify` reported the trusted fixture `OK`. The normal `WebPkiServerVerifier` control also validates the leaf against the isolated root before testing a pin mismatch, proving the trusted-root case is real. Public test-only keys are documented in `crates/blou-rdp/tests/fixtures/README.md`; no production secrets are included, and the test CA is never installed in the OS.

The initial dependency scan correctly failed for Rustls 0.23.41:

```text
error[vulnerability]: TLS 1.3 handshake messages incorrectly accepted across encryption level boundaries
ID: RUSTSEC-2026-0285
Solution: Upgrade to >=0.23.45
advisories FAILED, bans FAILED, licenses ok, sources ok
```

Rustls was upgraded and pinned to 0.23.45; the git dependency also specifies its package version as required by cargo-deny's no-wildcard policy. `cargo deny check` then exited 0 with `advisories ok, bans ok, licenses ok, sources ok`; `cargo audit` exited 0 with `Loaded 1296 security advisories` and `Scanning Cargo.lock for vulnerabilities (65 crate dependencies)`. No advisory exceptions were added. Advisory: https://rustsec.org/advisories/RUSTSEC-2026-0285.html.

`scripts/check-test-integrity.sh --update-baseline` printed `baseline updated: 77`. `scripts/verify.sh` exited 0 after implementation. Real output excerpts:

```text
All checks passed!
Ran 38 tests in 3.333s
OK
test-integrity: test-case count 77 >= baseline 77
test-integrity: OK.
== rust clippy (-D warnings, locked, offline)
Finished `dev` profile [unoptimized + debuginfo] target(s) in 4.16s
== rust tests (locked, offline)
test trusted_root_never_bypasses_pin_mismatch ... ok
test tls12_and_tls13_handshakes_enforce_the_same_pin ... ok
test in_memory_tls_accepts_matching_fixtures_and_rejects_mismatches ... ok
test upstream_strict_callback_works_only_as_a_failure_recovery_hook ... ok
test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.10s
PASS: shell syntax + actionlint + ruff + unittest + test-integrity + offline demo + package build + rust fmt/clippy/test.
```

All preceding 30 Rust and 38 Python tests also passed. IronRDP is unmodified at `e4143f26306a6639a889d80c1c484ca69c365a8f`; the self-signed control calls its explicit Strict callback path. Pinned source `rustls_verifier.rs` returns success before invoking the callback when normal validation succeeds, confirming the custom verifier is necessary for strict pinning.

UNVERIFIED: the future RDP transport using this config, NLA/CredSSP binding, Windows multi-monitor sessions, Android/native crypto build and on-device enforcement. Existing non-blocking mypy warning remains. No hosted CI used.
