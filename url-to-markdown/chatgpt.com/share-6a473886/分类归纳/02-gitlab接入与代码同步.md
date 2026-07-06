# GitLab 接入与代码同步（本地代码 / API / MCP、定时同步、Webhook 与 MR 评审）

## 本篇概述

本篇整理自对话第 31~60 问：用户将 Hermes Agent 接入一套公网 GitLab（`https://tool-gitlab.therow-online.com`，与 Hermes 不在同一服务器），场景为「只读 Token + 10 个以内仓库 + 需求评审 / 代码影响分析」。核心内容包括三种接入方案（本地 clone、GitLab API、GitLab MCP）的对比与分工选型、只读 Token 的权限与泄露处置、本地仓库定时同步方案、GitLab API 辅助脚本，以及 GitLab Webhook + 大模型 MR 自动评审的架构设计。最终落地形态为：本地 clone 作代码分析主力、API 脚本提供元数据、Webhook 评审因权限问题暂缓，MCP 留作后期增强。

---

## 一、前置准备：Token 与连通性验证

### 1. 创建 Personal Access Token

GitLab：头像 → Preferences → Access Tokens。完整权限（如需创建 MR 再加 `write_repository`）：

```text
api
read_api
read_repository
read_user
read_registry（可选）
```

用户实际场景只需**只读**，最终推荐的最小权限集：

```text
read_api
read_repository
read_user
```

### 2. 在 Hermes 服务器验证网络与 Token

GitLab 与 Hermes 不在同一服务器没有问题，只要 GitLab 有公网地址、Hermes 能出公网、有 PAT 即可。验证命令：

```bash
# 网络连通 + 版本
curl -I https://tool-gitlab.therow-online.com
curl https://tool-gitlab.therow-online.com/api/v4/version

# Token 有效性（GitLab 官方推荐 PRIVATE-TOKEN 请求头）
curl --header "PRIVATE-TOKEN: glpat-xxxxxxxxxxxxxxxx" \
https://tool-gitlab.therow-online.com/api/v4/user

# 项目列表
curl --header "PRIVATE-TOKEN: glpat-xxxxxxxxxxxxxxxx" \
"https://tool-gitlab.therow-online.com/api/v4/projects?simple=true"
```

用户截图显示上述命令均返回正常 JSON（根据上下文推断：截图为 curl 测试成功的终端输出），确认网络通、Token 权限正常。

---

## 二、接入方案对比（本地代码 / API / MCP）与选型结论

### 1. 三种方案对比

| 方案 | 优点 | 缺点 | 适合场景 |
|---|---|---|---|
| 本地 clone 到服务器 | 分析效果最好：全局搜索、看目录、跨文件读取，速度快，不依赖频繁 API | 占磁盘；需定期 `git pull` | 代码分析、需求影响评估 |
| GitLab API | 不占磁盘；实时获取项目 / MR / Issue / Pipeline 元信息 | 深度读代码麻烦，大量文件要分页请求，上下文组织差 | 查项目列表、分支、提交、MR、Pipeline |
| GitLab MCP Server | 让 Agent 更标准化地调用 GitLab 工具（查 issue/MR/文件、创建评论等） | 部署和权限配置更复杂 | 后期更复杂的自动化增强 |

关键理由：GitLab API 只能拿单个文件内容，无法像本地代码那样做深度搜索；而 Hermes 本身擅长搜代码、分析项目、生成架构文档，所以本地代码是主力。

### 2. 选型结论（分工使用）

```text
本地代码仓库 = 主力（深度代码分析、需求影响评估）
GitLab API   = 稳定只读查询（项目/分支/提交/MR/Pipeline）
GitLab MCP   = 后续增强能力，现在不接
```

对于只读 Token 的用户，MCP 带来的提升不大反而增加部署复杂度，结论是「现在先接 API，MCP 以后作为增强项，不替代本地代码」。

### 3. 磁盘占用问题

会占磁盘但一般可控：10 个普通业务仓库通常几百 MB 到几 GB。检查与优化手段：

```bash
# 查看各仓库大小
du -sh /srv/gitlab/*

# 只分析主分支时用浅克隆省空间
git clone --depth 1 https://oauth2:TOKEN@tool-gitlab.therow-online.com/group/project.git
```

---

## 三、本地代码方式落地步骤

### 1. 目录规划

GitLab 仓库**不要放在 `/opt/hermes` 下**（那是 Hermes 的配置 / session / memory 数据目录），代码单独放 `/srv/gitlab`：

```text
/opt/hermes
├── project-a        # Hermes 数据
└── project-b

/srv/gitlab          # GitLab 代码镜像
├── admin-page
├── aps-boot
├── h5-page
├── web-page
└── update-all.sh
```

### 2. 克隆仓库（oauth2 + Token 方式）

```bash
mkdir -p /srv/gitlab
cd /srv/gitlab

git clone --depth 1 https://oauth2:你的新TOKEN@tool-gitlab.therow-online.com/group/project-a.git
git clone --depth 1 https://oauth2:你的新TOKEN@tool-gitlab.therow-online.com/group/project-b.git

# 检查
ls -la /srv/gitlab
du -sh /srv/gitlab/*
```

也可以用 SSH 方式：`git clone git@tool-gitlab.therow-online.com:group/project-a.git`。

### 3. 挂载给 Hermes（聊天模式测试）

```bash
docker run -it --rm \
  -v /opt/hermes/project-a:/opt/data \
  -v /srv/gitlab:/workspace \
  nousresearch/hermes-agent hermes
```

进入后验证：

```text
请列出 /workspace 下有哪些项目
请分析 /workspace/aps-boot 的项目结构
```

用户实测（根据上下文推断：三张截图分别为同步脚本输出、`ls /workspace` 结果、Hermes 对 aps-boot 的分析），Hermes 已能读取 pom.xml、识别 SpringBoot / JeeCG 模块与业务领域，挂载完全成功。

### 4. Gateway 后台服务同样挂载

```bash
docker rm -f hermes-project-a-gateway

docker run -d \
  --name hermes-project-a-gateway \
  --restart unless-stopped \
  -v /opt/hermes/project-a:/opt/data \
  -v /srv/gitlab:/workspace \
  nousresearch/hermes-agent hermes gateway

docker ps
docker logs -f hermes-project-a-gateway
```

---

## 四、本地仓库定时同步方案

GitLab 上每天不同时间段都有人提交合并，本地镜像靠**定时自动 `git pull`** 保持接近最新。

### 1. 统一更新脚本

```bash
nano /srv/gitlab/update-all.sh
```

```bash
#!/bin/bash
set -e

BASE_DIR="/srv/gitlab"

for repo in "$BASE_DIR"/*; do
  if [ -d "$repo/.git" ]; then
    echo "Updating: $repo"
    cd "$repo"
    git fetch --all --prune
    git pull --ff-only
    echo "Done: $repo"
    echo "----------------"
  fi
done
```

```bash
chmod +x /srv/gitlab/update-all.sh
# 手动测试
/srv/gitlab/update-all.sh
```

### 2. crontab 定时执行

```bash
crontab -e
```

```cron
*/10 * * * * /srv/gitlab/update-all.sh >> /var/log/gitlab-repo-sync.log 2>&1
```

也可改为每 5 分钟或丢弃日志（`>/dev/null 2>&1`）。查看日志：

```bash
tail -f /var/log/gitlab-repo-sync.log
```

### 3. 关键性质

- **Hermes 不需要重启**：容器挂载的是宿主机目录（`-v /srv/gitlab:/workspace`），宿主机代码更新后容器内立即可见最新代码。
- `--depth 1` 浅克隆后普通 `git pull` 也能更新主分支最新代码。
- `git pull --ff-only` 在仓库有本地修改时会失败——这是有意为之的保护，避免自动覆盖；只读分析仓库一般不会有本地修改。

---

## 五、GitLab API 只读脚本接入

### 1. Token 配置进 Hermes 的 .env

```bash
nano /opt/hermes/project-a/.env
```

```env
GITLAB_BASE_URL=https://tool-gitlab.therow-online.com
GITLAB_TOKEN=你的新Token
```

```bash
chmod 600 /opt/hermes/project-a/.env
```

### 2. gitlab-api.sh 辅助脚本

```bash
nano /srv/gitlab/gitlab-api.sh
```

```bash
#!/bin/bash
set -e

# 兼容容器内与宿主机两种运行环境（踩坑后的修正版）
if [ -f "/opt/data/.env" ]; then
  ENV_FILE="/opt/data/.env"
elif [ -f "/opt/hermes/project-a/.env" ]; then
  ENV_FILE="/opt/hermes/project-a/.env"
else
  ENV_FILE=""
fi
[ -n "$ENV_FILE" ] && source "$ENV_FILE"

BASE="${GITLAB_BASE_URL%/}"
TOKEN="$GITLAB_TOKEN"

if [ -z "$BASE" ] || [ -z "$TOKEN" ]; then
  echo "Missing GITLAB_BASE_URL or GITLAB_TOKEN"
  exit 1
fi

case "$1" in
  me)
    curl -s --header "PRIVATE-TOKEN: $TOKEN" "$BASE/api/v4/user" ;;
  projects)
    curl -s --header "PRIVATE-TOKEN: $TOKEN" "$BASE/api/v4/projects?simple=true&per_page=100" ;;
  branches)
    curl -s --header "PRIVATE-TOKEN: $TOKEN" "$BASE/api/v4/projects/$2/repository/branches" ;;
  mrs)
    curl -s --header "PRIVATE-TOKEN: $TOKEN" "$BASE/api/v4/projects/$2/merge_requests?state=opened" ;;
  commits)
    curl -s --header "PRIVATE-TOKEN: $TOKEN" "$BASE/api/v4/projects/$2/repository/commits?per_page=20" ;;
  *)
    echo "Usage: $0 me|projects|branches <id>|mrs <id>|commits <id>" ;;
esac
```

```bash
chmod +x /srv/gitlab/gitlab-api.sh
```

### 3. 在 Hermes 中使用

```text
请执行 /workspace/gitlab-api.sh projects，列出 GitLab 项目，并结合 /workspace 下的本地代码说明每个项目的作用。
请执行 /workspace/gitlab-api.sh commits 7
请执行 /workspace/gitlab-api.sh branches 7
请执行 /workspace/gitlab-api.sh mrs 7
```

实测结果（根据上下文推断：截图为 Hermes 执行脚本后的输出）：

- `projects`：成功返回 24 个项目列表（web-page=2、h5-page=3、admin-page=4、aps-boot=7 等）；
- `commits 7`：返回最近 20 次提交（提交人、时间、message），可看出开发热点（确认信息管理优化、海关申报规则修改、物流附加费优化、站内信批量任务修复）；
- `branches 7`：返回 49 个分支，Hermes 还能分析出废弃分支、独立产品线等；
- `mrs 7`：Open MR 为 0——不是失败，而是当前没有未关闭 MR（或团队流程非 MR 驱动）。

由此 Hermes 同时具备「本地代码上下文 + Git 历史上下文」，可做需求评审、风险评估、自动周报、影响分析等。

---

## 六、GitLab Webhook 与飞书机器人的职责划分

架构缺口的两问：「谁通知 Hermes 有新事情发生？谁跟人交互？」——分别对应 Webhook 和飞书机器人。

- **GitLab Webhook**：GitLab 主动通知服务器，事件驱动。可监听 Push、Merge Request（创建/合并/关闭）、Issue、Tag。价值：有人提交 / 合并代码时自动触发分析（修改模块、影响面、建议回归点），再推送飞书。
- **飞书机器人**：人与 Hermes 的交互入口（产品经理 @Hermes 分析需求、开发问最近提交、测试问高风险变更）。

两者关系：只有机器人则不会自动通知；只有 Webhook 则结果没地方看；两者结合才是完整闭环。推荐架构：

```text
                     ┌──────────────┐
                     │   飞书群     │
                     └──────┬───────┘
                            ▼
                     ┌──────────────┐
                     │    Hermes    │
                     └──────┬───────┘
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
     本地代码仓库       GitLab API       GitLab Webhook
     (/workspace)                         (事件推送)
```

建议实施顺序：GitLab API + 本地代码镜像（已完成）→ 飞书机器人 → GitLab Webhook → n8n 编排 → 产品/项目经理 Agent。

---

## 七、Webhook 接收服务实现（MR 创建 / 更新 / 合并）

第一版目标：接收 MR 事件 → 落盘事件 JSON → 同步本地代码，暂不接飞书。

### 1. Python 标准库版接收服务（要点）

`/opt/gitlab-webhook/server.py`，基于 `http.server`，核心逻辑：

- `GET /health` 返回 `ok`；`POST /gitlab/webhook` 校验 `X-Gitlab-Token` 请求头与 `GITLAB_WEBHOOK_SECRET` 是否一致，不一致返回 403；
- 每个事件按 `时间戳_项目_mr编号_动作.json` 落盘到 `/srv/gitlab/webhook-events/`；
- 仅处理 `X-Gitlab-Event: Merge Request Hook`：`action` 为 `open/reopen/update` 时执行 `git -C <repo> fetch origin <source> <target> --prune`；`action == merge` 或 `state == merged` 时执行 `/srv/gitlab/update-all.sh` 全量同步。

关键片段：

```python
SECRET = os.environ.get("GITLAB_WEBHOOK_SECRET", "")
PORT = int(os.environ.get("GITLAB_WEBHOOK_PORT", "9099"))

token = self.headers.get("X-Gitlab-Token", "")
if SECRET and token != SECRET:
    self.send_response(403)

if action in ["open", "reopen", "update"]:
    run_cmd(f"git -C {repo_path} fetch origin {source_branch} {target_branch} --prune")
if action == "merge" or state == "merged":
    run_cmd(UPDATE_SCRIPT)   # /srv/gitlab/update-all.sh
```

### 2. systemd 常驻服务

`/etc/systemd/system/gitlab-webhook.service`：

```ini
[Unit]
Description=GitLab Webhook Receiver
After=network.target

[Service]
Type=simple
Environment=GITLAB_WEBHOOK_SECRET=你自己设置一个随机密钥
Environment=GITLAB_WEBHOOK_PORT=9099
ExecStart=/usr/bin/python3 /opt/gitlab-webhook/server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable gitlab-webhook
systemctl start gitlab-webhook

curl http://127.0.0.1:9099/health     # 返回 ok 即成功
journalctl -u gitlab-webhook -f       # 看日志
```

### 3. GitLab 侧 Webhook 配置

```text
项目 → Settings → Webhooks
URL：http://你的服务器公网IP:9099/gitlab/webhook
Secret Token：与 GITLAB_WEBHOOK_SECRET 相同
勾选：Merge request events（暂不勾 Push）
保存后用 Test → Merge request events 验证
```

---

## 八、Webhook 能否直接调用 Hermes？——双链路架构结论

用户敏锐地指出第一版 Webhook「没有走 Hermes Agent」。尝试非交互调用：

```bash
docker run --rm ... nousresearch/hermes-agent hermes --prompt "分析这个 MR..."
```

实测失败（根据上下文推断：截图为 `hermes --help` 输出与报错 `hermes: error: argument command: invalid choice: '分析这个 MR...'`）。Hermes v0.17.0 只有 `hermes chat / gateway / webhook` 等子命令，**没有 `run/ask/prompt` 这类非交互 CLI**，因此「Webhook → docker run hermes "分析 MR"」这条路走不通。

最终确定的可行方案是**两条链路并行**：

```text
人工分析链路：飞书/人 → Hermes → /workspace 本地代码 + GitLab API → 回答
自动评审链路：GitLab Webhook → Python 服务 → 同步代码 → 调用 Claude API（zetaapi）→ 生成 MR 评审报告 → 保存 /srv/gitlab/reports → 后续推飞书
```

理由：Hermes 的最大价值是「人 ↔ Agent」交互，而非「Webhook → Agent」；强行接会不稳定、难调试、不好自动化。企业里常见做法也是 `GitLab Webhook → n8n/服务 → LLM → 飞书` 与 `飞书 → Agent → GitLab` 分开。若一定要走 Hermes，可用折中方案：Webhook 生成任务文件（如 `analysis-request.json`），由 Hermes gateway / 定时任务消费——但需要再研究 Hermes 的 cron / hooks / sessions 机制。

---

## 九、大模型 MR 自动评审（AI Code Review）方案

### 1. 评审链路与评审内容

```text
开发提交 MR → GitLab Webhook → Python 服务
  → 获取 MR Diff + 最近 Commit + 本地完整代码
  → Claude（zetaapi）
  → 输出评审报告 → 飞书通知
```

大模型评审维度：业务影响分析（改了哪些 Service、影响哪些流程）、风险等级、测试建议、代码质量问题（空指针、事务缺失、重复代码、慢 SQL）、安全问题（硬编码 Token、SQL 注入、权限校验缺失）。

对话中类比了 GitHub Copilot Code Review、CodeRabbit、Greptile，本质都是 `Webhook → Diff → LLM → Review`；而本方案更强的一点是除 Diff 外还有 `/srv/gitlab` 完整代码仓库 + 历史 Commit + GitLab API 可一起分析，能做出调用链级别的影响推断（如 PaymentService → RefundService → OrderService → ShipmentService）。

### 2. 实施教程（Flask 版，做到第七步为止）

```bash
mkdir -p /opt/ai-review /opt/ai-review/reports
apt update && apt install -y git curl jq python3 python3-pip
pip3 install flask requests gitpython
```

配置 `/opt/ai-review/config.py`：

```python
GITLAB_URL = "https://tool-gitlab.therow-online.com"
GITLAB_TOKEN = "你的token"
CLAUDE_BASE_URL = "https://api.zetaapi.ai/v1"
CLAUDE_API_KEY = "你的zetaapi key"
CLAUDE_MODEL = "claude-sonnet-4-6"
LOCAL_REPO_ROOT = "/srv/gitlab"
REPORT_DIR = "/opt/ai-review/reports"
```

第一版 Webhook 接收（`/opt/ai-review/app.py`，端口 9000）：

```python
from flask import Flask, request

app = Flask(__name__)

@app.route("/gitlab/webhook", methods=["POST"])
def webhook():
    data = request.json
    if data["object_kind"] != "merge_request":
        return "ignore"
    attrs = data["object_attributes"]
    print("MR:", attrs["iid"])
    print("Title:", attrs["title"])
    print("Action:", attrs["action"])
    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)
```

获取 MR Diff（`gitlab_api.py`）：

```python
import requests
import config

headers = {"PRIVATE-TOKEN": config.GITLAB_TOKEN}

def get_mr_changes(project_id, mr_iid):
    url = (f"{config.GITLAB_URL}/api/v4/projects/{project_id}"
           f"/merge_requests/{mr_iid}/changes")
    return requests.get(url, headers=headers).json()
```

第一版评审 Prompt：

```text
你是资深Java架构师。
根据：
1. MR Diff
2. 本地完整代码
输出：
1. 功能说明
2. 风险等级
3. 影响模块
4. 测试建议
5. 代码问题
```

### 3. 实施结局

用户表示「这个地方涉及 gitlab 权限，先放到后面吧」——Webhook + MR 自动评审暂缓。结论转为固化已完成能力（本地同步脚本 + Hermes 挂载 + API 只读脚本 + Gateway 长期运行），下一步先接**飞书机器人**（不需要 GitLab 写权限）。

---

## 十、踩坑与解决

| 问题 | 现象 | 原因 | 解决 |
|---|---|---|---|
| Token 在截图中泄露 | 用户截图里 `glpat-...` 完整可见（根据上下文推断） | 明文 Token 出现在 curl 命令中被截图 | 立即到 GitLab User Settings → Access Tokens → Revoke 撤销，重新生成只读 Token 再使用 |
| Hermes 安全拦截脚本执行 | 弹出 Dangerous Command 确认（根据上下文推断：命令含 `python3 -c`） | Hermes 对含 `python3 -c` 的命令判定为危险命令 | 选 `1`（Allow once）单次放行；测试阶段不要选 `3` 加入永久白名单 |
| API 调用"看似回答了"但未生效 | 日志出现 `Timeout - denying command` / `[BLOCKED: User denied this command]`（根据上下文推断） | 安全确认超时被自动拒绝，脚本根本没执行 | 先在宿主机手动验证脚本，再回 Hermes 执行并及时选 Allow once |
| 宿主机执行脚本报 Missing GITLAB_BASE_URL or GITLAB_TOKEN | 宿主机跑 `/srv/gitlab/gitlab-api.sh` 读不到环境变量（根据上下文推断） | 脚本写死 `ENV_FILE="/opt/data/.env"`，这是**容器内路径**，宿主机不存在 | 改为 if/elif 依次探测 `/opt/data/.env` 与 `/opt/hermes/project-a/.env`，兼容容器与宿主机两种运行环境 |
| Webhook 无法直接驱动 Hermes | `hermes --prompt "..."` 报 `invalid choice` | Hermes v0.17.0 CLI 无非交互 prompt 模式 | 改为双链路：Webhook → Python 服务 → Claude API 自动评审；Hermes 只负责人工交互 |
| `mrs 7` 返回 0 个 MR 被误以为失败 | Open MR: 0 | 项目当前没有未关闭 MR（或流程非 MR 驱动） | 属正常结果，无需处理 |
| Webhook 涉及 GitLab 管理权限 | 配置 Webhook 需要项目 Settings 权限 | 用户 GitLab 账号权限受限 | 暂缓 Webhook，先固化已有能力并优先接飞书机器人 |

另有两点预防性设计：`git pull --ff-only` 在有本地修改时主动失败以防覆盖；Webhook 服务用 Secret Token（`X-Gitlab-Token` 头）校验来源。

---

## 十一、要点总结

- GitLab 与 Agent 不必同机：公网地址 + PAT + `PRIVATE-TOKEN` 头即可打通，先用 `/api/v4/version`、`/api/v4/user`、`/api/v4/projects` 三连验证。
- 代码分析场景的选型结论：**本地 clone 是主力，GitLab API 做元数据辅助，MCP 留作后期增强**——API 只能逐文件取内容，深度搜索必须靠本地代码。
- 只读 Token（`read_api` + `read_repository` + `read_user`）即可支撑代码分析与需求评审；Token 一旦泄露（哪怕只是截图）立即撤销重发。
- 仓库统一放 `/srv/gitlab`（与 Hermes 数据目录 `/opt/hermes` 分离），用 `--depth 1` 浅克隆省磁盘，`oauth2:TOKEN@` 形式免交互克隆。
- 同步方案 = `update-all.sh`（遍历仓库 `git fetch --all --prune` + `git pull --ff-only`）+ crontab 每 5~10 分钟执行；容器挂载宿主机目录，代码更新后 Hermes 无需重启。
- `gitlab-api.sh` 以 `me / projects / branches / mrs / commits` 子命令封装只读 API，供 Hermes 在对话中调用；脚本要兼容容器内（`/opt/data/.env`）与宿主机两种 env 路径。
- Webhook 与飞书机器人职责互补：Webhook 解决「事件自动触发」，机器人解决「人机交互入口」，两者结合才是闭环。
- Hermes CLI 不支持非交互 prompt，因此 MR 自动评审走独立链路：Webhook → Python 服务 → 拉 Diff + 本地代码 → Claude API → 评审报告，Hermes 专注人工问答。
- AI Code Review 的通用范式是 `Webhook → Diff → LLM → Review`；叠加完整本地仓库与提交历史后可做调用链级影响分析，这是相对只看 Diff 的方案的核心增值。
- 实施要按权限现实排序：Webhook 需要项目管理权限时可先搁置，优先落地不需要写权限的飞书机器人。
