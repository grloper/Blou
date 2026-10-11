#!/usr/bin/env bash
# Synthetic PUBLIC test credentials only; never use these keys for a real endpoint.
# Run manually to regenerate fixtures, then review/commit the resulting changes.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="crates/blou-rdp/tests/fixtures"
BUILD="$(mktemp -d)"
trap 'rm -rf "$BUILD"' EXIT
mkdir -p "$OUT"
openssl req -new -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes \
  -keyout "$BUILD/root-key.pem" -out "$BUILD/root.pem" -days 36500 \
  -subj '/CN=Blou Test Root' -addext 'basicConstraints=critical,CA:TRUE' \
  -addext 'keyUsage=critical,keyCertSign,cRLSign'
openssl req -new -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes \
  -keyout "$BUILD/trusted-key.pem" -out "$BUILD/trusted.csr" \
  -subj '/CN=rdp.example.invalid'
cat > "$BUILD/extensions.cnf" <<'CFG'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature
extendedKeyUsage=serverAuth
subjectAltName=DNS:rdp.example.invalid
CFG
openssl x509 -req -in "$BUILD/trusted.csr" -CA "$BUILD/root.pem" -CAkey "$BUILD/root-key.pem" \
  -set_serial 2 -days 36500 -extfile "$BUILD/extensions.cnf" -out "$BUILD/trusted.pem"
openssl req -new -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes \
  -keyout "$BUILD/self-signed-key.pem" -out "$BUILD/self-signed.pem" -days 36500 \
  -subj '/CN=rdp.example.invalid' -addext 'basicConstraints=critical,CA:FALSE' \
  -addext 'keyUsage=critical,digitalSignature' -addext 'extendedKeyUsage=serverAuth' \
  -addext 'subjectAltName=DNS:rdp.example.invalid'
for name in root trusted self-signed; do
  openssl x509 -in "$BUILD/$name.pem" -outform DER -out "$OUT/$name.der"
done
for name in trusted self-signed; do
  openssl pkcs8 -topk8 -nocrypt -in "$BUILD/$name-key.pem" -outform DER -out "$OUT/$name-test-key.der"
done
openssl verify -CAfile "$BUILD/root.pem" "$BUILD/trusted.pem"
echo 'generated synthetic certificate fixtures (keys are intentionally public test data)'
