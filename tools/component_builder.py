#!/usr/bin/env python3
"""Config-driven verified GitHub Release -> UPX -> deterministic component artifacts.

The build host is not the router. No untrusted archive is extracted to disk.
A passed build is *not* a claim of target-router functional compatibility.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tarfile
import zipfile
import tempfile
import urllib.error
import urllib.request

BASE = Path(__file__).resolve().parents[1]
REPO = "wekingchen/luci-app-component-updater"
USER_AGENT = "component-updater-builder/0.1"
ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]{0,39}$")
REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
TAG_PATTERN = re.compile(r"^v[0-9]+[A-Za-z0-9.+-]*$")
ARCH_PATTERN = re.compile(r"^[a-z0-9_-]+$")
MAX_ARCHIVE = 128 * 1024 * 1024
MAX_BINARY = 128 * 1024 * 1024


class BuildError(RuntimeError):
    pass


def validate_definition(cfg: dict) -> dict:
    if cfg.get("schema") != 1 or not ID_PATTERN.fullmatch(cfg.get("id", "")):
        raise BuildError("invalid component schema/id")
    if not REPO_PATTERN.fullmatch(cfg.get("upstream", {}).get("repository", "")):
        raise BuildError("invalid upstream repository")
    if cfg.get("upstream", {}).get("channel") != "stable":
        raise BuildError("only stable releases are permitted")
    comp = cfg.get("compression", {})
    if comp.get("type") not in ("upx", "none"):
        raise BuildError("unsupported compression mode")
    if comp["type"] == "upx":
        if not re.fullmatch(r"\d+\.\d+\.\d+", comp.get("version", "")):
            raise BuildError("invalid UPX version")
        if comp.get("arguments") != ["--lzma", "--best"]:
            raise BuildError("unexpected UPX arguments; review builder before changing")
    if not isinstance(comp.get("revision"), int) or comp["revision"] < 1:
        raise BuildError("invalid build revision")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", cfg.get("binary", {}).get("archive_member", "")):
        raise BuildError("unsafe binary member")
    template = cfg.get("source_asset_template", "{id}-{tag}-{suffix}")
    if template.count("{tag}") != 1 or template.count("{suffix}") != 1:
        raise BuildError("invalid asset template")
    if not re.fullmatch(r"[a-zA-Z0-9_.{}-]+", template):
        raise BuildError("unsafe asset template")
    targets = cfg.get("platforms", [])
    if not targets or len({t["id"] for t in targets}) != len(targets):
        raise BuildError("missing or duplicate targets")
    for target in targets:
        if not ARCH_PATTERN.fullmatch(target.get("id", "")):
            raise BuildError("invalid target architecture")
        if not re.fullmatch(r"[a-zA-Z0-9_.-]+\.(?:tar\.xz|tar\.gz|zip)", target.get("asset_suffix", "")):
            raise BuildError("invalid archive suffix")
        if not isinstance(target.get("elf_machine"), int):
            raise BuildError("invalid ELF machine")
    return cfg


def definitions(selected: str) -> list[dict]:
    files = sorted((BASE / "components").glob("*.json"))
    data = [validate_definition(json.loads(p.read_text())) for p in files]
    data = [x for x in data if x.get("enabled", False)]
    if selected != "all":
        data = [x for x in data if x["id"] == selected]
        if not data:
            raise BuildError("unknown or disabled component")
    return data


def github_json(url: str, token: str = "") -> dict:
    if not url.startswith("https://api.github.com/repos/"):
        raise BuildError("only GitHub Releases API is allowed")
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=25) as f:
        return json.load(f)


def download(url: str, maximum: int = MAX_ARCHIVE) -> bytes:
    if not url.startswith("https://github.com/"):
        raise BuildError("unexpected download host")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as f:
        content = f.read(maximum + 1)
    if len(content) > maximum:
        raise BuildError("download exceeds maximum size")
    return content


def digest_ok(data: bytes, expected: str) -> str:
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", expected or ""):
        raise BuildError("upstream asset has no valid SHA256 digest")
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected[7:]:
        raise BuildError("upstream digest mismatch")
    return actual


def find_asset(release: dict, name: str) -> dict:
    items = [x for x in release.get("assets", []) if x.get("name") == name]
    if len(items) != 1:
        raise BuildError(f"expected one exact official asset: {name}")
    if not items[0].get("browser_download_url", "").startswith("https://github.com/"):
        raise BuildError("unexpected official asset URL")
    return items[0]


def release_tag(cfg: dict, upstream: str) -> str:
    if not TAG_PATTERN.fullmatch(upstream):
        raise BuildError("unrecognized upstream tag")
    c = cfg["compression"]
    method = "upx" + c["version"].replace(".", "") if c["type"] == "upx" else "raw"
    return f"component-{cfg['id']}-{upstream}-{method}-r{c['revision']}"


def extract_member(blob: bytes, member_name: str, kind: str = "tar.xz") -> bytes:
    if kind in ("tar.xz", "tar.gz"):
        mode = "r:xz" if kind == "tar.xz" else "r:gz"
        with tarfile.open(fileobj=io.BytesIO(blob), mode=mode) as t:
            candidates = [m for m in t.getmembers() if m.name.removeprefix("./") == member_name and m.isfile()]
            if len(candidates) != 1:
                raise BuildError("expected exactly one regular binary in official archive")
            member = candidates[0]
            if member.size > MAX_BINARY:
                raise BuildError("binary too large")
            extracted = t.extractfile(member)
            if extracted is None:
                raise BuildError("could not read binary")
            return extracted.read(MAX_BINARY + 1)
    if kind == "zip":
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            members = [m for m in z.infolist() if m.filename == member_name and not m.is_dir()]
            if len(members) != 1 or members[0].file_size > MAX_BINARY:
                raise BuildError("invalid binary in ZIP archive")
            with z.open(members[0]) as f:
                return f.read(MAX_BINARY + 1)
    raise BuildError("unsupported official archive type")


def source_name(cfg: dict, tag: str, target: dict) -> str:
    return cfg.get("source_asset_template", "{id}-{tag}-{suffix}").format(
        id=cfg["id"], tag=tag, suffix=target["asset_suffix"])


def verify_elf(blob: bytes, machine: int) -> None:
    if (len(blob) < 64 or blob[:5] != b"\x7fELF\x02" or blob[5] != 1
            or struct.unpack_from("<H", blob, 18)[0] != machine):
        raise BuildError("ELF machine/class mismatch")


def upx_binary(version: str, token: str, override: str = "") -> str:
    if override:
        if not Path(override).is_file():
            raise BuildError("UPX override is not a file")
        return override
    release = github_json(f"https://api.github.com/repos/upx/upx/releases/tags/v{version}", token)
    filename = f"upx-{version}-amd64_linux.tar.xz"
    asset = find_asset(release, filename)
    blob = download(asset["browser_download_url"])
    digest_ok(blob, asset.get("digest", ""))
    data = None
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:xz") as t:
        matched = [m for m in t.getmembers() if m.isfile() and m.name.endswith("/upx")]
        if len(matched) != 1 or matched[0].size > 32 * 1024 * 1024:
            raise BuildError("UPX archive invalid")
        data = t.extractfile(matched[0]).read()
    path = Path(tempfile.mkdtemp(prefix="component-upx-")) / "upx"
    path.write_bytes(data)
    path.chmod(0o755)
    return str(path)


def compress(original: bytes, machine: int, upx: str) -> bytes:
    with tempfile.TemporaryDirectory(prefix="component-compress-") as folder:
        path = Path(folder) / "component"
        path.write_bytes(original)
        path.chmod(0o755)
        subprocess.run([upx, "--lzma", "--best", str(path)], check=True, timeout=180)
        subprocess.run([upx, "-t", str(path)], check=True, timeout=60)
        packed = path.read_bytes()
        if len(packed) >= len(original):
            raise BuildError("UPX did not reduce binary size")
        verify_elf(packed, machine)
        subprocess.run([upx, "-d", str(path)], check=True, timeout=120)
        if path.read_bytes() != original:
            raise BuildError("UPX round-trip did not preserve original")
    return packed


def archive(filename: Path, data: bytes, meta: dict, binary_name: str) -> None:
    with tarfile.open(filename, mode="w:xz", preset=6) as f:
        for name, content, mode in [
            (binary_name, data, 0o755),
            ("METADATA.json", (json.dumps(meta, sort_keys=True, indent=2) + "\n").encode(), 0o644),
        ]:
            entry = tarfile.TarInfo(name)
            entry.size, entry.mode, entry.mtime = len(content), mode, 0
            entry.uid, entry.gid = 0, 0
            f.addfile(entry, io.BytesIO(content))


def build_one(cfg: dict, release: dict, target: dict, upx: str, out: Path) -> dict:
    tag = release["tag_name"]
    upstream_name = source_name(cfg, tag, target)
    asset = find_asset(release, upstream_name)
    archive_bytes = download(asset["browser_download_url"])
    origin_sha = digest_ok(archive_bytes, asset.get("digest", ""))
    original = extract_member(archive_bytes, cfg["binary"]["archive_member"], target["asset_suffix"].split(".", 1)[1])
    verify_elf(original, target["elf_machine"])
    packed = compress(original, target["elf_machine"], upx) if cfg["compression"]["type"] == "upx" else original
    method = "upx" + cfg["compression"]["version"].replace(".", "") if cfg["compression"]["type"] == "upx" else "raw"
    name = f"{cfg['id']}-{tag}-openwrt-{target['id']}-{method}-r{cfg['compression']['revision']}.tar.xz"
    metadata = {
        "component": cfg["id"], "upstream_tag": tag, "architecture": target["id"],
        "source_asset": upstream_name, "source_archive_sha256": origin_sha,
        "original_binary_sha256": hashlib.sha256(original).hexdigest(),
        "compressed_binary_sha256": hashlib.sha256(packed).hexdigest(),
        "compression": cfg["compression"]["type"], "upx_version": cfg["compression"].get("version"),
    }
    path = out / name
    archive(path, packed, metadata, cfg["binary"]["archive_member"])
    return {
        "filename": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size, "binary_sha256": metadata["compressed_binary_sha256"],
        "source_sha256": origin_sha, "original_bytes": len(original),
        "compressed_bytes": len(packed),
        "validation": {"elf": "passed", "upx_test": "passed" if cfg["compression"]["type"] == "upx" else "not-applicable", "round_trip": "passed" if cfg["compression"]["type"] == "upx" else "not-applicable", "device_runtime": "unverified"}
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--component", default="all")
    parser.add_argument("--output", default="dist")
    parser.add_argument("--upx", default="", help="verified local UPX binary for tests")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    token = os.environ.get("GITHUB_TOKEN", "")
    for cfg in definitions(args.component):
        upstream = cfg["upstream"]["repository"]
        release = github_json(f"https://api.github.com/repos/{upstream}/releases/latest", token)
        if release.get("draft") or release.get("prerelease"):
            raise BuildError("latest release is not stable")
        tag = release["tag_name"]
        build_tag = release_tag(cfg, tag)
        print(f"{cfg['id']} official={tag} build={build_tag}", flush=True)
        if args.dry_run:
            for target in cfg["platforms"]:
                a = find_asset(release, source_name(cfg, tag, target))
                if not a.get("digest", "").startswith("sha256:"):
                    raise BuildError("missing upstream digest")
                print(f"  {target['id']}: {a['name']} SHA256={a['digest']}")
            continue
        upx = upx_binary(cfg["compression"]["version"], token, args.upx) if cfg["compression"]["type"] == "upx" else ""
        manifest = {
            "schema": 1, "component": cfg["id"], "upstream_repository": upstream,
            "upstream_tag": tag, "release_tag": build_tag,
            "build_revision": cfg["compression"]["revision"],
            "compression": cfg["compression"],
            "binary_name": cfg["binary"]["archive_member"],
            "assets": {}
        }
        for target in cfg["platforms"]:
            result = build_one(cfg, release, target, upx, out)
            manifest["assets"][target["id"].replace("-", "_")] = result
            print(f"  {target['id']} compressed {result['original_bytes']} -> {result['compressed_bytes']}", flush=True)
        (out / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        (out / "release-tag.txt").write_text(build_tag + "\n")


if __name__ == "__main__":
    try:
        main()
    except (BuildError, urllib.error.URLError, subprocess.CalledProcessError, TimeoutError) as err:
        raise SystemExit(f"BUILD FAILED: {err}")
