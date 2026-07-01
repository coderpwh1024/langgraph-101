# Codex 项目目录结构说明

> 本文说明 OpenAI **Codex CLI** 的目录与配置组织方式，作为团队使用 Codex 协作时的参考。
> 内容依据 Codex 官方文档（`developers.openai.com/codex`、`github.com/openai/codex`）整理，
> 并结合本机 `~/.codex/` 实际目录做了核对。

## 目录

- [一、总体结构](#一总体结构)
- [二、全局配置目录 `~/.codex/`](#二全局配置目录-codex)
- [三、核心配置文件 `config.toml`](#三核心配置文件-configtoml)
- [四、指令文件 `AGENTS.md`](#四指令文件-agentsmd)
- [五、项目级 `.codex/` 目录](#五项目级-codex-目录)
- [六、配置优先级（precedence）](#六配置优先级precedence)
- [七、与本仓库（langgraph-101）的关系](#七与本仓库langgraph-101的关系)

---

## 一、总体结构

Codex 的配置分为三个层次，按「作用范围从大到小」排列：

| 层次 | 位置 | 作用范围 | 是否入库 |
| --- | --- | --- | --- |
| 全局（user） | `~/.codex/`（可用 `CODEX_HOME` 覆盖） | 当前用户的所有项目 | 否（本机私有） |
| 项目（project） | 仓库内 `.codex/` 与各级 `AGENTS.md` | 单个仓库 | 通常入库共享 |
| 系统（system） | `/etc/codex/config.toml`、`requirements.toml` | 整台机器 / 受管环境 | 由管理员维护 |

其中：

- **`config.toml`** 是「机器可读」的配置（模型、沙箱、审批策略、MCP 服务等）。
- **`AGENTS.md`** 是「自然语言」的指令（构建/测试命令、编码规范、协作约定等）。

两者职责互补：`config.toml` 决定 Codex **怎么发现与处理**指令文件，`AGENTS.md` 告诉 Codex
**要做什么、有哪些预期**。

---

## 二、全局配置目录 `~/.codex/`

用户级配置目录，默认位于 `~/.codex/`，可通过环境变量 `CODEX_HOME` 指向其他路径。
下面是各常见文件 / 子目录的用途（`*` 标记的为本机实际存在项）：

| 文件 / 目录 | 用途 |
| --- | --- |
| `config.toml` * | 用户级主配置（模型、沙箱、审批、MCP、插件等），详见第三节 |
| `AGENTS.md` | 全局指令文件，作为所有项目指令链的「基座」（`AGENTS.override.md` 优先） |
| `auth.json` * | 登录凭证（API key / OAuth token）。**私密文件，切勿提交或外传** |
| `history.jsonl` * | 会话输入历史（受 `history.persistence` 控制） |
| `sessions/` * | 历史会话记录（transcript），可用于恢复 / 回看 |
| `session_index.jsonl` * | 会话索引 |
| `log/` 或 `codex-tui.log` | 运行日志目录 / TUI 明文日志（在配置 `log_dir` 后开启） |
| `skills/` * | 已安装的技能（skills） |
| `plugins/` * | 已启用的插件（如 documents、pdf、browser 等） |
| `mcp_servers`（配置于 `config.toml`） | MCP 服务定义（如 `node_repl`） |
| `cache/`、`models_cache.json` * | 模型元数据与缓存 |
| `*.sqlite`（`logs_*`、`state_*`、`memories_*`、`goals_*`）* | 内部状态、日志、记忆等 SQLite 数据库 |
| `version.json`、`installation_id` * | 版本与安装标识 |

> 说明：`~/.codex/` 属于本机私有目录，包含凭证与历史记录，**不应纳入版本控制**。
> 需要团队共享的规则应写入仓库内的 `AGENTS.md` 或 `.codex/config.toml`。

---

## 三、核心配置文件 `config.toml`

用户级配置位于 `~/.codex/config.toml`，采用 TOML 格式。常用配置项：

| 配置项 | 说明 |
| --- | --- |
| `model` | 使用的模型，例如 `"gpt-5.5"` |
| `model_reasoning_effort` | 推理强度，如 `"high"` |
| `model_provider` | 选择 provider（默认 `openai`）。**仅用户级生效，项目级会被忽略** |
| `approval_policy` | 执行命令前何时暂停征求批准：`untrusted` / `on-request` / `never`（`on-failure` 已弃用） |
| `sandbox_mode` | 命令执行沙箱策略：`read-only` / `workspace-write` / `danger-full-access` |
| `[mcp_servers.<id>]` | 定义 MCP 服务，子键含 `command` / `args` / `env` / `url` / `enabled` / 超时等 |
| `[profiles.<name>]` | 命名配置层，用 `--profile <name>` 选择。**仅用户级生效** |
| `[projects."<path>"]` | 项目信任级别 `trust_level`（`trusted` / `untrusted`）；不信任的项目会跳过其 `.codex/` 层 |
| `notify` | 通知回调命令，接收 Codex 传入的 JSON 负载。**仅用户级生效** |
| `[history]` | `persistence`（`save-all` / `none`）控制是否写入 `history.jsonl`；`max_bytes` 限制大小 |
| `[shell_environment_policy]` | 子进程环境变量策略：`inherit` / `include_only` / `exclude` / `set` 等 |
| `project_doc_fallback_filenames` | 除 `AGENTS.md` 外，额外当作指令文件的文件名（如 `TEAM_GUIDE.md`） |
| `project_doc_max_bytes` | 指令链合并的字节上限，默认 32 KiB |

本机 `config.toml` 片段示例：

```toml
model = "gpt-5.5"
model_reasoning_effort = "high"

[mcp_servers.node_repl]
command = "/Applications/Codex.app/Contents/Resources/cua_node/bin/node_repl"
args = []
startup_timeout_sec = 120
```

---

## 四、指令文件 `AGENTS.md`

`AGENTS.md` 是 Codex 在开始工作前读取的自然语言指令，用来传达构建/测试命令、编码规范、
审批要求、仓库约定等。Codex 每次运行（或每个 TUI 会话）会构建一条「指令链」。

### 4.1 查找顺序

1. **全局作用域**：Codex home 目录（默认 `~/.codex/`）。先找 `AGENTS.override.md`，
   不存在再用 `AGENTS.md`；本级只取第一个非空文件。
2. **项目作用域**：从项目根（通常是 Git 根）**向下逐级走到当前工作目录**。每一级目录依次查找
   `AGENTS.override.md` → `AGENTS.md` → `project_doc_fallback_filenames` 中的名字，每级最多取一个文件。
   若未找到项目根，则只检查当前目录。

### 4.2 合并与优先级

- 所有命中的文件**从根到叶按顺序拼接**（以空行连接）。
- **越靠近当前目录的文件优先级越高**（deepest wins）：它们出现在合并提示的更后面，从而覆盖上层指导。
- 跳过空文件；合并大小达到 `project_doc_max_bytes`（默认 32 KiB）后停止追加。

即：**全局 `AGENTS.md` 打底 → 仓库根 `AGENTS.md` 叠加 → 子目录 `AGENTS.md` 最终生效**。

### 4.3 与 `config.toml` 的区别

| `AGENTS.md` | `config.toml` |
| --- | --- |
| 自然语言指令与上下文 | 机器可读的配置项 |
| 按目录分层合并、就近覆盖 | 设定 `project_doc_fallback_filenames`、`project_doc_max_bytes` 等发现机制 |
| 告诉 Codex「做什么、有何预期」 | 告诉 Codex「如何发现并处理指令文件」 |

---

## 五、项目级 `.codex/` 目录

在仓库内可放置项目级配置，仅对**受信任（trusted）**的项目生效：

| 文件 | 用途 |
| --- | --- |
| `.codex/config.toml` | 项目级配置覆盖（部分键如 `model_provider` / `profiles` / `notify` 在此无效） |
| `.codex/hooks.json` | 项目级生命周期钩子 |
| `AGENTS.md`（仓库根及各级子目录） | 项目指令链，见第四节 |

> 不受信任的项目会跳过所有项目级 `.codex/` 层（含 project-local config、hooks、rules），
> 但用户级与系统级配置仍会加载。信任级别由用户级 `config.toml` 的
> `[projects."<path>"].trust_level` 控制。

---

## 六、配置优先级（precedence）

Codex 解析配置时，从**高到低**为：

1. CLI 参数 / `--config`
2. 项目级 `.codex/config.toml`
3. profile 文件（`<name>.config.toml`）
4. 用户级 `~/.codex/config.toml`
5. 系统级 `/etc/codex/config.toml`
6. 内置默认值

受管环境中，管理员可用 `requirements.toml` 强制约束（例如
`allow_managed_hooks_only = true` 仅允许受管 hooks）；该键**只在 `requirements.toml` 中生效**，
写在 `config.toml` 无效。

---

## 七、与本仓库（langgraph-101）的关系

本仓库已包含一个仓库根级 [`AGENTS.md`](../AGENTS.md)，它是 Codex 指令链中的「项目层」，
与 [`CLAUDE.md`](../CLAUDE.md) 内容互补：

- `AGENTS.md`：面向 Codex 的仓库协作指南（项目结构、运行命令、编码风格、提交规范、安全提示）。
- `CLAUDE.md`：面向 Claude 的详细 Python 风格与评审规则。

在本仓库使用 Codex 时的建议：

- 团队共享的规范写进仓库根 `AGENTS.md`；如需为 `notebooks/201/` 等子目录定制更细的规则，
  可在该子目录新增 `AGENTS.md`，利用「就近覆盖」机制生效。
- 模型、沙箱、MCP 等个人偏好放在本机 `~/.codex/config.toml`，**不要**提交到仓库。
- 切勿提交 `.env`、`auth.json` 或任何真实密钥（与 `AGENTS.md` 的安全约定一致）。

---

## 参考资料

- Codex 配置总览：<https://github.com/openai/codex/blob/main/docs/config.md>
- 配置参考（config-reference）：<https://developers.openai.com/codex/config-reference>
- AGENTS.md 指南：<https://developers.openai.com/codex/guides/agents-md>
- AGENTS.md 规范站点：<https://agents.md>
