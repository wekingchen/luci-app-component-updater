"""Offline LuCI/rpcd registration and package ABI-independent contracts.

Actual GL-MT3600BE/N1 compatibility still requires device-side verification.
"""
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'luci-app-component-updater'
PLUGIN=APP/'root/usr/libexec/rpcd/component-updater'

class RpcdCompatibilityTests(unittest.TestCase):
    def test_rpcd_executable_list_protocol(self):
        out=subprocess.check_output(['/bin/sh',str(PLUGIN),'list'],text=True)
        methods=json.loads(out)
        self.assertEqual(set(methods),{'status','check','plan','start','rollback'})
        self.assertTrue(all(v=={} for v in methods.values()))

    def test_rpcd_rejects_unregistered_method(self):
        p=subprocess.run(['/bin/sh',str(PLUGIN),'call','arbitrary-shell-command'],
                         capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0)
        self.assertEqual(json.loads(p.stdout)['error'],'unsupported RPC method')

    def test_acl_write_separated_from_read(self):
        acl=json.loads((APP/'root/usr/share/rpcd/acl.d/luci-app-component-updater.json').read_text())
        rule=acl['luci-app-component-updater']
        self.assertEqual(set(rule['read']['ubus']['component-updater']),{'status','check','plan'})
        self.assertEqual(set(rule['write']['ubus']['component-updater']),{'start','rollback'})
        self.assertEqual(rule['read']['uci'],['component-updater'])
        self.assertEqual(rule['write']['uci'],['component-updater'])
        self.assertNotIn('file',str(rule))
        menu=json.loads((APP/'root/usr/share/luci/menu.d/luci-app-component-updater.json').read_text())
        self.assertIn('admin/system/component-updater/settings',menu)

    def test_opkg_package_requires_usign_and_includes_proxy_ui(self):
        with tempfile.TemporaryDirectory() as td:
            subprocess.run([sys.executable,str(ROOT/'tools/package_ipk.py'),'--out',td],check=True,
                           stdout=subprocess.DEVNULL)
            p=Path(td)/'luci-app-component-updater_0.2.0-1_all.ipk'
            control=subprocess.check_output(['ar','p',str(p),'control.tar.gz'])
            with tarfile.open(fileobj=io.BytesIO(control),mode='r:gz') as tar:
                dep=tar.extractfile('./control').read().decode()
            self.assertIn('opkg',dep)
            data=subprocess.check_output(['ar','p',str(p),'data.tar.gz'])
            with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as tar:
                members=set(tar.getnames())
            self.assertIn('./www/luci-static/resources/view/component-updater/settings.js',members)
            self.assertIn('./etc/config/component-updater',members)
            self.assertIn('./usr/libexec/component-updater/device-readonly-acceptance.sh',members)
            self.assertIn('./usr/libexec/component-updater/device-live-acceptance.sh',members)

if __name__=='__main__':
    unittest.main()
