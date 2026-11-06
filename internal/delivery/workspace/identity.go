package workspace

import (
	"context"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
	"unicode/utf8"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
)

// NormalizePath 是声明范围、来源与消费器共用的项目相对 POSIX 路径入口。
// 目录尾斜线是调用方的选择提示，不属于正文索引键。
func NormalizePath(value string) (string, error) {
	if value == "" || !utf8.ValidString(value) || strings.ContainsRune(value, 0) || strings.ContainsAny(value, "\\:") || filepath.IsAbs(value) || filepath.VolumeName(value) != "" {
		return "", fmt.Errorf("非法项目相对路径: %q", value)
	}
	for _, part := range strings.Split(value, "/") {
		if part == ".." {
			return "", fmt.Errorf("路径不能含 ..: %q", value)
		}
	}
	return filepath.ToSlash(filepath.Clean(value)), nil
}
func inside(root, path string) bool {
	rel, err := filepath.Rel(root, path)
	return err == nil && rel != ".." && !strings.HasPrefix(rel, ".."+string(filepath.Separator))
}

// Identity 返回请求路径的冻结终点身份；未读取与合法 absence 明确区分。
func Identity(s model.Snapshot, value string) (model.FileIdentity, bool, error) {
	p, err := NormalizePath(value)
	if err != nil {
		return model.FileIdentity{}, false, err
	}
	b, ok := s.Document(model.FileIdentityFactPrefix + p)
	if !ok {
		return model.FileIdentity{}, false, nil
	}
	var id model.FileIdentity
	if err := json.Unmarshal(b, &id); err != nil {
		return id, false, err
	}
	return id, true, nil
}

type referenceInputIdentity struct {
	model.FileIdentity
	InputPaths []string `json:"input_paths"`
}

func (c *consumption) referenceIdentity(request string, id model.FileIdentity, links map[string]bool) error {
	id.Path = request
	inputs := []string{id.ResolvedPath}
	for p := range links {
		rel, err := filepath.Rel(c.root, p)
		if err != nil {
			return err
		}
		inputs = append(inputs, filepath.ToSlash(rel))
	}
	sort.Strings(inputs)
	body, err := json.Marshal(referenceInputIdentity{FileIdentity: id, InputPaths: inputs})
	if err != nil {
		return err
	}
	c.documents[model.FileIdentityFactPrefix+request] = body
	return nil
}

type consumption struct {
	root          string
	requestedRoot string
	rootError     error
	files         map[string]model.FileIdentity
	documents     map[string][]byte
}

func newConsumption(root string) *consumption {
	physical, err := filepath.EvalSymlinks(root)
	return &consumption{root: physical, requestedRoot: root, rootError: err, files: map[string]model.FileIdentity{}, documents: map[string][]byte{}}
}
func (c *consumption) record(id model.FileIdentity) error {
	if old, exists := c.files[id.Path]; exists {
		if !reflect.DeepEqual(old, id) {
			return fmt.Errorf("同次消费输入已漂移: %s", id.Path)
		}
	} else if len(c.files) >= 10000 {
		return fmt.Errorf("消费文件数超过 10000")
	}
	c.files[id.Path] = id
	return nil
}
func (c *consumption) read(ctx context.Context, relative string) ([]byte, bool, error) {
	rel, err := NormalizePath(relative)
	if err != nil {
		return nil, false, err
	}
	links := map[string]bool{}
	resolved, exists, err := c.resolve(ctx, filepath.Join(c.root, filepath.FromSlash(rel)), 0, links)
	if err != nil {
		return nil, false, err
	}
	if !exists {
		id := model.FileIdentity{Path: resolved, Kind: "absent", ResolvedPath: resolved}
		if err := c.record(id); err != nil {
			return nil, false, err
		}
		return nil, false, c.referenceIdentity(rel, id, links)
	}
	path := filepath.Join(c.root, filepath.FromSlash(resolved))
	before, err := os.Lstat(path)
	if err != nil {
		return nil, false, err
	}
	mode := uint32(before.Mode())
	id := model.FileIdentity{Path: resolved, ResolvedPath: resolved, Mode: &mode}
	if before.IsDir() {
		id.Kind = "directory"
		if err := c.record(id); err != nil {
			return nil, false, err
		}
		return nil, false, c.referenceIdentity(rel, id, links)
	}
	if !before.Mode().IsRegular() {
		return nil, false, fmt.Errorf("来源不是常规文件: %s", rel)
	}
	body, err := os.ReadFile(path)
	if err != nil {
		return nil, false, err
	}
	after, err := os.Lstat(path)
	if err != nil {
		return nil, false, err
	}
	if !os.SameFile(before, after) || before.Size() != after.Size() || before.ModTime() != after.ModTime() || before.Mode() != after.Mode() {
		return nil, false, fmt.Errorf("读取时输入漂移: %s", rel)
	}
	digest := fmt.Sprintf("%x", sha256.Sum256(body))
	id.Kind = "file"
	id.SHA256 = &digest
	if err := c.record(id); err != nil {
		return nil, false, err
	}
	c.documents[rel] = body
	return body, true, c.referenceIdentity(rel, id, links)
}
func (c *consumption) resolve(ctx context.Context, path string, depth int, seen map[string]bool) (string, bool, error) {
	if c.rootError != nil {
		return "", false, c.rootError
	}
	if err := ctx.Err(); err != nil {
		return "", false, err
	}
	if depth > 64 {
		return "", false, fmt.Errorf("链接深度超过 64: %s", path)
	}
	if !inside(c.root, path) {
		return "", false, fmt.Errorf("来源超出项目: %s", path)
	}
	rel, _ := filepath.Rel(c.root, path)
	parts := strings.Split(rel, string(filepath.Separator))
	current := c.root
	for i, part := range parts {
		current = filepath.Join(current, part)
		info, err := os.Lstat(current)
		if os.IsNotExist(err) {
			return filepath.ToSlash(rel), false, nil
		}
		if err != nil {
			return "", false, err
		}
		if info.Mode()&os.ModeSymlink == 0 {
			continue
		}
		if seen[current] {
			return "", false, fmt.Errorf("符号链接环: %s", current)
		}
		seen[current] = true
		target, err := os.Readlink(current)
		if err != nil {
			return "", false, err
		}
		name, _ := filepath.Rel(c.root, current)
		mode := uint32(info.Mode())
		if err := c.record(model.FileIdentity{Path: filepath.ToSlash(name), Kind: "symlink", Mode: &mode, LinkTarget: &target}); err != nil {
			return "", false, err
		}
		dest := target
		if !filepath.IsAbs(dest) {
			dest = filepath.Join(filepath.Dir(current), dest)
		}
		dest = filepath.Clean(dest)
		if !inside(c.root, dest) && filepath.IsAbs(target) {
			dest = c.physicalProjectPath(dest)
		}
		if !inside(c.root, dest) {
			return "", false, fmt.Errorf("符号链接超出项目: %s", current)
		}
		if i+1 < len(parts) {
			dest = filepath.Join(dest, filepath.Join(parts[i+1:]...))
		}
		return c.resolve(ctx, dest, depth+1, seen)
	}
	return filepath.ToSlash(rel), true, nil
}

// 只统一项目边界以上的别名，保留项目内部的每个链接节点供 resolve 登记。
func (c *consumption) physicalProjectPath(target string) string {
	if inside(c.requestedRoot, target) {
		rel, _ := filepath.Rel(c.requestedRoot, target)
		return filepath.Join(c.root, rel)
	}
	for candidate, depth := target, 0; depth < 64; candidate, depth = filepath.Dir(candidate), depth+1 {
		if filepath.Base(candidate) == filepath.Base(c.root) {
			parent, err := filepath.EvalSymlinks(filepath.Dir(candidate))
			if err == nil && filepath.Join(parent, filepath.Base(candidate)) == c.root {
				rel, _ := filepath.Rel(candidate, target)
				return filepath.Join(c.root, rel)
			}
		}
		if filepath.Dir(candidate) == candidate {
			break
		}
	}
	return target
}
func (c *consumption) identities() []model.FileIdentity {
	files := make([]model.FileIdentity, 0, len(c.files))
	for _, f := range c.files {
		files = append(files, f)
	}
	return files
}

func (c *consumption) observeScope(ctx context.Context, value string) (ScopePathFact, error) {
	rel, err := NormalizePath(value)
	if err != nil {
		return ScopePathFact{}, err
	}
	resolved, exists, err := c.resolve(ctx, filepath.Join(c.root, rel), 0, map[string]bool{})
	if err != nil {
		return ScopePathFact{}, err
	}
	fact := ScopePathFact{Path: rel, ResolvedPath: resolved, Kind: "absent"}
	if !exists {
		return fact, nil
	}
	info, err := os.Lstat(filepath.Join(c.root, resolved))
	if err != nil {
		return ScopePathFact{}, err
	}
	switch {
	case info.IsDir():
		fact.Kind = "directory"
	case info.Mode().IsRegular():
		fact.Kind = "file"
	default:
		return ScopePathFact{}, fmt.Errorf("范围不是普通文件或目录: %s", rel)
	}
	return fact, nil
}

// Extend 在同一消费闭包中增补正文；前后复核拒绝混合不同时刻的输入。
func (r Reader) Extend(ctx context.Context, s model.Snapshot, paths []string) (model.Snapshot, error) {
	v, ok := s.(*snapshot)
	if !ok {
		return nil, fmt.Errorf("需要 workspace 快照")
	}
	if err := r.verifyFiles(ctx, s); err != nil {
		return nil, err
	}
	c := newConsumption(v.workspace.ProjectRoot)
	for k, b := range v.documents {
		c.documents[k] = append([]byte(nil), b...)
	}
	for _, f := range v.files {
		c.files[f.Path] = f
	}
	for _, value := range paths {
		p, err := NormalizePath(value)
		if err != nil {
			return nil, err
		}
		if _, done := c.documents[p]; done {
			continue
		}
		if inside(v.workspace.DeliveryRoot, filepath.Join(v.workspace.ProjectRoot, p)) {
			if err := governedPath(ctx, c, v.workspace, p); err != nil {
				return nil, err
			}
		}
		if _, _, err := c.read(ctx, p); err != nil {
			return nil, err
		}
		if len(c.files) > 10000 {
			return nil, fmt.Errorf("消费文件数超过 10000")
		}
	}
	result, err := NewSnapshot(v.workspace, v.scope, v.request, c.documents, c.identities(), v.diagnostics)
	if err != nil {
		return nil, err
	}
	if err := r.verifyFiles(ctx, result); err != nil {
		return nil, err
	}
	return result, nil
}
func (r Reader) Verify(ctx context.Context, s model.Snapshot) error {
	return r.verifyPublication(ctx, s, "")
}

// VerifyPublication 仅忽略本次原子发布拥有的精确暂存路径，消费文件仍完整复核。
func (r Reader) VerifyPublication(ctx context.Context, s model.Snapshot, temporaryPath string) error {
	rel, err := filepath.Rel(s.Workspace().ProjectRoot, temporaryPath)
	if err != nil {
		return err
	}
	rel, err = NormalizePath(filepath.ToSlash(rel))
	if err != nil {
		return err
	}
	facts, err := Facts(s)
	if err != nil {
		return err
	}
	allowedDir := filepath.Dir(rel) == filepath.Dir(facts.Artifacts["status"])
	for _, output := range facts.ArchiveOutputPaths {
		allowedDir = allowedDir || filepath.Dir(rel) == filepath.Dir(output)
	}
	if !allowedDir || !strings.HasPrefix(filepath.Base(rel), ".ai-delivery-write-") {
		return fmt.Errorf("发布豁免仅限 status 同目录的唯一暂存文件")
	}
	for _, f := range s.Files() {
		if f.Path == rel || f.ResolvedPath == rel {
			return fmt.Errorf("暂存路径不能是已消费输入")
		}
	}
	info, err := os.Lstat(temporaryPath)
	if err != nil {
		return err
	}
	if !info.Mode().IsRegular() {
		return fmt.Errorf("发布暂存路径必须是普通文件")
	}
	return r.verifyPublication(ctx, s, rel)
}

func (r Reader) verifyPublication(ctx context.Context, s model.Snapshot, temporaryPath string) error {
	if err := r.verifyFiles(ctx, s); err != nil {
		return err
	}
	if facts, err := Facts(s); err == nil && facts.GitChangesKnown && !facts.Historical {
		observed, known, err := ObservedChanges(ctx, s.Workspace().ProjectRoot)
		if err != nil {
			return err
		}
		if temporaryPath != "" {
			filtered := []string{}
			for _, p := range observed {
				if p != temporaryPath {
					filtered = append(filtered, p)
				}
			}
			observed = filtered
		}
		if !known || !reflect.DeepEqual(FilterExactOutputs(FilterRunOutputs(observed, facts.RunOutputPaths), facts.ArchiveOutputPaths), facts.ObservedChangedPaths) {
			return fmt.Errorf("实际 Git 阅读范围已漂移，请重新生成快照")
		}
	}
	return nil
}

func FilterExactOutputs(paths, outputs []string) []string {
	out := []string{}
	for _, p := range paths {
		skip := false
		for _, o := range outputs {
			skip = skip || p == o
		}
		if !skip {
			out = append(out, p)
		}
	}
	return out
}

// FilterRunOutputs 只排除 reader 冻结的执行输出路径，不忽略任意生产目录。
func FilterRunOutputs(paths, outputs []string) []string {
	out := []string{}
	for _, p := range paths {
		excluded := false
		for _, output := range outputs {
			if p == output || strings.HasPrefix(p, output+"/") {
				excluded = true
				break
			}
		}
		if !excluded {
			out = append(out, p)
		}
	}
	return out
}

// CaptureFiles 重新观察明确的执行输入；不把运行日志产生的 Git 变更加入输入。
// 调用者仍须单独复核实际生产变更范围，不能据此声称已发现宿主的完整依赖。
func (r Reader) CaptureFiles(ctx context.Context, w model.Workspace, paths []string) ([]model.FileIdentity, error) {
	c := newConsumption(w.ProjectRoot)
	for _, p := range paths {
		if _, _, err := c.read(ctx, p); err != nil {
			return nil, err
		}
	}
	out := c.identities()
	sort.Slice(out, func(i, j int) bool { return out[i].Path < out[j].Path })
	return out, nil
}
func (r Reader) verifyFiles(ctx context.Context, s model.Snapshot) error {
	c := newConsumption(s.Workspace().ProjectRoot)
	if c.rootError != nil {
		return c.rootError
	}
	if facts, err := Facts(s); err == nil && facts.ProjectRootResolved != c.root {
		return fmt.Errorf("项目物理根已漂移")
	}
	for _, expected := range s.Files() {
		if _, _, err := c.read(ctx, expected.Path); err != nil {
			return err
		}
	}
	for _, expected := range s.Files() {
		actual, ok := c.files[expected.Path]
		if !ok || !reflect.DeepEqual(expected, actual) {
			return fmt.Errorf("消费输入已漂移: %s", expected.Path)
		}
	}
	if facts, err := Facts(s); err == nil {
		for _, expected := range facts.ScopePaths {
			actual, err := c.observeScope(ctx, expected.Path)
			if err != nil {
				return err
			}
			if actual != expected {
				return fmt.Errorf("范围选择事实已漂移: %s", expected.Path)
			}
		}
	}
	return nil
}
