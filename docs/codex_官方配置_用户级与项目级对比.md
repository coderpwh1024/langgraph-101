# Codex 官方配置：用户级 vs 项目级 分层对比

> 核对日期：2026-07-05
> 依据：Codex 官方文档（developers.openai.com/codex），各节均附原文关键句与链接。
> 范围：config.toml、AGENTS.md、Skills、MCP、Plugins、Subagents（自定义 Agent）、
> Hooks、Rules、Custom Prompts（已废弃）、Permissions/沙箱。
> 姊妹篇：[codex_claude_配置对比.md](codex_claude_配置对比.md)（Codex 与 Claude Code 双侧对照）。

---

## 〇、配置层级总览（先看这张图）

Codex 的配置分布在**四个物理层级**，加载优先级从高到低：

```
优先级高 ▲
│ 1. CLI 参数 / -c --config 一次性覆盖        （仅本次运行）
│ 2. 项目级   <repo>/.codex/ + <repo>/.agents/ （入库、团队共享；⚠️ 仅 trusted 项目生效）
│             └─ 子目录可再嵌套，"closest wins"（就近优先）
│ 3. Profile  ~/.codex/<name>.config.toml      （--profile 按场景切换）
│ 4. 用户级   ~/.codex/ + ~/.agents/           （个人全局，跨项目）
│ 5. 系统级   /etc/codex/                      （机器/容器级；企业可另加 requirements.toml 强制约束）
▼ 6. 内置默认值
优先级低
```

官方原文（[config-basic](https://developers.openai.com/codex/config-basic)）：

- "Codex stores user-level configuration at `~/.codex/config.toml`."
- 项目配置 "closest wins; **trusted projects only**"。
- "Codex loads project `.codex/` layers only when you trust the project." 未受信任时
  "Codex skips project-scoped `.codex/` layers, **including project-local config, hooks, and rules**"，
  但用户级、系统级仍然加载。

两侧目录的完整形态：

```
~（用户级，个人全局）                        <repo>（项目级，入库共享）
├── .codex/                                  ├── .codex/            ⚠️ trusted 才加载
│   ├── config.toml        基础配置/MCP/插件  │   ├── config.toml    项目覆盖配置/MCP
│   ├── AGENTS.md          全局指令           │   ├── agents/*.toml  项目自定义 Agent
│   ├── AGENTS.override.md 全局指令(优先)     │   ├── hooks.json     项目 Hooks
│   ├── agents/*.toml      个人自定义 Agent   │   └── rules/*.rules  项目命令规则
│   ├── hooks.json         个人 Hooks         ├── .agents/
│   ├── rules/*.rules      个人命令规则       │   └── skills/        项目技能（无 trusted 要求）
│   ├── prompts/*.md       自定义提示词(废弃) ├── AGENTS.md          项目指令（根）
│   └── auth.json 等       凭证/运行时        └── <子目录>/AGENTS.md 嵌套指令（就近优先）
└── .agents/
    └── skills/            个人技能
```

> **一个容易忽略的关键点**：技能放在 `.agents/`（开放标准 [agentskills.io](https://agentskills.io) 路径），
> 其余项目级配置放在 `.codex/`；且 **`.codex/` 受 trusted 门槛管控，`.agents/skills/` 不受**。

---

## 一、逐项对比

每项按「用户级 → 项目级 → 差异重点」展开。

### 1. config.toml（基础配置）

| 层级 | 路径 | 说明 |
| --- | --- | --- |
| 用户级 | `~/.codex/config.toml` | 个人默认：模型、`approval_policy`、`sandbox_mode`、MCP、插件启停、`[agents]`、`[[skills.config]]` 等 |
| Profile | `~/.codex/<name>.config.toml` | `--profile <name>` 选用；官方建议 "keep profile files focused on the values that differ" |
| 项目级 | `<repo>/.codex/config.toml` | 按仓库/子目录覆盖，可嵌套，就近优先；**仅 trusted 项目生效** |
| 系统级 | `/etc/codex/config.toml` | 机器级基础配置（Unix） |

**差异重点**：

- 项目级优先于用户级（这与"用户配置覆盖项目配置"的直觉相反，注意方向）。
- 模型/速度类设置（`model`、`model_reasoning_effort` 等）也走同一优先级链，
  因此项目可以按仓库固定模型档位，个人用 profile 切换快慢档。
- 一次性覆盖：`codex -c key=value`，优先级最高（值按 TOML 解析，解析失败则按字符串处理）。
- **项目级有天花板**：即使 trusted，项目 config 也**无法覆盖机器级键**
  （provider、认证、通知、遥测等）——这些只能在用户级/系统级设置。
- **0.134.0 起 profile 写法变更**：`--profile` 不再读取 config.toml 里的
  `[profiles.<name>]` 表，旧写法须迁移到独立的 `~/.codex/<name>.config.toml` 文件。

📄 [config-basic](https://developers.openai.com/codex/config-basic) ·
[config-reference](https://developers.openai.com/codex/config-reference)

### 2. AGENTS.md（项目指令）

| 层级 | 位置 | 规则 |
| --- | --- | --- |
| 用户级 | `~/.codex/AGENTS.override.md` → `~/.codex/AGENTS.md` | 先找 override 再找普通文件，"Codex uses only the first non-empty file at this level" |
| 项目级 | 项目根 → 当前工作目录，逐级向下 | "Starting at the project root (typically the Git root), Codex walks down to your current working directory"；每个目录内 `AGENTS.override.md` → `AGENTS.md` → `project_doc_fallback_filenames` 备用名，"at most one file per directory" |

**合并语义：拼接（concatenate），不是覆盖**——
"Codex concatenates files from the root down, joining them with blank lines."
越靠近当前目录的文件出现在提示词越后面，实际优先级越高。

**差异重点**：

- 总量上限 `project_doc_max_bytes` 默认 **32 KiB**，超限即停止追加
  （"stops adding files once the combined size reaches the limit"）。
- `AGENTS.override.md` 用于**临时压制**同目录的 AGENTS.md 而不删除它，
  "Remove the override to restore the shared guidance."
- AGENTS.md **不受 trusted 门槛限制**（它不在 `.codex/` 里），任何项目都会被读取。
- 指令链每次运行构建一次（TUI 中通常每会话一次）；找不到项目根时只检查当前目录。

**官方给出的三个验证/审计方法**：

```bash
# 1. 直接让模型复述当前加载的指令
codex --ask-for-approval never "Summarize the current instructions."
# 2. 从子目录启动，确认嵌套 override 生效
codex --cd services/payments "..."
# 3. 打开日志，审计实际加载了哪些 AGENTS.md 文件
codex -c log_dir=./.codex-log   # 之后查看 codex-tui.log
```

📄 [guides/agents-md](https://developers.openai.com/codex/guides/agents-md)

### 3. Skills（技能）

官方扫描表（"Codex reads skills from repository, user, admin, and system locations"）：

| 作用域 | 路径 | 说明 |
| --- | --- | --- |
| 项目级（REPO） | 从当前目录到仓库根，**每一级**的 `.agents/skills/` | "Codex scans `.agents/skills` in every directory from your current working directory up to the repository root" |
| 用户级（USER） | `~/.agents/skills/` | 个人技能，跨仓库 |
| 系统级（ADMIN） | `/etc/codex/skills/` | 机器/容器共享 |
| 内置（SYSTEM） | 随 Codex 捆绑 | 如 skill-creator、plan |

**合并语义：不合并、不覆盖**——
"If two skills share the same `name`, Codex doesn't merge them; **both** can appear in skill selectors."
这与 AGENTS.md（拼接）、config.toml（就近覆盖）都不同：同名技能会**重复出现**，需自行避免两级重名。

**单个 skill 的目录结构**（官方示例）：

```
my-skill/
├── SKILL.md          # 必需：指令 + 元数据（frontmatter 须含 name 和 description）
├── scripts/          # 可选：可执行代码
├── references/       # 可选：文档
├── assets/           # 可选：模板、资源
└── agents/
    └── openai.yaml   # 可选：Codex 专属外观与依赖配置
```

**差异重点**：

- frontmatter 必需且仅官方承诺 `name` + `description` 两个字段
  （"The `SKILL.md` file must include `name` and `description`"）；
  图标、隐式触发开关等扩展元数据放 `agents/openai.yaml`，不放 frontmatter。
- 支持**符号链接**的 skill 文件夹，扫描时会跟随链接目标（可用于多仓库共享同一份技能源）。
- 启停不分项目：在**用户级** `~/.codex/config.toml` 用 `[[skills.config]]`（`path` + `enabled = false`）按路径禁用。
- 技能列表有上下文预算：初始列表最多占上下文窗口 2%，超出先裁描述、再裁技能。
- 路径在 `.agents/` 下，**不受 trusted 限制**；历史路径 `~/.codex/skills/` 已不在官方扫描表中（本机实测仍被扫，见姊妹篇）。

📄 [skills](https://developers.openai.com/codex/skills)

### 4. MCP 服务器

| 层级 | 位置 | 说明 |
| --- | --- | --- |
| 用户级 | `~/.codex/config.toml` 的 `[mcp_servers.<name>]` 表 | "By default this is `~/.codex/config.toml`"；CLI 与 IDE 扩展共享同一配置 |
| 项目级 | `<repo>/.codex/config.toml` | 官方明确支持："you can also scope MCP servers to a project with `.codex/config.toml` (**trusted projects only**)" |

**差异重点**：

- MCP 没有独立配置文件，就是 config.toml 的一张表，因此合并语义跟随 config 层级（项目级可增补/覆盖用户级同名服务器）。
- 两种传输：STDIO（`command`/`args`/`env`）和 Streamable HTTP（`url`/`bearer_token_env_var`/OAuth）。
- 管理入口：`codex mcp add <name> -- <command>`、`codex mcp login <name>`、TUI 内 `/mcp`。
- 细粒度控制：`enabled_tools`/`disabled_tools` 白/黑名单、`default_tools_approval_mode`（`auto`/`prompt`/`approve`）、
  `startup_timeout_sec`（默认 10s）、`tool_timeout_sec`（默认 60s）。

📄 [mcp](https://developers.openai.com/codex/mcp)

### 5. Plugins（插件）

> "Plugins bundle **skills, app integrations, and MCP servers** into reusable workflows for Codex."

| 层级 | 支持情况 | 说明 |
| --- | --- | --- |
| 用户级 | ✅ 安装与启停都在用户级 | 安装：Codex 应用 Plugins 页或 CLI `/plugins`；启停：`~/.codex/config.toml` 中 `[plugins."<name>@<marketplace>"] enabled = false` |
| 项目级 | ❌ 无项目级安装目录 | 仅在**分发**层面支持团队共享："You can share plugins by publishing them through a marketplace source, such as a repo marketplace" |

**差异重点**（与其他项差别最大的一项）：

- 插件是**用户级安装物**，不能像 skills/hooks 那样放进仓库随代码走；
  想让团队统一，只能走 marketplace 源（含 repo marketplace）让每人自行安装。
- 安装后仍受既有审批设置约束："your existing approval settings still apply"。
- 官方精选示例：Codex Security、Gmail、Google Drive、Slack、**Sites** 等。
- 三个来源分类：Curated by OpenAI / Shared with you / Created by you。

📄 [plugins](https://developers.openai.com/codex/plugins)

### 6. Subagents / 自定义 Agent

| 层级 | 路径 | 说明 |
| --- | --- | --- |
| 用户级 | `~/.codex/agents/*.toml` | 官方原文："add standalone TOML files under `~/.codex/agents/` for personal agents" |
| 项目级 | `<repo>/.codex/agents/*.toml` | "or `.codex/agents/` for project-scoped agents"（位于 `.codex/` 下，受 trusted 门槛管控） |

**文件格式**：每个 TOML 定义一个 agent，必填 `name`、`description`、`developer_instructions`；
`name` 字段是身份来源（"the `name` field is the source of truth"），文件名一致只是惯例。

**差异重点**：

- 自定义 agent 文件本身就是一个**配置层**："custom agents can override the same settings as a
  normal Codex session config"——可内嵌 `model`、`model_reasoning_effort`、`sandbox_mode`、
  `mcp_servers`、`skills.config` 等键，省略则继承父会话。
- 同名可覆盖内置 agent（内置三个：`default` / `worker` / `explorer`）：
  "If a custom agent name matches a built-in agent such as `explorer`, your custom agent takes precedence."
- 但**运行时设置更硬**：父会话的 `/permissions`、`--yolo` 等实时设置会重新套用，
  "even if the selected custom agent file sets different defaults."
- 全局编排参数在 config.toml `[agents]` 表：`max_threads`（默认 6）、`max_depth`（默认 1，仅允许一层子代理）、
  `job_max_runtime_seconds`（CSV 批量任务超时，默认回退 1800s）。
- 触发是显式的："Codex only spawns subagents when you explicitly ask it to."；CLI 用 `/agent` 切换/查看线程。

📄 [subagents](https://developers.openai.com/codex/subagents)

### 7. Hooks（生命周期钩子）

> "Hooks are an extensibility framework for Codex" · "Hooks are enabled by default."

| 层级 | 位置（两种形式二选一或并存） |
| --- | --- |
| 用户级 | `~/.codex/hooks.json` 或 `~/.codex/config.toml` 内联 `[hooks]` |
| 项目级 | `<repo>/.codex/hooks.json` 或 `<repo>/.codex/config.toml`；"Project-local hooks load only when the project `.codex/` layer is **trusted**." |

**合并语义：全部加载（并集）**——
"If more than one hook source exists, Codex loads **all** matching hooks."
即用户级与项目级 hooks 同时生效，不互相覆盖（又一种不同于前几项的语义）。

**差异重点**：

- 事件覆盖完整生命周期：`SessionStart`、`SubagentStart`/`SubagentStop`、
  `PreToolUse`/`PostToolUse`（可拦截 Bash、`apply_patch`、MCP 工具）、`PermissionRequest`（可 allow/deny）、
  `PreCompact`/`PostCompact`、`UserPromptSubmit`、`Stop`。
- 结构三层：事件 → matcher 组 → 处理器；当前仅 `type: "command"` 可运行
  （"Only `type: \"command\"` handlers run today."）。
- 安全模型：非托管 hooks 必须先逐条审查信任
  （"Codex requires you to review and trust the exact hook definition"），TUI 用 `/hooks` 管理。
- 协议：stdin 收 JSON、stdout/退出码回传决策，默认超时 600s；
  关闭方式 `[features] hooks = false`；插件与企业 `requirements.toml` 也可携带 hooks。

📄 [hooks](https://developers.openai.com/codex/hooks)

### 8. Rules（命令级规则，实验性）

> "Rules are experimental and may change."

| 层级 | 路径 | 说明 |
| --- | --- | --- |
| 用户级 | `~/.codex/rules/*.rules` | TUI 里点"允许"会自动持久化到这里："Codex writes to the user layer at `~/.codex/rules/default.rules`" |
| 项目级 | `<repo>/.codex/rules/*.rules` | "Project-local rules under `<repo>/.codex/rules/` load only when the project `.codex/` layer is **trusted**." |

**合并语义：取最严格**——
"Codex applies the most restrictive decision when more than one rule matches
(`forbidden` > `prompt` > `allow`)."
所以项目级无法"放松"用户级的禁令，只能收紧——这对安全设计非常关键。

**差异重点**：

- 格式为 Starlark 的 `prefix_rule()`：`pattern`（前缀 token 列表，元素可为并集）、
  `decision`（`allow`/`prompt`/`forbidden`，默认 allow）、`justification`、
  `match`/`not_match`（内联自测样例，加载时校验）。
- **前缀严格按序匹配**，参数乱序不命中（`git push --force` 规则拦不住 `git push origin --force`），
  须配合沙箱兜底；实测记录见姊妹篇第五节。
- `bash -lc` 复合命令若由安全操作符连接的简单命令组成，会被拆开逐条评估，"the most restrictive result wins"。
- 测试工具：`codex execpolicy check`。

📄 [rules](https://developers.openai.com/codex/rules)

### 9. Custom Prompts / 斜杠命令（⚠️ 已废弃，被 Skills 取代）

| 层级 | 支持情况 | 说明 |
| --- | --- | --- |
| 用户级 | ✅（仅此一级） | `~/.codex/prompts/*.md`，只扫顶层 Markdown，不递归子目录 |
| 项目级 | ❌ 不支持 | 官方明确其定位是本地个人物，"they're not shared through your repository" |

**差异重点**：

- 官方已标记 **deprecated**，推荐用 Skills 承接"可复用指令"场景（Skills 才有项目级路径）。
- 仍可用：`/prompts:<name>` 调用；frontmatter 支持 `description`、`argument-hint`；
  占位符 `$1`–`$9`、`$ARGUMENTS`、命名占位符（`$FILE` 等，`KEY=value` 传入）。
- 迁移判断：需要入库共享、或希望模型隐式触发 → 改写成 skill；纯个人快捷指令 → 可暂留。

📄 [custom-prompts](https://developers.openai.com/codex/custom-prompts) ·
[guides/slash-commands](https://developers.openai.com/codex/guides/slash-commands/)

### 10. Permissions / 沙箱（新旧两套，Beta 过渡期）

| 层级 | 支持情况 |
| --- | --- |
| 用户级 | ✅ `~/.codex/config.toml`（旧：`approval_policy` + `sandbox_mode`；新：`default_permissions` + `[permissions.*]`） |
| 项目级 | 旧设置随 config.toml 层级可被项目覆盖（trusted）；新 Permission Profiles 文档目前只演示系统级与用户级 |
| 系统/企业级 | ✅ `/etc/codex/config.toml`；托管设备可用 `requirements.toml` 强制（如 `allowed_permission_profiles`、禁止 `approval_policy = "never"`） |

**差异重点**：

- **新旧互斥**："Configure either `default_permissions` and `[permissions]`, or
  `sandbox_mode` / `sandbox_workspace_write`, but not both."
  任一层出现 `sandbox_mode` 或传了 `--sandbox`，即整体回退旧模式。
- 三个内置 profile：`:read-only` / `:workspace` / `:danger-full-access`，
  可用 `[permissions.<name>]` + `extends` 自定义（不能继承 `:danger-full-access`）。
- 网络域名规则：`"*.github.com"`（仅子域）、`"**.example.com"`（主域+子域）、
  "Deny entries override allow entries."、无 allow 条目时默认全拦；
  本地回环需显式放行或 `allow_local_binding = true`。

📄 [permissions](https://developers.openai.com/codex/permissions) ·
[concepts/sandboxing](https://developers.openai.com/codex/concepts/sandboxing)

---

## 二、总对照速查表

| 配置项 | 用户级路径 | 项目级路径 | 项目级前提 | 多层合并语义 |
| --- | --- | --- | --- | --- |
| 基础配置 | `~/.codex/config.toml`（+ profile） | `<repo>/.codex/config.toml`（可嵌套） | ⚠️ trusted | **就近覆盖**（项目 > profile > 用户 > 系统） |
| 指令 AGENTS.md | `~/.codex/AGENTS(.override).md` | 根→当前目录逐级 `AGENTS.md` | 无 | **顺序拼接**，越近越靠后越优先；总量 32 KiB |
| Skills | `~/.agents/skills/` | 各级 `.agents/skills/`（cwd→仓库根） | 无 | **不合并**，同名并列出现 |
| MCP | config.toml `[mcp_servers.*]` | 项目 config.toml 同表 | ⚠️ trusted | 随 config 层级 |
| Plugins | 用户级安装 + `[plugins.*]` 启停 | ❌ 无（仅 marketplace 分发） | — | — |
| Subagents | `~/.codex/agents/*.toml` | `<repo>/.codex/agents/*.toml` | ⚠️ trusted（`.codex/` 层） | 同名时自定义 > 内置；运行时设置最硬 |
| Hooks | `~/.codex/hooks.json` 或 `[hooks]` | `<repo>/.codex/hooks.json` 或 `[hooks]` | ⚠️ trusted + 逐条信任 | **并集**，全部加载 |
| Rules | `~/.codex/rules/*.rules` | `<repo>/.codex/rules/*.rules` | ⚠️ trusted | **取最严**（forbidden > prompt > allow） |
| Custom Prompts | `~/.codex/prompts/*.md` | ❌ 不支持 | — | —（已废弃，改用 Skills） |
| Permissions | config.toml（新旧两套） | 旧设置可随项目 config 覆盖 | ⚠️ trusted | 随 config 层级；新旧互斥 |

---

## 三、重点差异专述（最值得记住的 5 条）

1. **`.codex/` 与 `.agents/` 的信任边界不同**。
   项目级 `.codex/`（config、agents、hooks、rules）统一受 trusted 门槛管控——
   不信任的仓库这些全部跳过；而 `AGENTS.md` 与 `.agents/skills/` 不在此列，总是被读取。
   含义：**能执行命令/改行为的配置有信任门槛，纯文本指令与技能没有**
   （技能虽含脚本，但执行仍受沙箱与审批约束）。

2. **五种截然不同的多层合并语义**（最容易踩坑的地方）：
   config.toml 就近**覆盖**、AGENTS.md 顺序**拼接**、skills **不合并**（同名并列）、
   hooks **并集**全加载、rules **取最严**。同一对"用户级 vs 项目级"路径，
   冲突结果因配置项而完全不同，不能凭直觉套用。

3. **rules 只能收紧、不能放松**。因为多规则取最严，项目级 `allow` 压不过用户级
   `forbidden`——把硬禁令放用户/系统级即成为全局底线。

4. **plugins 与 custom prompts 是仅有的"无项目级"配置**。
   插件靠 marketplace 源做团队分发；custom prompts 已废弃，官方迁移方向就是有项目级路径的 Skills。

5. **优先级方向是"项目 > 用户"**（config 类），与部分工具相反；
   但 subagents 的运行时设置（`/permissions`、`--yolo`）又高于 agent 文件默认值——
   总原则：**越接近本次运行的层，优先级越高**（CLI 参数 > 项目 > profile > 用户 > 系统）。

---

## 四、官方文档索引

| 主题 | 链接 |
| --- | --- |
| 配置基础（层级与优先级） | <https://developers.openai.com/codex/config-basic> |
| 配置参考 / 高级配置 | <https://developers.openai.com/codex/config-reference> · <https://developers.openai.com/codex/config-advanced> |
| AGENTS.md 指南 | <https://developers.openai.com/codex/guides/agents-md> |
| Agent Skills | <https://developers.openai.com/codex/skills> |
| MCP | <https://developers.openai.com/codex/mcp> |
| Plugins | <https://developers.openai.com/codex/plugins> |
| Subagents | <https://developers.openai.com/codex/subagents> |
| Hooks | <https://developers.openai.com/codex/hooks> |
| Rules（实验性） | <https://developers.openai.com/codex/rules> |
| Custom Prompts（已废弃） | <https://developers.openai.com/codex/custom-prompts> |
| Permissions（Beta） | <https://developers.openai.com/codex/permissions> |
| 沙箱概念 | <https://developers.openai.com/codex/concepts/sandboxing> |
| Customization 概念总览 | <https://developers.openai.com/codex/concepts/customization> |
| Agent Skills 开放标准 | <https://agentskills.io> |
| AGENTS.md 开放格式（Linux 基金会 Agentic AI Foundation 托管） | <https://agents.md> |
| openai/codex 仓库 AGENTS.md 文档 | <https://github.com/openai/codex/blob/main/docs/agents_md.md> |
| skills 目录位置的官方讨论 | <https://github.com/openai/codex/discussions/9682> |
| OpenAI 官方 Skills Catalog | <https://github.com/openai/skills> |

> **信息来源说明**（核对于 2026-07-05）：官方**没有**发布过单独的完整目录结构图，
> X 上也未检索到 Codex 工程师发布的目录结构分享——权威来源即上表的
> developers.openai.com 文档与 openai/codex 仓库；本文的目录树为据此拼合。
> 各工具的项目级技能目录约定对照：Codex `.agents/skills/`、Claude Code `.claude/skills/`、
> GitHub Copilot `.github/skills/`、OpenCode `.opencode/skills/`；
> 社区标准仓库的共识方向是 `.agents/skills/`。
