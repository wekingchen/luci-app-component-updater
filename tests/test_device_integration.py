"""Production POSIX backend simulated against a real native-IPK opkg test double."""
import hashlib,json,os,re,shlex,shutil,subprocess,sys,tempfile,time,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from package_component_ipk import build_ipk,inspect_ipk
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'luci-app-component-updater/root/usr/sbin/component-updaterctl'
TAG='v154.0.8037.49-5';BUILD=f'component-naiveproxy-{TAG}-upx521-r3'
ARCH='aarch64_cortex-a53';NEW='154.0.8037.49.5-r3';OLD='150.0.7871.63.1-r1'
FILE=f'naiveproxy_{NEW}_{ARCH}.ipk'
def sha(b):return hashlib.sha256(b).hexdigest()
def binary(v):return f'#!/bin/sh\necho "naive {v}"\n'.encode()
@unittest.skipUnless(shutil.which('jq') and shutil.which('tar') and shutil.which('sha256sum'),'requires Linux build tools')
class NativeTransactions(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.root=Path(t.name);self.base=self.root/'state';self.cache=self.root/'cache'
        self.bin=self.root/'usr/bin/naive';self.bin.parent.mkdir(parents=True)
        self.old=binary('154.0.8037.49')+b'# manually packed prior build\n';self.new=binary('154.0.8037.49')
        self.bin.write_bytes(self.old);self.bin.chmod(0o755)
        self.pkg=self.root/'package.json';self.pkg.write_text(json.dumps(dict(version=OLD,arch=ARCH)))
        self.release=self.root/'openwrt_release';self.release.write_text("DISTRIB_ARCH='aarch64_cortex-a53'\n")
        self.fixture=self.root/'fixtures';self.fixture.mkdir()
        self.mockbin=self.root/'mockbin';self.mockbin.mkdir()
        jshn=self.root/'jshn.sh'
        jshn.write_text("""json_init() { _JSON=''; }
json_add_string() { _JSON="$_JSON$1\t$2
"; }
json_dump() { printf '%s' "$_JSON" | python3 -c "import json,sys;print(json.dumps(dict(x.rstrip('\\n').split('\\t',1) for x in sys.stdin if '\\t' in x)))"; }
""")
        self.mock('jsonfilter',r'''#!/usr/bin/env python3
import json,re,sys
try:
 a=sys.argv
 obj=json.load(open(a[a.index('-i')+1]))
 exp=a[a.index('-e')+1]
 for key in re.findall(r'[A-Za-z_][A-Za-z0-9_-]*|\[\d+\]',exp[2:]):
  obj=obj[int(key[1:-1])] if key.startswith('[') else obj[key]
 print('true' if obj is True else 'false' if obj is False else obj)
except Exception:pass
''')
        self.mock('opkg',r'''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
from package_component_ipk import inspect_ipk
st=Path(os.environ['TEST_PKG']);s=json.loads(st.read_text())
a=sys.argv[1:];cmd=a[0] if a else ''
if cmd=='status':
 print('Package: naiveproxy\nVersion: '+s['version']+'\nArchitecture: '+s['arch']+'\nDepends: libc')
elif cmd=='files':
 print('Package naiveproxy files:\n/usr/bin/naive')
 if os.environ.get('TEST_EXTRA_OWNER'):print('/etc/config/naiveproxy')
elif cmd=='search':
 print('naiveproxy - '+s['version'])
elif cmd=='install':
 if os.environ.get('TEST_INSTALL_FAIL') and '--force-downgrade' not in a:sys.exit(1)
 try:
  c,b=inspect_ipk(Path(a[-1]).read_bytes(),'/usr/bin/naive')
  assert c['Package']=='naiveproxy' and c['Architecture']==s['arch']
  if c['Version']==s['version'] and '--force-reinstall' not in a:
   sys.exit(0) # realistic no-op: an already-installed version isn't rewritten
  target=Path(os.environ['TEST_BINARY'])
  target.write_bytes(b);target.chmod(0o755)
  s['version']=c['Version']
  st.write_text(json.dumps(s))
 except Exception as e:print(e,file=sys.stderr);sys.exit(1)
else:sys.exit(2)
''')
        self.mock('uci','#!/bin/sh\nexit 1\n')
        self.mock('pidof','#!/bin/sh\nexit 1\n')
        controller=SOURCE.read_text()
        for old,new in [('BASE=/etc/component-updater','BASE='+shlex.quote(str(self.base))),
                        ('CACHE=/tmp/component-updater','CACHE='+shlex.quote(str(self.cache))),
                        ('BINARY=/usr/bin/naive','BINARY='+shlex.quote(str(self.bin))),
                        ('/usr/share/libubox/jshn.sh',str(jshn)),
                        ('/etc/openwrt_release',str(self.release))]:
            assert old in controller,old
            controller=controller.replace(old,new)
        stub="""download() {
 case "$1" in
  https://api.github.com/repos/klzgrad/naiveproxy/releases/latest) cp "$TEST_FIXTURE/official.json" "$2";;
  */releases/tags/component-naiveproxy-*) cp "$TEST_FIXTURE/release.json" "$2";;
  */manifest.json) cp "$TEST_FIXTURE/manifest.json" "$2";;
  */*.ipk) cp "$TEST_FIXTURE/update.ipk" "$2";;
  *) return 1;;
 esac
}
"""
        controller=controller.replace('release_digest() {',stub+'\nrelease_digest() {')
        self.cmd=self.root/'component-updaterctl'
        self.cmd.write_text(controller);self.cmd.chmod(0o755)
        self.build_fixture()
    def mock(self,name,data):
        p=self.mockbin/name;p.write_text(data);p.chmod(0o755)
    def build_fixture(self,b=None,hash_override=None):
        b=self.new if b is None else b
        blob=build_ipk(package='naiveproxy',version=NEW,architecture=ARCH,target='/usr/bin/naive',binary=b,depends=['libc','libgcc1'])
        (self.fixture/'update.ipk').write_bytes(blob)
        (self.fixture/'official.json').write_text(json.dumps(dict(tag_name=TAG)))
        m=dict(schema=1,component='naiveproxy',upstream_tag=TAG,release_tag=BUILD,
          assets={'aarch64_cortex_a53':dict(filename=FILE,format='ipk',package='naiveproxy',
          package_arch=ARCH,package_version=NEW,dependencies=['libc','libgcc1'],sha256=hash_override or sha(blob),
          binary_sha256=sha(b))})
        raw=json.dumps(m).encode()
        (self.fixture/'manifest.json').write_bytes(raw)
        rel=dict(tag_name=BUILD,assets=[dict(name='manifest.json',digest='sha256:'+sha(raw)),
             dict(name=FILE,digest='sha256:'+sha(blob))])
        (self.fixture/'release.json').write_text(json.dumps(rel))
    def call(self,action,extra=None):
        env=os.environ.copy();env.update(PATH=str(self.mockbin)+':'+env['PATH'],
          PYTHONPATH=str(ROOT/'tools'),TEST_FIXTURE=str(self.fixture),
          TEST_PKG=str(self.pkg),TEST_BINARY=str(self.bin))
        if extra:env.update(extra)
        cmd=['busybox','sh'] if env.get('COMPONENT_TEST_SHELL')=='busybox' else ['/bin/sh']
        r=subprocess.run(cmd+[str(self.cmd),action],env=env,cwd=self.root,text=True,
           capture_output=True,timeout=25)
        try: out=json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:out=dict(stdout=r.stdout,stderr=r.stderr)
        return r.returncode,out
    def checked(self):
        rc,out=self.call('check');self.assertEqual((rc,out.get('status')),(0,'ready'),out)
    def test_status_separates_manual_binary_and_opkg(self):
        rc,out=self.call('status');self.assertEqual(rc,0,out)
        self.assertEqual(out['installed_version'],'154.0.8037.49')
        self.assertEqual(out['package_version'],OLD)
    def test_native_install_then_rollback(self):
        self.checked()
        rc,out=self.call('run');self.assertEqual(rc,0,out)
        self.assertEqual(json.loads(self.pkg.read_text())['version'],NEW)
        self.assertEqual(self.bin.read_bytes(),self.new)
        self.assertNotEqual(sha(self.old),sha(self.new),'test fixture must exercise changed bytes')
        oldpack=list((self.base/'backups/naiveproxy').glob('*/previous.ipk'))
        self.assertEqual(len(oldpack),1)
        # Older 21.02-era GL.iNet opkg requires exact archive member names:
        # GNU ar-style suffix '/' makes even a valid IPK unparsable.
        recovery=oldpack[0].read_bytes()
        self.assertTrue(recovery.startswith(b'!<arch>\n'))
        pos=8; members=[]
        while pos<len(recovery):
            header=recovery[pos:pos+60]
            name=header[:16].decode('ascii').rstrip(' ')
            self.assertFalse(name.endswith('/'),name)
            members.append(name)
            count=int(header[48:58].decode('ascii').strip())
            pos+=60+count+(count%2)
        self.assertEqual(members,['debian-binary','control.tar.gz','data.tar.gz'])
        control,raw=inspect_ipk(oldpack[0].read_bytes(),'/usr/bin/naive')
        self.assertEqual(control['Version'],OLD);self.assertEqual(raw,self.old)
        rc,out=self.call('rollback');self.assertEqual(rc,0,out)
        self.assertEqual(json.loads(self.pkg.read_text())['version'],OLD)
        self.assertEqual(self.bin.read_bytes(),self.old)
    def test_same_package_version_repairs_manually_replaced_binary(self):
        self.pkg.write_text(json.dumps(dict(version=NEW,arch=ARCH)))
        self.bin.write_bytes(binary('150.0.7871.63'))
        self.bin.chmod(0o755)
        self.checked()
        rc,out=self.call('run')
        self.assertEqual(rc,0,out)
        self.assertEqual(self.bin.read_bytes(),self.new)
        self.assertEqual(json.loads(self.pkg.read_text())['version'],NEW)
        rc,out=self.call('rollback')
        self.assertEqual(rc,0,out)
        self.assertEqual(self.bin.read_bytes(),binary('150.0.7871.63'))
        self.assertEqual(json.loads(self.pkg.read_text())['version'],NEW)

    def test_corrupt_ipk_never_installs(self):
        self.checked()
        (self.fixture/'update.ipk').write_bytes(b'tampered')
        rc,out=self.call('run');self.assertNotEqual(rc,0,out)
        self.assertEqual(json.loads(self.pkg.read_text())['version'],OLD)
    def test_manifest_digest_mismatch_rejected(self):
        (self.fixture/'manifest.json').write_bytes(b'evil')
        rc,out=self.call('check');self.assertNotEqual(rc,0,out)
        self.assertFalse((self.cache/'plan.json').exists())
    def test_ipk_digest_mismatch_rejected(self):
        self.build_fixture(hash_override='f'*64)
        rc,out=self.call('check');self.assertNotEqual(rc,0,out)
    def test_pending_discards_old_plan(self):
        self.checked();(self.fixture/'release.json').unlink()
        rc,out=self.call('check');self.assertEqual(out['status'],'pending')
        self.assertFalse((self.cache/'plan.json').exists())
    def test_owner_has_multiple_files_refused(self):
        self.checked()
        rc,out=self.call('run',dict(TEST_EXTRA_OWNER='1'))
        self.assertNotEqual(rc,0,out)
        self.assertEqual(json.loads(self.pkg.read_text())['version'],OLD)
    def test_opkg_failure_rolls_back(self):
        self.checked()
        rc,out=self.call('run',dict(TEST_INSTALL_FAIL='1'))
        self.assertNotEqual(rc,0,out)
        self.assertEqual(json.loads(self.pkg.read_text())['version'],OLD)
    def test_expired_plan_fails(self):
        self.checked();p=self.cache/'plan.json';d=json.loads(p.read_text())
        d['checked_at']=str(int(time.time())-4000);p.write_text(json.dumps(d))
        rc,out=self.call('run');self.assertNotEqual(rc,0,out)
    def test_incomplete_transaction_blocks(self):
        self.base.mkdir(parents=True)
        (self.base/'transaction.json').write_text('{"backup_id":"123-45"}')
        rc,out=self.call('check');self.assertEqual(out['status'],'recovery_required')
    def test_unsupported_arch(self):
        self.release.write_text("DISTRIB_ARCH='mips_24kc'\n")
        rc,out=self.call('check');self.assertEqual(out['status'],'unsupported')
    def test_busy_lock(self):
        self.checked();(self.cache/'update.lock').mkdir()
        rc,out=self.call('run');self.assertNotEqual(rc,0,out)
if __name__=='__main__':unittest.main()
