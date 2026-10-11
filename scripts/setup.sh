#!/usr/bin/env bash
# Deterministic bootstrap for a clean checkout or a cloud sandbox (Codex, devcontainer, CI).
#
#   scripts/setup.sh                      create .venv, install the project + pinned dev tools (needs network once)
#   scripts/setup.sh --prefetch DIR       download every wheel needed into DIR (run while online)
#   scripts/setup.sh --wheelhouse DIR     install from DIR only, no network at all
#   scripts/setup.sh --with-freerdp       also fetch the pinned FreeRDP submodule (optional, ~100 MB, needs network)
#
# Environment: PYTHON (interpreter, default python3; must be >= 3.10), VENV (default .venv).
# After a successful run, scripts/verify.sh works without network access.
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-python3}"
VENV="${VENV:-.venv}"
WHEELHOUSE="" PREFETCH="" WITH_FREERDP=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --wheelhouse) WHEELHOUSE="${2:?--wheelhouse needs a directory}"; shift 2 ;;
    --prefetch) PREFETCH="${2:?--prefetch needs a directory}"; shift 2 ;;
    --with-freerdp) WITH_FREERDP=1; shift ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "setup: unknown argument '$1'" >&2; exit 2 ;;
  esac
done

command -v "$PYTHON" >/dev/null 2>&1 || { echo "setup: '$PYTHON' not found" >&2; exit 2; }
command -v cargo >/dev/null 2>&1 || { echo "setup: cargo not found; install Rust with rustup first" >&2; exit 2; }
"$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
  || { echo "setup: Python >= 3.10 required, found $("$PYTHON" --version 2>&1)" >&2; exit 2; }
"$PYTHON" -c 'import venv, ensurepip' 2>/dev/null \
  || { echo "setup: python venv/ensurepip missing (Debian/Ubuntu: apt install python3-venv)" >&2; exit 2; }

if [[ ! -x "$VENV/bin/python" ]]; then "$PYTHON" -m venv "$VENV"; fi
PY="$VENV/bin/python"
PIP=("$PY" -m pip --disable-pip-version-check -q)
BUILD_REQ="setuptools==84.0.0"

if [[ -n "$PREFETCH" ]]; then
  mkdir -p "$PREFETCH"
  "${PIP[@]}" download -d "$PREFETCH" -c constraints-dev.txt "$BUILD_REQ" wheel pip ".[dev]"
  # actionlint-py is an sdist that fetches the actionlint binary while building; build it into a
  # wheel now (online) so the offline install needs no network. The wheel is platform specific.
  "${PIP[@]}" wheel --no-deps -c constraints-dev.txt -w "$PREFETCH" actionlint-py==1.7.12.25
  echo "setup: wheels saved to $PREFETCH; later run: scripts/setup.sh --wheelhouse $PREFETCH"
  exit 0
fi

if [[ -n "$WHEELHOUSE" ]]; then
  [[ -d "$WHEELHOUSE" ]] || { echo "setup: wheelhouse '$WHEELHOUSE' not found" >&2; exit 2; }
  OFFLINE=(--no-index --find-links "$WHEELHOUSE")
  "${PIP[@]}" install "${OFFLINE[@]}" "$BUILD_REQ" wheel
  # --no-build-isolation: the build backend must come from the venv, not the network.
  "${PIP[@]}" install "${OFFLINE[@]}" --no-build-isolation -c constraints-dev.txt -e ".[dev]"
else
  "${PIP[@]}" install -c constraints-dev.txt -e ".[dev]"
fi

if (( WITH_FREERDP )); then
  # The gitlink points at upstream FreeRDP 3.31.1 (63b948ca5). Not needed for the Python gate.
  git submodule update --init --depth 1 FreeRDP
fi

if [[ -n "$WHEELHOUSE" ]]; then
  cargo fetch --locked --offline
else
  cargo fetch --locked
fi

"$PY" -c 'import blou; print("setup: blou importable from", blou.__file__)'
echo "setup: done. Activate with: source $VENV/bin/activate   Gate: scripts/verify.sh"
