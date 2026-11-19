#!/usr/bin/env python3
"""Offline Wiki/link/version/release-policy checks. Does not prove hardware or Wiki publication."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = (
    "Home.md", "_Sidebar.md", "System-Architecture.md",
    "Compatibility-and-Devices.md", "Security-and-Recovery.md",
    "Operations-and-Troubleshooting.md", "Release-and-Verification.md",
    "Developer-Guide.md",
)
LINKS = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def read(root, rel, errors):
    file = root / rel
    if not file.is_file():
        errors.append(f"缺少文件: {rel}")
        return ""
    return file.read_text(encoding="utf-8")


def link_errors(root, rel, wiki=False):
    errors = []
    text = read(root, rel, errors)
    # Fenced code is not navigational Markdown.
    text = re.sub(r"(?ms)^(?:\x60{3,}|~{3,}).*?^(?:\x60{3,}|~{3,})[ \t]*$", "", text)
    for match in LINKS.finditer(text):
        url = match.group(1).strip().split()[0]
        target = url.split("#", 1)[0].split("?", 1)[0]
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        if target.startswith("/"):
            errors.append(f"{rel}: 仓库绝对路径: {url}")
            continue
        base = root / ("wiki-src" if wiki else str(Path(rel).parent))
        dest = (base / target).resolve()
        if wiki and not dest.suffix:
            dest = dest.with_suffix(".md")
        if not dest.is_relative_to(root.resolve()) or not dest.exists():
            errors.append(f"{rel}: 链接无效: {url}")
    return errors


def release_policy_errors(ci, apk):
    errors = []
    for name, source in (("manager", ci), ("ax6s", apk)):
        for text, explanation in (
            ("vars.AX6S_APK_AUTO_PUBLISH == 'true'", "缺少实体设备门禁"),
            ("github.ref == 'refs/heads/main'", "发布不限于 main"),
            ("github.event_name != 'pull_request'", "PR 可能发布"),
            ("--latest=false", "可能覆盖 latest"),
            ("--prerelease", "预发布标记丢失"),
            ("SHA256SUMS.txt", "缺少校验文件"),
        ):
            if text not in source:
                errors.append(f"{name}: {explanation}")
    if "gh release delete" in ci or "gh release delete" in apk:
        errors.append("发布流程不得删除旧 Release")
    return errors


def validate(root=ROOT):
    errors = []
    required = [
        "AGENTS.md", "README.md", "docs/project-governance.md",
        "docs/acceptance-gates.md", "docs/ax6s-hardware-acceptance-checklist.md",
        "tools/wiki_sync.py", ".github/workflows/wiki-publish.yml",
        "luci-app-component-updater/Makefile", "tools/package_ipk.py",
    ]
    texts = {p: read(root, p, errors) for p in required}
    for name in PAGES:
        rel = f"wiki-src/{name}"
        read(root, rel, errors)
        errors.extend(link_errors(root, rel, wiki=True))
    extras = {p.name for p in (root / "wiki-src").glob("*.md")} - set(PAGES)
    if extras:
        errors.append(f"新增 Wiki 页面须纳入同步清单: {sorted(extras)}")
    sidebar = read(root, "wiki-src/_Sidebar.md", errors)
    for name in PAGES:
        if name != "_Sidebar.md" and f"({name})" not in sidebar:
            errors.append(f"侧边栏缺少: {name}")
    for rel in ("README.md", "AGENTS.md", "docs/project-governance.md"):
        errors.extend(link_errors(root, rel))
    agents = texts["AGENTS.md"]
    for rel in ("docs/project-governance.md", "docs/acceptance-gates.md",
                "docs/ax6s-hardware-acceptance-checklist.md", "wiki-src/Home.md"):
        if rel not in agents:
            errors.append(f"AGENTS.md 缺少必读项: {rel}")
    readme = texts["README.md"]
    if not all(s in readme for s in ("AGENTS.md", "wiki-src/", "docs/project-governance.md")):
        errors.append("README 知识库与开发约束入口不完整")
    ci = read(root, ".github/workflows/ci.yml", errors)
    apk = read(root, ".github/workflows/ax6s-apk-build.yml", errors)
    wiki = texts[".github/workflows/wiki-publish.yml"]
    if "python3 tools/check_docs.py" not in ci:
        errors.append("主 CI 没有执行文档合约验证")
    if "wiki-src/**" not in wiki or "pull_request_target" in wiki:
        errors.append("Wiki 发布来源或秘钥边界异常")
    errors.extend(release_policy_errors(ci, apk))
    if "AX6S_APK_AUTO_PUBLISH" not in texts["docs/project-governance.md"]:
        errors.append("知识治理缺少自动发布风险声明")
    if "AX6S_APK_AUTO_PUBLISH" not in texts["docs/ax6s-hardware-acceptance-checklist.md"]:
        errors.append("验收待办缺少自动发布门禁")
    make = texts["luci-app-component-updater/Makefile"]
    version = re.search(r"^PKG_VERSION:=([^\s]+)$", make, re.M)
    rev = re.search(r"^PKG_RELEASE:=(\d+)$", make, re.M)
    if not version or not rev:
        errors.append("管理器 Makefile 未声明版本")
    else:
        v, r = version.group(1), rev.group(1)
        for package in (f"luci-app-component-updater_{v}-{r}_all.ipk",
                        f"luci-app-component-updater-{v}-r{r}.apk"):
            if package not in ci:
                errors.append(f"CI 双包版本不一致: {package}")
        if f'VERSION = "{v}-{r}"' not in texts["tools/package_ipk.py"]:
            errors.append("IPK 打包版本不同于 Makefile")
        if f"V{v}" not in readme or f"V{v}" not in read(root, "wiki-src/Home.md", errors):
            errors.append(f"README/Wiki 当前版本未同步 V{v}")
    return errors


if __name__ == "__main__":
    findings = validate()
    for finding in findings:
        print("ERROR:", finding)
    print(f"Docs contract: {'FAIL' if findings else 'PASS'} ({len(PAGES)} Wiki pages)")
    sys.exit(bool(findings))
