# 阻塞目录

## 核心阻塞器

- `blocked_requirement_conflict`：需求来源自身矛盾，或与其他需求来源矛盾。
- `blocked_missing_requirement`：缺少关键业务事实。
- `blocked_figma_conflict`：设计来源自身矛盾。
- `blocked_requirement_figma_conflict`：需求实情与视觉实情不一致。
- `blocked_missing_design`：设计证据中缺少所需的视觉载体。
- `blocked_dependency`：上游子需求尚未合并到主开发分支。
- `blocked_merge_conflict`：合并回主开发分支失败。
- `blocked_verification_failure`：必要检查失败，输出不可信。

## API 契约阻塞器

- `blocked_missing_api_contract`：用户要求 API 映射，但不存在可信的面向客户端契约来源。
- `blocked_api_contract_conflict`：多个 Swagger、OpenAPI 或导出的契约来源在面向客户端实情上存在分歧。
- `blocked_requirement_api_conflict`：需求实情与接口契约实情不一致。

## 使用规则

选择能够解释为何无法进行下一次状态转换的最窄阻塞器，然后在相应的需求文件夹中记录证据和恢复条件。
