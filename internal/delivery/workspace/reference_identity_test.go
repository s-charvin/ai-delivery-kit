package workspace_test

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

func TestReferenceIdentityDistinguishesAliasAbsenceDirectoryAndFile(t *testing.T) {
	for _, kind := range []string{"absent", "directory", "file"} {
		t.Run(kind, func(t *testing.T) {
			root := fixture(t)
			switch kind {
			case "directory":
				if e := os.Mkdir(filepath.Join(root, "target"), 0755); e != nil {
					t.Fatal(e)
				}
			case "file":
				put(t, root, "target", "当前文件")
			}
			if e := os.Symlink("target", filepath.Join(root, "alias")); e != nil {
				t.Fatal(e)
			}
			r := workspace.Reader{}
			w, e := r.Resolve(context.Background(), root, "")
			if e != nil {
				t.Fatal(e)
			}
			a := model.Action{Intent: "merge", TargetStatus: "merged"}
			s, e := r.Load(context.Background(), w, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, model.ReadRequest{Action: &a})
			if e != nil {
				t.Fatal(e)
			}
			s, e = r.Extend(context.Background(), s, []string{"./alias"})
			if e != nil {
				t.Fatal(e)
			}
			id, ok, e := workspace.Identity(s, "alias")
			if e != nil || !ok || id.Path != "alias" || id.ResolvedPath != "target" || id.Kind != kind {
				t.Fatal(id, ok, e)
			}
			if kind == "file" {
				*id.SHA256 = "mutated"
				again, _, _ := workspace.Identity(s, "alias")
				if *again.SHA256 == "mutated" {
					t.Fatal("事实未复制")
				}
			}
			if _, ok, e := workspace.Identity(s, "not-consumed"); e != nil || ok {
				t.Fatal("未读取不等于absence")
			}
			os.Remove(filepath.Join(root, "alias"))
			put(t, root, "other", "other")
			os.Symlink("other", filepath.Join(root, "alias"))
			if r.Verify(context.Background(), s) == nil {
				t.Fatal("链接换目标未失效")
			}
		})
	}
}
func TestReferenceIdentityPreservesAncestorBinding(t *testing.T) {
	root := fixture(t)
	put(t, root, "a/evidence.log", "same")
	put(t, root, "b/evidence.log", "same")
	os.Symlink("a", filepath.Join(root, "link"))
	r := workspace.Reader{}
	w, e := r.Resolve(context.Background(), root, "")
	if e != nil {
		t.Fatal(e)
	}
	a := model.Action{Intent: "merge"}
	s, e := r.Load(context.Background(), w, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, model.ReadRequest{Action: &a})
	if e != nil {
		t.Fatal(e)
	}
	s, e = r.Extend(context.Background(), s, []string{"link/evidence.log"})
	if e != nil {
		t.Fatal(e)
	}
	id, ok, e := workspace.Identity(s, "link/evidence.log")
	if e != nil || !ok || id.ResolvedPath != "a/evidence.log" {
		t.Fatal(id, ok, e)
	}
	os.Remove(filepath.Join(root, "link"))
	os.Symlink("b", filepath.Join(root, "link"))
	if r.Verify(context.Background(), s) == nil {
		t.Fatal("同字节祖先链接改指向不能复用")
	}
}
