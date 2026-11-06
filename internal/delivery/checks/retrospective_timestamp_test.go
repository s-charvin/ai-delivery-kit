package checks

import (
	"strings"
	"testing"
	"time"
)

func TestRetrospectiveReviewedAtCurrentTimestampBoundary(t *testing.T) {
	now := time.Date(2026, 11, 5, 0, 0, 0, 0, time.UTC)
	for _, tc := range []struct {
		raw   string
		valid bool
	}{
		{"2026-11-05", true},
		{"2026-11-05T10:00:00.123456789+08:00", true},
		{"2026-11-05T10:00:00Z", true},
		// 保持标记自身日历日期比较；不转换成 UTC 后再改归档日期语义。
		{"2026-11-05T00:00:00+23:59", true},
		{"2026-11-05T1:00:00Z", false},
		{"2026-11-05T10:00:00+24:00", false},
		{"2026-11-05T10:00:00", false},
		{"2026-11-05T10:00:00,123Z", false},
		{"2026-11-31", false},
	} {
		t.Run(tc.raw, func(t *testing.T) {
			body := strings.Replace(ledger, "2026-11-05T10:00:00+08:00", tc.raw, 1)
			_, err := RetrospectiveEntries([]byte(body), now)
			if (err == nil) != tc.valid {
				t.Fatalf("reviewed-at=%q accepted=%v want=%v error=%v", tc.raw, err == nil, tc.valid, err)
			}
			if !tc.valid {
				for _, text := range []string{"YYYY-MM-DD", "RFC3339Nano", "2026-11-05T12:00:00+08:00"} {
					if !strings.Contains(err.Error(), text) {
						t.Fatalf("目标格式诊断缺少 %s: %v", text, err)
					}
				}
			}
		})
	}
	stale := strings.Replace(ledger, "2026-11-05T10:00:00+08:00", "2026-11-04", 1)
	if _, err := RetrospectiveEntries([]byte(stale), now); err == nil || !strings.Contains(err.Error(), "不是归档当日") {
		t.Fatalf("归档日期比较改变: %v", err)
	}
}
