# Display-control encoding evidence

Date: 2026-10-11. Branch: `agent/display-control`, stacked on `agent/rust-certificate-pinning`. Local Ubuntu WSL, Rust 1.94.1, Python 3.12.3. Offline byte tests only; no remote session.

Before changes, `scripts/verify.sh` exited 0 with 38 Python + 39 Rust tests and baseline 77.

Tests were added before changing behaviour. Commands and real red results:

```text
$ .venv/bin/python -m unittest discover -s tests -p test_dvc.py -v
AssertionError: 0 != 40
AssertionError: ValueError not raised
Ran 5 tests
FAILED (failures=3)

$ cargo test -p blou-core --locked --offline --test dvc
test result: FAILED. 2 passed; 3 failed; 0 ignored; 0 measured; 0 filtered out

$ cargo test -p blou-rdp --locked --offline --test display_control
test adapter_rejects_more_than_four_monitors ... FAILED
test one_to_four_monitor_bytes_equal_unmodified_upstream ... FAILED
test adapter_rejects_odd_width_before_upstream_can_adjust_it ... FAILED
test result: FAILED. 1 passed; 3 failed; 0 ignored; 0 measured; 0 filtered out
```

The cross-check showed the reference header's third word was 0 where upstream emits 40, and physical dimensions incorrectly copied pixel sizes. Both Rust and Python now emit MonitorLayoutSize=40, unknown physical millimetres=0, orientation=0 and explicit scale factors=100. All previous assertions remain. The core serialisation is an independent oracle; the RDP adapter converts geometry and uses the unmodified upstream encoder for transport bytes.

Core and adapter enforce product count 1..4 and MS-RDPEDISP dimensions 200..8192 (width even; height can be odd). Rejection happens before upstream constructors, which the negative control proves silently round 1921 to 1920. No rounding or input mutation is used by Blou. Golden vectors were regenerated from the corrected Python reference. Wire rules and upstream evidence: pinned `ironrdp-displaycontrol/src/pdu/mod.rs`, especially `DisplayControlMonitorLayout::encode` and `MonitorLayoutEntry`; [MS-RDPEDISP monitor layout](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-rdpedisp/22741217-12a0-4fb8-b5a0-df43905aaf06).

`scripts/check-test-integrity.sh --update-baseline` printed `baseline updated: 87`. `scripts/verify.sh` exited 0 after implementation. Real output excerpts:

```text
All checks passed!
Ran 41 tests in 3.352s
OK
test-integrity: test-case count 87 >= baseline 87
test-integrity: OK.
== rust clippy (-D warnings, locked, offline)
Finished `dev` profile [unoptimized + debuginfo] target(s) in 12.03s
== rust tests (locked, offline)
test odd_widths_are_rejected_without_rounding ... ok
test monitor_layout_size_and_unknown_physical_dimensions ... ok
test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
test one_to_four_monitor_bytes_equal_unmodified_upstream ... ok
test caps_bytes_equal_unmodified_upstream ... ok
test adapter_rejects_odd_width_before_upstream_can_adjust_it ... ok
test adapter_rejects_more_than_four_monitors ... ok
test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
PASS: shell syntax + actionlint + ruff + unittest + test-integrity + offline demo + package build + rust fmt/clippy/test.
```

Total: 41 Python + 46 Rust tests, including all prior pinning cases. No tests were removed or skipped. IronRDP is unmodified at `e4143f26306a6639a889d80c1c484ca69c365a8f`, with explicit package versions and a locked dependency graph.

## Separate supply-chain policy failure (unresolved)

`cargo audit` exited 0 with `Loaded 1296 security advisories` and `Scanning Cargo.lock for vulnerabilities (112 crate dependencies)`. Cargo-deny's JSON summary reports advisories errors=0, licenses errors=0, sources errors=0, **bans errors=7**. It rejects duplicate versions of `block-buffer`, `const-oid`, `crypto-common`, `der`, `digest`, `spki`, and `syn`. That was the result with `multiple-versions = "deny"`. Per owner decision, `multiple-versions` is now `warn` (duplicates are transitive from the pinned IronRDP rev and are not security advisories; revisit when upstream dedupes), so `cargo deny check` exits 0 with these as warnings. No advisory ignores or skip entries were added.

The dependency trees show `hmac 0.12`/`md-5 0.10` require the digest 0.10 family while `sha1 0.11` requires digest 0.11 inside the pinned IronRDP PDU crate. Its PKCS#1 and X.509 paths similarly require distinct DER/SPKI families. Procedural macros require syn 2 and 3. A simple Cargo version unification cannot cross these incompatible constraints. This policy issue needs upstream dependency alignment or a separately justified policy decision before a production supply-chain sign-off. Blou has not patched the engine or relaxed the ban.

MIT and Unicode-3.0 license allowances were added after reviewing the actual upstream/parser/macro manifests. Advisory exceptions remain empty. The single verification gate remains `scripts/verify.sh`; its green result does not claim this additional policy check is green.

UNVERIFIED: a Windows host applying these layouts dynamically, display-control capability negotiation/session wiring, real three-display acceptance and Android. Existing non-blocking mypy warning remains. No hosted CI used.
