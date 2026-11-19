"""Build artifact, archive-format and install-package contracts.

These tests supplement unit tests: they catch wrong file layouts and incomplete
release manifests before we let a CI-green IPK reach a router.
"""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import component_builder as b
from package_component_ipk import inspect_ipk


def fake_elf(machine=183):
    data=bytearray(96)
    data[0:6]=b'\x7fELF\x02\x01'
    data[18:20]=machine.to_bytes(2,'little')
    return bytes(data)


class ReleaseContractTests(unittest.TestCase):
    def setUp(self):
        self.cfg=b.definitions('naiveproxy')[0]

    def test_no_arbitrary_upstream_host(self):
        with self.assertRaises(b.BuildError):
            b.github_json('https://example.net/latest')
        with self.assertRaises(b.BuildError):
            b.download('https://example.com/payload')

    def test_missing_or_duplicate_release_asset(self):
        with self.assertRaises(b.BuildError):
            b.find_asset({'assets':[]},'a.tar.xz')
        with self.assertRaises(b.BuildError):
            b.find_asset({'assets':[{'name':'a.tar.xz'}, {'name':'a.tar.xz'}]},'a.tar.xz')
        with self.assertRaises(b.BuildError):
            b.find_asset({'assets':[{'name':'a.tar.xz','browser_download_url':'http://evil.test'}]},'a.tar.xz')

    def test_no_fallback_to_missing_sha256(self):
        with self.assertRaises(b.BuildError):
            b.digest_ok(b'hello','')
        with self.assertRaises(b.BuildError):
            b.digest_ok(b'hello','sha256:invalid')

    def test_reject_non_elf_or_wrong_machine(self):
        for v in [b'',b'javascript',fake_elf(62),b'\x7fELF\x01\x01'+bytes(90)]:
            with self.subTest(v=v[:6]):
                with self.assertRaises(b.BuildError):
                    b.verify_elf(v,183)

    def test_reject_traversal_and_links_in_tar(self):
        for item_type, path in [(tarfile.SYMTYPE,'naive'),(tarfile.REGTYPE,'../naive')]:
            with self.subTest(item_type=item_type):
                buf=io.BytesIO()
                with tarfile.open(fileobj=buf,mode='w:xz') as t:
                    i=tarfile.TarInfo(path)
                    i.type=item_type
                    if item_type==tarfile.SYMTYPE:i.linkname='/etc/passwd'
                    else:i.size=1
                    t.addfile(i, io.BytesIO(b'x') if i.size else None)
                with self.assertRaises(b.BuildError):
                    b.extract_member(buf.getvalue(),'naive')

    def test_release_manifest_contains_source_provenance(self):
        elf=fake_elf()
        buf=io.BytesIO()
        with tarfile.open(fileobj=buf,mode='w:xz') as t:
            i=tarfile.TarInfo('directory/naive')
            i.size=len(elf)
            t.addfile(i,io.BytesIO(elf))
        blob=buf.getvalue()
        name=b.source_name(self.cfg,'v154.0.8037.49-5',self.cfg['platforms'][0])
        release={'tag_name':'v154.0.8037.49-5','assets':[{'name':name,'browser_download_url':'https://github.com/foo/bar','digest':'sha256:'+hashlib.sha256(blob).hexdigest()}]}
        with tempfile.TemporaryDirectory() as td, patch.object(b,'download',return_value=blob),patch.object(b,'compress',return_value=elf):
            result=b.build_one(self.cfg,release,self.cfg['platforms'][0],'/fake/upx',Path(td))
            archive=Path(td)/result['filename']
            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(),result['sha256'])
            ctl,packaged=inspect_ipk(archive.read_bytes(),'/usr/bin/naive')
            self.assertEqual(ctl['Package'],'naiveproxy')
            self.assertEqual(ctl['Architecture'],'aarch64_cortex-a53')
            self.assertEqual(ctl['Version'],'154.0.8037.49.5-r3')
            self.assertEqual(packaged,elf)
            self.assertEqual(result['source_sha256'],hashlib.sha256(blob).hexdigest())
            self.assertEqual(result['validation']['device_runtime'],'unverified')

    def test_component_definitions_remain_extensible(self):
        raw=json.loads(json.dumps(self.cfg))
        raw['id']='another-program'
        raw['name']='Future component'
        raw['install']['package']='another-program'
        raw['compression']={'type':'none','revision':1}
        b.validate_definition(raw)
        self.assertEqual(b.release_tag(raw,'v1.2.3'),'component-another-program-v1.2.3-raw-r1')

    def test_manager_package_version_is_consistent(self):
        manager=(ROOT/'luci-app-component-updater/Makefile').read_text()
        wrapper=(ROOT/'tools/package_ipk.py').read_text()
        workflow=(ROOT/'.github/workflows/ci.yml').read_text()
        self.assertIn('PKG_VERSION:=0.3.0',manager)
        self.assertIn('PKG_RELEASE:=1',manager)
        self.assertIn('VERSION = "0.3.0-1"',wrapper)
        self.assertIn('luci-app-component-updater_0.3.0-1_all.ipk',workflow)
        self.assertIn('pkg=luci-app-component-updater_0.3.0-1_all.ipk',workflow)
        self.assertIn('sha256sum "$pkg"',workflow)
        self.assertIn('gh release download "$tag" --pattern SHA256SUMS.txt',workflow)
        self.assertIn('"$actual" == "$expected"',workflow)
        self.assertNotIn('luci-app-component-updater_0.2.3-1_all.ipk',workflow)

    def test_offline_ipk_contains_required_files_and_permissions(self):
        with tempfile.TemporaryDirectory() as td:
            subprocess.run([sys.executable,str(ROOT/'tools/package_ipk.py'),'--out',td],check=True,capture_output=True,text=True)
            pkg=Path(td)/'luci-app-component-updater_0.3.0-1_all.ipk'
            self.assertTrue(pkg.is_file())
            self.assertTrue(pkg.read_bytes().startswith(bytes((0x1f,0x8b))))
            with tarfile.open(pkg,mode='r:gz') as archive:
                self.assertEqual(archive.getnames(),[
                    './debian-binary','./data.tar.gz','./control.tar.gz'])
                data=archive.extractfile('./data.tar.gz').read()
            with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as t:
                names=set(t.getnames())
                for path in [
                    './usr/sbin/component-updaterctl',
                    './usr/libexec/rpcd/component-updater',
                    './usr/share/rpcd/acl.d/luci-app-component-updater.json',
                    './usr/share/luci/menu.d/luci-app-component-updater.json',
                    './www/luci-static/resources/view/component-updater/overview.js',
                    './www/luci-static/resources/component-updater/design.css',
                ]:
                    self.assertIn(path,names)
                self.assertEqual(t.getmember('./usr/sbin/component-updaterctl').mode,0o755)
                self.assertEqual(t.getmember('./usr/libexec/rpcd/component-updater').mode,0o755)
                acl=json.load(t.extractfile('./usr/share/rpcd/acl.d/luci-app-component-updater.json'))
                rules=acl['luci-app-component-updater']
                self.assertEqual(rules['read']['ubus']['component-updater'],['status','check','plan'])
                self.assertEqual(rules['write']['ubus']['component-updater'],['start','rollback'])
                self.assertEqual(rules['read']['uci'],['component-updater'])
                self.assertEqual(rules['write']['uci'],['component-updater'])
                self.assertIn('./www/luci-static/resources/view/component-updater/settings.js',names)

if __name__=='__main__':unittest.main()
