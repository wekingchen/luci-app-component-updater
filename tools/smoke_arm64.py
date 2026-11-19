#!/usr/bin/env python3
"""Execute both reviewed AArch64 native-IPK payloads on native ARM64 GitHub Actions runners.

A native Linux ARM64 --version smoke test is not a replacement for real GL-MT3600BE/N1
runtime acceptance, but it catches unusable UPX stubs and ABI regressions
before Release publication.
"""
import argparse
import json
import platform
import re
import subprocess
import tempfile
from pathlib import Path
from package_component_ipk import inspect_ipk

def verify(manifest: Path) -> None:
    data=json.loads(manifest.read_text())
    if not re.fullmatch(r'v[0-9]+(?:\.[0-9]+)+(?:-[0-9]+)?',data['upstream_tag']):
        raise ValueError('unexpected official version')
    expected=data['upstream_tag'].removeprefix('v').split('-')[0]
    for key,asset in sorted(data['assets'].items()):
        if asset['format']!='ipk' or asset['package']!='naiveproxy':
            raise ValueError('unexpected component IPK')
        path=manifest.parent / asset['filename']
        metadata,binary=inspect_ipk(path.read_bytes(),'/usr/bin/naive')
        if metadata['Architecture']!=asset['package_arch']:
            raise ValueError('Architecture mismatch')
        with tempfile.TemporaryDirectory(prefix='component-qemu-') as td:
            program=Path(td)/'naive'
            program.write_bytes(binary)
            program.chmod(0o755)
            if platform.machine().lower() not in ('aarch64','arm64'):
                raise RuntimeError('Native ARM64 runner required')
            result=subprocess.run([str(program),'--version'],capture_output=True,text=True,timeout=45)
            if result.returncode:
                raise RuntimeError(f'Native ARM64 execution failed (exit={result.returncode}) '
                                   f'stdout={result.stdout!r}, stderr={result.stderr!r}')
            displayed=(result.stdout+result.stderr).strip().splitlines()
            if not displayed or displayed[0]!=f'naive {expected}':
                raise ValueError(f'Native ARM64 version mismatch for {key}: {displayed!r}')
        print('Native AArch64 verified',key,expected,flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--manifest',type=Path,required=True)
    verify(ap.parse_args().manifest)
