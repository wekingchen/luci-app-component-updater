"""Manual manager RC3 release cannot bypass the stable auto-publish gate."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/manual-manager-rc3-release.yml").read_text()

class ManualRcReleaseContracts(unittest.TestCase):
    def test_dispatch_only_and_authorized(self):
        self.assertIn("workflow_dispatch:", WORKFLOW)
        self.assertIn("inputs.confirm_release", WORKFLOW)
        self.assertIn("refs/heads/main", WORKFLOW)
        self.assertIn("PUBLISH_0.5.6_RC3", WORKFLOW)
        self.assertNotIn("  push:", WORKFLOW)
        self.assertNotIn("  schedule:", WORKFLOW)
        self.assertNotIn("pull_request:", WORKFLOW)

    def test_pinned_successful_ci_artifacts(self):
        self.assertIn("8981a7f8e08b3f788080b36a716a27ec08052b46", WORKFLOW)
        self.assertIn("44897597757", WORKFLOW)
        self.assertIn("14704935350", WORKFLOW)
        self.assertIn("luci-app-component-updater_0.5.6-3_all.ipk", WORKFLOW)
        self.assertIn("luci-app-component-updater-0.5.6-r3.apk", WORKFLOW)
        self.assertIn("gh run download", WORKFLOW)
        self.assertIn("sha256sum -c", WORKFLOW)
        self.assertIn("conclusion == \"success\"", WORKFLOW)

    def test_no_immutable_release_override_or_stable_claim(self):
        self.assertIn("gh release create", WORKFLOW)
        self.assertIn("--latest=false --prerelease", WORKFLOW)
        self.assertIn("SHA256SUMS.txt", WORKFLOW)
        self.assertIn("gh release view", WORKFLOW)
        self.assertNotIn("gh release upload", WORKFLOW)
        self.assertNotIn("gh release delete", WORKFLOW)
        self.assertNotIn("AX6S_APK_AUTO_PUBLISH == 'true'", WORKFLOW)
        self.assertIn("has not yet been evidenced", WORKFLOW)

if __name__ == "__main__":
    unittest.main()
