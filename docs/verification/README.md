# Blou — executed evidence

Original verification date: 2026-10-01 (Windows). The suite was re-run on Linux for v0.1.0 via `scripts/verify.sh`.
Documentation and pre-existing demo data were treated as untrusted leads. Claims below come from inspected implementation and local execution.

## Rust-first follow-ups (2026-10-11)

- [FreeRDP fallback patches](freerdp-patches.md): both pinned patches apply; Android compilation remains UNVERIFIED.
- [FreeRDP probe policy](freerdp-probe-policy.md): offline runner regression tests; live launch blocked by missing native strict pin integration.

## Verified use case

Validate fabricated monitor layouts, map a phone viewport to a composite desktop and encode RDP display-control messages in Python.

## Executed checks

36 local unit tests pass (as of the v0.1.0 release). They verify geometry, display-control byte layouts, viewport navigation and synthetic certificate fingerprint behavior.

```text
python -m unittest discover -s tests -v
```

## Concrete corrections

Malformed peer certificate/fingerprint inputs now return the explicit rejection result instead of raising out of the verification callback. Added empty-byte, malformed-string and unexpected-type regressions.

## Limits and exact blockers

No Android client build, FreeRDP native integration, physical phone, real TLS session or Windows multimonitor RDP session was exercised. FreeRDP is an uninitialized submodule in this isolated clone. HardwareKeystorePolicy is a policy manifest, not evidence of Android Keystore enforcement.

## Source attribution

- [src/blou/layout.py](../../src/blou/layout.py)
- [src/blou/viewport.py](../../src/blou/viewport.py)
- [src/blou/dvc.py](../../src/blou/dvc.py)
- [src/blou/security.py](../../src/blou/security.py)
- [patches](../../patches)
- [scripts](../../scripts)

## Capability verdict

Useful protocol/geometry core; a working native Android RDP product is not yet established by this run. No stars, customers, revenue, accuracy or deployed-integration claims were inferred from repository size or marketing.

The artwork in `docs/assets/overview.svg` is a source-based workflow illustration. Screenshots, where present, are actual local runs with synthetic input as described above.

The `scripts/demo_local.py` capture is a synthetic Python-core run, not a native client session.
