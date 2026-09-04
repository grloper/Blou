# 🔒 Blou Security Architecture & Threat Model

## 1. Threat Model Boundary

### IN SCOPE (Defended by Blou)
| Threat | Mitigation Architecture |
| :--- | :--- |
| **Lost or Stolen Device** | Credentials protected via Android Keystore EC P-256 key with `setUserAuthenticationRequired(true)`. Unlocking requires local biometric authentication (`BiometricPrompt`). Private keys never leave hardware boundary (StrongBox / TEE). |
| **Malicious Node inside Tailnet (MITM)** | Strict Certificate Pinning in FreeRDP callback (`pVerifyCertificateEx`). SHA-256 fingerprint verified against hardcoded or app-configured pin. **Zero Trust-on-First-Use (TOFU)**. Zero user override dialogs. |
| **Screen-Capture Malware / Shoulder Surfing** | `FLAG_SECURE` enforced on session activity. Blocks Android recents thumbnails, screen recording, and unauthorized screenshots of the remote desktop session. |
| **Memory Safety in Client Fork** | Pinned upstream release commit (`3.31.1`). Zero modifications to FreeRDP core protocol or decompression logic; client modifications restricted strictly to configuration injection and certificate callbacks. |

### OUT OF SCOPE (Handled by Existing Infrastructure)
- **Network Transport Confidentiality**: Handled by Tailscale / WireGuard (Curve25519 + ChaCha20-Poly1305).
- **Session Confidentiality & Integrity**: Handled by standard RDP TLS (ECDSA P-256 / AES-GCM).
- **Public Internet Exposure**: Host RDP port 3389 is strictly firewalled to the Tailscale virtual interface with tailnet ACL enforcement.
- **Pre-Auth Attack Surface**: Handled by Windows Network Level Authentication (NLA) / CredSSP.

---

## 2. Certificate Pinning Implementation Contract

Stock RDP clients implement Trust-On-First-Use (TOFU) or prompt the user with modal dialogs to "accept certificate anyway". Users are trained to click through these warnings, making MITM attacks trivial.

**Blou eliminates the prompt entirely**:
- Implements `pVerifyCertificateEx` and `pVerifyChangedCertificateEx`.
- Extracts server certificate SHA-256 fingerprint.
- Compares against profile pinned fingerprint.
- **On mismatch**: Returns `0` immediately. Connection is aborted. Zero override button.

---

## 3. Hardware-Backed Credential Protection

```
+-------------------------------------------------------------+
| Android Keystore (StrongBox / TEE)                          |
|   - Key Pair: EC P-256                                      |
|   - Purpose: PURPOSE_AGREE_KEY (ECDH)                       |
|   - setUserAuthenticationRequired(true)                     |
|   - userAuthenticationParameters(timeout=0, BIOMETRIC_STRONG)|
+-------------------------------------------------------------+
                              │
                              ▼ Unlocked via BiometricPrompt
+-------------------------------------------------------------+
| Key Agreement & Encryption                                  |
|   - Ephemeral Key Agreement -> AES-256-GCM Key             |
|   - Encrypts / Decrypts Stored RDP Password                 |
|   - Plaintext password exists only in memory during connect |
|   - Memory explicitly zeroed after freerdp_connect          |
+-------------------------------------------------------------+
```
