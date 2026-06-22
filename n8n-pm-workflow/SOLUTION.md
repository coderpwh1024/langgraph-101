# 基于 n8n 的「PM 需求评估 + 项目管理工时评估」AI 编排方案

> 一套从**部署**到**实现**的完整方案。事件驱动、私有化、多项目多 Agent。
> 适用：私有 GitLab + 飞书企业版 + 内网部署的大模型。

---

## 目录

1. [方案概述](#1-方案概述)
2. [整体架构](#2-整体架构)
3. [技术选型](#3-技术选型)
4. [前置准备](#4-前置准备)
5. [部署篇](#5-部署篇)
6. [集成篇](#6-集成篇)
7. [实现篇](#7-实现篇)
8. [飞书交互与审批](#8-飞书交互与审批)
9. [测试篇](#9-测试篇)
10. [运维篇](#10-运维篇)
11. [扩展路线](#11-扩展路线)

---

## 1. 方案概述

### 1.1 业务目标

- **产品经理**提交一条需求。
- **需求评估 Agent** 按该项目的标准自动打分，给出通过/驳回 + 理由 + 待补充项。
- 评估通过后，**工时评估 Agent**（承担项目管理角色）拆解任务、估算人天、识别风险。
- 结果自动**回写 GitLab issue** 并**推送飞书卡片**给 PM / 项管。
- **不同 GitLab 项目使用不同的 Agent 配置**（不同评估标准、工时基准、模型）。
- 关键工时由**项管在飞书审批确认**（AI 辅助，不全自动拍板）。

### 1.2 核心原则

| 原则 | 说明 |
|------|------|
| 事件驱动 | GitLab / 飞书事件触发，无需人工跑流程 |
| 配置表驱动 | 加项目只加配置，不改工作流 |
| 结构化输出 | Agent 输出 JSON，才能做分支判断和自动回写 |
| 人在环上 | AI 给建议，关键决策走飞书审批 |
| 全私有化 | 代码、数据、模型都在内网，符合合规 |

---

## 2. 整体架构

### 2.1 架构图

```
┌────────────┐      ┌────────────┐
│ 私有 GitLab │      │  飞书企业版 │
│ (多项目)    │      │ 应用/机器人 │
└─────┬──────┘      └─────┬──────┘
      │ Webhook           │ 事件订阅 / API
      │ (内网直连)         │ (需公网 HTTPS 回调)
      ▼                   ▼
┌──────────────────────────────────────────┐
│            Nginx (反代 + HTTPS)            │
└───────────────────┬──────────────────────┘
                    ▼
        ┌────────────────────────┐
        │          n8n           │  ← 主编排器
        │  Webhook → 路由 → Agent │
        └───────────┬────────────┘
        ┌───────────┼────────────┐
        ▼           ▼            ▼
  ┌─────────┐ ┌──────────┐ ┌──────────┐
  │ 配置源   │ │ 内网 LLM │ │ Postgres │
  │(多维表格)│ │(Qwen/DS) │ │(n8n 存储)│
  └─────────┘ └──────────┘ └──────────┘
```

### 2.2 数据流

```
1. PM 在飞书提交需求(自建表单/审批) 或 GitLab 新建 issue
2. 事件 → Nginx → n8n Webhook
3. n8n 解析出 project_id + 需求内容
4. 按 project_id 从配置源取该项目的 Agent 配置
5. 需求评估 Agent 调内网 LLM → 结构化评分
6. 分支判断：
   - 不通过 → 飞书推送驳回卡片 → 结束
   - 通过   → 工时评估 Agent → 估时
7. 回写 GitLab issue 评论 + 打标签
8. 飞书推送工时卡片 → 项管审批确认
9. 审批结果回写 GitLab(最终工时/排期)
```

---

## 3. 技术选型

| 层 | 选型 | 理由 |
|----|------|------|
| 编排器 | **n8n** | GitLab/飞书集成强、事件触发是核心、内置 AI Agent 节点、可私有化 |
| Agent | **n8n AI Agent 节点** | 无需额外平台，PM/项管场景的推理深度足够 |
| 配置源 | **飞书多维表格** | PM 自己能维护项目配置，无需改代码 |
| 模型 | **内网 Qwen / DeepSeek**（OpenAI 兼容） | 数据不出内网，n8n 仅改 base_url |
| 存储 | **PostgreSQL** | n8n 生产推荐，替代默认 SQLite |
| 反代 | **Nginx + Let's Encrypt** | 飞书回调要求 HTTPS |

> **为什么不用 Dify / LangGraph？** 本场景是「集成 + 事件触发 + 流程编排」为主、
> Agent 为辅。Dify 不擅长主动事件触发和多系统集成；LangGraph 灵活但需写代码、
> 维护成本高。n8n 一个平台即可覆盖，且 PM 可参与维护。

---

## 4. 前置准备

### 4.1 服务器

| 项 | 最低 | 推荐 |
|----|------|------|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 20 GB | 50 GB+ |
| 系统 | Linux + Docker 20.10+ | + Docker Compose v2 |

### 4.2 网络

- n8n 服务器需能访问：内网 GitLab、内网 LLM 服务、飞书公网域名（`open.feishu.cn`）。
- 需一个**公网可达的 HTTPS 域名**（飞书事件回调强制要求），如 `n8n.yourcompany.com`。
  - 内网方案：在 DMZ 放反代，或用飞书「长连接（WebSocket）」模式免公网。

### 4.3 账号与权限

- 飞书：管理员可创建「企业自建应用」。
- GitLab：各目标项目的 Maintainer，可配 Webhook、建 Access Token。
- 内网 LLM：OpenAI 兼容的 base_url + api_key。

---

## 5. 部署篇

### 5.1 目录结构

```
/opt/n8n/
├── docker-compose.yml
├── .env
└── nginx/
    └── n8n.conf
```

### 5.2 `.env`

```bash
# === n8n 基础 ===
N8N_HOST=n8n.yourcompany.com
N8N_PORT=5678
N8N_PROTOCOL=https
WEBHOOK_URL=https://n8n.yourcompany.com/
GENERIC_TIMEZONE=Asia/Shanghai
TZ=Asia/Shanghai

# === 登录鉴权 ===
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=请改成强密码

# === 加密密钥(务必固定，丢了凭据全废) ===
N8N_ENCRYPTION_KEY=请生成32位随机串

# === PostgreSQL ===
DB_TYPE=postgresdb
DB_POSTGRESDB_HOST=postgres
DB_POSTGRESDB_PORT=5432
DB_POSTGRESDB_DATABASE=n8n
DB_POSTGRESDB_USER=n8n
DB_POSTGRESDB_PASSWORD=请改成强密码

POSTGRES_DB=n8n
POSTGRES_USER=n8n
POSTGRES_PASSWORD=请改成强密码
```

> `N8N_ENCRYPTION_KEY` 生成：`openssl rand -hex 16`。**这个值一旦变更，所有已存凭据无法解密**，务必备份。

### 5.3 `docker-compose.yml`

```yaml
services:
  postgres:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  n8n:
    image: docker.n8n.io/n8nio/n8n:latest
    restart: always
    ports:
      - "127.0.0.1:5678:5678"   # 只对本机开放，外部走 Nginx
    environment:
      - N8N_HOST=${N8N_HOST}
      - N8N_PORT=${N8N_PORT}
      - N8N_PROTOCOL=${N8N_PROTOCOL}
      - WEBHOOK_URL=${WEBHOOK_URL}
      - GENERIC_TIMEZONE=${GENERIC_TIMEZONE}
      - TZ=${TZ}
      - N8N_BASIC_AUTH_ACTIVE=${N8N_BASIC_AUTH_ACTIVE}
      - N8N_BASIC_AUTH_USER=${N8N_BASIC_AUTH_USER}
      - N8N_BASIC_AUTH_PASSWORD=${N8N_BASIC_AUTH_PASSWORD}
      - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
      - DB_TYPE=${DB_TYPE}
      - DB_POSTGRESDB_HOST=${DB_POSTGRESDB_HOST}
      - DB_POSTGRESDB_PORT=${DB_POSTGRESDB_PORT}
      - DB_POSTGRESDB_DATABASE=${DB_POSTGRESDB_DATABASE}
      - DB_POSTGRESDB_USER=${DB_POSTGRESDB_USER}
      - DB_POSTGRESDB_PASSWORD=${DB_POSTGRESDB_PASSWORD}
    volumes:
      - n8n_data:/home/node/.n8n
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  postgres_data:
  n8n_data:
```

启动：

```bash
cd /opt/n8n
docker compose up -d
docker compose logs -f n8n   # 看启动日志
```

### 5.4 Nginx 反代 + HTTPS (`nginx/n8n.conf`)

```nginx
server {
    listen 80;
    server_name n8n.yourcompany.com;
    location / { return 301 https://$host$request_uri; }
}

server {
    listen 443 ssl;
    server_name n8n.yourcompany.com;

    ssl_certificate     /etc/letsencrypt/live/n8n.yourcompany.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/n8n.yourcompany.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5678;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;       # n8n 需要 WebSocket
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;   # Agent 调用可能较慢
    }
}
```

证书（公网域名场景）：

```bash
certbot certonly --nginx -d n8n.yourcompany.com
```

> 纯内网无公网域名：用内部 CA 自签证书，并在飞书侧改用**长连接模式**避免回调。

### 5.5 内网 LLM 接入（在 n8n UI 配凭据）

n8n → Credentials → New → **OpenAI** 类型：

| 字段 | 值 |
|------|-----|
| API Key | 内网 LLM 的 key（没有可填任意非空串） |
| Base URL | `http://内网IP:端口/v1`（Qwen/DeepSeek 的 OpenAI 兼容端点） |

> Qwen 兼容端点示例：`https://dashscope.aliyuncs.com/compatible-mode/v1`（公有云），
> 私有部署填内网地址。模型名在工作流里由配置表注入（如 `qwen-max`）。

---

## 6. 集成篇

### 6.1 GitLab Webhook（每个目标项目配一次）

1. 项目 → Settings → Webhooks。
2. URL：`https://n8n.yourcompany.com/webhook/pm-requirement`
3. Secret Token：填一个密钥（n8n 侧校验，防伪造）。
4. Trigger 勾选：**Issues events**（按需加 Comments / Merge request events）。
5. 私有 GitLab 内网直连 n8n，无需公网。

> 也可只用飞书做需求入口，GitLab 仅作为回写目标，二选一。

### 6.2 飞书自建应用

1. [飞书开放平台](https://open.feishu.cn) → 创建**企业自建应用**。
2. **权限**开通：
   - `im:message`（发消息 / 机器人）
   - `bitable:app`（读多维表格配置）
   - `approval`（审批，可选）
   - 表单/事件相关权限按需。
3. **事件订阅**：
   - 请求地址：`https://n8n.yourcompany.com/webhook/feishu-event`
   - 或启用**长连接模式**（无需公网，推荐内网环境）。
   - 订阅「审批实例状态变更」「表单提交」等所需事件。
4. **群机器人**：在目标群添加自定义机器人，拿到 webhook 地址，填入配置表。
5. **多维表格**：建一张「项目 Agent 配置表」（字段见 7.2），把 app_token / table_id 配到 n8n。

### 6.3 飞书 tenant_access_token

调飞书 API（发消息、读多维表格）需先换 token。在 n8n 里加一个 HTTP 节点或子工作流：

```
POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal
body: { "app_id": "xxx", "app_secret": "xxx" }
→ 返回 tenant_access_token（有效期 2h，可缓存）
```

> 简化方案：发通知用**群机器人 webhook**（无需 token）；只有读多维表格 / 审批才需 token。

---

## 7. 实现篇

### 7.1 工作流总览

导入 `workflow.json`（同目录），13 个节点：

```
Webhook 接收需求
  → 解析需求字段 (Set)
  → 读项目配置 (Code, 按 project_id)
  → 需求评估 Agent (AI Agent + 模型 + 输出解析)
  → 评估是否通过 (IF)
       ├─false→ 飞书通知-驳回 (HTTP)
       └─true → 工时评估 Agent (AI Agent + 模型 + 输出解析)
                 → GitLab 回写评论
                 → 飞书通知-工时卡片 (HTTP)
```

### 7.2 配置表设计（飞书多维表格）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `project_id` | 文本 | GitLab 项目 ID，路由主键 |
| `project_name` | 文本 | 项目名，注入 prompt |
| `eval_system` | 多行文本 | 需求评估 Agent 的 system prompt |
| `effort_system` | 多行文本 | 工时评估 Agent 的 system prompt |
| `model` | 单选 | `qwen-max` / `deepseek-chat` / … |
| `pass_threshold` | 数字 | 评估通过分数线（如 70） |
| `effort_baseline` | 文本 | 工时基准，如 `S=1,M=3,L=8` |
| `feishu_webhook` | 文本 | 该项目飞书群机器人地址 |
| `gitlab_project` | 文本 | 回写目标项目 |

> 骨架里 `读项目配置` 用 Code 节点内置映射开箱即跑。生产环境把 Code 换成
> **飞书多维表格「查询记录」节点**，按 `project_id` 过滤取该行配置。

### 7.3 需求评估 Agent

**System prompt（由配置注入 `eval_system`）：**

```
你是「{project_name}」的资深产品评审专家，按本项目标准评估需求。
评估维度：清晰度、可行性、业务价值、{项目专属维度}。
评分 >= {pass_threshold} 且无致命缺失项时 passed=true。
列出所有必须补充的缺失项。严格按给定 JSON 结构输出，不要多余文字。
```

**User 输入：**

```
需求标题：{{ title }}
需求描述：{{ description }}
```

**结构化输出 schema：**

```json
{
  "passed": true,
  "score": 82,
  "dimensions": {"清晰度": 85, "可行性": 80, "价值": 80},
  "missing": ["未说明目标用户量级", "缺少验收标准"],
  "reason": "需求价值明确，但验收标准缺失需补充"
}
```

### 7.4 工时评估 Agent

**System prompt（由配置注入 `effort_system`）：**

```
你是「{project_name}」的项目管理专家，已知需求评估已通过。
按本项目技术栈拆解任务并估算人天，参考工时基准：{effort_baseline}。
考虑前端/后端/测试/联调/风险缓冲。识别影响工期的风险。
严格按给定 JSON 结构输出。
```

**User 输入：**

```
需求标题：{{ title }}
需求描述：{{ description }}
评估结论：{{ 评估Agent的JSON输出 }}
```

**结构化输出 schema：**

```json
{
  "total_person_days": 12,
  "breakdown": [
    {"task": "前端页面", "days": 4},
    {"task": "后端接口", "days": 5},
    {"task": "联调测试", "days": 3}
  ],
  "risks": ["依赖外部支付接口，存在不确定性"],
  "suggested_sprint": "可排入下个迭代"
}
```

### 7.5 「不同项目不同 Agent」三种实现

| 方案 | 适用 | 做法 |
|------|------|------|
| **配置表驱动**（推荐） | 流程相同，仅 prompt/模型不同 | 一条主路径，prompt/model 用表达式从配置注入 |
| **Switch 多分支** | 项目少（≤5），差异中等 | Switch 按 project_id 分到多个 Agent 节点 |
| **子工作流** | 项目流程差异巨大 | 每项目一个子工作流，主流程 `Execute Sub-workflow` 调用 |

> 实战推荐**配置表 + 子工作流混用**：常规项目走配置表，特殊项目走子工作流。

### 7.6 GitLab 回写

`GitLab 回写评论` 节点（resource=issue, operation=createComment）：

```
🤖 自动评估完成
评估：通过（{{ score }} 分）
预估工时：{{ total_person_days }} 人天
排期建议：{{ suggested_sprint }}
风险：{{ risks }}
```

可再加一个 GitLab 节点给 issue **打标签**（如 `评估通过`、`待排期`）。

---

## 8. 飞书交互与审批

### 8.1 驳回卡片（红）

```json
{
  "msg_type": "interactive",
  "card": {
    "header": {"title": {"tag": "plain_text", "content": "❌ 需求评估未通过"}, "template": "red"},
    "elements": [
      {"tag": "div", "text": {"tag": "lark_md",
        "content": "**需求：**{{ title }}\n**理由：**{{ reason }}"}},
      {"tag": "div", "text": {"tag": "lark_md",
        "content": "**需补充：**{{ missing.join('、') }}"}}
    ]
  }
}
```

### 8.2 工时卡片（绿）+ 审批按钮

```json
{
  "msg_type": "interactive",
  "card": {
    "header": {"title": {"tag": "plain_text", "content": "✅ 需求已评估，待确认工时"}, "template": "green"},
    "elements": [
      {"tag": "div", "text": {"tag": "lark_md",
        "content": "**需求：**{{ title }}\n**工时：**{{ total_person_days }} 人天\n**排期：**{{ suggested_sprint }}"}},
      {"tag": "action", "actions": [
        {"tag": "button", "text": {"tag": "plain_text", "content": "确认"}, "type": "primary", "value": {"action": "approve"}},
        {"tag": "button", "text": {"tag": "plain_text", "content": "驳回"}, "type": "danger", "value": {"action": "reject"}}
      ]}
    ]
  }
}
```

### 8.3 审批闭环（可选）

1. 工时卡片后接**飞书审批 API**（创建审批实例）或卡片按钮回调。
2. n8n 加 **Wait** 节点挂起，等飞书「审批状态变更」事件回调到另一个 Webhook 唤醒。
3. 审批通过 → 回写 GitLab 最终工时；驳回 → 通知 PM 重新评估。

> 简化版可不接审批，工时卡片仅作通知，项管线下确认。

---

## 9. 测试篇

### 9.1 单元测试（手动触发 Webhook）

```bash
curl -X POST https://n8n.yourcompany.com/webhook/pm-requirement \
  -H 'Content-Type: application/json' \
  -d '{
    "project_id": "1001",
    "title": "购物车支持优惠券叠加",
    "description": "用户结算时可叠加多张优惠券，需校验互斥规则与封顶金额",
    "reporter": "张三"
  }'
```

### 9.2 验证清单

- [ ] Webhook 收到并解析出 4 个字段
- [ ] `读项目配置` 正确返回该项目配置（换 project_id=9999 应报错）
- [ ] 评估 Agent 返回合法 JSON，`passed` 字段存在
- [ ] IF 分支：低质量需求走驳回、高质量走工时
- [ ] 驳回卡片 / 工时卡片正确推送到对应飞书群
- [ ] GitLab issue 出现自动评论
- [ ] 换不同 project_id 时，prompt / 模型 / 飞书群随之切换

### 9.3 调试技巧

- n8n 每个节点点开看 **Input/Output JSON**，定位数据在哪一步断。
- AI Agent 输出非法 JSON 时，在 prompt 里强调「只输出 JSON」，或调低 temperature。
- 用 **Pin Data** 固定测试输入，反复跑不重打 Webhook。

---

## 10. 运维篇

### 10.1 监控告警

- 工作流加 **Error Trigger**：任一节点失败 → 推送飞书运维群。
- n8n Executions 页看历史执行、失败原因。

### 10.2 日志与数据备份

```bash
# 备份 n8n 数据(凭据、工作流) + Postgres
docker compose exec postgres pg_dump -U n8n n8n > /backup/n8n_$(date +%F).sql
tar czf /backup/n8n_data_$(date +%F).tar.gz /var/lib/docker/volumes/n8n_n8n_data
```

> **必须单独备份 `N8N_ENCRYPTION_KEY`**，否则恢复后凭据无法解密。

### 10.3 升级

```bash
cd /opt/n8n
docker compose pull
docker compose up -d
```

### 10.4 安全加固

| 项 | 措施 |
|----|------|
| 访问 | Basic Auth + 仅 Nginx 暴露 443，n8n 端口绑 127.0.0.1 |
| Webhook 防伪 | 校验 GitLab Secret Token / 飞书签名 |
| 凭据 | 全部走 n8n Credentials，**禁止硬编码 key 到节点** |
| 模型 | base_url 走内网，数据不出企业网络 |
| 最小权限 | 飞书应用、GitLab Token 只开必需权限 |
| 审计 | 保留 Executions 历史，关键操作回写 GitLab 留痕 |

---

## 11. 扩展路线

| 阶段 | 能力 |
|------|------|
| MVP | 需求评估 + 工时评估 + 飞书/GitLab 回写（本方案） |
| V2 | 飞书审批闭环、需求自动建 GitLab issue、自动分配负责人 |
| V3 | 接知识库 RAG（历史需求 / 项目规范），评估更精准 |
| V4 | 多 Agent 协作（评估→工时→排期→风险→里程碑），引入子工作流编排 |
| V5 | 逻辑复杂到瓶颈时，把核心 Agent 迁到 LangGraph，n8n 仅做集成层调 API |

---

## 附：文件清单

| 文件 | 说明 |
|------|------|
| `SOLUTION.md` | 本文档：完整方案 |
| `workflow.json` | 可导入 n8n 的工作流骨架 |
| `README.md` | 快速上手与导入说明 |

> ⚠️ `workflow.json` 为结构正确的骨架，未在真实 n8n 实例实跑。导入后需替换凭据、
> 接入触发源，并检查 AI Agent 子节点连线是否自动连上（n8n 导入 AI 节点常见小坑）。
