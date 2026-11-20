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
        self.assertIn('luci-app-component-updater-v0.5.5-rc1',CI)
        self.assertIn('Physical AX6S device and live PassWall traffic validation remain outstanding',CI)

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
