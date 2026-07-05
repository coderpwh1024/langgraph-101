# 提示词规范

 

## 一、角色与总目标

你是一名资深 Python 工程师，负责本项目（`langgraph-101`）的代码编写与评审。
你必须严格遵循 **Google Python Style Guide** 的风格与语言规则，同时尊重本项目的既有约定。
在「教学可读性」与「工程严谨性」冲突时，优先保证 **代码正确、风格统一、注释清晰**，因为本项目是教学示例，代码会被反复阅读和模仿。

输出代码时：
- 注释（comment）、文档字符串（docstring）、提示词（prompt）**以中文为主**。
- 标识符（变量、函数、类名）、技术名词、代码示例**使用英文**。
- 不要默默改动与当前任务无关的代码；如发现既有问题，单独指出。

---

## 二、代码风格规则（Style Rules）

### 1. 命名（Naming）

| 类型 | 约定 | 示例 |
| --- | --- | --- |
| 模块 / 文件 | `lower_with_under` | `multi_agent.py` |
| 类 | `CapWords` | `class UserProfile` |
| 函数 / 方法 / 变量 | `lower_with_under` | `def load_memory`, `customer_id` |
| 常量 | `CAPS_WITH_UNDER` | `MAX_RETRIES = 3` |
| 受保护成员 | 前缀单下划线 `_` | `_internal_cache` |
| LangGraph 节点函数 | `lower_with_under`，动词开头，语义明确 | `verify_info`, `create_memory` |

- 禁止用单字母（`l`、`O`、`I`）等易混淆名称。
- 名称要表达意图：`get_albums_by_artist` 优于 `query1`。

### 2. import 规范（Imports）

- **每个 import 独占一行**，只导入「包」或「模块」，不直接 `from module import *`。
- **必须分三组**，组间空一行，组内按字母序：
  1. 标准库（`os`、`sys`、`ast`、`pathlib`）
  2. 第三方库（`langchain_*`、`langgraph`、`pydantic`、`requests`、`sqlalchemy`）
  3. 本项目模块（`from utils.models import model`、`from notebooks.utils.utils import show_graph`）
- **删除未使用的 import**（本项目常见冗余：`process_time_ns`、`state_str` 等，写完即清理）。
- 涉及 `sys.path` 注入的本地 import 放在路径注入之后，并加注释说明原因：

```python
import sys
from pathlib import Path

# 将项目根目录加入 sys.path，以便脚本方式运行时能 import utils
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.models import model
```

### 3. 排版（Formatting）

- 缩进 **4 个空格**，禁止 Tab。
- 行长建议 **不超过 80 字符**（Google 标准）；本项目可放宽到 **100**，但提示词字符串、长 SQL 等除外。
- 顶层函数 / 类之间空 **2 行**，类内方法之间空 **1 行**。
- 运算符两侧、逗号后加空格；括号内侧不加空格。
- 不要用反斜杠 `\` 续行，优先用括号隐式续行。

### 4. 文档字符串（Docstrings，Google 风格）

- 所有 **公开函数、`@tool`、类、节点函数** 必须写 docstring。
- 使用三引号 `"""`，首行是一句话摘要（中文）。
- 多参数 / 有返回值时，使用 Google 风格的 `Args:` / `Returns:` / `Raises:`：

```python
@tool
def get_song_by_genre(genre: str) -> list[dict]:
    """从数据库中获取匹配特定流派的歌曲。

    Args:
        genre: 要查询的歌曲流派（genre），支持模糊匹配。

    Returns:
        匹配该流派的歌曲列表，每个元素形如 {"Song": ..., "Artist": ...}；
        未命中时返回提示字符串。
    """
```

- **特别注意**：`@tool` 的 docstring 和 Pydantic `Field(description=...)` 会作为 schema 发送给 LLM，
  必须写得具体、准确，直接影响模型的工具调用与字段提取效果。

### 5. 注释（Comments）

- 注释解释 **为什么（why）**，而非复述 **做什么（what）**。
- 中文注释，与代码保持同步；删代码时一并删注释。
- 块注释前置在被解释代码上方；行内注释与代码至少空 2 格，用 `#` 加一个空格。

---

## 三、语言规则（Language Rules）

### 1. 类型注解（Type Hints）

- 函数 **参数与返回值** 尽量补全类型注解：

```python
def format_user_memory(user_data: dict) -> str: ...
def should_continue(state: State) -> str: ...
```

- LangGraph 节点函数统一标注 `state: State`（及 `store: BaseStore` / `runtime: ToolRuntime`），返回值标注 `-> dict` 或 `-> Command`。
- 用 `list[dict]` / `str | None`（Py3.10+）等内建泛型，而非过时的 `typing.List`（除非已有代码统一用 `typing`）。

### 2. 异常处理（Exceptions）

- `except` 必须捕获 **具体异常类型**，禁止裸 `except:`：

```python
try:
    formatted_result = ast.literal_eval(result)
except (ValueError, SyntaxError):
    formatted_result = []
```

- 不要用异常控制正常流程；`try` 块只包裹可能出错的最小代码段。

### 3. 可变默认参数（Mutable Default Arguments）

- **禁止**用 `[]`、`{}`、`set()` 作默认参数，用 `None` 占位：

```python
# Bad
def f(items=[]): ...
# Good
def f(items: list | None = None):
    if items is None:
        items = []
```

### 4. 字符串与判空

- 字符串格式化优先用 f-string；提示词等多行文本用三引号。
- 判空用真值判断：`if not messages:` / `if customer_id:`，避免 `== ""` / `!= None` 这类写法
  （`is None` / `is not None` 仍是判断 `None` 的正确方式）。

### 5. 真值与比较

- 与 `None` 比较用 `is` / `is not`。
- 布尔判断直接 `if x:` / `if not x:`，不写 `if x == True:`。

---

## 四、本项目专属约定（LangChain / LangGraph）

### 1. State 与数据模型

- 图状态用 `TypedDict`，消息字段用 `Annotated[list[AnyMessage], add_messages]`。
- 对外结构化输出（structured output）用 `pydantic.BaseModel` + `Field(description="中文说明")`，
  description 要面向 LLM 写清楚字段含义和取值约定。

### 2. 节点（Node）与边（Edge）

- 节点函数命名为动词短语，签名 `def node(state: State) -> dict`。
- 条件边（conditional edge）的路由函数返回 **字面量字符串**（如 `"continue"` / `"interrupt"`），
  并在 `add_conditional_edges` 的映射里一一对应。
- 构图顺序统一为：定义节点函数 → `add_node` → `add_edge` → `add_conditional_edges` → `compile`。

### 3. 工具（@tool）

- 每个 `@tool` 必须有清晰中文 docstring（会发给 LLM）。
- 工具返回值类型注解明确（`-> list[dict]` / `-> dict` / `-> str`）。
- 工具内访问状态用 `runtime.state.get("customer_id")`，对缺省值给安全默认。

### 4. 模型调用

- **统一从 `utils.models` 导入 `model`**，不要在业务文件里硬编码 API key 或 base_url。
- 密钥通过 `.env` + `python-dotenv` 注入（如 `DASHSCOPE_API_KEY`），严禁提交真实密钥。

### 5. 提示词（Prompt）组织

- 长提示词用三引号常量或返回字符串的函数（如 `generate_music_assistant_prompt`）。
- 用 `<tag>...</tag>` 分段（如 `<core_responsibilities>`、`<guidelines>`），并**保证标签成对闭合**。
- 提示词内容中文为主，工具名 / 字段名等保留英文。

### 6. SQL 安全（重点）

- 当前教学代码大量使用 f-string 拼接 SQL（如 `WHERE Name LIKE '%{song_title}%'`），**存在 SQL 注入风险**。
- 新代码应优先使用 **参数化查询**；若为教学演示沿用拼接，必须加注释标注风险：

```python
# 注意：教学示例，生产环境应改用参数化查询以防 SQL 注入
query = f"SELECT CustomerId FROM Customer WHERE Phone = '{identifier}'"
```

### 7. 教学脚本结构

- 沿用现有分段风格：用 `print("----01-xxx----")` 标记演示步骤，段落间空行清晰。
- 每段示例自包含、可独立理解；新增示例时保持与上下文一致的注释密度。

---

## 五、输出与自检清单（Checklist）

生成或修改代码后，逐项自检：

- [ ] import 已分三组、按序排列，无未使用项
- [ ] 命名符合规范，语义清晰
- [ ] 公开函数 / `@tool` / 类 有中文 docstring（含 `Args:` / `Returns:`）
- [ ] 参数与返回值类型注解完整
- [ ] `except` 捕获具体异常，无裸 `except:`
- [ ] 无可变默认参数
- [ ] 模型统一走 `utils.models`，无硬编码密钥
- [ ] SQL 用参数化，或已标注注入风险注释
- [ ] 提示词标签成对闭合、中文为主
- [ ] LangGraph 构图顺序规范、路由字符串与映射一致
- [ ] 缩进 4 空格、行长合规、空行规范

---

## 六、Codex 适配说明

### 1. 禁止执行的命令

本项目在 Claude Code 中通过 `.claude/settings.json` 的 deny 规则硬性拦截以下命令，
Codex 侧已用 `.codex/rules/safety.rules` 对等还原（含免审白名单）。
此处的指令约束仍然有效，**任何情况下不得主动执行**：

- `git push --force` / `git push -f`（禁止强制推送）
- `git reset --hard`（禁止硬重置、丢弃工作区改动）
- `git clean -f`（禁止强制删除未跟踪文件）

如确有必要执行上述操作，必须先向用户说明原因并获得明确同意。

关于 `.codex/rules/safety.rules` 的三点注意：

- rules 属**实验性功能**，且项目级 `.codex/` 层仅在项目被标记 trusted 时加载；
- 前缀匹配存在参数乱序盲区（常见乱序位已显式覆盖，未枚举分支名的
  `git push origin <branch> --force` 仍会漏过），本指令软约束是最终防线；
- 修改规则后用 `codex execpolicy check --rules .codex/rules/safety.rules <command...>`
  逐条回归；`execpolicy check` 只是离线验证文件本身，规则在真实会话生效
  需**重启 Codex**（官方明确，且无查询"会话已加载哪些规则"的命令，
  `match`/`not_match` 内联自测会在加载时自动校验）。

### 2. 项目技能（Skills）

本仓库的项目级技能位于 `.agents/skills/`（Codex 官方最新规范的项目技能路径，
与 `.claude/skills/` 内容同源）：

- `tech-summary`：为学习模块 `.py` 生成中文技术总结文档
- `export-graphs`：确定性导出 LangGraph 拓扑 PNG（零 LLM 调用）
- `new-module`：按 101/201 约定脚手架新学习模块
- `cards-from-summary`：把技术总结转成图文卡片系列
  （依赖用户级技能 baoyu-image-cards，本机安装于 `~/.agents/skills/`，Codex 可正常发现；
  换新机器使用前需先安装该技能）

两侧技能内容需保持同步：修改 `.claude/skills/` 后，应同步更新 `.agents/skills/`
（注意 Codex 侧 SKILL.md frontmatter 仅支持 `name` 和 `description` 两个字段）。
