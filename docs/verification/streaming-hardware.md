# S1 hardware proof: partial evidence, 2026-10-12

Status: **IN PROGRESS; H0 UNVERIFIED**. The owner reported "i am connected" after adding the PC over Tailscale. Host server status changed from free to busy. Neither statement proves stream quality, input mapping or pairing persistence. No restart was performed. No Android device was available through ADB; phone observations require the owner.

## Host preflight

PowerShell commands below use environment variables and redact identities. Raw installer/log artifacts are kept outside tracked files. No credentials, pairing PINs, device addresses or monitor identifiers are recorded here.

| Command / check actually performed | Result |
|---|---|
| `Get-CimInstance Win32_OperatingSystem` (edition/version/build only) | Microsoft Windows 11 Home; 10.0.26200; build 26200 |
| `Get-CimInstance Win32_VideoController` (GPU/driver only) | NVIDIA GeForce RTX 4070, 32.0.16.1714; AMD Radeon(TM) Graphics, 32.0.11034.2 |
| Sunshine `tools/dxgi-info.exe` | Two attached NVIDIA outputs, 2560 x 1440 and 1920 x 1080; per-output refresh rate UNVERIFIED |
| `& "$env:ProgramFiles/Sunshine/sunshine.exe" --version` | Exit 0; version 2026.914.233613, commit 63d35f702ee9e362e43263742981836ec0710384; non-admin invocation also reported a log rotation access error |
| `& "$env:ProgramFiles/Tailscale/tailscale.exe" version` | 1.102.3; commit 9329c3677031109ff6d0b80abee0cddc8f35ff6f |
| `Get-Service SunshineService,Tailscale` | Both `Running` |
| `adb devices` | Header only; no attached phone |
| `tailscale status --json` (identity fields omitted) | Backend Running; PC online; one Android peer subsequently online |

Sunshine was already installed. The official [Sunshine release](https://github.com/LizardByte/Sunshine/releases/tag/v2026.914.233613) MSI was downloaded and checked against the GitHub release API asset digest with `Get-FileHash -Algorithm SHA256`. SHA-256: `1d7fed8beecd5889dc7ff14cf9f42d6d38f37c3066c13c6c2a5f4e91847e0ccf`. `Get-AuthenticodeSignature` returned status 0, "Signature verified." Administrative extraction with `msiexec /a ... /qn TARGETDIR=...` exited 0. Extracted and installed `sunshine.exe` hashes both equalled `8e2c4627318432b67520a9de7cfd8ac089068a2873ccf8443756733a1af7d571`. This verifies the installed main executable against that installer, not every installed file. The executable itself was unsigned; the signature check applies to the MSI. No reinstall was needed.

The official [Moonlight Android v12.2 release](https://github.com/moonlight-stream/moonlight-android/releases/tag/v12.2) non-root APK was downloaded and its SHA-256 matched the release API: `a871f6190365386ef3ac5722a016d4da015ee1555631ec257f6e5dc3f4a45fe0`. This APK was not installed by the agent; the phone's installed version remains UNVERIFIED.

## Network and session evidence

The four existing enabled Sunshine firewall allow rules initially allowed any remote address/interface. An elevated `Set-NetFirewallRule` restricted those rules to interface `Tailscale` and remote ranges `100.64.0.0/10`, `fd7a:115c:a1e0::/48`. Read-back with `Get-NetFirewallRule`, `Get-NetFirewallAddressFilter` and `Get-NetFirewallInterfaceFilter` confirmed all four restrictions. This was an authorized host configuration change; it can make an old Moonlight LAN address stop working. Negative testing from a non-tailnet peer and tailnet ACL review remain UNVERIFIED. Do not broaden these rules for the LAN control measurement; record that control as unavailable under the current exposure policy.

`Get-NetTCPConnection` filtered by Sunshine process IDs showed listening ports 47984, 47989, 47990 and 48010. No Sunshine UDP binding was observed in the idle snapshot; active-session UDP ports remain UNVERIFIED.

`Invoke-WebRequest` to `http://<PC-tailnet-address>:47989/serverinfo` on the PC itself returned HTTP 200 and protocol status 200. Before the owner connected: `SUNSHINE_SERVER_FREE`, `currentgame=0`. After the owner reported connected:

```text
{"HTTPStatus":200,"ProtocolStatus":"200","State":"SUNSHINE_SERVER_BUSY","CurrentGame":"881448767"}
SunshineService Running
Tailscale       Running
```

The anonymous `PairStatus` field is not evidence of the phone's pairing status. This self-address HTTP check is not a phone-side reachability test.

The first peer snapshot had `Active=false`, no direct endpoint and relay region `ams`. That does not establish the stream's path. A subsequent explicit PC-to-phone probe:

```text
tailscale ping --c 3 --timeout 5s <phone-tailnet-address>
pong from [redacted peer] via [redacted direct endpoint] in 18ms
tailscale ping exit code: 0
```

Only one reply was produced because a direct path was found. This is one network round trip, not an average, stream latency or input-to-photon measurement. Record the path again during each M1 run; do not infer five minutes of direct streaming from this probe.

The in-app browser rejected access to the local Sunshine web UI under its URL security policy. No alternative browser/API bypass was attempted. Pairing and config interaction must be performed by the owner in their normal browser; passwords and PINs must not be sent to the agent.

## Phone worksheet: every measurement still incomplete

First collect phone model, Android version, installed Moonlight and Tailscale versions. Confirm Desktop is visibly updating and responds to touch. Keep the same stream resolution, target FPS, bitrate and codec for comparable runs; record the actual settings and any automatic adjustment. Use a harmless desktop window without personal information.

| ID | Next owner-assisted steps | Evidence so far / missing result |
|---|---|---|
| M1 | Enable Moonlight's performance overlay; stream Desktop for five minutes. At each minute copy every displayed label/value, particularly actual FPS, resolution, network latency, host processing, decode time and dropped frames. Note scrolling/mouse smoothness, pauses and audio. Repeat the same settings on another permitted network path if available; keep unavailable paths explicit. | One direct Tailscale ping: 18 ms. All overlay numbers, five-minute stability, actual stream path and subjective feel **UNVERIFIED**. LAN control unavailable with Tailscale-only firewall rules; do not relax them. DERP run only if naturally available. |
| M2 | With a high-frame-rate camera, film touch and phone display together plus the PC's response to a harmless click-to-color test. Record camera FPS and 20 frame counts from touch to the first changed phone frame. Convert each count to milliseconds; calculate median and p95 with the percentile method stated. | Camera availability and all 20 samples **UNVERIFIED**. A screen recording or decode time alone cannot substitute for input-to-photon latency. |
| M3 | Repeat M2 using RDP on a separately available Windows Pro host, with the same network/settings. | Current PC is Windows Home. Pro host and RDP baseline **UNVERIFIED**; no RDP workaround installed. |
| M4 | If a Bluetooth keyboard is available, send Ctrl+Alt+Shift+F1, then F2, then F3 while recording the phone. Identify the displayed physical monitor, first changed frame, resolution/aspect and any disconnection. With two attached outputs, record F3's observed behaviour without assuming a third monitor. | Keyboard availability, forwarding, mapping, switching time and size-change handling **UNVERIFIED**. |
| M5 | Once M4 works, repeat after a planned reboot, monitor sleep and safe unplug/replug. Record mapping for every trial and whether a reconnect is needed. Coordinate interruptions with the owner. | All stability trials **UNVERIFIED**. |
| M6 | Owner uses Sunshine's normal web UI to select each output identifier privately. Observe whether Save alone changes the running stream, whether reconnecting changes it, and only then whether restarting Sunshine is required. Record each stage and restore the intended output. | Actual `output_name` behaviour and restart requirement **UNVERIFIED**. Do not publish output identifiers. |
| M7 | If a second client is available, connect it while the phone streams. Record whether the first stays connected, stops, or shares the session; retain only redacted relevant log lines. | Second device availability and multi-client behaviour **UNVERIFIED**. |
| M8 | From the phone over Tailscale, test a supplied MagicDNS name / saved tailnet address. For auto-discovery, test on a different network and distinguish an already saved host from a newly discovered entry. Do not delete working pairing just to test mDNS. API token testing is optional and requires a separately supplied secret outside logs. | Owner reports connected after the tailnet address instructions; saved-name, mDNS cross-tailnet behaviour and API fields **UNVERIFIED**. PC self-address HTTP 200 is only a host preflight. |
| M9 | Confirm the phone shows this Windows Home desktop and accepts input; record continuous stream duration. | Home edition and active Sunshine host session observed. Phone rendering, input and duration **UNVERIFIED**. |
| M10 | On a harmless stream, attempt an Android screenshot and report allowed/blocked; do not send private desktop images. Review the actual Sunshine encryption settings and separately verify negotiated traffic protection. | Tailscale-only firewall read-back verified. Screenshot behaviour, negotiated Sunshine encryption and non-tailnet rejection **UNVERIFIED**. |

Do not tick S1 or advance H1/S2 from this partial evidence. H0 requires the owner to assess the completed measurements. If a missing device prevents a measurement, retain UNVERIFIED and state that constraint rather than inserting a typical number.

## Repository validation

Before these documentation changes, `scripts/verify.sh` exited 0: `Ran 52 tests in 3.722s`, `OK`, `test-case count 98 >= baseline 98`, all 46 Rust tests passed, and final `PASS: shell syntax + actionlint + ruff + unittest + test-integrity + offline demo + package build + rust fmt/clippy/test.` Existing mypy assignment error remains a non-blocking warning. Post-change verification must also pass before commit.
