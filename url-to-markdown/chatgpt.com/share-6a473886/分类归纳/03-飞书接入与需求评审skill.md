# 飞书接入与需求评审 Skill 体系（第 61~82 问）

## 本篇概述

本篇整理自 ChatGPT 对话的第 61~82 问，主题是给 Hermes Agent 接入飞书机器人并构建企业级需求评审能力。内容覆盖飞书企业自建应用的配置与多机器人（多 AppID）隔离方案、WebSocket 与 Webhook 两种消息通道的选择、需求评审的提示词五层约束、符合 Hermes 规范的 Skill 文档格式（`--- name/description ---` frontmatter）与五大 Skill 全文、评测打分与改进方向、应用命名（最终选定 HipobuyAgent）、操作/使用手册规划，以及对照「一个项目一个 Agent」目标的差距分析。

---

## 一、飞书机器人接入与多机器人切换

### 1.1 接入前置条件与流程

接入需要 4 个要素：飞书开放平台账号、企业自建应用、App ID、App Secret（另有 Verification Token、Encrypt Key）。整体链路：

```text
飞书自建应用 → 开启机器人能力 → 配置事件订阅
→ Hermes Gateway 接收飞书消息 → 群里 @Hermes 提问
→ Hermes 读取 /workspace 代码 + GitLab API
```

自建应用需开启：机器人、事件订阅、消息接收。

### 1.2 多机器人（AppID）随时切换

飞书机器人配置本质就是几个环境变量，改 `.env` 后重启容器即可切换：

```env
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_VERIFICATION_TOKEN=xxx
FEISHU_ENCRYPT_KEY=xxx
```

```bash
nano /opt/hermes/project-a/.env   # 修改 APP_ID / APP_SECRET
docker restart hermes-project-a-gateway
```

### 1.3 推荐的多项目隔离架构

每个项目一套独立的 Hermes + GitLab + 飞书机器人 + 飞书群，每个项目一个 `.env`（`/opt/hermes/project-a/.env`、`/opt/hermes/project-b/.env`），分别启动容器：

```bash
docker run -d \
  --name hermes-project-a-gateway \
  -v /opt/hermes/project-a:/opt/data \
  -v /srv/gitlab:/workspace \
  nousresearch/hermes-agent hermes gateway
```

优点：完全隔离、随时更换机器人、权限/数据隔离、后续接 GitLab Webhook 不会串项目；A/B 两个 Agent 可以用不同的模型、Prompt、GitLab、飞书机器人，这是最推荐的企业部署方案。

### 1.4 启用 Feishu/Lark Gateway 的配置排查

用户截图（根据上下文推断：`.env` 已写入飞书密钥但 Gateway 日志报 `No messaging platforms enabled`），排查步骤：

1. 进入容器：`docker exec -it hermes-project-a-gateway bash`，执行 `hermes setup gateway`，在平台列表里选择 Feishu / Lark。
2. 确认配置是否加载：`cat /opt/data/.env`、`env | grep FEISHU`（有输出说明环境变量已注入；无输出说明 `.env` 写了但容器启动时没加载，需重启）。
3. 配置完退出容器后 `docker restart` 并看 `docker logs -f`，正常时不再出现 `No messaging platforms enabled`，而是出现 `Feishu connected / Gateway started / WebSocket connected / Listening for messages`。

另外的关键认知（第 64 问，根据截图推断用户在容器内又执行了 docker 命令）：提示符 `root@3cae117556e3:/#` 表示已在容器内；容器内执行 `docker ps` 报 `Cannot connect to the Docker daemon` 是正常的，因为没有挂载 Docker Socket，不是配置了 DIND（Docker in Docker）。

第 65 问：`hermes setup gateway` 出现 `Reconfigure Feishu / Lark? (y/N)` 并要求重新输入 App ID，说明进入的是交互式重新配置流程，不是自动读取 `.env`；若 `.env` 已写好，可直接 Ctrl+C 退出后重启容器。

### 1.5 WebSocket vs Webhook 模式选择

第 66 问（根据截图推断：setup 过程出现连接模式选择界面），建议选 **WebSocket (recommended — no public URL needed)**：

- WebSocket 优点：不需要公网 URL、不需要 HTTPS、不需要配置飞书事件订阅回调地址、穿透 NAT 没问题、部署最简单。
- Webhook 仅在已有域名 + Nginx + SSL + 公网 80/443，且后续要接企业微信/Slack/自定义 Webhook/多机器人统一入口时才建议。
- 当前企业内部方案（GitLab API + 本地代码 + Hermes + 飞书机器人）全部走 WebSocket 最稳。

若走 Webhook，飞书开放平台「事件订阅 → 请求地址」需填 Hermes Gateway 对外暴露的公网 HTTPS 地址，且容器启动时要加 `-p` 端口映射。

---

## 二、企业落地测试方式与分阶段推广

### 2.1 五个验证场景

个人飞书接通后（根据截图推断：群里 `@Hipobuy-1.0` 已可正常对话并读取代码），建议按 5 个场景测试：

1. 代码分析：`@Hipobuy-1.0 分析 aps-boot 的角色复制功能`
2. 需求评审：`【优化需求】订单管理增加批量退款功能，需求是否合理？`（期望输出合理性、影响模块、数据库影响、接口影响、风险点、工时评估）
3. 代码定位：`退款逻辑在哪里？`（开发最喜欢的功能）
4. GitLab 分析：`最近 aps-boot 谁改了订单模块？` / `最近 20 次提交做了什么？`
5. 架构分析：`分析 aps-boot 的订单模块架构`（Controller / Service / DAO / 第三方依赖 / 定时任务）

### 2.2 四阶段落地路线

| 阶段 | 定位 | 能力 |
| --- | --- | --- |
| 一 | AI 问答助手 | 代码定位、需求评审、GitLab 分析、工时评估（进研发/测试/产品群，基本零风险） |
| 二 | AI 产品经理 | 需求评审、技术方案输出、风险分析、测试用例 |
| 三 | AI 项目经理 | 接 GitLab Webhook，MR 创建/更新/合并时自动发送代码评审、风险分析、变更摘要 |
| 四 | 企业研发 Copilot | 飞书 + GitLab + n8n + Hermes 全链路：提需求 → 评审 → 方案 → 任务 → MR → AI 评审 → 用例 → 上线检查 |

推广时先给团队开放固定指令（分析 xxx 功能 / 需求是否合理 / 最近谁改了 xxx / 输出技术方案 / 评估工时），优先级依次为：需求评审 Prompt 固化 → 代码架构分析 Prompt 固化 → GitLab Webhook 自动评审 → n8n 自动流程闭环。

---

## 三、需求评审的提示词约束设计（五层）

不加约束时 Hermes 做需求评审的典型问题：过于乐观（动不动说"需求合理，可以实现"）、不了解公司业务规则、不会主动看代码（只根据需求文字回答）、输出格式不统一无法沉淀成流程。因此必须加 Prompt 约束，并做成 Skill 固化。

五层约束设计：

**第一层：角色约束**

```text
你是资深产品经理和技术架构师。
你必须：
1. 优先查看 /workspace 中的代码。
2. 优先查看 GitLab 最近提交记录。
3. 不允许凭空猜测。
4. 不确定时必须说明需要进一步确认。
5. 输出必须包含风险和工时。
```

**第二层：需求评审输出模板**（固定十余个小节：需求描述 / 是否合理 / 当前系统是否已支持 / 影响模块 / 数据库影响 / 接口影响 / 风险分析 / 边界场景 / 工时评估 / 建议方案 / 最终结论）

**第三层：强制代码检查（最重要）**

```text
如果用户提到需求：
1. 必须先搜索 /workspace。
2. 必须分析 Controller。
3. 必须分析 Service。
4. 必须分析数据库表。
5. 必须分析最近 Git 提交。
6. 没有查看代码前禁止直接下结论。
```

**第四层：风险规则**——高风险模块清单（订单、支付、库存、物流、退款、定时任务），涉及这些模块必须输出风险等级、回归范围、上线建议。

**第五层：工时规则**——统一口径：简单 0.5~2h、普通 1~2d、复杂 3~5d、高风险 1 周+。

预期效果示例（对"角色管理增加复制功能"的回答）：结论合理、`copyRolePermission` 已存在、剩余工作为前端按钮+页面、风险低、工时 2~3h——接近有经验的后端负责人水平。结论：**System Prompt 定义角色和输出规范，Skill 定义企业知识、评审流程、风险规则、工时规则**，双层方案缺一不可。

---

## 四、Skill 文档的标准格式与格式演进

### 4.1 格式认知的三次修正（第 71~74 问）

这段对话里 Skill 格式经历了三轮讨论：

1. **示例有没有必要**（第 71 问）：有必要但非全部——Skill 本质是 Few-shot Prompt，`pm-review/examples.md` 和 `code-review/examples.md` 最重要，示例会直接影响回答风格（如看到类似代码会主动检查 `@Transactional` 缺失、Redis 双写、循环查库）。
2. **examples.md 不是标准 Skill 格式**（第 72 问，用户指出）：Hermes 官方 Skill 核心只有 `my-skill/SKILL.md` 一个文件；`examples.md` / `company-rules.md` 这种拆分是 Claude Code 自定义 Commands、Cursor Rules、OpenHands Skills 等框架为方便维护 Prompt 的做法，非 Hermes 强制要求。Hermes 加载 Skill 时是「读取整个 SKILL.md → 拼接进 Prompt」最稳定，拆出去的文件是否自动加载取决于版本实现（用户用的是 v0.17.0），所以**第一版建议全部写进一个 SKILL.md**。
3. **必须带 YAML frontmatter**（第 74 问，用户再次指出）：之前给的偏「知识文档」，标准格式必须以 `---` YAML 头开始，正文按固定小节组织：

```markdown
---
name: pm-review
description: 企业需求评审专家
---

# Purpose
...
# Instructions
...
# Output Format
...
# Rules
...
# Examples
...
```

### 4.2 最终目录结构

```text
/opt/hermes/project-a/skills
├── project-knowledge/SKILL.md
├── pm-review/SKILL.md
├── code-review/SKILL.md
├── architecture/SKILL.md
└── gitlab-engineering-report/SKILL.md
```

不要拆 `examples.md` / `company-rules.md`。AI 还建议最终可合并成一个 `enterprise-pm/SKILL.md`（因为 AI 产品经理 + 技术负责人 + 架构师 + Code Reviewer 本质上是一个 Agent），以及后续增加 `tech-leader`、`project-manager` 两个 Skill。

### 4.3 部署方式

```bash
docker exec -it hermes-project-a-gateway bash
mkdir -p /opt/data/skills/{project-knowledge,pm-review,code-review,architecture,gitlab-engineering-report}
# 保存各 SKILL.md 后
exit
docker restart hermes-project-a-gateway
```

---

## 五、五大 Skill 文档核心内容（最终版，带 frontmatter）

### 5.1 pm-review（需求评审专家）

```markdown
---
name: pm-review
description: 企业需求评审专家，负责需求合理性分析、影响范围评估、工时评估和风险分析。
---

# Purpose
你是资深产品经理、技术负责人和 Java 架构师。
职责：需求评审、技术方案评审、工时评估、风险分析、上线评估。

# Instructions
收到需求后必须执行：
1. 理解需求。
2. 搜索 /workspace。
3. 查看 Controller / Service / Mapper / 数据库 / 前端页面。
4. 查看最近 Git 提交。
5. 判断当前系统是否已经支持。
禁止：未搜索代码直接回答；凭经验猜测；未确认影响范围直接估工时。

# Output Format
# 需求评审报告
## 一、需求描述  ## 二、需求合理性  ## 三、当前系统是否已支持
## 四、涉及模块  ## 五、涉及接口  ## 六、涉及数据库
## 七、边界场景  ## 八、风险分析  ## 九、工时评估
## 十、测试范围  ## 十一、上线建议  ## 十二、结论

# Rules
风险等级：
低：仅前端修改。 中：一个服务修改。
高：涉及订单、支付、提现、物流。
极高：涉及数据库结构变更、核心流程变更、定时任务。
工时规则：简单 0.5h~2h；普通 0.5d~1d；复杂 2d~5d；大型 1 周以上。

# Examples
用户：【优化需求】角色管理增加复制功能。
回答：当前系统：copyRolePermission 已实现。剩余工作：前端增加按钮。
风险：低。工时：2~3小时。
```

### 5.2 code-review（代码评审专家）

```markdown
---
name: code-review
description: 企业代码评审专家，负责代码质量、风险和上线评审。
---

# Purpose
你是资深 Java 架构师。负责 Code Review、风险分析、上线评审。

# Instructions
评审重点：重复代码、空指针、事务、并发、SQL性能、
Redis一致性、安全漏洞、MQ幂等性。

# Output Format
# 代码评审
## 功能说明  ## 风险等级  ## 问题列表
## 修改建议  ## 回归范围  ## 是否允许上线

# Examples
发现：@Transactional 缺失。风险：订单数据部分提交。
建议：增加事务控制。风险等级：高。
```

（中间版本的检查项更细：空指针用 Optional/判空、并发看 synchronized/锁/线程安全、数据库看慢 SQL/索引/N+1 查询、Redis 看双写一致性/缓存穿透、安全看 SQL 注入/XSS/权限校验、MQ 看幂等/重试/死信。）

### 5.3 architecture（架构分析专家）

```markdown
---
name: architecture
description: 企业架构分析专家，负责系统结构、调用链和技术债分析。
---

# Purpose
你是资深系统架构师。负责模块结构、调用链、数据流、技术债分析。

# Instructions
必须：查看项目结构、Controller、Service、数据库、第三方集成、定时任务。

# Output Format
# 架构分析
## 模块结构  ## 核心调用链  ## 数据流  ## 第三方依赖
## 风险模块  ## 技术债  ## 优化建议  ## Mermaid 架构图

# Examples
订单：Controller ↓ OrderService ↓ PaymentService ↓ ShipmentService ↓ ThirdPartyApi
```

### 5.4 gitlab-engineering-report（GitLab 工程分析专家）

```markdown
---
name: gitlab-engineering-report
description: GitLab 工程分析专家，负责分析提交、分支和研发热点。
---

# Purpose
你是研发效能分析专家。负责 Git 提交、Branch、Merge Request、热点模块分析。

# Instructions
必须结合 Git 提交记录、Branch、Merge Request、本地代码，输出研发分析报告。

# Output Format
# 工程分析报告
## 最近提交  ## 活跃开发人员  ## 热点模块  ## 风险模块
## 当前需求方向  ## 技术债  ## 建议

# Examples
最近开发：海关申报规则、物流附加费、确认信息管理。
热点模块：Logistics、Shipment、Order。风险：高。
```

### 5.5 project-knowledge（企业项目知识库）

```markdown
---
name: project-knowledge
description: Hipobuy 项目背景知识和技术栈说明。
---

# Purpose
提供项目背景知识。

# Instructions
项目代码位于 /workspace。
项目：aps-boot（Java 后端：订单/商品/支付/提现/物流/定时任务/第三方对接）、
admin-page（后台管理，Vue2 + ElementUI）、web-page（PC 商城，Vue2）、
h5-page（移动端商城，UniApp + Vue）。
技术栈：后端 SpringBoot / MyBatis / Mysql / Redis / XXL-Job；
前端 Vue2 / ElementUI / UniApp。

# Rules
所有分析必须：1. 优先查看代码。2. 优先查看最近提交。3. 优先查看历史实现。
禁止：凭空猜测；未搜索代码直接下结论。
```

公司背景：Hipobuy，跨境电商、海外仓、订单履约、支付、提现、物流、营销活动、第三方平台对接。

---

## 六、评测结果与改进方向（第 75 问）

用户发了两张评测截图（根据上下文推断：一张是"物流刷新 50 次限制"的需求评审输出，另一张是"微店 offerID 接口 7 月 1 日废弃"的分析输出），AI 综合评价 **8.5/10，可在中小团队（10~30 人研发）试运行**：

- 第一张（物流刷新 50 次）9/10：知道先找代码（`POST /logisticsTrace/refresh`）、有 PM 思维（控制第三方 API 成本、防运营误操作）、会问边界问题（50 次是总次数？是否可重置？是否只限邮政？）、工时评估合理（后端 2h、前端 1h）。漏了两点：Redis Key 失效策略、历史数据迁移（已刷 200 次的存量怎么算）。
- 第二张（微店 offerID）9.5/10：发现时间风险（7 月 1 日废弃接口，今天 6 月 29 日只剩 2 天）、分析业务后果（无法下单、采购全线瘫痪）、定位到具体代码（`Pattern.compile("itemID=...")` 正则不支持 offerID）。

分项评分：代码搜索 9.5、需求评审 9、工时评估 8.5、风险分析 8.5、输出规范 7、可解释性 7、技术负责人能力 8.5。

还缺的 5 个能力（可试运行，但不建议直接给老板演示）：

1. 输出格式不统一——必须把固定模板放进 Skill。
2. 没有输出代码引用（文件路径 + 行号），影响开发信任度。
3. 没有输出搜索过程（已检查 Controller / Service / Mapper / 前端 / 最近提交 的清单）。
4. 没有置信度（如"结论可信度 95%"或列出结论依赖了哪些已查/未查项）。
5. 不会主动说"我无法确定"——必须加规则：若代码未搜索完整，禁止给确定性结论。

进阶建议再加三个 Skill：`requirement-report`（统一输出模板）、`risk-analysis`（专门分析支付/订单/定时任务/MQ/Redis）、`change-impact-analysis`（改 A 影响 B/C/D，最适合老板演示）。

---

## 七、应用命名讨论（第 76~77 问）

切换到企业飞书时，不建议继续叫 `Hipobuy-1.0`（像测试机器人）。命名要有 AI 感、产品经理感、企业平台感、便于扩展。

AI 首推的候选：**HipoBrain（海马智脑）**、HipoPM（海马产品官）、HipoCopilot（海马智能助手）、HipoAgent（海马智能体）、HipoFlow（海马流程助手），以及 DevMate / DevBrain / OneAI / HipoOne 等方向。

用户提出 **HipobuyAgent**，AI 评 8.8/10：优点是与公司品牌 Hipobuy 强绑定、一看就是内部应用、方便扩展多 Agent（HipobuyAgent-PM / -Dev / -Arch / -Ops / -QA）；小缺点是偏技术、偏内部工具，对非技术同事没有 HipoBrain 高级。最终推荐命名体系：

```text
应用名：HipobuyAgent
机器人显示名称：Hipobuy AI
群昵称：Hipobuy-1.0
```

飞书应用描述模板：「HipobuyAgent 是欢宽内部 AI 智能协作平台，集成需求评审、代码分析、GitLab 工程洞察、架构分析和项目管理能力，为研发团队提供智能协作支持。」

---

## 八、操作手册与使用手册（第 78~79 问）

### 8.1 部署/运维文档（给自己/运维看）

建议至少 6+1 份：

```text
docs/
├── 01-环境部署.md        # OS/Docker 版本、/opt/hermes 与 /srv/gitlab 目录、容器清单、重启命令
├── 02-Hermes配置.md      # .env（GITLAB_*、FEISHU_*）、docker run 启动、日志、进容器
├── 03-GitLab接入.md      # Token 权限（read_api + read_repository 即可）、
│                         # update-all.sh 同步、crontab 每 10 分钟、gitlab-api.sh 测试
├── 04-飞书机器人接入.md   # 创建应用、机器人权限（收发消息/群信息/用户信息）、
│                         # 事件订阅（接收消息 v2、机器人被添加/移除）、WebSocket 无需公网
├── 05-Skill设计规范.md   # skills 目录 + 各 skill 的 name/description frontmatter
├── 06-日常运维手册.md     # docker ps/logs/restart、代码同步、df -h、tar 备份
└── 07-企业落地指南.md     # 需求评审流程、MR 流程、项目隔离、权限模型（产品/开发/测试/管理员）、
                          # 故障恢复（容器挂了/同步失败/飞书不回/Token 过期）
```

最终整合为《HipobuyAgent 企业 AI 研发协作平台部署与运维手册 v1.0》，每加一个能力（Webhook、MCP、多 Agent）只需迭代文档。

### 8.2 用户使用手册（比部署手册更重要）

《HipobuyAgent 用户使用手册 v1.0》（`08-用户使用手册.md`），八章结构：产品介绍、支持的能力（需求评审 / 需求卡片评审 / 代码分析 / 接口分析 / Git 提交分析 / 代码定位 / 工时评估）、推荐提问方式、支持的命令、需求评审规范、最佳实践（产品/开发/测试/技术负责人四种角色的用法）、常见问题、企业使用规范。

推荐提问模板：

```text
【需求】
背景：
现状：
目标：
边界：
请评估。
```

（Bug 用「现象/复现步骤/期望结果」，优化需求用「问题/目标/约束」。）

企业使用规范建议：产品的所有需求先经过 AI 评审；开发遇到陌生模块先问 AI；测试的所有需求先让 AI 输出风险点；所有 MR 必须经过 AI Review。另建议增加 `09-提示词手册.md`，沉淀需求评审/Bug 分析/SQL 分析/架构设计/MR 评审等常用 Prompt。

---

## 九、对照「一个项目一个 Agent」目标的差距分析（第 80~82 问）

用户发的截图（根据上下文推断：一张关于 n8n 多项目使用要求的图，n8n 本身不用管）核心表达：一个项目 = 一个独立 Agent，需具备项目背景、短期目标、长期目标、上下文记忆、项目隔离五要素。逐项对比当前方案：

| 能力 | 状态 |
| --- | --- |
| 项目隔离（独立 .env / memories / sessions / skills / 飞书机器人） | ✅ 100%，甚至超出要求 |
| 代码隔离 / GitLab 集成 / 飞书集成 | ✅ 100% |
| 项目背景 | ⚠️ 40%（Hermes 只能看代码，不知道"为什么做、业务目标、当前阶段"） |
| 短期目标 / 长期目标 | ❌ 0% |
| 项目上下文（规则约束） | ⚠️ 50%（只有聊天/代码上下文，没有"不能改数据库、必须兼容旧接口"这类规则上下文） |
| 企业知识沉淀 | ⚠️ 30%（只有 GitLab 代码，缺产品文档、架构文档、决策记录） |

而需求评审、GitLab 分析、飞书协同能力则已超出图片要求。补齐差距只需给每个项目加四个文件：

```text
/opt/hermes/project-a/
├── SOUL.md        # 项目背景（名称、目标、技术栈、核心原则）
├── ROADMAP.md     # 短期目标（当前阶段/本月目标）+ 长期目标（按季度）
├── CONTEXT.md     # 项目约束（禁止：升级 SpringBoot/MySQL、改订单核心表；必须：兼容旧接口、支持灰度）
└── DECISIONS.md   # 技术决策记录（如：物流轨迹统一走 17track；支付统一走 OnlyPay）
```

补完这四个文件后，Hermes + GitLab + 飞书 就基本等同于企业级多项目 AI Agent 平台。

---

## 踩坑与解决

1. **`.env` 写了飞书密钥但 Gateway 报 `No messaging platforms enabled`**：写入 `.env` 不等于启用了 Feishu/Lark 平台，需在容器内执行 `hermes setup gateway` 选择 Feishu / Lark；并用 `cat /opt/data/.env` + `env | grep FEISHU` 区分"文件写了但没加载"（需重启容器）和"根本没配置"两种情况。
2. **容器内执行 `docker ps` 报 `Cannot connect to the Docker daemon`**：这是正常现象——容器内没有挂载 Docker Socket，无法控制宿主机 Docker（相当于未配置的 Docker in Docker），先 `exit` 回宿主机再执行 docker 命令。
3. **`hermes setup gateway` 仍要求手动输入 App ID**：这是交互式重新配置流程（`Reconfigure Feishu / Lark?` 回答 y 后触发），不会自动读取 `.env`；若 `.env` 已配好可 Ctrl+C 退出直接重启容器。
4. **没有公网 HTTPS 无法配置事件订阅回调**：选 WebSocket 模式即可绕过，无需公网 URL、HTTPS、域名证书和回调地址配置；`docker ps` 里 Hermes 没有端口映射也不影响 WebSocket 模式。
5. **Skill 拆分成 examples.md / company-rules.md 可能不生效**：Hermes（v0.17.0）标准 Skill 只保证加载 `SKILL.md` 并拼接进 Prompt，附属 md 是否自动加载取决于版本实现——第一版应把规则、模板、Few-shot 示例全部写进一个 SKILL.md。
6. **Skill 写成纯 md 知识文档没有 frontmatter**（用户两次指出格式问题）：标准 Skill 必须以 `--- name: xxx / description: xxx ---` YAML 头开始，正文按 Purpose / Instructions / Output Format / Rules / Examples 组织。
7. **不加提示词约束时评审质量低**：模型会过于乐观、不看代码直接下结论、输出格式漂移；需通过角色约束 + 固定模板 + 强制代码检查 + 风险规则 + 工时规则五层约束解决。

---

## 要点总结

- 飞书机器人配置本质是 4 个环境变量（APP_ID / APP_SECRET / VERIFICATION_TOKEN / ENCRYPT_KEY），改 `.env` + `docker restart` 即可随时切换 AppID；多项目按「一个项目 = Hermes + GitLab + 飞书机器人 + 飞书群」完全隔离部署。
- 企业内部接入优先选 WebSocket 模式：无需公网 URL、HTTPS 和事件订阅回调地址，部署最简单；Webhook 仅在有域名/SSL 且需多平台统一入口时才考虑。
- 启用飞书通道要执行 `hermes setup gateway` 选择 Feishu/Lark，仅写 `.env` 不生效；用 `env | grep FEISHU` 判断环境变量是否真正注入容器。
- 需求评审必须加五层提示词约束：角色约束、固定输出模板、强制代码检查（未看代码禁止下结论）、高风险模块规则、统一工时口径；采用 System Prompt + Skill 双层方案。
- Hermes 标准 Skill 格式 = `skills/<name>/SKILL.md` 单文件 + `--- name/description ---` YAML frontmatter + Purpose / Instructions / Output Format / Rules / Examples 结构；示例（Few-shot）直接决定回答风格，必须内嵌。
- 第一版 Skill 包共五个：project-knowledge、pm-review、code-review、architecture、gitlab-engineering-report；放入 `/opt/data/skills/` 后重启容器生效。
- 评测综合 8.5/10 可试运行，改进方向：统一输出格式、附代码引用（文件+行号）、展示搜索过程、给出置信度、允许说"我无法确定"。
- 应用命名最终方案：应用名 HipobuyAgent、机器人显示名 Hipobuy AI、群昵称 Hipobuy-1.0，便于后续扩展 HipobuyAgent-PM/-Dev/-Arch 等多 Agent。
- 落地需配套两类文档：部署运维手册（环境/配置/GitLab/飞书/Skill 规范/运维/落地指南）和用户使用手册（能力清单、提问模板、企业使用规范），后者更重要。
- 对照「一个项目一个 Agent」目标，隔离和集成已 100% 达标，尚缺项目级长期记忆——补 SOUL.md（背景）、ROADMAP.md（短/长期目标）、CONTEXT.md（约束）、DECISIONS.md（决策）四个文件即完整。
