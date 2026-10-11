# Public test-only certificates and keys

These EC P-256 fixtures are synthetic and name only `rdp.example.invalid` and `Blou Test Root`. The private keys here are deliberately public test data, never credentials for a real service. Never deploy them or install this CA in a system trust store.

`root.der` signs `trusted.der`; tests create an isolated Rustls root store containing only that CA. `self-signed.der` is independent. The leaf test keys let in-memory Rustls handshakes prove signature verification without network, hardware or production secrets. The root private key is not retained.

Regenerate manually with `bash scripts/generate_test_certificates.sh` (OpenSSL required only for regeneration). Tests use checked-in DER and never invoke OpenSSL. Long test validity avoids fixture expiry churn; this does not prescribe production-certificate validity.
