"""Test proxy transport independently of the trust-anchored update manifest."""
import os
from pathlib import Path
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
BACKEND=ROOT/'luci-app-component-updater/root/usr/sbin/component-updaterctl'

class ProxyTests(unittest.TestCase):
    def probe(self, mode, prefix, url):
        s=BACKEND.read_text()
        start=s.index('proxy_target() {')
        end=s.index('\ndownload_once() {',start)
        script="""config_get() {
            case "$1" in
                github_proxy_mode) printf '%s\\n' "$TEST_MODE";;
                github_proxy_prefix) printf '%s\\n' "$TEST_PREFIX";;
            esac
        }
        """+s[start:end]+"""
        proxy_target "$1"
        """
        env=os.environ.copy()
        env['TEST_MODE']=mode
        env['TEST_PREFIX']=prefix
        return subprocess.run(['/bin/sh','-c',script,'probe',url],env=env,
                              text=True,capture_output=True,timeout=5)

    def test_release_asset_prefixed(self):
        url='https://github.com/wekingchen/luci-app-component-updater/releases/download/tag/file.tar.xz'
        r=self.probe('assets','https://mirror.example/',url)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(r.stdout.strip(),'https://mirror.example/'+url)

    def test_api_only_in_all_mode(self):
        url='https://api.github.com/repos/klzgrad/naiveproxy/releases/latest'
        self.assertNotEqual(self.probe('assets','https://mirror.example/',url).returncode,0)
        self.assertEqual(self.probe('all','https://mirror.example/',url).returncode,0)

    def test_off_never_proxies(self):
        url='https://github.com/wekingchen/luci-app-component-updater/releases/download/tag/file'
        self.assertNotEqual(self.probe('off','https://mirror.example/',url).returncode,0)

    def test_reject_untrusted_prefixes(self):
        url='https://github.com/wekingchen/luci-app-component-updater/releases/download/a/b'
        for prefix in ['http://mirror.example/','https://localhost/','https://127.0.0.1/',
                       'https://192.168.1.1/','https://mirror.example/../',
                       'https://name:password@host/','https://mirror.example/?x=1']:
            with self.subTest(prefix=prefix):
                self.assertNotEqual(self.probe('assets',prefix,url).returncode,0)

    def test_unknown_url_never_proxies(self):
        self.assertNotEqual(self.probe('all','https://mirror.example/','https://evil.example/bad').returncode,0)

    def test_tls_and_known_release_sources_contract(self):
        code=BACKEND.read_text()
        self.assertIn('release_digest()',code)
        self.assertIn('GitHub Release API asset digest',code)
        self.assertIn("--proto '=https' --proto-redir '=https'",code)
        for phrase in ['--no-check-certificate','--insecure']:
            self.assertNotIn(phrase,code)

if __name__ == '__main__':
    unittest.main()
