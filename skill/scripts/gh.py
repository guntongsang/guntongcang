#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
github-toolkit / gh.py
======================
Zero-dependency GitHub REST API CLI for AI agents (Python 3.8+ standard library only).

Authentication:
  - Environment variable GITHUB_TOKEN, or
  - --token <TOKEN> on any command.

Usage:
  python gh.py <group> <action> [options]

Groups:
  me | repo | issue | pr | release | search

Run `python gh.py --help` for the full command list.
"""

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"
DEFAULT_PER_PAGE = 30


def _die(msg, code=1):
    print(json.dumps({"error": True, "message": msg}, ensure_ascii=False))
    sys.exit(code)


def _token(args, required=True):
    tok = getattr(args, "token", None) or os.environ.get("GITHUB_TOKEN", "")
    if required and not tok:
        _die("GitHub token is required. Set the GITHUB_TOKEN environment variable or pass --token <TOKEN>.")
    return tok


def _headers(token, accept="application/vnd.github+json"):
    h = {
        "Accept": accept,
        "User-Agent": "github-toolkit/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _request(method, path, token, payload=None, accept="application/vnd.github+json",
             params=None, raw=False):
    url = API + path
    if params:
        qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        if qs:
            url += ("&" if "?" in url else "?") + qs
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method,
                                 headers=_headers(token, accept))
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read()
            link = resp.headers.get("Link", "")
            if raw:
                return body.decode("utf-8", "replace"), link
            if not body:
                return {}, link
            return json.loads(body), link
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", "replace")
        try:
            msg = json.loads(err).get("message", err)
        except Exception:
            msg = err
        _die(f"GitHub API {method} {path} -> {e.code}: {msg}", e.code or 1)


def _next_link(link):
    for part in link.split(","):
        m = re.match(r'<([^>]+)>;\s*rel="next"', part.strip())
        if m:
            return m.group(1)
    return None


def _paginate(method, path, token, limit=100, accept="application/vnd.github+json",
              params=None):
    """Collect pages up to `limit` items (or until no next page)."""
    items = []
    params = dict(params or {})
    params = {k: v for k, v in params.items() if v is not None}
    params.setdefault("per_page", min(DEFAULT_PER_PAGE, max(1, limit or DEFAULT_PER_PAGE)))
    current = API + path + ("&" if "?" in path else "?") + urllib.parse.urlencode(params)
    while current and (limit is None or len(items) < limit):
        req = urllib.request.Request(current, method=method, headers=_headers(token, accept))
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read()
                link = resp.headers.get("Link", "")
                if not body:
                    page = []
                else:
                    page = json.loads(body)
                if isinstance(page, dict):
                    page = page.get("items", [])
                items.extend(page)
                current = _next_link(link) if (limit is None or len(items) < limit) else None
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", "replace")
            try:
                msg = json.loads(err).get("message", err)
            except Exception:
                msg = err
            _die(f"GitHub API {method} {current} -> {e.code}: {msg}", e.code or 1)
    if limit is not None:
        return items[:limit]
    return items


def _out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------- me / auth
def cmd_me(args):
    _out(_request("GET", "/user", _token(args), accept="application/vnd.github+json")[0])


def cmd_auth_check(args):
    token = _token(args)
    try:
        data, _ = _request("GET", "/user", token)
        _out({"ok": True, "login": data.get("login"), "id": data.get("id"),
              "html_url": data.get("html_url")})
    except SystemExit:
        _out({"ok": False, "message": "invalid token"})


# ---------------------------------------------------------------- repo
def cmd_repo_search(args):
    items = _paginate("GET", f"/search/repositories", _token(args, required=False),
                      limit=args.limit, params={"q": args.query})
    _out({"total": len(items), "items": [{
        "full_name": i.get("full_name"), "html_url": i.get("html_url"),
        "description": i.get("description"), "language": i.get("language"),
        "stars": i.get("stargazers_count"), "forks": i.get("forks_count"),
        "updated_at": i.get("updated_at")} for i in items]})


def cmd_repo_get(args):
    _out(_request("GET", f"/repos/{args.repo}", _token(args, required=False))[0])


def cmd_repo_create(args):
    payload = {"name": args.name, "description": args.description,
               "private": args.private}
    if args.auto_init:
        payload["auto_init"] = True
    _out(_request("POST", "/user/repos", _token(args), payload=payload)[0])


def cmd_repo_branches(args):
    items = _paginate("GET", f"/repos/{args.repo}/branches", _token(args, required=False), limit=args.limit)
    _out({"total": len(items), "items": [{
        "name": i.get("name"),
        "sha": (i.get("commit") or {}).get("sha"),
        "protected": i.get("protected")} for i in items]})


def cmd_repo_commits(args):
    items = _paginate("GET", f"/repos/{args.repo}/commits", _token(args, required=False),
                      limit=args.limit, params={"sha": args.sha})
    _out({"total": len(items), "items": [{
        "sha": i.get("sha"),
        "message": (i.get("commit") or {}).get("message", "").splitlines()[0],
        "author": ((i.get("commit") or {}).get("author") or {}).get("name"),
        "date": ((i.get("commit") or {}).get("author") or {}).get("date"),
        "html_url": i.get("html_url")} for i in items]})


def cmd_repo_contents(args):
    path = args.path or ""
    items = _paginate("GET", f"/repos/{args.repo}/contents/{path}", _token(args, required=False),
                      limit=args.limit)
    _out({"total": len(items), "items": [{
        "name": i.get("name"), "path": i.get("path"), "type": i.get("type"),
        "size": i.get("size"), "download_url": i.get("download_url")} for i in items]})


def cmd_repo_read_file(args):
    data, _ = _request("GET", f"/repos/{args.repo}/contents/{args.path}",
                       _token(args, required=False), accept="application/vnd.github.raw", raw=True)
    print(data)


def _get_sha(repo, path, token, branch):
    try:
        data, _ = _request("GET", f"/repos/{repo}/contents/{path}", token,
                           params={"ref": branch})
        return data.get("sha")
    except SystemExit:
        return None


def cmd_repo_write_file(args):
    token = _token(args)
    if args.from_file:
        with open(args.from_file, "rb") as f:
            content = f.read().decode("utf-8")
    elif args.content is not None:
        content = args.content
    else:
        _die("--content <text> or --from-file <path> is required")
    sha = _get_sha(args.repo, args.path, token, args.branch)
    payload = {"message": args.message, "content": base64.b64encode(content.encode("utf-8")).decode("ascii")}
    if args.branch:
        payload["branch"] = args.branch
    if sha:
        payload["sha"] = sha
    data, _ = _request("PUT", f"/repos/{args.repo}/contents/{args.path}", token,
                       payload=payload)
    _out({"created": not sha, "path": args.path, "commit": (data.get("commit") or {}).get("sha"),
          "html_url": (data.get("commit") or {}).get("html_url")})


def cmd_repo_delete_file(args):
    token = _token(args)
    sha = _get_sha(args.repo, args.path, token, args.branch)
    if not sha:
        _die(f"file {args.path} not found in {args.repo}")
    payload = {"message": args.message, "sha": sha}
    if args.branch:
        payload["branch"] = args.branch
    data, _ = _request("DELETE", f"/repos/{args.repo}/contents/{args.path}", token,
                       payload=payload)
    _out({"deleted": True, "commit": (data.get("commit") or {}).get("sha")})


# ---------------------------------------------------------------- issue
def cmd_issue_list(args):
    items = _paginate("GET", f"/repos/{args.repo}/issues", _token(args, required=False), limit=args.limit,
                      params={"state": args.state, "labels": args.labels})
    _out({"total": len(items), "items": [{
        "number": i.get("number"), "title": i.get("title"), "state": i.get("state"),
        "user": (i.get("user") or {}).get("login"),
        "labels": [l.get("name") for l in (i.get("labels") or [])],
        "created_at": i.get("created_at"), "html_url": i.get("html_url"),
        "pull_request": bool(i.get("pull_request"))} for i in items]})


def cmd_issue_get(args):
    _out(_request("GET", f"/repos/{args.repo}/issues/{args.number}", _token(args, required=False))[0])


def cmd_issue_create(args):
    payload = {"title": args.title}
    if args.body:
        payload["body"] = args.body
    if args.labels:
        payload["labels"] = args.labels.split(",")
    _out(_request("POST", f"/repos/{args.repo}/issues", _token(args), payload=payload)[0])


def cmd_issue_update(args):
    payload = {}
    for k, v in (("state", args.state), ("title", args.title), ("body", args.body)):
        if v is not None:
            payload[k] = v
    if args.labels is not None:
        payload["labels"] = args.labels.split(",") if args.labels else []
    _out(_request("PATCH", f"/repos/{args.repo}/issues/{args.number}", _token(args),
                  payload=payload)[0])


def cmd_issue_comment(args):
    _out(_request("POST", f"/repos/{args.repo}/issues/{args.number}/comments",
                  _token(args), payload={"body": args.body})[0])


# ---------------------------------------------------------------- pr
def cmd_pr_list(args):
    items = _paginate("GET", f"/repos/{args.repo}/pulls", _token(args, required=False), limit=args.limit,
                      params={"state": args.state, "head": args.head, "base": args.base})
    _out({"total": len(items), "items": [{
        "number": i.get("number"), "title": i.get("title"), "state": i.get("state"),
        "user": (i.get("user") or {}).get("login"),
        "head": (i.get("head") or {}).get("ref"), "base": (i.get("base") or {}).get("ref"),
        "created_at": i.get("created_at"), "html_url": i.get("html_url")} for i in items]})


def cmd_pr_get(args):
    _out(_request("GET", f"/repos/{args.repo}/pulls/{args.number}", _token(args, required=False))[0])


def cmd_pr_create(args):
    payload = {"title": args.title, "head": args.head, "base": args.base}
    if args.body:
        payload["body"] = args.body
    if args.draft:
        payload["draft"] = True
    _out(_request("POST", f"/repos/{args.repo}/pulls", _token(args), payload=payload)[0])


def cmd_pr_update(args):
    payload = {}
    for k, v in (("state", args.state), ("title", args.title), ("body", args.body)):
        if v is not None:
            payload[k] = v
    _out(_request("PATCH", f"/repos/{args.repo}/pulls/{args.number}", _token(args),
                  payload=payload)[0])


def cmd_pr_merge(args):
    payload = {"merge_method": args.method}
    data, _ = _request("PUT", f"/repos/{args.repo}/pulls/{args.number}/merge",
                       _token(args), payload=payload)
    _out({"merged": data.get("merged"), "message": data.get("message"),
          "sha": data.get("sha")})


# ---------------------------------------------------------------- release
def cmd_release_list(args):
    items = _paginate("GET", f"/repos/{args.repo}/releases", _token(args, required=False), limit=args.limit)
    _out({"total": len(items), "items": [{
        "tag_name": i.get("tag_name"), "name": i.get("name"), "draft": i.get("draft"),
        "prerelease": i.get("prerelease"), "published_at": i.get("published_at"),
        "html_url": i.get("html_url")} for i in items]})


def cmd_release_get_latest(args):
    _out(_request("GET", f"/repos/{args.repo}/releases/latest", _token(args, required=False))[0])


def cmd_release_get(args):
    _out(_request("GET", f"/repos/{args.repo}/releases/tags/{args.tag}", _token(args, required=False))[0])


def cmd_release_create(args):
    payload = {"tag_name": args.tag, "name": args.name or args.tag,
               "body": args.body or "", "draft": args.draft, "prerelease": args.prerelease}
    if args.target:
        payload["target_commitish"] = args.target
    _out(_request("POST", f"/repos/{args.repo}/releases", _token(args), payload=payload)[0])


def cmd_release_upload_asset(args):
    token = _token(args)
    release, _ = _request("GET", f"/repos/{args.repo}/releases/tags/{args.tag}", token)
    url = release.get("upload_url", "").split("{")[0]
    if not url:
        _die("release not found, cannot upload asset")
    with open(args.file, "rb") as f:
        data = f.read()
    qs = urllib.parse.urlencode({"name": args.name or os.path.basename(args.file)})
    req = urllib.request.Request(
        f"{url}?{qs}", data=data, method="POST",
        headers=_headers(token, "application/octet-stream"))
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            _out(json.loads(resp.read().decode("utf-8")))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", "replace")
        _die(f"asset upload failed -> {e.code}: {err}", e.code or 1)


# ---------------------------------------------------------------- search
def cmd_search(args):
    kind = args.kind
    endpoint = {
        "repos": "/search/repositories",
        "code": "/search/code",
        "issues": "/search/issues",
        "prs": "/search/issues",
        "commits": "/search/commits",
        "users": "/search/users",
    }.get(kind)
    if not endpoint:
        _die(f"unknown search kind: {kind}")
    accept = "application/vnd.github+json"
    if kind == "commits":
        accept = "application/vnd.github.cloak-preview+json"
    q = args.query
    if kind == "prs" and "is:pr" not in q:
        q = f"{q} is:pr"
    items = _paginate("GET", endpoint, _token(args, required=False), limit=args.limit,
                      accept=accept, params={"q": q})
    out_items = []
    for i in items:
        if kind == "repos":
            out_items.append({"full_name": i.get("full_name"), "html_url": i.get("html_url"),
                              "description": i.get("description"), "language": i.get("language"),
                              "stars": i.get("stargazers_count")})
        elif kind == "code":
            out_items.append({"name": i.get("name"), "path": i.get("path"),
                              "repository": (i.get("repository") or {}).get("full_name"),
                              "html_url": i.get("html_url")})
        elif kind == "commits":
            c = i.get("commit") or {}
            out_items.append({"sha": i.get("sha"), "message": (c.get("message") or "").splitlines()[0],
                              "author": (c.get("author") or {}).get("name"),
                              "repository": (i.get("repository") or {}).get("full_name"),
                              "html_url": i.get("html_url")})
        elif kind == "users":
            out_items.append({"login": i.get("login"), "type": i.get("type"),
                              "html_url": i.get("html_url")})
        else:  # issues / prs
            out_items.append({"number": i.get("number"), "title": i.get("title"),
                              "state": i.get("state"),
                              "repository": (i.get("repository") or {}).get("full_name"),
                              "user": (i.get("user") or {}).get("login"),
                              "html_url": i.get("html_url")})
    _out({"total": len(items), "items": out_items})


# ---------------------------------------------------------------- cli
def build_parser():
    p = argparse.ArgumentParser(prog="gh.py", description="Zero-dependency GitHub REST API CLI")
    p.add_argument("--token", help="GitHub personal access token (overrides GITHUB_TOKEN env var)")
    sub = p.add_subparsers(dest="cmd", required=True)

    # me
    me = sub.add_parser("me", help="show authenticated user")
    me.set_defaults(fn=cmd_me)
    ac = sub.add_parser("auth-check", help="check token validity")
    ac.set_defaults(fn=cmd_auth_check)

    def add_limit(sp, default=30):
        sp.add_argument("--limit", type=int, default=default, help="max items to return")

    # repo
    rp = sub.add_parser("repo", help="repository & code management")
    rsub = rp.add_subparsers(dest="action", required=True)
    s = rsub.add_parser("search"); s.add_argument("query"); add_limit(s); s.set_defaults(fn=cmd_repo_search)
    s = rsub.add_parser("get"); s.add_argument("repo"); s.set_defaults(fn=cmd_repo_get)
    s = rsub.add_parser("create"); s.add_argument("name"); s.add_argument("--description")
    s.add_argument("--private", action="store_true"); s.add_argument("--auto-init", action="store_true")
    s.set_defaults(fn=cmd_repo_create)
    s = rsub.add_parser("branches"); s.add_argument("repo"); add_limit(s); s.set_defaults(fn=cmd_repo_branches)
    s = rsub.add_parser("commits"); s.add_argument("repo"); s.add_argument("--sha"); add_limit(s); s.set_defaults(fn=cmd_repo_commits)
    s = rsub.add_parser("contents"); s.add_argument("repo"); s.add_argument("--path", default=""); add_limit(s, 100); s.set_defaults(fn=cmd_repo_contents)
    s = rsub.add_parser("read-file"); s.add_argument("repo"); s.add_argument("path"); s.set_defaults(fn=cmd_repo_read_file)
    s = rsub.add_parser("write-file"); s.add_argument("repo"); s.add_argument("path")
    s.add_argument("--message", required=True); s.add_argument("--content"); s.add_argument("--from-file")
    s.add_argument("--branch"); s.set_defaults(fn=cmd_repo_write_file)
    s = rsub.add_parser("delete-file"); s.add_argument("repo"); s.add_argument("path")
    s.add_argument("--message", required=True); s.add_argument("--branch"); s.set_defaults(fn=cmd_repo_delete_file)

    # issue
    ip = sub.add_parser("issue", help="issue management")
    isub = ip.add_subparsers(dest="action", required=True)
    s = isub.add_parser("list"); s.add_argument("repo"); s.add_argument("--state", default="open", choices=["open", "closed", "all"])
    s.add_argument("--labels"); add_limit(s); s.set_defaults(fn=cmd_issue_list)
    s = isub.add_parser("get"); s.add_argument("repo"); s.add_argument("number", type=int); s.set_defaults(fn=cmd_issue_get)
    s = isub.add_parser("create"); s.add_argument("repo"); s.add_argument("--title", required=True)
    s.add_argument("--body"); s.add_argument("--labels"); s.set_defaults(fn=cmd_issue_create)
    s = isub.add_parser("update"); s.add_argument("repo"); s.add_argument("number", type=int)
    s.add_argument("--state", choices=["open", "closed"]); s.add_argument("--title"); s.add_argument("--body"); s.add_argument("--labels")
    s.set_defaults(fn=cmd_issue_update)
    s = isub.add_parser("comment"); s.add_argument("repo"); s.add_argument("number", type=int)
    s.add_argument("--body", required=True); s.set_defaults(fn=cmd_issue_comment)

    # pr
    pp = sub.add_parser("pr", help="pull request management")
    psub = pp.add_subparsers(dest="action", required=True)
    s = psub.add_parser("list"); s.add_argument("repo"); s.add_argument("--state", default="open", choices=["open", "closed", "all"])
    s.add_argument("--head"); s.add_argument("--base"); add_limit(s); s.set_defaults(fn=cmd_pr_list)
    s = psub.add_parser("get"); s.add_argument("repo"); s.add_argument("number", type=int); s.set_defaults(fn=cmd_pr_get)
    s = psub.add_parser("create"); s.add_argument("repo"); s.add_argument("--title", required=True)
    s.add_argument("--head", required=True); s.add_argument("--base", required=True)
    s.add_argument("--body"); s.add_argument("--draft", action="store_true"); s.set_defaults(fn=cmd_pr_create)
    s = psub.add_parser("update"); s.add_argument("repo"); s.add_argument("number", type=int)
    s.add_argument("--state", choices=["open", "closed"]); s.add_argument("--title"); s.add_argument("--body")
    s.set_defaults(fn=cmd_pr_update)
    s = psub.add_parser("merge"); s.add_argument("repo"); s.add_argument("number", type=int)
    s.add_argument("--method", default="merge", choices=["merge", "squash", "rebase"]); s.set_defaults(fn=cmd_pr_merge)

    # release
    rl = sub.add_parser("release", help="releases & version publishing")
    rsub2 = rl.add_subparsers(dest="action", required=True)
    s = rsub2.add_parser("list"); s.add_argument("repo"); add_limit(s); s.set_defaults(fn=cmd_release_list)
    s = rsub2.add_parser("get-latest"); s.add_argument("repo"); s.set_defaults(fn=cmd_release_get_latest)
    s = rsub2.add_parser("get"); s.add_argument("repo"); s.add_argument("tag"); s.set_defaults(fn=cmd_release_get)
    s = rsub2.add_parser("create"); s.add_argument("repo"); s.add_argument("--tag", required=True)
    s.add_argument("--name"); s.add_argument("--body"); s.add_argument("--target")
    s.add_argument("--draft", action="store_true"); s.add_argument("--prerelease", action="store_true")
    s.set_defaults(fn=cmd_release_create)
    s = rsub2.add_parser("upload-asset"); s.add_argument("repo"); s.add_argument("--tag", required=True)
    s.add_argument("--file", required=True); s.add_argument("--name"); s.set_defaults(fn=cmd_release_upload_asset)

    # search
    sp = sub.add_parser("search", help="cross-repository search")
    sp.add_argument("kind", choices=["repos", "code", "issues", "prs", "commits", "users"])
    sp.add_argument("query"); add_limit(sp); sp.set_defaults(fn=cmd_search)

    return p


def main():
    args = build_parser().parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
