use blou_core::pin::CertificatePinningVerifier;
use blou_rdp::tls::{pinned_client_config, PinnedServerVerifier};
use rustls::{
    client::{danger::ServerCertVerifier, WebPkiServerVerifier},
    pki_types::{CertificateDer, PrivateKeyDer, PrivatePkcs8KeyDer, ServerName, UnixTime},
    ClientConnection, ServerConnection,
};
use std::{io::Cursor, sync::Arc, time::Duration};

const SELF: &[u8] = include_bytes!("fixtures/self-signed.der");
const TRUSTED: &[u8] = include_bytes!("fixtures/trusted.der");
const ROOT: &[u8] = include_bytes!("fixtures/root.der");
const SELF_KEY: &[u8] = include_bytes!("fixtures/self-signed-test-key.der");
const TRUSTED_KEY: &[u8] = include_bytes!("fixtures/trusted-test-key.der");

fn policy(cert: &[u8]) -> CertificatePinningVerifier {
    CertificatePinningVerifier::new(Some(
        &CertificatePinningVerifier::fingerprint(cert).unwrap(),
    ))
    .unwrap()
}
fn check(
    verifier: &dyn ServerCertVerifier,
    cert: &[u8],
) -> Result<rustls::client::danger::ServerCertVerified, rustls::Error> {
    verifier.verify_server_cert(
        &CertificateDer::from(cert),
        &[],
        &ServerName::try_from("rdp.example.invalid").unwrap(),
        &[],
        UnixTime::since_unix_epoch(Duration::from_secs(1_800_000_000)),
    )
}
fn handshake(
    config: rustls::ClientConfig,
    cert: &[u8],
    key: &[u8],
) -> Result<(), Box<dyn std::error::Error>> {
    let server = rustls::ServerConfig::builder_with_provider(Arc::new(
        rustls::crypto::ring::default_provider(),
    ))
    .with_safe_default_protocol_versions()?
    .with_no_client_auth()
    .with_single_cert(
        vec![CertificateDer::from(cert.to_vec())],
        PrivateKeyDer::Pkcs8(PrivatePkcs8KeyDer::from(key.to_vec())),
    )?;
    let mut client = ClientConnection::new(
        Arc::new(config),
        ServerName::try_from("rdp.example.invalid")?,
    )?;
    let mut server = ServerConnection::new(Arc::new(server))?;
    for _ in 0..16 {
        let mut wire = Vec::new();
        client.write_tls(&mut wire)?;
        server.read_tls(&mut Cursor::new(wire))?;
        server.process_new_packets()?;
        let mut wire = Vec::new();
        server.write_tls(&mut wire)?;
        client.read_tls(&mut Cursor::new(wire))?;
        client.process_new_packets()?;
        if !client.is_handshaking() && !server.is_handshaking() {
            return Ok(());
        }
    }
    Err("in-memory TLS handshake did not finish".into())
}

#[test]
fn matching_self_signed_fixture_is_accepted() {
    assert!(check(&PinnedServerVerifier::new(policy(SELF)), SELF).is_ok());
}

#[test]
fn any_changed_certificate_is_rejected() {
    let mut changed = SELF.to_vec();
    let last = changed.len() - 1;
    changed[last] ^= 1;
    assert!(check(&PinnedServerVerifier::new(policy(SELF)), &changed).is_err());
}

#[test]
fn missing_pin_is_rejected() {
    assert!(check(
        &PinnedServerVerifier::new(CertificatePinningVerifier::new(None).unwrap()),
        SELF
    )
    .is_err());
}

#[test]
fn malformed_certificate_with_matching_hash_is_rejected_without_panic() {
    for der in [b"not an X.509 certificate".as_slice(), &[0x30, 0x03, 0x01]] {
        assert!(check(&PinnedServerVerifier::new(policy(der)), der).is_err());
    }
}

#[test]
fn trusted_root_never_bypasses_pin_mismatch() {
    let mut roots = rustls::RootCertStore::empty();
    roots.add(CertificateDer::from(ROOT)).unwrap();
    let normal = WebPkiServerVerifier::builder_with_provider(
        Arc::new(roots),
        Arc::new(rustls::crypto::ring::default_provider()),
    )
    .build()
    .unwrap();
    assert!(
        check(normal.as_ref(), TRUSTED).is_ok(),
        "fixture must actually chain to the configured trusted root"
    );
    assert!(check(&PinnedServerVerifier::new(policy(SELF)), TRUSTED).is_err());
    assert!(check(&PinnedServerVerifier::new(policy(TRUSTED)), TRUSTED).is_ok());
}

#[test]
fn every_single_bit_pin_mismatch_is_rejected() {
    let hash = ring::digest::digest(&ring::digest::SHA256, SELF);
    for byte in 0..32 {
        for bit in 0..8 {
            let mut pin = hash.as_ref().to_vec();
            pin[byte] ^= 1 << bit;
            let hex = pin.iter().map(|b| format!("{b:02x}")).collect::<String>();
            let verifier =
                PinnedServerVerifier::new(CertificatePinningVerifier::new(Some(&hex)).unwrap());
            assert!(check(&verifier, SELF).is_err());
        }
    }
}

#[test]
fn in_memory_tls_accepts_matching_fixtures_and_rejects_mismatches() {
    for (cert, key) in [(SELF, SELF_KEY), (TRUSTED, TRUSTED_KEY)] {
        assert!(handshake(pinned_client_config(policy(cert)).unwrap(), cert, key).is_ok());
        assert!(handshake(
            pinned_client_config(CertificatePinningVerifier::new(Some(&"00".repeat(32))).unwrap())
                .unwrap(),
            cert,
            key
        )
        .is_err());
        assert!(handshake(
            pinned_client_config(CertificatePinningVerifier::new(None).unwrap()).unwrap(),
            cert,
            key
        )
        .is_err());
    }
}

#[test]
fn upstream_strict_callback_works_only_as_a_failure_recovery_hook() {
    // Source at the pinned rev proves trusted validation returns before the callback.
    // This self-signed control verifies the callback's match/mismatch behaviour.
    rustls::crypto::ring::default_provider()
        .install_default()
        .expect("provider installed once in this test process");
    for matches in [true, false] {
        let pin = if matches {
            policy(SELF)
        } else {
            policy(TRUSTED)
        };
        let callback = Arc::new(move |der: &[u8], _: &str, _: &str| {
            pin.verify(blou_core::pin::PresentedCertificate::Der(der))
                == blou_core::pin::VerificationResult::Accepted
        });
        let config = ironrdp_tls::rustls_client_config(
            ironrdp_tls::CertificateValidation::Strict,
            "rdp.example.invalid",
            Some(callback),
        )
        .unwrap();
        assert_eq!(handshake(config, SELF, SELF_KEY).is_ok(), matches);
    }
}

#[test]
fn tls12_and_tls13_handshakes_enforce_the_same_pin() {
    for version in [&rustls::version::TLS12, &rustls::version::TLS13] {
        for matches in [true, false] {
            let verifier = PinnedServerVerifier::new(if matches {
                policy(SELF)
            } else {
                policy(TRUSTED)
            });
            let config = rustls::ClientConfig::builder_with_provider(Arc::new(
                rustls::crypto::ring::default_provider(),
            ))
            .with_protocol_versions(&[version])
            .unwrap()
            .dangerous()
            .with_custom_certificate_verifier(Arc::new(verifier))
            .with_no_client_auth();
            assert_eq!(handshake(config, SELF, SELF_KEY).is_ok(), matches);
        }
    }
}
