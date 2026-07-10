package bootstrap

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"
)

const (
	uiContractHookMarker = "validate-ui-contract.sh"
	ideGateBackupKeep    = 3
	ideGateBackupRelRoot = ".ai-delivery/backups/ide-gates"
)

// AmendReport 记录一次 IDE gate JSON 的 amend 结果，供 CLI 提示恢复入口。
type AmendReport struct {
	BackupStamp string   // 备份时间戳目录名；无备份时为空
	BackupDir   string   // 备份目录绝对路径
	Files       []string // 被备份并 amend 的项目相对路径
}

func (r AmendReport) Empty() bool {
	return len(r.Files) == 0
}

// amendSession 绑定单次 bootstrap / reapply 过程，共享同一备份时间戳。
type amendSession struct {
	repoRoot string
	stamp    string
	report   *AmendReport
	now      func() time.Time
}

func newAmendSession(repoRoot string, now func() time.Time, report *AmendReport) *amendSession {
	if now == nil {
		now = time.Now
	}
	if report == nil {
		report = &AmendReport{}
	}
	return &amendSession{
		repoRoot: repoRoot,
		now:      now,
		report:   report,
	}
}

func isAmendableJSONTarget(target string) bool {
	switch filepath.ToSlash(target) {
	case ".cursor/hooks.json", ".claude/settings.json", ".codex/hooks.json":
		return true
	default:
		return false
	}
}

func isAmendableAgentsMDTarget(target string) bool {
	return filepath.ToSlash(target) == "AGENTS.md"
}

func isAmendableCodexConfigTarget(target string) bool {
	return filepath.ToSlash(target) == ".codex/config.toml"
}

func isAmendableManagedTarget(target string) bool {
	return isAmendableJSONTarget(target) ||
		isAmendableAgentsMDTarget(target) ||
		isAmendableCodexConfigTarget(target)
}

func amendableManagedTargets() []string {
	return []string{
		".cursor/hooks.json",
		".claude/settings.json",
		".codex/hooks.json",
		".codex/config.toml",
		"AGENTS.md",
	}
}

// mergeAmendableJSON 将 kit 门禁配置合并进已有项目 JSON，
// 不删除无关顶层字段与外来 hook 条目。
func mergeAmendableJSON(existing, desired []byte) ([]byte, error) {
	desiredObj := map[string]any{}
	if err := json.Unmarshal(desired, &desiredObj); err != nil {
		return nil, fmt.Errorf("parse desired gate json: %w", err)
	}

	existingObj := map[string]any{}
	if len(bytes.TrimSpace(existing)) == 0 {
		existingObj = map[string]any{}
	} else if err := json.Unmarshal(existing, &existingObj); err != nil {
		return nil, fmt.Errorf("parse existing gate json: %w", err)
	}

	desiredHooks, _ := desiredObj["hooks"].(map[string]any)
	existingHooks, _ := existingObj["hooks"].(map[string]any)
	if existingHooks == nil {
		existingHooks = map[string]any{}
	}
	if desiredHooks == nil {
		desiredHooks = map[string]any{}
	}

	for event, desiredValue := range desiredHooks {
		desiredGroups, ok := desiredValue.([]any)
		if !ok {
			existingHooks[event] = desiredValue
			continue
		}
		existingGroups, _ := existingHooks[event].([]any)
		existingHooks[event] = upsertHookGroups(existingGroups, desiredGroups)
	}
	existingObj["hooks"] = existingHooks

	// Cursor hooks.json：已有文件无 version 时补上 desired 的 version。
	if _, ok := existingObj["version"]; !ok {
		if version, ok := desiredObj["version"]; ok {
			existingObj["version"] = version
		}
	}

	out, err := json.MarshalIndent(existingObj, "", "  ")
	if err != nil {
		return nil, err
	}
	return append(out, '\n'), nil
}

func upsertHookGroups(existing, desired []any) []any {
	result := append([]any{}, existing...)
	for _, desiredGroup := range desired {
		desiredMap, ok := desiredGroup.(map[string]any)
		if !ok {
			result = append(result, desiredGroup)
			continue
		}
		replaced := false
		for i, existingGroup := range result {
			existingMap, ok := existingGroup.(map[string]any)
			if !ok {
				continue
			}
			if hookGroupOwnsUIContractGate(existingMap) {
				result[i] = desiredMap
				replaced = true
				break
			}
		}
		if !replaced {
			result = append(result, desiredMap)
		}
	}
	return result
}

func hookGroupOwnsUIContractGate(group map[string]any) bool {
	if commandContainsMarker(group["command"]) {
		return true
	}
	hooks, ok := group["hooks"].([]any)
	if !ok {
		return false
	}
	for _, hook := range hooks {
		hookMap, ok := hook.(map[string]any)
		if !ok {
			continue
		}
		if commandContainsMarker(hookMap["command"]) {
			return true
		}
	}
	return false
}

func commandContainsMarker(value any) bool {
	command, ok := value.(string)
	if !ok {
		return false
	}
	return strings.Contains(command, uiContractHookMarker)
}

// writeAmendableJSON 合并写入 amendable IDE JSON：
// 已有文件先备份，再原子写；首次创建不备份。
func (s *amendSession) writeAmendableJSON(relTarget, absTarget string, desired []byte) error {
	existing, err := os.ReadFile(absTarget)
	if err != nil {
		if !os.IsNotExist(err) {
			return fmt.Errorf("read %s: %w", absTarget, err)
		}
		existing = nil
	}

	merged, err := mergeAmendableJSON(existing, desired)
	if err != nil {
		return fmt.Errorf("merge %s: %w", absTarget, err)
	}

	if existing != nil {
		if err := s.backupExisting(relTarget, absTarget, existing); err != nil {
			return err
		}
	}

	if err := atomicWriteFile(absTarget, merged, 0o644); err != nil {
		return fmt.Errorf("write %s: %w", absTarget, err)
	}
	return nil
}

const (
	agentsGateStart = "<!-- ai-delivery:ui-contract-gate:start -->"
	agentsGateEnd   = "<!-- ai-delivery:ui-contract-gate:end -->"
)

// writeAmendableAgentsMD 将 kit 门禁段落 upsert 进 AGENTS.md（Codex 官方指令入口）。
func (s *amendSession) writeAmendableAgentsMD(relTarget, absTarget string, desired []byte) error {
	existing, err := os.ReadFile(absTarget)
	if err != nil {
		if !os.IsNotExist(err) {
			return fmt.Errorf("read %s: %w", absTarget, err)
		}
		existing = nil
	}

	merged := upsertAgentsMDSection(existing, desired)
	if existing != nil && bytes.Equal(existing, merged) {
		return nil
	}
	if existing != nil {
		if err := s.backupExisting(relTarget, absTarget, existing); err != nil {
			return err
		}
	}
	if err := atomicWriteFile(absTarget, merged, 0o644); err != nil {
		return fmt.Errorf("write %s: %w", absTarget, err)
	}
	return nil
}

func upsertAgentsMDSection(existing, desired []byte) []byte {
	section := bytes.TrimSpace(desired)
	if !bytes.Contains(section, []byte(agentsGateStart)) {
		section = []byte(agentsGateStart + "\n" + string(section) + "\n" + agentsGateEnd)
	}
	section = append(bytes.TrimRight(section, "\n"), '\n')

	if len(bytes.TrimSpace(existing)) == 0 {
		return section
	}

	start := bytes.Index(existing, []byte(agentsGateStart))
	end := bytes.Index(existing, []byte(agentsGateEnd))
	if start >= 0 && end > start {
		end += len(agentsGateEnd)
		for end < len(existing) && (existing[end] == '\n' || existing[end] == '\r') {
			end++
		}
		var out bytes.Buffer
		out.Write(existing[:start])
		out.Write(section)
		if !bytes.HasSuffix(section, []byte("\n")) {
			out.WriteByte('\n')
		}
		out.Write(existing[end:])
		return out.Bytes()
	}

	var out bytes.Buffer
	out.Write(bytes.TrimRight(existing, "\n"))
	out.WriteString("\n\n")
	out.Write(section)
	return out.Bytes()
}

// writeAmendableCodexConfig 确保项目 .codex/config.toml 开启 hooks。
func (s *amendSession) writeAmendableCodexConfig(relTarget, absTarget string, desired []byte) error {
	existing, err := os.ReadFile(absTarget)
	if err != nil {
		if !os.IsNotExist(err) {
			return fmt.Errorf("read %s: %w", absTarget, err)
		}
		existing = nil
	}

	merged := ensureCodexHooksEnabled(existing, desired)
	if existing != nil && bytes.Equal(existing, merged) {
		return nil
	}
	if existing != nil {
		if err := s.backupExisting(relTarget, absTarget, existing); err != nil {
			return err
		}
	}
	if err := atomicWriteFile(absTarget, merged, 0o644); err != nil {
		return fmt.Errorf("write %s: %w", absTarget, err)
	}
	return nil
}

var (
	codexHooksTrueRE  = regexp.MustCompile(`(?m)^\s*hooks\s*=\s*true\s*$`)
	codexHooksFalseRE = regexp.MustCompile(`(?m)^(\s*hooks\s*=\s*)false(\s*)$`)
)

func ensureCodexHooksEnabled(existing, desired []byte) []byte {
	if len(bytes.TrimSpace(existing)) == 0 {
		out := bytes.TrimRight(desired, "\n")
		return append(out, '\n')
	}
	if codexHooksTrueRE.Match(existing) {
		return existing
	}
	if codexHooksFalseRE.Match(existing) {
		return codexHooksFalseRE.ReplaceAll(existing, []byte(`${1}true${2}`))
	}
	var out bytes.Buffer
	out.Write(bytes.TrimRight(existing, "\n"))
	out.WriteString("\n\n# ai-delivery-kit: enable Codex project hooks\n[features]\nhooks = true\n")
	return out.Bytes()
}

func (s *amendSession) backupExisting(relTarget, absTarget string, existing []byte) error {
	if s.stamp == "" {
		s.stamp = s.now().UTC().Format("2006-01-02T15-04-05Z")
	}
	backupRoot := filepath.Join(s.repoRoot, filepath.FromSlash(ideGateBackupRelRoot), s.stamp)
	dest := filepath.Join(backupRoot, filepath.FromSlash(relTarget))
	if err := os.MkdirAll(filepath.Dir(dest), 0o755); err != nil {
		return fmt.Errorf("create backup dir for %s: %w", relTarget, err)
	}
	if err := os.WriteFile(dest, existing, 0o644); err != nil {
		return fmt.Errorf("backup %s: %w", absTarget, err)
	}

	s.report.BackupStamp = s.stamp
	s.report.BackupDir = backupRoot
	s.report.Files = appendUnique(s.report.Files, filepath.ToSlash(relTarget))

	if err := pruneIDEGateBackups(s.repoRoot, ideGateBackupKeep); err != nil {
		return err
	}
	return nil
}

func appendUnique(items []string, value string) []string {
	for _, item := range items {
		if item == value {
			return items
		}
	}
	return append(items, value)
}

func atomicWriteFile(target string, body []byte, mode os.FileMode) error {
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		return err
	}
	tmp := target + ".tmp"
	if err := os.WriteFile(tmp, body, mode); err != nil {
		return err
	}
	if err := os.Rename(tmp, target); err != nil {
		_ = os.Remove(tmp)
		return err
	}
	return nil
}

func pruneIDEGateBackups(repoRoot string, keep int) error {
	root := filepath.Join(repoRoot, filepath.FromSlash(ideGateBackupRelRoot))
	entries, err := os.ReadDir(root)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return fmt.Errorf("list backups: %w", err)
	}

	var stamps []string
	for _, entry := range entries {
		if entry.IsDir() {
			stamps = append(stamps, entry.Name())
		}
	}
	sort.Sort(sort.Reverse(sort.StringSlice(stamps)))
	if len(stamps) <= keep {
		return nil
	}
	for _, stamp := range stamps[keep:] {
		if err := os.RemoveAll(filepath.Join(root, stamp)); err != nil {
			return fmt.Errorf("prune backup %s: %w", stamp, err)
		}
	}
	return nil
}

// ListIDEGateBackups 返回备份时间戳，最新在前。
func ListIDEGateBackups(repoRoot string) ([]string, error) {
	root := filepath.Join(repoRoot, filepath.FromSlash(ideGateBackupRelRoot))
	entries, err := os.ReadDir(root)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, fmt.Errorf("list backups: %w", err)
	}
	var stamps []string
	for _, entry := range entries {
		if entry.IsDir() {
			stamps = append(stamps, entry.Name())
		}
	}
	sort.Sort(sort.Reverse(sort.StringSlice(stamps)))
	return stamps, nil
}

// RestoreIDEGateBackup 从指定时间戳恢复 amendable IDE 配置与 AGENTS.md。
// 恢复前会先备份当前文件（再给一次回滚机会）。
func RestoreIDEGateBackup(repoRoot, stamp string, now func() time.Time) (AmendReport, error) {
	report := AmendReport{}
	if repoRoot == "" {
		return report, fmt.Errorf("repo root is required")
	}
	root := filepath.Clean(repoRoot)
	if !filepath.IsAbs(root) {
		abs, err := filepath.Abs(root)
		if err != nil {
			return report, err
		}
		root = abs
	}

	backupRoot := filepath.Join(root, filepath.FromSlash(ideGateBackupRelRoot), stamp)
	st, err := os.Stat(backupRoot)
	if err != nil {
		return report, fmt.Errorf("backup %s not found: %w", stamp, err)
	}
	if !st.IsDir() {
		return report, fmt.Errorf("backup %s is not a directory", stamp)
	}

	session := newAmendSession(root, now, &report)
	restored := 0
	for _, rel := range amendableManagedTargets() {
		src := filepath.Join(backupRoot, filepath.FromSlash(rel))
		body, err := os.ReadFile(src)
		if err != nil {
			if os.IsNotExist(err) {
				continue
			}
			return report, fmt.Errorf("read backup %s: %w", rel, err)
		}
		dest := filepath.Join(root, filepath.FromSlash(rel))
		if current, err := os.ReadFile(dest); err == nil {
			if err := session.backupExisting(rel, dest, current); err != nil {
				return report, err
			}
		} else if !os.IsNotExist(err) {
			return report, fmt.Errorf("read current %s: %w", rel, err)
		}
		if err := atomicWriteFile(dest, body, 0o644); err != nil {
			return report, fmt.Errorf("restore %s: %w", rel, err)
		}
		restored++
	}
	if restored == 0 {
		return report, fmt.Errorf("backup %s contains no amendable IDE gate files", stamp)
	}
	return report, nil
}
