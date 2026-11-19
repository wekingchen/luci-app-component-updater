#!/usr/bin/env python3
"""Build a small architecture-independent IPK for CI bootstrapping/testing.
For official feeds use the OpenWrt Makefile/SDK instead.
"""
from pathlib import Path
import argparse
import io
import tarfile
from package_component_ipk import _outer_ipk
import tempfile

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "luci-app-component-updater"
NAME = "luci-app-component-updater"
VERSION = "0.2.1-1"


def create_tar(path: Path, files: list[tuple[str, bytes, int]]) -> None:
    """OpenWrt opkg does not create every missing parent directory for tar files.

    Emit explicit directory entries before files to permit fresh installations
    into a minimal rootfs (not merely extraction by Python tarfile).
    """
    directories=set()
    for name, _, _ in files:
        if not name.startswith("./") or "/../" in name or name.endswith("/"):
            raise ValueError("unsafe package file target")
        parts=name[2:].split("/")
        if not all(parts):
            raise ValueError("empty package file path")
        for i in range(1,len(parts)):
            directories.add("./"+"/".join(parts[:i]))
    with tarfile.open(path, "w:gz") as t:
        for name in sorted(directories,key=lambda x:(x.count("/"),x)):
            entry=tarfile.TarInfo(name+"/")
            entry.type=tarfile.DIRTYPE
            entry.mode=0o755
            entry.uid=entry.gid=entry.mtime=0
            t.addfile(entry)
        for name, data, mode in files:
            entry=tarfile.TarInfo(name)
            entry.size,entry.mode,entry.uid,entry.gid,entry.mtime=len(data),mode,0,0,0
            t.addfile(entry,io.BytesIO(data))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="dist")
    args = parser.parse_args()
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        (folder / "debian-binary").write_text("2.0\n")
        control = ("Package: luci-app-component-updater\nVersion: " + VERSION +
                   "\nArchitecture: all\nMaintainer: wekingchen\n" +
                   "Depends: luci-base, rpcd, jsonfilter, libubox, opkg\n" +
                   "Section: luci\nDescription: GitHub native IPK updater (NaiveProxy adapter)\n")
        postinst = ("#!/bin/sh\n[ -n \"${IPKG_INSTROOT:-}\" ] && exit 0\n"
                    "rm -f /tmp/luci-indexcache /tmp/luci-modulecache/* 2>/dev/null || true\n"
                    "[ ! -x /etc/init.d/rpcd ] || /etc/init.d/rpcd restart >/dev/null 2>&1 || true\n"
                    "exit 0\n")
        create_tar(folder / "control.tar.gz", [
            ("./control", control.encode(), 0o644),
            ("./conffiles", b"/etc/config/component-updater\n", 0o644),
            ("./postinst", postinst.encode(), 0o755),
        ])
        data = []
        for path in (APP / "root").rglob("*"):
            if path.is_file():
                target = path.relative_to(APP / "root").as_posix()
                mode = 0o755 if target in ("usr/sbin/component-updaterctl", "usr/libexec/rpcd/component-updater", "usr/libexec/component-updater/device-readonly-acceptance.sh", "usr/libexec/component-updater/device-live-acceptance.sh") else 0o644
                data.append(("./" + target, path.read_bytes(), mode))
        for path in (APP / "htdocs").rglob("*"):
            if path.is_file():
                target = "www/" + path.relative_to(APP / "htdocs").as_posix()
                data.append(("./" + target, path.read_bytes(), 0o644))
        create_tar(folder / "data.tar.gz", sorted(data))
        dest = output / f"{NAME}_{VERSION}_all.ipk"
        dest.write_bytes(_outer_ipk([
            ("debian-binary", (folder/"debian-binary").read_bytes()),
            ("data.tar.gz", (folder/"data.tar.gz").read_bytes()),
            ("control.tar.gz", (folder/"control.tar.gz").read_bytes()),
        ]))
        print(dest)


if __name__ == "__main__":
    main()
