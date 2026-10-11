#!/usr/bin/env bash
# Check both patches against the exact gitlink without changing the checkout.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="${1:-$ROOT/FreeRDP}"
PIN=63b948ca5cb94307fd5444ee6e73927a41ccdab4
if [[ ! -d "$SOURCE" ]] || ! git -C "$SOURCE" rev-parse --verify HEAD >/dev/null 2>&1; then
    echo 'check-patches: pinned FreeRDP checkout required; run scripts/setup.sh --with-freerdp' >&2
    exit 2
fi
if [[ "$(git -C "$SOURCE" rev-parse HEAD)" != "$PIN" ]]; then
    echo 'check-patches: unexpected FreeRDP revision' >&2
    exit 2
fi
if [[ -n "$(git -C "$SOURCE" status --porcelain --untracked-files=no)" ]]; then
    echo 'check-patches: FreeRDP tracked files must be clean' >&2
    exit 2
fi
TEMP="$(mktemp -d)"
trap 'rm -rf -- "$TEMP"' EXIT
PATCHES=("$ROOT/patches/0001-xfreerdp-fabricated-multimon-layout.patch"
         "$ROOT/patches/0002-android-cmake-cross-compile-fixes.patch")
for patch in "${PATCHES[@]}"; do
    git apply --numstat "$patch" > "$TEMP/patch-files.tsv"
    while IFS=$'\t' read -r added removed file; do
        mkdir -p "$TEMP/$(dirname "$file")"
        git -C "$SOURCE" show "$PIN:$file" > "$TEMP/$file"
    done < "$TEMP/patch-files.tsv"
done
for patch in "${PATCHES[@]}"; do
    git -C "$TEMP" apply --check "$patch"
    git -C "$TEMP" apply "$patch"
    echo "check-patches: $(basename "$patch") applies"
done
echo "check-patches: PASS against $PIN; checkout unchanged"
