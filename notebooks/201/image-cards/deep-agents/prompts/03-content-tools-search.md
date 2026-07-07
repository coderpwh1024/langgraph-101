Create a Xiaohongshu style vertical 3:4 infographic in sketch-notes style.

## Style

Warm cream paper texture, macaron blue/lavender/mint/peach blocks, hand-drawn arrows, rounded cards, small doodle icons, charcoal Chinese handwriting with coral accent.

## Text Rules

All text must be clear Chinese. API names must be exact: @tool, TavilyClient, TAVILY_API_KEY.
Render ONLY the text listed in Content below — do not invent any extra labels, captions or card titles. No other English words anywhere.
Exactly FIVE step cards. Each number 1, 2, 3, 4, 5 appears exactly ONCE, in strict ascending order.
Decorative cards contain only blank scribble lines, NO readable-looking fake text.
The step 5 card contains only the text: 5. Agent 写入研究笔记 — no English subtitle inside the card. The label "research notes" appears only on the robot's small notebook.

## Content

Title:
工具扩展：让 Agent 能搜索

Core message:
@tool 把外部能力变成 LLM 可调用动作

Flow steps:
1. 检查 TAVILY_API_KEY 缺失直接报错
2. 创建 TavilyClient
3. search(query)
4. 返回标题 + URL + 摘要
5. Agent 写入研究笔记

Side note:
docstring 会进入工具 schema
写得越清楚，模型越会用

Risk note:
缺少 key 直接报错
避免匿名模式被限流

Visual concept:
A search magnifier at the top. A small robot at the bottom collects results into a notebook labeled "research notes". The five numbered steps are stacked as ONE single vertical column of pastel rounded cards.

Layout:
ONE single vertical column, top to bottom: step 1 card, step 2 card, step 3 card, step 4 card, step 5 card, connected by short downward arrows. No grid, no zigzag, no side-by-side step cards. The side note and risk note are two separate bubbles at the bottom, each rendered verbatim in large clear text without mixing their sentences.

No watermark.

