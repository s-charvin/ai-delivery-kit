# 阻塞项分类

## 核心阻塞项

- `blocked_requirement_conflict`: 需求来源自身矛盾或与其他需求来源矛盾。
- `blocked_missing_requirement`: 关键业务事实缺失。
- `blocked_figma_conflict`: 设计来源自身矛盾。
- `blocked_requirement_figma_conflict`: 需求真值与视觉真值不一致。
- `blocked_missing_design`: 设计证据中缺少所需的视觉载体。
- `blocked_dependency`: 上游子需求尚未合并到主开发分支。
- `blocked_merge_conflict`: 合并回主开发分支失败。
- `blocked_verification_failure`: 必要检查失败，输出不可信。

## 使用规则

选择最能解释为何无法进行下一状态转换的最具体阻塞项，然后在相应的需求文件夹中记录证据和恢复条件。
