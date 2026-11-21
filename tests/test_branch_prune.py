"""Prune only branches exactly matching already merged PR heads."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts/prune_merged_branches.py"
spec = importlib.util.spec_from_file_location("branch_cleanup", PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

REPO = "wekingchen/luci-app-component-updater"


def pr(name, sha, number, merged=True, owner=REPO, base="main"):
    return {"head": {"ref": name, "sha": sha, "repo": {"full_name": owner}},
            "base": {"ref": base}, "merged_at": "2026-11-19T00:00:00Z" if merged else None,
            "number": number}


class BranchCleanupTests(unittest.TestCase):
    def test_only_verified_merged_heads_deleted(self):
        current = [
            {"name": "main", "commit": {"sha": "m"}, "protected": False},
            {"name": "feat/merged", "commit": {"sha": "a"}, "protected": False},
            {"name": "feat/reused", "commit": {"sha": "new"}, "protected": False},
            {"name": "fix/protected", "commit": {"sha": "p"}, "protected": True},
            {"name": "feat/open", "commit": {"sha": "o"}, "protected": False},
            {"name": "release/stable", "commit": {"sha": "r"}, "protected": False},
            {"name": "fix/unmerged", "commit": {"sha": "u"}, "protected": False},
            {"name": "feat/external", "commit": {"sha": "e"}, "protected": False}
        ]
        closed = [
            pr("feat/merged", "a", 1), pr("feat/reused", "old", 2),
            pr("fix/protected", "p", 3), pr("feat/open", "o", 4),
            pr("release/stable", "r", 5), pr("fix/unmerged", "u", 6, merged=False),
            pr("feat/external", "e", 7, owner="other/fork")
        ]
        active = [pr("feat/open", "o", 9, merged=False)]
        deletes = []

        def fake_api(path, method="GET"):
            if method == "DELETE":
                deletes.append(path)
                return None
            if "/branches?" in path:
                return current
            if "state=closed" in path:
                return closed
            if "state=open" in path:
                return active
            raise AssertionError(path)

        with patch.dict(mod.os.environ, {"GITHUB_REPOSITORY": REPO}), patch.object(mod, "gh_api", side_effect=fake_api):
            cleaned = mod.clean()
        self.assertEqual(cleaned, ["feat/merged"])
        self.assertEqual(deletes, ["repos/%s/git/refs/heads/feat/merged" % REPO])

    def test_refuses_unrelated_repository(self):
        with patch.dict(mod.os.environ, {"GITHUB_REPOSITORY": "different/repo"}):
            with self.assertRaises(RuntimeError):
                mod.clean()

    def test_only_development_branch_names(self):
        for name in ("main", "release/stable", "dev", "feat/bad name", "feature/test"):
            self.assertIsNone(mod.ALLOWED.fullmatch(name))
        for name in ("fix/v0.3.0-release-sha-filename", "feat/v0.3.0-product-ui-zh"):
            self.assertIsNotNone(mod.ALLOWED.fullmatch(name))


    def test_one_time_release_cleanup_requires_original_head_and_verified_release(self):
        expected = mod.ONE_TIME_V056_RELEASE_BRANCHES
        branches = {
            name: {"name": name, "protected": False, "commit": {"sha": sha}}
            for name, (sha, _) in expected.items()
        }
        merged = [
            pr(name, sha, number)
            for name, (sha, number) in expected.items()
            if number is not None
        ]
        deleted = []
        calls = []

        def fake_api(path, method="GET"):
            calls.append((path, method))
            if method == "DELETE":
                deleted.append(path)
                return None
            if path.endswith("/releases/tags/luci-app-component-updater-v0.5.6"):
                return {
                    "tag_name": "luci-app-component-updater-v0.5.6",
                    "draft": False, "prerelease": False,
                    "assets": [
                        {"name": name, "digest": digest, "state": "uploaded"}
                        for name, digest in mod.ONE_TIME_V056_RELEASE_ASSETS.items()
                    ]
                }
            if "/compare/" in path:
                self.assertIn("91008d098080552e8579872ec52f1bb9cb87b366...main", path)
                return {"status": "ahead", "behind_by": 0}
            raise AssertionError(path)

        with patch.object(mod, "gh_api", side_effect=fake_api):
            cleaned = mod.prune_one_time_v056_release_branches(
                branches, merged, set()
            )
        self.assertEqual(set(cleaned), set(expected))
        self.assertEqual(len(deleted), 3)
        self.assertTrue(all("/git/refs/heads/release/" in p for p in deleted))
        self.assertFalse(mod.ALLOWED.fullmatch("release/stable"))
        # Running the same cleanup after the branches vanish is a safe no-op.
        with patch.object(mod, "gh_api", side_effect=fake_api):
            self.assertEqual(
                mod.prune_one_time_v056_release_branches({}, merged, set()), []
            )

    def test_one_time_release_cleanup_rejects_drift_and_unverified_artifacts(self):
        expected = mod.ONE_TIME_V056_RELEASE_BRANCHES
        names = list(expected)
        branches = {
            names[0]: {"name": names[0], "protected": False,
                       "commit": {"sha": "new-unmerged-work"}},
            names[1]: {"name": names[1], "protected": True,
                       "commit": {"sha": expected[names[1]][0]}},
            names[2]: {"name": names[2], "protected": False,
                       "commit": {"sha": expected[names[2]][0]}},
        }
        merged = [
            pr(name, sha, number)
            for name, (sha, number) in expected.items()
            if number is not None
        ]
        deleted = []
        def fake_api(path, method="GET"):
            if method == "DELETE":
                deleted.append(path)
                return None
            if path.endswith("/releases/tags/luci-app-component-updater-v0.5.6"):
                return {
                    "tag_name": "luci-app-component-updater-v0.5.6",
                    "draft": False, "prerelease": False,
                    "assets": [
                        {"name": name, "digest": digest, "state": "uploaded"}
                        for name, digest in mod.ONE_TIME_V056_RELEASE_ASSETS.items()
                    ]
                }
            if "/compare/" in path:
                return {"status": "diverged", "behind_by": 1}
            raise AssertionError(path)
        with patch.object(mod, "gh_api", side_effect=fake_api):
            self.assertEqual(
                mod.prune_one_time_v056_release_branches(
                    branches, merged, set()), []
            )
        self.assertFalse(deleted)

        def bad_release(path, method="GET"):
            return {
                "tag_name": "luci-app-component-updater-v0.5.6",
                "draft": False, "prerelease": False, "assets": []
            }
        with patch.object(mod, "gh_api", side_effect=bad_release):
            with self.assertRaises(RuntimeError):
                mod.prune_one_time_v056_release_branches(branches, merged, set())


if __name__ == "__main__":
    unittest.main()
