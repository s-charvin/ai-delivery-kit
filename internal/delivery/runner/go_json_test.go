package runner

import (
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

func TestGoJSONPackageSkipRequiresNoActualTests(t *testing.T) {
	const start = "{\"Action\":\"start\",\"Package\":\"tested\"}\n"
	const run = "{\"Action\":\"run\",\"Package\":\"tested\",\"Test\":\"TestSave\"}\n"
	const pass = "{\"Action\":\"pass\",\"Package\":\"tested\",\"Test\":\"TestSave\"}\n"
	const done = "{\"Action\":\"pass\",\"Package\":\"tested\"}\n"
	const skip = "{\"Action\":\"skip\",\"Package\":\"tested\"}\n"
	const testSkip = "{\"Action\":\"skip\",\"Package\":\"tested\",\"Test\":\"TestSave\"}\n"
	const emptyStart = "{\"Action\":\"start\",\"Package\":\"empty\"}\n"
	const emptySkip = "{\"Action\":\"skip\",\"Package\":\"empty\"}\n"
	const valid = start + run + pass + done
	cases := []struct {
		name   string
		stream string
		valid  bool
	}{
		{"tested-only", valid, true},
		{"no-test-package-after", valid + emptyStart + emptySkip, true},
		{"no-test-package-interleaved", start + emptyStart + run + emptySkip + pass + done, true},
		{"all-zero", emptyStart + emptySkip, false},
		{"test-skip", start + run + testSkip + done, false},
		{"test-skip-after-pass", start + run + pass + testSkip + done, false},
		{"run-then-package-skip", start + run + skip, false},
		{"passed-test-then-package-skip", start + run + pass + skip, false},
		{"package-skip-then-run", start + skip + run + pass + done, false},
		{"package-pass-then-skip", valid + skip, false},
		{"duplicate-package-skip", valid + emptyStart + emptySkip + emptySkip, false},
		{"duplicate-start", start + start + run + pass + done, false},
		{"duplicate-pass", start + run + pass + pass + done, false},
		{"package-skip-without-start", valid + emptySkip, false},
		{"test-without-package-start", emptyStart + emptySkip + run + pass + done, false},
		{"all-starts-missing", run + pass + done, false},
		{"nameless-pause-before-skip", valid + emptyStart + "{\"Action\":\"pause\",\"Package\":\"empty\"}\n" + emptySkip, false},
		{"nameless-cont-before-skip", valid + emptyStart + "{\"Action\":\"cont\",\"Package\":\"empty\"}\n" + emptySkip, false},
		{"unfinished-package", valid + emptyStart, false},
		{"unfinished-test", start + run + done, false},
		{"test-output-then-package-skip", valid + emptyStart + "{\"Action\":\"output\",\"Package\":\"empty\",\"Test\":\"TestSkipped\",\"Output\":\"skip\"}\n" + emptySkip, false},
		{"fail", valid + emptyStart + "{\"Action\":\"fail\",\"Package\":\"empty\"}\n", false},
		{"cached", start + run + pass + "{\"Action\":\"output\",\"Package\":\"tested\",\"Output\":\"ok tested (cached)\"}\n" + done, false},
		{"unknown-action", valid + emptyStart + "{\"Action\":\"unknown\",\"Package\":\"empty\"}\n", false},
		{"malformed-json", valid + "{", false},
	}
	for _, value := range []string{`null`, `0`, `true`, `[]`, `{}`, `""`} {
		cases = append(cases, struct {
			name, stream string
			valid        bool
		}{
			"invalid-Test-" + value,
			valid + emptyStart + fmt.Sprintf("{\"Action\":\"skip\",\"Package\":\"empty\",\"Test\":%s}\n", value), false,
		})
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			path := filepath.Join(t.TempDir(), "stdout.log")
			if err := os.WriteFile(path, []byte(tc.stream), 0600); err != nil {
				t.Fatal(err)
			}
			got, err := parseGoTests(path)
			if tc.valid {
				if err != nil || !reflect.DeepEqual(got, []string{"tested/TestSave"}) {
					t.Fatalf("真实测试与无测试包的终结混淆: got=%v err=%v", got, err)
				}
			} else if err == nil {
				t.Fatalf("无效或未成功完成的事件流被接受: %v", got)
			}
		})
	}
}
