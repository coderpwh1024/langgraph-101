# deep_agents · Backend 一页纸速查

> 对象：`notebooks/201/deep_agents.py` 的 Part 3（Backends）
> 来源：费曼学习法阶段性测试（Backend 三轮 12 题）结业归档
> 配套：`deep_agents_学习路线.md`（阶段 B 的验收落地物）

---

## 一、一句话定义

**Backend = agent 读写文件时背后的「存储插座」。**
agent 调的永远是统一的 `ls` / `read_file` / `write_file` 动作，backend 决定这些动作**最终落到哪种介质**——换存储只换 backend，agent 代码一行不改（解耦）。

---

## 二、四种 Backend 对照

| Backend | 文件存哪 | 隔离维度 | 寿命 | 关键点 |
| --- | --- | --- | --- | --- |
| **StateBackend** | 对话 state 里 | 绑 `thread_id` | 临时 / 短期 | **依赖 checkpointer 才能跨 invoke 不丢** |
| **FilesystemBackend** | 真实磁盘目录 | 跨 thread / 跨用户可读 | 持久 / 可共享 | `virtual_mode=True` 开沙箱 |
| **StoreBackend** | store（偏 KV + namespace） | 绑 `namespace`（用户） | 长期记忆 | 跨 thread，按用户隔离 |
| **CompositeBackend** | 由路由分流到上面几种 | 按**路径前缀** | 取决于子 backend | `routes` 命中走对应，其余走 `default` |

---

## 三、两个最容易混的独立维度（重点）

这三件事是**不同维度**，不是包含关系：

```
· checkpointer = 把整个 state 拍快照「存档」      → 管「会不会丢」
                 MemorySaver = 内存版（临时，进程结束就没）
                 SqliteSaver = 落盘版（可持久）

· thread_id    = 决定读「哪一份存档」             → 管「读谁的会话」

· namespace    = StoreBackend 里按用户隔离        → 管「哪个用户的长期记忆」
```

**StateBackend ↔ checkpointer 的配合关系**（本块唯一难点）：

> StateBackend 只负责「把文件放进 state」（柜子）；
> checkpointer 负责「把整个 state 拍快照存档」（存档/读档）。
> **没有 checkpointer，哪怕同一个 thread，这次 invoke 写的文件，下次 invoke 也读不到**——因为没人帮 state 续命。
>
> 完整逻辑链：**先靠 checkpointer 存档（解决会不会丢）→ 再靠 thread_id 选读哪份存档（解决读谁的）**。两个条件都满足才能读到上一轮数据；少 checkpointer = 根本没存档，换 thread = 读错了存档，原因不同。

---

## 四、virtual_mode 沙箱

`FilesystemBackend(root_dir=..., virtual_mode=True)`：

- agent 眼里的「`/`」是**假根**，被映射到 `root_dir`；写 `/a.txt` 实际落在 `root_dir/a.txt`。
- agent **爬不出 `root_dir`**——碰不到系统其他文件（如 `/etc/passwd`），防越狱。
- 两层好处：① 安全（跳不出去）② 干净（agent 的文件世界收拢在一个目录里，好管理）。
- `virtual_mode=False`：路径即真实系统路径，**无沙箱保护，危险**。

---

## 五、CompositeBackend 路由

按**路径前缀**把文件分流到不同 backend：

```python
CompositeBackend(
    default=StateBackend(),                          # 兜底：没命中 routes 的都走这里
    routes={"/workspace/": FilesystemBackend(...)},  # 前缀命中：/workspace/* 落盘
)
```

- `/workspace/report.md` → FilesystemBackend（落盘持久）
- `/scratch.txt` → default 即 StateBackend（临时）
- agent 不用管分流，CompositeBackend 按前缀自动路由。

---

## 六、选型口诀

> **临时草稿 → State｜落盘文件 → Filesystem｜用户长期记忆 → Store｜要混用 → Composite**

典型组合（多用户助手：长期记忆 + 临时草稿）：

```python
CompositeBackend(
    default=StateBackend(),                    # 临时草稿，聊完就扔
    routes={"/memories/": StoreBackend()},     # 长期记忆，按用户 namespace 隔离
)
```
