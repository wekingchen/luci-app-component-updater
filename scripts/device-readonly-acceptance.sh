#!/bin/sh
# Read-only compatibility report for GL-MT3600BE / N1; never installs/restarts.
set -u
ok=0
failed=0
pass() { printf '[PASS] %s\n' "$1"; ok=$((ok+1)); }
fail() { printf '[BLOCK] %s\n' "$1"; failed=$((failed+1)); }
command_check() {
    if command -v "$1" >/dev/null 2>&1; then pass "command: $1"; else fail "missing command: $1"; fi
}
printf '%s\n' '=== COMPONENT UPDATER / READ-ONLY DEVICE ACCEPTANCE ==='
date -Iseconds 2>/dev/null || date
ubus call system board 2>/dev/null || fail "ubus system board inaccessible"
cat /etc/openwrt_release 2>/dev/null || fail "/etc/openwrt_release missing"
uname -a
for name in ubus rpcd jsonfilter usign sha256sum tar uci opkg; do command_check "$name"; done
if command -v uclient-fetch >/dev/null 2>&1 || command -v curl >/dev/null 2>&1; then
    pass "HTTPS download client available"
else
    fail "no curl or uclient-fetch"
fi
if [ -s /usr/share/component-updater/trust.pub ]; then
    pass "pinned usign trust.pub installed"
    sha256sum /usr/share/component-updater/trust.pub
else
    fail "public signing key not installed; updates intentionally disabled"
fi
if [ -x /usr/sbin/component-updaterctl ]; then
    pass "component-updaterctl installed"
    /usr/sbin/component-updaterctl status
else
    fail "component-updaterctl not installed"
fi
if [ -x /usr/libexec/rpcd/component-updater ]; then
    pass "rpcd executable plugin present"
    /usr/libexec/rpcd/component-updater list
else
    fail "rpcd executable plugin absent"
fi
if ubus -v list component-updater >/dev/null 2>&1; then
    pass "ubus registered component-updater"
    ubus -v list component-updater
    ubus call component-updater status
else
    fail "rpcd component-updater not registered (check /etc/init.d/rpcd)"
fi
if [ -r /www/luci-static/resources/view/component-updater/overview.js ] &&
   [ -r /www/luci-static/resources/view/component-updater/settings.js ]; then
    pass "LuCI overview/settings JS installed"
else
    fail "LuCI JavaScript missing"
fi
if [ -r /usr/share/luci/menu.d/luci-app-component-updater.json ] &&
   [ -r /usr/share/rpcd/acl.d/luci-app-component-updater.json ]; then
    pass "LuCI menu and rpcd ACL installed"
else
    fail "LuCI menu or ACL missing"
fi
if [ -x /usr/bin/naive ]; then
    pass "naive executable detected"
    /usr/bin/naive --version 2>&1 | head -n 2
    sha256sum /usr/bin/naive
    ls -l /usr/bin/naive /tmp/etc/passwall/bin/naive 2>/dev/null || true
    printf 'Active naive PIDs: '; pidof naive 2>/dev/null || true
else
    fail "/usr/bin/naive missing"
fi
df -h /overlay /tmp 2>/dev/null || true
printf '\nAcceptance summary: PASS=%s BLOCK=%s\n' "$ok" "$failed"
[ "$failed" -eq 0 ]
