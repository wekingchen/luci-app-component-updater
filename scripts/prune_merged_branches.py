#!/usr/bin/env python3
"""Safely prune development branches whose exact heads were merged to main.

The branch head MUST equal the recorded merged PR head. This matters for squash
merges: checking ancestry alone would incorrectly treat squash-merged branches
as unmerged. Never remove branches used by open PRs or protected branches.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from urllib.parse import quote

ALLOWED = re.compile(r"^(?:feat|fix|chore|docs|test|refactor)/[A-Za-z0-9._/-]+$")
REPOSITORY = "wekingchen/luci-app-component-updater"
PAGE_SIZE = 100


def gh_api(url: str, method: str = "GET"):
    cmd = ["gh", "api"]
    if method != "GET":
        cmd.extend(["-X", method])
    cmd.append(url)
    res = subprocess.run(cmd, check=True, capture_output=True, text=True)
    if method != "GET":
        return None
    return json.loads(res.stdout)


def paged(path: str):
    items = []
    page = 1
    while True:
        separator = "&" if "?" in path else "?"
        part = gh_api("repos/%s/%s%sper_page=%d&page=%d" % (REPOSITORY, path, separator, PAGE_SIZE, page))
        if not isinstance(part, list):
            raise RuntimeError("GitHub API returned a non-list response")
        items.extend(part)
        if len(part) < PAGE_SIZE:
            return items
        page += 1


def source_repo(pr):
    return (pr.get("head", {}).get("repo") or {}).get("full_name")



# One-time cleanup of three obsolete release-development refs after V0.5.6 Stable.
# These refs are NEVER added to ALLOWED: other release/* branches remain protected.
# Remove this helper and the workflow env flag in a subsequent cleanup PR.
ONE_TIME_V056_RELEASE_BRANCHES = {
    "release/manual-v0.5.6-rc3": (
        "bfba37853ba0f702a62cc9dfe7545e224dfdf442", 21
    ),
    "release/v0.5.6-scope-mt3600be-ax6s": (
        "08ef05e153d8651b877487b4d5b031c491c26a07", 22
    ),
    "release/v0.5.6-stable-scoped": (
        "91008d098080552e8579872ec52f1bb9cb87b366", None
    ),
}
ONE_TIME_V056_RELEASE_ASSETS = {
    "luci-app-component-updater-0.5.6-r3.apk":
        "sha256:5cd154cca438b599d29b5332eefa37c08043c4b6287aa386f591de7f2bff3cc7",
    "luci-app-component-updater_0.5.6-3_all.ipk":
        "sha256:6b6fcbd0c037d9083b47a49c0a17cd668a52de6558e4c0364957dc481d6aecdc",
    "SHA256SUMS.txt":
        "sha256:51f14f2a1ee4a8da3a4a309edd32fb142eaff63d8400780e2864ba077d588a27",
}


def prune_one_time_v056_release_branches(branches, merged, open_branches):
    """Delete only the reviewed V0.5.6 stale refs after checking stable assets.

    A squash-merged PR has a different merge SHA from the former branch HEAD.
    Check the HEAD against the merged PR's original commit, not ancestry.
    The third ref was never a PR: its exact HEAD must still be an ancestor of main.
    """
    release = gh_api("repos/%s/releases/tags/luci-app-component-updater-v0.5.6" % REPOSITORY)
    published = {
        a.get("name"): a.get("digest")
        for a in release.get("assets", [])
        if a.get("state") == "uploaded"
    }
    if (release.get("tag_name") != "luci-app-component-updater-v0.5.6"
            or release.get("draft") is not False
            or release.get("prerelease") is not False
            or published != ONE_TIME_V056_RELEASE_ASSETS):
        raise RuntimeError("V0.5.6 Stable release or asset digests differ; refusing release ref cleanup")

    deleted = []
    for name, (expected_head, merged_pr_number) in ONE_TIME_V056_RELEASE_BRANCHES.items():
        branch = branches.get(name)
        if not branch:
            print("已不存在：%s" % name)
            continue
        if branch.get("protected") or name in open_branches:
            print("保留：%s（受保护或仍关联开放 PR）" % name)
            continue
        current = (branch.get("commit") or {}).get("sha")
        if current != expected_head:
            print("保留：%s（当前 HEAD 不再是已审计的旧提交）" % name)
            continue
        if merged_pr_number is not None:
            if not any(
                pr.get("number") == merged_pr_number
                and pr.get("merged_at")
                and (pr.get("base") or {}).get("ref") == "main"
                and source_repo(pr) == REPOSITORY
                and (pr.get("head") or {}).get("ref") == name
                and (pr.get("head") or {}).get("sha") == expected_head
                for pr in merged
            ):
                print("保留：%s（未找到对应 HEAD 的已合并 PR）" % name)
                continue
        else:
            comparison = gh_api(
                "repos/%s/compare/%s...main" % (REPOSITORY, expected_head)
            )
            if (comparison.get("behind_by") != 0
                    or comparison.get("status") not in ("ahead", "identical")):
                print("保留：%s（旧基线并非当前 main 的祖先）" % name)
                continue

        gh_api("repos/%s/git/refs/heads/%s" %
               (REPOSITORY, quote(name, safe="/")), method="DELETE")
        print("已清理一次性旧发布分支：%s" % name)
        deleted.append(name)
    return deleted


def clean():
    if os.environ.get("GITHUB_REPOSITORY") != REPOSITORY:
        raise RuntimeError("Repository does not match the configured cleanup target")

    branches = {b["name"]: b for b in paged("branches")}
    merged = paged("pulls?state=closed")  # paged() appends pagination parameters.
    opened = paged("pulls?state=open")

    open_branches = {
        p.get("head", {}).get("ref")
        for p in opened if source_repo(p) == REPOSITORY
    }
    approved = {}
    for pr in merged:
        head = pr.get("head") or {}
        base = pr.get("base") or {}
        name = head.get("ref") or ""
        if (pr.get("merged_at") and base.get("ref") == "main"
                and source_repo(pr) == REPOSITORY and ALLOWED.fullmatch(name)):
            approved.setdefault(name, []).append((head.get("sha"), pr.get("number")))

    deleted = []
    for name, records in sorted(approved.items()):
        b = branches.get(name)
        if not b or b.get("protected") or name in open_branches:
            print("保留：%s（不存在、受保护或仍有关联 PR）" % name)
            continue
        current = (b.get("commit") or {}).get("sha")
        matches = [number for sha, number in records if sha and sha == current]
        if not matches:
            print("保留：%s（合并后已有新提交）" % name)
            continue
        ref = "repos/%s/git/refs/heads/%s" % (REPOSITORY, quote(name, safe="/"))
        gh_api(ref, method="DELETE")
        print("已清理：%s（对应已合并 PR #%s）" % (name, matches[0]))
        deleted.append(name)
    if os.environ.get("ONE_TIME_V056_RELEASE_CLEANUP") == "1":
        deleted.extend(prune_one_time_v056_release_branches(
            branches, merged, open_branches
        ))
    print("清理完成：%d 个分支；main 与未合并代码不受影响" % len(deleted))
    return deleted


if __name__ == "__main__":
    clean()
