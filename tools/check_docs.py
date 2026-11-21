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


def _publish_condition(source, job):
    """Find the job-level 'if', not a comment or a step-level condition."""
    match = re.search(r"(?m)^  " + re.escape(job) + r":\s*$", source)
    if not match:
        return ""
    body = source[match.end():]
    next_job = re.search(r"(?m)^  [a-zA-Z][\w-]+:\s*$", body)
    if next_job:
        body = body[:next_job.start()]
    match = re.search(r"(?m)^    if:\s*(.*)$", body)
    return match.group(1).strip() if match else ""


def release_policy_errors(ci, apk):
    errors = []
    jobs = (
        ("manager", ci, "publish-luci-candidate"),
        ("ax6s", apk, "publish-native-apk-candidate"),
    )
    for name, source, job in jobs:
        condition = _publish_condition(source, job)
        for text, explanation in (
            ("vars.AX6S_APK_AUTO_PUBLISH == 'true'", "发布 job 缺少实体设备门禁"),
            ("github.ref == 'refs/heads/main'", "发布 job 未限定 main"),
            ("github.event_name != 'pull_request'", "发布 job 没有拒绝 PR"),
        ):
            if text not in condition:
                errors.append(f"{name}: {explanation}")
        if "||" in condition or "publish-v0.5.0-rc1" in condition:
            errors.append(f"{name}: 禁止在发布条件中用 OR 绕过实机验收")
        for text, explanation in (
            ("--latest=false", "可能覆盖 latest"),
            ("--prerelease", "预发布标记丢失"),
            ("SHA256SUMS.txt", "缺少校验文件"),
        ):
            if text not in source:
                errors.append(f"{name}: {explanation}")
    if "gh release delete" in ci or "gh release delete" in apk:
        errors.append("发布流程不得删除旧 Release")
    return errors



def current_stable_docs_errors(root, version):
    """Catch stale 'latest release' claims; preserve explicitly historical records."""
    if version != "0.5.6":
        # Future version changes require their own release decision, not a V0.5.6 assertion.
        return []
    errors = []
    tag_url = ("https://github.com/wekingchen/luci-app-component-updater/"
               "releases/tag/luci-app-component-updater-v0.5.6")
    for rel in ("README.md", "wiki-src/Home.md",
                "wiki-src/Operations-and-Troubleshooting.md",
                "wiki-src/Release-and-Verification.md"):
        source = (root / rel).read_text(encoding="utf-8")
        if tag_url not in source:
            errors.append(f"{rel}: 未链接当前 V0.5.6 Stable 正式版")
    expected = {
        "README.md": ("当前正式版：V0.5.6 Stable", "N1 不需要实机测试"),
        "wiki-src/Home.md": ("当前正式版本：V0.5.6 Stable", "N1"),
        "docs/manual-manager-v0.5.6-stable.md": ("已完成的一次性自动发布", "已于 2026-11-21"),
        "docs/ax6s-apk-compatibility.md": ("V0.5.6", "正式发布 Stable"),
        "docs/product-ui-acceptance.md": ("历史验收档案", "不是 V0.5.6 Stable 的当前发布状态"),
    }
    for rel, snippets in expected.items():
        source = (root / rel).read_text(encoding="utf-8")
        for snippet in snippets:
            if snippet not in source:
                errors.append(f"{rel}: 缺少已发布稳定版事实: {snippet}")
    old_claims = {
        "README.md": ("已公开的管理器仍为 **V0.5.0 RC1**",),
        "wiki-src/Home.md": ("完整设备验收前，只允许 RC/prerelease",),
        "wiki-src/Operations-and-Troubleshooting.md": ("从 [管理器 V0.5.0 RC1 Release]",),
        "docs/ax6s-apk-compatibility.md": ("整机完整验收和稳定版资格尚未达到",),
    }
    for rel, claims in old_claims.items():
        source = (root / rel).read_text(encoding="utf-8")
        for claim in claims:
            if claim in source:
                errors.append(f"{rel}: 仍把历史 RC 状态写成当前状态: {claim}")
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
        errors.extend(current_stable_docs_errors(root, v))
        if f"V{v}" not in readme or f"V{v}" not in read(root, "wiki-src/Home.md", errors):
            errors.append(f"README/Wiki 当前版本未同步 V{v}")
    return errors


if __name__ == "__main__":
    findings = validate()
    for finding in findings:
        print("ERROR:", finding)
    print(f"Docs contract: {'FAIL' if findings else 'PASS'} ({len(PAGES)} Wiki pages)")
    sys.exit(bool(findings))
