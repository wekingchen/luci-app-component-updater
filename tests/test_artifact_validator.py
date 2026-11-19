"""Native IPK artifact validation including negative digest and metadata cases."""
import hashlib, json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from package_component_ipk import build_ipk, inspect_ipk, open_ipk
from validate_artifacts import verify_manifest
def sha(blob): return hashlib.sha256(blob).hexdigest()
class NativeArtifactTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.root=Path(t.name);self.bin=b'naive-upx-arm64'
        self.ver='154.0.8037.49.5-r3';self.arch='aarch64_generic'
        self.filename=f'naiveproxy_{self.ver}_{self.arch}.ipk'
        self.asset=self.root/self.filename
        self.asset.write_bytes(build_ipk(package='naiveproxy',version=self.ver,architecture=self.arch,target='/usr/bin/naive',binary=self.bin,depends=['libc','libgcc1']))
        self.manifest=self.root/'manifest.json'
        self.d={'schema':1,'component':'naiveproxy','upstream_tag':'v154.0.8037.49-5',
                'release_tag':'component-naiveproxy-v154.0.8037.49-5-upx521-r3',
                'assets':{'aarch64_generic':{'filename':self.filename,'format':'ipk',
                'package':'naiveproxy','package_version':self.ver,'package_arch':self.arch,'dependencies':['libc','libgcc1'],
                'install_path':'/usr/bin/naive','sha256':sha(self.asset.read_bytes()),
                'binary_sha256':sha(self.bin),'bytes':self.asset.stat().st_size,
                'validation':{'elf':'passed','round_trip':'passed'}}}}
        self.save()
    def save(self):self.manifest.write_text(json.dumps(self.d))
    def test_valid_ipk(self):
        self.assertEqual(verify_manifest(self.manifest)['component'],'naiveproxy')
        ctl,b=inspect_ipk(self.asset.read_bytes(),'/usr/bin/naive')
        self.assertEqual(ctl['Version'],self.ver);self.assertEqual(b,self.bin)
    def test_ancient_opkg_uses_exact_ar_names_without_slash(self):
        blob=self.asset.read_bytes()
        self.assertTrue(blob.startswith(b'!<arch>\\n'))
        pos=8
        names=[]
        while pos < len(blob):
            header=blob[pos:pos+60]
            self.assertEqual(header[58:],b'`\\n')
            member=header[:16].decode('ascii').rstrip(' ')
            self.assertFalse(member.endswith('/'),member)
            names.append(member)
            n=int(header[48:58].decode('ascii').strip())
            pos+=60+n+(n%2)
        self.assertEqual(names,['debian-binary','control.tar.gz','data.tar.gz'])

    def test_reproducible_package(self):
        kw=dict(package='naiveproxy',version=self.ver,architecture=self.arch,target='/usr/bin/naive',binary=self.bin)
        self.assertEqual(build_ipk(**kw),build_ipk(**kw))
    def test_invalid_sha(self):
        self.asset.write_bytes(self.asset.read_bytes()+b'x')
        with self.assertRaises(ValueError):verify_manifest(self.manifest)
    def test_invalid_arch(self):
        self.d['assets']['aarch64_generic']['package_arch']='mips_24kc';self.save()
        with self.assertRaises(ValueError):verify_manifest(self.manifest)
    def test_invalid_control(self):
        self.d['assets']['aarch64_generic']['package_version']='99-r1';self.save()
        with self.assertRaises(ValueError):verify_manifest(self.manifest)
    def test_invalid_binary_digest(self):
        self.d['assets']['aarch64_generic']['binary_sha256']='f'*64;self.save()
        with self.assertRaises(ValueError):verify_manifest(self.manifest)
    def test_unknown_path(self):
        with self.assertRaises(ValueError):
            build_ipk(package='naiveproxy',version='1-r1',architecture=self.arch,target='/etc/shadow',binary=self.bin)
    def test_missing_file(self):
        self.asset.unlink()
        with self.assertRaises(ValueError):verify_manifest(self.manifest)
if __name__=='__main__':unittest.main()
