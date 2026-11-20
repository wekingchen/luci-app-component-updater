#!/bin/sh
# No dependency on npm or third-party CDNs. Render actual shipped CSS in a
# deliberately hostile LuCI theme, test computed styles and capture previews.
set -eu
browser=
for binary in google-chrome chromium chromium-browser; do
    if command -v "$binary" >/dev/null 2>&1; then
        browser=$(command -v "$binary")
        break
    fi
done
[ -n "$browser" ] || { echo "ERROR: No Chrome/Chromium browser available for UI acceptance"; exit 1; }
mkdir -p ui-review
url="file://$(pwd)/tests/ui_visual_fixture.html"
render() {
    name=$1
    width=$2
    height=$3
    query=$4
    target="$url?$query"
    html=$("$browser" --headless --no-sandbox --disable-gpu --disable-dev-shm-usage \
        --hide-scrollbars --force-device-scale-factor=1 --window-size="$width,$height" \
        --virtual-time-budget=1800 --dump-dom "$target" 2>/dev/null) || return 1
    printf '%s\n' "$html" | grep -q 'data-ui-audit="pass"' || {
        printf '%s\n' "$html" | grep -o 'data-ui-problems="[^"]*"' | head -1 || true
        echo "ERROR: Browser UI audit failed at $width px ($name)"
        return 1
    }
    "$browser" --headless --no-sandbox --disable-gpu --disable-dev-shm-usage \
        --hide-scrollbars --force-device-scale-factor=1 --window-size="$width,$height" \
        --virtual-time-budget=1800 --screenshot="ui-review/$name.png" "$target" >/dev/null 2>&1
    test -s "ui-review/$name.png"
    echo "PASS: $name ($width x $height), preview at ui-review/$name.png"
}
render mobile-320-waiting 320 920 waiting
render mobile-390-waiting 390 920 waiting
render mobile-390-update-ready 390 920 ready
render desktop-1280-waiting 1280 920 waiting
