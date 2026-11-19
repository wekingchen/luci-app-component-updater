#!/usr/bin/env python3
"""Native-old-opkg archive acceptance fixture. Never touches a real device."""
import argparse
import io
import tarfile
import hashlib
from pathlib import Path
from package_component_ipk import build_ipk

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    args=p.parse_args()
    tmp=args.root/"tmp"
    tmp.mkdir(parents=True,exist_ok=True)
    cases={
      "old":("150.0.7871.63.1-r1",b"#!/bin/sh\nprintf 'naive 150.0.7871.63\\n'\n"),
      "new":("154.0.8037.49.5-r3",b"#!/bin/sh\nprintf 'naive 154.0.8037.49\\n'\n"),
      "repair":("154.0.8037.49.5-r3",b"#!/bin/sh\nprintf 'naive 154.0.8037.49 (reinstalled)\\n'\n")
    }
    for label,(version,content) in cases.items():
      b=build_ipk(package="naiveproxy",version=version,architecture="x86_64",
                  target="/usr/bin/naive",binary=content,depends=["libc"])
      (tmp/f"naive-{label}.ipk").write_bytes(b)
      (tmp/f"naive-{label}.sha").write_text(hashlib.sha256(content).hexdigest()+"  /usr/bin/naive\n")
      with tarfile.open(fileobj=io.BytesIO(b),mode='r:gz') as archive:
          assert archive.getnames()==[
              './debian-binary','./data.tar.gz','./control.tar.gz']
    print("Created isolated x86_64 OpenWrt 21.02 opkg round-trip fixture")

if __name__=="__main__":
    main()
