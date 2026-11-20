#!/usr/bin/env python3
"""Prepare exact APK backend fixtures for native AX6S chroot acceptance.

Only the network download function is redirected to local SHA256-checked
workflow artifacts. The production preflight, transaction, apk install, and
rollback code are used unmodified in the native firmware rootfs.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys

if len(sys.argv)!=5:
    raise SystemExit("usage: fixtures.py ROOTFS MANIFEST ORIGINAL-APK CANDIDATE-APK")
root=Path(sys.argv[1])
manifest_path=Path(sys.argv[2])
original=Path(sys.argv[3])
candidate=Path(sys.argv[4])
m=json.loads(manifest_path.read_text())
assert m["schema"]==2 and m["component"]=="naiveproxy"
for source,entry in [(original,m["original"]),(candidate,m["candidate"])]:
    assert source.name==entry["filename"]
    assert hashlib.sha256(source.read_bytes()).hexdigest()==entry["sha256"]
fixture=root/"tmp/component-acceptance-fixtures"
fixture.mkdir(parents=True,exist_ok=True)
shutil.copyfile(manifest_path,fixture/"manifest.json")
shutil.copyfile(original,fixture/"original.apk")
shutil.copyfile(candidate,fixture/"candidate.apk")
(fixture/"expected_version").write_text(m["candidate"]["version"]+"\n")
(fixture/"official.json").write_text(json.dumps({"tag_name":m["upstream_tag"]}))
release={
 "tag_name":m["release_tag"],
 "assets":[
    {"name":"manifest.json","digest":"sha256:"+hashlib.sha256(manifest_path.read_bytes()).hexdigest(),"size":manifest_path.stat().st_size},
    {"name":original.name,"digest":"sha256:"+m["original"]["sha256"],"size":original.stat().st_size},
    {"name":candidate.name,"digest":"sha256:"+m["candidate"]["sha256"],"size":candidate.stat().st_size}
 ]}
(fixture/"release.json").write_text(json.dumps(release))
source=Path("luci-app-component-updater/root/usr/sbin/component-updaterctl").read_text()
marker="# GitHub Release API returns a SHA256 digest for each uploaded asset."
assert marker in source
stub="""# Native chroot acceptance: replace only the network transport.
download() {
    case "$1" in
        https://api.github.com/repos/klzgrad/naiveproxy/releases/latest)
            cp /tmp/component-acceptance-fixtures/official.json "$2";;
        https://api.github.com/repos/wekingchen/luci-app-component-updater/releases/tags/component-naiveproxy-*)
            cp /tmp/component-acceptance-fixtures/release.json "$2";;
        https://github.com/wekingchen/luci-app-component-updater/releases/download/*/manifest.json)
            cp /tmp/component-acceptance-fixtures/manifest.json "$2";;
        https://github.com/wekingchen/luci-app-component-updater/releases/download/*/*.apk)
            case "$1" in
                *-r1_aarch64_cortex-a53.apk)
                    cp /tmp/component-acceptance-fixtures/original.apk "$2";;
                *-r3_aarch64_cortex-a53.apk)
                    cp /tmp/component-acceptance-fixtures/candidate.apk "$2";;
                *) return 1;;
            esac;;
        *) return 1;;
    esac
}
"""
target=root/"usr/sbin/component-updaterctl"
target.parent.mkdir(parents=True,exist_ok=True)
target.write_text(source.replace(marker,stub+marker))
target.chmod(0o755)
adapter=Path("luci-app-component-updater/root/usr/libexec/component-updater/ax6s-apkctl.sh")
adapter_target=root/"usr/libexec/component-updater/ax6s-apkctl.sh"
adapter_target.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(adapter,adapter_target)
adapter_target.chmod(0o644)
board=root/"tmp/sysinfo/board_name"
board.parent.mkdir(parents=True,exist_ok=True)
board.write_text("xiaomi,redmi-router-ax6s\n")
(root/"tmp").chmod(0o1777)
print("Native AX6S fixtures prepared against release:",m["release_tag"])
