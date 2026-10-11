# Moonlight + Sunshine + Tailscale stack: research

Status: research for DR-002 (`SPEC.md`, proposed). Written 2026-10-12 from the sources cited inline. Nothing here has been run on hardware. Anything not backed by a cited source or a source-code reading is marked **UNVERIFIED**. Re-check versions before relying on them; they move quickly.

## 1. Why consider this

- Windows Home editions cannot host incoming Remote Desktop sessions; only Pro, Enterprise, Education and Server can. Source: <https://learn.microsoft.com/en-us/windows-server/remote/remote-desktop-services/remotepc/remote-desktop-allow-access>.
- The owner's claim that GPU-capture streaming has lower latency than RDP is **UNVERIFIED**. This repository has no measurement. See section 9 (TO-MEASURE).

## 2. Components, licenses, versions

Read via the GitHub API and repository checkouts on 2026-10-12.

| Component | Role | License (GitHub SPDX + LICENSE file) | Latest release / state seen |
|---|---|---|---|
| Sunshine, <https://github.com/LizardByte/Sunshine> | Host (Windows/Linux/macOS), captures a display, encodes, serves the Moonlight protocol, web UI + REST API | GPL-3.0 (`LICENSE`; SPDX `GPL-3.0`) | Latest non-prerelease `v2026.914.233613` (2026-09-15). Newer pre-releases `v2026.1011.160319`, `v2026.1011.20959` (2026-10-11). Source read at master `d1fc311` (2026-10-11). |
| moonlight-android, <https://github.com/moonlight-stream/moonlight-android> | Android client (Java + JNI) | GPL-3.0 | `v12.2` (2026-09-12). Source read at `b48494c` (2026-09-12). `minSdk 21`, `targetSdk 36`, `versionName 12.2`, NDK `29.0.14206865` (`app/build.gradle`). |
| moonlight-common-c, <https://github.com/moonlight-stream/moonlight-common-c> | Shared C protocol core used by all Moonlight clients | GPL-3.0 (`LICENSE.txt`) | No GitHub releases or tags; consumed as a git submodule pinned by moonlight-android (`app/src/main/jni/moonlight-core/moonlight-common-c`, pinned `874ac95`). Submodules `enet` (<https://github.com/cgutman/enet>, MIT) and `nanors` (<https://github.com/sleepybishop/nanors>, MIT per GitHub API). |
| Tailscale (client), <https://github.com/tailscale/tailscale> | Mesh VPN | BSD-3-Clause | `v1.104.1` (2026-10-07) |
| Tailscale Android, <https://github.com/tailscale/tailscale-android> | Android app / VpnService | BSD-3-Clause | `1.104.1-...` (2026-10-08) |

Moonlight describes itself as a client for "Nvidia's GameStream protocol" (moonlight-common-c README: <https://github.com/moonlight-stream/moonlight-common-c>). Sunshine's GitHub description reads "Self-hosted game stream host for Moonlight". Sunshine's own docs: <https://docs.lizardbyte.dev/projects/sunshine/latest/>.

## 3. How Sunshine selects the captured monitor

Sources: `docs/configuration.md`, `docs/getting_started.md`, `src/video.cpp`, `src/input.cpp`, `src/display_device.cpp`, `src/platform/windows/display_base.cpp` at master `d1fc311`.

1. **`output_name` (global host config).** "Select the display number you want to stream." Default: Sunshine selects the default display. Value meaning per OS (from the doc):
   - Windows: the `device_id` string such as `{daeac860-f4db-5208-b1f5-cf59444fb768}`, taken from the "Currently available display devices" JSON that Sunshine logs at startup (fields: `device_id`, `display_name` like `\\.\DISPLAY1`, `friendly_name`, `info.origin_point`, `info.primary`, `info.resolution`).
   - Linux/FreeBSD: connector name (e.g. `DP-0`, recommended) or numeric id for some capture backends.
   - macOS: numeric id.
   `adapter_name` separately selects the GPU (Windows example: a GPU description string).
2. `display_device::map_output_name()` maps the configured value to a platform display name; the Windows capture loop then enumerates DXGI adapters and outputs and skips outputs whose `DeviceName` differs from the selected name (`display_base.cpp`). Capture is per output; each output's desktop coordinates give the capture offset and size.
3. **In-stream hotkey (verified in docs and source).** Docs: "`Ctrl+Alt+Shift+F1/F12`: Switch to different monitor for Streaming" (`docs/getting_started.md`, Shortcuts; the doc text says F1/F12, the code range is F1..F13). Source: `apply_shortcut()` in `src/input.cpp` maps VK_F1..VK_F13 to `mail::switch_display` with value `keyCode - VK_F1`; `src/video.cpp` consumes that event and sets `display_p = clamp(value, 0, display_names.size()-1)`, releasing and recreating the capture on the new display. Index = position in `platf::display_names()` for the capture backend, **not** the `output_name` value; the order is **UNVERIFIED** on the owner's hardware and may change on hotplug (`refresh_displays` tries to keep the same display).
4. **Per-session client choice: not in the protocol surface we read.** `make_launch_session()` (`src/nvhttp.cpp`) parses `rikey`, `appid`, width/height/fps, `sops`, surround, `gcmap`, `hdrMode` and similar; no monitor argument. So monitor selection is host config or the hotkey. Whether other fields could carry it: UNVERIFIED (not seen).
5. Display-device options (`dd_configuration_option`, `dd_resolution_option`, ...; Windows only) can change the host's display configuration at stream start, for example "ensure only display"; defaults to disabled (`docs/configuration.md`). On Windows, enabling them can alter the owner's monitor setup. Revert behaviour is configurable (`dd_config_revert_on_disconnect`).

**Consequence for Blou's "swipe between PC monitors":** the only verified in-session mechanism is the hotkey, which a client can synthesize as a keyboard packet. moonlight-android already forwards unrecognised Ctrl+Alt+Shift combos to the host (`Game.java` `handleSpecialKeys`: only Z, Q, C are consumed client-side; "This isn't a special combo that we consume on the client side" for the rest) and exposes `conn.sendKeyboardInput(keyMap, KEY_DOWN/UP, modifier, flags)` (`NvConnection.java:500`; `KeyboardTranslator.VK_F1 = 112`). Whether the stream seamlessly changes resolution/aspect when the target monitor differs in size is UNVERIFIED: the client must handle a changed frame size; moonlight-common-c's behaviour there was not checked.

## 4. Multiple simultaneous streams / per-session monitors

Verified from source (`src/nvhttp.cpp`, `src/rtsp.cpp`, `src/video.cpp`):
- `/launch` returns 400 "An app is already running on this host" if `proc::proc.running() > 0` (nvhttp.cpp `launch()`). `/resume` requires a running app. `/serverinfo` reports `SUNSHINE_SERVER_BUSY` when an app runs.
- The RTSP server keeps a *set* of sessions (`_session_slots`) and logs "[active sessions: N]", and display preparation is only done "if there are no active sessions" (`session_count() == 0`), so more than one session object is possible in code (resume path). Whether a second *client* can resume and receive an independent stream is **UNVERIFIED**; the capture machinery in `video.cpp` uses one shared display selection and `switch_display` is a global mail event, so multiple sessions would share the same monitor choice (inference from code, not tested).
- Conclusion: **one monitor at a time per host, switched by hotkey or config.** True simultaneous per-monitor streams (e.g. to prefetch neighbours for smooth swiping) are not supported by anything we verified. A "swipe" will therefore have a capture-switch latency, to be measured (section 9).
- A Windows virtual display (IDD) can create extra monitors, which Sunshine's docs reference ("IDD HDR", "SunshineHDR" in the output example; `docs/configuration.md` output_name). Treating a virtual display driver as an option is **UNVERIFIED** and outside the stock product; do not assume it ships with Sunshine.

## 5. Pairing flow

Sources: `docs/getting_started.md` ("Configuration", steps 5-6), `PairingManager.java` in moonlight-android, `src/nvhttp.cpp`, `src/confighttp.cpp`.

1. Client has host address. Default ports: HTTP 47989 (`NvHTTP.DEFAULT_HTTP_PORT`), HTTPS 47984 (`DEFAULT_HTTPS_PORT`); Sunshine docs: config `port` default 47989 and other ports offset from it; web UI `https://localhost:47990` (docs/configuration.md `port`, getting_started.md).
2. Client generates a 4-digit PIN (shown to user) and a 16-byte salt, derives an AES key from `hash(salt || pin)` (SHA-256 for server generation >= 7, SHA-1 earlier; `PairingManager.pair`).
3. `GET /pair?phrase=getservercert&salt=<hex>&clientcert=<hex>`: the request blocks (no read timeout) until the user enters the PIN on the host. Then `clientchallenge`, `serverchallengeresp`, `clientpairingsecret`, followed by a pairing-challenge over HTTPS (steps seen in `PairingManager.java`; full byte-level protocol not independently re-derived here).
4. The user enters the PIN in Sunshine's web UI ("PIN" page: PIN + device name; getting_started.md step 6) or via the REST API.
5. Result: mutual certificate exchange; client stores the server cert (pin-style trust), Sunshine stores the client cert. Sunshine limits pending pairings ("Too many pending pairing sessions", 503; duplicate uniqueid 409; nvhttp.cpp).

**Automation option:** `POST /api/pin` with JSON `{"pairing_id":"...","pin":"1234","name":"My PC"}` and `GET /api/pin` listing pending pairings (confighttp.cpp doc comments) require the Sunshine admin credentials (Basic auth) and CSRF handling for browsers (non-browser clients exempt, `docs/api.md`). This could enable a "pair from the PC browser" flow, but Blou must never ask for or store the Sunshine admin password on the phone without a separate security review (UNVERIFIED design).

## 6. API and web UI

`docs/api.md` (master `d1fc311`): REST API authenticated with admin username/password (Basic); CSRF tokens for browser state-changing calls. Documented endpoints: `/api/csrf-token`, `/api/apps` (GET/POST), `/api/apps/close`, `/api/apps/{index}` (DELETE), `/api/browse`, `/api/clients/list`, `/api/clients/unpair`, `/api/clients/unpair-all`, `/api/clients/update`, `/api/config` (GET/POST), `/api/configLocale`, `/api/covers/*`, `/api/logs`, `/api/password`, `/api/pin`, `/api/reset-display-device-persistence`, `/api/reset-portal-token`, `/api/restart`, `/api/virtual-input/status`. The web UI is served on HTTPS 47990 with a self-signed certificate (`docs/getting_started.md`). Protocol endpoints for clients (not the admin API): `/serverinfo`, `/pair`, `/applist`, `/launch`, `/resume`, `/cancel` (`src/nvhttp.cpp`). A REST way to change `output_name` is `POST /api/config` plus restart (endpoints exist; that changing `output_name` takes effect without restart is **UNVERIFIED**; it is a poor fit for a swipe anyway).

## 7. moonlight-android structure and where Blou features would go

Layout (`app/src/main/java/com/limelight`): `PcView` (host list, 788 lines), `Game` (stream activity, 2700 lines), `computers/` (`ComputerManagerService`, `ComputerDatabaseManager`, `IdentityManager`), `discovery/DiscoveryService`, `nvstream/` (`NvConnection`, `http/NvHTTP`, `http/PairingManager`, `mdns/`, `jni/`, `wol/`), `binding/` (`input/`, `video/`, `audio/`, `crypto/`), `preferences/` (including `AddComputerManually`), `ui/StreamView`. Native side: `app/src/main/jni/moonlight-core` with the moonlight-common-c submodule, OpenSSL and Opus built via `ndkBuild`.

Findings from reading the code:
- Discovery today is local mDNS: service type `_nvstream._tcp` via `NsdManagerDiscoveryAgent` (Android 14+) or jmDNS before (`DiscoveryService.java`, `nvstream/mdns/`). Manual add by IP/hostname exists (`PcView` -> `AddComputerManually`). Tailscale does not use this path; whether multicast mDNS crosses a tailnet is **UNVERIFIED** (not tested), so assume it does not and add an explicit source.
- `FLAG_SECURE`: no occurrence in the app source (grep over `com/limelight` found none). Blou's security requirement (SPEC 5c) would be new work in `Game.java` and `PcView`.
- Saved hosts live in `ComputerDatabaseManager` (SQLite); no biometric lock was found. Blou's SPEC 5b (Keystore + biometric) would be new work.
- Input: `Game.java` translates Android key events through `KeyboardTranslator` and calls `conn.sendKeyboardInput`; Ctrl+Alt+Shift+Z/Q/C are intercepted locally, others forwarded. A monitor swipe handler would live in `Game`/`StreamView` gesture code and call a small helper that sends modifiers down, `VK_F{n}`, then releases (swipe index -> `F(n+1)`), mirroring `keyboardEvent()` (`Game.java` ~2631).
- Possible integration points for Tailscale discovery: a new `computers`-level source feeding `ComputerManagerService` the same way manual addresses do; UI entry in `PcView`.

## 8. Tailscale integration options on Android

Verified from documentation and source:

1. **Tailscale API, list devices.** `GET https://api.tailscale.com/api/v2/tailnet/{tailnet}/devices` (`-` = default tailnet); auth by API access token (Basic with token as username, or Bearer). Console-created tokens expire in 1 to 90 days; OAuth client access tokens expire after 1 hour and come from `https://api.tailscale.com/api/v2/oauth/token`; creating a token requires an Owner/Admin/IT admin/Network admin role. Sources: <https://tailscale.com/docs/reference/tailscale-api>, <https://tailscale.com/docs/features/oauth-clients>, <https://github.com/tailscale/tailscale/blob/f348f178118241ba5fe1c622f3ae1554171f383c/api.md>. This works from any network but puts a tailnet-wide credential on the phone (the OAuth `devices:core:read` scope, per a third-party mirror of the API docs <https://context7.com/websites/api_tailscale_api_v2/llms.txt>, narrows it but the exact scope name should be checked on the official page: **UNVERIFIED**). Needs secure storage (Keystore) and user-pasted secrets; the tokens are secrets and must never be logged.
2. **Local Tailscale app status: no supported cross-app API found.** The Tailscale Android app's LocalAPI (`/localapi/v0/status`, etc.) is called in-process by the app itself (`app.callLocalAPI`, <https://context7.com/tailscale/tailscale-android/llms.txt>); a Tailscale maintainer, answering a feature request for an Intent to fetch status/IP, said exposing status to third-party apps would raise privacy concerns and suggested the Tailscale API or a server in the tailnet: <https://github.com/tailscale/tailscale/issues/11683>. Documented broadcast intents exist only to connect/disconnect: `com.tailscale.ipn.CONNECT_VPN` / `DISCONNECT_VPN` to `com.tailscale.ipn.IPNReceiver` (<https://github.com/tailscale/tailscale-android/pull/84>, <https://github.com/tailscale/tailscale-android/pull/87>). Whether these are enabled by default on the current release: UNVERIFIED.
3. **Probe-based discovery over the tailnet (no credentials).** Since the phone is on the tailnet (VPN routing all `100.64.0.0/10`), the client could probe user-listed MagicDNS names or `100.x` addresses on Sunshine's port 47989 `GET /serverinfo` (unauthenticated HTTP in the Moonlight protocol, see `NvHTTP.getServerInfo`). A *scan* of the whole CGNAT range is impractical and noisy; a list must come from option 1, the user, or option 4. Cost/behaviour on the owner's tailnet: UNVERIFIED.
4. **Host-assisted discovery.** Not researched; mention only as a possible later option (a Windows-side agent conflicts with SPEC rule 3).

**Recommended starting point (for S3):** manual add by MagicDNS name or tailnet IP first (already works in moonlight-android), then API-key-based device listing as an *optional* feature stored in Keystore, with the probe in option 3 to confirm Sunshine presence. "One tap" is achievable only after the user supplies a token once; this is a UX/security tradeoff the owner must accept. Sunshine reachability over Tailscale (ports 47984/47989/47990, UDP 47998-48000/48010 offset by `port`; protocol UDP port list is **UNVERIFIED** here, take it from <https://docs.lizardbyte.dev/projects/sunshine/latest/> at S1) and the Tailscale ACL (SPEC section 2) must allow them.

## 9. Measurements: TO-MEASURE (owner's PC; do not fill with estimates)

Every row stays `TO-MEASURE` until an agent with access to the owner's PC records real numbers with date, versions and commit hashes. No fabricated or typical values.

Preconditions (human/agent with PC access):
1. Record host: Windows edition/build, GPU + driver, monitor count/resolutions/refresh, Sunshine version, Tailscale versions on PC and phone, phone model/Android version, Moonlight Android version.
2. Install Sunshine from the official release; note the first-run credentials handling; do not paste credentials into docs.
3. Pair Moonlight Android (PIN via web UI). Connect over the tailnet address (not LAN) and, separately, over LAN for a control.
4. Record ports actually used (Sunshine log) and the Tailscale ACL change needed. Redact IPs, hostnames, device names.

Measurements (fill the table, keep raw logs under `docs/verification/` redacted):

| ID | Measurement | Exact steps | Result |
|---|---|---|---|
| M1 | Moonlight stats overlay: network RTT, host processing latency, decode time, frame drops | In Moonlight Android settings enable "Show performance stats"; stream the desktop app for 5 min at the same resolution/fps/bitrate for each case (LAN, tailnet-direct, tailnet-relayed if reachable; `tailscale status` shows direct vs DERP on the PC); record min/avg/max from the overlay at 1 min intervals | TO-MEASURE |
| M2 | Input-to-photon latency | Film the phone screen and the PC monitor side by side with a high-frame-rate camera while tapping a Windows test app that changes color on click; count camera frames from touch to the color change shown on the phone; 20 samples, report median and p95 | TO-MEASURE |
| M3 | RDP baseline on a Pro host, same network path | Use the existing FreeRDP/other RDP client with same resolution; repeat M2 | TO-MEASURE |
| M4 | Monitor switch via hotkey | Connect, then send Ctrl+Alt+Shift+F1, F2, F3 (from a Bluetooth keyboard into Moonlight Android, which forwards unrecognised combos); record which monitor each F-key selects (compare with Sunshine's logged display order), time from keypress to first new frame (screen-record the phone, count frames), whether resolution/aspect changes mid-stream, any stream drop | TO-MEASURE |
| M5 | Monitor order stability | Repeat M4 after reboot, after sleeping a monitor, after hot-unplug/replug; note whether index to monitor mapping changed | TO-MEASURE |
| M6 | `output_name` selection | Set `output_name` to each Windows `device_id` from the Sunshine log; confirm which monitor streams; record whether config change needs restart | TO-MEASURE |
| M7 | Second client | While one client streams, try pairing/connecting a second device; record Sunshine log lines and result (rejected? takes over? shared?) | TO-MEASURE |
| M8 | Tailscale discovery inputs | With the API token path: one `GET /api/v2/tailnet/-/devices` call (token via env var, never in logs); confirm fields available (name, addresses, OS, online). With the probe path: `curl` `http://<magicdns>:47989/serverinfo` from a tailnet device | TO-MEASURE |
| M9 | Windows editions | Confirm on a Windows Home host that Sunshine runs and streams (no RDP server) | TO-MEASURE |
| M10 | Security checks | `FLAG_SECURE` absent in stock moonlight-android (screenshot test on device); what traffic is unencrypted on the tailnet vs Sunshine's own encryption (`encryption` settings in Sunshine config) | TO-MEASURE |

## 10. GPLv3 implications

Facts: Sunshine, moonlight-android and moonlight-common-c are GPL-3.0 (section 2). Blou is Apache-2.0 (`LICENSE`, workspace `Cargo.toml`). Apache-2.0 is compatible with GPLv3 (one-way: Apache-licensed code can be combined into a GPLv3 work): <https://www.apache.org/licenses/GPL-compatibility.html>, GPL license list <https://www.gnu.org/licenses/license-list.html#apache2>. This is a summary, not legal advice; ask the owner whether counsel is wanted before release.

Implications:
1. **A fork of moonlight-android, or any app that links moonlight-common-c, is a derivative work: the whole distributed Android app (APK) must be offered under GPLv3, with corresponding source** for every distribution. Blou's own Android app code (Kotlin, any new files inside that app) must therefore be GPLv3-compatible; Apache-2.0, MIT, BSD-3 are. Closed-source or otherwise GPLv3-incompatible additions cannot be included.
2. **The Rust core can stay Apache-2.0** as a separately licensed component, since Apache-2.0 code may be included in a GPLv3 combined work. Its dependencies per `deny.toml` are limited to Apache-2.0, ISC, BSD-3-Clause, MIT, Unicode-3.0, all GPLv3-compatible per the FSF list (not re-verified per crate here; `cargo deny check licenses` is the gate). The combined APK is GPLv3; the Rust crates alone keep their licenses. Do not relicense the Rust core to GPL without the owner's decision; also note a repository containing both Apache-2.0 crates and a GPLv3 fork needs per-directory license files and a top-level README explaining it. Choice of whether the fork lives in this repo or a separate one is part of S2.
3. **A clean new app that talks the Moonlight/GameStream protocol without using moonlight-android/common-c code** would not be bound by their license through code reuse, but this means reimplementing the protocol (RTSP, ENet, FEC via nanors, RTP, encryption), which is large and goes against SPEC's "no custom protocol stack" principle (rule 1 is about RDP, but the intent applies). Not recommended; any code copied or translated from the GPL sources is derivative. Whether protocol reimplementation has other legal exposure (NVIDIA GameStream marks): UNVERIFIED.
4. **Names and branding:** "Moonlight" and "Sunshine" are projects' names; do not ship under them. Trademark policy not reviewed: UNVERIFIED.
5. **FreeRDP, IronRDP** (Apache-2.0 / MIT OR Apache-2.0) remain compatible; RDP mode in a GPLv3 app is fine.
6. **Distribution:** GPLv3 requires source offer and prohibits additional restrictive terms. Whether Google Play's terms are compatible with distributing a GPLv3 Blou fork: UNVERIFIED; moonlight-android itself is distributed on Play (not verified here), which is evidence only that it has been done. F-Droid and direct APK from GitHub releases are options (S7 signing).
7. **Sunshine host** is a separate program the user installs; Blou does not bundle or link it, so its GPLv3 does not apply to Blou as long as Blou is not redistributing it. If Blou's installer or docs ever bundle Sunshine, GPLv3 conditions for redistribution apply.

## 11. Open questions for the owner / hardware agent

1. Fork `moonlight-android` (fastest, GPLv3 app) vs new app that wraps `moonlight-common-c` via JNI (more work, same GPLv3 outcome). Decision in S2.
2. Is a short-lived Tailscale API token (or OAuth client) on the phone acceptable?
3. Which hosts: Windows Home, Pro, both?
4. Accept a capture-switch pause (not seamless) on swipe, given only one display can be captured at a time?

## 12. Source list

- Sunshine: <https://github.com/LizardByte/Sunshine>, docs <https://docs.lizardbyte.dev/projects/sunshine/latest/>, files `docs/configuration.md`, `docs/getting_started.md`, `docs/api.md`, `src/nvhttp.cpp`, `src/rtsp.cpp`, `src/video.cpp`, `src/input.cpp`, `src/confighttp.cpp` at `d1fc311`.
- moonlight-android: <https://github.com/moonlight-stream/moonlight-android> at `b48494c`.
- moonlight-common-c: <https://github.com/moonlight-stream/moonlight-common-c>.
- Tailscale: URLs inline in section 8; Microsoft RDP host editions: section 1.
