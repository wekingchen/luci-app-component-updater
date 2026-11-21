"""Scoped V0.5.6 stable manual publication safeguards."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
WF=(ROOT/'.github/workflows/manual-manager-v0.5.6-stable.yml').read_text()
GATES=(ROOT/'docs/acceptance-gates.md').read_text()
class ScopedStableContracts(unittest.TestCase):
    def test_manual_gate(self):
        for value in ('workflow_dispatch:', 'PUBLISH_0.5.6_STABLE', 'refs/heads/main'):
            self.assertIn(value, WF)
        for forbidden in ('  push:', '  schedule:', 'pull_request:', 'AX6S_APK_AUTO_PUBLISH =='):
            self.assertNotIn(forbidden, WF)
    def test_pinned_assets_and_immutable_public_release(self):
        for value in ('91008d098080552e8579872ec52f1bb9cb87b366', '44898618719', '14705110670',
                      'sha256:2f61569d4c6a078ec55f5eb9a750537e14f722bad2a1ddb626031f0c29378637',
                      'luci-app-component-updater_0.5.6-3_all.ipk',
                      'luci-app-component-updater-0.5.6-r3.apk',
                      'sha256sum -c SHA256SUMS.txt', 'gh release view', '--latest --notes-file',
                      '.prerelease == false'):
            self.assertIn(value, WF)
        for forbidden in ('gh release delete', 'gh release upload', '--prerelease'):
            self.assertNotIn(forbidden, WF)
    def test_honest_hardware_scope(self):
        self.assertIn('N1 physical testing is not required for this release', WF)
        self.assertIn('Complete three-stage IPK command logs were not archived', WF)
        self.assertIn('N1 不在 V0.5.6 Stable 的强制真机验收范围内', GATES)
if __name__ == '__main__':
    unittest.main()
