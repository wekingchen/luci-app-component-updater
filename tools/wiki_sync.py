#!/usr/bin/env python3
"""Stage managed Wiki Markdown safely; never delete or overwrite unrelated pages."""
import argparse
from pathlib import Path
from check_docs import PAGES


def sync(source, target):
    source, target = Path(source), Path(target)
    if not source.is_dir() or not target.is_dir():
        raise ValueError("source/target must be directories")
    changes = []
    for name in PAGES:
        src, dst = source / name, target / name
        if not src.is_file() or src.is_symlink():
            raise ValueError(f"Invalid Wiki source: {name}")
        if dst.is_symlink() or (dst.exists() and not dst.is_file()):
            raise ValueError(f"Unsafe Wiki destination: {name}")
        data = src.read_bytes()
        if not data or not data.lstrip().startswith((b"#", b"**")):
            raise ValueError(f"Invalid Wiki content: {name}")
        if not dst.exists() or dst.read_bytes() != data:
            dst.write_bytes(data)
            changes.append(name)
    return changes


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("wiki-src"))
    parser.add_argument("--target", type=Path, required=True)
    opts = parser.parse_args()
    print("Wiki sync changed:", ", ".join(sync(opts.source, opts.target)) or "none")
