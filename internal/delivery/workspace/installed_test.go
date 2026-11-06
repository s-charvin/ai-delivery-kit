package workspace_test

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	"github.com/s-charvin/ai-delivery-kit/internal/bootstrap"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

func TestInstalledReaderNeverDowngradesAfterManifestRemoved(t *testing.T) {
	root := t.TempDir()
	if err := (bootstrap.Engine{}).Run(bootstrap.Config{RepoRoot: root}); err != nil {
		t.Fatal(err)
	}
	r := workspace.NewInstalledReader()
	w, err := r.Resolve(context.Background(), root, "")
	if err != nil {
		t.Fatal(err)
	}
	if err = os.Remove(filepath.Join(root, ".ai-delivery/meta/kit-assets.json")); err != nil {
		t.Fatal(err)
	}
	if _, err = r.Load(context.Background(), w, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, model.ReadRequest{Action: &model.Action{Intent: "analyze"}}); err == nil {
		t.Fatal("resolve 后删除清单仍降级为 raw reader")
	}
}

func TestInstalledResourcesAllowUnownedInstructionsButBindManagedBytes(t *testing.T) {
	root := t.TempDir()
	if err := (bootstrap.Engine{}).Run(bootstrap.Config{RepoRoot: root}); err != nil {
		t.Fatal(err)
	}
	agents := filepath.Join(root, "AGENTS.md")
	b, err := os.ReadFile(agents)
	if err != nil {
		t.Fatal(err)
	}
	if err = os.WriteFile(agents, append(b, []byte("\n用户自己的项目规范，合法修订\n")...), 0644); err != nil {
		t.Fatal(err)
	}
	r := workspace.NewInstalledReader()
	w, err := r.Resolve(context.Background(), root, "")
	if err != nil {
		t.Fatal("非受管规范误判安装损坏", err)
	}
	s, err := r.Load(context.Background(), w, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, model.ReadRequest{Action: &model.Action{Intent: "analyze"}})
	if err != nil {
		t.Fatal(err)
	}
	p := filepath.Join(root, ".agents/skills/requirement-breakdown/SKILL.md")
	if err = os.WriteFile(p, []byte("资源已替换"), 0644); err != nil {
		t.Fatal(err)
	}
	if err = r.Verify(context.Background(), s); err == nil {
		t.Fatal("受管资源漂移未使旧快照失效")
	}
	if _, err = r.Load(context.Background(), w, s.Scope(), s.Request()); err == nil {
		t.Fatal("受管资源漂移被重读接受")
	}
}
