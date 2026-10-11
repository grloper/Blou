#!/usr/bin/env bash
# Phase 0 configuration preflight. Live launch is blocked pending strict native pinning.
set -euo pipefail
usage() {
    cat <<'HELP'
Usage: scripts/run_phase0_probe.sh [--prepare | --help]
Required environment: HOST, USERNAME, CERT_SHA256 (64 hex digits), FREERDP_BIN.
No host/account defaults. 100.64.0.10 is a documentation placeholder only.
--prepare validates configuration offline and reports the pending native policy.
Connection identifiers and pins are not printed. No password argument is accepted.
Live execution is blocked until FreeRDP ExternalCertificateManagement delegates
every leaf certificate to the Rust pin policy; CLI allowlists are insufficient.
Windows topology, native TLS/NLA and Android behaviour remain UNVERIFIED.
HELP
}
PREPARE=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h) usage; exit 0 ;;
        --prepare) PREPARE=1; shift ;;
        *) echo 'probe: unknown argument; use --help' >&2; exit 2 ;;
    esac
done
for name in HOST USERNAME CERT_SHA256 FREERDP_BIN; do
    if [[ -z "${!name:-}" ]]; then
        echo "probe: $name is required" >&2
        exit 2
    fi
done
if [[ ! "$CERT_SHA256" =~ ^[[:xdigit:]]{64}$ ]]; then
    echo 'probe: CERT_SHA256 must contain exactly 64 hexadecimal digits' >&2
    exit 2
fi
if [[ ! -f "$FREERDP_BIN" || ! -x "$FREERDP_BIN" ]]; then
    echo 'probe: FREERDP_BIN must name an executable file' >&2
    exit 2
fi
if (( ! PREPARE )); then
    echo 'probe: live execution blocked; strict pin callback is not integrated' >&2
    exit 3
fi
cat <<'PLAN'
Configuration valid; preparation only. No client was launched.
Required layout: BLOU_FAKE_MONITORS=1, 3x1920x1080, bounding box 5760x1080.
Required connection settings: /sec:nla /multimon:force -clipboard.
Required trust: ExternalCertificateManagement, empty fingerprint allowlist,
always-on VerifyX509Certificate -> Rust SHA-256 pin policy, no override/TOFU.
Native pinning, TLS/NLA and Windows topology: UNVERIFIED.
See docs/verification/freerdp-probe-policy.md before attempting a host gate.
PLAN
