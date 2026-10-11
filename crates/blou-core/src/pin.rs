//! Fingerprint policy parity with Python. This layer hashes bytes; TLS validates X.509 separately.
use crate::CoreError;
use ring::digest::{digest, SHA256};
use subtle::ConstantTimeEq;

pub enum PresentedCertificate<'a> {
    Der(&'a [u8]),
    Fingerprint(&'a str),
    Missing,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VerificationResult {
    Accepted,
    RejectedMismatch,
    RejectedNoPin,
    RejectedMalformed,
}

pub struct CertificatePinningVerifier {
    pin: Option<[u8; 32]>,
}
impl CertificatePinningVerifier {
    pub fn new(pin: Option<&str>) -> Result<Self, CoreError> {
        let pin = match pin {
            None | Some("") => None,
            Some(fp) => Some(parse_fingerprint(fp)?),
        };
        Ok(Self { pin })
    }
    pub fn fingerprint(der: &[u8]) -> Result<String, CoreError> {
        if der.is_empty() {
            return Err(CoreError("Certificate bytes cannot be empty"));
        }
        let hash = digest(&SHA256, der);
        let hex = b"0123456789abcdef";
        let mut result = String::with_capacity(64);
        for byte in hash.as_ref() {
            result.push(char::from(hex[usize::from(byte >> 4)]));
            result.push(char::from(hex[usize::from(byte & 15)]));
        }
        Ok(result)
    }
    pub fn verify(&self, presented: PresentedCertificate<'_>) -> VerificationResult {
        let Some(pin) = &self.pin else {
            return VerificationResult::RejectedNoPin;
        };
        let presented = match presented {
            PresentedCertificate::Der(der) if !der.is_empty() => {
                let hash = digest(&SHA256, der);
                match <[u8; 32]>::try_from(hash.as_ref()) {
                    Ok(hash) => hash,
                    Err(_) => return VerificationResult::RejectedMalformed,
                }
            }
            PresentedCertificate::Fingerprint(fp) => match parse_fingerprint(fp) {
                Ok(fp) => fp,
                Err(_) => return VerificationResult::RejectedMalformed,
            },
            _ => return VerificationResult::RejectedMalformed,
        };
        if bool::from(pin.ct_eq(&presented)) {
            VerificationResult::Accepted
        } else {
            VerificationResult::RejectedMismatch
        }
    }
}
fn parse_fingerprint(fp: &str) -> Result<[u8; 32], CoreError> {
    let chars: Vec<char> = fp
        .chars()
        .filter(|c| !c.is_whitespace() && *c != ':')
        .collect();
    if chars.len() != 64 {
        return Err(CoreError(
            "SHA-256 fingerprint must contain 64 hex characters",
        ));
    }
    let mut bytes = [0u8; 32];
    for (i, pair) in chars.chunks_exact(2).enumerate() {
        let hi = pair[0]
            .to_digit(16)
            .ok_or(CoreError("Fingerprint contains non-hex character"))?;
        let lo = pair[1]
            .to_digit(16)
            .ok_or(CoreError("Fingerprint contains non-hex character"))?;
        bytes[i] = (hi * 16 + lo) as u8;
    }
    Ok(bytes)
}

/// Policy data only. Android Keystore enforcement remains unimplemented.
pub struct HardwareKeystorePolicy {
    pub algorithm: &'static str,
    pub curve: &'static str,
    pub purpose: &'static str,
    pub user_auth_required: bool,
    pub biometric_strong_required: bool,
    pub auth_timeout: u32,
    pub strongbox_preferred: bool,
    pub flag_secure_enforced: bool,
    pub zero_credentials_log: bool,
}
impl HardwareKeystorePolicy {
    pub fn manifest() -> Self {
        Self {
            algorithm: "EC",
            curve: "secp256r1",
            purpose: "AGREE_KEY",
            user_auth_required: true,
            biometric_strong_required: true,
            auth_timeout: 0,
            strongbox_preferred: true,
            flag_secure_enforced: true,
            zero_credentials_log: true,
        }
    }
}
