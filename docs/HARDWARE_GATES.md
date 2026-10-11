# Windows and phone gate checklists — UNVERIFIED

No host or phone gate was run in this task. The Rust byte tests are offline evidence only. Keep all `[human]` boxes unchecked until the required evidence exists. Do not deploy the public fixture keys or install the test CA on a host/device.

## Prerequisites and safe evidence

1. A Windows 11 Pro test host with RDP and NLA enabled, accessible over the owner's tailnet; port 3389 restricted to that interface/ACL. Use an account permitted to log on. Keep actual addresses, usernames, credentials, certificate hashes and local paths outside the repository.
2. A client with one physical display for Phase 0, and a physical Android phone for the owner's Android gate. Record client commit, Windows build, phone OS/ABI and pass/fail; redact personal identifiers. Confirm the queried topology belongs to the tested RDP session, not the console or another client.
3. Obtain the host's bound RDP certificate independently on the host. With the confirmed certificate's thumbprint, PowerShell can compute its SHA-256 from public DER (no private key access):

```powershell
$certificate = Get-Item 'Cert:\LocalMachine\Remote Desktop\CERT_THUMBPRINT'
$hash = [System.Security.Cryptography.SHA256]::Create()
try {
    [BitConverter]::ToString($hash.ComputeHash($certificate.RawData)).Replace('-', '').ToLowerInvariant()
} finally {
    $hash.Dispose()
}
```

Select the certificate actually bound to RDP; do not guess from certificate-store order. Provision this fingerprint out of band. No TOFU, certificate-ignore mode or acceptance dialog is allowed. A changed/missing pin must abort.

## N7 / Phase 0: FreeRDP baseline creates three displays

1. Run `scripts/setup.sh` and `scripts/verify.sh`; require exit 0. Initialise the optional FreeRDP submodule and confirm its source matches the gitlink:

```bash
git submodule update --init FreeRDP
git ls-tree HEAD FreeRDP
git -C FreeRDP rev-parse HEAD
git -C FreeRDP apply --check ../patches/0001-xfreerdp-fabricated-multimon-layout.patch
```

The required upstream commit is `63b948ca5cb94307fd5444ee6e73927a41ccdab4`. If the check passes, apply the patch, inspect `git -C FreeRDP diff` in full, build the X11 client for that source and record exact build commands/version. This checklist does not claim a native build occurred here.

2. **Current security block: do not start a host session with the CLI fingerprint allowlist.** At the exact pinned revision, `libfreerdp/crypto/tls.c` accepts a matching allowlisted fingerprint early, then falls through to normal CA/name validation on a mismatch. `/cert:deny` controls failed-validation handling; it does not reject a CA/name-valid mismatching leaf. This is source evidence, not a native handshake test. See `verification/freerdp-probe-policy.md`.
3. Run `bash scripts/run_phase0_probe.sh --help` for required inputs. Supply `HOST`, `USERNAME`, `CERT_SHA256` and `FREERDP_BIN` outside Git, then use `--prepare` for offline configuration validation. It prints no identity/pin and never launches the executable. Live invocation exits 3 until strict native pinning is integrated. There is currently no approved host-connect command.
4. Before enabling a live probe, integrate `ExternalCertificateManagement` and `VerifyX509Certificate` with the immutable Rust pin policy, leaving the built-in fingerprint allowlist empty so it cannot bypass the callback. Upstream parses certificates; Rust ring/subtle hashes and compares. Prove missing/wrong pins reject for both self-signed and actually trusted-root fixtures, matching pins succeed, and no interactive override or TLS-only fallback occurs. Then publish the exact reviewed command and run the wrong-pin negative control before real credentials. Credentials must use a protected flow, never command-line arguments/logs.

5. **Inside that exact RDP session**, open PowerShell and run:

```powershell
Add-Type -AssemblyName System.Windows.Forms
$screens = [System.Windows.Forms.Screen]::AllScreens
$screens.Count
$screens | ForEach-Object {
    [pscustomobject]@{
        X = $_.Bounds.X; Y = $_.Bounds.Y
        Width = $_.Bounds.Width; Height = $_.Bounds.Height
        Primary = $_.Primary
    }
} | Sort-Object X,Y | Format-Table
```

PASS requires exactly three rows: `(0,0,1920,1080,True)`, `(1920,0,1920,1080,False)`, `(3840,0,1920,1080,False)`. Also inspect Settings > System > Display and capture a redacted screenshot of the three displays. A 5760-wide framebuffer alone is insufficient evidence of three monitors.
6. Disconnect/reconnect and repeat. For the one-monitor control, **unset** `BLOU_FAKE_MONITORS` (`env -u BLOU_FAKE_MONITORS ...`); its presence triggers the patch regardless of value. The existing patch hard-codes three monitors, so `BLOU_FAKE_MONITORS=4` does not create a four-monitor control. Four-monitor live control remains UNVERIFIED until a reviewed configurable probe exists.
7. Save redacted evidence under `docs/verification/`: source/patch diff, build command/version, one physical client display, Windows build, topology output, screenshot, reconnect result and negative-control verdict. No passwords, real endpoint identifiers or raw framebuffer logs. Report the gate result before claiming completion.

## N8: IronRDP host/NLA gate

**Current block:** the N6 dependency graph fails its security scan and no approved live `blou-rdp` connection executable/rendering client exists. There is no runnable connect command to supply; do not substitute the byte-test command or synthetic `mark_credssp_as_done` step. Keep this gate UNVERIFIED.

Once that block is resolved and a live transport exists:

1. Use the same host, independently provisioned pin and three-monitor geometry. The transport must consume both configs from `build_connection_config`, use the custom pinned Rustls config, perform real CredSSP through the upstream helper and bind the actual TLS server public key. No TLS-only fallback, TOFU, credential/frame logging or resumption bypass.
2. Run missing-pin and single-bit wrong-pin controls first, before real authentication; require rejection. Re-run matching-pin positive control, including the approved trusted-root case. Record exact executable/commit/command without secrets.
3. Establish NLA, then run the same PowerShell topology query **inside that same IronRDP session** and capture redacted Display Settings evidence. Another RDP client/console session does not validate this session. If the probe has no interactive viewport/input, the display-count check is blocked rather than inferred from emitted GCC bytes.
4. Require three displays with the bounds above. Repeat reconnect and 1/4-monitor controls through the reviewed configurable transport. Record failure reasons and retain FreeRDP when the engine gate fails. Never mark this done from an offline test.

## Phase 1 / G1: Android NLA and pinning

1. Finish N9's actual NDK/crypto build, bridge and application build. Record Rust, NDK, SDK and ABI versions plus APK hash/commit. The current arm64 core check failed in ring's Android compiler setup; no APK or `.so` success is available.
2. Install the reviewed APK on the owner's physical phone using its supported deployment flow. Confirm tailnet connectivity to the host and NLA enabled. Provision the host pin independently and credentials through the intended protected flow. Do not invent stock-app pin settings; if the stock baseline cannot provision trust without an override, report that limitation.
3. Missing/wrong pin must prevent connection without an acceptance dialog. Matching pin must complete **real** TLS and NLA using the required engine/config. Confirm credentials and pixels stay out of logs; inspect connection state and interactive desktop behaviour. Record a redacted result.
4. For IronRDP adoption, verify the fabricated topology in the same session and the phone's viewport/input mapping against all three displays. Frame-path/Keystore enforcement need their separate tests and device evidence; policy manifests and host unit tests are insufficient.
5. Preserve the FreeRDP baseline/fallback until G0 (both engines), G1 and G2 are all evidenced. A build, emulator-only observation or offline TLS fixture is not the owner's physical-phone gate.
