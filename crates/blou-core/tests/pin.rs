use blou_core::pin::{
    CertificatePinningVerifier, HardwareKeystorePolicy, PresentedCertificate, VerificationResult,
};

const CERT: &[u8] = b"MIIB...SAMPLE_X509_CERTIFICATE_DER_BYTES...1234567890";
fn verifier() -> CertificatePinningVerifier {
    CertificatePinningVerifier::new(Some(
        &CertificatePinningVerifier::fingerprint(CERT).unwrap(),
    ))
    .unwrap()
}

#[test]
fn exact_fingerprint_match_accepts() {
    assert_eq!(
        verifier().verify(PresentedCertificate::Der(CERT)),
        VerificationResult::Accepted
    );
}

#[test]
fn colon_separated_pinned_fingerprint_normalized() {
    let fp = CertificatePinningVerifier::fingerprint(CERT).unwrap();
    let colon = fp
        .as_bytes()
        .chunks(2)
        .map(|c| std::str::from_utf8(c).unwrap())
        .collect::<Vec<_>>()
        .join(":")
        .to_uppercase();
    assert_eq!(
        CertificatePinningVerifier::new(Some(&colon))
            .unwrap()
            .verify(PresentedCertificate::Der(CERT)),
        VerificationResult::Accepted
    );
}

#[test]
fn single_bit_cert_mismatch_strictly_rejected() {
    let mut tampered = CERT.to_vec();
    *tampered.last_mut().unwrap() = b'X';
    assert_eq!(
        verifier().verify(PresentedCertificate::Der(&tampered)),
        VerificationResult::RejectedMismatch
    );
}

#[test]
fn zero_tofu_rejection_when_unpinned() {
    assert_eq!(
        CertificatePinningVerifier::new(None)
            .unwrap()
            .verify(PresentedCertificate::Der(CERT)),
        VerificationResult::RejectedNoPin
    );
}

#[test]
fn invalid_fingerprint_format_raises_error() {
    assert!(CertificatePinningVerifier::new(Some("too_short_fingerprint")).is_err());
    assert!(CertificatePinningVerifier::new(Some(&"z".repeat(64))).is_err());
}

#[test]
fn malformed_presented_certificate_is_rejected_without_raising() {
    for presented in [
        PresentedCertificate::Der(b""),
        PresentedCertificate::Fingerprint("not-a-fingerprint"),
        PresentedCertificate::Fingerprint(""),
        PresentedCertificate::Fingerprint(&"z".repeat(64)),
        PresentedCertificate::Missing,
    ] {
        assert_eq!(
            verifier().verify(presented),
            VerificationResult::RejectedMalformed
        );
    }
}

#[test]
fn keystore_manifest_invariants() {
    let p = HardwareKeystorePolicy::manifest();
    assert_eq!(
        (p.algorithm, p.curve, p.purpose),
        ("EC", "secp256r1", "AGREE_KEY")
    );
    assert!(p.user_auth_required && p.biometric_strong_required);
    assert_eq!(p.auth_timeout, 0);
    assert!(p.strongbox_preferred && p.flag_secure_enforced && p.zero_credentials_log);
}
