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

SHA = re.compile(r'^[0-9a-f]{64}$')


def verify_manifest(path: Path) -> dict:
    data = json.loads(path.read_text())
    if data.get('schema') != 1 or not data.get('component') or not data.get('upstream_tag') or not data.get('release_tag'):
        raise ValueError('invalid release manifest header')
    assets = data.get('assets')
    if not isinstance(assets, dict) or not assets:
        raise ValueError('empty release assets')
    for architecture, item in assets.items():
        if not re.fullmatch(r'[a-z0-9_-]+', architecture):
            raise ValueError('invalid architecture ID')
        name = item.get('filename', '')
        if not re.fullmatch(r'[A-Za-z0-9_.-]+\.tar\.xz', name):
            raise ValueError('unsafe archive filename')
        asset_path = path.parent/name
        if not asset_path.is_file() or asset_path.is_symlink():
            raise ValueError('asset missing or symlink: '+name)
        content = asset_path.read_bytes()
        declared = item.get('sha256', '')
        if not SHA.fullmatch(declared) or hashlib.sha256(content).hexdigest() != declared:
            raise ValueError('artifact digest mismatch: '+name)
        if item.get('bytes') != len(content):
            raise ValueError('artifact byte length mismatch: '+name)
        with tarfile.open(fileobj=io.BytesIO(content), mode='r:xz') as archive:
            members=archive.getmembers()
            binary_name=data.get('binary_name')
            if [m.name for m in members] != [binary_name,'METADATA.json'] or not all(m.isfile() for m in members):
                raise ValueError('unsafe archive content: '+name)
            binary=archive.extractfile(members[0]).read(128*1024*1024+1)
            metadata=json.load(archive.extractfile(members[1]))
        if len(binary)>128*1024*1024 or not SHA.fullmatch(item.get('binary_sha256','')) or hashlib.sha256(binary).hexdigest()!=item['binary_sha256']:
            raise ValueError('binary digest mismatch: '+name)
        if (metadata.get('component')!=data['component'] or
            metadata.get('upstream_tag')!=data['upstream_tag'] or
            metadata.get('compressed_binary_sha256')!=item['binary_sha256'] or
            metadata.get('source_archive_sha256')!=item.get('source_sha256')):
            raise ValueError('embedded provenance mismatch: '+name)
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
