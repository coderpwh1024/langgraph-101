# Hermes Agent Docker 部署：权限控制与防死循环指南

> 适用场景：Linux 服务器上以 Docker 方式部署 [Hermes Agent](https://github.com/nousresearch/hermes-agent)（Nous Research）。
> 目标：① 限制 agent 的权限边界，防止其失控破坏宿主机；② 防止 agent 陷入死循环，避免资源与 API 费用失控。

---

## 一、权限控制

### 1. 容器本身加固（docker run / compose 层面）

Hermes 官方推荐挂载 `~/.hermes:/opt/data` 存放配置和密钥。在此基础上加固：

```yaml
# docker-compose.yml
services:
  hermes:
    image: nousresearch/hermes-agent:latest
    command: gateway run
    restart: unless-stopped
    volumes:
      - ~/.hermes:/opt/data          # 只挂这一个数据目录，不要挂宿主机敏感路径
    ports:
      - "127.0.0.1:8642:8642"        # 只绑本地回环，不要 0.0.0.0
    security_opt:
      - no-new-privileges:true       # 禁止提权
    cap_drop:
      - ALL                          # 丢弃全部 capabilities
    pids_limit: 512                  # 防 fork 炸弹
    deploy:
      resources:
        limits:
          memory: 4G                 # 用浏览器工具建议 >=2G，否则 1G 够
          cpus: "2.0"
```

几条关键红线：

- **绝不挂载 `/var/run/docker.sock`** —— 挂了等于把整台宿主机 root 权限给了 agent。
- **端口只绑 `127.0.0.1`**，对外访问走 Nginx/Caddy 反代 + TLS + 认证。如果只用
  Telegram/飞书等聊天平台对接，8642 端口可以完全不暴露。Hermes 文档明确警告：
  2026 年 6 月的 MCP 配置持久化攻击事件，入口就是暴露在公网的未认证 dashboard，
  扫描器直接驱动 agent 种了 SSH 后门。所以 dashboard（9119）和 API server
  如果要开，必须设置 `API_SERVER_KEY`。
- 不要用网上教程常见的 `chmod 777` 偷懒。正确做法是让数据目录属主与容器运行
  用户一致，例如 `--user $(id -u):$(id -g)` 配合 `chown -R` 数据目录。

### 2. 用 Hermes 自带的沙箱边界（更重要）

Hermes 支持多种终端后端（local、docker、ssh、modal 等）。**把 terminal backend
设为 `docker`**，agent 执行的所有 shell 命令、文件操作、代码执行都会进入一个
独立的、被 Hermes 强制加固的容器（全部 capabilities 丢弃、禁止提权、PID 限制，
默认 1 CPU / 5GB 内存 / 50GB 磁盘）。这样即使 agent 被提示注入（prompt injection），
破坏范围也被限制在沙箱内。

配套两点：

- **密钥最小化注入**：Hermes 的 `terminal.docker_forward_env` 是白名单机制，
  只有列进去的环境变量才会进入沙箱容器。保持这个列表为空或最小集合，
  API key 等敏感变量不要转发进去。
- **审批与黑名单**：Hermes 有内置命令黑名单（`rm -rf /`、fork 炸弹、写块设备等
  无条件拒绝，`--yolo` 也绕不过），危险命令审批超时默认拒绝（fail-closed）。
  注意：使用 docker 后端时危险命令审批会被跳过（因为容器本身就是边界），
  所以沙箱容器的资源限制和不挂敏感目录就更重要了。

---

## 二、防死循环

分三层：应用层限制 → 容器层兜底 → 监控告警。

### 1. Hermes 配置层（config.yaml，在 `~/.hermes` 下直接编辑）

```yaml
agent:
  max_turns: 90        # 每轮对话最大工具调用次数，可按需调低到 30~50
  tool_loop_guardrails:
    hard_stop_enabled: true
    hard_stop_after:
      exact_failure: 5           # 同一命令连续失败 5 次强制停止
      idempotent_no_progress: 5  # 幂等调用无进展 5 次强制停止
```

`max_turns` 是硬上限，`tool_loop_guardrails` 是官方专门针对「反复执行同一
失败命令」这类死循环的守护配置 —— 这两个是防死循环的主力。

### 2. 容器层兜底

- 上面 compose 里的 `cpus`、`memory`、`pids_limit` 就是兜底：即使 agent
  逻辑上陷入循环，也不会拖垮整台服务器。
- `restart: unless-stopped` 而不是 `always` —— 如果手动 stop 排查问题，
  容器不会自己爬起来继续循环。Docker 的重启策略自带指数退避，
  能避免崩溃-重启风暴。

### 3. 监控与成本熔断

- 死循环最直接的代价是 **API token 消耗**。在模型供应商侧
  （DashScope/OpenAI 等）设置每日花费上限或告警，这是最可靠的最终熔断。
- 日常观察：`docker stats hermes` 看 CPU 是否长期打满；
  `docker compose logs -f hermes` 看是否在重复输出相同的工具调用。
  可以加一个简单的 cron 巡检脚本，发现容器 CPU 持续 >90% 超过 10 分钟
  就告警或 `docker restart`。

---

## 三、优先级建议

如果只做三件事：

1. terminal backend 用 docker 沙箱 + 不挂 docker.sock + 端口只绑 127.0.0.1；
2. 开启 `tool_loop_guardrails` 并调低 `max_turns`；
3. 在模型供应商侧设消费上限。

这三条分别覆盖了「权限失控」「逻辑死循环」「经济损失」三个最大的风险面。

---

## 四、保护同机 GitLab 镜像仓库不被 agent 修改

场景：同一台 Linux 服务器上存放了 GitLab 的副本（镜像）仓库，由定时任务从真实
GitLab 拉取更新。要求：Hermes agent 不得修改这些镜像；即使用户的自然语言指令
触发了修改意图，也要能拦截并停止；定时同步不受影响。

设计原则：**自然语言拦截只是体验层，真正的边界必须是内核强制的**。被提示注入
（prompt injection）的 agent 会无视提示词里的「不许改」，但改不动一个只读
文件系统 —— 写入时直接得到 `EROFS: read-only file system` 错误并停止。

### 1. 第一层：文件系统边界（内核强制，真正的「停止」）

**用户与属主隔离** —— 镜像目录由专用同步用户拥有，其他用户只读：

```bash
sudo useradd -r -m gitsync
sudo mkdir -p /srv/git-mirrors
sudo chown -R gitsync:gitsync /srv/git-mirrors
sudo chmod -R 755 /srv/git-mirrors   # 其他用户可读、不可写
```

**沙箱容器不挂载或只读挂载** —— Hermes 的 docker 沙箱后端默认只有
/workspace，镜像目录对 agent 天然不可见，这是最干净的状态。如果 agent
需要读镜像代码，二选一：

- 只读挂载进沙箱：`-v /srv/git-mirrors:/mirrors:ro`（`:ro` 由内核强制，
  任何命令都写不进去）；
- 更推荐：完全不挂载，在宿主机用 git daemon 以只读协议对外提供镜像，
  agent 在沙箱内通过网络 clone：

```bash
# git:// 协议默认只读（receive-pack 未开启），协议层面就推不进去
sudo -u gitsync git daemon --export-all \
    --base-path=/srv/git-mirrors --listen=127.0.0.1 &
# agent 沙箱内： git clone git://host.docker.internal/xxx.git
```

主 Hermes 容器（gateway）同样不要在 compose 的 volumes 里挂镜像目录。

### 2. 第二层：agent 应用层拦截（友好提前停止）

这一层负责「用户自然语言触发修改时，agent 礼貌拒绝并说明原因」，
而不是等到写入报错：

- **常驻指令声明只读区**：在 Hermes 的系统提示 / 常驻上下文（如 bootstrap
  指令、skill 说明）中写明：`/srv/git-mirrors`（沙箱内为 `/mirrors`）是
  GitLab 只读镜像，收到任何修改请求时必须拒绝，并引导用户先 clone 到
  /workspace 再修改。
- **命令审批规则**：利用 Hermes 的危险命令审批 / 黑名单机制，对「命令中
  包含镜像路径且属于写操作（rm、mv、tee、git commit/push、重定向写入等）」
  的模式加拦截规则（具体配置键名随版本略有差异，见官方 Security 文档）。
- 注意：这一层可被复杂指令或注入绕过，**只作为体验优化，不能替代第一层**。

### 3. 正确的修改工作流：clone 出来改

用户确实需要基于镜像里的代码做修改时，标准流程是：

```
agent 从只读镜像 clone 到沙箱 /workspace → 在副本上修改 → 产出 patch/分支
```

改动只存在于 agent 自己的工作区，镜像永远不被触碰。如需回推到真实
GitLab，由人工审核 patch 后用人的凭证推送。

### 4. 定时同步任务的隔离

- cron 任务挂在 `gitsync` 用户下，与 agent 完全隔离：

```cron
# crontab -u gitsync -e（避开整点，见 sync 脚本日志排查）
*/17 * * * * /home/gitsync/bin/sync-mirrors.sh >> /var/log/git-mirror-sync.log 2>&1
```

```bash
#!/usr/bin/env bash
# sync-mirrors.sh：镜像用 git clone --mirror 创建的 bare 仓库，无工作区可污染
set -euo pipefail
for repo in /srv/git-mirrors/*.git; do
    git -C "$repo" remote update --prune
    git -C "$repo" fsck --no-dangling || echo "ALERT: $repo 完整性异常" >&2
done
```

- **拉取凭证用只读 deploy token**（GitLab 侧仅授 `read_repository` 权限），
  存放在 gitsync 家目录、权限 600。绝不放进 `~/.hermes/.env`，绝不加入
  `terminal.docker_forward_env` —— 即使凭证泄漏给 agent，也只能读不能推。
- 建议镜像使用 bare mirror（`git clone --mirror`）：没有工作区文件，
  agent 即使拿到读权限也没有可直接编辑的源码树。

### 5. 审计与自愈

- auditd 监控镜像目录的写行为，记录是哪个进程/用户在尝试写：

```bash
sudo auditctl -w /srv/git-mirrors -p wa -k git_mirror_write
# 查询：ausearch -k git_mirror_write
```

- 定时同步本身就是自愈机制：即使出现意外改动，下一次
  `remote update --prune` 会将引用恢复到真实 GitLab 的状态；
  配合上面 fsck 告警，可在发现漂移时人工介入。

### 6. 最终兜底：真实 GitLab 侧

- agent 运行环境（容器、沙箱、转发变量）中**永远不存在可写的 GitLab
  凭证**，从根源上杜绝「镜像没改成，直接推真仓库」。
- 真实 GitLab 上对关键分支启用 protected branches / push rules，
  作为最后一道防线。

小结：第一层（只读文件系统/属主隔离）保证「改不动」，第二层（审批规则 +
常驻指令）保证「尽早友好拦截」，同步凭证只读化保证「即使全被绕过也推不回
真仓库」。三层各自独立生效，任何一层被绕过都不会导致镜像或上游被污染。

---

## 五、触发即停：熔断机制与 ReAct 死循环抑制

前提：Hermes agent 在容器内，git 镜像在宿主机且**未挂载进容器** ——
容器边界本身已经隔离，agent 的任何访问尝试只会在容器内得到
`No such file or directory` / `Permission denied`，根本碰不到宿主机文件。
因此这一节要解决的不是「改坏」，而是：**一旦触发了对镜像的修改意图，
让 agent 立即停止，而不是对失败命令反复换姿势重试、陷入 ReAct 推理循环**。

### 1. Hermes 配置层：把失败熔断调紧（第一响应）

```yaml
agent:
  max_turns: 40                      # 调低总上限
  tool_loop_guardrails:
    hard_stop_enabled: true
    hard_stop_after:
      exact_failure: 2               # 同一命令第 2 次失败就硬停
      idempotent_no_progress: 3      # 幂等调用 3 次无进展就硬停
```

同时在常驻指令（系统提示 / bootstrap）中写明：

> 访问 /workspace 之外的路径若出现 Permission denied、Read-only、
> No such file or directory，属于预期的安全边界，**第一次失败就停止
> 并向用户报告原因，禁止更换命令或路径重试**。

两者配合：提示层让守规矩的模型「第一次就停」，guardrails 兜底
「最多 N 次必停」—— 后者是硬机制，不依赖模型是否听话。

### 2. 外部 watchdog：日志命中敏感模式，立即熔断（硬停止）

agent 内部机制之外，再加一个宿主机侧的独立看门狗：tail 容器日志，
命中「镜像路径 + 写操作」或「短时间内重复相同报错」就直接对容器动手。

```bash
#!/usr/bin/env bash
# hermes-watchdog.sh —— 建议做成 systemd 服务常驻
set -euo pipefail
MIRROR_PATTERN='(/srv/git-mirrors|/mirrors)'
WRITE_PATTERN='(rm |mv |tee |git push|git commit|chmod|chown|> )'

docker logs -f --tail 0 hermes 2>&1 | while read -r line; do
    if [[ "$line" =~ $MIRROR_PATTERN && "$line" =~ $WRITE_PATTERN ]]; then
        docker pause hermes                     # 秒级冻结，保留现场
        curl -s -X POST "$ALERT_WEBHOOK" \
            -H 'Content-Type: application/json' \
            -d "{\"text\": \"hermes 已熔断暂停，触发行: ${line//\"/}\"}"
        break
    fi
done
```

变体：不匹配路径、只统计「60 秒内同一错误串出现 ≥3 次」也触发 ——
这能兜住所有形式的失败重试循环，不局限于镜像场景。

### 3. 分级处置动作

| 动作 | 效果 | 适用 |
| --- | --- | --- |
| `docker pause hermes` | 秒级冻结全部进程，现场保留，可 `unpause` 恢复 | 第一时间止损 + 人工排查 |
| `docker restart hermes` | 打断进行中的 ReAct 循环（循环状态在内存里），数据卷不丢 | 确认是死循环后快速复位 |
| `docker stop hermes` | 彻底下线 | 需要离线审计时 |

关键点：正在推理的 ReAct 循环只存在于进程内存中，`restart` 即可打断；
配置、会话历史都在挂载卷 `~/.hermes` 里，不会丢失。

### 4. 兜底与检测

- compose 里的 `cpus` / `memory` / `pids_limit` 保证：即使循环没被
  及时发现，也只烧自己的配额，不影响宿主机和镜像同步任务。
- 模型供应商侧的日消费上限是成本维度的最终熔断。
- 宿主机 auditd 对镜像目录的写监控（见第四节）此时的角色变为
  **边界失效检测**：正常情况下永远不该有来自 hermes 的写事件，
  一旦出现，说明挂载或权限配置被人改过，需要立即人工介入。

小结：agent 内部 `tool_loop_guardrails` 负责「几次失败内自己停」，
外部 watchdog 负责「命中敏感行为秒级强停」，资源限额负责「停不下来
也烧不穿」。三层的触发方互相独立，不依赖模型配合。

---

## 六、业务范围限定：锁定在需求评审与工时评估

场景：这套 Hermes 部署是团队内部专用工具，只做两件事 —— **需求评审**和
**工时评估**，评审时以 git 镜像中的代码作为影响面分析依据。用户通过
自然语言交互；当用户输入与需求评审无关时，希望 agent 拒绝执行、停止
或引导回评审话题。

核心认知：**「拒绝跑题」的提示词是软约束，真正的保证来自能力剥夺**。
设计目标是：即使跑题指令（或注入）骗过了提示层，agent 也没有工具、
网络、凭证去执行跑题任务 —— 最多浪费几轮对话 token，随后被
`max_turns` / 熔断兜住。

### 1. 角色常驻指令：任务白名单 + 跑题处置规则（软约束，第一道）

在 Hermes 的系统提示 / bootstrap 常驻指令中，用白名单方式定义职责，
并明确跑题时的行为 ——「不调用工具、一句话拒绝、引导回评审」：

```text
<role>
你是团队内部的需求评审与工时评估助手，只处理以下任务：
1. 需求文档评审：完整性、歧义点、风险、验收标准；
2. 基于 /mirrors 镜像代码库的影响面与改动范围分析（只读）；
3. 工时与复杂度评估，给出拆分建议。
</role>

<scope_rules>
- 用户请求与上述任务无关时：不调用任何工具，直接回复
  「本助手仅支持需求评审与工时评估」，并询问是否有待评审的需求。
- 一次拒绝即止，不解释、不代做、不推荐替代方案。
- 禁止执行代码修改、部署、发送消息、联网检索等评审之外的操作。
- 镜像代码只读分析；需要运行验证时 clone 到 /workspace 进行。
</scope_rules>
```

要点：白名单（只做什么）比黑名单（不做什么）更抗绕过；
「不调用任何工具直接拒绝」让跑题请求连一次工具调用都不消耗。

### 2. 工具最小化：能力层硬边界（最重要）

需求评审 + 工时评估只需要：读镜像代码、读需求文档、（可选）在沙箱里
跑只读分析命令。据此裁剪 Hermes 的工具集：

- 在 config.yaml 中**禁用不需要的内置工具**：浏览器自动化、网页检索、
  消息发送、定时任务等（具体键名见官方 Configuration 文档）；
- 终端后端保持 docker 沙箱（见第一节），沙箱内无任何业务凭证；
- 不配置任何可写的 GitLab / 飞书 / 邮件凭证 —— agent「想」跑题
  也没有账号可用。

工具集就是 agent 的能力上限：没有 browser 工具就无法帮用户爬网页，
没有消息工具就无法代发通知，这一层不依赖模型是否听话。

### 3. 网络出口白名单：跑题任务的釜底抽薪

评审场景的合法出站流量只有两类：模型 API、宿主机的 git daemon。
用出口代理做域名白名单，其余全部拒绝：

```yaml
# compose 片段：hermes 走内部网络，出站只能经代理
services:
  hermes:
    networks: [hermes-net]
    environment:
      - HTTP_PROXY=http://egress-proxy:3128
      - HTTPS_PROXY=http://egress-proxy:3128
  egress-proxy:            # squid/tinyproxy，白名单仅放行模型 API 域名
    networks: [hermes-net, default]
networks:
  hermes-net:
    internal: true         # 该网络无直接外网出口
```

出口被锁死后，「帮我查一下 XX 新闻」「调用 XX 网站」这类跑题任务
在网络层面就不可能完成。

### 4. 入口收窄：用固定流程承载评审（减少自由发挥面）

- 把评审流程固化为 Hermes skill / 命令模板（如「需求评审」skill：
  输入需求文档 → 拉取相关代码 → 输出评审报告 + 工时表），
  引导用户走结构化入口，而不是完全自由聊天；
- 若通过飞书等平台接入，可在机器人回调侧加一层轻量前置过滤
  （关键词或小模型分类）：与评审无关的消息直接模板回复，
  根本不进入 agent，连推理 token 都不消耗（可选增强）。

### 5. 跑题熔断联动（复用第五节机制）

- 评审任务是有界任务，`max_turns` 可以压得更低（如 30）——
  正常评审用不完，跑题长任务必然撞上限被硬停；
- watchdog 的监控模式在「镜像路径 + 写操作」之外，追加跑题特征：
  `pip install`、`apt install`、`curl http`、长时间编译等命令模式，
  命中即 `docker pause` + 告警；
- 供应商侧日消费上限不变，作为成本熔断。

### 6. 责任分层小结

| 层 | 手段 | 是否硬边界 |
| --- | --- | --- |
| 提示层 | 角色白名单 + 跑题即拒绝话术 | 否（可被注入绕过） |
| 能力层 | 工具裁剪、无业务凭证、沙箱只读 | **是** |
| 网络层 | 出口代理域名白名单 | **是** |
| 入口层 | skill 模板化、前置分类过滤 | 部分 |
| 熔断层 | 低 max_turns、watchdog、消费上限 | **是** |

提示层决定「体验好不好」（第一时间礼貌拉回评审话题），
能力/网络层决定「跑题最坏能坏到哪」（答案：什么也做不了），
熔断层决定「浪费的上限」（几轮对话内必停）。

---

## 参考资料

- [Hermes Agent — Docker 官方指南](https://hermes-agent.nousresearch.com/docs/user-guide/docker)
- [Hermes Agent — Security 文档](https://hermes-agent.nousresearch.com/docs/user-guide/security)
- [Hermes Agent — Configuration 文档](https://hermes-agent.nousresearch.com/docs/user-guide/configuration)
- [Docker Hub: nousresearch/hermes-agent](https://hub.docker.com/r/nousresearch/hermes-agent)
- [GitHub: NousResearch/hermes-agent](https://github.com/nousresearch/hermes-agent)
