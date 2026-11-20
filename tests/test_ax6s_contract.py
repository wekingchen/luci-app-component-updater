"""AX6S 2026-11-17 release support: APK is not opkg, fail closed.

Native APK update support is gated on exact firmware, package ownership,
verified source and rollback. Cloud chroot verification cannot replace a
live AX6S device acceptance.
"""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
BACKEND=(ROOT/'luci-app-component-updater/root/usr/sbin/component-updaterctl').read_text()
MANAGER=(ROOT/'tools/package_manager_apk.sh').read_text()
CI=(ROOT/'.github/workflows/ci.yml').read_text()
PREFLIGHT=(ROOT/'scripts/device-ax6s-apk-preflight.sh').read_text()
BUNDLED=(ROOT/'luci-app-component-updater/root/usr/libexec/component-updater/device-ax6s-apk-preflight.sh').read_text()
UI=(ROOT/'luci-app-component-updater/htdocs/luci-static/resources/view/component-updater/overview.js').read_text()
NATIVE=(ROOT/'luci-app-component-updater/root/usr/libexec/component-updater/ax6s-apkctl.sh').read_text()
BUILDER=(ROOT/'tools/build_ax6s_apk_assets.py').read_text()
APKACTION=(ROOT/'.github/workflows/ax6s-apk-build.yml').read_text()


class Ax6sApkCompatibilityTests(unittest.TestCase):
    def test_exact_release_identity_contract(self):
        self.assertIn('mediatek/mt7622',BACKEND)
        self.assertIn('aarch64_cortex-a53',BACKEND)
        self.assertRegex(BACKEND,r'redmi.router.ax6s')
        self.assertIn('/lib/apk/db',BACKEND)
        self.assertIn('command -v apk',BACKEND)
        self.assertIn("json_add_string compatibility 'ax6s-apk-native'",BACKEND)

    def test_all_mutations_are_guarded_before_opkg(self):
        self.assertIn('load_apk_backend',BACKEND)
        self.assertIn('apk_check',BACKEND)
        self.assertIn('apk_perform',BACKEND)
        self.assertIn('apk_rollback',BACKEND)
        self.assertIn('require_opkg || return 1',BACKEND)
        self.assertIn("json_msg unsupported 'Native APK firmware requires",BACKEND)
        self.assertIn('[ "$(package_manager)" = opkg ]',BACKEND)
        self.assertIn('status) status;;',BACKEND)

    def test_chinese_ui_supports_native_apk_and_rejects_unknown_firmware(self):
        self.assertIn("status.package_manager === 'apk'", UI)
        self.assertIn("已识别红米 AX6S", UI)
        self.assertIn('apkGuard', UI)
        self.assertIn('APK 软件包',UI)
        self.assertIn("Verified native APK is ready",UI)

    def test_signed_release_does_not_enable_unsafe_install(self):
        self.assertIn('"$APK_TOOL" mkpkg',MANAGER)
        self.assertIn('--info "arch:noarch"',MANAGER)
        self.assertIn('conffiles_static',MANAGER)
        self.assertIn('post-upgrade',MANAGER)
        self.assertIn('depends:luci-base rpcd jsonfilter libubox',MANAGER)
        self.assertNotIn('--allow-untrusted',MANAGER,
                         'Packaging must not silently install anything on the device')
        self.assertIn('apk adbdump --format json',CI)
        self.assertIn('dist/*.apk',CI)
        self.assertIn('luci-app-component-updater-v0.5.6-rc3',CI)
        self.assertIn('NaiveProxy component update/rollback, live PassWall traffic and power-loss recovery remain unverified on physical hardware',CI)
        self.assertIn('AX6S physical-router web manager upgrade r3 -> test-only r4 -> r3 rollback passed',CI)
        self.assertIn('--prerelease',CI)
        self.assertIn("vars.AX6S_APK_AUTO_PUBLISH == 'true'",CI)

    def test_apk_manifest_transport_and_digest_are_separate_fail_closed_paths(self):
        self.assertIn("check_msg error 'APK manifest download failed'", NATIVE)
        self.assertIn("check_msg error 'APK manifest hash mismatch'", NATIVE)
        self.assertRegex(
            NATIVE,
            r'(?s)download "https://github[.]com/\$GITHUB/releases/download/\$build/manifest[.]json".*?APK manifest download failed.*?check_sha.*?APK manifest hash mismatch')
        self.assertIn("'APK manifest download failed':", UI)
        self.assertIn("'APK manifest hash mismatch':", UI)

    def test_low_overlay_budget_is_measured_not_fixed_16mb(self):
        import subprocess
        import tempfile
        import os
        import shlex
        text=NATIVE.split('apk_overlay_budget_ok() {',1)[1].split('\napk_plan_ok() {',1)[0]
        with tempfile.TemporaryDirectory() as td:
            binary=Path(td)/'naive'
            binary.write_bytes(b'x' * (3400*1024))
            receipt=Path(td)/'receipt.json'
            active=Path(td)/'active.apk'
            script=('apk_overlay_budget_ok() {'+text+'\n'
                    +f'BINARY={shlex.quote(str(binary))}\n'
                    +f'RECEIPT={shlex.quote(str(receipt))}\n'
                    +f'APK_ACTIVE={shlex.quote(str(active))}\n'
                    +'df() { printf "Filesystem 1024-blocks Used Available Capacity Mounted\n"; '
                    'printf "/overlay 14746 2146 %s 15%% /\n" "$FREE_KIB"; }\n'
                    +'binary_bytes=3210000\n'
                    +'apk_overlay_budget_ok 3969118 3218562 "$binary_bytes"\n'
                    +'rc=$?\n'
                    +'[ "$binary_bytes" = 3210000 ] || exit 77\n'
                    +'exit "$rc"\n')
            def test(free_kib,receipt_present=False):
                if receipt_present:
                    receipt.write_text('{}')
                    active.write_text('verified-archive')
                else:
                    receipt.unlink(missing_ok=True)
                    active.unlink(missing_ok=True)
                return subprocess.run(['/bin/sh','-c',script],
                                      env={**os.environ,'FREE_KIB':str(free_kib)},
                                      capture_output=True,text=True).returncode
            self.assertEqual(test(12600),0,
                             '12.3 MiB must be tested against exact APK/ELF sizes, not a fixed 16 MiB')
            self.assertNotEqual(test(9000),0,
                                'genuinely insufficient flash must still reject update')
            self.assertEqual(test(9000,True),0,
                             'a verified hardlink must not be charged as a duplicate APK')
            # Measured from the original SHA256-pinned AX6S firmware rootfs.
            # An exact budget must *reject* 12.3 MiB when restoring the real
            # uncompressed 7,771,744-byte original ELF could exhaust flash.
            binary.write_bytes(b'x' * 7771744)
            self.assertNotEqual(test(12600),0,
                                '12.3 MiB cannot guarantee original AX6S APK+ELF rollback')
            self.assertEqual(test(18000),0,
                             'sufficient persistent overlay should enable normal update')
            self.assertIn("check_msg storage_limited 'Insufficient space for APK backup'",NATIVE)
            self.assertIn("current_elf=$(wc -c",NATIVE)
            self.assertIn("ln \"$APK_ACTIVE\" \"$bak/previous.apk\"",NATIVE)
            self.assertIn("ln \"$rd/previous.apk\" \"$APK_ACTIVE.tmp.$$",NATIVE)
            self.assertNotIn('cp -p "$BINARY" "$bak/naive-old"',NATIVE)
            self.assertNotIn('cp "$APK_ACTIVE" "$bak/active.apk"',NATIVE)

    def test_world_constraints_remain_unchanged_after_native_apk_transactions(self):
        self.assertIn('cp -p /etc/apk/world "$bak/world"',NATIVE)
        self.assertIn('cp -p "$bak/world" /etc/apk/world',NATIVE)
        self.assertIn('cp -p "$rd/world" /etc/apk/world',NATIVE)
        self.assertIn('check_sha /etc/apk/world "$worldsum"',NATIVE)
        self.assertIn('world world.sha256',NATIVE)
        self.assertIn('--no-network --allow-untrusted --no-scripts --no-commit-hooks',NATIVE)
        self.assertNotIn('/etc/init.d/passwall restart',NATIVE)

    def test_future_release_cloud_build_and_hardware_release_gate(self):
        self.assertIn('workflow_run:',APKACTION)
        self.assertIn("head_branch == 'main'",APKACTION)
        self.assertIn("head_repository.full_name == github.repository",APKACTION)
        self.assertIn("github.event.workflow_run.event != 'pull_request'",APKACTION)
        self.assertIn("AX6S_APK_AUTO_PUBLISH == 'true'",APKACTION)
        self.assertIn('native-arm64-controller:',APKACTION)
        self.assertIn('component-naiveproxy-$upstream-upx521-r3',APKACTION)
        self.assertIn('source/manifest.json',APKACTION)
        self.assertIn('apk-tools',APKACTION)
        self.assertIn('BASE_SHA',BUILDER)
        self.assertIn('apk_restore',NATIVE)
        self.assertIn('apk_rollback',NATIVE)

    def test_readonly_preflight_never_modifies_packages_or_services(self):
        self.assertEqual(PREFLIGHT,BUNDLED)
        self.assertIn('apk info -L naiveproxy',PREFLIGHT)
        self.assertIn('apk info -W /usr/bin/naive',PREFLIGHT)
        self.assertIn('sha256sum "$file"',PREFLIGHT)
        self.assertIn('/etc/init.d/naiveproxy',PREFLIGHT)
        self.assertIn('/etc/config/naiveproxy',PREFLIGHT)
        self.assertNotRegex(PREFLIGHT,r'^\s*apk\s+(add|del|upgrade|fix|fetch)\b', 'preflight must not mutate', )
        self.assertNotIn('/etc/init.d/rpcd restart',PREFLIGHT)

if __name__=='__main__':
    unittest.main()
