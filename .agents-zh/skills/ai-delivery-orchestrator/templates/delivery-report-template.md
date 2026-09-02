<!-- ai-delivery-template-language
使用本模板前，将所有人类可读的标题、标签和正文改为用户当前对话语言。ID、状态值、路径、命令、时间戳、哈希和占位符保持原样。实例化模板后删除本注释。
-->

# 交付报告 — <req-id>

> 由 archive 动作自动生成（所有子需求已归档）。本文件是 `runtime_mode=completed` 的交付摘要；canonical 产物保留在各自需求目录中。

## 概览

- 需求 ID：<req-id>
- 归档时间：<archived_at>
- 子需求数：<subreq_count>
- canonical 产物：各子需求产物保留在原目录中；本文件仅提供摘要。

## 子需求清单

| 子需求 | 状态 | canonical 产物 | verification |
|--------|------|----------|-------------|
<subreq_rows>

## 验证摘要

- 每个子需求的 `verification.md` 已签署，并包含评审轮次、验证命令与结果、签署对应的三个必备语言无关标记。
- `validate-artifact-layout.py --verify-archive` 仅在旧仓库存在历史快照时额外校验；当前原位归档不要求快照。

## 变更与后续

- 需求后续变更须开新 `<req-id>/` 目录；已完成需求目录保留为历史事实源。
- 归档期间不得复制第二份 canonical 需求产物。
