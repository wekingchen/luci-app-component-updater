#!/bin/sh
# Build an OpenWrt 25.12+ APKv3 manager for the AX6S firmware.
# Requires a host-side apk-tools 3 with 'mkpkg' (NOT the router's minimal apk).
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
APP="$ROOT/luci-app-component-updater"
OUT="${1:-$ROOT/dist}"
APK_TOOL="${APK_TOOL:-apk}"
VERSION=$(sed -n 's/^PKG_VERSION:=//p' "$APP/Makefile" | head -n1)
RELEASE=$(sed -n 's/^PKG_RELEASE:=//p' "$APP/Makefile" | head -n1)
[ -n "$VERSION" ] && [ -n "$RELEASE" ] || { echo 'missing package version'; exit 1; }
VERSION="$VERSION-r$RELEASE"
command -v "$APK_TOOL" >/dev/null 2>&1 || { echo 'apk-tools host executable missing'; exit 1; }
# Run the actual mkpkg command later: older apk-tools builds return an
# error for '--help' even when the non-minimal mkpkg subcommand exists.
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM
stage="$work/root"
mkdir -p "$stage/www" "$stage/lib/apk/packages" "$OUT"
cp -a "$APP/root/." "$stage/"
cp -a "$APP/htdocs/." "$stage/www/"
# OpenWrt APK stores conffile metadata in lib/apk/packages/.
printf '/etc/config/component-updater\n' > "$stage/lib/apk/packages/luci-app-component-updater.conffiles"
hash=$(sha256sum "$stage/etc/config/component-updater" | awk '{print $1}')
printf '/etc/config/component-updater %s\n' "$hash" > "$stage/lib/apk/packages/luci-app-component-updater.conffiles_static"
find "$stage" -type f | sed "s|^$stage|/|" | sort > "$stage/lib/apk/packages/luci-app-component-updater.list"
cat > "$work/post-install" <<'SCRIPT'
#!/bin/sh
# Same behavior as the opkg manager package; don't restart proxy services.
[ -n "${IPKG_INSTROOT:-}" ] && exit 0
rm -f /tmp/luci-indexcache /tmp/luci-indexcache.* 2>/dev/null || true
rm -rf /tmp/luci-modulecache/* 2>/dev/null || true
[ ! -x /etc/init.d/rpcd ] || /etc/init.d/rpcd reload >/dev/null 2>&1 || true
exit 0
SCRIPT
chmod 755 "$work/post-install"
outfile="$OUT/luci-app-component-updater-$VERSION.apk"
SOURCE_DATE_EPOCH=0 "$APK_TOOL" mkpkg \
  --info "name:luci-app-component-updater" \
  --info "version:$VERSION" \
  --info "arch:noarch" \
  --info "license:MIT" \
  --info "origin:luci-app-component-updater" \
  --info "url:https://github.com/wekingchen/luci-app-component-updater" \
  --info "description:OpenWrt component updater (native APK install and rollback)" \
  --info "maintainer:wekingchen" \
  --info "depends:luci-base rpcd jsonfilter libubox" \
  --script "post-install:$work/post-install" \
  --script "post-upgrade:$work/post-install" \
  --files "$stage" \
  --output "$outfile"
[ -s "$outfile" ] || { echo 'APK output is empty'; exit 1; }
echo "$outfile"
