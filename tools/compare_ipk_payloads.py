#!/usr/bin/env python3
"""Compare immutable manager IPKs by their installed payload, not gzip headers.

The original V0.3.0 RC1 used tarfile's nondeterministic gzip writer. Two
archives may have identical installed files and modes but different SHA256
values. This checker verifies the published asset against the published
SHA256SUMS first, then ignores only compression/archiving timestamps.
A changed payload still fails closed and requires a new release version.
"""
from __future__ import annotations

import hashlib
import io
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile

from package_component_ipk import open_ipk

MAX_ARCHIVE = 16 * 1024 * 1024
MAX_MEMBER = 16 * 1024 * 1024


def verify_release_sum(published: Path, checksum: Path) -> str:
    """Require the downloaded published IPK to match its Release checksum."""
    expected = []
    for line in checksum.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == published.name:
            if not re.fullmatch(r"[0-9a-f]{64}",parts[0]):
                raise ValueError("invalid published SHA256 digest")
            expected.append(parts[0])
    if len(expected) != 1:
        raise ValueError("missing or ambiguous published checksum")
    digest = hashlib.sha256(published.read_bytes()).hexdigest()
    if digest != expected[0]:
        raise ValueError("published IPK failed its release checksum")
    return digest


def semantic_manifest(blob: bytes) -> tuple:
    """Compare all install-relevant tar entries, modes and ownership.

    Disallow links, duplicate paths, absolute paths, traversal and unsafe types.
    A mismatch in any of the control or data members prevents silent reuse of
    an existing release tag.
    """
    if len(blob) > MAX_ARCHIVE:
        raise ValueError("oversized manager archive")
    outer = open_ipk(blob)
    result = [("debian-binary",outer["debian-binary"])]
    for layer in ("data.tar.gz","control.tar.gz"):
        members = []
        seen = set()
        with tarfile.open(fileobj=io.BytesIO(outer[layer]),mode="r:gz") as archive:
            for item in archive:
                name = item.name
                path = PurePosixPath(name)
                if not name.startswith("./") or ".." in path.parts or name in seen:
                    raise ValueError("unsafe or duplicated member path")
                if not (item.isfile() or item.isdir()) or item.size > MAX_MEMBER:
                    raise ValueError("unsupported or oversized package member")
                seen.add(name)
                payload = b""
                if item.isfile():
                    payload = archive.extractfile(item).read(MAX_MEMBER + 1)
                    if len(payload) != item.size or len(payload) > MAX_MEMBER:
                        raise ValueError("invalid member size")
                members.append((name,"file" if item.isfile() else "dir",
                                item.mode,item.uid,item.gid,len(payload),
                                hashlib.sha256(payload).hexdigest()))
        result.append((layer,tuple(sorted(members))))
    return tuple(result)


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print("usage: compare_ipk_payloads.py candidate.ipk published.ipk SHA256SUMS.txt",file=sys.stderr)
        return 2
    candidate,published,checksums = (Path(p) for p in argv[1:])
    try:
        verify_release_sum(published,checksums)
        if semantic_manifest(candidate.read_bytes()) != semantic_manifest(published.read_bytes()):
            raise ValueError("published IPK payload differs: bump the manager version")
    except (ValueError,OSError,tarfile.TarError) as exc:
        print("Immutable release check failed: "+str(exc),file=sys.stderr)
        return 1
    print("Published IPK content is unchanged; gzip metadata differences ignored.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
