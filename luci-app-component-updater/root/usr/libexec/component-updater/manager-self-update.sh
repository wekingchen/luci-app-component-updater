#!/bin/sh
# Native APKv3 manager self-update; never accepts a remote path or command.
# A first-time updater requires the current-version APK as rollback input.
umask 077
ROOT=/etc/component-updater/manager
TMP=/tmp/component-updater-manager
STAGE=$TMP/stage
PLAN=$TMP/plan.json
STATE=$TMP/state.json
TXN=$ROOT/transaction.json
PREV=$ROOT/previous
ACTIVE=$ROOT/active.apk
LOCK=$TMP/operation.lock
SELF=/usr/libexec/component-updater/manager-self-update.sh
NAME=luci-app-component-updater
[ -r /usr/share/libubox/jshn.sh ] || exit 1
. /usr/share/libubox/jshn.sh

field() { jsonfilter -i "$1" -e "$2" 2>/dev/null | head -n 1; }
respond() {
    json_init
    json_add_string status "$1"
    json_add_string message "$2"
    json_dump
    printf '\n'
}
state() {
    json_init
    json_add_string state "$1"
    json_add_string message "$2"
    json_dump > "$STATE.tmp.$$" &&
        mv -f "$STATE.tmp.$$" "$STATE"
}
init_dirs() {
    [ ! -L "$ROOT" ] && [ ! -L "$TMP" ] && [ ! -L "$STAGE" ] || return 1
    mkdir -p "$ROOT" "$TMP" "$STAGE" || return 1
    chmod 700 "$ROOT" "$TMP" "$STAGE"
}
valid_sha() {
    [ "$(printf %s "$1" | wc -c)" -eq 64 ] || return 1
    case "$1" in *[!0-9a-f]*) return 1;; esac
}
sha_ok() { [ "$(sha256sum "$1" 2>/dev/null | awk '{print $1}')" = "$2" ]; }
pkgver() {
    apk --no-network list --installed --manifest "$NAME" 2>/dev/null |
        awk '$1 == "luci-app-component-updater" {print $2;exit}'
}
compatible() {
    [ -d /lib/apk/db ] && command -v apk >/dev/null 2>&1 || return 1
    grep -q "DISTRIB_TARGET='mediatek/mt7622'" /etc/openwrt_release 2>/dev/null || return 1
    grep -q "DISTRIB_ARCH='aarch64_cortex-a53'" /etc/openwrt_release 2>/dev/null || return 1
    [ "$(cat /tmp/sysinfo/board_name 2>/dev/null)" = xiaomi,redmi-router-ax6s ] &&
    [ -n "$(pkgver)" ] && [ -r /etc/config/component-updater ] &&
    [ -r /etc/apk/world ]
}
# Never execute archive-supplied hooks; limit every extracted file to the
# updater's own namespace, disallow symlinks and device nodes.
inspect() {
    file=$1
    required=$2
    temp=$(mktemp -d "$TMP/inspect.XXXXXX") || return 1
    if ! apk adbdump --format json "$file" > "$temp/meta.json" 2>/dev/null ||
       ! grep -Eq '"name"[[:space:]]*:[[:space:]]*"luci-app-component-updater"' "$temp/meta.json" ||
       ! grep -Eq '"arch"[[:space:]]*:[[:space:]]*"noarch"' "$temp/meta.json"; then
        rm -rf "$temp"; return 1
    fi
    version=$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$temp/meta.json" | head -n 1)
    case "$version" in ''|*[!0-9A-Za-z.+_-]*) rm -rf "$temp"; return 1;; esac
    case "$version" in *-r[0-9]*) ;; *) rm -rf "$temp"; return 1;; esac
    [ -z "$required" ] || [ "$required" = "$version" ] || { rm -rf "$temp"; return 1; }
    mkdir "$temp/root" || { rm -rf "$temp"; return 1; }
    apk --no-network --allow-untrusted extract --no-chown --destination "$temp/root" "$file" >/dev/null 2>&1 ||
        { rm -rf "$temp"; return 1; }
    for mandatory in usr/sbin/component-updaterctl usr/libexec/rpcd/component-updater \
        usr/share/rpcd/acl.d/luci-app-component-updater.json; do
        [ -f "$temp/root/$mandatory" ] || { rm -rf "$temp"; return 1; }
    done
    if [ -z "$required" ]; then
        # New candidates must ship the independently copied worker and UI;
        # legacy installed r4 APKs do not yet contain these paths.
        [ -f "$temp/root/usr/libexec/component-updater/manager-self-update.sh" ] &&
        [ -f "$temp/root/www/luci-static/resources/view/component-updater/manager.js" ] ||
            { rm -rf "$temp"; return 1; }
    fi
    bad=$(find "$temp/root" ! -type d ! -type f -print | head -n 1)
    [ -z "$bad" ] || { rm -rf "$temp"; return 1; }
    valid=true
    find "$temp/root" -type f | while IFS= read -r member; do
        rel=$(echo "$member" | sed "s|^$temp/root/||")
        case "$rel" in
            usr/sbin/component-updaterctl|usr/libexec/rpcd/component-updater|\
            usr/libexec/component-updater/*|\
            usr/share/rpcd/acl.d/luci-app-component-updater.json|\
            usr/share/luci/menu.d/luci-app-component-updater.json|\
            www/luci-static/resources/view/component-updater/*|\
            www/luci-static/resources/component-updater/*|\
            etc/config/component-updater|lib/apk/packages/luci-app-component-updater.*) ;;
            *) exit 1;;
        esac
    done
    code=$?
    rm -rf "$temp"
    [ "$code" -eq 0 ] || return 1
    printf '%s\n' "$version"
}
# First update: user supplies current-version APK. Subsequent updates use
# the active APK previously cached by a verified successful transaction.
old_pkg() {
    installed=$(pkgver)
    if [ -f "$ACTIVE" ] && [ ! -L "$ACTIVE" ] &&
       [ "$(cat "$ROOT/active.version" 2>/dev/null)" = "$installed" ] &&
       sha_ok "$ACTIVE" "$(cat "$ROOT/active.sha256" 2>/dev/null)"; then
        printf '%s\n' "$ACTIVE"; return 0
    fi
    file=$STAGE/current.apk
    [ -f "$file" ] && [ ! -L "$file" ] &&
       [ "$(cat "$file.version" 2>/dev/null)" = "$installed" ] &&
       sha_ok "$file" "$(cat "$file.sha256" 2>/dev/null)" || return 1
    printf '%s\n' "$file"
}
capacity_ok() {
    a=$1; b=$2
    [ "$a" -ge 1024 ] && [ "$b" -ge 1024 ] || return 1
    existing=0
    if [ -f "$PREV/previous.apk" ]; then
        existing=$(wc -c < "$PREV/previous.apk" | tr -d ' ')
    fi
    case "$existing" in ''|*[!0-9]*) existing=0;; esac
    free=$(df -Pk /etc 2>/dev/null | awk 'NR==2 {print $4}')
    case "$free" in ''|*[!0-9]*) return 1;; esac
    required=$(((a+b+existing+1023)/1024+512))
    [ "$free" -ge "$required" ]
}
status() {
    compatible || { respond unsupported 'AX6S APKv3 manager only'; return 1; }
    init_dirs || return 1
    cache=false; old_pkg >/dev/null 2>&1 && cache=true
    backup=false
    [ -f "$PREV/previous.apk" ] &&
        sha_ok "$PREV/previous.apk" "$(cat "$PREV/previous.sha256" 2>/dev/null)" && backup=true
    busy=false; [ -d "$LOCK" ] && busy=true
    required=false; [ -f "$TXN" ] && required=true
    json_init
    json_add_string status ok
    json_add_string installed_version "$(pkgver)"
    json_add_string current_archive "$cache"
    json_add_string recovery_available "$backup"
    json_add_string recovery_required "$required"
    json_add_string busy "$busy"
    json_add_string job_state "$(field "$STATE" '@.state')"
    json_add_string job_message "$(field "$STATE" '@.message')"
    json_add_string staged_candidate "$(cat "$STAGE/candidate.apk.version" 2>/dev/null)"
    json_dump; printf '\n'
}
upload() {
    compatible && init_dirs || { respond unsupported 'AX6S APKv3 manager only'; return 1; }
    [ ! -f "$TXN" ] && [ ! -d "$LOCK" ] ||
        { respond recovery_required 'Unresolved manager transaction'; return 1; }
    input=$(cat)
    kind=$(jsonfilter -s "$input" -e '@.kind' 2>/dev/null | head -n 1)
    expected=$(jsonfilter -s "$input" -e '@.sha256' 2>/dev/null | head -n 1)
    bytes=$(jsonfilter -s "$input" -e '@.size' 2>/dev/null | head -n 1)
    valid_sha "$expected" || { respond error 'Invalid upload checksum'; return 1; }
    case "$bytes" in ''|0|*[!0-9]*) respond error 'Invalid upload size'; return 1;; esac
    [ "$bytes" -ge 1024 ] && [ "$bytes" -le 10485760 ] ||
        { respond error 'Manager APK is over 10 MiB'; return 1; }
    case "$kind" in
        candidate) src=/tmp/component-updater-manager-new.apk; dst=$STAGE/candidate.apk; same='';;
        previous) src=/tmp/component-updater-manager-current.apk; dst=$STAGE/current.apk; same=$(pkgver);;
        *) respond error 'Invalid manager upload role'; return 1;;
    esac
    [ -f "$src" ] && [ ! -L "$src" ] &&
        [ "$(wc -c < "$src" | tr -d ' ')" = "$bytes" ] &&
        sha_ok "$src" "$expected" ||
        { respond error 'Uploaded bytes do not match SHA256'; return 1; }
    version=$(inspect "$src" "$same") ||
        { respond error 'Unsupported manager APK identity or payload'; return 1; }
    [ "$kind" = previous ] || [ "$version" != "$(pkgver)" ] ||
        { respond error 'Candidate version already installed'; return 1; }
    mv -f "$src" "$dst" && chmod 600 "$dst" || return 1
    printf '%s\n' "$expected" > "$dst.sha256"
    printf '%s\n' "$version" > "$dst.version"
    rm -f "$PLAN"
    respond prepared "$version"
}
check() {
    compatible && init_dirs || { respond unsupported 'AX6S APKv3 manager only'; return 1; }
    [ ! -f "$TXN" ] && [ ! -d "$LOCK" ] ||
        { respond recovery_required 'Unresolved manager transaction'; return 1; }
    new=$STAGE/candidate.apk
    [ -f "$new" ] && sha_ok "$new" "$(cat "$new.sha256" 2>/dev/null)" ||
        { respond error 'Upload and verify candidate first'; return 1; }
    newver=$(inspect "$new" "") ||
        { respond error 'Invalid manager candidate'; return 1; }
    old=$(old_pkg) || { respond requires_previous 'Upload current version APK for offline rollback'; return 0; }
    oldver=$(pkgver)
    [ "$(inspect "$old" "$oldver")" = "$oldver" ] && [ "$newver" != "$oldver" ] ||
        { respond error 'Recovery archive does not match installed manager'; return 1; }
    nsize=$(wc -c < "$new" | tr -d ' ')
    osize=$(wc -c < "$old" | tr -d ' ')
    capacity_ok "$nsize" "$osize" ||
        { respond storage_limited 'Insufficient Overlay for manager backup and upgrade'; return 0; }
    json_init
    json_add_string old_version "$oldver"
    json_add_string new_version "$newver"
    json_add_string new_sha256 "$(cat "$new.sha256")"
    json_add_string old_sha256 "$(sha256sum "$old" | awk '{print $1}')"
    json_add_string candidate_bytes "$nsize"
    json_add_string previous_bytes "$osize"
    json_dump > "$PLAN.tmp.$$" && mv -f "$PLAN.tmp.$$" "$PLAN" || return 1
    respond ready "$newver"
}
plan_ok() {
    [ -f "$PLAN" ] || return 1
    [ "$(field "$PLAN" '@.old_version')" = "$(pkgver)" ] || return 1
    newsha=$(field "$PLAN" '@.new_sha256')
    oldsha=$(field "$PLAN" '@.old_sha256')
    valid_sha "$newsha" && valid_sha "$oldsha" || return 1
    sha_ok "$STAGE/candidate.apk" "$newsha" || return 1
    old=$(old_pkg) && sha_ok "$old" "$oldsha" || return 1
    [ "$(inspect "$STAGE/candidate.apk" "$(field "$PLAN" '@.new_version')")" = "$(field "$PLAN" '@.new_version')" ] || return 1
    [ "$(inspect "$old" "$(pkgver)")" = "$(pkgver)" ] || return 1
    capacity_ok "$(field "$PLAN" '@.candidate_bytes')" "$(field "$PLAN" '@.previous_bytes')"
}
save_world() {
    cp -p /etc/apk/world "$1/world" &&
    cp -p /etc/config/component-updater "$1/config" &&
    sha256sum /etc/apk/world | awk '{print $1}' > "$1/world.sha256" &&
    sha256sum /etc/config/component-updater | awk '{print $1}' > "$1/config.sha256"
}
restore_pkg() {
    dir=$1
    [ -f "$dir/previous.apk" ] && [ ! -L "$dir/previous.apk" ] &&
        sha_ok "$dir/previous.apk" "$(cat "$dir/previous.sha256" 2>/dev/null)" || return 1
    apk --no-network --allow-untrusted --no-scripts --no-commit-hooks add \
        "$dir/previous.apk" > "$TMP/restore.log" 2>&1 || return 1
    cp -p "$dir/world" /etc/apk/world &&
        cp -p "$dir/config" /etc/config/component-updater || return 1
    [ "$(pkgver)" = "$(cat "$dir/version")" ] &&
        sha_ok /etc/apk/world "$(cat "$dir/world.sha256")" &&
        sha_ok /etc/config/component-updater "$(cat "$dir/config.sha256")" &&
        [ -r /usr/libexec/rpcd/component-updater ] || return 1
    cp "$dir/previous.apk" "$ROOT/active.tmp.$$" &&
        mv -f "$ROOT/active.tmp.$$" "$ACTIVE" &&
        cp "$dir/previous.sha256" "$ROOT/active.sha256" &&
        cp "$dir/version" "$ROOT/active.version"
}
upgrade() {
    plan_ok || { state failed 'Manager plan expired or invalid'; return 1; }
    mkdir "$LOCK" 2>/dev/null || return 1
    trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT
    [ ! -f "$TXN" ] || return 1
    state backing_up 'Preparing persistent manager recovery'
    old=$(old_pkg) || return 1
    # A pre-transaction interruption can leave a partial next directory.
    # The durable TXN guard above prevents removal during recovery.
    rm -rf "$ROOT/next"
    mkdir "$ROOT/next" 2>/dev/null || return 1
    cp "$old" "$ROOT/next/previous.apk" &&
        printf '%s\n' "$(pkgver)" > "$ROOT/next/version" &&
        sha256sum "$ROOT/next/previous.apk" | awk '{print $1}' > "$ROOT/next/previous.sha256" &&
        save_world "$ROOT/next" || { state failed 'Cannot preserve recovery archive'; return 1; }
    sha_ok "$ROOT/next/previous.apk" "$(cat "$ROOT/next/previous.sha256")" || return 1
    printf '%s\n' next > "$TXN"
    sync
    state installing 'Updating LuCI manager without running package hooks'
    new=$STAGE/candidate.apk
    if ! apk --no-network --allow-untrusted --no-scripts --no-commit-hooks add \
        "$new" > "$TMP/install.log" 2>&1 ||
       ! cp -p "$ROOT/next/world" /etc/apk/world ||
       ! cp -p "$ROOT/next/config" /etc/config/component-updater ||
       [ "$(pkgver)" != "$(field "$PLAN" '@.new_version')" ] ||
       ! sha_ok "$new" "$(field "$PLAN" '@.new_sha256')" ||
       ! sha_ok /etc/apk/world "$(cat "$ROOT/next/world.sha256")" ||
       ! sha_ok /etc/config/component-updater "$(cat "$ROOT/next/config.sha256")"; then
        if restore_pkg "$ROOT/next"; then rm -f "$TXN"; state rolled_back 'Upgrade failed; old manager restored'
        else state recovery_required 'Upgrade failed; backup retained'; fi
        return 1
    fi
    cp "$new" "$ROOT/active.tmp.$$" &&
        mv -f "$ROOT/active.tmp.$$" "$ACTIVE" &&
        printf '%s\n' "$(field "$PLAN" '@.new_sha256')" > "$ROOT/active.sha256" &&
        printf '%s\n' "$(pkgver)" > "$ROOT/active.version" || {
            if restore_pkg "$ROOT/next"; then rm -f "$TXN"; state rolled_back 'Cache failed; restored old manager'
            else state recovery_required 'Manager recovery required'; fi
            return 1
        }
    rm -rf "$PREV" || return 1
    mv "$ROOT/next" "$PREV" || return 1
    rm -f "$TXN" "$PLAN"
    state completed 'Manager upgrade completed; one rollback archive retained'
}
restore() {
    mkdir "$LOCK" 2>/dev/null || return 1
    trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT
    dir=$PREV
    [ ! -f "$TXN" ] || dir=$ROOT/next
    state restoring 'Restoring previous manager APK'
    if restore_pkg "$dir"; then
        rm -f "$TXN" "$PLAN"
        # On a user-requested rollback, previous and active now point to the
        # same version; do not retain a redundant, unusable recovery entry.
        [ "$dir" != "$PREV" ] || rm -rf "$PREV"
        state rolled_back 'Previous manager restored and checked'
    else
        state recovery_required 'Manager recovery failed; archive kept'
        return 1
    fi
}
launch() {
    compatible && init_dirs || { respond unsupported 'AX6S APKv3 manager only'; return 1; }
    [ ! -d "$LOCK" ] || { respond busy 'Manager transaction in progress'; return 1; }
    case "$1" in
        upgrade) plan_ok || { respond error 'Manager plan invalid'; return 1; };;
        restore) [ -f "$PREV/previous.apk" ] || [ -r "$TXN" ] ||
            { respond error 'No manager recovery archive'; return 1; };;
        *) return 1;;
    esac
    cp "$SELF" "$TMP/worker.tmp.$$" &&
        chmod 700 "$TMP/worker.tmp.$$" &&
        mv -f "$TMP/worker.tmp.$$" "$TMP/worker.sh" || return 1
    state queued 'Manager background task queued'
    (nohup /bin/sh "$TMP/worker.sh" "$1" > "$TMP/worker.log" 2>&1 </dev/null &)
    respond started 'Manager task started'
}
worker() {
    compatible && init_dirs || return 1
    if [ "$1" = upgrade ]; then upgrade; else restore; fi
    result=$?
    /etc/init.d/rpcd restart >/dev/null 2>&1 || true
    /etc/init.d/uhttpd restart >/dev/null 2>&1 || true
    exit "$result"
}
case "$1" in
    status) status;;
    upload) upload;;
    check) check;;
    start) launch upgrade;;
    rollback) launch restore;;
    upgrade|restore) worker "$1";;
    *) respond error 'Unsupported manager method'; exit 1;;
esac
