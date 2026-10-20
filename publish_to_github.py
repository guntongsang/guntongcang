#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publish_to_github.py — 一键发布 github-toolkit 开源包到 GitHub。

用法：
    python publish_to_github.py --token ghp_xxx [--owner guntongsang] [--repo guntongcang] [--src <包目录>]

行为：
    1. 检查仓库是否存在，不存在则创建（public，auto_init 生成初始提交）；
    2. 将包目录下所有文件（README.md / LICENSE / .gitignore / skill/**）通过 contents API 推送到仓库；
    3. 打印仓库 URL。
零依赖（仅标准库）。Token 不落盘。
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"


def die(msg, code=1):
    print(json.dumps({"error": True, "message": msg}, ensure_ascii=False))
    sys.exit(code)


def request(method, path, token, payload=None, params=None):
    url = API + path
    if params:
        qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        if qs:
            url += ("?" if "?" not in url else "&") + qs
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "github-toolkit-publisher/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
            "Authorization": f"Bearer {token}",
        })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", "replace")
        try:
            msg = json.loads(err).get("message", err)
        except Exception:
            msg = err
        return {"error": e.code, "message": msg}


def repo_exists(token, owner, repo):
    r = request("GET", f"/repos/{owner}/{repo}", token)
    return "error" not in r


def ensure_repo(token, owner, repo):
    r = request("GET", f"/repos/{owner}/{repo}", token)
    if "error" not in r:
        print(f"仓库已存在：https://github.com/{owner}/{repo}")
        return True
    if r.get("error") != 404:
        die(f"查询仓库失败：{r.get('message')}")
    r = request("POST", "/user/repos", token, payload={
        "name": repo,
        "description": "GitHub Toolkit — 零依赖的 GitHub 全能力 Agent 技能插件（仓库/代码/Issue/PR/Release/搜索）",
        "private": False,
        "auto_init": True,
    })
    if "error" in r:
        die(f"创建仓库失败：{r.get('error')} {r.get('message')}")
    print(f"仓库已创建：https://github.com/{owner}/{repo}")
    return True


def push_file(token, owner, repo, rel_path, abs_path):
    with open(abs_path, "rb") as f:
        content = f.read().decode("utf-8")
    # 若文件已存在（如 auto_init 生成的 README），先取 sha 再覆盖
    sha = None
    r = request("GET", f"/repos/{owner}/{repo}/contents/{rel_path}", token)
    if "error" not in r and isinstance(r, dict) and r.get("sha"):
        sha = r["sha"]
    payload = {
        "message": f"add {rel_path}",
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
    }
    if sha:
        payload["sha"] = sha
    r = request("PUT", f"/repos/{owner}/{repo}/contents/{rel_path}", token, payload=payload)
    if "error" in r:
        die(f"推送 {rel_path} 失败：{r.get('error')} {r.get('message')}")
    print(f"  ✓ {rel_path}")


def walk_files(src):
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for name in files:
            abs_path = os.path.join(root, name)
            rel_path = os.path.relpath(abs_path, src).replace("\\", "/")
            yield rel_path, abs_path


def main():
    ap = argparse.ArgumentParser(description="一键发布 github-toolkit 到 GitHub")
    ap.add_argument("--token", required=True, help="GitHub Personal Access Token（repo 权限）")
    ap.add_argument("--owner", default="guntongsang", help="GitHub 用户名")
    ap.add_argument("--repo", default="guntongcang", help="仓库名")
    ap.add_argument("--src", default=os.path.dirname(os.path.abspath(__file__)),
                    help="要发布的开源包目录")
    args = ap.parse_args()

    token = args.token
    print(f"==> 检查/创建仓库 {args.owner}/{args.repo}")
    if not ensure_repo(token, args.owner, args.repo):
        sys.exit(1)
    print(f"==> 推送 {args.src} 中的文件")
    files = sorted(walk_files(args.src))
    if not files:
        die("包目录为空，无文件可推送")
    for rel, abs_ in files:
        push_file(token, args.owner, args.repo, rel, abs_)
    print(f"==> 发布完成：https://github.com/{args.owner}/{args.repo}")


if __name__ == "__main__":
    main()
