# 🏗️ Architecture & Blast Radius Contract: Blou

## 1. System Topology & Data Flow

```
+--------------------------------------------------------------------------------+
| Host: Windows 11 (<WORKSTATION_TAILSCALE_IP>:3389 over Tailscale)              |
|   - NLA / CredSSP Auth                                                         |
|   - Virtual Monitor Layout received from client (e.g. 3x 1920x1080 = 5760x1080)|
|   - Windows Virtual Desktop Engine creates 3 distinct logical displays         |
|   - Composites into single wide framebuffer (5760x1080)                        |
+--------------------------------------------------------------------------------+
                                       ▲
                                       │ Tailscale (WireGuard Curve25519)
                                       │ + RDP TLS (ECDSA P-256)
                                       ▼
+--------------------------------------------------------------------------------+
| Client: Blou (Android Native + FreeRDP 3.x C Core)                             |
|                                                                                |
| [Layer 1: Security & Auth]                                                     |
|   - Cert Pinning: pVerifyCertificateEx strict SHA-256 fingerprint check (No TOFU|
|   - Credential Store: Android Keystore EC P-256 StrongBox/TEE + BiometricPrompt|
|                                                                                |
| [Layer 2: FreeRDP C Core & JNI Wrapper]                                         |
|   - Unmodified core engine pinned to tagged release commit                     |
|   - Pre-connect settings injection:                                            |
|       FreeRDP_UseMultimon = TRUE                                               |
|       FreeRDP_MonitorCount = 3                                                 |
|       FreeRDP_MonitorDefArray = [ (0,0,1920,1080), (1920,0,1920,1080), ... ]   |
|       FreeRDP_DesktopWidth = 5760, FreeRDP_DesktopHeight = 1080                |
|   - DISPLAYCONTROL Dynamic Virtual Channel handler                             |
|                                                                                |
| [Layer 3: Viewport & Input Translation Subsystem]                              |
|   - Framebuffer Manager: Holds 5760x1080 texture                               |
|   - Viewport Renderer: Crops to Monitor[currentMonitor] (0..N-1)               |
|   - UI: Horizontal swipe gesture + page indicator dots                         |
|   - Coordinate Mapper: maps touch (viewport_x, viewport_y) ->                  |
|     absolute (full_fb_x, full_fb_y) for input injection                        |
+--------------------------------------------------------------------------------+
```

---

## 2. Blast Radius Matrix & Ticket Decomposition

### Ticket-0: Phase 0 — Layout Lie Validation
- **Title**: Phase 0 — Validate Layout Lie via xfreerdp3
- **Allowed Files**: ["phase0/*", "scripts/*", "tests/*"]
- **Forbidden Files**: ["FreeRDP/*", "client/*", "app/*"]
- **TDD Tests**: ["tests/test_phase0.py"]

### Ticket-1: Phase 1 — Stock Android FreeRDP Build & Baseline Connection
- **Title**: Phase 1 — FreeRDP Android NDK/CMake/Gradle Baseline Build
- **Allowed Files**: ["FreeRDP/*", "build.gradle*", "settings.gradle*", "app/*"]
- **Forbidden Files**: ["src/crypto/*", "SPEC.md"]
- **TDD Tests**: ["tests/test_phase1.py"]

### Ticket-2: Phase 2 — Fabricated Monitor Injection
- **Title**: Phase 2 — Settings Injection in FreeRDP JNI Layer
- **Allowed Files**: ["client/Android/*", "app/src/main/jni/*"]
- **Forbidden Files**: ["libfreerdp/core/*"]
- **TDD Tests**: ["tests/test_phase2.py"]

### Ticket-3: Phase 3 — Viewport UI & Coordinate Translation
- **Title**: Phase 3 — Monitor Viewport Navigation & Input Mapping
- **Allowed Files**: ["app/src/main/java/*", "app/src/main/res/*", "app/src/test/*"]
- **Forbidden Files**: ["FreeRDP/libfreerdp/*"]
- **TDD Tests**: ["app/src/test/java/CoordinateTranslationTest.java"]

### Ticket-4: Phase 4 — Dynamic Reconfiguration
- **Title**: Phase 4 — DISPLAYCONTROL Channel & Profiles
- **Allowed Files**: ["app/src/main/java/*", "app/src/main/res/*"]
- **Forbidden Files**: ["libfreerdp/core/*"]
- **TDD Tests**: ["tests/test_phase4.py"]

### Ticket-5: Phase 5 — Security Hardening
- **Title**: Phase 5 — Strict Cert Pinning, Hardware Keystore, FLAG_SECURE
- **Allowed Files**: ["app/src/main/java/security/*", "app/src/main/jni/cert_pinning.c"]
- **Forbidden Files**: ["libfreerdp/crypto/*"]
- **TDD Tests**: ["tests/test_phase5.py"]
