#!/bin/sh
# Deliberately opt-in destructive acceptance. Requires local/backup management.
set -eu
[ "${1:-}" = "--install-and-rollback" ] || {
    echo 'Usage: COMPONENT_ACCEPT_LIVE=I_UNDERSTAND sh device-live-acceptance.sh --install-and-rollback'
    exit 2
}
[ "${COMPONENT_ACCEPT_LIVE:-}" = I_UNDERSTAND ] || {
    echo 'BLOCK: physical/local backup management and explicit acknowledgement required'
    exit 2
}
command -v sha256sum >/dev/null
command -v jsonfilter >/dev/null
[ -x /usr/sbin/component-updaterctl ] && [ -x /usr/bin/naive ] || exit 2
[ ! -L /usr/bin/naive ] || { echo 'BLOCK: unsafe symlink target'; exit 2; }
if [ -r /etc/component-updater/transaction.json ]; then
    echo 'BLOCK: unfinished transaction must be recovered first'
    exit 2
fi
old=$(sha256sum /usr/bin/naive | awk '{print $1}')
old_version=$(/usr/bin/naive --version 2>&1 | head -n1)
owner=$(opkg search /usr/bin/naive 2>/dev/null || true)
link=$(readlink /tmp/etc/passwall/bin/naive 2>/dev/null || true)
echo "Before: $old_version SHA256=$old"
echo "Owner: $owner"
echo "Runtime link: $link"
echo 'Checking official release and signed prebuilt artifact...'
/usr/sbin/component-updaterctl check
[ -r /tmp/component-updater/plan.json ] || { echo 'NOT_TESTED: no approved install plan'; exit 3; }
ready=$(jsonfilter -i /tmp/component-updater/plan.json -e '@.ready' 2>/dev/null || true)
[ "$ready" = true ] || { echo 'NOT_TESTED: signed plan is not ready'; exit 3; }
echo 'Installing signed candidate; PassWall will NOT be restarted'
if ! /usr/sbin/component-updaterctl run; then
    echo 'FAIL: install aborted; inspect updater status and persistent transaction record'
    exit 1
fi
new=$(sha256sum /usr/bin/naive | awk '{print $1}')
[ "$old" != "$new" ] || { echo 'NOT_TESTED: binary was unchanged'; exit 3; }
echo "Installed candidate: $(/usr/bin/naive --version 2>&1 | head -n1) SHA256=$new"
echo 'Restoring previous managed binary...'
/usr/sbin/component-updaterctl rollback
restored=$(sha256sum /usr/bin/naive | awk '{print $1}')
[ "$old" = "$restored" ] || { echo 'FAIL: restored SHA256 mismatch'; exit 1; }
if [ -n "$link" ]; then
    [ "$(readlink /tmp/etc/passwall/bin/naive 2>/dev/null)" = "$link" ] || {
        echo 'FAIL: PassWall runtime symlink changed'
        exit 1
    }
fi
[ ! -r /etc/component-updater/transaction.json ] || {
    echo 'FAIL: recovery transaction marker still exists'
    exit 1
}
echo 'PASS: signed install and rollback restored original SHA256; PassWall was not restarted.'
echo 'NOTE: Proxy functionality and browser/ACL still require separate real device validation.'
