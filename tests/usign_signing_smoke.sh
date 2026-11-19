#!/bin/sh
# Real usign/Ed25519 signing acceptance; separate from Python's isolated router mock.
set -eu
command -v usign >/dev/null 2>&1 || { echo 'missing usign'; exit 1; }
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
usign -G -s "$tmp/private.key" -p "$tmp/public.key" -c "component-updater-ci-test"
printf '%s\n' '{"schema":1,"component":"naiveproxy","upstream_tag":"v1.0"}' > "$tmp/manifest.json"
usign -S -m "$tmp/manifest.json" -s "$tmp/private.key" -x "$tmp/manifest.json.sig"
usign -V -q -m "$tmp/manifest.json" -p "$tmp/public.key" -x "$tmp/manifest.json.sig"
printf '%s\n' '{"schema":1,"component":"attacker","upstream_tag":"v1.0"}' > "$tmp/manifest.json"
if usign -V -q -m "$tmp/manifest.json" -p "$tmp/public.key" -x "$tmp/manifest.json.sig" >/dev/null 2>&1; then
    echo 'SECURITY FAILURE: tampered manifest accepted' >&2
    exit 1
fi
echo 'usign/Ed25519 signed-manifest acceptance PASS'
