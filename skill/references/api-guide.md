# GitHub REST API 速查（github-toolkit 配套参考）

本文档供 Agent 在扩展脚本、调试或需要更细粒度参数时查阅。日常操作直接使用 `scripts/gh.py` 命令即可。

## 认证与限流

- Base URL：`https://api.github.com`，版本头 `X-GitHub-Api-Version: 2022-11-28`。
- 认证方式：`Authorization: Bearer <TOKEN>`。
- Token 权限（Personal Access Token scopes）：
  - `repo`：仓库、代码、Issue、PR、Release 的读写（最常用）。
  - `read:org`：读取组织信息与成员。
  - `workflow`：更新 GitHub Actions 工作流文件。
- 限流：认证后 5000 次/小时（核心 API）；未认证 60 次/小时。响应头 `X-RateLimit-Remaining` 可查余量。
- 分页：`?per_page=1..100`（默认 30）；响应头 `Link` 中 `rel="next"` 指向下一页。`gh.py` 的 `--limit` 已自动处理分页。

## 常用端点

### 仓库与内容
| 方法 | 端点 | 用途 |
|---|---|---|
| GET | `/search/repositories?q=` | 搜索仓库 |
| GET | `/repos/{owner}/{repo}` | 仓库详情 |
| POST | `/user/repos` | 创建仓库（body: name, private, description, auto_init） |
| GET | `/repos/{owner}/{repo}/branches` | 分支列表 |
| GET | `/repos/{owner}/{repo}/commits?sha={branch}` | 提交列表 |
| GET | `/repos/{owner}/{repo}/contents/{path}` | 目录列表或文件元数据 |
| GET | `/repos/{owner}/{repo}/contents/{path}`（Accept: `application/vnd.github.raw`） | 文件原始内容 |
| PUT | `/repos/{owner}/{repo}/contents/{path}` | 新建/更新文件（body: message, content[base64], branch?, sha?；更新须带原文件 sha） |
| DELETE | `/repos/{owner}/{repo}/contents/{path}` | 删除文件（body: message, sha） |

文件 sha 获取：先 `GET contents`，从响应的 `sha` 字段取；文件不存在时 GitHub 返回 404。

### Issue
| 方法 | 端点 | 用途 |
|---|---|---|
| GET | `/repos/{owner}/{repo}/issues?state=&labels=` | 列出 Issue（注意：列表同时包含 PR，靠 `pull_request` 字段区分） |
| GET | `/repos/{owner}/{repo}/issues/{n}` | Issue 详情 |
| POST | `/repos/{owner}/{repo}/issues` | 创建（body: title, body?, labels[]） |
| PATCH | `/repos/{owner}/{repo}/issues/{n}` | 更新（state/title/body/labels） |
| POST | `/repos/{owner}/{repo}/issues/{n}/comments` | 评论（body: body） |

### Pull Request
| 方法 | 端点 | 用途 |
|---|---|---|
| GET | `/repos/{owner}/{repo}/pulls?state=&head=&base=` | 列出 PR |
| GET | `/repos/{owner}/{repo}/pulls/{n}` | PR 详情 |
| POST | `/repos/{owner}/{repo}/pulls` | 创建（body: title, head, base, body?, draft?） |
| PATCH | `/repos/{owner}/{repo}/pulls/{n}` | 更新 |
| PUT | `/repos/{owner}/{repo}/pulls/{n}/merge` | 合并（body: merge_method: merge/squash/rebase） |

### Release
| 方法 | 端点 | 用途 |
|---|---|---|
| GET | `/repos/{owner}/{repo}/releases` | 列表 |
| GET | `/repos/{owner}/{repo}/releases/latest` | 最新版 |
| GET | `/repos/{owner}/{repo}/releases/tags/{tag}` | 按 tag 查 |
| POST | `/repos/{owner}/{repo}/releases` | 创建（body: tag_name, name?, body?, target_commitish?, draft?, prerelease?） |
| POST | `{upload_url}`（去掉 `{?name,label}` 部分）+ `?name=` | 上传附件，Content-Type: application/octet-stream，直接传二进制 |

### 搜索
| 方法 | 端点 | 说明 |
|---|---|---|
| GET | `/search/code?q=` | 代码搜索（需认证；默认 10 条/请求） |
| GET | `/search/commits?q=` | 提交搜索（Accept: `application/vnd.github.cloak-preview+json`） |
| GET | `/search/issues?q=` | Issue/PR 搜索（PR 加 `is:pr`） |
| GET | `/search/users?q=` | 用户搜索 |

搜索语法示例：`repo:octocat/Hello-World code`、`is:pr is:open review-requested:@me`、`user:defunkt stars:>100`。

## 常见错误码

- `401` Token 无效/过期；`403` 权限不足或限流；`404` 资源不存在（contents 404 常表示文件不存在）；`422` 参数/校验错误；`409` 合并冲突。

## 扩展建议

如需新增能力（如 Teams、Copilot review、秘密扫描），参考本表端点模式在 `scripts/gh.py` 中新增子命令即可，保持零依赖与 JSON 输出风格一致。
