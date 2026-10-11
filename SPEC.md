# 📋 Feature Specification: Blou — Android RDP Client with Virtual Multi-Monitor

## 1. Executive Summary & Objective
Blou is an Android RDP client that declares a fabricated multi-monitor layout to a Windows host, allowing a single-screen phone to host a genuine multi-monitor RDP session. The phone acts as a viewport that the user swipes between virtual monitors.

### The Core Insight
In RDP, the client monitor layout is declared by the client and not verified by the server. FreeRDP's `/multimon` transmits the combined geometry of connected monitors. Blou provides a fabricated layout (e.g., 3x 1920x1080 side-by-side, 5760x1080 bounding box). Windows initializes virtual displays accordingly, enabling native taskbar placement, multi-display desktop arrangement, and Win+Shift+Arrow window snapping. Blou receives the composite framebuffer and renders a single monitor rect viewport at a time.

---

## 2. Environment & Connectivity
- **Host**: Windows 11, IP `100.64.0.10` (placeholder; use your own tailnet address) over Tailscale VPN, RDP port `3389`, NLA enabled.
- **Firewall**: Port 3389 restricted strictly to Tailscale interface.
- **Tailscale ACL**: Restricted to `tag:<WORKSTATION_TAG>:3389`.
- **Client**: Android device.
- **Upstream Codebase**: FreeRDP 3.x (`client/Android`).

---

## 3. Non-Negotiable Architectural Rules
1. **Zero custom RDP implementation**: Blou does not write its own RDP protocol stack. The RDP engine is an upstream library: FreeRDP (C core untouched except for settings injection and certificate callbacks) or, per DR-001 below, IronRDP used as an unmodified dependency. Using IronRDP as a library is not a custom implementation; forking or patching its protocol code is (show the diff, rule 5).
2. **Zero custom cryptography**: Transport is already double-encrypted via WireGuard (Curve25519) and RDP TLS. Blou only handles key storage and strict trust decisions.
3. **No Windows-side agent or service**: Purely client-side.
4. **Phase-by-phase gated progression**: Stop and report at every gate before proceeding.
5. **Exact diff inspection**: Show actual diffs for any modification to FreeRDP source.
6. **Pinned release commit**: Pin the RDP engine (FreeRDP tag, or IronRDP crates.io version/git rev) to an exact version with minimal dependencies. No floating main branch.
7. **Fast escalation on build churn**: If Android/NDK build struggles across multiple attempts, stop and surface blockers immediately.

---

## 4. Phase Breakdown & Acceptance Criteria (Gated)

### Phase 0: Validate the Layout Lie (GATE)
- **Goal**: Prove Windows 11 host accepts a fabricated multi-monitor layout from a client with a single physical display before writing Android code.
- **Method**: Build/run FreeRDP (`xfreerdp3`) on Linux/WSL or native machine with 1 physical display, sending a 3-monitor layout (3x 1920x1080 side by side, 5760x1080 bounding box).
- **Acceptance Criterion (GATE)**: Windows reports 3 active displays inside the RDP session (verified via Windows Display Settings / PowerShell `Get-CimInstance Win32_DesktopMonitor` or display topology query). Stop and report findings.

### Phase 1: Stock Android Build Connects (GATE)
- **Goal**: Clone FreeRDP tagged release, configure Android NDK + CMake + Gradle, build unmodified `client/Android`, install on device/emulator, and connect to `100.64.0.10`.
- **Acceptance Criterion (GATE)**: Unmodified FreeRDP Android client connects successfully with NLA over Tailscale. Stop and report.

### Phase 2: Inject Fabricated Layout
- **Goal**: Inject fabricated layout parameters into FreeRDP settings before `freerdp_connect`:
  - `FreeRDP_UseMultimon = TRUE`
  - `FreeRDP_ForceMultimon = TRUE`
  - `FreeRDP_MonitorCount = 3`
  - `FreeRDP_MonitorDefArray = 3x rdpMonitor` (Primary at `(0,0)`, monitors 2 & 3 at `(1920,0)` and `(3840,0)`)
  - `FreeRDP_DesktopWidth = 5760`
  - `FreeRDP_DesktopHeight = 1080`
- **Constraints**: Primary monitor strictly at `(0,0)`; coordinates unsigned 32-bit (all monitors to right or below primary).
- **Acceptance Criterion**: Session connects at 5760x1080 with Windows recognizing 3 displays.

### Phase 3: Viewport UI & Input Translation
- **Goal**: Receive 5760x1080 framebuffer, render viewport cropped to `currentMonitor` (0..N-1) scaled to phone display, enable horizontal swipe switching, and display active monitor indicator dots.
- **Critical Requirement**: Input translation mapping touch/pointer coordinates from phone viewport back to absolute coordinates in the full 5760x1080 framebuffer. Automated unit tests verifying coordinate transformation matrices.

### Phase 4: Configurable Layout & Dynamic Virtual Channel
- **Goal**: User configuration for monitor count (1-4), per-monitor resolution, arrangement (row / 2x2 grid) persisted per profile.
- **Dynamic Updates**: Use `DISPLAYCONTROL` dynamic virtual channel to push layout changes mid-session without reconnecting.

### Phase 5: Security Hardening & Threat Model
- **5a. Strict Certificate Pinning**: Implement `pVerifyCertificateEx` and `pVerifyChangedCertificateEx`. Match SHA-256 fingerprint against app config. Mismatch returns `0` (rejection). Zero TOFU, zero user-override dialogs.
- **5b. Hardware-Backed Credential Storage**: Android Keystore EC P-256 (StrongBox preferred, graceful fallback to TEE), `setUserAuthenticationRequired(true)`, BiometricPrompt. ECDH key agreement (`PURPOSE_AGREE_KEY`) wrapping AES-256-GCM key.
- **5c. Attack Surface Reduction**: `FLAG_SECURE` on session activity, zero framebuffer/credential logging, clipboard clear on disconnect, zero telemetry/analytics.
- **5d. Supply Chain**: Pinned FreeRDP release commit, verified release signature, documented minimal dependencies.

---

## 5. Decision Records

### DR-001: Rust-first architecture, IronRDP as the preferred engine (DIRECTION ADOPTED; ENGINE GATED, 2026-10-11)

Status: Rust-first architecture adopted by the owner. IronRDP is the preferred engine; replacing the FreeRDP fallback remains conditional on the gates below. Evidence: `docs/IRONRDP_FEASIBILITY.md`. Port plan: `docs/RUST_PORT.md`. Order of work: `docs/ROADMAP.md`.

**Decision.** Blou's product logic moves to a Rust core (`blou-core`: layout geometry, touch-to-framebuffer mapping, certificate pinning/verification, display-control messages; `blou-rdp`: engine adapter; `blou-android`: bridge) with a thin Android UI (Kotlin). IronRDP (MIT OR Apache-2.0, Devolutions) becomes the preferred RDP engine, replacing FreeRDP, *if and only if* it passes the gates. FreeRDP stays as the fallback and as the Phase 0 baseline until then.

**Rationale.**
- One memory-safe language for everything Blou owns (geometry, trust decisions); one test suite shared by Android and desktop tooling.
- IronRDP is a library with the needed primitives: client monitor layout in GCC (on master), DISPLAYCONTROL DVC PDUs, NLA/CredSSP, a TLS certificate callback. The offline spike shows the generated client GCC monitor block for 3x1920x1080 is byte-exact.
- Removes the C/CMake/NDK-OpenSSL build churn that blocked Phase 1 (see patches/ and ROADMAP R10).

**Risks (honest).**
1. `Config::monitor_layout` exists only on IronRDP master (PR #1675, 2026-08-16), not in crates.io 0.10.0 (2026-07-10). Blou would pin a git rev until a release; all IronRDP crates are 0.x with breaking changes between releases.
2. The Phase 0 gate (Windows accepts a fabricated 3-monitor layout) is UNVERIFIED for any engine. If Windows rejects it, the product premise fails regardless of engine.
3. No Android build, linked `.so`, or on-device run of IronRDP has been done. `ironrdp-tls` with rustls needs a C toolchain (NDK clang) for the crypto provider; Android root-store behaviour is unknown.
4. IronRDP ships no Android bindings; the UniFFI/JNI bridge and surface rendering are Blou's own work.
5. TLS pinning hook is a callback that runs only when normal validation fails; strict "pin or reject" semantics need a Rust test with fixture certs (and possibly a custom rustls verifier). Default IronRDP policy accepts invalid certs; Blou must force `Strict`.
6. DISPLAYCONTROL multi-monitor needs raw PDU construction (helper is single-monitor); odd widths are silently rounded. Server behaviour for mid-session multi-monitor changes is UNVERIFIED.
7. Rewrite risk: parity with the Python reference must be proven by ported tests before any deletion.
8. Upstream is a commercial vendor's project; roadmap/priorities are not under Blou's control.

**What changes in rule 1.** "Zero custom RDP implementation" now reads: no Blou-authored RDP protocol code. Depending on FreeRDP *or* IronRDP unmodified (version-pinned) is allowed. Blou-authored code is limited to configuration, layout/geometry, pinning policy, input mapping, and UI. Rule 2 (zero custom cryptography) is unchanged: pinning compares a SHA-256 fingerprint; TLS/CredSSP come from the engine.

**Gates (all must pass before FreeRDP is removed).**
- G0: Phase 0 on a real Windows 11 host passes with FreeRDP (baseline) and with IronRDP (checklist in `docs/IRONRDP_FEASIBILITY.md`).
- G1: IronRDP connects with NLA from an Android build (device or emulator) with pinning enforced (mismatch rejected, tested).
- G2: 27 portable Python test cases pass as Rust tests with golden-vector parity.

**Fallback.** If G0 (IronRDP) or G1 fails, keep FreeRDP as the engine behind the same `blou-core`; the Rust core and Kotlin UI are still valid (hybrid). The Rust/Kotlin split does not depend on the engine choice.

### DR-002: Pivot the primary direction to GPU-capture streaming (Moonlight + Sunshine + Tailscale); RDP becomes "RDP mode" (PROPOSED, 2026-10-12)

Status: **proposed by the owner's direction; not accepted until the hardware proof gate below passes.** Evidence: `docs/MOONLIGHT_STACK.md` (research with citations; measurements are TO-MEASURE). Order of work: `docs/ROADMAP.md` (S1-S10). DR-001 is not revoked: it governs "RDP mode".

**Decision.** Blou's primary product becomes a low-latency GPU-capture streaming client for Android in the style of Moonlight + Sunshine + Tailscale: Sunshine (host) captures and encodes a PC display, the Android client decodes it over the tailnet, with one-tap Tailscale host discovery and swipe-to-switch between PC monitors. The existing Rust core, RDP/FreeRDP/IronRDP work and Python reference are kept as an alternative "RDP mode" (nothing is deleted; priority is demoted).

**Motivation (owner's).** Many Windows editions cannot host RDP (Home; Microsoft states only Pro/Enterprise/Education/Server can host: see `docs/MOONLIGHT_STACK.md` section 1), and GPU-capture streaming is expected to have lower latency. The latency claim is UNVERIFIED until measured (M1-M3).

**What research established (see the doc for citations and limits).**
- Sunshine, moonlight-android and moonlight-common-c are all GPL-3.0. Any Blou Android app that forks or links them is distributed under GPLv3 (implications in the doc, section 10). The Apache-2.0 Rust core may be included in such a GPLv3 app; `deny.toml` license allow-list is Apache-2.0, ISC, BSD-3-Clause, MIT, Unicode-3.0.
- Sunshine streams one display at a time. Monitor selection is the host `output_name` config or the in-stream hotkey Ctrl+Alt+Shift+F1..F13 (source-verified). No client-side per-session monitor parameter and no verified simultaneous multi-stream. Swipe therefore means a capture switch, with a pause to be measured (M4).
- Tailscale on Android has no supported cross-app peer-listing API; discovery options are the Tailscale API with a user token (secret on phone) or probing user-supplied names/IPs (section 8).
- moonlight-android has no `FLAG_SECURE` and no biometric lock in the source read; Blou's security requirements would be new work.

**Consequences for SPEC rules.**
- Rule 1 (no custom protocol stack) now also covers the streaming protocol: Blou must not reimplement GameStream/Moonlight; it forks or wraps moonlight-android / moonlight-common-c unmodified-as-far-as-possible, version-pinned (rule 6).
- Rule 3 (no Windows-side agent): Sunshine is a third-party host program the user installs; Blou ships no host code. A Blou-authored host component remains forbidden without a new DR.
- Rule 2 (no custom crypto) unchanged: pairing/encryption comes from the Moonlight protocol stack.
- Section 2 (RDP over Tailscale) applies to RDP mode only.
- Sections 4-5b-5c (phases, pinning, Keystore, `FLAG_SECURE`) remain the requirements for RDP mode and carry over, adapted, to streaming mode (S6).

**Gate (all required before DR-002 is accepted).**
- H0: on the owner's real PC and phone over Tailscale, stock Sunshine + stock moonlight-android pair and stream (M1), record latency vs the RDP baseline (M2/M3), and show the monitor hotkey switch works (M4-M6). Evidence under `docs/verification/` (redacted). No agent may mark H0 passed without it.
- H1: owner decides fork-vs-new-app (S2) with the GPLv3 consequences accepted.
- If H0 fails (stream unusable, latency not better, or monitor switching unworkable), DR-002 is rejected and DR-001 order resumes.

**Risks (honest).**
1. Latency advantage is a hypothesis; no measurement exists.
2. One-display-at-a-time capture limits the "swipe between monitors" UX to a switch with a pause; index-to-monitor order of the F-keys is unverified and may change on hotplug.
3. GPLv3 for the Android app; the owner must accept it, and distribution channels (Play Store) are unverified.
4. Dependence on upstream projects that are GPL, fast-moving (Sunshine releases date-versioned; recent builds are pre-releases) and not under Blou's control; Sunshine's admin API uses a password the phone should not store.
5. Tailscale API tokens on the phone are tailnet-wide secrets (1 to 90 day expiry for user tokens; OAuth tokens one hour).
6. Security posture of streaming mode (host exposure, Sunshine config, input injection privileges on the PC) is not yet threat-modelled; `docs/SECURITY_ARCHITECTURE.md` covers RDP only.
7. Sunk cost: RDP-mode work (pinning, DISPLAYCONTROL) may go unused in streaming mode.
