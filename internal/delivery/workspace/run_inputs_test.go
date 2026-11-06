package workspace_test

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"testing"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

func TestRunInputIdentityProjectionKeepsFrozenAliasChainOnly(t *testing.T) {
	for _, kind := range []string{"file", "absent", "directory", "absolute-parent-alias"} {
		t.Run(kind, func(t *testing.T) {
			root := fixture(t)
			if err := os.MkdirAll(filepath.Join(root, "target"), 0755); err != nil {
				t.Fatal(err)
			}
			endpoint := "target/value"
			switch kind {
			case "file", "absolute-parent-alias":
				put(t, root, endpoint, "当前输入")
			case "directory":
				if err := os.Mkdir(filepath.Join(root, endpoint), 0755); err != nil {
					t.Fatal(err)
				}
			}
			linkTarget := "target"
			if kind == "absolute-parent-alias" {
				parentAlias := filepath.Join(t.TempDir(), "parent")
				if err := os.Symlink(filepath.Dir(root), parentAlias); err != nil {
					t.Fatal(err)
				}
				linkTarget = filepath.Join(parentAlias, filepath.Base(root), "target")
			}
			if err := os.Symlink(linkTarget, filepath.Join(root, "middle")); err != nil {
				t.Fatal(err)
			}
			if err := os.Symlink("middle", filepath.Join(root, "alias")); err != nil {
				t.Fatal(err)
			}
			put(t, root, "consumer-output.log", "验收闭包额外读取，不是该路径的执行输入")
			r := workspace.Reader{}
			w, err := r.Resolve(context.Background(), root, "")
			if err != nil {
				t.Fatal(err)
			}
			s, err := r.Load(context.Background(), w, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, model.ReadRequest{Action: &model.Action{Intent: "verify"}})
			if err != nil {
				t.Fatal(err)
			}
			s, err = r.Extend(context.Background(), s, []string{"alias/value", "consumer-output.log"})
			if err != nil {
				t.Fatal(err)
			}
			ids, err := workspace.RunInputIdentities(s, []string{"alias/value"})
			if err != nil {
				t.Fatal(err)
			}
			paths := []string{}
			for _, id := range ids {
				paths = append(paths, id.Path)
			}
			if !reflect.DeepEqual(paths, []string{"alias", "middle", "target/value"}) {
				t.Fatal("解析链丢失或混入consumer输出", paths)
			}
			if kind == "absent" && ids[2].Kind != "absent" {
				t.Fatal("删除/absence 身份丢失", ids)
			}
			if _, err := workspace.RunInputIdentities(s, []string{"not-consumed"}); err == nil {
				t.Fatal("未读取被当成合法absence")
			}
		})
	}
}

func TestRunInputOutputOwnershipUsesRequestsAndConfiguredRoot(t *testing.T) {
	for _, layout := range []string{"default", "custom", "parent-alias"} {
		t.Run(layout, func(t *testing.T) {
			root := fixture(t)
			delivery := ".ai-delivery"
			if layout != "default" {
				delivery = "nested/delivery"
				if err := os.Mkdir(filepath.Join(root, "nested"), 0755); err != nil {
					t.Fatal(err)
				}
				if err := os.Rename(filepath.Join(root, ".ai-delivery"), filepath.Join(root, delivery)); err != nil {
					t.Fatal(err)
				}
				put(t, root, delivery+"/meta/project-binding.json", `{"version":3,"ai_delivery_path":"nested/delivery"}`)
			}
			requestedRoot := root
			if layout == "parent-alias" {
				parent := filepath.Join(t.TempDir(), "parent")
				if err := os.Symlink(filepath.Dir(root), parent); err != nil {
					t.Fatal(err)
				}
				requestedRoot = filepath.Join(parent, filepath.Base(root))
			}
			design := delivery + "/requirements/R/sub-requirements/SR-001/design.md"
			verification := delivery + "/requirements/R/sub-requirements/SR-001/verification.md"
			sibling := delivery + "/requirements/R/sub-requirements/SR-002/design.md"
			receipt := delivery + "/runs/run-controlled/receipt.json"
			put(t, root, delivery+"/requirements/R/status.json", `{"_schema":"2.0","sub_requirements":{"SR-001":{"status":"in_dev"},"SR-002":{"status":"merged"}}}`)
			put(t, root, design, "当前设计")
			put(t, root, sibling, "另一切片的 canonical 设计")
			put(t, root, verification, "生成验证材料")
			put(t, root, receipt, "运行收据")
			put(t, root, "source.txt", "生产正文")
			cmd := exec.Command("git", "init", "-q", root)
			if out, err := cmd.CombinedOutput(); err != nil {
				t.Fatal(err, string(out))
			}
			r := workspace.Reader{}
			w, err := r.Resolve(context.Background(), requestedRoot, delivery)
			if err != nil {
				t.Fatal(err)
			}
			load := func(paths ...string) model.Snapshot {
				s, e := r.Load(context.Background(), w, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, model.ReadRequest{Action: &model.Action{Intent: "verify"}})
				if e != nil {
					t.Fatal(e)
				}
				s, e = r.Extend(context.Background(), s, paths)
				if e != nil {
					t.Fatal(e)
				}
				return s
			}
			contains := func(paths []string, wanted string) bool {
				for _, p := range paths {
					if p == wanted {
						return true
					}
				}
				return false
			}
			s := load(verification, receipt, sibling, "source.txt")
			paths, err := workspace.KnownRunInputPaths(s, nil, design)
			if err != nil {
				t.Fatal(err)
			}
			if contains(paths, verification) || contains(paths, receipt) || contains(paths, sibling) || !contains(paths, "source.txt") {
				t.Fatal("输出所有权或精确 sibling 分类错误", paths)
			}
			// 元数据路径本身可排除，生产 alias 不能继承其终点分类。
			if err := os.Symlink(sibling, filepath.Join(root, "metadata-alias.txt")); err != nil {
				t.Fatal(err)
			}
			s = load("metadata-alias.txt")
			paths, err = workspace.KnownRunInputPaths(s, nil, design)
			if err != nil || !contains(paths, "metadata-alias.txt") {
				t.Fatal("生产 alias 继承 sibling 豁免", paths, err)
			}
			ids, err := workspace.RunInputIdentities(s, []string{"metadata-alias.txt"})
			if err != nil {
				t.Fatal(err)
			}
			foundLink := false
			for _, id := range ids {
				foundLink = foundLink || id.Path == "metadata-alias.txt" && id.Kind == "symlink"
			}
			if !foundLink {
				t.Fatal("新的生产 alias 节点丢失", ids)
			}
			if err := os.Symlink(receipt, filepath.Join(root, "output-alias.txt")); err != nil {
				t.Fatal(err)
			}
			s = load("output-alias.txt")
			if _, err := workspace.KnownRunInputPaths(s, nil, design); err == nil {
				t.Fatal("生产 alias 静默继承生成输出豁免")
			}
			if _, err := workspace.KnownRunInputPaths(s, []string{"output-alias.txt"}, design); err == nil {
				t.Fatal("显式 alias 未拒绝输入输出冲突")
			}
		})
	}
}
