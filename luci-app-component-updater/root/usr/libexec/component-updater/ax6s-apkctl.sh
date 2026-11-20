#!/bin/sh
# Native APKv3 update and rollback adapter for the exact AX6S release.
# Sourced by component-updaterctl; uses shared SHA256, download, JSON and locks.
# Never auto-installs dependencies or restarts PassWall.
APK_ACTIVE="$BASE/installed/naiveproxy-active.apk"
APK_OLD_VERSION=154.0.8037.49.5-r1
APK_OLD_SHA=94a9d2ebce92b2fd877e1e7019dbfa09a7bb7a5d481ec593bd34b5d5abd2a861
APK_INIT_SHA=4d9dec9eb81586c5ea932260500329b68fc60f8c38af0712516b7a0f0ae59849
APK_CONFIG_SHA=201d0b3afd1e131f7695a4e4f541ec0ff6447dc8bf824eb8f96827d530b03682
APK_ORIG_FILE=naiveproxy_154.0.8037.49.5-r1_aarch64_cortex-a53.apk
apk_pkgversion() {
    apk --no-network list --installed --manifest naiveproxy 2>/dev/null |
        awk '$1 == "naiveproxy" { print $2 }' | head -n1
}
apk_owned_files_ok() {
    paths=$(apk --no-network info -L naiveproxy 2>/dev/null |
        sed -n '/ contains:/,$p' | sed '1d;/^$/d' | LC_ALL=C sort)
    wanted=$(printf '%s\n' etc/config/naiveproxy etc/init.d/naiveproxy \
        lib/apk/packages/naiveproxy.conffiles lib/apk/packages/naiveproxy.conffiles_static \
        lib/apk/packages/naiveproxy.list usr/bin/naive | LC_ALL=C sort)
    minimal=$(printf '%s\n' etc/config/naiveproxy etc/init.d/naiveproxy usr/bin/naive | LC_ALL=C sort)
    [ "$paths" = "$wanted" ] || [ "$paths" = "$minimal" ] || return 1
    for p in /usr/bin/naive /etc/config/naiveproxy /etc/init.d/naiveproxy; do
        [ -f "$p" ] && [ ! -L "$p" ] || return 1
        owned=$(apk --no-network info -W "$p" 2>/dev/null | head -n1)
        case "$owned" in *'is owned by naiveproxy-'*) ;; *) return 1;; esac
    done
    [ -x "$BINARY" ] && [ -x /etc/init.d/naiveproxy ]
}
apk_ownership_baseline_ok() {
    ax6s_apk_target && apk_owned_files_ok || return 1
    check_sha /etc/init.d/naiveproxy "$APK_INIT_SHA" || return 1
    oldver=$(apk_pkgversion)
    oldhash=$(sha256sum "$BINARY" | awk '{print $1}')
    if [ "$oldver" = "$APK_OLD_VERSION" ]; then
        [ "$oldhash" = "$APK_OLD_SHA" ] || return 1
    else
        [ "$(jsonval "$RECEIPT" '@.manager')" = apk ] || return 1
        [ "$oldver" = "$(jsonval "$RECEIPT" '@.package_version')" ] || return 1
        [ "$oldhash" = "$(jsonval "$RECEIPT" '@.binary_sha256')" ] || return 1
        oldpkgsha=$(jsonval "$RECEIPT" '@.package_sha256')
        valid_hash "$oldpkgsha" && [ -f "$APK_ACTIVE" ] &&
        [ ! -L "$APK_ACTIVE" ] && check_sha "$APK_ACTIVE" "$oldpkgsha" || return 1
    fi
}
apk_release_tag() { printf 'component-naiveproxy-%s-upx521-r3-ax6s-apk1\n' "$1"; }
# Fetch the exact package sizes from the same GitHub release metadata whose
# SHA256 digests already gate this update. Never infer free flash from /tmp.
apk_asset_bytes() {
    metadata=$1
    name=$2
    idx=0
    while [ "$idx" -lt 80 ]; do
        asset=$(jsonval "$metadata" "@.assets[$idx].name")
        [ -n "$asset" ] || break
        if [ "$asset" = "$name" ]; then
            bytes=$(jsonval "$metadata" "@.assets[$idx].size")
            case "$bytes" in ''|0|*[!0-9]*) return 1;; esac
            [ "$bytes" -le 104857600 ] || return 1
            printf '%s\n' "$bytes"
            return 0
        fi
        idx=$((idx+1))
    done
    return 1
}
apk_tmp_ok() {
    tmp_kib=$(df -Pk /tmp 2>/dev/null | awk 'NR==2 {print $4}')
    case "$tmp_kib" in ''|*[!0-9]*) return 1;; esac
    [ "$tmp_kib" -ge 32768 ]
}
# Read the *uncompressed* on-flash ELF size from a verified candidate package,
# extracted only inside /tmp. No scripts run, no device files are changed.
apk_candidate_binary_bytes() {
    archive=$1
    expected=$2
    staging=$(mktemp -d "$CACHE/apk-inspect.XXXXXX") || return 1
    chmod 700 "$staging" || { rm -rf "$staging"; return 1; }
    if ! apk --no-network --allow-untrusted extract --no-chown --destination "$staging" "$archive" >/dev/null 2>&1 ||
       [ ! -f "$staging/usr/bin/naive" ] || [ -L "$staging/usr/bin/naive" ] ||
       ! check_sha "$staging/usr/bin/naive" "$expected"; then
        rm -rf "$staging"
        return 1
    fi
    n=$(wc -c < "$staging/usr/bin/naive" | tr -d ' ')
    rm -rf "$staging"
    case "$n" in ''|0|*[!0-9]*) return 1;; esac
    printf '%s\n' "$n"
}
# In kB: one persistent rollback APK + the new active APK (for future
# upgrades) + the larger of old/new ELF sizes (for worst-case rollback)
# + 1.5 MiB filesystem/db headroom.
# For subsequent updates the previous APK is hardlinked from APK_ACTIVE on
# the same overlay; it requires no second full on-flash package copy.
# Never assume all space in /tmp is available in the 14 MiB overlay.
apk_overlay_budget_ok() {
    old_bytes=$1
    new_bytes=$2
    budget_elf_bytes=$3
    for n in "$old_bytes" "$new_bytes" "$budget_elf_bytes"; do
        case "$n" in ''|0|*[!0-9]*) return 1;; esac
        [ "$n" -le 104857600 ] || return 1
    done
    current_elf=$(wc -c < "$BINARY" 2>/dev/null | tr -d ' ') || return 1
    case "$current_elf" in ''|0|*[!0-9]*) return 1;; esac
    [ "$current_elf" -le 104857600 ] || return 1
    [ "$current_elf" -le "$budget_elf_bytes" ] || budget_elf_bytes=$current_elf
    free_kib=$(df -Pk /etc 2>/dev/null | awk 'NR==2 {print $4}')
    case "$free_kib" in ''|*[!0-9]*) return 1;; esac
    if [ -r "$RECEIPT" ] && [ -f "$APK_ACTIVE" ] &&
       [ ! -L "$APK_ACTIVE" ]; then
        # A verified hardlink is made from the existing persisted APK.
        old_bytes=0
    fi
    required_kib=$(((old_bytes+new_bytes+budget_elf_bytes+1023)/1024+1536))
    [ "$free_kib" -ge "$required_kib" ]
}
apk_plan_ok() {
    [ ! -r "$TXN" ] && [ -r "$PLAN" ] || return 1
    [ "$(jsonval "$PLAN" '@.manager')" = apk ] &&
    [ "$(jsonval "$PLAN" '@.ready')" = true ] || return 1
    apk_ownership_baseline_ok || return 1
    [ "$(jsonval "$PLAN" '@.old_version')" = "$(apk_pkgversion)" ] || return 1
    [ "$(jsonval "$PLAN" '@.old_binary')" = "$(sha256sum "$BINARY" | awk '{print $1}')" ] || return 1
    when=$(jsonval "$PLAN" '@.checked_at')
    case "$when" in ''|*[!0-9]*) return 1;; esac
    now=$(date +%s)
    [ "$now" -ge "$when" ] && [ $((now-when)) -le 3600 ] || return 1
    tag=$(jsonval "$PLAN" '@.upstream_tag')
    valid_tag "$tag" || return 1
    [ "$(jsonval "$PLAN" '@.build_tag')" = "$(apk_release_tag "$tag")" ] || return 1
    candidate=$(build_version "$tag") || return 1
    [ "$(jsonval "$PLAN" '@.package_version')" = "$candidate" ] || return 1
    filename=$(printf 'naiveproxy_%s_aarch64_cortex-a53.apk' "$candidate")
    [ "$(jsonval "$PLAN" '@.filename')" = "$filename" ] || return 1
    [ "$(jsonval "$PLAN" '@.baseline_filename')" = "$APK_ORIG_FILE" ] || return 1
    for key in sha256 binary_sha256 baseline_sha256; do
        valid_hash "$(jsonval "$PLAN" "@.$key")" || return 1
    done
}
apk_check() {
    create_dirs || return 1
    rm -f "$PLAN"
    [ ! -r "$TXN" ] || {
        check_msg recovery_required 'Previous APK transaction must be recovered first'
        return 1
    }
    apk_ownership_baseline_ok || {
        check_msg unsupported 'Native APK package ownership or installed firmware does not match the verified AX6S baseline'
        return 1
    }
    apk_tmp_ok || { check_msg unsupported 'Insufficient temporary space for APK verification'; return 1; }
    download https://api.github.com/repos/klzgrad/naiveproxy/releases/latest "$CACHE/official.tmp" ||
        { check_msg error 'Official GitHub API unavailable'; return 1; }
    mv -f "$CACHE/official.tmp" "$CACHE/official.json" || return 1
    tag=$(jsonval "$CACHE/official.json" '@.tag_name')
    valid_tag "$tag" || { check_msg error 'Unexpected official release tag'; return 1; }
    desired=$(build_version "$tag") ||
        { check_msg error 'Unsupported official release version'; return 1; }
    build=$(apk_release_tag "$tag")
    download "https://api.github.com/repos/$GITHUB/releases/tags/$build" "$CACHE/apk-release.tmp" ||
        { check_msg pending 'Cloud APK package is being prepared'; return 0; }
    mv -f "$CACHE/apk-release.tmp" "$CACHE/apk-release.json" || return 1
    [ "$(jsonval "$CACHE/apk-release.json" '@.tag_name')" = "$build" ] ||
        { check_msg error 'APK release identity mismatch'; return 1; }
    msha=$(release_digest "$CACHE/apk-release.json" manifest.json)
    valid_hash "$msha" || { check_msg error 'Missing APK manifest checksum'; return 1; }
    download "https://github.com/$GITHUB/releases/download/$build/manifest.json" "$CACHE/apk-manifest.tmp" ||
        { check_msg error 'APK manifest download failed'; return 1; }
    check_sha "$CACHE/apk-manifest.tmp" "$msha" ||
        { check_msg error 'APK manifest hash mismatch'; return 1; }
    mv -f "$CACHE/apk-manifest.tmp" "$CACHE/apk-manifest.json" || return 1
    manifest="$CACHE/apk-manifest.json"
    [ "$(jsonval "$manifest" '@.schema')" = 2 ] &&
    [ "$(jsonval "$manifest" '@.component')" = naiveproxy ] &&
    [ "$(jsonval "$manifest" '@.platform')" = mediatek/mt7622 ] &&
    [ "$(jsonval "$manifest" '@.architecture')" = aarch64_cortex-a53 ] &&
    [ "$(jsonval "$manifest" '@.firmware_release')" = 2026.11.17-2044-AX6S-MTK ] &&
    [ "$(jsonval "$manifest" '@.upstream_tag')" = "$tag" ] &&
    [ "$(jsonval "$manifest" '@.release_tag')" = "$build" ] &&
    [ "$(jsonval "$manifest" '@.opkg_release_tag')" = "component-naiveproxy-$tag-upx521-r3" ] ||
        { check_msg error 'APK manifest platform mismatch'; return 1; }
    filename=$(printf 'naiveproxy_%s_aarch64_cortex-a53.apk' "$desired")
    [ "$(jsonval "$manifest" '@.candidate.filename')" = "$filename" ] &&
    [ "$(jsonval "$manifest" '@.candidate.version')" = "$desired" ] &&
    [ "$(jsonval "$manifest" '@.candidate.init_sha256')" = "$APK_INIT_SHA" ] &&
    [ "$(jsonval "$manifest" '@.original.filename')" = "$APK_ORIG_FILE" ] &&
    [ "$(jsonval "$manifest" '@.original.version')" = "$APK_OLD_VERSION" ] &&
    [ "$(jsonval "$manifest" '@.original.binary_sha256')" = "$APK_OLD_SHA" ] &&
    [ "$(jsonval "$manifest" '@.original.init_sha256')" = "$APK_INIT_SHA" ] &&
    [ "$(jsonval "$manifest" '@.original.config_sha256')" = "$APK_CONFIG_SHA" ] ||
        { check_msg error 'APK baseline recovery identity mismatch'; return 1; }
    digest=$(jsonval "$manifest" '@.candidate.sha256')
    binary=$(jsonval "$manifest" '@.candidate.binary_sha256')
    original=$(jsonval "$manifest" '@.original.sha256')
    for h in "$digest" "$binary" "$original"; do
        valid_hash "$h" || { check_msg error 'Invalid native APK SHA256'; return 1; }
    done
    [ "$(release_digest "$CACHE/apk-release.json" "$filename")" = "$digest" ] &&
    [ "$(release_digest "$CACHE/apk-release.json" "$APK_ORIG_FILE")" = "$original" ] ||
        { check_msg error 'APK asset digest does not match Release API'; return 1; }
    baseline_bytes=$(apk_asset_bytes "$CACHE/apk-release.json" "$APK_ORIG_FILE") ||
        { check_msg error 'APK recovery asset size unavailable'; return 1; }
    candidate_bytes=$(apk_asset_bytes "$CACHE/apk-release.json" "$filename") ||
        { check_msg error 'APK candidate asset size unavailable'; return 1; }
    if [ "$(apk_pkgversion)" = "$desired" ] && check_sha "$BINARY" "$binary"; then
        check_msg up_to_date 'Installed native APK matches latest official binary'
        return 0
    fi
    # Read exact new ELF size before promising an installable candidate.
    # SHA256 must match the verified release metadata before APK extraction.
    rm -f "$CACHE/apk-candidate-verified.apk"
    download "https://github.com/$GITHUB/releases/download/$build/$filename" "$CACHE/apk-candidate-verified.apk" ||
        { check_msg error 'APK candidate download failed'; return 1; }
    check_sha "$CACHE/apk-candidate-verified.apk" "$digest" ||
        { rm -f "$CACHE/apk-candidate-verified.apk"; check_msg error 'APK candidate hash mismatch'; return 1; }
    real_size=$(wc -c < "$CACHE/apk-candidate-verified.apk" | tr -d ' ')
    [ "$real_size" = "$candidate_bytes" ] ||
        { rm -f "$CACHE/apk-candidate-verified.apk"; check_msg error 'APK candidate size mismatch'; return 1; }
    binary_bytes=$(apk_candidate_binary_bytes "$CACHE/apk-candidate-verified.apk" "$binary") ||
        { check_msg error 'APK candidate extraction or binary verification failed'; return 1; }
    apk_overlay_budget_ok "$baseline_bytes" "$candidate_bytes" "$binary_bytes" ||
        { check_msg unsupported 'Insufficient space for APK backup'; return 1; }
    json_init
    json_add_string manager apk
    json_add_string ready true
    json_add_string upstream_tag "$tag"
    json_add_string build_tag "$build"
    json_add_string package_version "$desired"
    json_add_string old_version "$(apk_pkgversion)"
    json_add_string old_binary "$(sha256sum "$BINARY" | awk '{print $1}')"
    json_add_string filename "$filename"
    json_add_string sha256 "$digest"
    json_add_string binary_sha256 "$binary"
    json_add_string baseline_filename "$APK_ORIG_FILE"
    json_add_string baseline_sha256 "$original"
    json_add_string baseline_bytes "$baseline_bytes"
    json_add_string candidate_bytes "$candidate_bytes"
    json_add_string binary_bytes "$binary_bytes"
    json_add_string checked_at "$(date +%s)"
    json_dump > "$PLAN.tmp.$$" || return 1
    mv -f "$PLAN.tmp.$$" "$PLAN" || return 1
    check_msg ready 'Verified native APK is ready for manual installation'
}
apk_receipt_write() {
    json_init
    json_add_string manager apk
    json_add_string upstream_tag "$1"
    json_add_string build_tag "$2"
    json_add_string package_version "$3"
    json_add_string package_sha256 "$4"
    json_add_string binary_sha256 "$5"
    json_add_string previous_backup "$6"
    json_add_string installed_at "$(date +%s)"
    json_dump > "$RECEIPT.tmp.$$" || return 1
    mv -f "$RECEIPT.tmp.$$" "$RECEIPT"
}
apk_restore() {
    rid=$1
    case "$rid" in ''|*[!0-9-]*) return 1;; esac
    rd="$BACKUPS/$rid"
    for n in previous.apk previous.sha256 version binary.sha256 config.sha256 config-original world world.sha256; do
        [ -f "$rd/$n" ] && [ ! -L "$rd/$n" ] || return 1
    done
    oldsha=$(cat "$rd/previous.sha256")
    valid_hash "$oldsha" && check_sha "$rd/previous.apk" "$oldsha" || return 1
    worldsum=$(cat "$rd/world.sha256")
    valid_hash "$worldsum" && check_sha "$rd/world" "$worldsum" || return 1
    apk --no-network --allow-untrusted --no-scripts --no-commit-hooks add \
        "$rd/previous.apk" > "$rd/restore.log" 2>&1 || return 1
    cp -p "$rd/config-original" /etc/config/naiveproxy || return 1
    # APK 'add <localfile>' pins a content hash into /etc/apk/world even
    # when replacing an already installed package. Preserve the pre-update
    # firmware world exactly so future repository upgrades are not blocked.
    cp -p "$rd/world" /etc/apk/world || return 1
    check_sha /etc/apk/world "$worldsum" || return 1
    [ "$(apk_pkgversion)" = "$(cat "$rd/version")" ] &&
    check_sha "$BINARY" "$(cat "$rd/binary.sha256")" &&
    check_sha /etc/config/naiveproxy "$(cat "$rd/config.sha256")" &&
    check_sha /etc/init.d/naiveproxy "$APK_INIT_SHA" &&
    apk_owned_files_ok || return 1
    if [ -s "$rd/receipt.json" ]; then
        cp "$rd/receipt.json" "$RECEIPT" || return 1
        # Reuse the already-verified rollback package without copying
        # another full APK into the small persistent overlay.
        ln "$rd/previous.apk" "$APK_ACTIVE.tmp.$$" &&
        mv -f "$APK_ACTIVE.tmp.$$" "$APK_ACTIVE" || return 1
    else
        rm -f "$RECEIPT" "$APK_ACTIVE"
    fi
    rm -f "$TXN" "$PLAN"
}
apk_perform() {
    apk_plan_ok || { job_record failed 'Check for APK updates before installing'; return 1; }
    apk_tmp_ok || { job_record failed 'Insufficient temporary space for APK verification'; return 1; }
    tag=$(jsonval "$PLAN" '@.upstream_tag')
    build=$(jsonval "$PLAN" '@.build_tag')
    newver=$(jsonval "$PLAN" '@.package_version')
    filename=$(jsonval "$PLAN" '@.filename')
    sum=$(jsonval "$PLAN" '@.sha256')
    binary=$(jsonval "$PLAN" '@.binary_sha256')
    oldver=$(apk_pkgversion)
    work="$CACHE/apk-job.$$"
    mkdir -m 700 "$work" || return 1
    job_record downloading 'Downloading native APK with SHA256 verification'
    # The check phase may already have a verified package in tmpfs.
    # It is never trusted without re-verifying its immutable SHA256.
    if [ -f "$CACHE/apk-candidate-verified.apk" ] &&
       check_sha "$CACHE/apk-candidate-verified.apk" "$sum"; then
        cp "$CACHE/apk-candidate-verified.apk" "$work/update.apk" || return 1
    else
        download "https://github.com/$GITHUB/releases/download/$build/$filename" "$work/update.apk" ||
            { job_record failed 'APK download failed'; return 1; }
    fi
    check_sha "$work/update.apk" "$sum" || {
        job_record failed 'APK download or checksum mismatch'
        return 1
    }
    real_size=$(wc -c < "$work/update.apk" | tr -d ' ')
    [ "$real_size" = "$(jsonval "$PLAN" '@.candidate_bytes')" ] ||
        { job_record failed 'APK candidate size changed since check'; return 1; }
    binary_bytes=$(apk_candidate_binary_bytes "$work/update.apk" "$binary") ||
        { job_record failed 'APK candidate extraction or binary verification failed'; return 1; }
    [ "$binary_bytes" = "$(jsonval "$PLAN" '@.binary_bytes')" ] ||
        { job_record failed 'APK binary size changed since check'; return 1; }
    apk_overlay_budget_ok "$(jsonval "$PLAN" '@.baseline_bytes')" "$real_size" "$binary_bytes" ||
        { job_record failed 'Insufficient overlay capacity for APK recovery'; return 1; }
    job_record backing_up 'Preparing complete native APK rollback package'
    id="$(date +%s)-$$"
    bak="$BACKUPS/$id"
    mkdir -m 700 "$bak" || return 1
    oldhash=$(sha256sum "$BINARY" | awk '{print $1}')
    printf '%s\n' "$oldhash" > "$bak/binary.sha256"
    printf '%s\n' "$oldver" > "$bak/version"
    sha256sum /etc/config/naiveproxy | awk '{print $1}' > "$bak/config.sha256"
    [ -f /etc/apk/world ] && [ ! -L /etc/apk/world ] &&
    cp -p /etc/apk/world "$bak/world" &&
    sha256sum /etc/apk/world | awk '{print $1}' > "$bak/world.sha256" &&
    cp -p /etc/config/naiveproxy "$bak/config-original" || {
        job_record failed 'Could not preserve current NaiveProxy files or APK world policy'
        return 1
    }
    [ -r "$RECEIPT" ] && cp "$RECEIPT" "$bak/receipt.json" || true
    if [ "$oldver" = "$APK_OLD_VERSION" ]; then
        baseline=$(jsonval "$PLAN" '@.baseline_filename')
        baseline_sum=$(jsonval "$PLAN" '@.baseline_sha256')
        download "https://github.com/$GITHUB/releases/download/$build/$baseline" "$bak/previous.apk" &&
        check_sha "$bak/previous.apk" "$baseline_sum" || {
            job_record failed 'Verified firmware recovery APK unavailable'
            return 1
        }
    else
        baseline_sum=$(jsonval "$RECEIPT" '@.package_sha256')
        valid_hash "$baseline_sum" && check_sha "$APK_ACTIVE" "$baseline_sum" &&
        ln "$APK_ACTIVE" "$bak/previous.apk" || {
            job_record failed 'Cached previous APK is unavailable'
            return 1
        }
    fi
    printf '%s\n' "$baseline_sum" > "$bak/previous.sha256"
    # Never permit a dependency download, auto service restart or force-broken-world.
    apk --no-network --allow-untrusted --no-scripts --no-commit-hooks \
        --simulate add "$work/update.apk" > "$work/preflight.log" 2>&1 || {
        job_record failed 'Native APK solver rejected update before changes'
        return 1
    }
    json_init
    json_add_string manager apk
    json_add_string backup_id "$id"
    json_add_string original_version "$oldver"
    json_add_string intended_version "$newver"
    json_dump > "$TXN.tmp.$$" || return 1
    mv -f "$TXN.tmp.$$" "$TXN" || return 1
    sync
    job_record installing 'Installing native APK; PassWall will not be restarted'
    if ! apk --no-network --allow-untrusted --no-scripts --no-commit-hooks add \
            "$work/update.apk" > "$work/install.log" 2>&1 ||
       ! cp -p "$bak/world" /etc/apk/world ||
       ! check_sha /etc/apk/world "$(cat "$bak/world.sha256")" ||
       [ "$(apk_pkgversion)" != "$newver" ] ||
       ! check_sha "$BINARY" "$binary" ||
       ! check_sha /etc/config/naiveproxy "$(cat "$bak/config.sha256")" ||
       ! check_sha /etc/init.d/naiveproxy "$APK_INIT_SHA" ||
       ! apk_owned_files_ok; then
        if apk_restore "$id"; then
            job_record rolled_back 'APK install failed; previous package restored'
        else
            job_record recovery_required 'APK install failed; recovery files retained'
        fi
        return 1
    fi
    if ! cp "$work/update.apk" "$APK_ACTIVE.tmp.$$" ||
       ! mv -f "$APK_ACTIVE.tmp.$$" "$APK_ACTIVE" ||
       ! apk_receipt_write "$tag" "$build" "$newver" "$sum" "$binary" "$id"; then
        if apk_restore "$id"; then
            job_record rolled_back 'APK receipt write failed; previous restored'
        else
            job_record recovery_required 'APK receipt write failed; recovery files retained'
        fi
        return 1
    fi
    rm -f "$TXN" "$PLAN"
    job_record completed 'Native APK installed; PassWall not restarted'
    ls -1 "$BACKUPS" 2>/dev/null | LC_ALL=C sort -r | awk 'NR>2' |
        while IFS= read -r stale; do
            case "$stale" in ''|*[!0-9-]*) continue;; esac
            rm -rf "$BACKUPS/$stale"
        done
}
apk_rollback() {
    create_dirs || return 1
    lock="$CACHE/update.lock"
    mkdir "$lock" 2>/dev/null || { json_msg busy 'Update or rollback in progress'; return 1; }
    trap 'rmdir "$lock" 2>/dev/null || true' EXIT
    ax6s_apk_target || { json_msg unsupported 'APK recovery is AX6S-only'; return 1; }
    if [ -r "$TXN" ]; then
        [ "$(jsonval "$TXN" '@.manager')" = apk ] || return 1
        id=$(jsonval "$TXN" '@.backup_id')
    else
        [ "$(jsonval "$RECEIPT" '@.manager')" = apk ] || return 1
        id=$(jsonval "$RECEIPT" '@.previous_backup')
    fi
    if apk_restore "$id"; then
        job_record rolled_back 'Original APK version and configuration restored'
        json_msg rolled_back 'Previous native APK restored without restarting PassWall'
    else
        job_record recovery_required 'Native APK rollback failed; backup retained'
        json_msg recovery_required 'Verified APK recovery failed; preserved files remain available'
        return 1
    fi
}
