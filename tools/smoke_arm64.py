#!/usr/bin/env python3
"""Run both original and UPX-packed official binaries on native AArch64 Linux.

A failed packed binary with a successful original isolates an UPX/runtime issue;
neither success alone is equivalent to GL firmware or N1 functional acceptance.
"""
import argparse
import hashlib
import json
import platform
import re
import subprocess
import tempfile
from pathlib import Path
from component_builder import (
    definitions,github_json,find_asset,source_name,download,digest_ok,extract_member
)
from package_component_ipk import inspect_ipk

def run_native(blob: bytes, label: str) -> tuple[int,str,str]:
    with tempfile.TemporaryDirectory(prefix='component-arm64-') as td:
        path=Path(td)/'naive'
        path.write_bytes(blob)
        path.chmod(0o755)
        result=subprocess.run([str(path),'--version'],capture_output=True,text=True,timeout=45)
        print(label, 'rc='+str(result.returncode),
              'stdout='+repr(result.stdout.strip()),
              'stderr='+repr(result.stderr.strip()),flush=True)
        return result.returncode,result.stdout.strip(),result.stderr.strip()

def verify(manifest: Path) -> None:
    if platform.machine().lower() not in ('aarch64','arm64'):
        raise RuntimeError('Native ARM64 runner required')
    data=json.loads(manifest.read_text())
    tag=data['upstream_tag']
    if not re.fullmatch(r'v[0-9]+(?:\.[0-9]+)+(?:-[0-9]+)?',tag):
        raise ValueError('unexpected official version')
    cfg=definitions(data['component'])[0]
    targets={t['id']:t for t in cfg['platforms']}
    release=github_json('https://api.github.com/repos/'+cfg['upstream']['repository']+'/releases/tags/'+tag)
    expected='naive '+tag.removeprefix('v').split('-')[0]
    for key,entry in sorted(data['assets'].items()):
        if entry['format']!='ipk' or entry['package']!='naiveproxy':
            raise ValueError('unexpected component IPK')
        target=targets[entry['package_arch']]
        meta,binary=inspect_ipk((manifest.parent/entry['filename']).read_bytes(),'/usr/bin/naive')
        if meta['Architecture']!=target['id']:
            raise ValueError('package architecture mismatch')
        asset=find_asset(release,source_name(cfg,tag,target))
        blob=download(asset['browser_download_url'])
        source_sha=digest_ok(blob,asset['digest'])
        if source_sha!=entry['source_sha256']:
            raise ValueError('source asset SHA256 mismatch')
        suffix=target['asset_suffix'].split('.',1)[1]
        original=extract_member(blob,cfg['binary']['archive_member'],suffix)
        if len(original)!=entry['original_bytes']:
            raise ValueError('source binary size mismatch')
        baseline=run_native(original,key+' official-uncompressed')
        packed=run_native(binary,key+' UPX-compressed')
        if baseline[0]!=0 or baseline[1].splitlines()[0]!=expected:
            raise RuntimeError(f'Official upstream ARM64 baseline failed: {key}, {baseline}')
        if packed[0]!=0 or packed[1].splitlines()[0]!=expected:
            raise RuntimeError(f'UPX-compressed ARM64 binary failed, upstream baseline was OK: {key}, {packed}')
        print('Native ARM64 source and UPX executable verified',key,flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--manifest',type=Path,required=True)
    verify(ap.parse_args().manifest)
