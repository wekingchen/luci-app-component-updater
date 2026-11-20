"""LuCI menu installation hooks: offline, mock-service regression tests.

The AX6S real-device failure was: APK registered in the package database
but no LuCI navigation entry appeared. These checks cover the post-install
gap the ARM64 chroot test missed by using --no-scripts.
"""
import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "tools/manager_postinstall.sh"
APK_BUILDER = ROOT / "tools/package_manager_apk.sh"
IPK_BUILDER = ROOT / "tools/package_ipk.py"
SDK_MAKEFILE = ROOT / "luci-app-component-updater/Makefile"


class MenuActivationTests(unittest.TestCase):
    def test_shell_syntax_and_no_unrelated_service_restart(self):
        subprocess.run(["/bin/sh", "-n", str(HOOK)], check=True)
        script = HOOK.read_text()
        for required in ("IPKG_INSTROOT", "/tmp/luci-indexcache",
                         "/tmp/luci-modulecache", "/etc/init.d/rpcd",
                         "/etc/init.d/uhttpd", "restart"):
            self.assertIn(required, script)
        self.assertNotIn("/etc/init.d/passwall", script)
        self.assertNotIn("/etc/init.d/naiveproxy", script)
        self.assertNotIn("reboot", script.split("set -u", 1)[1])

    def test_postinstall_really_removes_cache_and_restarts_only_luci_services(self):
        script = HOOK.read_text()
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            services = folder / "init.d"
            services.mkdir()
            cache = folder / "cache"
            cache.mkdir()
            (cache / "luci-indexcache").write_text("stale")
            (cache / "luci-indexcache.123").write_text("stale")
            (cache / "luci-modulecache").mkdir()
            (cache / "luci-modulecache" / "module").write_text("stale")
            for name in ("rpcd", "uhttpd"):
                service = services / name
                service.write_text(chr(10).join([
                    "#!/bin/sh",
                    'echo "' + name + ':$1" >> "$MOCK_LOG"',
                    ""
                ]))
                service.chmod(0o755)
            script = script.replace("/tmp/luci-indexcache", str(cache / "luci-indexcache"))
            script = script.replace("/tmp/luci-modulecache", str(cache / "luci-modulecache"))
            script = script.replace("/etc/init.d/rpcd", str(services / "rpcd"))
            script = script.replace("/etc/init.d/uhttpd", str(services / "uhttpd"))
            executable = folder / "postinst"
            executable.write_text(script)
            log = folder / "services.log"
            env = dict(os.environ, MOCK_LOG=str(log))
            # Offline image installation must not mutate services/cache.
            subprocess.run(["/bin/sh", str(executable)], env=dict(env, IPKG_INSTROOT="/staging"),
                           check=True)
            self.assertFalse(log.exists())
            self.assertTrue((cache / "luci-indexcache").exists())

            subprocess.run(["/bin/sh", str(executable)], env=env, check=True)
            self.assertEqual(log.read_text().splitlines(),
                             ["rpcd:restart", "uhttpd:restart"])
            self.assertFalse((cache / "luci-indexcache").exists())
            self.assertFalse((cache / "luci-indexcache.123").exists())
            self.assertFalse((cache / "luci-modulecache" / "module").exists())

            # Repeated post-upgrade must also be safe and idempotent.
            subprocess.run(["/bin/sh", str(executable)], env=env, check=True)
            self.assertEqual(log.read_text().splitlines(),
                             ["rpcd:restart", "uhttpd:restart",
                              "rpcd:restart", "uhttpd:restart"])

    def test_sdk_makefile_also_activates_luci_after_live_install(self):
        content = SDK_MAKEFILE.read_text()
        self.assertIn("define Package/luci-app-component-updater/postinst", content)
        self.assertIn('${IPKG_INSTROOT:-}', content, 'SDK hook must survive GNU Make expansion')
        hook = content.split("define Package/luci-app-component-updater/postinst", 1)[1].split("endef", 1)[0]
        for token in ('IPKG_INSTROOT', '/tmp/luci-indexcache',
                      '/tmp/luci-modulecache', '/etc/init.d/rpcd',
                      '/etc/init.d/uhttpd', 'restart'):
            self.assertIn(token, hook)
        self.assertNotIn('/etc/init.d/passwall', hook)
        self.assertNotIn('reboot', hook)

    def test_both_package_formats_ship_identical_postinstall(self):
        apk_source = APK_BUILDER.read_text()
        self.assertIn('cp "$ROOT/tools/manager_postinstall.sh" "$work/post-install"', apk_source)
        self.assertIn('--script "post-install:$work/post-install"', apk_source)
        self.assertIn('--script "post-upgrade:$work/post-install"', apk_source)

        with tempfile.TemporaryDirectory() as td:
            subprocess.run([sys.executable, str(IPK_BUILDER), "--out", td],
                           check=True, stdout=subprocess.DEVNULL)
            ipk = Path(td) / "luci-app-component-updater_0.5.5-1_all.ipk"
            self.assertTrue(ipk.is_file())
            with tarfile.open(ipk, mode="r:gz") as outer:
                control = outer.extractfile("./control.tar.gz").read()
            with tarfile.open(fileobj=io.BytesIO(control), mode="r:gz") as inner:
                embedded = inner.extractfile("./postinst").read()
            self.assertEqual(embedded, HOOK.read_bytes())


if __name__ == "__main__":
    unittest.main()
