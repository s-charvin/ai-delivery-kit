package workspace

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"sort"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
)

// RunOutputPaths 只描述本切片的生成输出，显式上游引用不由此从消费闭包删除。
func RunOutputPaths(w model.Workspace, artifacts map[string]string) []string {
	runs, _ := filepath.Rel(w.ProjectRoot, filepath.Join(w.DeliveryRoot, "runs"))
	return []string{".ai-delivery.lock", artifacts["verification"], filepath.ToSlash(runs)}
}

func runArtifacts(s model.Snapshot) (map[string]string, map[string]any, error) {
	body, ok := model.Fact(s, "binding")
	if !ok {
		return nil, nil, fmt.Errorf("缺少当前执行输入的 binding")
	}
	binding, err := protocol.Object(body)
	if err != nil {
		return nil, nil, err
	}
	artifacts, err := ArtifactPaths(s.Workspace(), s.Scope(), binding)
	return artifacts, binding, err
}

// KnownRunInputPaths 重算已知执行义务；不把验收读取闭包等同于执行输入。
// 其他切片的 canonical 合同只通过显式依赖进入，不因 Git 自动发现强加给本切片。
func KnownRunInputPaths(s model.Snapshot, explicit []string, design string) ([]string, error) {
	facts, err := Facts(s)
	if err != nil {
		return nil, err
	}
	artifacts, binding, err := runArtifacts(s)
	if err != nil {
		return nil, err
	}
	outputs := RunOutputPaths(s.Workspace(), artifacts)
	excluded := map[string]bool{}
	own := map[string]bool{}
	for _, p := range artifacts {
		own[p] = true
	}
	if raw, ok := model.Fact(s, "status"); ok {
		status, err := protocol.Object(raw)
		if err != nil {
			return nil, err
		}
		entries, _ := status["sub_requirements"].(map[string]any)
		for id := range entries {
			if id == s.Scope().SubrequirementID {
				continue
			}
			other, err := ArtifactPaths(s.Workspace(), model.Scope{RequirementID: s.Scope().RequirementID, SubrequirementID: id}, binding)
			if err != nil {
				return nil, err
			}
			for _, p := range other {
				if !own[p] {
					excluded[p] = true
				}
			}
		}
	}
	ownedOutput := func(p string) bool { return len(FilterRunOutputs([]string{p}, outputs)) == 0 }
	referencesOutput := func(p string) bool {
		if ownedOutput(p) {
			return true
		}
		id, ok, e := Identity(s, p)
		return e == nil && ok && ownedOutput(id.ResolvedPath)
	}
	seen := map[string]bool{}
	for _, p := range append(append([]string{}, explicit...), design) {
		normalized, err := NormalizePath(p)
		if err != nil {
			return nil, err
		}
		if referencesOutput(normalized) {
			return nil, fmt.Errorf("运行输入与自身输出冲突: %s", p)
		}
		seen[normalized] = true
	}
	for _, p := range facts.ObservedChangedPaths {
		normalized, err := NormalizePath(p)
		if err != nil {
			return nil, err
		}
		// 输出与其他切片元数据的所有权属于请求路径，生产 alias 不继承终点豁免。
		if ownedOutput(normalized) || excluded[normalized] {
			continue
		}
		if referencesOutput(normalized) {
			return nil, fmt.Errorf("生产输入路径与生成输出混用: %s", normalized)
		}
		seen[normalized] = true
	}
	paths := make([]string, 0, len(seen))
	for p := range seen {
		paths = append(paths, p)
	}
	sort.Strings(paths)
	return paths, nil
}

// RunInputIdentities 只投影候选路径的冻结终点和链接链，不读取磁盘或包含验收输出。
func RunInputIdentities(s model.Snapshot, paths []string) ([]model.FileIdentity, error) {
	known := map[string]model.FileIdentity{}
	for _, f := range s.Files() {
		known[f.Path] = f
	}
	selected := map[string]model.FileIdentity{}
	for _, p := range paths {
		normalized, err := NormalizePath(p)
		if err != nil {
			return nil, err
		}
		body, ok := s.Document(model.FileIdentityFactPrefix + normalized)
		if !ok {
			return nil, fmt.Errorf("必需执行输入身份未知: %s", p)
		}
		var reference referenceInputIdentity
		if err := json.Unmarshal(body, &reference); err != nil {
			return nil, err
		}
		if len(reference.InputPaths) == 0 {
			return nil, fmt.Errorf("必需执行输入缺少冻结解析链: %s", p)
		}
		for _, input := range reference.InputPaths {
			identity, ok := known[input]
			if !ok {
				return nil, fmt.Errorf("必需执行输入解析链未读取: %s", input)
			}
			selected[input] = identity
		}
	}
	out := make([]model.FileIdentity, 0, len(selected))
	for _, f := range selected {
		out = append(out, f)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Path < out[j].Path })
	return out, nil
}

// RunInputRoles 只把未被方法/额外输入显式依赖的 canonical status 当作运行前置。
// 所有身份在运行期间仍复核；最终验收重算角色，当前前置由正常门禁检查。
func RunInputRoles(s model.Snapshot, files []model.FileIdentity, explicit []string) (map[string]string, error) {
	roles := map[string]string{}
	for _, f := range files {
		roles[f.Path] = "execution"
	}
	facts, err := Facts(s)
	if err != nil {
		return roles, nil
	}
	statusPath := facts.Artifacts["status"]
	if artifacts, _, err := runArtifacts(s); err == nil {
		statusPath = artifacts["status"]
	}
	if statusPath == "" {
		return roles, nil
	}
	status, ok, err := Identity(s, statusPath)
	if err != nil {
		return nil, err
	}
	if !ok || status.Kind != "file" {
		return nil, fmt.Errorf("无法确定 canonical status 的真实输入身份")
	}
	for _, p := range explicit {
		normalized, err := NormalizePath(p)
		if err != nil {
			return nil, err
		}
		id, ok, err := Identity(s, normalized)
		if err != nil {
			return nil, err
		}
		if !ok {
			return nil, fmt.Errorf("明确执行输入未消费: %s", p)
		}
		if normalized == statusPath || id.ResolvedPath == status.ResolvedPath {
			return roles, nil
		}
	}
	if _, ok := roles[status.ResolvedPath]; ok {
		roles[status.ResolvedPath] = "prerequisite"
	}
	return roles, nil
}
