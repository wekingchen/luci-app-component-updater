#!/usr/bin/env python3
"""Native-old-opkg archive acceptance fixture. Never touches a real device."""
import argparse
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
      # Verify the 21.02 opkg target ar parsing prerequisites independently.
      pos=8
      assert b.startswith(b"!<arch>\n")
      while pos<len(b):
          head=b[pos:pos+60]
          assert not head[:16].strip().endswith(b"/"),head[:16]
          size=int(head[48:58].decode().strip())
          pos+=60+size+size%2
      assert pos==len(b)
    print("Created isolated x86_64 OpenWrt 21.02 opkg round-trip fixture")

if __name__=="__main__":
    main()
