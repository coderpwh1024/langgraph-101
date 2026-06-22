# PM 需求评估 → 工时评估 流水线（n8n）

事件驱动的双 Agent 流水线：产品经理提需求 → **需求评估 Agent** 打分 → 通过后 →
**工时评估 Agent** 拆解估时 → 回写 GitLab + 飞书通知。**不同项目走不同 Agent 配置**。

## 流程

```
PM 提需求(飞书表单/GitLab issue)
   │
 Webhook 接收 → 解析字段 → 读项目配置(按 project_id)
   │
 需求评估 Agent(项目专属 prompt+模型)
   │
 评估是否通过?
   ├─ 否 → 飞书通知-驳回(理由+待补充项) → 结束
   └─ 是 → 工时评估 Agent → GitLab 回写评论 → 飞书通知-工时卡片
```

## 「不同项目不同 Agent」怎么落地

采用**配置表驱动**：`读项目配置` 节点按 `project_id` 取出该项目专属的
评估标准、工时基准、模型、飞书群。**加新项目零改流程，只加一条配置**。

骨架里用 Code 节点内置了 `CONFIG` 映射（开箱即跑）。生产环境替换为读
**飞书多维表格** 或 **数据库**，让 PM 自己维护，字段如下：

| 字段 | 说明 | 示例 |
|------|------|------|
| `project_id` | GitLab 项目 ID，路由主键 | `1001` |
| `project_name` | 项目名，注入 prompt | `电商App` |
| `eval_system` | 需求评估 Agent 的 system prompt | 见 workflow.json |
| `effort_system` | 工时评估 Agent 的 system prompt | 见 workflow.json |
| `model` | 该项目用的模型 | `qwen-max` / `deepseek-chat` |
| `feishu_webhook` | 该项目飞书群机器人 webhook | `https://open.feishu.cn/...` |
| `gitlab_project` | 回写评论的目标项目 | `1001` |

> 若某些项目**流程差异巨大**（不只是 prompt 不同），把它单独做成一个
> **子工作流**，在 Switch 后用 `Execute Sub-workflow` 调用。

## Agent 结构化输出（IF 判断和回写的前提）

**需求评估 Agent：**
```json
{ "passed": true, "score": 82,
  "dimensions": {"清晰度": 85, "可行性": 80, "价值": 80},
  "missing": ["未说明目标用户量级"], "reason": "需补充验收标准" }
```

**工时评估 Agent：**
```json
{ "total_person_days": 12,
  "breakdown": [{"task": "前端", "days": 4}],
  "risks": ["依赖外部支付接口"], "suggested_sprint": "可排入下个迭代" }
```

## 导入与配置步骤

1. n8n → Workflows → 右上 `...` → **Import from File** → 选 `workflow.json`。
2. 替换 3 个凭据（节点上会标红）：
   - `REPLACE_CRED_LLM`：私有化 LLM。用 OpenAI 兼容凭据，**base_url 指向内网模型**
     （Qwen/DeepSeek 的 OpenAI 兼容端点）。
   - `REPLACE_CRED_GITLAB`：私有 GitLab 的 Access Token + 服务器地址。
   - 飞书 webhook：在 `读项目配置` 的 CONFIG 里把 `REPLACE_A/B` 换成真实群机器人地址。
3. **接入触发源**（二选一或都接）：
   - 飞书：开放平台「自建应用」事件订阅 → 回调指向 Webhook 的公网 HTTPS 地址。
   - GitLab：项目 Settings → Webhooks → 指向同一地址，勾 Issues events。
4. 先用飞书表单或 `curl` 打 Webhook 测一条，确认结构化输出和分支正常。

测试请求示例：
```bash
curl -X POST https://你的域名/webhook/pm-requirement \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"1001","title":"购物车支持优惠券叠加",
       "description":"用户结算时可叠加多张优惠券...","reporter":"张三"}'
```

## 私有化部署要点

- n8n Docker 部署在能同时通**内网 GitLab** 和**飞书公网出口**的网段。
- 飞书事件回调需**公网可达的 HTTPS**：配反代 + 证书，或用飞书长连接模式。
- 模型私有化：凭据 base_url 指向内网推理服务即可，无需改流程。

## ⚠️ 说明

- 这是**结构正确的骨架**，未在你的 n8n 实例实跑过。导入后请注意：
  - n8n 版本不同，节点 `typeVersion` 可能提示升级（按提示点一下即可）。
  - AI Agent 的子节点连线（模型 / 输出解析）导入后若未自动连上，**手动从
    模型节点和解析节点拖到 Agent 节点**的对应入口重连一次。
- 飞书审批兜底（项管人工确认工时）未画进骨架，需要的话在
  `飞书通知-工时卡片` 后加 `飞书审批 API` + `Wait` 节点。
