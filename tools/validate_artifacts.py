#!/usr/bin/env python3
"""Fail-closed validator for prebuilt release candidate assets.

Checks artifact digests, archive shape and embedded provenance using ONLY
local files. This does not certify compatibility with target routers.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
from package_component_ipk import inspect_ipk

SHA = re.compile(r'^[0-9a-f]{64}$')


def verify_manifest(path: Path) -> dict:
    data = json.loads(path.read_text())
    if data.get('schema') != 1 or not data.get('component') or not data.get('upstream_tag') or not data.get('release_tag'):
        raise ValueError('invalid release manifest header')
    assets = data.get('assets')
    if not isinstance(assets, dict) or not assets:
        raise ValueError('empty release assets')
    for architecture, item in assets.items():
        if item.get('format')!='ipk':
            raise ValueError('only native IPK assets are accepted')
        name=item.get('filename','')
        if not name.endswith('.ipk') or not re.fullmatch(r'[a-z][a-z0-9+.-]*_[0-9A-Za-z.+~_-]+_[a-z0-9_-]+[.]ipk',name):
            raise ValueError('unsafe native IPK filename')
        expected_name=f"{item['package']}_{item['package_version']}_{item['package_arch']}.ipk"
        if name!=expected_name or item['package_arch'].replace('-','_')!=architecture:
            raise ValueError('package metadata/file architecture mismatch')
        asset_path=path.parent/name
        if not asset_path.is_file() or asset_path.is_symlink():
            raise ValueError('asset missing or symlink: '+name)
        blob=asset_path.read_bytes()
        if item.get('bytes')!=len(blob) or not SHA.fullmatch(item.get('sha256','')) or hashlib.sha256(blob).hexdigest()!=item['sha256']:
            raise ValueError('artifact digest or byte length mismatch: '+name)
        control,binary=inspect_ipk(blob,item['install_path'])
        for k,field in [('Package','package'),('Version','package_version'),('Architecture','package_arch')]:
            if control.get(k)!=item[field]:
                raise ValueError('IPK control mismatch: '+k)
        if len(binary)>128*1024*1024 or not SHA.fullmatch(item.get('binary_sha256','')) or hashlib.sha256(binary).hexdigest()!=item['binary_sha256']:
            raise ValueError('binary digest mismatch: '+name)
        checks=item.get('validation',{})
        if checks.get('elf')!='passed' or checks.get('round_trip') not in ('passed','not-applicable'):
            raise ValueError('failed build validations: '+name)
    return data


if __name__ == '__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--manifest',type=Path,required=True)
    args=ap.parse_args()
    m=verify_manifest(args.manifest)
    print('Verified',len(m['assets']),'candidate assets for',m['component'],m['upstream_tag'])
