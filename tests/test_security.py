"""
Unit tests for Blou Strict Security & Certificate Pinning Engine.
"""
import hashlib
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from blou.security import (
    CertificatePinningVerifier,
    CertificateVerificationResult,
    HardwareKeystorePolicy
)


class TestCertificatePinningVerifier(unittest.TestCase):
    def setUp(self):
        self.dummy_cert_der = b"MIIB...SAMPLE_X509_CERTIFICATE_DER_BYTES...1234567890"
        self.expected_fp = hashlib.sha256(self.dummy_cert_der).hexdigest().lower()
        self.verifier = CertificatePinningVerifier(pinned_sha256_hex=self.expected_fp)

    def test_exact_fingerprint_match_accepts(self):
        res = self.verifier.verify_certificate(self.dummy_cert_der)
        self.assertEqual(res, CertificateVerificationResult.ACCEPTED)

    def test_colon_separated_pinned_fingerprint_normalized(self):
        # Colon-formatted string e.g. "AA:BB:CC:..."
        colon_fp = ":".join(self.expected_fp[i:i+2] for i in range(0, len(self.expected_fp), 2)).upper()
        verifier = CertificatePinningVerifier(pinned_sha256_hex=colon_fp)
        res = verifier.verify_certificate(self.dummy_cert_der)
        self.assertEqual(res, CertificateVerificationResult.ACCEPTED)

    def test_single_bit_cert_mismatch_strictly_rejected(self):
        tampered_cert = self.dummy_cert_der[:-1] + b"X"
        res = self.verifier.verify_certificate(tampered_cert)
        self.assertEqual(res, CertificateVerificationResult.REJECTED_MISMATCH)

    def test_zero_tofu_rejection_when_unpinned(self):
        # Non-negotiable rule: unpinned client rejects without TOFU prompt
        unpinned_verifier = CertificatePinningVerifier(pinned_sha256_hex=None)
        res = unpinned_verifier.verify_certificate(self.dummy_cert_der)
        self.assertEqual(res, CertificateVerificationResult.REJECTED_NO_PIN)

    def test_invalid_fingerprint_format_raises_error(self):
        with self.assertRaises(ValueError):
            CertificatePinningVerifier(pinned_sha256_hex="too_short_fingerprint")

        with self.assertRaises(ValueError):
            CertificatePinningVerifier(pinned_sha256_hex="z" * 64)  # Invalid non-hex char

    def test_malformed_presented_certificate_is_rejected_without_raising(self):
        for presented in (b"", "not-a-fingerprint", "", "z" * 64, None):
            with self.subTest(presented=presented):
                self.assertEqual(
                    self.verifier.verify_certificate(presented),
                    CertificateVerificationResult.REJECTED_MALFORMED,
                )


class TestHardwareKeystorePolicy(unittest.TestCase):
    def test_keystore_manifest_invariants(self):
        manifest = HardwareKeystorePolicy.get_security_manifest()
        self.assertEqual(manifest["algorithm"], "EC")
        self.assertEqual(manifest["curve"], "secp256r1")
        self.assertEqual(manifest["purpose"], "AGREE_KEY")
        self.assertTrue(manifest["user_auth_required"])
        self.assertTrue(manifest["biometric_strong_required"])
        self.assertEqual(manifest["auth_timeout"], 0)
        self.assertTrue(manifest["strongbox_preferred"])
        self.assertTrue(manifest["flag_secure_enforced"])
        self.assertTrue(manifest["zero_credentials_log"])


if __name__ == "__main__":
    unittest.main()
