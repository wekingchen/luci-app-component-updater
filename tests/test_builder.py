import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import component_builder as b


class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.cfg = b.definitions("naiveproxy")[0]

    def test_definition_targets_and_tag(self):
        self.assertEqual(len(self.cfg["platforms"]), 2)
        self.assertEqual(b.release_tag(self.cfg, "v154.0.8037.49-5"), "component-naiveproxy-v154.0.8037.49-5-upx521-r1")
        with self.assertRaises(b.BuildError):
            b.release_tag(self.cfg, "$(malicious)")

    def test_reject_malformed_config(self):
        bad = json.loads(json.dumps(self.cfg))
        bad["id"] = "../../bad"
        with self.assertRaises(b.BuildError):
            b.validate_definition(bad)
        bad = json.loads(json.dumps(self.cfg))
        bad["compression"]["arguments"] = ["--bad"]
        with self.assertRaises(b.BuildError):
            b.validate_definition(bad)

    def test_sha256_required_and_matching(self):
        content = b"original-archive"
        expected = hashlib.sha256(content).hexdigest()
        self.assertEqual(b.digest_ok(content, "sha256:"+expected), expected)
        with self.assertRaises(b.BuildError):
            b.digest_ok(content, "sha256:"+"f"*64)
        with self.assertRaises(b.BuildError):
            b.digest_ok(content, "")

    def test_safe_extract_rejects_nested_and_duplicate(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:xz") as t:
            f = tarfile.TarInfo("../naive")
            f.size = 4
            t.addfile(f, io.BytesIO(b"oops"))
        with self.assertRaises(b.BuildError):
            b.extract_member(buf.getvalue(), "naive")

    def test_nested_official_archive(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:xz") as t:
            name = "naiveproxy-v154-openwrt-aarch64_generic/naive"
            member = tarfile.TarInfo(name)
            member.size = 4
            t.addfile(member, io.BytesIO(b"test"))
        self.assertEqual(b.extract_member(buf.getvalue(), "naive"), b"test")

    def test_uncompressed_component_mode(self):
        raw = json.loads(json.dumps(self.cfg))
        raw["compression"] = {"type": "none", "revision": 2}
        b.validate_definition(raw)
        self.assertEqual(b.release_tag(raw, "v100.1-1"), "component-naiveproxy-v100.1-1-raw-r2")

    def test_elf_arch(self):
        elf = bytearray(64)
        elf[:6] = b"\x7fELF\x02\x01"
        elf[18:20] = (183).to_bytes(2, "little")
        b.verify_elf(bytes(elf), 183)
        with self.assertRaises(b.BuildError):
            b.verify_elf(bytes(elf), 62)


if __name__ == "__main__":
    unittest.main()
