package bootstrap

import (
	"bytes"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/s-charvin/ai-delivery-kit/internal/projectfs"
)

const (
	ideGateBackupKeep    = 3
	ideGateBackupRelRoot = ".ai-delivery/backups/ide-gates"
)

// AmendReport records IDE gate amendments so the CLI can expose recovery options.
type AmendReport struct {
	BackupStamp string   // Backup timestamp directory name; empty when no backup was made.
	BackupDir   string   // Absolute backup directory path.
	Files       []string // Project-relative paths that were backed up and amended.
}

func (r AmendReport) Empty() bool {
	return len(r.Files) == 0
}

// amendSession binds one bootstrap or reapply run to a shared backup timestamp.
type amendSession struct {
	backupRelRoot string
	repoRoot      string
	stamp         string
	report        *AmendReport
	now           func() time.Time
	deferPrune    bool
}

func newAmendSession(repoRoot string, now func() time.Time, report *AmendReport) *amendSession {
	if now == nil {
		now = time.Now
	}
	if report == nil {
		report = &AmendReport{}
	}
	return &amendSession{
		repoRoot:      repoRoot,
		backupRelRoot: ideGateBackupRelRoot,
		now:           now,
		report:        report,
	}
}

func isAmendableAgentsMDTarget(target string) bool {
	return filepath.ToSlash(target) == "AGENTS.md"
}

func isAmendableManagedTarget(target string) bool {
	return isAmendableAgentsMDTarget(target)
}

// 历史恢复允许列表不代表当前安装资源所有权。
func restorableIDEPaths() []string {
	return []string{
		".cursor/hooks.json",
		".claude/settings.json",
		".codex/hooks.json",
		".codex/config.toml",
		"AGENTS.md",
	}
}

const (
	agentsGateStart = "<!-- ai-delivery:ui-contract-gate:start -->"
	agentsGateEnd   = "<!-- ai-delivery:ui-contract-gate:end -->"
)

// writeAmendableAgentsMD upserts the kit gate section into the Codex AGENTS.md entrypoint.
func (s *amendSession) writeAmendableAgentsMD(relTarget, absTarget string, desired []byte) error {
	if err := projectfs.NoLinkedParents(s.repoRoot, absTarget); err != nil {
		return err
	}
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
	if err := s.writeFrom(absTarget, merged, 0o644, existing); err != nil {
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

func (s *amendSession) backupExisting(relTarget, absTarget string, existing []byte) error {
	if err := projectfs.NoLinkedParents(s.repoRoot, absTarget); err != nil {
		return err
	}
	if s.stamp == "" {
		base := s.now().UTC().Format("2006-01-02T15-04-05Z")
		parent := filepath.Join(s.repoRoot, filepath.FromSlash(s.backupRelRoot))
		if err := projectfs.NoLinkedParents(s.repoRoot, parent); err != nil {
			return err
		}
		if err := os.MkdirAll(parent, 0700); err != nil {
			return err
		}
		for sequence := 0; ; sequence++ {
			s.stamp = base
			if sequence > 0 {
				s.stamp = fmt.Sprintf("%s-%06d", base, sequence)
			}
			candidate := filepath.Join(parent, s.stamp)
			if err := os.Mkdir(candidate, 0700); err != nil {
				if os.IsExist(err) {
					continue
				}
				return err
			}
			break
		}
	}
	backupRoot := filepath.Join(s.repoRoot, filepath.FromSlash(s.backupRelRoot), s.stamp)
	dest := filepath.Join(backupRoot, filepath.FromSlash(relTarget))
	if err := projectfs.NoLinkedParents(s.repoRoot, dest); err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(dest), 0o700); err != nil {
		return fmt.Errorf("create backup dir for %s: %w", relTarget, err)
	}
	info, err := os.Lstat(absTarget)
	if err != nil {
		return err
	}
	if !info.Mode().IsRegular() {
		return fmt.Errorf("备份目标必须是普通文件: %s", absTarget)
	}
	if err := s.write(dest, existing, info.Mode().Perm()); err != nil {
		return fmt.Errorf("backup %s: %w", absTarget, err)
	}

	s.report.BackupStamp = s.stamp
	s.report.BackupDir = backupRoot
	s.report.Files = appendUnique(s.report.Files, filepath.ToSlash(relTarget))

	if s.deferPrune {
		return nil
	}
	if err := pruneBackupsAtRoot(filepath.Join(s.repoRoot, s.backupRelRoot), ideGateBackupKeep); err != nil {
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
	return projectfs.AtomicWriteFile(target, body, mode)
}

func (s *amendSession) write(target string, body []byte, mode os.FileMode) error {
	if err := projectfs.NoLinkedParents(s.repoRoot, target); err != nil {
		return err
	}
	original, err := os.ReadFile(target)
	if err != nil && !os.IsNotExist(err) {
		return err
	}
	return s.writeFrom(target, body, mode, original)
}

func (s *amendSession) writeFrom(target string, body []byte, mode os.FileMode, original []byte, extra ...func() error) error {
	var identity os.FileInfo
	check := func(string) error {
		for _, verify := range extra {
			if err := verify(); err != nil {
				return err
			}
		}
		if err := projectfs.NoLinkedParents(s.repoRoot, target); err != nil {
			return err
		}
		info, err := os.Lstat(target)
		if os.IsNotExist(err) {
			if original != nil {
				return fmt.Errorf("写入前文件已删除: %s", target)
			}
			return nil
		}
		if err != nil {
			return err
		}
		if original == nil || !info.Mode().IsRegular() {
			return fmt.Errorf("写入前文件身份已改变: %s", target)
		}
		current, err := os.ReadFile(target)
		if err != nil {
			return err
		}
		if !bytes.Equal(current, original) {
			return fmt.Errorf("写入前用户内容已改变: %s", target)
		}
		if identity != nil && (!os.SameFile(identity, info) || identity.Mode() != info.Mode()) {
			return fmt.Errorf("写入前文件身份已改变: %s", target)
		}
		identity = info
		return nil
	}
	if err := check(""); err != nil {
		return err
	}
	return projectfs.AtomicWriteFileChecked(target, body, mode, check)
}

func pruneIDEGateBackups(repoRoot string, keep int) error {
	return pruneBackupsAtRoot(filepath.Join(repoRoot, filepath.FromSlash(ideGateBackupRelRoot)), keep)
}

func pruneBackupsAtRoot(root string, keep int) error {
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

// ListIDEGateBackups returns backup timestamps in newest-first order.
func ListIDEGateBackups(repoRoot string, hint ...string) ([]string, error) {
	deliveryPath, err := currentDeliveryPath(repoRoot, hint...)
	if err != nil {
		return nil, err
	}
	root := filepath.Join(repoRoot, deliveryPath, "backups/ide-gates")
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

// RestoreIDEGateBackup restores amendable IDE settings and AGENTS.md from a timestamp.
// Current files are backed up first to preserve another rollback point.
func RestoreIDEGateBackup(repoRoot, stamp string, now func() time.Time, hint ...string) (AmendReport, error) {
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

	unlock, err := projectLock(root, false)
	if err != nil {
		return report, err
	}
	defer unlock()
	deliveryPath, err := currentDeliveryPath(root, hint...)
	if err != nil {
		return report, err
	}
	backupRelative := filepath.Join(deliveryPath, "backups/ide-gates")
	if stamp == "" || stamp == "." || filepath.Base(stamp) != stamp || strings.ContainsAny(stamp, `/\\`) {
		return report, fmt.Errorf("非法备份名称")
	}
	backupRoot := filepath.Join(root, backupRelative, stamp)
	if err := projectfs.NoLinkedParents(root, backupRoot); err != nil {
		return report, err
	}
	st, err := os.Stat(backupRoot)
	if err != nil {
		return report, fmt.Errorf("backup %s not found: %w", stamp, err)
	}
	if !st.IsDir() {
		return report, fmt.Errorf("backup %s is not a directory", stamp)
	}

	session := newAmendSession(root, now, &report)
	session.backupRelRoot = backupRelative
	session.deferPrune = true
	restored := 0
	for _, rel := range restorableIDEPaths() {
		src := filepath.Join(backupRoot, filepath.FromSlash(rel))
		if err := projectfs.NoLinkedParents(root, src); err != nil {
			return report, err
		}
		dest := filepath.Join(root, filepath.FromSlash(rel))
		if err := projectfs.NoLinkedParents(root, dest); err != nil {
			return report, err
		}
		body, err := os.ReadFile(src)
		if err != nil {
			if os.IsNotExist(err) {
				continue
			}
			return report, fmt.Errorf("read backup %s: %w", rel, err)
		}
		info, err := os.Lstat(src)
		if err != nil {
			return report, err
		}
		if !info.Mode().IsRegular() {
			return report, fmt.Errorf("备份源必须为普通文件: %s", src)
		}
		current, err := os.ReadFile(dest)
		if err == nil {
			if err := session.backupExisting(rel, dest, current); err != nil {
				return report, err
			}
		} else if !os.IsNotExist(err) {
			return report, fmt.Errorf("read current %s: %w", rel, err)
		}
		verifySource := func() error {
			if err := projectfs.NoLinkedParents(root, src); err != nil {
				return err
			}
			latest, err := os.Lstat(src)
			if err != nil {
				return err
			}
			if !os.SameFile(info, latest) || info.Mode() != latest.Mode() {
				return fmt.Errorf("恢复源身份已改变: %s", src)
			}
			raw, err := os.ReadFile(src)
			if err != nil {
				return err
			}
			if !bytes.Equal(raw, body) {
				return fmt.Errorf("恢复源内容已改变: %s", src)
			}
			return nil
		}
		if err := session.writeFrom(dest, body, info.Mode().Perm(), current, verifySource); err != nil {
			return report, fmt.Errorf("restore %s: %w", rel, err)
		}
		restored++
	}
	if restored == 0 {
		return report, fmt.Errorf("backup %s contains no amendable IDE gate files", stamp)
	}
	// 恢复操作保留所选源和所有既有恢复点；新增当前内容备份不能隐式清理历史。
	return report, nil
}
