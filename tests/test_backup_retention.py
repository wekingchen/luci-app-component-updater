"""Bounded offline rollback retention for both OPKG/IPK and APKv3.

The previous implementation kept the lexicographically newest two folders.
That could discard a referenced rollback when newer interrupted attempts
left orphan folders. Exercise the actual POSIX shell function in isolation.
"""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = (ROOT / "luci-app-component-updater/root/usr/sbin/component-updaterctl").read_text()
APK = (ROOT / "luci-app-component-updater/root/usr/libexec/component-updater/ax6s-apkctl.sh").read_text()
FUNCTION = "prune_backup_chain() {" + CONTROLLER.split(
    "prune_backup_chain() {", 1
)[1].split("\nconfig_get() {", 1)[0]


class BackupRetentionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.backups = self.base / "backups"
        self.backups.mkdir()
        self.receipt = self.base / "receipt.json"
        self.txn = self.base / "transaction.json"

    def archive(self, name, previous=None):
        folder = self.backups / name
        folder.mkdir()
        (folder / "previous.apk").write_bytes(b"verified old package")
        if previous is not None:
            (folder / "receipt.json").write_text(json.dumps(
                {"previous_backup": previous}
            ))
        return folder

    def select(self, backup=None):
        if backup is None:
            self.receipt.unlink(missing_ok=True)
        else:
            self.receipt.write_text(json.dumps({"previous_backup": backup}))

    def prune(self):
        # jsonval() is mocked only for the on-disk receipt field. All
        # directory checks, safety guards and removals run unmodified.
        shell = r"""
jsonval() {
    [ -r "$1" ] || return 0
    sed -n 's/.*"previous_backup"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$1" | head -n 1
}
""" + FUNCTION + """
BACKUPS=$1
RECEIPT=$2
TXN=$3
prune_backup_chain
"""
        return subprocess.run(
            ["/bin/sh", "-xc", shell, "test", str(self.backups),
             str(self.receipt), str(self.txn)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )

    def test_only_referenced_chain_survives_newer_orphan(self):
        self.archive("100-1")
        self.archive("200-2")
        self.archive("300-3", "200-2")
        self.archive("400-4")  # newer but unreferenced failed attempt
        self.select("300-3")
        r = self.prune()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(set(p.name for p in self.backups.iterdir()),
                         {"200-2", "300-3"})

    def test_pending_transaction_never_prunes(self):
        self.archive("100-1")
        self.archive("200-2")
        self.select("100-1")
        self.txn.write_text('{"backup_id":"200-2"}')
        self.assertEqual(self.prune().returncode, 0)
        self.assertEqual(len(list(self.backups.iterdir())), 2)

    def test_verified_restore_to_factory_without_receipt_clears_orphans(self):
        self.archive("100-1")
        self.archive("200-2")
        self.select(None)
        self.assertEqual(self.prune().returncode, 0)
        self.assertEqual(list(self.backups.iterdir()), [])

    def test_corrupted_reference_fails_closed(self):
        self.archive("100-1")
        self.archive("200-2")
        self.select("../200-2")
        self.assertNotEqual(self.prune().returncode, 0)
        self.assertEqual(len(list(self.backups.iterdir())), 2)

    def test_missing_ancestor_fails_closed(self):
        self.archive("100-1", "900-9")
        self.archive("300-3")
        self.select("100-1")
        self.assertNotEqual(self.prune().returncode, 0)
        self.assertTrue((self.backups / "300-3").exists())

    def test_symlinks_never_followed_and_hardlink_survives(self):
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "keep").write_text("protected")
        (self.backups / "500-5").symlink_to(outside, target_is_directory=True)
        orphan = self.archive("100-1")
        active = self.base / "naiveproxy-active.apk"
        active.hardlink_to(orphan / "previous.apk")
        self.select(None)
        self.assertEqual(self.prune().returncode, 0)
        self.assertEqual(active.read_bytes(), b"verified old package")
        self.assertTrue((outside / "keep").exists())
        self.assertTrue((self.backups / "500-5").is_symlink())

    def test_both_backends_use_same_bounded_cleanup(self):
        self.assertIn("prune_backup_chain || true", CONTROLLER)
        self.assertIn("prune_backup_chain || true", APK)
        self.assertIn("if [ ! -r \"$TXN\" ]; then prune_backup_chain", CONTROLLER)
        self.assertNotIn("awk 'NR>2'", CONTROLLER)
        self.assertNotIn("awk 'NR>2'", APK)


if __name__ == "__main__":
    unittest.main()
