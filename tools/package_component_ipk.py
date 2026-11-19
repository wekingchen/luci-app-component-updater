#!/usr/bin/env python3
"""Create and inspect OpenWrt-native gzip(tar) IPKs from verified component binaries.

No dependency on dpkg/opkg is required on GitHub Actions. All archive member
names, package metadata and target paths are declared by reviewed component
definitions, never by untrusted GitHub asset content.
"""
from __future__ import annotations
import gzip
import io
import re
import tarfile
from pathlib import PurePosixPath

LABEL=re.compile(r"^[a-z][a-z0-9+.-]{0,60}$")
ARCH=re.compile(r"^[a-z0-9_-]+$")
VERSION=re.compile(r"^[0-9][A-Za-z0-9.+~_-]*$")

def _tar(files: list[tuple[str,bytes,int]]) -> bytes:
    raw=io.BytesIO()
    with tarfile.open(fileobj=raw,mode="w",format=tarfile.USTAR_FORMAT) as t:
        for name, blob, mode in files:
            if not name.startswith("./") or ".." in PurePosixPath(name).parts:
                raise ValueError("unsafe payload path")
            info=tarfile.TarInfo(name)
            info.uid=info.gid=0
            info.mtime=0
            info.mode=mode
            info.size=len(blob)
            t.addfile(info,io.BytesIO(blob))
    packed=io.BytesIO()
    with gzip.GzipFile(filename="",mode="wb",fileobj=packed,mtime=0,compresslevel=6) as gz:
        gz.write(raw.getvalue())
    return packed.getvalue()

def _outer_ipk(files: list[tuple[str,bytes]]) -> bytes:
    """OpenWrt ipkg-build uses gzip(tar) of three files, not Debian ar."""
    if [name for name,_ in files]!=[
        "debian-binary","data.tar.gz","control.tar.gz"
    ]:
        raise ValueError("invalid OpenWrt outer archive member order")
    return _tar([("./"+name,data,0o644) for name,data in files])


def open_ipk(blob: bytes) -> dict[str, bytes]:
    if not blob.startswith(bytes((0x1f,0x8b))):
        raise ValueError("not an OpenWrt gzip(tar) IPK")
    members={}
    try:
        with tarfile.open(fileobj=io.BytesIO(blob),mode="r:gz") as archive:
            entries=archive.getmembers()
            if [e.name for e in entries]!=[
                "./debian-binary","./data.tar.gz","./control.tar.gz"
            ] or any(not e.isfile() for e in entries):
                raise ValueError("unexpected OpenWrt IPK archive entries")
            for entry in entries:
                blob_member=archive.extractfile(entry).read()
                if len(blob_member)>256*1024*1024:
                    raise ValueError("oversized IPK member")
                members[entry.name.removeprefix("./")]=blob_member
    except (tarfile.TarError,OSError) as exc:
        raise ValueError("invalid IPK gzip(tar) archive") from exc
    if members["debian-binary"]!=bytes((50,46,48,10)):
        raise ValueError("unsupported IPK packaging version")
    return members


def build_ipk(*, package: str, version: str, architecture: str, target: str,
              binary: bytes, depends: list[str] | None = None) -> bytes:
    if not LABEL.fullmatch(package) or not VERSION.fullmatch(version) or not ARCH.fullmatch(architecture):
        raise ValueError("unsafe package metadata")
    if not target.startswith("/usr/bin/") or not re.fullmatch(r"/usr/bin/[A-Za-z0-9_.-]+",target):
        raise ValueError("unsafe or unsupported install target")
    dependencies=depends if depends is not None else ["libc"]
    if not dependencies or any(not LABEL.fullmatch(d) for d in dependencies):
        raise ValueError("unsafe package dependency")
    control=(
        f"Package: {package}\nVersion: {version}\nArchitecture: {architecture}\n"
        f"Depends: {', '.join(dependencies)}\n"
        "Maintainer: Component Updater <https://github.com/wekingchen/luci-app-component-updater>\n"
        "Section: net\nPriority: optional\n"
        "Description: Official upstream binary repackaged for OpenWrt with UPX\n"
    ).encode("utf-8")
    control_tar=_tar([("./control",control,0o644)])
    data_tar=_tar([("."+target,binary,0o755)])
    return _outer_ipk([
        ("debian-binary",bytes((50,46,48,10))),
        ("data.tar.gz",data_tar),
        ("control.tar.gz",control_tar)
    ])

def inspect_ipk(blob: bytes, target: str) -> tuple[dict[str,str],bytes]:
    members=open_ipk(blob)
    with tarfile.open(fileobj=io.BytesIO(members["control.tar.gz"]),mode="r:gz") as ct:
        controls=ct.getmembers()
        if [m.name for m in controls]!=["./control"] or not controls[0].isfile():
            raise ValueError("invalid control entries")
        metadata={}
        for line in ct.extractfile(controls[0]).read().decode("utf-8").splitlines():
            if ": " in line:
                k,v=line.split(": ",1)
                metadata[k]=v
    with tarfile.open(fileobj=io.BytesIO(members["data.tar.gz"]),mode="r:gz") as dt:
        entries=dt.getmembers()
        if [m.name for m in entries]!=["."+target] or not entries[0].isfile():
            raise ValueError("IPK includes unexpected files")
        binary=dt.extractfile(entries[0]).read()
        if entries[0].mode & 0o111 == 0:
            raise ValueError("installed binary not executable")
    return metadata,binary

def package_version(upstream_tag: str, revision: int) -> str:
    match=re.fullmatch(r"v([0-9]+(?:\.[0-9]+)*)(?:-([0-9]+))?",upstream_tag)
    if not match or revision<1:
        raise ValueError("unsupported opkg version scheme")
    core=match.group(1)
    extra=("."+match.group(2)) if match.group(2) else ""
    return f"{core}{extra}-r{revision}"
