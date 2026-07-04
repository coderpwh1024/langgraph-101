# deep_agents 检测薄弱点整理（含标准答案）

> 来源：2026-07-04 费曼学习法检测（part08 长期记忆 + part09 final agent）。
> 首考 5.5/10，补考过关。本文只收录**当时答错或答虚的题**，每题给出：
> 原题 → 你当时的回答（错在哪）→ 标准答案。建议先遮住答案自测一遍再对比。

---

## 一、checkpointer vs store 的定位（原 A1，✗）

**原题**：agent 同时传了 `checkpointer=MemorySaver()` 和 `store=InMemoryStore()`，
这两个东西分别在存什么？为什么换一个 `thread_id` 之后 agent 就"失忆"，而 store 里的东西还在？

**你当时的回答**：checkpointer 是"临时存储，切换线程或程序挂掉数据就掉了"。

**错在哪**：把「按线程隔离」误解成了「临时/易失」，还把 MemorySaver
这个具体实现的属性（存内存、挂掉就丢）安到了 checkpointer 这个概念头上。

**标准答案**：

- **checkpointer = 线程内的记忆（按 thread_id 分抽屉）**。
  它的本职就是把对话状态**持久化**下来，按 thread_id 隔离。
  切到新 thread 看不到旧对话，不是数据丢了，而是抽屉换了——
  拿着旧 thread_id 再 invoke，对话能接着聊（HITL 的 resume 靠的就是这个）。
- **store = 跨线程的记忆（全局货架）**。不随 thread 走，
  按 namespace 组织，任何线程都能读到。
- "程序挂掉就丢"只是 **MemorySaver / InMemoryStore 这两个内存实现**的属性，
  换成 PostgresSaver / PostgresStore 就不丢了。概念与实现要分开。

一句话总结：**checkpointer 管"这一场对话"，store 管"这个用户/系统的长期知识"。**

---

## 二、三种记忆类型 + namespace 隔离（原 A3，✗）

**原题**：semantic / episodic / procedural 三种记忆各是什么？
如果三个路由用同一个 namespace 会发生什么？

**你当时的回答**：semantic 对了；episodic 说成"临时会话"；
procedural 说成"用户的长期记忆"；namespace 追问没答。

**标准答案**：

| 类型 | 定义 | 例子 |
|---|---|---|
| semantic | 事实与知识 | 用户偏好、项目信息 |
| episodic | **被持久化的"过往经历"**（不是临时的！） | 某次会话摘要、"五一去杭州旅游"、上次研究了什么 |
| procedural | **做事的规则和方法**（SOP / 肌肉记忆） | "写报告必须带行内引用"、Java 代码规范 |

**namespace 追问的答案**：namespace 元组本质上是 store 里的"文件夹路径"。
如果三类记忆用同一个 namespace，就全落进**同一个桶**，
同名文件互相覆盖，分类隔离名存实亡。

> 补考时你用"五一杭州游"（episodic）和"Java 代码规范"（procedural）
> 造例已经修正了这个混淆，此条算已过关，留档备忘。

---

## 三、路径前缀 → backend 路由（原 B1b、B4、补考第 1 题，✗✗✗ 连错三次）

**这是整个检测里唯一连错三次的知识点，也是当前唯一的 ⚠️ 残留弱点。**

**原题（补考版）**：在 part07 的 scoped_backend 配置下
（routes 只有 `/memories/user/` 和 `/memories/shared/` 两条，default 是 StateBackend），
`/memories/user/notes.md`、`/skills/blog/SKILL.md`、`/tmp/scratch.md`
三个文件各自归谁管、活多久？

**你当时的错法（三次都一样）**：看文件"身份"下结论——
"这是 skill 文件，所以归 skill 管"。backend 根本不知道什么叫 skill。

**标准答案**：

- `/memories/user/notes.md` → 匹配 `/memories/user/` 路由 → **StoreBackend**，
  namespace 是 `("user", <user_id>, "filesystem")`，跨线程存活、仅该 user 可见。
- `/skills/blog/SKILL.md` → **两条 route 都不匹配** → 落 default 的 **StateBackend**，
  和 `/tmp/scratch.md` 命运完全一样：换 thread 就没了，根本等不到"重启"。
- `/tmp/scratch.md` → 不匹配任何 route → **StateBackend**，寿命 = 这个 thread。

**必须刻下来的唯一规则**：

> 文件的命运只由**路径前缀匹配到哪个 backend** 决定，
> 和文件"是什么"（skill、报告、笔记）**毫无关系**。
> 判断时先扫一遍 routes，一条条比前缀，都不中就走 default。

**焊死它的实操练习（未做）**：跑一遍 part09 → 开新 thread、**不传 files** →
让 agent"把刚才的报告改写成 Twitter thread" → 观察：
`/memories/research_notes.md` 读得到（store），
`/final_report.md` 和所有 SKILL.md 读不到（state）→ 对照路由规则解释一遍输出。

---

## 四、skills 的渐进式披露（原 B2 + 补考第 2 题，✗ → 半对）

**原题**：`memory=["/AGENTS.md"]` 和 `skills=["/skills/"]` 的加载时机有什么区别？
为什么 deep agents 不把所有 SKILL.md 直接拼进 system prompt？

**你当时的回答**：只答了"把 skill 的目录拼进 system prompt"（机制），
没答加载时机的差别，也没答"为什么不拼全文"。

**标准答案**：

- `memory=["/AGENTS.md"]`：**每次运行都全文加载**进上下文，常驻指令。
- `skills=["/skills/"]`：**渐进式披露（progressive disclosure）**——
  启动时只把每个 skill 的 frontmatter（name + description）列进提示词，
  相当于一份"技能目录"；模型判断"这次要写 LinkedIn 帖子"之后，
  才主动 `read_file` 把 SKILL.md 全文读进来。
- **为什么不拼全文**：skill 会越加越多，全文常驻会吃光上下文窗口、
  用大量无关指令稀释注意力；目录只占几行，按需加载让 skill 数量可横向扩展。
- description 的作用不是"指挥"，是**检索线索**——模型靠它决定要不要打开这个技能，
  所以 description 写得好坏直接影响命中率。（Claude Code 的 Skill 机制是同一套思想。）

**要能脱口而出的一句话**：**"目录常驻、正文按需，换取 skill 数量可以无限扩展。"**

---

## 五、文件名对不上时的静默降级（原 B3，△）

**原题**：`memory=["/AGENTS.md"]` 但上传的文件叫 `/AGENT.md`（少个 S），会发生什么？

**你当时的回答**："不会报错" ✓，但没说后果。

**标准答案**：agent 去加载 `/AGENTS.md` 找不到 → **静默跳过，不报错**。
结果是 agent 在**没有那套"规划→研究→反思→写报告"工作流约束**的裸状态下跑，
只因 skills 还在、任务简单，输出看起来没毛病。
这类**静默降级比报错危险得多**——你根本不知道指令没生效。

> 这不是假设题：part08 的代码真踩了这个坑（第 875 行 `"/AGENT.md"`），
> 已于 2026-07-04 修复为 `"/AGENTS.md"`。

---

## 六、跑完后 result["files"] 里有什么、谁能跨线程存活（原 B4，✗）

**原题**：part09 跑完后 `result["files"]` 里有哪些文件？换新 thread 后哪些还在？

**你当时的回答**：只数了自己上传的文件，还说"skill 切换线程还能用"。

**标准答案**：

- 重点是 **agent 自己生成的文件**：按 AGENTS.md 工作流应有 `/final_report.md`、
  可能有社交帖子文件，以及 `/memories/research_notes.md`。
- 跨线程存活的判定标准**只有一条**：路径是否匹配 `/memories/` 路由。
  - `/memories/research_notes.md` → **活** ✓
  - `/final_report.md`、`/AGENTS.md`、两个 SKILL.md → 全在 state，新 thread 全没了。
- **skill 文件换线程后不能用**：它们是通过 invoke 的 `files` 参数塞进 state 的，
  新 thread 不重新上传就没有。part08 第二次 invoke（写 Twitter thread）
  换了新 thread 且没再传 files，那次运行 agent 其实摸不到任何 SKILL.md——
  可以对比两次输出，能看出格式约束松了。

---

## 七、final agent 的完整因果链（原 C1，✗ 太虚）

**原题**：讲一遍 part09 final agent 从 invoke 到产出的完整流程。

**你当时的回答**："边思考边推理形成闭环"——费曼法要消灭的正是这种不传递信息的话。

**标准答案（一条具体因果链）**：

1. 运行开始 → `/AGENTS.md` **全文注入**上下文（skills 只注入目录）
2. 模型按 AGENTS.md 的流程先 `write_todos` 拆任务
3. 调 2-3 次 `tavily_search`，每次搜索后反思
4. 综合写 `/final_report.md`（→ 落 **state**）
5. 看到任务要求 LinkedIn 帖子 → 从技能目录匹配到 linkedin-post
6. `read_file` 读入该 SKILL.md 全文 → 按格式写帖子
7. 把要点存 `/memories/research_notes.md`（→ 落 **store**，跨线程留存）

---

## 八、上生产要改什么（原 C2，△）

**原题**：这套 demo 直接上生产，最要命的问题是什么？

**你当时的回答**：说中"内存存储不能上生产"；"向量存储"方向偏了；
漏了最关键的身份伪造问题。

**标准答案**：

1. **存储实现替换** ✓：MemorySaver → PostgresSaver，InMemoryStore → PostgresStore。
2. 向量/语义检索解决的是"记忆多了怎么搜"，**不解决隔离问题**——
   Alice/Bob 的隔离靠 namespace 里的 `user_id`。
3. **最要命的（你漏的）**：demo 里 `user_id` 是从 `config` 里**客户端随便传的**——
   Bob 在请求里把 `user_id` 写成 "alice" 就能直接读走 Alice 的全部记忆。
   生产上 `user_id` 必须来自**服务端认证后的会话**，而不是请求参数。
4. `getattr(rt.context, "user_id", "default")` 这个兜底也危险：
   所有没带 user_id 的请求共享同一个 "default" 桶，
   等于匿名用户互相看得见对方的记忆。

---

## 附：最终掌握状态速查

| 知识点 | 状态 |
|---|---|
| checkpointer（线程内）vs store（跨线程） | ✓ 已掌握 |
| 三种记忆类型 + namespace 隔离 | ✓ 补考修正 |
| skills 渐进式披露 | ✓ 机制懂了，"为什么"需复述 |
| **路径前缀 → backend 路由** | ⚠️ 会背规则，未成条件反射（做第三节的实操练习焊死） |
