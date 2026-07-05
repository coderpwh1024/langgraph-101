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
├── .agents/
│   └── skills/               ← Codex 项目技能（同源副本，frontmatter 仅 name/description）
│       ├── tech-summary/
│       ├── export-graphs/    （含 scripts/export_graphs.py）
│       ├── new-module/
│       └── cards-from-summary/
└── .codex/
    └── rules/
        └── safety.rules      ← Codex 命令规则：还原 Claude 侧 deny/allow（trusted 才加载）
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
| `.codex/rules/*.rules` | 命令级硬规则（Starlark `prefix_rule`），decision 取 `allow` / `prompt` / `forbidden`，多规则命中取最严；**实验性功能** | "control which commands Codex can run outside the sandbox"、"forbidden: Block the request without prompting"、"Rules are experimental and may change" —— [rules](https://developers.openai.com/codex/rules) | ✅ 已配置 `safety.rules`（2026-07-05）：4 组 forbidden 还原 Claude deny + allow 白名单还原 Claude allow，`codex execpolicy check` 全量回归通过（见第五节） |

---

## 三、用户级配置对照（`~` 下、跨项目全局）

| 目录/文件 | 作用 | 官方依据 | 本机现状 |
| --- | --- | --- | --- |
| `~/.codex/config.toml` | 全局配置：`approval_policy`、`sandbox_mode`、权限 profile、`[[skills.config]]` 技能启停等 | "stores user-level configuration at `~/.codex/config.toml`"；优先级：CLI 参数 > 项目配置 > profile > 用户配置 > 系统配置（`/etc/codex/config.toml`） —— [config-basic](https://developers.openai.com/codex/config-basic) | ✅ 已有 |
| `~/.codex/AGENTS.md` | 全局指令，所有项目生效；先找 `AGENTS.override.md` 再找 `AGENTS.md` | "Codex uses only the first non-empty file at this level" —— [guides/agents-md](https://developers.openai.com/codex/guides/agents-md) | ❌ 未配置（可选） |
| `~/.agents/skills/` | 个人技能（当前官方标准路径） | 扫描表 USER 行："`$HOME/.agents/skills` — Personal skills across any repository" —— [skills](https://developers.openai.com/codex/skills) | ✅ 已有（baoyu、lark 等系列） |
| `~/.codex/skills/` | 个人技能（历史路径） | 当前官方文档扫描表已不列出；本机实测仍被作为技能根扫描（含 `.system` 内置技能） | ✅ 已有 80+ 个，与 `~/.agents/skills` 部分重复；官方称同名技能不合并、选择器中都出现 |
| `~/.codex/rules/default.rules` | 用户级命令规则；TUI 中点"允许"会自动持久化到此文件 | "When you allow a command from the TUI, Codex persists it to `~/.codex/rules/default.rules`" —— [rules](https://developers.openai.com/codex/rules) | 视使用情况自动生成 |
| `~/.codex/rules/local-allow.rules` | 手写的个人命令白名单（与自动持久化的 default.rules 分离，便于维护） | 同上（`~/.codex/rules/*.rules` 均被加载） | ✅ 已配置（2026-07-05）：还原 settings.local.json 的 Bash allow（cat / patch -p1 / codex 自检子命令），execpolicy 回归 9 用例通过 |
| `~/.codex/config.toml` 的 `[tools] web_search` | 官方 web search 工具开关 | [config-reference](https://developers.openai.com/codex/config-reference) | ✅ 已启用（2026-07-05，对应 Claude 侧 WebSearch 授权） |
| `~/.codex/auth.json`、cache、sessions | 登录凭证与运行时文件 | [auth](https://developers.openai.com/codex/auth) | ✅ 已有 |

---

## 四、与 Claude Code 的能力对位（项目级）

| Claude Code | Codex | 对等程度 |
| --- | --- | --- |
| `CLAUDE.md` | `AGENTS.md` | 完全对等；Codex 额外支持子目录嵌套覆盖与 `AGENTS.override.md` |
| `.claude/skills/` | `.agents/skills/` | 完全对等；Codex frontmatter 仅支持 `name`/`description`，`argument-hint`、`allowed-tools` 等扩展字段需剔除 |
| `.claude/settings.json` deny 列表 | `.codex/rules/safety.rules` 中 `decision = "forbidden"` | ✅ **已对等还原**（实验性；且项目须被标记 trusted 才加载项目 `.codex/` 层） |
| `.claude/settings.json` allow 列表 | `.codex/rules/safety.rules` 中 `decision = "allow"` | ✅ 已对等还原（git 只读/提交推送、pip/pip3/python -m pip install、uv 六子命令） |
| `.claude/settings.local.json`（个人、不入库） | 用户级 `~/.codex/config.toml` / `~/.codex/rules/` | ✅ 已按四类逐条对位（2026-07-05，见下方明细） |
| 无对应 | 项目级 `.codex/config.toml`（模型、审批策略等按仓库覆盖） | Codex 独有 |

**当前实际差异**：已消除（2026-07-05）。Claude 侧 4 条 deny 与 allow 白名单均已在
`.codex/rules/safety.rules` 硬性还原，`AGENTS.md` 第六章的指令软约束保留作为最终防线
（rules 为实验性功能，且仅 trusted 项目加载）。

**settings.local.json（个人本地权限）对位明细**（2026-07-05 落地）：

| Claude 本地权限 | Codex 官方对位 | 状态 |
| --- | --- | --- |
| `Bash(cat)`、`Bash(patch -p1)`、`Bash(codex features/doctor/debug/execpolicy *)` | `~/.codex/rules/local-allow.rules`（用户级 allow 规则，注意跨项目全局生效） | ✅ 已落地并回归。⚠️ 语义差异：Claude 不带 `*` 的 `Bash(cat)`/`Bash(patch -p1)` 是**精确匹配**，prefix_rule 只有前缀语义，Codex 侧放行范围略宽（`cat <file>` 等带参形式也免审），评估为低风险接受 |
| `WebSearch` | `~/.codex/config.toml` 顶层 `web_search = "live"`（现行规范键，默认 `"cached"` 只查缓存索引）+ `[tools] web_search = true`（legacy 布尔写法，双写兼容） | ✅ 已启用，`codex doctor` 确认 config 解析正常 |
| `Read(//Users/coderpwh/**)` 等读路径授权 | **无需配置**：Codex 沙箱默认全盘可读、只限制写入与网络 | ✅ 天然满足 |
| `WebFetch(domain:raw.githubusercontent.com)`、`WebFetch(domain:developers.openai.com)` | 域名级控制官方有两处：① Beta `[permissions]` 网络规则（`"*.example.com"` 语法，语义是**放行**指定域）；② `tools.web_search` 对象形式的 `allowed_domains`（语义是把搜索**收紧**到指定域，与 Claude 的"额外放行"方向相反，不适用）。prefix_rule 无法对 URL token 做域名匹配 | ⏸️ 未启用：①与 `sandbox_mode` 互斥且为 Beta，为两个域名切换整套体系不划算；②语义不符。实际访问时走审批，TUI 点"允许"会自动持久化到 `~/.codex/rules/default.rules` |

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

**落地记录（2026-07-05，`.codex/rules/safety.rules`）**：

- pattern 的 **token 并集**语法实测可用（如 `["git", "push", ["--force", "-f"]]`），
  每条规则均带 `match` / `not_match` 内联自测，加载时自动校验。
- 乱序覆盖：显式补了 `git push origin --force/-f` 与
  `git push origin master|HEAD --force/-f` 两组常见乱序位，回归全部 `forbidden`。
- **交叉场景验证**：`git push --force` 同时命中 allow（`git push` 前缀）与 forbidden，
  实测取最严 → `forbidden`，与官方"most restrictive wins"一致。
- **剩余盲区**（两侧一致）：未枚举分支名的 `git push origin <branch> --force`
  会命中 allow 前缀放行——Claude 侧 `git push*` allow + `--force*` deny 的组合
  存在完全相同的漏洞；靠 AGENTS.md 指令软约束与代码评审兜底。
- 回归命令：`codex execpolicy check --rules .codex/rules/safety.rules <command...>`，
  24 个用例（9 forbidden + 1 交叉 + 11 allow + 3 不命中）全部符合预期。

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

1. ~~新建 `.codex/rules/safety.rules` 硬性还原 Claude 侧 4 条 deny~~
   ✅ 已完成（2026-07-05，含 allow 白名单对等还原，落地记录见第五节）。
   注意：需确认本项目在 Codex 中被标记为 trusted，否则项目级 `.codex/` 层不加载。
2. **可选**：升级 Codex 本体（doctor 提示最新 0.142.5），升级后复跑
   `codex debug prompt-input` 确认技能与指令加载不回归，
   并复跑第五节的 execpolicy 回归用例。
3. 个人技能在 `~/.codex/skills`（老路径）与 `~/.agents/skills`（新路径）存在重复，
   与本项目无关，将来可自行收敛到新路径。
4. **维护约定**：`.claude/settings.json` 的 allow/deny 变更后，
   同步修改 `.codex/rules/safety.rules` 并重跑回归（与 skills/指令的
   "Claude 准源 → Codex 同步"约定一致）。
