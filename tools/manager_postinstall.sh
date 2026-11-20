#!/bin/sh
# Reload LuCI menu and rpcd ACLs after installing/upgrading the manager.
# Never restart the router or any managed proxy service.
set -u
[ -n "${IPKG_INSTROOT:-}" ] && exit 0

# Clear only LuCI's generated dispatcher/module caches. Do not touch UCI,
# browser credentials, PassWall or other process state.
rm -f /tmp/luci-indexcache /tmp/luci-indexcache.* 2>/dev/null || true
if [ -d /tmp/luci-modulecache ]; then
    rm -rf /tmp/luci-modulecache/* 2>/dev/null || true
fi

# A rpcd "reload" on some ImmortalWrt builds does not reload newly
# installed ACL JSONs and executable plugins. Restart rpcd in order for
# active LuCI authentication/menu checks to see the added permissions.
if [ -x /etc/init.d/rpcd ]; then
    /etc/init.d/rpcd restart >/dev/null 2>&1 || true
fi

# LuCI's dispatcher is served by uhttpd. Recycle it so a freshly installed
# menu.d entry is picked up on the next (new) browser session.
# This temporarily disconnects web UI sessions; SSH and proxy services
# are not restarted.
if [ -x /etc/init.d/uhttpd ]; then
    /etc/init.d/uhttpd restart >/dev/null 2>&1 || true
fi

exit 0
