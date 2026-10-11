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
1. **Zero custom RDP implementation**: FreeRDP C core stays untouched except for settings injection and certificate callbacks.
2. **Zero custom cryptography**: Transport is already double-encrypted via WireGuard (Curve25519) and RDP TLS. Blou only handles key storage and strict trust decisions.
3. **No Windows-side agent or service**: Purely client-side.
4. **Phase-by-phase gated progression**: Stop and report at every gate before proceeding.
5. **Exact diff inspection**: Show actual diffs for any modification to FreeRDP source.
6. **Pinned release commit**: Pin FreeRDP to a tagged release commit with minimal dependencies. No floating main branch.
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
