#!/usr/bin/env python3
"""Create and inspect standard Debian ar-format IPKs from verified component binaries.

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

def _ar(members: list[tuple[str,bytes]]) -> bytes:
    out=io.BytesIO()
    out.write(b"!<arch>\n")
    for name,data in members:
        if len(name)>15 or not re.fullmatch(r"[A-Za-z0-9.-]+",name):
            raise ValueError("invalid ar member")
        header=(f"{name+'/':<16}{0:<12}{0:<6}{0:<6}{'100644':<8}{len(data):<10}`\n").encode("ascii")
        if len(header)!=60:
            raise ValueError("invalid ar header")
        out.write(header)
        out.write(data)
        if len(data)%2: out.write(b"\n")
    return out.getvalue()

def open_ipk(blob: bytes) -> dict[str, bytes]:
    if not blob.startswith(b"!<arch>\n"):
        raise ValueError("not an ar IPK")
    members={}
    pos=8
    while pos < len(blob):
        if pos+60>len(blob): raise ValueError("truncated ar header")
        header=blob[pos:pos+60]
        name=header[:16].decode("ascii").strip().rstrip("/")
        if header[58:]!=b"`\n" or not header[48:58].decode("ascii").strip().isdigit():
            raise ValueError("invalid ar header")
        size=int(header[48:58].decode("ascii").strip())
        pos+=60
        if pos+size>len(blob) or name in members:
            raise ValueError("truncated or duplicated ar member")
        members[name]=blob[pos:pos+size]
        pos+=size+(size%2)
    if set(members)!={"debian-binary","control.tar.gz","data.tar.gz"}:
        raise ValueError("unknown IPK archive members")
    if members["debian-binary"]!=b"2.0\n":
        raise ValueError("unsupported IPK version")
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
    return _ar([("debian-binary",b"2.0\n"),("control.tar.gz",control_tar),("data.tar.gz",data_tar)])

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
