package aideliverygo_test

import (
	"go/ast"
	"go/parser"
	"go/token"
	"io/fs"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"testing"
)

// 空 PATH 之外再限制候选运行时的全部进程启动点；宿主程序只允许从绑定后的 runner argv 启动。
func TestRuntimeProcessLaunchesAreOnlyDeclaredHostOrGitObservation(t *testing.T) {
	_, source, _, _ := runtime.Caller(0)
	root := filepath.Clean(filepath.Join(filepath.Dir(source), "../.."))
	err := filepath.WalkDir(filepath.Join(root, "internal"), func(p string, d fs.DirEntry, e error) error {
		if e != nil {
			return e
		}
		if d.IsDir() {
			if d.Name() == "testdata" {
				return filepath.SkipDir
			}
			return nil
		}
		if !strings.HasSuffix(p, ".go") || strings.HasSuffix(p, "_test.go") {
			return nil
		}
		parsed, e := parser.ParseFile(token.NewFileSet(), p, nil, 0)
		if e != nil {
			return e
		}
		rel, _ := filepath.Rel(root, p)
		rel = filepath.ToSlash(rel)
		imports := map[string]string{}
		for _, im := range parsed.Imports {
			name, _ := strconv.Unquote(im.Path.Value)
			key := filepath.Base(name)
			if im.Name != nil {
				key = im.Name.Name
			}
			imports[key] = name
		}
		ast.Inspect(parsed, func(node ast.Node) bool {
			call, ok := node.(*ast.CallExpr)
			if !ok {
				return true
			}
			sel, ok := call.Fun.(*ast.SelectorExpr)
			if !ok {
				return true
			}
			pkg, ok := sel.X.(*ast.Ident)
			if !ok {
				return true
			}
			imp := imports[pkg.Name]
			launch := imp == "os/exec" && (sel.Sel.Name == "Command" || sel.Sel.Name == "CommandContext") || imp == "os" && sel.Sel.Name == "StartProcess" || imp == "syscall" && (sel.Sel.Name == "Exec" || sel.Sel.Name == "ForkExec" || sel.Sel.Name == "StartProcess")
			if !launch {
				return true
			}
			if rel == "internal/delivery/runner/run.go" && imp == "os/exec" && sel.Sel.Name == "Command" {
				return true
			}
			if rel == "internal/delivery/workspace/git.go" && imp == "os/exec" && sel.Sel.Name == "CommandContext" && len(call.Args) > 1 {
				if lit, ok := call.Args[1].(*ast.BasicLit); ok && lit.Value == `"git"` {
					return true
				}
			}
			t.Errorf("未声明的 kit 进程启动点: %s %s.%s", rel, pkg.Name, sel.Sel.Name)
			return true
		})
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
}
