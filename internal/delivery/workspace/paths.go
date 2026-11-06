package workspace

import (
	"context"
	"crypto/sha256"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/s-charvin/ai-delivery-kit/internal/assets"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
)

// Reader 零值用于低层原始协议调查；真实命令用 NewInstalledReader，所有读取保持安装要求。
type Reader struct{ requireInstalledResources bool }

var _ model.WorkspaceReader = Reader{}

func (r Reader) Resolve(ctx context.Context, project, deliveryRoot string) (model.Workspace, error) {
	explicit := project != ""
	if project == "" {
		var err error
		project, err = os.Getwd()
		if err != nil {
			return model.Workspace{}, err
		}
	}
	root, err := filepath.Abs(project)
	if err != nil {
		return model.Workspace{}, err
	}
	info, err := os.Stat(root)
	if err != nil || !info.IsDir() {
		return model.Workspace{}, fmt.Errorf("项目根不是目录: %s", root)
	}
	var candidates []string
	for count := 0; count < 64; count++ {
		if err := ctx.Err(); err != nil {
			return model.Workspace{}, err
		}
		if deliveryRoot != "" {
			p := deliveryRoot
			if filepath.IsAbs(p) {
				if !inside(root, p) {
					return model.Workspace{}, fmt.Errorf("治理根超出项目")
				}
			} else {
				rel, err := NormalizePath(p)
				if err != nil {
					return model.Workspace{}, err
				}
				p = filepath.Join(root, rel)
			}
			candidates = []string{p}
		} else {
			entries, err := os.ReadDir(root)
			if err != nil {
				return model.Workspace{}, err
			}
			for _, entry := range entries {
				if entry.Name() == ".ai-delivery-backups" {
					continue
				}
				p := filepath.Join(root, entry.Name())
				if _, err := os.Lstat(filepath.Join(p, "meta/project-binding.json")); err == nil {
					candidates = append(candidates, p)
				}
			}
		}
		if len(candidates) > 0 || explicit || filepath.Dir(root) == root {
			break
		}
		root = filepath.Dir(root)
	}
	if len(candidates) != 1 {
		return model.Workspace{}, fmt.Errorf("治理根候选数为 %d；请显式指定 --project 和 --delivery-root（项目须先初始化）", len(candidates))
	}
	ad := candidates[0]
	rel, _ := filepath.Rel(root, filepath.Join(ad, "meta/project-binding.json"))
	c := newConsumption(root)
	body, ok, err := c.read(ctx, filepath.ToSlash(rel))
	if err != nil {
		return model.Workspace{}, err
	}
	if !ok {
		return model.Workspace{}, fmt.Errorf("缺少项目 binding: %s", rel)
	}
	binding, err := protocol.Object(body)
	if err != nil {
		return model.Workspace{}, &protocol.FormatError{Path: filepath.ToSlash(rel), Cause: err}
	}
	if !explicit {
		declared := ".ai-delivery"
		if value, ok := binding["ai_delivery_path"].(string); ok {
			declared = value
		}
		if !protocol.SafeMetadataTemplate(declared) {
			return model.Workspace{}, fmt.Errorf("非法 ai_delivery_path")
		}
		inferred := ad
		for range strings.Split(filepath.ToSlash(filepath.Clean(declared)), "/") {
			inferred = filepath.Dir(inferred)
		}
		if filepath.Join(inferred, declared) != ad {
			return model.Workspace{}, fmt.Errorf("binding 实际位置与 ai_delivery_path 不一致")
		}
		root = inferred
	}
	if err := validateBinding(binding, root, ad); err != nil {
		return model.Workspace{}, &protocol.FormatError{Path: filepath.ToSlash(rel), Cause: err}
	}
	exe, err := os.Executable()
	if err != nil {
		return model.Workspace{}, err
	}
	program, err := os.ReadFile(exe)
	if err != nil {
		return model.Workspace{}, err
	}
	resources, err := ResourceDigest()
	if err != nil {
		return model.Workspace{}, err
	}
	w := model.Workspace{ProjectRoot: root, DeliveryRoot: ad, ProgramPath: exe, ProgramID: fmt.Sprintf("%x", sha256.Sum256(program)), ProtocolDigest: protocol.Digest(), ResourceDigest: resources}
	if r.requireInstalledResources {
		deliveryRel, _ := filepath.Rel(root, ad)
		c := newConsumption(root)
		if err := assets.Verify(filepath.ToSlash(deliveryRel), func(p string) ([]byte, bool, error) { return c.read(ctx, p) }); err != nil {
			return model.Workspace{}, err
		}
	}
	return w, nil
}

func validateBinding(binding map[string]any, root, ad string) error {
	if err := protocol.ValidateMetadata("binding", binding); err != nil {
		return err
	}
	path := ".ai-delivery"
	if v, ok := binding["ai_delivery_path"].(string); ok {
		path = v
	}
	if filepath.Clean(filepath.Join(root, path)) != filepath.Clean(ad) {
		return fmt.Errorf("binding 实际位置与 ai_delivery_path 不一致")
	}
	_, err := Layout(binding)
	return err
}

// Layout 仅合并当前绑定格式，返回独立默认值；不迁移历史格式。
func Layout(binding map[string]any) (map[string]any, error) {
	if err := protocol.ValidateMetadata("binding", binding); err != nil {
		return nil, err
	}
	layout := protocol.Defaults("binding")["layout"].(map[string]any)
	configured, _ := binding["layout"].(map[string]any)
	for key, value := range configured {
		current, ok := layout[key]
		if !ok {
			return nil, fmt.Errorf("未知 layout 键: %s", key)
		}
		if m, ok := current.(map[string]any); ok {
			given, ok := value.(map[string]any)
			if !ok {
				return nil, fmt.Errorf("layout.%s 必须是对象", key)
			}
			for k, v := range given {
				if _, ok := m[k]; !ok {
					return nil, fmt.Errorf("未知产物: %s", k)
				}
				m[k] = v
			}
		} else {
			layout[key] = value
		}
	}
	return layout, nil
}
func safeID(id string) bool {
	if id == "" || id == "." || id == ".." || strings.ContainsAny(id, "/\\:") {
		return false
	}
	for _, r := range id {
		if r < 32 {
			return false
		}
	}
	return true
}

func ValidateScope(scope model.Scope) error {
	if !safeID(scope.RequirementID) || !safeID(scope.SubrequirementID) {
		return fmt.Errorf("需求和切片 ID 必须为非路径 ID")
	}
	return nil
}

// ArtifactPaths 返回 repo-relative POSIX 路径；实际读取仍须经过 Reader。
func ArtifactPaths(w model.Workspace, scope model.Scope, binding map[string]any) (map[string]string, error) {
	if err := ValidateScope(scope); err != nil {
		return nil, err
	}
	layout, err := Layout(binding)
	if err != nil {
		return nil, err
	}
	result := map[string]string{}
	groups := []map[string]any{layout["project_artifacts"].(map[string]any), layout["requirement_artifacts"].(map[string]any), layout["sub_requirement_artifacts"].(map[string]any), {"requirement_root": layout["requirement_root"], "sub_requirement_dir": layout["sub_requirement_dir"]}}
	for _, group := range groups {
		for kind, v := range group {
			template := v.(string)
			var b strings.Builder
			for i := 0; i < len(template); {
				if i+1 < len(template) && template[i:i+2] == "{{" {
					b.WriteByte('{')
					i += 2
					continue
				}
				if i+1 < len(template) && template[i:i+2] == "}}" {
					b.WriteByte('}')
					i += 2
					continue
				}
				if template[i] == '{' {
					end := strings.IndexByte(template[i:], '}')
					token := template[i+1 : i+end]
					switch token {
					case "req_id":
						b.WriteString(scope.RequirementID)
					case "sr_id":
						b.WriteString(scope.SubrequirementID)
					default:
						return nil, fmt.Errorf("产物 %s 需要当前范围未提供的 %s", kind, token)
					}
					i += end + 1
					continue
				}
				b.WriteByte(template[i])
				i++
			}
			rel, err := NormalizePath(b.String())
			if err != nil {
				return nil, err
			}
			full := filepath.Join(w.DeliveryRoot, rel)
			if !inside(w.DeliveryRoot, full) {
				return nil, fmt.Errorf("产物越出治理根")
			}
			p, err := filepath.Rel(w.ProjectRoot, full)
			if err != nil {
				return nil, err
			}
			result[kind] = filepath.ToSlash(p)
		}
	}
	return result, nil
}
