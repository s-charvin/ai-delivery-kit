# 交付报告 — <req-id>

> 由 archive 动作自动生成（所有子需求已冻结归档）。本文件是需求交付的不可变总结，对应 `runtime_mode=completed`（全部子需求 `archived`）。

## 概览

- 需求 ID：<req-id>
- 归档时间：<archived_at>
- 子需求数：<subreq_count>
- 冻结快照：各子需求 `archive/<ISO-ts>/` + `MANIFEST.json`（sha256 校验）

## 子需求清单

| 子需求 | 状态 | 归档快照 | verification |
|--------|------|----------|-------------|
<subreq_rows>

## 验证摘要

- 每个子需求的 `verification.md` 已签署（必备三节：评审轮次记录 / 验证命令与结果 / 签署）。
- `validate-artifact-layout.py --verify-archive` 对全部归档快照通过 sha256 校验，无篡改。

## 变更与后续

- 需求后续变更须开新 `<req-id>/` 目录；本目录作为只读引用，不可变。
- 归档不可变性的机器校验依据为各 `archive/<ISO-ts>/MANIFEST.json` 的 sha256 清单。
