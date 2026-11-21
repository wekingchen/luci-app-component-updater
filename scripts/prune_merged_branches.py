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
    print("清理完成：%d 个分支；main 与未合并代码不受影响" % len(deleted))
    return deleted


if __name__ == "__main__":
    clean()
