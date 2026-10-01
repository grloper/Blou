# Blou

**New Windows milestone:** a consent-gated multi-monitor local desktop workbench
now includes real JPEG capture/transport/decode and an executable build script.
See [run instructions and verified limits](docs/WINDOWS-WORKBENCH.md).
This loopback prototype is separate from the RDP geometry core below.

![Blou source-based implementation overview](docs/assets/overview.svg)

Validate fabricated monitor layouts, map a phone viewport to a composite desktop and encode RDP display-control messages in Python.

**Status:** Useful protocol/geometry core; a working native Android RDP product is not yet established by this run.

## What was actually run

30 local unit tests passed. They verify geometry, display-control byte layouts, viewport navigation and synthetic certificate fingerprint behavior.

## Run locally

Commands below are local evaluation paths. Use an isolated environment. `RADAR_OFFLINE=1` is an environment-variable assignment; on PowerShell use `$env:RADAR_OFFLINE='1'` first.

```text
python -m unittest discover -s tests -v
```

## Scope you can rely on

No Android client build, FreeRDP native integration, physical phone, real TLS session or Windows multimonitor RDP session was exercised. FreeRDP is an uninitialized submodule in this isolated clone. HardwareKeystorePolicy is a policy manifest, not evidence of Android Keystore enforcement.

## Evidence and changes

Malformed peer certificate/fingerprint inputs now return the explicit rejection result instead of raising out of the verification callback. Added empty-byte, malformed-string and unexpected-type regressions.

Read the [executed evidence and source map](docs/verification/README.md) for the precise distinction between tested behavior, synthetic model/data boundaries and unverified integrations. Existing design documents describe intended or historical behavior; their claims require fresh verification against code.

Run `python scripts/demo_local.py` for a synthetic geometry/fingerprint demonstration with no RDP or TLS connection. The emitted [local-core-demo.json](docs/verification/local-core-demo.json) is fixture evidence.
