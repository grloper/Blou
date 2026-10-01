"""
Blou Strict Security & Certificate Pinning Engine.

Implements zero-TOFU certificate verification matching the FreeRDP
pVerifyCertificateEx and pVerifyChangedCertificateEx contract.
"""
import hashlib
import re
from typing import Optional, Union


class CertificateVerificationResult:
    ACCEPTED = 1
    REJECTED_MISMATCH = 0
    REJECTED_NO_PIN = -1
    REJECTED_MALFORMED = -2


class CertificatePinningVerifier:
    """
    Enforces strict certificate pinning for RDP TLS sessions.
    Zero Trust-On-First-Use (TOFU). Zero user override.
    """

    def __init__(self, pinned_sha256_hex: Optional[str] = None):
        self.pinned_fingerprint = self.normalize_fingerprint(pinned_sha256_hex) if pinned_sha256_hex else None

    @staticmethod
    def normalize_fingerprint(fp: Optional[str]) -> Optional[str]:
        """Normalizes hex fingerprints (removes colons, spaces, lowers case)."""
        if not fp:
            return None
        cleaned = re.sub(r"[\s:]+", "", fp).lower()
        if len(cleaned) != 64 or not all(c in "0123456789abcdef" for c in cleaned):
            raise ValueError(f"Invalid SHA-256 fingerprint: must be 64 hex characters (got '{fp}')")
        return cleaned

    @staticmethod
    def compute_cert_fingerprint(der_bytes: bytes) -> str:
        """Computes lowercase 64-char SHA-256 hex digest of X.509 DER certificate bytes."""
        if not der_bytes:
            raise ValueError("Certificate DER bytes cannot be empty")
        return hashlib.sha256(der_bytes).hexdigest().lower()

    def verify_certificate(
        self,
        cert_der_or_fingerprint: Union[bytes, str],
        host: str = "",
        port: int = 3389
    ) -> int:
        """
        Equivalent to FreeRDP pVerifyCertificateEx / pVerifyChangedCertificateEx callback.

        Returns:
          1: Certificate matches pinned fingerprint exactly -> ACCEPT
          0: Fingerprint mismatch or no pin configured -> REJECT (Disconnect)
        """
        if not self.pinned_fingerprint:
            # Non-negotiable rule: No unpinned connections. No TOFU.
            return CertificateVerificationResult.REJECTED_NO_PIN

        try:
            if isinstance(cert_der_or_fingerprint, bytes):
                presented_fp = self.compute_cert_fingerprint(cert_der_or_fingerprint)
            elif isinstance(cert_der_or_fingerprint, str):
                presented_fp = self.normalize_fingerprint(cert_der_or_fingerprint)
            else:
                return CertificateVerificationResult.REJECTED_MALFORMED
        except ValueError:
            # Peer-controlled input must fail closed through the callback result.
            return CertificateVerificationResult.REJECTED_MALFORMED
        if presented_fp is None:
            return CertificateVerificationResult.REJECTED_MALFORMED

        if presented_fp == self.pinned_fingerprint:
            return CertificateVerificationResult.ACCEPTED

        # Rejection on ANY mismatch — zero bypass dialog, zero TOFU
        return CertificateVerificationResult.REJECTED_MISMATCH


class HardwareKeystorePolicy:
    """
    Defines security parameters for Android Keystore credential storage.
    Enforces hardware isolation (StrongBox / TEE) and BiometricPrompt requirements.
    """

    KEY_ALIAS = "blou_rdp_credential_key"
    KEY_ALGORITHM = "EC"
    KEY_CURVE = "secp256r1"  # NIST P-256
    PURPOSE = "AGREE_KEY"    # ECDH for wrapping session AES key
    AUTH_TIMEOUT_SECONDS = 0  # Requires authentication for EVERY use

    @staticmethod
    def get_security_manifest() -> dict:
        return {
            "key_alias": HardwareKeystorePolicy.KEY_ALIAS,
            "algorithm": HardwareKeystorePolicy.KEY_ALGORITHM,
            "curve": HardwareKeystorePolicy.KEY_CURVE,
            "purpose": HardwareKeystorePolicy.PURPOSE,
            "user_auth_required": True,
            "biometric_strong_required": True,
            "auth_timeout": HardwareKeystorePolicy.AUTH_TIMEOUT_SECONDS,
            "strongbox_preferred": True,
            "tee_fallback": True,
            "flag_secure_enforced": True,
            "zero_credentials_log": True,
        }
