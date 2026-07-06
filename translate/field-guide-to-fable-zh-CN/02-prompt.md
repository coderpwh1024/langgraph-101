# 翻译提示词

## 任务

将 `translate/field-guide-to-fable.md`（英文，X Article）翻译为简体中文，输出到 `translation.md`。

## 目标读者与风格

- 受众：technical（熟悉 AI 编程工具的开发者）
- 风格：technical——精准、简洁，少修饰；但保留作者第一人称经验分享的语感
- 质量标准：读起来像中文原生技术博客，不带翻译腔

## 硬性要求

1. 保留全部 Markdown 结构：标题层级、图片、链接、列表。
2. Frontmatter：源字段加 `source` 前缀（camelCase），新增翻译后的元信息字段；正文有 H1，故不加 `title` 字段。
3. 术语按 `01-analysis.md` 术语表统一；核心概念首次出现标注英文。
4. 作者建议原样使用的触发词（"blindspot pass"、"unknown unknowns"）在示例提示词中保留英文，可加中文说明。
5. 原文笔误按作者意图译顺；正文裸 URL 按上下文补出自然锚文本。
6. 示例提示词（Example prompts）译为可直接复用的中文提示词。
7. 仅在读者确实需要背景时加**粗体括注**，全篇控制在 3 处以内。

## 长句处理

英文长句拆为中文短句；隐喻（potholes / forest through the trees 等）按意图意译，不逐字硬译。
