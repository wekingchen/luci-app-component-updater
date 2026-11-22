"""Fail-closed contract for the MT3600BE-only one-time IPK candidate."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
WF=(ROOT/'.github/workflows/mt3600be-null-ipk-r4-candidate.yml').read_text(encoding='utf-8')
DOC=(ROOT/'docs/mt3600be-null-ui-r4-candidate.md').read_text(encoding='utf-8')

class MT3600BEHotfixCandidateContract(unittest.TestCase):
    def test_trusted_ci_one_time_trigger(self):
        for s in ('workflow_run:', 'branches: [main]', 'types: [completed]',
                  "github.event.workflow_run.conclusion == 'success'",
                  "github.event.workflow_run.event == 'push'",
                  "github.event.workflow_run.head_repository.full_name == github.repository",
                  'a4c24204bdb84dfa8b4704e5eb51300e0421af34',
                  "SOURCE_CI_RUN: '44986972380'",
                  'gh release view "$TAG"', 'skip=true',
                  'gh api "repos/$GH_REPO/git/ref/tags/$TAG"'):
            self.assertIn(s,WF)
        for bad in ('workflow_dispatch:', 'AX6S_APK_AUTO_PUBLISH ==',
                    'gh release upload', 'gh release delete', 'gh release edit'):
            self.assertNotIn(bad,WF)

    def test_new_revision_no_stable_overwrite(self):
        for s in ('package_ipk.VERSION = "0.5.6-4"',
                  '"Version: 0.5.6-4\\n"',
                  'luci-app-component-updater_0.5.6-4_all.ipk',
                  'luci-app-component-updater-v0.5.6-4-mt3600be-null-fix-rc1',
                  'var toolLinks = [];', 'managerBuild',
                  'sha256sum -c SHA256SUMS.txt',
                  'gh release create "$TAG"',
                  '--prerelease --latest=false'):
            self.assertIn(s,WF)
        for s in ('0.5.6-4', 'MT3600BE', 'SHA256SUMS.txt', '不是 APK'):
            self.assertIn(s,DOC)
        self.assertNotIn('gh release create "luci-app-component-updater-v0.5.6"',WF)

if __name__=='__main__':
    unittest.main()
