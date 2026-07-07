Create a Xiaohongshu style vertical 3:4 infographic in sketch-notes style.

## Style

Hand-drawn educational diagram, warm cream background, macaron palette, rounded cards, wavy arrows, simple icons, clear hierarchy.

## Text Rules

All text must be readable Chinese. Keep API names exact: StateBackend, FilesystemBackend, StoreBackend, CompositeBackend.

## Content

Title:
Backend 路由

Subtitle:
文件路径看起来一样
背后的存储语义不一样

Central node:
CompositeBackend
路径分流器

Three route rows. Keep each path, backend and meaning in the same row:

Row 1:
默认路径
StateBackend
临时状态 / 会话内文件

Row 2:
/workspace/*
FilesystemBackend
真实磁盘 / 可持久化文件

Row 3:
/memories/*
StoreBackend
长期记忆 / namespace 隔离

Bottom takeaway:
路径前缀 = 存储边界 = 业务语义

Visual concept:
A central pastel router box named "CompositeBackend 路径分流器" sends three clearly separated horizontal rows downward. Do not cross arrows. Do not swap labels. Each row must place the path on the left, the backend name in the middle, and the storage meaning on the right.

Layout:
Flow/list hybrid. Top is the router title. Middle is three stacked route rows:
1 默认路径 -> StateBackend -> 临时状态
2 /workspace/* -> FilesystemBackend -> 真实磁盘
3 /memories/* -> StoreBackend -> 长期记忆
Bottom takeaway banner.

No watermark.
