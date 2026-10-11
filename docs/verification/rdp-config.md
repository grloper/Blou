# N6 connector configuration prototype: adoption blocked

Date: 2026-10-11. Branch: `agent/rdp-config`, stacked on `agent/display-control`. Ubuntu WSL, Rust 1.94.1, Python 3.12.3. All network state-machine input is synthetic; there is no real RDP/NLA result.

Before changes, `scripts/verify.sh` exited 0 with 41 Python + 46 Rust tests, baseline 87. New builder/GCC tests were written before implementation. Against stubs:

```text
$ cargo test -p blou-rdp --locked --offline --test gcc_bytes
test monitor_data_pdu_bytes_are_exact ... FAILED
test tls_only_server_confirm_is_rejected ... FAILED
test builder_requires_nla_and_a_configured_pin ... FAILED
test monitor_block_omitted_if_server_lacks_extended_client_data ... FAILED
test connector_emits_three_monitors_in_gcc_client_blocks ... FAILED
test result: FAILED. 2 passed; 5 failed; 0 ignored; 0 measured; 0 filtered out
```

After implementation, `cargo test -p blou-rdp --locked --offline --test gcc_bytes --test spike_displaycontrol` exited 0:

```text
test result: ok. 7 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.03s
test rejects_two_primaries_and_adjusts_odd_width ... ok
test three_monitor_layout_pdu_bytes ... ok
test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
```

All six original spike cases are represented: four GCC cases and the two unchanged raw upstream display-control cases. The raw odd-width adjustment test is a control for upstream behaviour; the product adapter continues rejecting odd widths. The builder also requires a valid pin, rejects TLS-only negotiation, counts above four, odd widths and desktop bounds exceeding `u16`. Credentials are supplied to the builder; synthetic tests use placeholders.

`scripts/check-test-integrity.sh --update-baseline` printed `baseline updated: 96`. The full `scripts/verify.sh` exited 0 after implementation; real output excerpts:

```text
All checks passed!
Ran 41 tests in 3.379s
OK
test-integrity: test-case count 96 >= baseline 96
test-integrity: OK.
== rust clippy (-D warnings, locked, offline)
Finished `dev` profile [unoptimized + debuginfo] target(s) in 27.46s
== rust tests (locked, offline)
test monitor_data_pdu_bytes_are_exact ... ok
test tls_only_server_confirm_is_rejected ... ok
test connector_emits_three_monitors_in_gcc_client_blocks ... ok
test result: ok. 7 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
PASS: shell syntax + actionlint + ruff + unittest + test-integrity + offline demo + package build + rust fmt/clippy/test.
```

Total: 41 Python + 55 Rust. All old tests remain. CredSSP is marked complete solely inside the synthetic test driver to inspect the subsequent GCC frame; production has no such bypass and no live transport yet. A byte/flag check is not an authentication result.

## Blocking dependency findings

`cargo audit` exited 1:

```text
Scanning Cargo.lock for vulnerabilities (307 crate dependencies)
Crate:     rsa
Version:   0.10.0-rc.18
ID:        RUSTSEC-2023-0071
error: 1 vulnerability found!
error: 1 denied warning found!
Solution:  No fixed upgrade is available!
Crate:     atomic-polyfill
Version:   1.0.3
Warning:   unmaintained
ID:        RUSTSEC-2023-0089
```

The reported RSA graph is `ironrdp-connector -> sspi/picky/winscard -> rsa`. The unmaintained graph is `ironrdp-connector -> sspi -> winscard -> iso7816 -> heapless -> atomic-polyfill`. Authoritative advisories: [RSA](https://rustsec.org/advisories/RUSTSEC-2023-0071.html), [atomic-polyfill](https://rustsec.org/advisories/RUSTSEC-2023-0089.html). Exploit reachability in the intended username/password client profile is **UNVERIFIED**; no safety waiver is inferred from the offline tests.

`cargo deny --format json check` exited 1. Its summary reports advisories errors=2, bans errors=20, licenses errors=0, sources errors=0. No ignored advisories, ban skips, weakened lint or engine patches were added. N6 remains unchecked for adoption. A passing single verification gate proves the local checks ran, not that this separate supply-chain block is resolved. FreeRDP remains the fallback.

## Independent Android preflight

`rustup target add --toolchain 1.94.1 aarch64-linux-android x86_64-linux-android` exited 0. `rustup target list --installed --toolchain 1.94.1` printed both Android targets and the Linux host target.

`cargo check -p blou-core --target aarch64-linux-android --locked --offline` failed in ring. Output contained:

```text
error: failed to run custom build command for `ring v0.17.14`
CC_aarch64-linux-android = None
CC_aarch64_linux_android = None
TARGET_CC = None
CC = None
```

The compiler launch error was `Permission denied (os error 13)` for `aarch64-linux-android-clang`. `type -a aarch64-linux-android-clang` and `type -a x86_64-linux-android-clang` both reported `not found`. No compiler permissions were bypassed and no C/crypto step was skipped. N9 is not complete; no `.so`, APK, JNI/UniFFI, emulator, phone or frame-performance result is claimed. Provision an actual NDK Clang toolchain before another cross-build.

Existing non-blocking mypy warning remains. Windows display acceptance, actual TLS/NLA/CredSSP binding and all device checks remain UNVERIFIED. No hosted CI was used. Human checklists: `docs/HARDWARE_GATES.md`.
