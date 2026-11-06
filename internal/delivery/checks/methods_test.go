package checks

import (
	"strings"
	"testing"
)

const nativeJSON = `{"version":1,"checks":[{"id":"native-save","acceptance_ids":["AC-001"],"argv":["go","test","-json","-count=1","./src"],"cwd":".","parser_id":"go-test-json","input_paths":["src/owner.go","src/owner_test.go","go.mod"],"report_paths":[],"source_refs":["src/owner_test.go"]}]}`

func methodDesign(body string) []byte {
	return []byte("<!-- ai-delivery:behavior-contract:start -->\n<!-- ai-delivery:behavior-contract:scope -->\n保存\n<!-- ai-delivery:behavior-contract:behavior -->\nB-001 保存\n<!-- ai-delivery:behavior-contract:acceptance -->\nAC-001 保存\n<!-- ai-delivery:native-methods:v1 -->\n```json\n" + body + "\n```\n<!-- /ai-delivery:native-methods:v1 -->\n<!-- ai-delivery:behavior-contract:traceability -->\nB-001 AC-001\n<!-- ai-delivery:behavior-contract:end -->\n")
}

func TestNativeMethodsStrictBinding(t *testing.T) {
	methods, err := NativeMethods(methodDesign(nativeJSON))
	if err != nil || len(methods) != 1 || methods[0].Method.ParserID != "go-test-json" || methods[0].AcceptanceIDs[0] != "AC-001" {
		t.Fatalf("%+v %v", methods, err)
	}
	for _, body := range []string{
		strings.Replace(nativeJSON, `"version":1`, `"version":1,"unrecognized":true`, 1),
		strings.Replace(nativeJSON, `"id":"native-save"`, `"id":"native-save","required":false`, 1),
		strings.Replace(nativeJSON, `"version":1`, `"version":2`, 1),
		strings.Replace(nativeJSON, `"version":1`, `"version":1,"version":1`, 1),
		strings.Replace(nativeJSON, `"native-save"`, `"inputs"`, 1),
		strings.Replace(nativeJSON, `"native-save"`, `"verification"`, 1),
		strings.Replace(nativeJSON, `"go-test-json"`, `"plugin"`, 1),
		strings.Replace(nativeJSON, `"AC-001"`, `"AC-009"`, 1),
		strings.Replace(nativeJSON, `"cwd":"."`, `"cwd":"../outside"`, 1),
		strings.Replace(nativeJSON, `"src/owner.go"`, `"/outside"`, 1),
		strings.Replace(nativeJSON, `"input_paths":["src/owner.go","src/owner_test.go","go.mod"]`, `"input_paths":[]`, 1),
		strings.Replace(nativeJSON, `"source_refs":["src/owner_test.go"]`, `"source_refs":[]`, 1),
		strings.Replace(nativeJSON, `"argv":["go","test","-json","-count=1","./src"]`, `"argv":[]`, 1),
		strings.Replace(nativeJSON, `"report_paths":[]`, `"report_paths":null`, 1),
		strings.Replace(nativeJSON, `}]}`, `},`+strings.Split(nativeJSON, `"checks":[`)[1], 1),
		`{bad`,
	} {
		if _, err := NativeMethods(methodDesign(body)); err == nil {
			t.Errorf("接受非法方法: %s", body)
		}
	}
	if _, err := NativeMethods(append(methodDesign(nativeJSON), methodDesign(nativeJSON)...)); err == nil {
		t.Fatal("重复块被接受")
	}
	if _, err := NativeMethods([]byte("````markdown\n" + string(methodDesign(nativeJSON)) + "````\n")); err == nil {
		t.Fatal("代码示例提供执行权限")
	}
	if methods, err := NativeMethods([]byte("普通无方法设计")); err != nil || len(methods) != 0 {
		t.Fatal(methods, err)
	}
}
