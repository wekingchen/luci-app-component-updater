"""AX6S 2026-11-17 release support: APK is not opkg, fail closed.

These checks deliberately do not claim native APK NaiveProxy updates are live
until package-owned config, init scripts and rollback are tested on hardware.
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


class Ax6sApkCompatibilityTests(unittest.TestCase):
    def test_exact_release_identity_contract(self):
        self.assertIn('mediatek/mt7622',BACKEND)
        self.assertIn('aarch64_cortex-a53',BACKEND)
        self.assertRegex(BACKEND,r'redmi.router.ax6s')
        self.assertIn('/lib/apk/db',BACKEND)
        self.assertIn('command -v apk',BACKEND)
        self.assertIn("json_add_string compatibility 'ax6s-apk-readonly'",BACKEND)

    def test_all_mutations_are_guarded_before_opkg(self):
        for method in ('check_update','start','run','rollback','perform_install'):
            self.assertRegex(BACKEND,rf'{method}\(\) \{{\s*require_opkg \|\| return 1')
        self.assertIn("json_msg unsupported 'Native APK firmware requires",BACKEND)
        self.assertIn('[ "$(package_manager)" = opkg ]',BACKEND)
        self.assertIn('status) status;;',BACKEND)

    def test_chinese_ui_is_readonly_for_native_apk(self):
        self.assertIn("status.package_manager === 'apk'", UI)
        self.assertIn("已识别红米 AX6S", UI)
        self.assertIn('apkGuard', UI)
        self.assertIn('APK 软件包',UI)
        self.assertIn("Native APK firmware requires a verified",UI)

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
        self.assertIn('luci-app-component-updater-v0.4.0-rc1',CI)
        self.assertIn('APK NaiveProxy install and rollback remain locked',CI)

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
