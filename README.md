# 📱 Blou — Android RDP Client with Virtual Multi-Monitor

> **A single-screen Android phone providing a genuine multi-monitor Windows RDP session through client-side layout fabrication and viewport navigation.**

---

## 💡 The Core Insight (The Whole Trick)

In standard Remote Desktop Protocol (RDP), the client's monitor layout is **declared unilaterally by the client**. The server does not and cannot verify the client's physical display hardware.

FreeRDP's `/multimon` transmits the combined geometry of connected monitors. **Nothing stops us from announcing an arbitrary multi-monitor layout we invented.**

```
Client Announces: 3 Monitors (3x 1920x1080 = 5760x1080 Bounding Box)
                           │
                           ▼
Windows Host creates 3 distinct logical displays:
  ├── Display 1: (0, 0, 1920, 1080)   [Primary]
  ├── Display 2: (1920, 0, 1920, 1080)
  └── Display 3: (3840, 0, 1920, 1080)
                           │
                           ▼
  • Native Windows taskbar placement per display
  • Native Win + Shift + Left/Right window snapping
  • Single composite 5760x1080 framebuffer streamed to client
                           │
                           ▼
Blou Phone Viewport: Renders one monitor at a time (0..2),
swiped smoothly with absolute coordinate touch translation.
```

**No existing Android RDP client does this.** That is the gap Blou fills.

---

## 🏛️ System Architecture

```
+--------------------------------------------------------------------------------+
| Host: Windows 11 (100.64.0.10:3389 over Tailscale)                            |
|   - Network Level Authentication (NLA) / CredSSP                               |
|   - Virtual Monitor Layout received from client (3x 1920x1080 = 5760x1080)     |
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
|   - Strict Cert Pinning: pVerifyCertificateEx SHA-256 check (Zero TOFU)        |
|   - Credential Store: Android Keystore EC P-256 StrongBox/TEE + BiometricPrompt|
|                                                                                |
| [Layer 2: FreeRDP C Core & JNI Wrapper]                                         |
|   - Pinned tagged release: v3.31.1 (commit 63b948ca5)                          |
|   - Pre-connect settings injection:                                            |
|       FreeRDP_UseMultimon = TRUE                                               |
|       FreeRDP_ForceMultimon = TRUE                                             |
|       FreeRDP_MonitorCount = 3                                                 |
|       FreeRDP_MonitorDefArray = [ (0,0), (1920,0), (3840,0) ]                  |
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

## 🚦 Phased Implementation Roadmap & Gates

| Phase | Description | Status | Gate Requirement |
| :--- | :--- | :---: | :--- |
| **Phase 0** | **Validate the Layout Lie (WSL/Linux Probe)** | ⏳ In Review | Windows 11 host accepts fabricated 3-monitor layout from a client with 1 display and reports 3 monitors in session. |
| **Phase 1** | **Stock Android Build & Baseline Connection** | 🔨 In Progress | FreeRDP 3.x `client/Android` builds cleanly (NDK/CMake/Gradle) and connects to host over Tailscale. |
| **Phase 2** | **Inject Fabricated Layout in Android JNI** | 📋 Queued | Pre-connect settings injection in JNI establishes 5760x1080 3-monitor session on Android. |
| **Phase 3** | **Viewport UI & Coordinate Translation** | 📋 Queued | Horizontal swipe between monitor rects; touch event coordinate mapping from viewport to 5760x1080 canvas. |
| **Phase 4** | **Configurable Layout & Dynamic Channel** | 📋 Queued | User profiles (1-4 monitors) + dynamic layout reconfiguration via `DISPLAYCONTROL` DVC without reconnecting. |
| **Phase 5** | **Security Hardening** | 📋 Queued | Zero-TOFU certificate pinning, StrongBox/TEE Keystore with BiometricPrompt, `FLAG_SECURE`. |

---

## 🛠️ Repository Layout

```
Blou/
├── FreeRDP/             # Pinned git submodule (tag 3.31.1, commit 63b948ca5)
├── patches/             # Exact, documented diffs against FreeRDP source
│   ├── 0001-xfreerdp-fabricated-multimon-layout.patch
│   └── 0002-android-cmake-cross-compile-fixes.patch
├── scripts/             # Automation, verification & build orchestrators
│   ├── run_phase0_probe.sh           # Phase 0 WSL test runner
│   ├── verify_windows_topology.ps1   # In-session Windows display auditor
│   ├── patch_phase0.py               # FreeRDP xf_monitor layout patcher
│   └── build_android.ps1             # Android Gradle build helper
├── docs/                # Comprehensive architectural and protocol specs
│   ├── PROTOCOL_INSIGHTS.md          # MS-RDPBCGR monitor layout PDU mechanics
│   └── SECURITY_ARCHITECTURE.md      # Cert pinning, Keystore, threat boundary
├── SPEC.md              # Gated feature specification (SHA-256 frozen)
├── ARCHITECTURE.md      # Blast radius matrix & ticket decomposition
└── README.md
```

---

## 🚀 Phase 0: Reproducing the Layout Lie (WSL/Linux)

Before building Android, Phase 0 validates that Windows 11 accepts our fabricated topology.

### 1. Build xfreerdp with the Layout Lie
```bash
# In WSL Ubuntu 24.04:
cd FreeRDP
patch -p1 < ../patches/0001-xfreerdp-fabricated-multimon-layout.patch
cmake -GNinja -DCHANNEL_URBDRC=OFF -DCHANNEL_PRINTER=OFF -DWITH_CUPS=OFF -DWITH_FUSE=OFF -B build -S .
ninja -C build xfreerdp
```

### 2. Connect to the Windows 11 Host
```bash
./scripts/run_phase0_probe.sh 100.64.0.10 v
```

### 3. Verify Inside the Windows Session
Open PowerShell inside the RDP session and run:
```powershell
./scripts/verify_windows_topology.ps1
```
Expected output: **3 displays detected**, desktop geometry: **5760x1080**.

---

## 🔒 Security & Threat Model

- **Strict Certificate Pinning**: Zero Trust-On-First-Use (TOFU). Server cert SHA-256 fingerprint checked in `pVerifyCertificateEx`. Any mismatch immediately terminates the connection with no bypass dialog.
- **Hardware-Backed Credential Storage**: Android Keystore EC P-256 key (`StrongBox` with graceful fallback to `TEE`). `setUserAuthenticationRequired(true)` gates session password decryption behind `BiometricPrompt`.
- **Minimal Attack Surface**: `FLAG_SECURE` on session activity blocks screenshots and screen recording. Zero logging of credentials or framebuffer memory. Zero analytics or third-party telemetry.
