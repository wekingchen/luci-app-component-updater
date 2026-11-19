#!/bin/sh
# AX6S APKv3: read-only firmware + package ownership baseline.
# Does NOT invoke apk add, remove, upgrade, fix, apk fetch or service restart.
set -u
failures=0
checks=0
pass() { printf '[通过] %s\n' "$1"; checks=$((checks+1)); }
block() { printf '[待处理] %s\n' "$1"; failures=$((failures+1)); }
version_of() {
    sed -n "s/^$1='\([^']*\)'.*/\1/p" /etc/openwrt_release 2>/dev/null | head -n1
}
printf '%s\n' '=== 红米 AX6S · APK 兼容性只读报告 ==='
date -Iseconds 2>/dev/null || date
arch=$(version_of DISTRIB_ARCH)
target=$(version_of DISTRIB_TARGET)
board=$(cat /tmp/sysinfo/board_name 2>/dev/null || true)
printf '架构：%s\n固件平台：%s\n板级标识：%s\n' "$arch" "$target" "$board"
[ "$arch" = aarch64_cortex-a53 ] && pass 'ARM64 架构匹配' || block '架构与目标固件不匹配'
[ "$target" = mediatek/mt7622 ] && pass '目标平台匹配' || block '目标平台与 AX6S 不匹配'
case "$board" in *redmi-router-ax6s*|*redmi_router_ax6s*) pass '板级标识匹配';; *) block '板级标识未确认';; esac
if command -v apk >/dev/null 2>&1 && [ -d /lib/apk/db ]; then
    pass '原生 APK 数据库存在'
    apk --version 2>&1 | head -n2
else
    block '未检测到原生 APK 环境'
fi
if command -v opkg >/dev/null 2>&1; then
    printf '%s\n' '注意：另检测到 opkg，但本固件的 APK 数据库优先，禁止混用安装方式。'
fi
if command -v apk >/dev/null 2>&1; then
    if apk info -e naiveproxy >/dev/null 2>&1; then pass 'NaiveProxy 已登记在 APK 数据库'; else block 'APK 数据库中没有 NaiveProxy'; fi
    printf '\n%s\n' '--- 已安装 NaiveProxy 版本 ---'
    apk --no-network list --installed --manifest naiveproxy 2>&1 | head -n10 || true
    printf '\n%s\n' '--- 当前 APK 软件包拥有的文件 ---'
    apk info -L naiveproxy 2>&1 | head -n60 || true
    printf '\n%s\n' '--- 程序文件归属 ---'
    apk info -W /usr/bin/naive 2>&1 | head -n10 || true
fi
for file in /usr/bin/naive /etc/init.d/naiveproxy /etc/config/naiveproxy; do
    if [ -f "$file" ] && [ ! -L "$file" ]; then
        pass "存在普通文件：$file"
        sha256sum "$file" 2>/dev/null || true
    else
        block "文件不存在或不是普通文件：$file"
    fi
done
printf '\n%s\n' '--- 当前可执行程序版本 ---'
/usr/bin/naive --version 2>&1 | head -n2 || true
printf '\n%s\n' '--- 管理器安装与 RPC 接口 ---'
if [ -x /usr/sbin/component-updaterctl ]; then
    /usr/sbin/component-updaterctl status
else
    block '尚未安装组件更新器'
fi
if command -v ubus >/dev/null 2>&1; then
    ubus -v list component-updater 2>&1 || true
fi
printf '\n%s\n' '--- 可用空间 ---'
df -h /overlay /tmp 2>/dev/null || true
printf '\n完成：符合项 %s，待确认项 %s。所有操作均为只读；未修改任何软件包。\n' "$checks" "$failures"
[ "$failures" -eq 0 ]
