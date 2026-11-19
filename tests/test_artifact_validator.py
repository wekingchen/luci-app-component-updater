"""Manifest/asset validation negative matrix (no network)."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from validate_artifacts import verify_manifest


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


class ArtifactValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.original=b'arm64-test-program'
        self.asset=self.root/'component-naiveproxy-test.tar.xz'
        self.meta={'component':'naiveproxy','upstream_tag':'v1.0',
                   'compressed_binary_sha256':sha(self.original),
                   'source_archive_sha256':'a'*64}
        self.build_archive()
        self.manifest=self.root/'manifest.json'
        self.data={'schema':1,'component':'naiveproxy','upstream_tag':'v1.0',
                   'release_tag':'component-naiveproxy-v1.0-upx521-r1','binary_name':'naive',
                   'assets':{'aarch64_generic':{'filename':self.asset.name,'sha256':sha(self.asset.read_bytes()),
                   'binary_sha256':sha(self.original),'source_sha256':'a'*64,'bytes':self.asset.stat().st_size,
                   'validation':{'elf':'passed','round_trip':'passed'}}}}
        self.write_manifest()

    def build_archive(self, extra=False):
        with tarfile.open(self.asset,mode='w:xz') as t:
            for name,blob in [('naive',self.original),('METADATA.json',json.dumps(self.meta).encode())] + ([('bad',b'x')] if extra else []):
                info=tarfile.TarInfo(name)
                info.size=len(blob)
                t.addfile(info,io.BytesIO(blob))

    def write_manifest(self):
        self.manifest.write_text(json.dumps(self.data))

    def test_genuine_candidate_passes(self):
        self.assertEqual(verify_manifest(self.manifest)['component'],'naiveproxy')

    def test_tampered_asset_fails(self):
        self.asset.write_bytes(self.asset.read_bytes()+b'evil')
        with self.assertRaises(ValueError):verify_manifest(self.manifest)

    def test_missing_asset_fails(self):
        self.asset.unlink()
        with self.assertRaises(ValueError):verify_manifest(self.manifest)

    def test_wrong_embedded_provenance_fails(self):
        self.meta['component']='fake'
        self.build_archive()
        self.data['assets']['aarch64_generic']['sha256']=sha(self.asset.read_bytes())
        self.data['assets']['aarch64_generic']['bytes']=self.asset.stat().st_size
        self.write_manifest()
        with self.assertRaises(ValueError):verify_manifest(self.manifest)

    def test_unexpected_archive_member_fails(self):
        self.build_archive(extra=True)
        self.data['assets']['aarch64_generic']['sha256']=sha(self.asset.read_bytes())
        self.data['assets']['aarch64_generic']['bytes']=self.asset.stat().st_size
        self.write_manifest()
        with self.assertRaises(ValueError):verify_manifest(self.manifest)

if __name__=='__main__':unittest.main()
