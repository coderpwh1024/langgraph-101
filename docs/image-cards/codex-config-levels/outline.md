---
strategy: b
name: Information-Dense
style: sketch-notes
palette: macaron
style_reason: "干货对比类内容，沿用本仓库卡片系列锁定风格 sketch-notes × macaron，保证系列视觉一致"
elements:
  background: warm-cream-paper
  decorations: [wobble-boxes, hand-drawn-arrows, sticky-notes, small-mascot]
  emphasis: coral-highlight
  typography: hand-drawn-chinese-cartoon
layout: dense
image_count: 8
language: zh
---

## P1 Cover
**Type**: cover
**Hook**: "Codex 配置到底放哪？🤔 用户级 vs 项目级 一次讲清"
**Visual**: 中央一只困惑的小吉祥物站在两个文件夹岔路口（~/.codex 与 <repo>/.codex），
上方大字标题，底部小字"5 种合并语义 · 10 项配置 · 官方文档核对"
**Layout**: sparse

## P2 分层总览
**Type**: content
**Message**: 6 级优先级链（CLI 覆盖 > 项目级 > profile > 用户级 > 系统级 > 内置默认），
项目级仅 trusted 生效、就近优先
**Visual**: 纵向阶梯/金字塔图，每级一个色块，箭头自上而下标"优先级高→低"，
trusted 门槛画成小闸机图标
**Layout**: flow

## P3 双目录树对照
**Type**: content
**Message**: 用户级 ~/.codex + ~/.agents/skills vs 项目级 <repo>/.codex + <repo>/.agents/skills；
config/AGENTS.md/prompts/hooks/rules 各就各位；⚠️ 技能在 .agents/ 不在 .codex/
**Visual**: 左右两棵手绘目录树对照，关键差异用珊瑚色高亮圈出（.agents/skills）
**Layout**: comparison

## P4 config.toml 与 AGENTS.md
**Type**: content
**Message**: config.toml 就近覆盖（项目 > 用户，方向反直觉）；AGENTS.md 顺序拼接、
越近越优先、总量 32 KiB；override 文件优先；机器级键项目改不动
**Visual**: 上下两个便签分区：上半 config 覆盖示意（大块盖小块），
下半 AGENTS.md 拼接示意（纸条从根到当前目录依次粘贴）
**Layout**: dense

## P5 Skills 四级作用域
**Type**: content
**Message**: REPO（cwd→仓库根每级 .agents/skills）/ USER（~/.agents/skills）/
ADMIN（/etc/codex/skills）/ SYSTEM（内置）；SKILL.md 必含 name+description；
同名不合并、并列出现
**Visual**: 四个同心圆或四层货架，每层放技能小盒子；旁边一个 my-skill/ 目录小结构图
**Layout**: dense

## P6 五种合并语义（高潮页）
**Type**: content
**Message**: config=就近覆盖 / AGENTS.md=顺序拼接 / skills=不合并并列 /
hooks=并集全加载 / rules=取最严；同一对路径冲突结果完全不同
**Visual**: 五行清单，每行一个小图标（盖章/胶带/双胞胎/漏斗全开/锁）+ 一句话，
标题带"⭐ 最容易踩坑"角标
**Layout**: list

## P7 避坑要点
**Type**: content
**Message**: ① trusted 边界：.codex/ 受管控，AGENTS.md 与 .agents/skills 不受；
② rules 只能收紧不能放松；③ plugins 与 custom prompts 没有项目级
（prompts 已废弃 → 迁 skills）
**Visual**: 三个警示便签贴在软木板上，每条配小图标（闸机/棘轮/墓碑→新芽）
**Layout**: dense

## P8 Ending
**Type**: ending
**Message**: 一句心法"越接近本次运行的层，优先级越高"；
官方文档 developers.openai.com/codex；CTA：收藏备查 + 关注系列
**Visual**: 小吉祥物竖大拇指，旁边速查小卡（5 行迷你表），底部 CTA 横条
**Layout**: balanced
