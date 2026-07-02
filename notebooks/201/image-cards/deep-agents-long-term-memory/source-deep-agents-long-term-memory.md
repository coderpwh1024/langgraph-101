# 源内容 — deep_agents.py part07 长期记忆（Long-term Memory / Backend）

> 精炼自 `notebooks/201/deep_agents.py` 第 07 段「07-Long-term-Memory」，聚焦 Backend 机制。

## 一句话本质

Deep Agent 有一套虚拟文件系统（`write_file` / `read_file` / `ls`）。文件写到哪、能不能跨对话记住，
完全由 **Backend** 决定——长期记忆的魔法不是模型变聪明，而是「把文件柜从便利贴换成了云盘」。

## 四种 Backend（用文件柜类比）

| Backend | 类比 | 生命周期 | 底层靠谁 |
| --- | --- | --- | --- |
| `StateBackend` | 便利贴（贴在本场会议白板） | 线程结束即擦掉 | checkpointer 会话状态 |
| `FilesystemBackend` | 真实档案柜 | 永久，重启仍在 | 本机磁盘目录 |
| `StoreBackend` | 公司云盘 | 跨所有线程持久 | store（如 InMemoryStore） |
| `CompositeBackend` | 前台总台 | 取决于转发去向 | 按路径前缀路由 |

关键：Agent 自己不知道文件存哪，只管说「写到 `/memories/findings.md`」；
`CompositeBackend` 看到 `/memories/` 前缀，就转交给 `StoreBackend`（云盘），于是实现跨对话记忆。

## 演示 1：最基础的持久记忆

```python
composite_backend = CompositeBackend(
    default=StateBackend(),                     # 默认：便利贴（临时）
    routes={"/memories/": StoreBackend()},      # /memories/ 开头：云盘（持久）
)
```

- 线程1 把内容写到 `/memories/findings.md` → 落进云盘。
- 线程2（全新 thread_id = 新会议）去读同一文件 → 白板是空的，但云盘还在 → 读得到。
- 若写到 `/scratch.txt`（不带前缀）→ 走 default 的 StateBackend → 换线程就读不到。

## 演示 2：三种记忆类型，靠 namespace 分桶

```python
routes={
    "/memories/semantic/":   StoreBackend(namespace=lambda rt: ("memories", "semantic")),
    "/memories/episodic/":   StoreBackend(namespace=lambda rt: ("memories", "episodic")),
    "/memories/procedural/": StoreBackend(namespace=lambda rt: ("memories", "procedural")),
}
```

三条路由共用同一个 store，靠 `namespace`（分区键 tuple）分成三个桶：

- **semantic 语义记忆** = 事实：用户喜欢 Python
- **episodic 情景记忆** = 经历：上次一起研究了 LangGraph
- **procedural 程序记忆** = 规则：报告里用 [1][2] 行内引用

namespace 是 store 里的分区键，用 `(namespace, key)` 定位数据；同名文件也互不干扰。

## 演示 3：分级记忆 private vs shared（lambda rt 动态 namespace）

```python
"/memories/user/":   StoreBackend(
    namespace=lambda rt: ("user", getattr(rt.context, "user_id", "default"), "filesystem")),
"/memories/shared/": StoreBackend(namespace=lambda rt: ("shared", "filesystem")),
```

- Alice（user_id=alice）→ namespace 算成 `("user","alice",…)`
- Bob（user_id=bob）→ namespace 算成 `("user","bob",…)` → 另一个桶 → 看不到 Alice
- shared 的 namespace 写死 `("shared",…)` → 与 user_id 无关 → 全员共享

隔离逻辑既不在 Agent、也不在 prompt，而在 namespace 那行 **`lambda rt`**：
它把「当前是谁」从运行时 context 读出来拼进 key，这才是 private vs shared 的开关。

## 三级递进（整段主线）

| 维度 | 谁决定 |
| --- | --- |
| 存哪个柜子（能否跨线程） | CompositeBackend 的 routes 前缀 |
| 同柜子分不同抽屉 | StoreBackend 的 namespace（静态） |
| 抽屉按人隔离/共享 | namespace 的 lambda rt（动态） |

三者其实是「routing + namespace」由静到动的三级递进。
