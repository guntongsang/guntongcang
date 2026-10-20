# github-toolkit

零依赖的 GitHub 全能力工具插件（Agent Skill），供 AI Agent（豆包、通用大模型助手等）直接调用 GitHub REST API，覆盖仓库/代码管理、Issue/PR 自动化、版本发布与跨仓库搜索。

A zero-dependency GitHub toolkit plugin for AI agents. Works with Doubao Work and any agent runtime that supports folder-based skills.

## 功能特性

- **仓库与代码管理**：搜索/查看/创建仓库、分支与提交、目录浏览、文件读写删除
- **Issue 自动化**：列表/详情/创建/更新/评论
- **Pull Request 自动化**：列表/详情/创建/更新/合并
- **版本发布**：Release 列表/详情/创建、附件上传
- **跨仓库搜索**：代码、提交、Issue、PR、用户、仓库
- **零依赖**：仅 Python 3.8+ 标准库（`urllib`），无需 `requests`、无需安装 git

## 快速开始

### 1. 安装到豆包（Doubao Work）

将 `skill/` 目录整体复制到用户技能目录：

```text
<workspace>/.user_skills/github-toolkit/
```

### 2. 配置 Token

生成 [GitHub Personal Access Token](https://github.com/settings/tokens)，勾选 `repo`、`read:org` 权限，然后设置环境变量：

```bash
# Windows PowerShell
$env:GITHUB_TOKEN = "ghp_xxx"

# macOS / Linux
export GITHUB_TOKEN="ghp_xxx"
```

只读命令（仓库搜索、Issue 列表等公开数据）可不带 Token 使用（受 60 次/小时限流约束）。

### 3. 使用

```bash
python skill/scripts/gh.py <group> <action> [参数]
```

```bash
# 查看全部命令
python skill/scripts/gh.py --help

# 搜索仓库
python skill/scripts/gh.py repo search "quantum computing" --limit 10

# 查看仓库
python skill/scripts/gh.py repo get octocat/Hello-World

# 创建 Issue
python skill/scripts/gh.py issue create owner/repo --title "Bug: xxx" --body "复现步骤..."

# 合并 PR
python skill/scripts/gh.py pr merge owner/repo 12 --method squash

# 发布 Release
python skill/scripts/gh.py release create owner/repo --tag v1.0.0 --body "首个正式版本"
python skill/scripts/gh.py release upload-asset owner/repo --tag v1.0.0 --file dist/app.zip
```

## 命令参考

| 分组 | 命令 | 说明 |
|---|---|---|
| 身份 | `me` / `auth-check` | 查看当前用户 / 校验 Token |
| 仓库 | `repo search` `repo get` `repo create` | 搜索/查看/创建仓库 |
| 仓库 | `repo branches` `repo commits` `repo contents` | 分支、提交、目录 |
| 仓库 | `repo read-file` `repo write-file` `repo delete-file` | 文件读写删 |
| Issue | `issue list` `issue get` `issue create` `issue update` `issue comment` | Issue 全流程 |
| PR | `pr list` `pr get` `pr create` `pr update` `pr merge` | PR 全流程 |
| Release | `release list` `release get-latest` `release get` `release create` `release upload-asset` | 版本发布 |
| 搜索 | `search repos\|code\|issues\|prs\|commits\|users` | 跨仓库搜索 |

## 安全说明

- 所有写操作（创建/删除/合并等）由 Agent 在执行前向用户确认，Token 不写入日志与产物。
- Token 请勿提交到仓库；本仓库已配置 `.gitignore` 忽略 `.env`、`__pycache__` 等。

## 目录结构

```text
github-toolkit/
├── README.md
├── LICENSE
└── skill/
    ├── SKILL.md            # 技能主文档（触发描述 + 工作流 + 命令速查）
    ├── scripts/
    │   └── gh.py           # 零依赖 GitHub REST API CLI
    └── references/
        └── api-guide.md    # GitHub REST API 速查
```

## License

[MIT](LICENSE)
