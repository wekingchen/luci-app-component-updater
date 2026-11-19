#!/usr/bin/env python3
"""Build native APKv3 NaiveProxy candidates AND exact recovery packages.

The old package is reconstructed only from a SHA256-verified AX6S firmware
squashfs, not from changing feeds or a generic official upstream binary.
The candidate reuses the original service and config files verbatim, replacing
only the executable using the already verified component IPK build artifact.
No APKv2 tar fallback; requires pinned full host apk-tools 3.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "tools"))
from package_component_ipk import inspect_ipk

FIRMWARE_TAG = "2026.11.17-2044-AX6S-MTK"
FIRMWARE_SHA256 = "a963222763cf7c2c1b9bc521730a9d1b06b2e261caca156e6c7ebdebe1afc181"
ARCH = "aarch64_cortex-a53"
BASE_VERSION = "154.0.8037.49.5-r1"
BASE_SHA = {
    "usr/bin/naive": "94a9d2ebce92b2fd877e1e7019dbfa09a7bb7a5d481ec593bd34b5d5abd2a861",
    "etc/init.d/naiveproxy": "4d9dec9eb81586c5ea932260500329b68fc60f8c38af0712516b7a0f0ae59849",
    "etc/config/naiveproxy": "201d0b3afd1e131f7695a4e4f541ec0ff6447dc8bf824eb8f96827d530b03682",
}
MODES = {"usr/bin/naive": 0o755, "etc/init.d/naiveproxy":0o755,
         "etc/config/naiveproxy":0o600}
TAG_PATTERN = re.compile(r"v[0-9]+(?:\.[0-9]+)*(?:-[0-9]+)?\Z")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require_source(root: Path) -> dict[str, bytes]:
    contents = {}
    for name, expected in BASE_SHA.items():
        p = root / name
        if not p.is_file() or p.is_symlink() or p.stat().st_size > 12 * 1024 * 1024:
            raise ValueError("missing, symlinked or oversized firmware file: " + name)
        data = p.read_bytes()
        if sha(data) != expected:
            raise ValueError("AX6S original firmware hash mismatch: " + name)
        contents[name] = data
    if not (root/"lib/apk/db/installed").is_file():
        raise ValueError("firmware native APK database is missing")
    return contents


def check_original_metadata(root: Path, apk_tool: str) -> None:
    # The package must be installed and own exactly the three intended files.
    cmd = [apk_tool,"--root",str(root),"--arch",ARCH]
    info = subprocess.run(cmd+["info","-v","naiveproxy"],check=True,
                          capture_output=True,text=True).stdout.strip()
    if info != "naiveproxy-" + BASE_VERSION:
        raise ValueError("firmware package version mismatch: "+repr(info))
    files = subprocess.run(cmd+["info","-L","naiveproxy"],check=True,
                           capture_output=True,text=True).stdout
    paths = {line.strip().lstrip("/") for line in files.splitlines()
             if line.strip().startswith(("etc/","usr/","/etc/","/usr/"))}
    if paths != set(BASE_SHA):
        raise ValueError("original APK package owns unexpected paths: "+repr(sorted(paths)))


def mkpkg(apk_tool: str, out: Path, version: str, payload: dict[str,bytes]) -> Path:
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)+-r[0-9]+",version):
        raise ValueError("unsafe candidate version")
    with tempfile.TemporaryDirectory(prefix="ax6s-apk-") as tmp:
        stage = Path(tmp)/"root"
        for name, data in payload.items():
            if name not in BASE_SHA:
                raise ValueError("unrecognized package file")
            path=stage/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)
            path.chmod(MODES[name])
        # OpenWrt native APK protected conffile metadata.
        meta = stage/"lib/apk/packages"
        meta.mkdir(parents=True,exist_ok=True)
        (meta/"naiveproxy.conffiles").write_text("/etc/config/naiveproxy\n")
        # The APK ownership metadata includes only approved package paths.
        dest=out/f"naiveproxy_{version}_{ARCH}.apk"
        subprocess.run([apk_tool,"mkpkg",
            "--info","name:naiveproxy",
            "--info",f"version:{version}",
            "--info",f"arch:{ARCH}",
            "--info","license:BSD-3-Clause",
            "--info","origin:naiveproxy",
            "--info","url:https://github.com/klzgrad/naiveproxy",
            "--info","description:NaiveProxy native AX6S APK, retains original service and config",
            "--info","maintainer:Component Updater",
            "--info","depends:libc",
            "--files",str(stage),
            "--output",str(dest)], check=True,
            env={**os.environ,"SOURCE_DATE_EPOCH":"0"})
    if not dest.is_file() or dest.stat().st_size > 18 * 1024 * 1024:
        raise ValueError("native APK build missing or too large")
    return dest


def create(root: Path, manifest_path: Path, candidate_ipk: Path,
           apk_tool: str, out: Path) -> dict:
    base = require_source(root)
    check_original_metadata(root, apk_tool)
    upstream = json.loads(manifest_path.read_text())
    if upstream.get("schema") != 1 or upstream.get("component") != "naiveproxy":
        raise ValueError("wrong source manifest")
    tag=upstream.get("upstream_tag","")
    if not TAG_PATTERN.fullmatch(tag):
        raise ValueError("unsupported official NaiveProxy version")
    source_tag=f"component-naiveproxy-{tag}-upx521-r3"
    if upstream.get("release_tag") != source_tag:
        raise ValueError("UPX source release identity mismatch")
    source=upstream["assets"]["aarch64_cortex_a53"]
    if (source.get("filename") != candidate_ipk.name or
        source.get("format") != "ipk" or
        source.get("package_arch") != ARCH or
        source.get("package") != "naiveproxy" or
        sha(candidate_ipk.read_bytes()) != source.get("sha256")):
        raise ValueError("UPX IPK source digest/identity mismatch")
    _, binary=inspect_ipk(candidate_ipk.read_bytes(),"/usr/bin/naive")
    if sha(binary) != source.get("binary_sha256"):
        raise ValueError("candidate NaiveProxy ELF sha mismatch")
    version=source["package_version"]
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)+-r3",version):
        raise ValueError("unexpected candidate version")
    out.mkdir(parents=True,exist_ok=True)
    base_apk=mkpkg(apk_tool,out,BASE_VERSION,base)
    latest={**base,"usr/bin/naive":binary}
    candidate=mkpkg(apk_tool,out,version,latest)
    build_tag=source_tag+"-ax6s-apk1"
    result={
        "schema":2,"component":"naiveproxy","platform":"mediatek/mt7622",
        "architecture":ARCH,"device":"xiaomi,redmi-router-ax6s",
        "firmware_release":FIRMWARE_TAG,"firmware_sha256":FIRMWARE_SHA256,
        "upstream_tag":tag,"release_tag":build_tag,
        "opkg_release_tag":source_tag,
        "original":{
            "filename":base_apk.name,"version":BASE_VERSION,
            "sha256":sha(base_apk.read_bytes()),
            "binary_sha256":BASE_SHA["usr/bin/naive"],
            "init_sha256":BASE_SHA["etc/init.d/naiveproxy"],
            "config_sha256":BASE_SHA["etc/config/naiveproxy"]
        },
        "candidate":{
            "filename":candidate.name,"version":version,
            "sha256":sha(candidate.read_bytes()),
            "binary_sha256":sha(binary),
            "init_sha256":BASE_SHA["etc/init.d/naiveproxy"],
            "config_sha256":BASE_SHA["etc/config/naiveproxy"]
        },
        "validation":{"firmware_image":"sha256-pinned","baseline_files":"sha256-pinned",
                      "original_package_db":"verified","candidate_source":"verified native IPK",
                      "device_runtime":"unverified"}
    }
    (out/"manifest.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    (out/"release-tag.txt").write_text(build_tag+"\n")
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--rootfs",type=Path,required=True)
    parser.add_argument("--source-manifest",type=Path,required=True)
    parser.add_argument("--source-ipk",type=Path,required=True)
    parser.add_argument("--apk-tool",required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(create(args.rootfs,args.source_manifest,args.source_ipk,
                             args.apk_tool,args.out),indent=2))

if __name__ == "__main__":
    main()
