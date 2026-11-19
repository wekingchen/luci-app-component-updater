"""Regression tests for knowledge/CI contracts and wiki staging."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_docs
import wiki_sync


class GovernanceTests(unittest.TestCase):
    def test_current_knowledge_base(self):
        self.assertEqual(check_docs.validate(ROOT), [])

    def test_broken_wiki_link_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "wiki-src").mkdir()
            (root / "wiki-src" / "Home.md").write_text("# Hi\n[bad](Missing.md)\n")
            self.assertEqual(len(check_docs.link_errors(root, "wiki-src/Home.md", True)), 1)

    def test_accidental_automatic_publish_fails(self):
        ci = (ROOT / ".github/workflows/ci.yml").read_text()
        apk = (ROOT / ".github/workflows/ax6s-apk-build.yml").read_text()
        self.assertEqual(check_docs.release_policy_errors(ci, apk), [])
        self.assertTrue(check_docs.release_policy_errors(
            ci.replace("vars.AX6S_APK_AUTO_PUBLISH == 'true'", "true"), apk))

    def test_wiki_sync_preserves_unknown_pages_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            (dest / "Community.md").write_text("# Keep\n")
            self.assertEqual(
                set(wiki_sync.sync(ROOT / "wiki-src", dest)), set(check_docs.PAGES))
            self.assertEqual(wiki_sync.sync(ROOT / "wiki-src", dest), [])
            self.assertEqual((dest / "Community.md").read_text(), "# Keep\n")

    def test_wiki_sync_rejects_symlink_target(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            (dest / "Home.md").symlink_to(dest / "elsewhere")
            with self.assertRaises(ValueError):
                wiki_sync.sync(ROOT / "wiki-src", dest)


if __name__ == "__main__":
    unittest.main()
