#!/usr/bin/env bash
# Blou — Phase 0 Layout Lie Probe Runner
# Executes xfreerdp with fabricated 3-monitor layout (3x 1920x1080 = 5760x1080)
set -euo pipefail

HOST="${1:-100.64.0.10}"
USER="${2:-v}"

echo "=========================================================="
echo "  Blou Phase 0: Fabricated Multi-Monitor Layout Probe"
echo "  Target Host : $HOST"
echo "  Username    : $USER"
echo "  Layout      : 3x 1920x1080 (Bounding Box: 5760x1080)"
echo "=========================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FREERDP_BIN="${FREERDP_BIN:-${FREERDP_PHASE0_DIR:-$HOME/freerdp-phase0}/build/client/X11/xfreerdp}"

if [ ! -f "$FREERDP_BIN" ]; then
    echo "[!] Error: xfreerdp binary not found at $FREERDP_BIN"
    echo "    Please build Phase 0 FreeRDP in WSL first."
    exit 1
fi

export DISPLAY="${DISPLAY:-:0}"
export BLOU_FAKE_MONITORS=1

echo "[*] Launching xfreerdp with BLOU_FAKE_MONITORS=1..."
"$FREERDP_BIN" \
    /v:"$HOST" \
    /u:"$USER" \
    /cert:ignore \
    +clipboard \
    /multimon:force \
    /dynamic-resolution
