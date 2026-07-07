Create a Xiaohongshu style vertical 3:4 infographic in sketch-notes style.

## Style

Warm cream paper texture, macaron blue/lavender/mint/peach blocks, hand-drawn arrows, rounded cards, small doodle icons, charcoal Chinese handwriting with coral accent.

## Text Rules

All text must be clear Chinese. API names must be exact: @tool, TavilyClient, TAVILY_API_KEY, RuntimeError.

## Content

Title:
工具扩展：让 Agent 能搜索

Core message:
@tool 把外部能力变成 LLM 可调用动作

Flow steps:
1. 检查 TAVILY_API_KEY
2. 创建 TavilyClient
3. search(query)
4. 返回标题 + URL + 摘要
5. Agent 写入研究笔记

Side note:
docstring 会进入工具 schema
写得越清楚，模型越会用

Risk note:
缺少 key 时抛 RuntimeError
避免匿名模式被限流

Visual concept:
A search magnifier sends a query to three result cards, each card has title, URL tag and summary lines. A small robot collects them into a notebook named "research notes".

Layout:
Flow layout, left-to-right then downward path. Use five numbered pastel nodes connected by curved arrows.

No watermark.

