# Hermes Agent Docker 部署与授权（第 1~30 问）

## 本篇概述

这部分对话记录了用户从零开始用 Docker 部署 Nous Research 的 Hermes Agent 的完整过程：起初容器启动后卡在 Nous Portal 授权登录，用户希望完全跳过官方账号体系，改用自己的中转站 API（`https://api.zetaapi.ai`）。对话逐步解决了「Portal 授权是什么、怎么绕开」「Setup Wizard 每一步如何选择」「多项目多实例如何用独立数据目录隔离部署」以及「后台常驻（gateway 模式）容器为何反复重启、如何正确启动」等问题，最终以 gateway 服务成功常驻运行收尾。

---

## 一、Nous Portal 账号的作用与是否必需

首次启动 Hermes 容器时，日志显示服务本身已正常启动，但进入了首次登录向导（根据上下文推断，用户截图为容器启动日志）：

```text
main-hermes successfully started
dashboard successfully started
Not logged into Nous Portal. Starting login...
Waiting for approval...
```

这不是 Docker 报错，而是 Hermes 默认接入 Nous Portal 云平台，等待用户到 `https://portal.nousresearch.com/manage-subscription?user_code=xxxx-xxxx` 输入 user_code 完成授权。

Nous Portal 账号（类似 ChatGPT / Claude / Cursor 的账号体系）主要承担四个职能：

1. **身份认证（Authentication）**：识别是哪个用户在使用服务。
2. **订阅管理（Subscription）**：一个订阅可访问 300+ 模型（GPT、Claude、Gemini、DeepSeek、Llama 等）及工具能力（Web Search、Browser Automation、图像生成、TTS）。
3. **API 网关（Tool Gateway）**：搜索、浏览器操作、图像生成、多模型路由等能力走 Nous 云端网关，需要校验身份与额度。
4. **计费与额度（Usage / Billing）**：统计 token、调用次数、管理套餐。

若不登录，容器不会报错，只会一直停在 `Waiting for approval (polling every 1s)...`。

**两种部署模式对比**：

| 模式 | 优点 | 缺点 |
|------|------|------|
| Nous Portal（官方托管） | 开箱即用、300+ 模型、工具链齐全 | 数据经过 Nous 云端，企业代码有合规风险，依赖外部服务 |
| 纯私有部署 / BYOK（Bring Your Own Key） | 代码和数据留在自己服务器，安全可控 | 需自行配置模型 API、工具 |

企业内部场景（接飞书、GitLab、n8n）推荐后者。

## 二、跳过 Nous Portal，改用自有 API / 中转站

### 密钥读取位置

Hermes 从**进程环境变量**和数据目录下的 **`.env` 文件**（宿主机 `~/.hermes/.env`，容器内 `/opt/data/.env`）读取密钥。

### `.env` 配置写法

```env
# OpenAI 兼容中转站（绝大多数中转站属于此类）
OPENAI_API_KEY=你的key
OPENAI_BASE_URL=https://你的中转地址/v1

# Claude 官方
ANTHROPIC_API_KEY=sk-ant-xxxx

# DeepSeek（OpenAI 兼容）
OPENAI_API_KEY=sk-xxxx
OPENAI_BASE_URL=https://api.deepseek.com/v1
```

Docker Compose 中也可以直接用环境变量注入：

```yaml
environment:
  OPENAI_API_KEY: xxxx
  OPENAI_BASE_URL: https://你的中转地址/v1
```

### 若已卡在 Portal 登录界面

先 `Ctrl+C` 退出登录向导，再重新进入模型配置（`hermes model` / `hermes setup model` / `docker run ... setup model`），选择 OpenAI-compatible / Custom endpoint 而非 Nous Portal，填入 base_url、api_key、model。

## 三、理解 `docker run --rm` 的一次性安装方式

用户实际使用的官方安装命令：

```bash
docker run -it --rm \
  -v ~/.hermes:/opt/data \
  nousresearch/hermes-agent setup
```

两个关键点：

- **`--rm`**：容器退出后立即删除。因此 `docker ps` 里看不到 Hermes 容器，宿主机执行 `hermes` 会提示 `Command 'hermes' not found` —— 这是**正常现象**，`hermes` 命令只存在于容器内（容器里 `which hermes` 返回 `/usr/local/bin/hermes`），不会安装到宿主机。
- **`-v ~/.hermes:/opt/data`**：配置持久化到宿主机 `~/.hermes`（内含 `config.yaml`、`.env`、`sessions/`、`memories/`、`plans/`、`skills/`、`workspace/` 等），容器删除后配置仍在。

旧配置目录若想彻底重来（清掉 Portal token、auth.lock、旧 provider 配置等残留）：

```bash
rm -rf ~/.hermes
```

然后重新运行 setup。若只是换成自己的 API，则无需删除，直接改 `config.yaml` / `.env` 即可。

## 四、Setup Wizard 各步骤选择指南（BYOK 场景）

对话中逐屏走完了配置向导（各屏内容根据上下文推断自用户截图），针对「自有 API + 企业内部部署」目标的推荐选择如下：

| 向导页面 | 推荐选择 | 说明 |
|----------|----------|------|
| Setup 类型 | **Full setup**（bring your own keys） | 不选 Quick Setup (Nous Portal)——会强制 Portal 登录；Blank Slate 需全手动配置，首次不建议 |
| Terminal Backend | **Keep current (local)** | Docker 选项是 Docker-in-Docker，挂载麻烦且需授权 `/var/run/docker.sock`；SSH 仅用于操作另一台服务器；Modal/Daytona 是云开发环境 |
| Model Provider | **Custom endpoint (enter URL manually)** | 中转站是 OpenAI 兼容接口时不要选 OpenAI/Anthropic 官方项 |
| API 协议类型 | **1. Auto-detect [current]** | Hermes 会自动判断 Chat Completions / Responses / Anthropic Messages；Responses/Codex（`/v1/responses`）很多中转不支持；Anthropic Messages（`/v1/messages`）仅 Claude 原生接口用 |
| Context length | **留空直接回车（auto-detect）** | 除非确定中转站上下文上限且自动检测失败，否则不要手填 |
| Display name | 回车用默认，或起区分名如 `zeta-claude` | 仅用于区分多个 Provider，与调用/计费无关 |
| Messaging Platform | **Skip**（不勾选任何平台） | 飞书/企微/Telegram 都需要额外的 App ID、Secret、回调地址，先跑通核心，之后用 `hermes setup gateway` 再接 |
| Browser Tool | **Local Browser [recommended · free]** | 用 Headless Chromium，无桌面的纯 Linux 服务器也能跑，免费、数据不出服务器；Nous Subscription 需要 Portal，Browser Use/Browserbase/Firecrawl 需付费且数据过第三方 |
| Image Generation | **Skip — keep defaults / configure later** | FAL.ai / OpenAI gpt-image / OpenRouter 都需额外 Key；企业代码工作流用不到，以后可用 `hermes setup tools` 补配 |
| Auxiliary Models / Tool Providers | Skip | 后续再配 GitLab MCP、搜索等 |
| Enable tool calling（如出现） | Yes | 后面接 GitLab、n8n、MCP Server 都依赖 Tool Calling |

### Base URL 填写规则

中转站文档若写 `https://api.zetaapi.ai/v1/chat/completions`，Base URL 填 `https://api.zetaapi.ai/v1`；若文档只给 `https://api.zetaapi.ai`，就照填。Model 必须填中转站支持的**真实模型名**。

配置成功的标志：Hermes 能通过 `/v1/models` 拉取到中转站的模型列表（对话中成功列出了 `claude-sonnet-4-6`、`claude-opus-4-8` 等，根据上下文推断自截图）。模型选择建议：日常开发/代码分析选 Sonnet（快、便宜、代码能力强），复杂架构设计/深度审查再切 Opus（慢、贵）。

配置保存位置（容器内视角）：API Key 存到 `/opt/data/.env`（及 `auth.json`），配置存到 `/opt/data/config.yaml`。

## 五、Docker 多实例隔离部署方案

核心原则：**一个项目 = 一个 Hermes 容器 + 一个独立数据目录**。

### 目录结构

```bash
mkdir -p /opt/hermes/project-a
mkdir -p /opt/hermes/project-b
```

每个项目目录初始化后包含独立的 `.env`、`config.yaml`、`sessions/`、`memories/`、`workspace/`、`skills/`、`plans/`、`logs/`。

### 初始化某个项目

```bash
docker run -it --rm \
  --name hermes-project-a-setup \
  -v /opt/hermes/project-a:/opt/data \
  nousresearch/hermes-agent setup
```

### 常驻启动（注意：需指定 gateway，见「踩坑」一节）

```bash
docker run -d \
  --name hermes-project-a \
  --restart unless-stopped \
  -v /opt/hermes/project-a:/opt/data \
  nousresearch/hermes-agent hermes gateway
```

### Docker Compose 管理多实例

```yaml
services:
  hermes-project-a:
    image: nousresearch/hermes-agent
    container_name: hermes-project-a
    restart: unless-stopped
    volumes:
      - /opt/hermes/project-a:/opt/data

  hermes-project-b:
    image: nousresearch/hermes-agent
    container_name: hermes-project-b
    restart: unless-stopped
    volumes:
      - /opt/hermes/project-b:/opt/data
```

```bash
cd /opt/hermes
docker compose up -d
```

### 隔离重点

- **禁止**多个实例共用 `-v ~/.hermes:/opt/data`；必须每实例一个独立目录（`/opt/hermes/project-a:/opt/data`、`/opt/hermes/project-b:/opt/data`），使 sessions、memories、tools、workspace 互相隔离。
- 每个项目可用不同的 API Key、不同的飞书机器人、不同的 GitLab 仓库。
- 删除容器（`docker rm -f hermes-project-a`）不会丢数据，数据都在宿主机挂载目录里。
- 挂载目录必须前后一致：setup 时配置写在哪个目录，正式启动就挂哪个目录，否则等同于全新安装、看不到已有配置。

### 企业推荐架构

```text
Hermes-A (Gateway) ── 飞书群A ── GitLab项目A ── n8n流程A
Hermes-B (Gateway) ── 飞书群B ── GitLab项目B ── n8n流程B
临时聊天容器 ── docker run -it ... hermes
```

推荐生产环境：Ubuntu 24.04、Docker 28+、Docker Compose v2、4 核 CPU、8G 内存、100G 磁盘。

## 六、两种运行模式：交互聊天 vs gateway 常驻服务

| 模式 | 命令 | 用途 | 是否需要终端 |
|------|------|------|--------------|
| `hermes` | `docker run -it --rm ... hermes` | 手动聊天、调试 Agent，退出（Ctrl+D）容器即结束 | 需要 |
| `hermes gateway` | `docker run -d --restart unless-stopped ... hermes gateway` | 24 小时后台服务，监听消息平台 + cron 调度，服务器重启自动拉起 | 不需要 |

### 交互聊天

```bash
docker run -it --rm \
  --name hermes-project-a-chat \
  -v /opt/hermes/project-a:/opt/data \
  nousresearch/hermes-agent hermes
```

进入后输入 `hello`，模型正常回复即说明中转站、API Key、模型全部打通，完全脱离 Nous Portal。

### Gateway 常驻服务

```bash
docker run -d \
  --name hermes-project-a-gateway \
  --restart unless-stopped \
  -v /opt/hermes/project-a:/opt/data \
  nousresearch/hermes-agent \
  hermes gateway
```

Gateway 的本质：一直监听飞书/企微/Telegram/Slack/Webhook/n8n 等入口的消息，收到后调用大模型返回结果。启动成功的日志标志：

```text
service main-hermes successfully started
service dashboard successfully started
service legacy-services successfully started
Hermes Gateway Starting...
Messaging platforms + cron scheduler
```

回答用户关心的问题：**Gateway 常驻后，关闭 SSH 离开服务器它仍在运行**（`--restart unless-stopped` 保证服务器重启后自动恢复）。想操作时随时 `docker exec -it 容器名 bash` 进入，或 `docker logs -f 容器名` 看日志；想聊天时推荐另开一个临时聊天容器（挂同一数据目录，与后台 Gateway 共用配置/记忆/Session，互不影响），而不是钻进 Gateway 容器里再跑 `hermes`。

注意：在未接入任何消息平台之前，Gateway 只是空跑等待，没有实际意义；接入飞书/GitLab 前应先在容器内执行 `hermes setup gateway` 完成平台配置。

### 常用运维命令

```bash
docker ps                          # 查看容器（Up 为正常，Restarting/Exited 为异常）
docker logs -f hermes-project-a    # 跟踪日志
docker exec -it hermes-project-a bash   # 进入容器
docker restart hermes-project-a    # 重启
docker rm -f hermes-project-a      # 删除（数据不丢）
docker update --restart unless-stopped 容器名   # 修改重启策略
```

## 七、踩坑与解决

1. **容器启动后卡在 `Waiting for approval...`**
   原因：Hermes 默认走 Nous Portal 授权登录，没有账号/订阅就会一直轮询等待。
   解法：`Ctrl+C` 退出登录向导，改走 BYOK 模式——setup 时选 Full setup + Custom endpoint，配置自己的 API Key 与 Base URL，完全不登录 Portal。

2. **宿主机执行 `hermes` 提示 `Command 'hermes' not found`，`docker ps` 也没有 Hermes 容器**（根据上下文推断，截图显示宿主机 `root@n8n:~/.hermes#` 下只有 n8n 容器在跑）
   原因：安装命令带 `--rm`，容器退出即销毁；`hermes` 二进制只在容器内，不会装到宿主机 PATH。配置文件则通过 `-v ~/.hermes:/opt/data` 留在了宿主机。
   解法：这是预期行为。要么每次 `docker run -it --rm ... hermes` 临时启动，要么起一个常驻容器再 `docker exec` 进去用。

3. **担心 `~/.hermes` 旧目录残留 Portal 登录痕迹**
   曾触发过 Portal 登录流程的目录可能残留 Portal token、auth.lock、旧 provider 配置。最干净的做法是 `rm -rf ~/.hermes` 后重新 setup；若只是切换 API 则改配置即可，无需删除。

4. **`docker run -d`（默认命令）启动正式容器后一直 `Restarting`，`docker exec` 进不去**
   日志关键行：

   ```text
   Warning: Input is not a terminal (fd=0).
   Goodbye!
   ```

   原因：容器不是崩溃，而是镜像默认命令会进入 `hermes` 交互聊天；`-d` 后台模式下没有终端输入（stdin 不是 tty），聊天进程立即退出，配合 `--restart unless-stopped` 形成无限重启循环。
   解法：后台常驻必须显式指定 gateway 子命令——`docker run -d ... nousresearch/hermes-agent hermes gateway`；交互聊天则用 `docker run -it --rm ... hermes`。排查时可先 `docker rm -f` 掉重启容器，再用 `docker run -it --rm ... bash` 挂同一数据目录进去执行 `hermes doctor` / `hermes config`。

5. **Gateway 启动后日志出现两个 Warning**

   ```text
   No user allowlists configured.
   No messaging platforms enabled.
   ```

   原因：还没有配置允许访问的用户白名单，也没有接入任何消息平台（飞书/企微/Telegram 等）。
   解法：这不是错误，Gateway 已正常运行，只是在空等；后续通过 `hermes setup gateway` 接入飞书等平台后即有实际功能。

6. **setup 保存目录与正式容器挂载目录不一致导致「配置丢失」**
   对话中配置一度保存在 `/opt/hermes`（而非计划中的 `/opt/hermes/project-a`）。正式启动时若挂载了不同目录，Hermes 会表现得像全新安装。
   解法：启动正式容器时挂载与 setup 时**完全相同**的宿主机目录。

## 八、要点总结

- Hermes Agent 默认走 Nous Portal 账号体系（认证 + 订阅 + 工具网关 + 计费）；不登录不会报错，只会停在 `Waiting for approval...`。
- 企业/私有场景可完全跳过 Portal：setup 选 **Full setup（BYOK）**，Model Provider 选 **Custom endpoint**，配置自己的 `OPENAI_API_KEY` + `OPENAI_BASE_URL`（OpenAI 兼容中转）或 `ANTHROPIC_API_KEY`。
- 密钥读取自环境变量和数据目录 `.env`（容器内 `/opt/data/.env`）；配置持久化靠 `-v 宿主机目录:/opt/data`，容器可随删随建，数据不丢。
- 官方安装命令带 `--rm` 是一次性容器，`hermes` 命令只在容器内，宿主机找不到属正常。
- 中转站接口类型选 **Auto-detect**，Base URL 带 `/v1`（视文档而定），Model 填中转站真实模型名；Context length 留空自动检测。
- 向导中 Messaging、Image Generation、Auxiliary Models、Tool Providers 均可先 Skip，之后用 `hermes setup gateway` / `hermes setup tools` 补配；Browser Tool 选免费的 Local Browser（Headless Chromium）。
- 多实例隔离的核心：一个项目一个容器一个独立数据目录（`/opt/hermes/project-x:/opt/data`），严禁共用 `~/.hermes`；推荐用 docker compose 统一管理。
- 后台常驻必须用 `hermes gateway` 子命令 + `-d --restart unless-stopped`；直接 `-d` 跑默认命令会因无终端而无限重启。
- Gateway 常驻后可随时离开服务器；调试聊天时另开临时容器（`docker run -it --rm ... hermes`）挂同一数据目录，与 Gateway 共享配置和记忆。
- Gateway 在未接入飞书/GitLab/n8n 前只是空跑；下一阶段工作是 `hermes setup gateway` 接入消息平台与 GitLab MCP。
