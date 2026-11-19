"""Offline, non-root device transaction tests.

Runs an isolated copy of the production /bin/sh controller against controlled
fixtures; every hard-coded device path is rewritten into a temporary sandbox.
No router files, GitHub requests or production processes are modified.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import subprocess
import tarfile
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'luci-app-component-updater/root/usr/sbin/component-updaterctl'
TAG = 'v154.0.8037.49-5'
BUILD = f'component-naiveproxy-{TAG}-upx521-r1'
ARCH = 'aarch64_cortex-a53'
FILENAME = f'naiveproxy-{TAG}-openwrt-{ARCH}-upx521-r1.tar.xz'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def binary(version):
    return ('#!/bin/sh\necho "naive ' + version + '"\n').encode()


@unittest.skipUnless(shutil.which('jq') and shutil.which('tar') and shutil.which('sha256sum'),
                     'requires jq, tar and sha256sum on Linux CI')
class DeviceTransactionTests(unittest.TestCase):
    def setUp(self):
        self.ctx = tempfile.TemporaryDirectory(prefix='component-test-')
        self.addCleanup(self.ctx.cleanup)
        self.root = Path(self.ctx.name)
        self.base = self.root / 'state'
        self.cache = self.root / 'cache'
        self.bin = self.root / 'usr/bin/naive'
        self.bin.parent.mkdir(parents=True)
        self.bin.write_bytes(binary('150.0.7871.63'))
        self.bin.chmod(0o755)
        self.old = self.bin.read_bytes()
        self.release = self.root / 'openwrt_release'
        self.release.write_text("DISTRIB_ARCH='aarch64_cortex-a53'\n")
        self.fixtures = self.root / 'fixtures'
        self.fixtures.mkdir()
        self.mockbin = self.root / 'mockbin'
        self.mockbin.mkdir()
        self.jshn = self.root / 'jshn.sh'
        self.jshn.write_text('''json_init() { _JSON=''; }
json_add_string() { _JSON="${_JSON}${1}	${2}
"; }
json_dump() { printf '%s' "$_JSON" | python3 -c "import json,sys;print(json.dumps(dict(x.rstrip('\\n').split('\\t',1) for x in sys.stdin if '\\t' in x)))"; }
''')
        self.mock_cmd('jsonfilter', '''#!/usr/bin/env python3
import json,sys
args=sys.argv
p=args[args.index('-i')+1]; expr=args[args.index('-e')+1]
try:
 d=json.load(open(p))
 for key in expr[2:].split('.'):
  d=d[key]
 print('true' if d is True else 'false' if d is False else d)
except Exception:
 pass
''')
        self.mock_cmd('opkg', '#!/bin/sh\necho "Version: 150.0.7871.63.1-r1"\n')
        self.mock_cmd('pidof', '#!/bin/sh\nexit 1\n')
        s = BACKEND.read_text()
        for before, after in [
            ('BASE=/etc/component-updater', 'BASE=' + shlex.quote(str(self.base))),
            ('CACHE=/tmp/component-updater', 'CACHE=' + shlex.quote(str(self.cache))),
            ('BINARY=/usr/bin/naive', 'BINARY=' + shlex.quote(str(self.bin))),
            ('/usr/share/libubox/jshn.sh', str(self.jshn)),
            ('/etc/openwrt_release', str(self.release)),
        ]:
            assert before in s, before
            s = s.replace(before, after)
        # The overriding test-only downloader never goes to the network.
        mock_download = '''
download() {
    case "$1" in
      https://api.github.com/repos/klzgrad/naiveproxy/releases/latest)
         cp "$TEST_FIXTURES/official.json" "$2";;
      */manifest.json)
         cp "$TEST_FIXTURES/manifest.json" "$2";;
      */*.tar.xz)
         cp "$TEST_FIXTURES/archive.tar.xz" "$2";;
      *) return 1;;
    esac
}
'''
        assert 'space_ok() {' in s
        s = s.replace('space_ok() {', mock_download + '\nspace_ok() {')
        self.cmd = self.root / 'component-updaterctl'
        self.cmd.write_text(s)
        self.cmd.chmod(0o755)
        self.archive = self.fixtures / 'archive.tar.xz'
        self.new = binary('154.0.8037.49')
        self.make_assets()

    def mock_cmd(self, name, contents):
        p=self.mockbin/name
        p.write_text(contents)
        p.chmod(0o755)

    def make_assets(self, data=None, extra=False, reported_checksum=None):
        data = self.new if data is None else data
        with tarfile.open(self.archive, 'w:xz') as t:
            for name, blob in [('naive', data), ('METADATA.json', b'{}')]+([('unexpected',b'bad')] if extra else []):
                info=tarfile.TarInfo(name)
                info.mode=0o755 if name=='naive' else 0o644
                info.size=len(blob)
                t.addfile(info, io.BytesIO(blob))
        (self.fixtures/'official.json').write_text(json.dumps({'tag_name':TAG}))
        (self.fixtures/'manifest.json').write_text(json.dumps({
            'component':'naiveproxy', 'upstream_tag':TAG, 'release_tag':BUILD,
            'assets':{'aarch64_cortex_a53':{'filename':FILENAME,
                      'sha256':reported_checksum or sha(self.archive.read_bytes()),
                      'binary_sha256':sha(data)}}
        }))

    def call(self, action, extra=None):
        env=os.environ.copy()
        env['PATH']=str(self.mockbin)+os.pathsep+env['PATH']
        env['TEST_FIXTURES']=str(self.fixtures)
        if extra: env.update(extra)
        shell = ['busybox', 'sh'] if env.get('COMPONENT_TEST_SHELL') == 'busybox' else ['/bin/sh']
        r=subprocess.run(shell+[str(self.cmd),action],cwd=self.root,env=env,capture_output=True,text=True,timeout=25)
        try:
            out=json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            out={'stdout':r.stdout.strip(),'stderr':r.stderr.strip()}
        return r.returncode,out

    def checked(self):
        rc,out=self.call('check')
        self.assertEqual((rc,out.get('status')), (0,'ready'),out)

    def test_status_does_not_change_binary(self):
        rc,d=self.call('status')
        self.assertEqual(rc,0,d)
        self.assertEqual(d['installed_version'],'150.0.7871.63')
        self.assertEqual(self.bin.read_bytes(),self.old)

    def test_check_creates_expiring_approved_plan(self):
        self.checked()
        p=json.loads((self.cache/'plan.json').read_text())
        self.assertEqual(p['build_tag'], BUILD)
        self.assertEqual(p['sha256'], sha(self.archive.read_bytes()))
        self.assertTrue(p['ready']) if isinstance(p['ready'],bool) else self.assertEqual(p['ready'],'true')
        self.assertEqual(self.bin.read_bytes(),self.old)

    def test_latest_unpublished_invalidates_old_plan(self):
        self.checked()
        (self.fixtures/'manifest.json').unlink()
        rc,d=self.call('check')
        self.assertEqual(d['status'],'pending',d)
        self.assertFalse((self.cache/'plan.json').exists())
        rc,d=self.call('run')
        self.assertNotEqual(rc,0)
        self.assertEqual(self.bin.read_bytes(),self.old)

    def test_github_failure_invalidates_old_plan(self):
        self.checked()
        (self.fixtures/'official.json').unlink()
        rc,d=self.call('check')
        self.assertNotEqual(rc,0)
        self.assertFalse((self.cache/'plan.json').exists())

    def test_forged_manifest_is_rejected(self):
        d=json.loads((self.fixtures/'manifest.json').read_text())
        d['upstream_tag']='v999.9'
        (self.fixtures/'manifest.json').write_text(json.dumps(d))
        rc,report=self.call('check')
        self.assertNotEqual(rc,0)
        self.assertFalse((self.cache/'plan.json').exists())
        self.assertEqual(self.bin.read_bytes(),self.old)

    def test_unsupported_architecture_is_rejected(self):
        self.release.write_text("DISTRIB_ARCH='mipsel_24kc'\n")
        rc,d=self.call('check')
        self.assertNotEqual(rc,0)
        self.assertEqual(d['status'],'unsupported')

    def test_checksum_mismatch_does_not_modify_target(self):
        self.checked()
        self.archive.write_bytes(self.archive.read_bytes()+b'bad')
        rc,d=self.call('run')
        self.assertNotEqual(rc,0)
        self.assertEqual(self.bin.read_bytes(),self.old)
        self.assertEqual(json.loads((self.cache/'job.json').read_text())['state'],'failed')

    def test_unexpected_archive_member_is_rejected(self):
        self.make_assets(extra=True)
        self.checked()
        rc,d=self.call('run')
        self.assertNotEqual(rc,0)
        self.assertEqual(self.bin.read_bytes(),self.old)

    def test_nonrunnable_candidate_does_not_modify_target(self):
        self.make_assets(data=b'not-an-executable\n')
        self.checked()
        rc,d=self.call('run')
        self.assertNotEqual(rc,0)
        self.assertEqual(self.bin.read_bytes(),self.old)

    def test_successful_atomic_install_and_rollback(self):
        self.checked()
        rc,d=self.call('run')
        self.assertEqual(rc,0,d)
        self.assertEqual(self.bin.read_bytes(), self.new)
        self.assertFalse((self.base/'transaction.json').exists())
        self.assertTrue((self.base/'installed/naiveproxy.json').exists())
        receipt=json.loads((self.base/'installed/naiveproxy.json').read_text())
        self.assertEqual(receipt['upstream_tag'],TAG)
        rc,d=self.call('rollback')
        self.assertEqual(rc,0,d)
        self.assertEqual(self.bin.read_bytes(),self.old)
        self.assertFalse((self.cache/'plan.json').exists())
        self.assertFalse((self.base/'transaction.json').exists())

    def test_expired_plan_is_rejected(self):
        self.checked()
        plan=self.cache/'plan.json'
        d=json.loads(plan.read_text())
        d['checked_at']=str(int(time.time())-3601)
        plan.write_text(json.dumps(d))
        rc,out=self.call('run')
        self.assertNotEqual(rc,0)
        self.assertEqual(self.bin.read_bytes(),self.old)

    def test_changed_plan_checksum_is_rejected(self):
        self.checked()
        plan=self.cache/'plan.json'
        d=json.loads(plan.read_text())
        d['binary_sha256']='INVALID'
        plan.write_text(json.dumps(d))
        rc,out=self.call('run')
        self.assertNotEqual(rc,0)
        self.assertEqual(self.bin.read_bytes(),self.old)

    def test_symlink_target_is_rejected(self):
        target=self.root/'actual-naive'
        target.write_bytes(self.old);target.chmod(0o755)
        self.bin.unlink(); self.bin.symlink_to(target)
        self.checked()
        rc,out=self.call('run')
        self.assertNotEqual(rc,0)
        self.assertEqual(target.read_bytes(),self.old)

    def test_pending_transaction_blocks_another_update_and_can_recover(self):
        self.checked()
        backup=self.base/'backups/naiveproxy/1234567-1'
        backup.mkdir(parents=True)
        (backup/'naive').write_bytes(self.old)
        (backup/'sha256').write_text(sha(self.old)+'\n')
        self.bin.write_bytes(self.new)
        (self.base/'transaction.json').write_text(json.dumps({'backup_id':backup.name}))
        rc,d=self.call('status')
        self.assertEqual(d['job_state'],'recovery_required')
        rc,d=self.call('check')
        self.assertEqual(d['status'],'recovery_required')
        rc,d=self.call('run')
        self.assertNotEqual(rc,0)
        rc,d=self.call('rollback')
        self.assertEqual(rc,0,d)
        self.assertEqual(self.bin.read_bytes(),self.old)
        self.assertFalse((self.base/'transaction.json').exists())

    def test_lock_blocks_concurrent_install(self):
        self.checked()
        (self.cache/'update.lock').mkdir()
        rc,d=self.call('run')
        self.assertNotEqual(rc,0)
        self.assertEqual(self.bin.read_bytes(),self.old)

if __name__=='__main__':
    unittest.main()
