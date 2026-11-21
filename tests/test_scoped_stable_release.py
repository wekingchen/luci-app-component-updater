"""V0.5.6 one-time Stable publication is automatic, immutable, and scoped."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
WF=(ROOT/'.github/workflows/auto-manager-v0.5.6-stable.yml').read_text()
class AutoStableContract(unittest.TestCase):
    def test_trusted_ci_trigger_without_manual_input(self):
        for v in ('workflow_run:', 'Component Updater / CI & native IPK/APK',
                  "github.event.workflow_run.conclusion == 'success'",
                  "github.event.workflow_run.head_branch == 'main'",
                  "github.event.workflow_run.event == 'push'",
                  "github.event.workflow_run.head_repository.full_name == github.repository"):
            self.assertIn(v,WF)
        for v in ('workflow_dispatch:', 'inputs.confirm_release', 'CONFIRM_RELEASE',
                  'PUBLISH_0.5.6_STABLE', 'PUBLISH_0.5.6_Stable',
                  'AX6S_APK_AUTO_PUBLISH ==', '  schedule:'):
            self.assertNotIn(v,WF)
    def test_chinese_release_metadata_without_republishing_assets(self):
        notes = (ROOT / 'docs/releases/v0.5.6-zh-CN.md').read_text()
        self.assertIn('LuCI 组件更新器 V0.5.6 正式稳定版', WF)
        self.assertIn('gh release edit', WF)
        self.assertIn('--notes-file "$notes_file"', WF)
        self.assertIn('steps.preflight.outputs.skip == \'true\'', WF)
        self.assertIn('APK_SHA256:', WF)
        self.assertIn('IPK_SHA256:', WF)
        self.assertIn('SUMS_SHA256:', WF)
        self.assertIn('N1 不要求额外实机测试', notes)
        self.assertIn('MT3600BE', notes)
        self.assertIn('AX6S', notes)
        self.assertIn('SHA256SUMS.txt', notes)

    def test_one_time_pinned_artifact_and_fail_closed(self):
        for v in ('91008d098080552e8579872ec52f1bb9cb87b366',
                  '44898618719','14705110670',
                  'sha256:2f61569d4c6a078ec55f5eb9a750537e14f722bad2a1ddb626031f0c29378637',
                  'luci-app-component-updater_0.5.6-3_all.ipk',
                  'luci-app-component-updater-0.5.6-r3.apk',
                  'sha256sum -c SHA256SUMS.txt', 'gh release view',
                  'skip=true','skip=false', "steps.preflight.outputs.skip != 'true'",
                  'gh release create','--latest --notes-file','.prerelease == false'):
            self.assertIn(v,WF)
        for v in ('--prerelease','gh release delete','gh release upload'):
            self.assertNotIn(v,WF)
if __name__=='__main__': unittest.main()
