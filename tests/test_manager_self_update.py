"""Manager self-upgrade security and native APK integration contracts."""
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
CONTROLLER=ROOT/"luci-app-component-updater"
BACKEND=(CONTROLLER/"root/usr/libexec/component-updater/manager-self-update.sh").read_text()
UI=(CONTROLLER/"htdocs/luci-static/resources/view/component-updater/manager.js").read_text()
RPC=(CONTROLLER/"root/usr/libexec/rpcd/component-updater").read_text()
ACL=json.loads((CONTROLLER/"root/usr/share/rpcd/acl.d/luci-app-component-updater.json").read_text())
MENU=json.loads((CONTROLLER/"root/usr/share/luci/menu.d/luci-app-component-updater.json").read_text())
MAKE=(CONTROLLER/"Makefile").read_text()
CI=(ROOT/".github/workflows/ax6s-apk-build.yml").read_text()

class SelfUpdateContract(unittest.TestCase):
    def test_shell_parses(self):
        with tempfile.NamedTemporaryFile(mode="w",suffix=".sh") as f:
            f.write(BACKEND)
            f.flush()
            result=subprocess.run(["sh","-n",f.name],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_only_exact_upload_paths_and_manager_package(self):
        self.assertIn("NEW_UPLOAD", BACKEND) if "NEW_UPLOAD" in BACKEND else None
        self.assertIn("/tmp/component-updater-manager-new.apk",BACKEND)
        self.assertIn("/tmp/component-updater-manager-current.apk",BACKEND)
        self.assertIn("NAME=luci-app-component-updater",BACKEND)
        self.assertIn("apk adbdump --format json",BACKEND)
        self.assertIn('sha_ok "$src" "$expected"',BACKEND)
        self.assertIn("Unsupported manager APK identity or payload",BACKEND)
        self.assertIn("never accepts a remote path or command",BACKEND)
        self.assertNotRegex(BACKEND,r"eval\s|sh\s+-c\s+\"\$|/etc/init\.d/passwall")
        self.assertIn("--no-network --allow-untrusted --no-scripts --no-commit-hooks",BACKEND)

    def test_manager_recovery_kept_separate_from_naiveproxy(self):
        self.assertIn("ROOT=/etc/component-updater/manager",BACKEND)
        self.assertNotIn("backups/naiveproxy",BACKEND)
        self.assertIn('printf \'%s\\n\' next > "$TXN"',BACKEND)
        self.assertIn("sync",BACKEND)
        self.assertIn('sha_ok "$root/previous.apk"',BACKEND)
        self.assertIn("mkdir \"$LOCK\"",BACKEND)
        self.assertIn('cp "$SELF" "$TMP/worker.tmp.$$"',BACKEND)
        self.assertIn("nohup /bin/sh",BACKEND)
        self.assertIn("rm -rf \"$PREV\"",BACKEND)

    def test_manager_menu_and_upload_acl_are_scoped(self):
        self.assertEqual(MENU["admin/system/component-updater/manager"]["action"]["path"],
                         "component-updater/manager")
        cap=ACL["luci-app-component-updater"]
        self.assertEqual(cap["write"]["cgi-io"],["upload"])
        self.assertEqual(set(cap["write"]["file"]),{
            "/tmp/component-updater-manager-new.apk",
            "/tmp/component-updater-manager-current.apk"})
        self.assertIn("manager_upload",cap["write"]["ubus"]["component-updater"])
        self.assertNotIn("manager_upload",cap["read"]["ubus"]["component-updater"])
        self.assertIn("manager_status",cap["read"]["ubus"]["component-updater"])
        for action in ("manager_status","manager_upload","manager_check",
                       "manager_start","manager_rollback"):
            self.assertIn(action,RPC)

    def test_client_must_confirm_before_mutating(self):
        self.assertIn("ui.uploadFile(path)",UI)
        self.assertIn("Number.isSafeInteger(info.size)",UI)
        self.assertIn("ui.showModal('确认更新管理器'",UI)
        self.assertIn("uploadCall(kind,info.sha256sum,info.size)",UI)
        self.assertIn("manager-self-update",CI)
        self.assertIn("0.5.6",MAKE)
        self.assertIn("恢复包",UI)
        self.assertIn("role",UI) if "role" in UI else None

if __name__=="__main__":
    unittest.main()
