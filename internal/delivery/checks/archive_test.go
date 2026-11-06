package checks

import (
	"strings"
	"testing"
	"time"
)

const ledger = `<!-- ai-delivery-retrospective:reviewed-at:2026-11-05T10:00:00+08:00 -->
<!-- ai-delivery-retrospective:problem-index:v2 -->
| Problem | Trigger | Scenario | Path | knowledge_type | reuse_scope | index_decision | confidence | importance | Status | Details |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RET-001 | 保存失败 | 重试 | src/save.go | reusable | project | include | confirmed | high | resolved | [详情](#ret-001) |
<!-- /ai-delivery-retrospective:problem-index:v2 -->
<a id="ret-001"></a>
## RET-001 保存失败
原因与修复。
`

func TestRetrospectiveStructureAndRouting(t *testing.T) {
	now := time.Date(2026, 11, 5, 0, 0, 0, 0, time.UTC)
	for _, tc := range []struct {
		name, body string
		valid      bool
	}{
		{"qualified", ledger, true},
		{"html-entity-anchor", strings.ReplaceAll(ledger, `id="ret-001"`, `id="ret&#45;001"`), true},
		{"calendar-date", strings.ReplaceAll(ledger, "2026-11-05T10:00:00+08:00", "2026-11-05"), true},
		{"stale", strings.ReplaceAll(ledger, "2026-11-05T", "2026-11-04T"), false},
		{"duplicate-row", strings.Replace(ledger, "<!-- /ai-delivery-retrospective:problem-index:v2 -->", "| RET-001 | x | x | x | reusable | project | include | confirmed | high | resolved | [详情](#ret-001) |\n<!-- /ai-delivery-retrospective:problem-index:v2 -->", 1), false},
		{"wrong-anchor", strings.Replace(ledger, "](#ret-001)", "](#other)", 1), false},
		{"orphan-detail", ledger + "\n## RET-002 无来源\n", false},
		{"revision-section", ledger + "\n## 本轮新增\n", false},
		{"quoted-heading", ledger + "\n```md\n## RET-002 示例\n```\n", true},
		{"comment-heading", ledger + "\n<!--\n## RET-002 示例\n-->\n", true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			rows, err := RetrospectiveEntries([]byte(tc.body), now)
			if (err == nil) != tc.valid {
				t.Fatalf("rows=%v error=%v", rows, err)
			}
			if tc.valid && (len(rows) != 1 || !rows[0].Indexable()) {
				t.Fatal(rows)
			}
		})
	}
}
