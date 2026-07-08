# Codex CLI 中的斜杠命令（Slash Commands）

斜杠命令为你提供快速、以键盘为先的方式来控制 Codex。在输入框（composer）中键入 `/` 即可打开斜杠命令弹窗，选择一个命令，Codex 就会执行相应操作，比如切换模型、调整权限，或对长对话进行总结——全程无需离开终端。

本指南将向你展示如何：

- 为某项任务找到合适的内置斜杠命令
- 使用 `/model`、`/fast`、`/personality`、`/permissions`、`/approve`、`/raw`、`/agent`、`/status` 等命令来引导正在进行的会话

## 内置斜杠命令

Codex 自带以下命令。打开斜杠命令弹窗后，输入命令名称即可过滤列表。

当某个任务正在运行时，你可以键入斜杠命令并按 `Tab` 键，将其排入下一轮（turn）的队列。Codex 会在排队的斜杠命令实际运行时才解析它们，因此命令菜单和错误提示会在当前轮次结束后才出现。在命令入队之前，斜杠命令的自动补全仍然可用。

| 命令 | 用途 | 使用时机 |
| --- | --- | --- |
| [`/permissions`](#update-permissions-with-permissions) | 设置 Codex 无需事先询问即可执行的操作范围。 | 在会话中途放宽或收紧审批要求，例如在 Auto（自动）与 Read Only（只读）之间切换。 |
| [`/ide`](#include-ide-context-with-ide) | 包含打开的文件、当前选中内容及其他 IDE 上下文。 | 将编辑器上下文拉入下一条提示词，无需重复解释你在 IDE 中打开了什么。 |
| [`/keymap`](#remap-tui-shortcuts-with-keymap) | 重新映射 TUI 键盘快捷键。 | 查看并将自定义快捷键绑定持久化到 `config.toml` 中。 |
| [`/vim`](#toggle-vim-mode-with-vim) | 为输入框开关 Vim 模式。 | 在 Vim 的 normal/insert 行为与默认输入框编辑模式之间切换。 |
| [`/sandbox-add-read-dir`](#grant-sandbox-read-access-with-sandbox-add-read-dir) | 为沙箱授予额外目录的读取权限（仅限 Windows）。 | 解除那些需要读取当前可读根目录之外的绝对路径的命令的阻塞。 |
| [`/agent`](#switch-agent-threads-with-agent) | 切换活跃的 agent 线程。 | 查看或继续某个已派生子 agent 线程中的工作。 |
| [`/apps`](#browse-apps-with-apps) | 浏览应用（连接器）并将其插入到提示词中。 | 在要求 Codex 使用某个应用前，先以 `$app-slug` 形式附加它。 |
| [`/plugins`](#browse-plugins-with-plugins) | 浏览已安装及可发现的插件。 | 查看插件工具、安装推荐插件，或管理插件的可用性。 |
| [`/hooks`](#view-and-manage-lifecycle-hooks-with-hooks) | 查看并管理生命周期钩子（hooks）。 | 查看已配置的钩子、信任新的或已变更的钩子，或在非托管钩子运行前将其禁用。 |
| [`/clear`](#clear-the-terminal-and-start-a-new-chat-with-clear) | 清空终端并开始新的对话。 | 当你想重新开始时，同时重置可见界面和对话内容。 |
| [`/archive`](#archive-the-current-session-with-archive) | 归档当前会话并退出 Codex。 | 将当前会话从活跃会话列表中移除，但不删除其对话记录（transcript）。 |
| [`/delete`](#delete-the-current-session-with-delete) | 永久删除当前会话并退出 Codex。 | 当仅归档还不够时，删除对话记录及其派生的后代会话。 |
| [`/compact`](#keep-transcripts-lean-with-compact) | 总结可见对话以释放 token。 | 在长时间运行后使用，让 Codex 保留关键要点而不撑爆上下文窗口。 |
| [`/copy`](#copy-the-latest-response-with-copy) | 复制最近一条已完成的 Codex 输出。 | 无需手动选中即可获取最近完成的响应或计划文本。也可以按 `Ctrl+O`。 |
| [`/diff`](#review-changes-with-diff) | 显示 Git diff，包括 Git 尚未跟踪的文件。 | 在提交或运行测试之前审查 Codex 的编辑。 |
| [`/exit`](#exit-the-cli-with-quit-or-exit) | 退出 CLI（与 `/quit` 相同）。 | 另一种写法；两个命令都会退出会话。 |
| [`/experimental`](#toggle-experimental-features-with-experimental) | 开关实验性功能。 | 从 CLI 启用可选功能，例如子 agent（subagents）。 |
| [`/approve`](#approve-an-auto-review-denial-with-approve) | 批准对最近一次自动审查拒绝的单次重试。 | 重试被自动审查器（auto reviewer）拒绝的命令或操作。 |
| [`/memories`](#configure-memories-with-memories) | 配置记忆（memory）的使用与生成。 | 无需离开 TUI 即可开启或关闭记忆注入或记忆生成。 |
| [`/skills`](#use-skills-with-skills) | 浏览并使用技能（skills）。 | 通过选择相关的本地技能来改进特定任务的表现。 |
| [`/import`](#import-claude-code-configuration-with-import) | 导入 Claude Code 的配置、项目文件和近期聊天记录。 | 将受支持的外部 agent 产物迁移到 Codex 配置和本地文件中。 |
| [`/feedback`](#send-feedback-with-feedback) | 向 Codex 维护者发送日志。 | 报告问题或向支持团队分享诊断信息。 |
| [`/init`](#generate-agentsmd-with-init) | 在当前目录生成 `AGENTS.md` 脚手架。 | 为你正在工作的仓库或子目录记录持久化指令。 |
| [`/logout`](#sign-out-with-logout) | 退出 Codex 登录。 | 在共享机器上使用时清除本地凭据。 |
| [`/mcp`](#list-mcp-tools-with-mcp) | 列出已配置的 Model Context Protocol（MCP）工具。 | 检查会话期间 Codex 可以调用哪些外部工具；加上 `verbose` 可查看服务器详情。 |
| [`/mention`](#highlight-files-with-mention) | 将文件附加到对话中。 | 让 Codex 关注你希望它接下来检查的特定文件或文件夹。 |
| [`/model`](#set-the-active-model-with-model) | 选择活跃模型（以及推理强度，若可用）。 | 在运行任务前，在通用模型（`gpt-4.1-mini`）与更深度的推理模型之间切换。 |
| [`/fast`](#toggle-fast-mode-with-fast) | 当模型目录提供 Fast 服务档位时，开关该档位。 | 开启或关闭当前模型的 Fast 档位，或查看当前线程是否正在使用它。 |
| [`/plan`](#switch-to-plan-mode-with-plan) | 切换到计划模式（plan mode），并可选发送一条提示词。 | 在实现工作开始前，让 Codex 先提出一个执行计划。 |
| [`/goal`](#set-or-view-a-task-goal-with-goal) | 设置、暂停、恢复、查看或清除任务目标。 | 在较大任务运行期间，给 Codex 一个持续跟踪的目标。 |
| [`/personality`](#set-a-communication-style-with-personality) | 为响应选择一种沟通风格。 | 让 Codex 更简洁、更详细或更具协作性，而无需修改你的指令。 |
| [`/ps`](#check-background-terminals-with-ps) | 显示实验性的后台终端及其最近输出。 | 无需离开主对话记录即可检查长时间运行的命令。 |
| [`/stop`](#stop-background-terminals-with-stop) | 停止所有后台终端。 | 取消当前会话启动的后台终端任务。 |
| [`/fork`](#fork-the-current-conversation-with-fork) | 将当前对话分叉（fork）到一个新线程。 | 从活跃会话分支出去探索新方案，而不丢失当前对话记录。 |
| [`/side`、`/btw`](#start-a-side-conversation-with-side) | 开启一个临时的旁路对话（side conversation）。 | 在不打乱主线程对话记录的前提下，提出一个聚焦的追问。 |
| [`/raw`](#toggle-raw-scrollback-with-raw) | 开关原始回滚（raw scrollback）模式。 | 在查看长输出时，让终端的选择和复制少受格式干扰。 |
| [`/resume`](#resume-a-saved-conversation-with-resume) | 从会话列表中恢复一个已保存的对话。 | 从之前的 CLI 会话继续工作，而无需从头开始。 |
| [`/new`](#start-a-new-conversation-with-new) | 在同一个 CLI 会话中开始新对话。 | 当你想在同一仓库中以全新提示词开始时，无需离开 CLI 即可重置聊天上下文。 |
| [`/quit`](#exit-the-cli-with-quit-or-exit) | 退出 CLI。 | 立即离开会话。 |
| [`/review`](#ask-for-a-working-tree-review-with-review) | 让 Codex 审查你的工作区（working tree）。 | 在 Codex 完成工作后运行，或当你希望有第二双眼睛检查本地改动时使用。 |
| [`/status`](#inspect-the-session-with-status) | 显示会话配置和 token 使用情况。 | 确认活跃模型、审批策略、可写根目录以及剩余上下文容量。 |
| [`/usage`](#view-account-usage-with-usage) | 查看账户 token 用量或使用限额重置。 | 在 TUI 内查看每日、每周或累计的 ChatGPT token 活动。 |
| [`/debug-config`](#inspect-config-layers-with-debug-config) | 打印配置层级及策略要求的诊断信息。 | 调试配置优先级和策略要求，包括实验性的网络约束。 |
| [`/statusline`](#configure-footer-items-with-statusline) | 交互式配置 TUI 状态栏字段。 | 挑选并排序底栏条目（模型/上下文/限额/git/tokens/会话），并持久化到 config.toml。 |
| [`/title`](#configure-terminal-title-items-with-title) | 交互式配置终端窗口或标签页标题字段。 | 挑选并排序标题条目，如项目、状态、线程、分支、模型和任务进度。 |
| [`/theme`](#choose-a-syntax-theme-with-theme) | 选择语法高亮主题。 | 预览并持久化一个终端语法高亮主题。 |

`/quit` 和 `/exit` 都会退出 CLI。请仅在保存或提交了所有重要工作之后再使用它们。

使用 `/permissions` 来调整 Codex 无需事先询问即可执行的操作。只有在需要重试一个刚被自动审查拒绝的操作时才使用 `/approve`。

## 使用斜杠命令控制你的会话

以下工作流可以让你的会话保持在正轨上，而无需重启 Codex。

### 使用 `/model` 设置活跃模型

1. 启动 Codex 并打开输入框。
2. 键入 `/model` 并按回车。
3. 从弹窗中选择一个模型，例如 `gpt-4.1-mini` 或 `gpt-4.1`。

预期结果：Codex 会在对话记录中确认新模型。运行 `/status` 可验证变更是否生效。

### 使用 `/fast` 开关 Fast 模式

1. 键入 `/fast on`、`/fast off` 或 `/fast status`。
2. 如果希望该设置持久生效，在 Codex 提示保存时进行确认。

预期结果：Codex 会报告当前模型的 Fast 服务档位在当前线程中是开启还是关闭。在 TUI 底栏中，你也可以通过 `/statusline` 显示 Fast 模式的状态栏条目。

Fast 档位命令由模型目录（catalog）驱动。如果当前模型没有声明 Fast 档位，Codex 就不会显示 `/fast`。

### 使用 `/personality` 设置沟通风格

使用 `/personality` 来改变 Codex 的沟通方式，而无需重写你的提示词。

1. 在活跃对话中，键入 `/personality` 并按回车。
2. 从弹窗中选择一种风格。

预期结果：Codex 会在对话记录中确认新风格，并在该线程的后续响应中使用它。

Codex 支持 `friendly`（友好）、`pragmatic`（务实）和 `none`（无）三种个性。使用 `none` 可禁用个性化指令。

如果活跃模型不支持特定于个性的指令，Codex 会隐藏此命令。

### 使用 `/plan` 切换到计划模式

1. 键入 `/plan` 并按回车，将活跃对话切换到计划模式。
2. 可选：提供内联提示词文本（例如 `/plan Propose a migration plan for this service`）。
3. 在使用 `/plan` 内联参数时，你可以粘贴内容或附加图片。

预期结果：Codex 进入计划模式，并将你可选的内联提示词作为第一条规划请求。

当有任务正在运行时，`/plan` 暂时不可用。

### 使用 `/goal` 设置或查看任务目标

1. 键入 `/goal <objective>` 来设置目标，例如 `/goal Finish the migration and keep tests green`。
2. 键入 `/goal` 查看当前目标。
3. 使用 `/goal pause`、`/goal resume` 或 `/goal clear` 来暂停、恢复或移除目标。

预期结果：在工作继续进行的同时，Codex 会将该目标始终附加在活跃线程上。

目标内容不得为空，且最多 4,000 个字符。对于更长的指令，请将详情放入一个文件中，并让目标指向该文件。

### 使用 `/experimental` 开关实验性功能

1. 键入 `/experimental` 并按回车。
2. 切换你想要的功能（例如 Apps 或 Smart Approvals），如果提示需要重启 Codex，则重启。

预期结果：Codex 将你的功能选择保存到配置中，并在重启后生效。

### 使用 `/approve` 批准自动审查的拒绝

当自动审查器拒绝了最近一次操作、而你希望 Codex 重试一次时，使用 `/approve`。

1. 键入 `/approve`。
2. 当 Codex 展示相关被拒操作时，确认重试。

预期结果：Codex 在当前会话策略下对该被拒操作重试一次。

### 使用 `/memories` 配置记忆

1. 键入 `/memories`。
2. 选择 Codex 是应该使用已有记忆、生成新记忆，还是保持记忆功能禁用。

预期结果：Codex 为后续会话更新相应的记忆设置。

### 使用 `/skills` 使用技能

1. 键入 `/skills`。
2. 挑选你希望 Codex 应用的技能。

预期结果：Codex 插入所选技能的上下文，使下一条请求遵循该技能的指令。

### 使用 `/import` 导入 Claude Code 配置

1. 键入 `/import`。
2. 选择你想迁移的 Claude Code 配置、项目文件或近期聊天记录。

预期结果：Codex 打开外部 agent 导入选择器，并将所选的受支持产物导入到 Codex 配置和本地文件中。

请在本地 TUI 会话中运行 `/import`。在任务运行期间、远程会话中，以及连接到本地 app-server 守护进程时，该命令不可用。

### 使用 `/clear` 清空终端并开始新对话

1. 键入 `/clear` 并按回车。

预期结果：Codex 清空终端、重置可见的对话记录，并在同一个 CLI 会话中开始新的对话。

与 <kbd>Ctrl</kbd>+<kbd>L</kbd> 不同，`/clear` 会开启一个新对话。

<kbd>Ctrl</kbd>+<kbd>L</kbd> 只清空终端视图并保留当前对话。任务进行期间，Codex 会禁用这两个操作。

### 使用 `/archive` 归档当前会话

1. 键入 `/archive` 并按回车。
2. 确认你要归档当前会话并退出 Codex。

预期结果：Codex 归档当前会话并关闭交互式 TUI。Codex 会将会话记录保留在本地；之后可以通过 `codex unarchive <SESSION>` 恢复。

任务运行期间，`/archive` 不可用。

### 使用 `/delete` 删除当前会话

1. 键入 `/delete` 并按回车。
2. 确认你要删除当前会话并退出 Codex。

预期结果：Codex 删除当前会话的对话记录并关闭交互式 TUI。删除是永久性的，同时也会移除派生的后代会话。

任务运行期间或处于旁路对话中时，`/delete` 不可用。

### 使用 `/permissions` 更新权限

1. 键入 `/permissions` 并按回车。
2. 选择符合你接受程度的审批预设，例如用于放手运行的 `Auto`，或用于审查编辑的 `Read Only`。当启用了命名权限配置（named permission profiles）时，选择器还会显示已配置的自定义配置及其描述。

预期结果：Codex 会宣布更新后的策略。在你再次更改之前，后续操作都会遵循更新后的审批模式。

### 使用 `/ide` 包含 IDE 上下文

1. 键入 `/ide`。
2. 如果想说明 Codex 应如何处理当前 IDE 中的选中内容或打开的文件，可添加可选的内联文本。

预期结果：Codex 会在下一条提示词中包含可用的 IDE 上下文。

### 使用 `/vim` 开关 Vim 模式

1. 键入 `/vim`。
2. 继续在输入框中编辑。

预期结果：Codex 为当前会话开关输入框的 Vim 模式。若要让 Vim 模式成为新会话的默认设置，请在 `config.toml` 中设置 `tui.vim_mode_default = true`。

### 使用 `/copy` 复制最新响应

1. 键入 `/copy` 并按回车。

预期结果：Codex 将最近一条已完成的 Codex 输出复制到你的剪贴板。

如果某一轮仍在运行，`/copy` 会使用最近完成的输出，而不是进行中的响应。在第一条 Codex 输出完成之前，以及回滚（rollback）之后的瞬间，该命令不可用。

你也可以在主 TUI 中直接按 <kbd>Ctrl</kbd>+<kbd>O</kbd> 复制最近完成的响应，无需打开斜杠命令菜单。

### 使用 `/raw` 开关原始回滚模式

1. 键入 `/raw`、`/raw on` 或 `/raw off`。

预期结果：Codex 开关原始回滚（raw scrollback）模式，使终端的选择和复制更直接。你也可以使用默认的 <kbd>Alt</kbd>+<kbd>R</kbd> 快捷键，或通过 `tui.raw_output_mode = true` 持久化默认设置。

### 使用 `/sandbox-add-read-dir` 授予沙箱读取权限

此命令仅在 Windows 上原生运行 CLI 时可用。

1. 键入 `/sandbox-add-read-dir C:\absolute\directory\path` 并按回车。
2. 确认该路径是一个已存在的绝对目录路径。

预期结果：Codex 刷新 Windows 沙箱策略，为之后在沙箱中运行的命令授予该目录的读取权限。

### 使用 `/status` 检查会话状态

1. 在任意对话中，键入 `/status`。
2. 查看输出中的活跃模型、审批策略、可写根目录以及当前 token 使用情况。当 TUI 以远程方式连接时，输出还会显示远程地址和服务器版本。

预期结果：Codex 打印一份摘要，确认它正运行在你预期的环境中。

### 使用 `/usage` 查看账户用量

1. 键入 `/usage` 打开用量菜单。
2. 选择是查看 token 活动，还是兑换一次可用的已获得限额重置。
3. 要直接打开 token 活动视图，键入 `/usage daily`、`/usage weekly` 或 `/usage cumulative`。

预期结果：Codex 打开用量操作菜单，或显示所选视图的账户 token 活动。如果会话没有 Codex 服务账户认证，Codex 会提示需要登录。

### 使用 `/debug-config` 检查配置层级

1. 键入 `/debug-config`。
2. 查看输出中的配置层级顺序（优先级最低的在前）、开关状态以及策略来源。

预期结果：Codex 打印层级诊断信息，以及诸如 `allowed_approval_policies`、`allowed_sandbox_modes`、`mcp_servers`、`rules`、`enforce_residency` 和 `experimental_network`（若已配置）等策略详情。

使用此输出来排查为什么实际生效的设置与 `config.toml` 不一致。

### 使用 `/statusline` 配置底栏条目

1. 键入 `/statusline`。
2. 使用选择器切换和排序条目，然后确认。

预期结果：底栏状态行立即更新，并持久化到 `config.toml` 中的 `tui.status_line`。

可用的状态栏条目包括：模型、模型+推理强度、上下文统计、限额、git 分支、token 计数器、会话 id、当前目录/项目根目录，以及 Codex 版本。

### 使用 `/title` 配置终端标题条目

1. 键入 `/title`。
2. 使用选择器切换和排序条目，然后确认。

预期结果：终端窗口或标签页标题立即更新，并持久化到 `config.toml` 中的 `tui.terminal_title`。

可用的标题条目包括：应用名、项目、加载动画（spinner）、状态、线程、git 分支、模型和任务进度。

### 使用 `/theme` 选择语法高亮主题

1. 键入 `/theme`。
2. 在选择器中预览主题，然后确认。

预期结果：Codex 更新语法高亮，并将选择持久化到 `config.toml` 中的 `tui.theme`。

### 使用 `/keymap` 重新映射 TUI 快捷键

使用 `/keymap` 来查看、更新并持久化 TUI 的键盘快捷键绑定。

1. 键入 `/keymap`。
2. 选择你想更改的快捷键上下文（context）和动作（action）。
3. 输入新的绑定，或移除现有绑定。

预期结果：Codex 更新活跃的键位映射，并将自定义绑定写入 `config.toml` 中的 `tui.keymap`。

键位绑定使用诸如 `ctrl-a`、`shift-enter`、`page-down` 之类的名称。特定上下文的绑定会覆盖 `tui.keymap.global`；空的绑定列表则会解绑该动作。

### 使用 `/ps` 检查后台终端

1. 键入 `/ps`。
2. 查看后台终端列表及其状态。

预期结果：Codex 显示每个后台终端的命令，外加最多三行最近的非空输出行，让你一眼就能了解进度。

后台终端在使用 `unified_exec` 时才会出现；否则列表可能为空。

### 使用 `/stop` 停止后台终端

1. 键入 `/stop`。
2. 如果 Codex 在停止列出的终端前询问，请确认。

预期结果：Codex 停止当前会话的所有后台终端。`/clean` 仍然可以作为 `/stop` 的别名使用。

### 使用 `/compact` 保持对话记录精简

1. 在一段较长的交流后，键入 `/compact`。
2. 当 Codex 提议总结到目前为止的对话时，进行确认。

预期结果：Codex 用一份简洁的总结替换掉之前的轮次，在保留关键细节的同时释放上下文空间。

### 使用 `/diff` 审查改动

1. 键入 `/diff` 查看 Git diff。
2. 在 CLI 内滚动浏览输出，审查编辑内容和新增文件。

预期结果：Codex 会显示你已暂存的改动、尚未暂存的改动，以及 Git 尚未开始跟踪的文件，方便你决定保留哪些内容。

### 使用 `/mention` 高亮文件

1. 键入 `/mention`，后跟一个路径，例如 `/mention src/lib/api.ts`。
2. 从弹窗中选择匹配的结果。

预期结果：Codex 将该文件加入对话，确保后续轮次会直接引用它。

### 使用 `/new` 开始新对话

1. 键入 `/new` 并按回车。

预期结果：Codex 在同一个 CLI 会话中开始一段全新对话，让你无需离开终端就能切换任务。

与 `/clear` 不同，`/new` 不会先清空当前终端视图。

### 使用 `/resume` 恢复已保存的对话

1. 键入 `/resume` 并按回车。
2. 从已保存会话选择器中挑选你想要的会话。

预期结果：Codex 重新加载所选对话的记录，让你从上次停下的地方继续，同时保持原始历史完整。

### 使用 `/fork` 分叉当前对话

1. 键入 `/fork` 并按回车。

预期结果：Codex 将当前对话克隆到一个拥有全新 ID 的新线程中，原始对话记录保持不变，这样你可以并行探索另一种方案。

如果你需要分叉的是某个已保存的会话而非当前会话，请在终端中运行 `codex fork` 打开会话选择器。

### 使用 `/side` 开启旁路对话

使用 `/side` 从当前对话开启一个临时分叉，而无需离开主任务。

1. 键入 `/side` 打开一个旁路对话。
2. 可选地添加内联文本，例如 `/side Check whether this plan has an obvious risk`。
3. 在这段聚焦的"绕道"结束后，返回父线程。

预期结果：Codex 打开一个旁路对话，其对话记录与父线程相互独立。当你处于旁路模式时，TUI 会继续显示父线程的状态，让你能看到主任务是否仍在运行。

在另一个旁路对话内部，以及在审查模式（review mode）期间，`/side` 不可用。

### 使用 `/init` 生成 `AGENTS.md`

1. 在你希望 Codex 查找持久化指令的目录中运行 `/init`。
2. 检查生成的 `AGENTS.md`，然后编辑它以匹配你仓库的约定。

预期结果：Codex 创建一个 `AGENTS.md` 脚手架，你可以对其加以完善并提交，供未来会话使用。

### 使用 `/review` 请求工作区审查

1. 键入 `/review`。
2. 如果想查看确切的文件改动，可以接着运行 `/diff`。

预期结果：Codex 总结它在你工作区中发现的问题，重点关注行为变化和缺失的测试。除非你在 `config.toml` 中设置了 `review_model`，否则它会使用当前会话的模型。

### 使用 `/mcp` 列出 MCP 工具

1. 键入 `/mcp`。
2. 查看列表以确认哪些 MCP 服务器和工具可用。

预期结果：你会看到本次会话中 Codex 可调用的已配置 Model Context Protocol（MCP）工具。

使用 `/mcp verbose` 可以包含详细的服务器诊断信息。如果传入 `verbose` 以外的任何参数，Codex 会显示该命令的用法说明。

### 使用 `/apps` 浏览应用

1. 键入 `/apps`。
2. 从列表中挑选一个应用。

预期结果：Codex 以 `$app-slug` 的形式将该应用的提及（mention）插入输入框，你可以立刻要求 Codex 使用它。

### 使用 `/plugins` 浏览插件

1. 键入 `/plugins`。
2. 选择一个市场（marketplace）标签页，然后挑选一个插件以查看其能力或可用操作。

预期结果：Codex 打开插件浏览器，你可以在其中查看已安装的插件、你的配置允许发现的插件，以及已安装插件的状态。在已安装的插件上按 <kbd>Space</kbd> 可切换其启用状态。

### 使用 `/hooks` 查看并管理生命周期钩子

1. 键入 `/hooks`。
2. 选择一个钩子事件以查看匹配的处理器（handlers）。
3. 按需信任、禁用或重新启用非托管钩子。

预期结果：Codex 打开钩子浏览器，你可以在其中查看已配置的生命周期钩子。托管钩子（managed hooks）会显示为托管状态，无法从用户钩子浏览器中禁用。

### 使用 `/agent` 切换 agent 线程

1. 键入 `/agent` 并按回车。
2. 从选择器中选择你想要的线程。

预期结果：Codex 切换活跃线程，让你可以查看或继续该 agent 的工作。

### 使用 `/feedback` 发送反馈

1. 键入 `/feedback` 并按回车。
2. 按照提示附上日志或诊断信息。

预期结果：Codex 收集所需的诊断信息，并将其提交给维护者。

### 使用 `/logout` 退出登录

1. 键入 `/logout` 并按回车。

预期结果：Codex 清除当前用户会话的本地凭据。

### 使用 `/quit` 或 `/exit` 退出 CLI

1. 键入 `/quit`（或 `/exit`）并按回车。

预期结果：Codex 立即退出。请先保存或提交所有重要工作。
