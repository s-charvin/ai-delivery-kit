# 阻止器目录

## 核心阻止器

- `blocked_requirement_conflict`：需求源与自身或其他需求源矛盾。
- `blocked_missing_requirement`：关键业务事实缺失。
- `blocked_figma_conflict`：设计源与自身矛盾。
- `blocked_requirement_figma_conflict`：需求真相与视觉真相不一致。
- `blocked_missing_design`：设计证据中缺少必需的视觉载体。
- `blocked_dependency`：上游子需求未合并到主开发分支。
- `blocked_merge_conflict`：合并回主开发分支失败。
- `blocked_verification_failure`：所需检查失败，输出不可信。

## 使用规则

选择最能解释为何无法进行下一个状态转换的具体阻止器，然后在匹配的需求文件夹中记录证据和恢复条件。
