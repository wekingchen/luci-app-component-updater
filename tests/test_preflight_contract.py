"""Non-destructive field preflight and current native-IPK release contract."""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/'luci-app-component-updater/root/usr/libexec/component-updater'
LUCI=ROOT/'luci-app-component-updater/htdocs/luci-static/resources/view/component-updater'

class FieldPreflightTests(unittest.TestCase):
    def test_readonly_preflight_requires_native_package_not_signing(self):
        text=(SCRIPTS/'device-readonly-acceptance.sh').read_text()
        self.assertNotIn('trust.pub',text)
        self.assertNotIn('usign',text)
        self.assertIn('opkg status naiveproxy',text)
        self.assertIn('opkg files naiveproxy',text)
        self.assertIn('aarch64_cortex-a53|aarch64_generic',text)
        self.assertIn('ubus -v list component-updater',text)
        self.assertNotRegex(text,r'(^|\n)\s*opkg\s+(install|remove|upgrade)\b')

    def test_live_preflight_requires_explicit_opt_in(self):
        text=(SCRIPTS/'device-live-acceptance.sh').read_text()
        self.assertIn('COMPONENT_ACCEPT_LIVE',text)
        self.assertIn('I_UNDERSTAND',text)
        self.assertIn('--install-and-rollback',text)
        self.assertIn('old_pkg=',text)
        self.assertIn('restored_pkg=',text)
        self.assertNotIn('signed candidate',text)

    def test_luci_copy_does_not_claim_detached_signature(self):
        s=(LUCI/'settings.js').read_text()
        self.assertNotIn('内置公钥签名',s)
        self.assertNotIn('签名文件',s)
        self.assertIn('SHA256',s)
        self.assertIn('API',s)

    def test_preflight_scripts_in_source_package_match_tests(self):
        for name in ('device-readonly-acceptance.sh','device-live-acceptance.sh'):
            external=(ROOT/'scripts'/name).read_bytes()
            bundled=(SCRIPTS/name).read_bytes()
            self.assertEqual(external,bundled)

if __name__=='__main__':
    unittest.main()
