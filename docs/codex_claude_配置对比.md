# Codex 与 Claude Code 配置对比（本项目实测版）

> 适用仓库：`langgraph-101`
> 核对日期：2026-07-05
> 核对方法：逐条对照 Codex 官方文档（developers.openai.com/codex），并在本机用
> `codex debug prompt-input`（技能/指令加载验证）与 `codex execpolicy check`（命令规则验证）实测。
> 本机 Codex：手动安装构建（版本号显示 0.0.0，doctor 提示最新为 0.142.5），
> 已实测支持 `.agents/skills` 扫描与 execpolicy 规则引擎。

---

## 一、本项目双侧目录现状

```
langgraph-101/
├── CLAUDE.md                 ← Claude 项目指令（准源）
├── AGENTS.md                 ← Codex 项目指令（= CLAUDE.md + 第六章 Codex 适配）
├── .claude/
│   ├── settings.json         ← Claude 权限：git/pip/uv 白名单 + 危险 git 命令硬 deny
│   ├── settings.local.json   ← 个人本地权限（不入库）
│   └── skills/               ← 4 个项目技能（准源，含 Claude 扩展 frontmatter 字段）
└── .agents/
    └── skills/               ← Codex 项目技能（同源副本，frontmatter 仅 name/description）
        ├── tech-summary/
        ├── export-graphs/    （含 scripts/export_graphs.py）
        ├── new-module/
        └── cards-from-summary/
```

维护约定：**以 `.claude/skills/` 与 `CLAUDE.md` 为准源**，修改后同步到
`.agents/skills/` 与 `AGENTS.md`（Codex 侧 frontmatter 仅支持 `name`、`description`）。

---

## 二、项目级配置对照（仓库内、团队共享）

| 目录/文件 | 作用 | 官方依据 | 本项目现状 |
| --- | --- | --- | --- |
| `AGENTS.md`（根目录，可嵌套子目录） | 项目指令。从项目根向下逐级拼接到工作目录，越近越优先；合并上限默认 32 KiB（`project_doc_max_bytes`） | "Starting at the project root, Codex walks down to your current working directory"、"Files closer to your current directory override earlier guidance" —— [guides/agents-md](https://developers.openai.com/codex/guides/agents-md) | ✅ 已配置，实测出现在模型可见提示中 |
| `.agents/skills/` | 项目技能。从当前目录逐级向上扫到仓库根 | "Codex scans `.agents/skills` in every directory from your current working directory up to the repository root" —— [skills](https://developers.openai.com/codex/skills) | ✅ 4 个技能实测被发现，描述完整、无重复 |
| `.codex/config.toml` | 项目级配置覆盖，**仅受信任（trusted）项目生效**，就近优先 | "To scope settings to a specific project or subfolder, add a `.codex/config.toml` file in your repo"、"closest wins; trusted projects only" —— [config-basic](https://developers.openai.com/codex/config-basic) | ❌ 未配置（暂无需要） |
| `.codex/rules/*.rules` | 命令级硬规则（Starlark `prefix_rule`），decision 取 `allow` / `prompt` / `forbidden`，多规则命中取最严；**实验性功能** | "control which commands Codex can run outside the sandbox"、"forbidden: Block the request without prompting"、"Rules are experimental and may change" —— [rules](https://developers.openai.com/codex/rules) | ❌ 未配置（可选增强，见第五节实测） |

---

## 三、用户级配置对照（`~` 下、跨项目全局）

| 目录/文件 | 作用 | 官方依据 | 本机现状 |
| --- | --- | --- | --- |
| `~/.codex/config.toml` | 全局配置：`approval_policy`、`sandbox_mode`、权限 profile、`[[skills.config]]` 技能启停等 | "stores user-level configuration at `~/.codex/config.toml`"；优先级：CLI 参数 > 项目配置 > profile > 用户配置 > 系统配置（`/etc/codex/config.toml`） —— [config-basic](https://developers.openai.com/codex/config-basic) | ✅ 已有 |
| `~/.codex/AGENTS.md` | 全局指令，所有项目生效；先找 `AGENTS.override.md` 再找 `AGENTS.md` | "Codex uses only the first non-empty file at this level" —— [guides/agents-md](https://developers.openai.com/codex/guides/agents-md) | ❌ 未配置（可选） |
| `~/.agents/skills/` | 个人技能（当前官方标准路径） | 扫描表 USER 行："`$HOME/.agents/skills` — Personal skills across any repository" —— [skills](https://developers.openai.com/codex/skills) | ✅ 已有（baoyu、lark 等系列） |
| `~/.codex/skills/` | 个人技能（历史路径） | 当前官方文档扫描表已不列出；本机实测仍被作为技能根扫描（含 `.system` 内置技能） | ✅ 已有 80+ 个，与 `~/.agents/skills` 部分重复；官方称同名技能不合并、选择器中都出现 |
| `~/.codex/rules/default.rules` | 用户级命令规则；TUI 中点"允许"会自动持久化到此文件 | "When you allow a command from the TUI, Codex persists it to `~/.codex/rules/default.rules`" —— [rules](https://developers.openai.com/codex/rules) | 视使用情况自动生成 |
| `~/.codex/auth.json`、cache、sessions | 登录凭证与运行时文件 | [auth](https://developers.openai.com/codex/auth) | ✅ 已有 |

---

## 四、与 Claude Code 的能力对位（项目级）

| Claude Code | Codex | 对等程度 |
| --- | --- | --- |
| `CLAUDE.md` | `AGENTS.md` | 完全对等；Codex 额外支持子目录嵌套覆盖与 `AGENTS.override.md` |
| `.claude/skills/` | `.agents/skills/` | 完全对等；Codex frontmatter 仅支持 `name`/`description`，`argument-hint`、`allowed-tools` 等扩展字段需剔除 |
| `.claude/settings.json` deny 列表 | `.codex/rules/` 中 `decision = "forbidden"` | **可对等还原**（实验性；且项目须被标记 trusted 才加载项目 `.codex/` 层） |
| `.claude/settings.json` allow 列表 | `.codex/rules/` 中 `decision = "allow"`，或依赖 `approval_policy` + 沙箱 | 可对等 |
| `.claude/settings.local.json`（个人、不入库） | 用户级 `~/.codex/config.toml` / `~/.codex/rules/` | 机制不同、效果相当 |
| 无对应 | 项目级 `.codex/config.toml`（模型、审批策略等按仓库覆盖） | Codex 独有 |

**当前实际差异**：本项目 Claude 侧的 4 条 deny（`git push --force`、`git push -f`、
`git reset --hard`、`git clean -f`）在 Codex 侧目前仅以 `AGENTS.md` 第六章的指令软约束存在，
尚未用 rules 硬性还原。

---

## 五、rules 硬拦截实测记录（2026-07-05，本机）

用 `codex execpolicy check` 对临时规则文件验证：

```python
prefix_rule(
    pattern = ["git", "push", "--force"],
    decision = "forbidden",
    justification = "禁止强制推送",
)
```

| 测试命令 | 结果 |
| --- | --- |
| `git push --force origin master` | `"decision":"forbidden"` ✅ 拦截成功 |
| `git push origin master` | 无规则命中，正常放行 ✅ |
| `git push origin --force`（参数乱序） | **无规则命中，不拦截** ⚠️ |

⚠️ **前缀匹配盲区**：官方明确 "the prefix must match exactly in order — reordered
arguments don't match"。若要落地 rules，需同时覆盖 `--force` / `-f` 的常见 token 位置，
并保留沙箱（`workspace-write`）作为兜底防线；不要依赖 rules 做唯一防护。
（注：Claude 的 `Bash(git push --force*)` 通配 deny 同样存在乱序盲区，两侧此局限一致。）

---

## 六、官方文档索引

| 主题 | 链接 |
| --- | --- |
| Agent Skills（技能路径/格式/渐进披露） | <https://developers.openai.com/codex/skills> |
| AGENTS.md 指南（层级/合并/上限） | <https://developers.openai.com/codex/guides/agents-md> |
| 配置基础（用户级/项目级/优先级） | <https://developers.openai.com/codex/config-basic> |
| 配置参考 / 高级配置 | <https://developers.openai.com/codex/config-reference> 、<https://developers.openai.com/codex/config-advanced> |
| Rules（命令级规则，实验性） | <https://developers.openai.com/codex/rules> |
| Permissions（文件系统/网络权限 profile，Beta） | <https://developers.openai.com/codex/permissions> |
| 沙箱概念 | <https://developers.openai.com/codex/concepts/sandboxing> |
| 插件（技能分发形式） | <https://developers.openai.com/codex/plugins> |
| Agent Skills 开放标准（Codex 与 Claude 共同遵循） | <https://agentskills.io> |
| 官方技能示例仓库 | <https://github.com/openai/skills> |

---

## 七、遗留事项与建议

1. **可选**：新建 `.codex/rules/safety.rules` 硬性还原 Claude 侧 4 条 deny
   （规则写法见第五节，写入后用 `codex execpolicy check` 逐条回归）。
2. **可选**：升级 Codex 本体（doctor 提示最新 0.142.5），升级后复跑
   `codex debug prompt-input` 确认技能与指令加载不回归。
3. 个人技能在 `~/.codex/skills`（老路径）与 `~/.agents/skills`（新路径）存在重复，
   与本项目无关，将来可自行收敛到新路径。
