#!/usr/bin/env bash
# THE verification gate for Blou. Exit code 0 = pass; anything else = not done.
# Usage: scripts/verify.sh        (run scripts/setup.sh once first; this script needs no network afterwards)
#
# NOT CHECKED (do not claim these from a green run): Windows/Android builds, FreeRDP native
# submodule, real remote sessions, Windows screen capture (scripts/*.ps1, src/blou/desktop.py ImageGrab path).
# Non-blocking steps print "WARN" and never fail the run.
set -euo pipefail
cd "$(dirname "$0")/.."

VENV="${VENV:-.venv}"
step() { printf '\n== %s\n' "$*"; }
warn_step() { local n="$1"; shift; step "$n (non-blocking)"; if ! "$@"; then echo "WARN: '$n' failed (non-blocking)"; fi; }
command -v git >/dev/null 2>&1 || { echo "verify: git not found" >&2; exit 2; }

step "shell syntax"
for f in scripts/*.sh; do bash -n "$f"; done

step "python environment"
if [[ ! -x "$VENV/bin/python" ]]; then
  echo "verify: $VENV missing; running scripts/setup.sh (needs network)"; scripts/setup.sh
fi
export PATH="$PWD/$VENV/bin:$PATH"
python --version

step "workflow lint (actionlint)"
actionlint

step "ruff"
ruff check src tests scripts

warn_step "mypy" mypy --ignore-missing-imports src

step "unit tests"
python -m unittest discover -s tests -v

step "test-integrity (test-case count >= scripts/test-baseline.txt)"
EVENT_NAME=local scripts/check-test-integrity.sh

step "offline demo (must not change the committed fixture)"
python scripts/demo_local.py >/dev/null
git diff --exit-code -- docs/verification/local-core-demo.json

step "package build (sdist + wheel, no network)"
OUT="$(mktemp -d)"; trap 'rm -rf "$OUT"' EXIT
python -m build --no-isolation --outdir "$OUT" . >/dev/null
ls "$OUT"
python - "$OUT" <<'PY'
import sys, zipfile, glob
whl = glob.glob(sys.argv[1] + "/*.whl")
assert len(whl) == 1, whl
names = zipfile.ZipFile(whl[0]).namelist()
assert "blou/layout.py" in names, names
print("wheel contains blou package:", whl[0].rsplit("/", 1)[-1])
PY

step "rust (fmt, clippy -D warnings, test) - only if a root Cargo.toml exists and cargo is installed"
if [[ -f Cargo.toml ]] && command -v cargo >/dev/null 2>&1; then
  cargo fmt --all -- --check
  cargo clippy --workspace --all-targets -- -D warnings
  cargo test --workspace
else
  echo "SKIP: no root Cargo.toml (Rust workspace not created yet) or cargo not installed"
fi

printf '\nPASS: shell syntax + actionlint + ruff + unittest + test-integrity + offline demo + package build (+ rust fmt/clippy/test when a root Cargo.toml exists).\n'
printf 'NOT CHECKED: Windows/Android builds, FreeRDP native submodule, real remote sessions, Windows screen capture.\n'
