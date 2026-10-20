---
name: github-toolkit
description: GitHub 全能力操作工具集（仓库与代码管理、Issue/PR 自动化、版本 Release 发布、跨仓库代码搜索）。当用户要求操作 GitHub 时使用：创建/搜索/查看仓库、浏览与读写删除仓库文件、查看分支与提交、管理 Issue 与评论、创建/更新/合并 Pull Request、管理 Release 版本与上传附件、跨仓库搜索代码/提交/Issue/PR/用户；或用户提到 GitHub、仓库、Issue、PR、Pull Request、Release、代码搜索等关键词并希望执行相关操作时使用。
---

# GitHub Toolkit

通过 `scripts/gh.py` 调用 GitHub REST API，完成仓库、代码、Issue、PR、Release 与搜索的全部常用操作。脚本零依赖（仅 Python 3.8+ 标准库）。

## 前置条件

- Python 3.8+（`python gh.py --help` 可查看全部命令）。
- 认证：设置环境变量 `GITHUB_TOKEN`，或每条命令传 `--token <TOKEN>`。Token 建议勾选 `repo`、`read:org` 权限。
- 若运行时没有 Token：只读命令（repo search/get、issue list/get、release list 等公开数据）仍可用，但受 GitHub 未认证限流（60 次/小时）约束；写操作必须报错并请求用户提供 Token。

## 安全规则

1. 所有**写操作**（创建仓库、写/删文件、创建/更新 Issue、评论、创建/更新/合并 PR、创建 Release、上传附件）执行前，必须向用户确认：目标仓库、动作、影响范围。用户确认前不得执行。
2. 永不把 Token、凭据或私有内容写入 prompt、日志、文件名或交付产物。
3. 只操作用户点名的仓库；未经授权不向额外账号、组织或仓库写入。
4. 删除类操作（delete-file、关闭 Issue/PR、删除 Release）额外说明不可逆性后再执行。

## 核心工作流

1. **解析目标**：确认 `owner/repo`、Issue/PR 编号、分支、tag 等标识，不猜测。
2. **先只读核实**：写操作前先用只读命令（`repo get`、`issue get`、`pr get`、`release get-latest`）确认对象存在与当前状态。
3. **确认后执行**：向用户说明将执行的动作，得到确认后调用对应命令。
4. **链式推进**：用返回的标识（commit sha、issue number、release id）衔接后续操作。

## 命令速查

统一调用方式：`python <skill_dir>/scripts/gh.py <group> <action> [参数]`

### 身份与认证
| 命令 | 说明 |
|---|---|
| `me` | 查看当前认证用户 |
| `auth-check` | 校验 Token 是否有效 |

### 仓库与代码管理（repo）
| 命令 | 说明 |
|---|---|
| `repo search <query> [--limit N]` | 按名称/描述/topic 搜索仓库 |
| `repo get <owner/repo>` | 查看仓库详情 |
| `repo create <name> [--private] [--description ...] [--auto-init]` | 创建仓库 |
| `repo branches <owner/repo> [--limit N]` | 列出分支 |
| `repo commits <owner/repo> [--sha <branch>] [--limit N]` | 列出提交 |
| `repo contents <owner/repo> [--path <dir>] [--limit N]` | 列出目录内容 |
| `repo read-file <owner/repo> <path>` | 读取文件原始内容 |
| `repo write-file <owner/repo> <path> --message <msg> --content <text>\|--from-file <file> [--branch]` | 新建/更新文件（自动处理 sha） |
| `repo delete-file <owner/repo> <path> --message <msg> [--branch]` | 删除文件（不可逆） |

### Issue 管理（issue）
| 命令 | 说明 |
|---|---|
| `issue list <owner/repo> [--state open\|closed\|all] [--labels a,b] [--limit N]` | 列出 Issue |
| `issue get <owner/repo> <number>` | 查看 Issue 详情 |
| `issue create <owner/repo> --title ... [--body ...] [--labels a,b]` | 创建 Issue |
| `issue update <owner/repo> <number> [--state] [--title] [--body] [--labels]` | 更新 Issue |
| `issue comment <owner/repo> <number> --body ...` | 添加评论 |

### Pull Request 管理（pr）
| 命令 | 说明 |
|---|---|
| `pr list <owner/repo> [--state open\|closed\|all] [--head] [--base] [--limit N]` | 列出 PR |
| `pr get <owner/repo> <number>` | 查看 PR 详情 |
| `pr create <owner/repo> --title ... --head <branch> --base <branch> [--body] [--draft]` | 创建 PR |
| `pr update <owner/repo> <number> [--state] [--title] [--body]` | 更新 PR |
| `pr merge <owner/repo> <number> [--method merge\|squash\|rebase]` | 合并 PR（不可逆） |

### 版本发布（release）
| 命令 | 说明 |
|---|---|
| `release list <owner/repo> [--limit N]` | 列出 Releases |
| `release get-latest <owner/repo>` | 查看最新 Release |
| `release get <owner/repo> <tag>` | 按 tag 查看 Release |
| `release create <owner/repo> --tag <tag> [--name] [--body] [--target] [--draft] [--prerelease]` | 创建 Release |
| `release upload-asset <owner/repo> --tag <tag> --file <path> [--name]` | 上传 Release 附件 |

### 跨仓库搜索（search）
| 命令 | 说明 |
|---|---|
| `search repos <query> [--limit N]` | 搜索仓库 |
| `search code <query> [--limit N]` | 搜索代码 |
| `search issues <query> [--limit N]` | 搜索 Issue |
| `search prs <query> [--limit N]` | 搜索 PR（自动补 is:pr） |
| `search commits <query> [--limit N]` | 搜索提交 |
| `search users <query> [--limit N]` | 搜索用户 |

## 典型场景

**生成 README 并提交**：
1. `repo get owner/repo` 核实仓库存在与默认分支；
2. 生成 README 内容写入本地临时文件；
3. 向用户确认后：`repo write-file owner/repo README.md --message "docs: add README" --from-file <file>`。

**任务追踪**：`issue list owner/repo --state open` → 对每项 `issue comment owner/repo <n> --body ...`；新增需求用 `issue create`。

**合入代码**：`pr list owner/repo` → `pr get owner/repo <n>` 检查状态 → 向用户确认 → `pr merge owner/repo <n> --method squash`。

**发版**：`release list owner/repo` 看已有版本 → `release create owner/repo --tag v1.1.0 --name "v1.1.0" --body "<变更说明>"` → `release upload-asset owner/repo --tag v1.1.0 --file dist/app.zip`。

## 失败处理

- `401`：Token 无效或过期，请用户重新提供。
- `403`：权限不足或触发限流（检查返回 message 中的 Rate Limit 提示）。
- `404`：仓库/文件/Issue/PR/Release 不存在，先核实标识拼写。
- `422`：参数错误（如 write-file 缺少 message、PR 分支冲突），按 message 修正。
- 网络错误：重试一次；仍失败则报告失败操作与原因，不静默跳过。

## 详细参考

端点、参数与更多示例见 [references/api-guide.md](references/api-guide.md)。若脚本行为需要调整，先读 `scripts/gh.py` 再修改。
