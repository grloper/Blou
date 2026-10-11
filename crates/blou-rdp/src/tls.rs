//! Always-on leaf pinning. A configured SHA-256 pin is the trust authority.
//!
//! CA/name validation cannot substitute for a matching pin. Rustls parses X.509 and
//! rustls/ring verifies handshake signatures. IronRDP's failure-only callback is insufficient.
use blou_core::pin::{CertificatePinningVerifier, PresentedCertificate, VerificationResult};
use rustls::{
    client::danger::{HandshakeSignatureValid, ServerCertVerified, ServerCertVerifier},
    pki_types::{CertificateDer, ServerName, UnixTime},
    DigitallySignedStruct, SignatureScheme,
};
use std::sync::Arc;

pub struct PinnedServerVerifier {
    pin: CertificatePinningVerifier,
}
impl std::fmt::Debug for PinnedServerVerifier {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("PinnedServerVerifier")
    }
}
impl PinnedServerVerifier {
    pub fn new(pin: CertificatePinningVerifier) -> Self {
        Self { pin }
    }
}
impl ServerCertVerifier for PinnedServerVerifier {
    fn verify_server_cert(
        &self,
        cert: &CertificateDer<'_>,
        _: &[CertificateDer<'_>],
        _: &ServerName<'_>,
        _: &[u8],
        _: UnixTime,
    ) -> Result<ServerCertVerified, rustls::Error> {
        if self.pin.verify(PresentedCertificate::Der(cert.as_ref())) != VerificationResult::Accepted
        {
            return Err(rustls::Error::InvalidCertificate(
                rustls::CertificateError::ApplicationVerificationFailure,
            ));
        }
        // A matching hash of arbitrary bytes is not a usable certificate. Parsing and
        // handshake-signature verification are upstream operations, never Blou crypto.
        rustls::server::ParsedCertificate::try_from(cert)?;
        Ok(ServerCertVerified::assertion())
    }
    fn verify_tls12_signature(
        &self,
        message: &[u8],
        cert: &CertificateDer<'_>,
        dss: &DigitallySignedStruct,
    ) -> Result<HandshakeSignatureValid, rustls::Error> {
        rustls::crypto::verify_tls12_signature(
            message,
            cert,
            dss,
            &rustls::crypto::ring::default_provider().signature_verification_algorithms,
        )
    }
    fn verify_tls13_signature(
        &self,
        message: &[u8],
        cert: &CertificateDer<'_>,
        dss: &DigitallySignedStruct,
    ) -> Result<HandshakeSignatureValid, rustls::Error> {
        rustls::crypto::verify_tls13_signature(
            message,
            cert,
            dss,
            &rustls::crypto::ring::default_provider().signature_verification_algorithms,
        )
    }
    fn supported_verify_schemes(&self) -> Vec<SignatureScheme> {
        rustls::crypto::ring::default_provider()
            .signature_verification_algorithms
            .supported_schemes()
    }
}
pub fn pinned_client_config(
    pin: CertificatePinningVerifier,
) -> Result<rustls::ClientConfig, rustls::Error> {
    let mut config = rustls::ClientConfig::builder_with_provider(Arc::new(
        rustls::crypto::ring::default_provider(),
    ))
    .with_safe_default_protocol_versions()?
    .dangerous()
    .with_custom_certificate_verifier(Arc::new(PinnedServerVerifier::new(pin)))
    .with_no_client_auth();
    // Every connection must present and validate its certificate; never log TLS secrets.
    config.resumption = rustls::client::Resumption::disabled();
    config.key_log = Arc::new(rustls::NoKeyLog);
    Ok(config)
}
