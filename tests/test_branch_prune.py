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


if __name__ == "__main__":
    unittest.main()
