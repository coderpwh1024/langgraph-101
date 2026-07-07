Create a Xiaohongshu style vertical 3:4 infographic in sketch-notes style.

## Style

Warm cream paper, hand-drawn educational flow, macaron color blocks, small doodles, coral highlights, clear Chinese handwriting.

## Text Rules

All text must be readable. Preserve exact API names: wrap_tool_call, handler(request), ClearToolUsesEdit, trigger=1, keep=1.

## Content

Title:
Middleware：运行时治理层

Core message:
工具调用不是黑盒
可以记录、包裹、裁剪

Pipeline:
Tool Request
-> wrap_tool_call
-> 打印工具名和参数
-> handler(request)
-> Tool Done

Context editing box:
ClearToolUsesEdit
trigger=1
keep=1
清理旧工具结果
保留最近信息

Why it matters:
搜索型 Agent 最怕上下文噪声
旧结果要及时收纳

Visual concept:
A conveyor belt carries tool calls. A logger stamp marks the request, a tool box executes it, and scissors trim old long result scrolls.

Layout:
Top half flow pipeline, bottom half context cleanup mini-diagram.

No watermark.

