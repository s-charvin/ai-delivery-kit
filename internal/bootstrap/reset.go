package bootstrap

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/s-charvin/ai-delivery-kit/internal/projectfs"
	"github.com/s-charvin/ai-delivery-kit/internal/version"
)

type ResetReport struct {
	BackupDir   string
	OriginalDir string
	SourceRoot  string
	TargetRoot  string
	Targets     []string
}

type backupEntry struct {
	Path   string `json:"path"`
	Type   string `json:"type"`
	Mode   uint32 `json:"mode,omitempty"`
	SHA256 string `json:"sha256,omitempty"`
	Target string `json:"link_target,omitempty"`
}

// noLinkedParents 拒绝路径上的目录跳转，不跟随用户链接写入外部项目。
func noLinkedParents(root, path string) error {
	return projectfs.NoLinkedParents(root, path)
}

func resetTargets(source string) []string {
	targets := []string{source}
	if source != ".ai-delivery" {
		targets = append(targets, ".ai-delivery")
	}
	for _, asset := range Manifest() {
		if strings.HasPrefix(asset.Target, ".ai-delivery/") {
			continue
		}
		targets = append(targets, asset.Target)
	}
	return targets
}

func validateResetSource(root, source string) (string, error) {
	if filepath.IsAbs(source) {
		return "", fmt.Errorf("旧交付根必须是项目内相对目录")
	}
	source = filepath.Clean(source)
	if source == "." || source == ".." || strings.HasPrefix(source, ".."+string(filepath.Separator)) {
		return "", fmt.Errorf("不能重建项目根或外部目录")
	}
	first := strings.Split(filepath.ToSlash(source), "/")[0]
	switch first {
	case ".git", ".agents", ".codex", ".claude", ".cursor", ".ai-delivery-backups":
		return "", fmt.Errorf("禁止作为交付根: %s", source)
	}
	path := filepath.Join(root, source)
	if err := noLinkedParents(root, path); err != nil {
		return "", err
	}
	info, err := os.Lstat(path)
	if os.IsNotExist(err) {
		return "", fmt.Errorf("未发现旧数据: %s", path)
	}
	if err != nil {
		return "", err
	}
	if !info.IsDir() {
		return "", fmt.Errorf("旧交付根必须是目录: %s", path)
	}
	if source != ".ai-delivery" {
		// 只检查边界文件存在，不解析或猜测旧协议。
		marked := false
		for _, name := range []string{"project-binding.json", "workflow-policy.json"} {
			if info, err := os.Lstat(filepath.Join(path, "meta", name)); err == nil && (info.Mode().IsRegular() || info.Mode()&os.ModeSymlink != 0) {
				marked = true
			}
		}
		if !marked {
			return "", fmt.Errorf("自定义旧根缺少交付元数据边界: %s/meta", path)
		}
		if _, err := os.Lstat(filepath.Join(root, ".ai-delivery")); !os.IsNotExist(err) {
			return "", fmt.Errorf("标准目标已存在，拒绝混合两份交付数据: %s", root)
		}
		for _, asset := range Manifest() {
			target := filepath.FromSlash(asset.Target)
			if source == target || strings.HasPrefix(target, source+string(filepath.Separator)) {
				return "", fmt.Errorf("旧根包含受管资产目标: %s", source)
			}
		}
	}
	return source, nil
}

func (e Engine) resetAndRun(cfg Config) error {
	source, err := validateResetSource(cfg.RepoRoot, cfg.ResetData)
	if err != nil {
		return err
	}
	targets := resetTargets(source)
	// 所有将被更新的链接目标必须先拒绝。数据树内链接只备份链接自身。
	for _, target := range targets[1:] {
		path := filepath.Join(cfg.RepoRoot, target)
		if err = noLinkedParents(cfg.RepoRoot, path); err != nil {
			return err
		}
		if err = filepath.WalkDir(path, func(path string, d fs.DirEntry, err error) error {
			if os.IsNotExist(err) {
				return nil
			}
			if err != nil {
				return err
			}
			if d.Type()&os.ModeSymlink != 0 {
				return fmt.Errorf("受管资产含符号链接，不能安全重建: %s", path)
			}
			return nil
		}); err != nil {
			return err
		}
	}
	parent := filepath.Join(cfg.RepoRoot, ".ai-delivery-backups")
	if err = noLinkedParents(cfg.RepoRoot, parent); err != nil {
		return err
	}
	if err = os.MkdirAll(parent, 0700); err != nil {
		return err
	}
	now := time.Now().UTC()
	if e.Now != nil {
		now = e.Now().UTC()
	}
	temp, err := os.MkdirTemp(parent, ".incomplete-"+now.Format("20060102T150405Z")+"-")
	if err != nil {
		return err
	}
	defer os.RemoveAll(temp)
	published := filepath.Join(parent, strings.TrimPrefix(filepath.Base(temp), ".incomplete-"))
	if cfg.Progress != nil {
		fmt.Fprintf(cfg.Progress, "备份重建：\n旧根：%s\n新根：%s\n备份目标：%s\n先完成并校验备份，再修改活跃数据。\n", filepath.Join(cfg.RepoRoot, source), filepath.Join(cfg.RepoRoot, ".ai-delivery"), published)
	}
	entries := []backupEntry{}
	for _, target := range targets {
		if err = copyBackupTree(cfg.RepoRoot, temp, target, &entries); err != nil {
			return fmt.Errorf("备份未完成，原数据未改动: %w", err)
		}
	}
	if err = verifyBackup(cfg.RepoRoot, temp, entries); err != nil {
		return fmt.Errorf("备份校验失败，原数据未改动: %w", err)
	}
	manifest := struct {
		Version     string        `json:"tool_version"`
		ProjectRoot string        `json:"project_root"`
		SourceRoot  string        `json:"source_root"`
		TargetRoot  string        `json:"target_root"`
		Targets     []string      `json:"targets"`
		Entries     []backupEntry `json:"entries"`
	}{version.String(), cfg.RepoRoot, source, ".ai-delivery", targets, entries}
	body, err := json.MarshalIndent(manifest, "", "  ")
	if err != nil {
		return err
	}
	if err = writeBackupFile(filepath.Join(temp, "manifest.json"), append(body, '\n'), 0600); err != nil {
		return fmt.Errorf("备份清单写入失败，原数据未改动: %w", err)
	}
	if _, err = os.Lstat(published); !os.IsNotExist(err) {
		return fmt.Errorf("备份目标已存在或不可检查: %s", published)
	}
	if err = os.Rename(temp, published); err != nil {
		return fmt.Errorf("发布备份失败，原数据未改动: %w", err)
	}
	report := ResetReport{BackupDir: published, OriginalDir: filepath.Join(published, "original-data"), SourceRoot: filepath.Join(cfg.RepoRoot, source), TargetRoot: filepath.Join(cfg.RepoRoot, ".ai-delivery"), Targets: targets}
	if cfg.ResetReport != nil {
		*cfg.ResetReport = report
	}
	failure := func(err error) error {
		return fmt.Errorf("备份已完成，但重建失败: %w\n完整备份: %s\n旧原件位置（搬移成功后）: %s\n源目录: %s\n新目标: %s\n可能已写入的受管目标: %s\n按 manifest.json 将 files/ 中各路径恢复；type=absent 表示原先不存在，请核对后自行撤回。不要覆盖备份后新增的用户修改。", err, published, report.OriginalDir, report.SourceRoot, report.TargetRoot, strings.Join(targets, ", "))
	}
	if err = os.Rename(report.SourceRoot, report.OriginalDir); err != nil {
		return failure(err)
	}
	// 只清理 kit 拥有的三个 skill，不删除用户其他技能。
	for _, asset := range Manifest() {
		if asset.Kind == "dir" {
			if err = os.RemoveAll(filepath.Join(cfg.RepoRoot, asset.Target)); err != nil {
				return failure(err)
			}
		}
	}
	cfg.ResetData = ""
	cfg.DeliveryPath = ".ai-delivery"
	if err = e.run(cfg); err != nil {
		return failure(err)
	}
	return nil
}

func copyBackupTree(root, backup, rel string, entries *[]backupEntry) error {
	source := filepath.Join(root, rel)
	info, err := os.Lstat(source)
	if os.IsNotExist(err) {
		*entries = append(*entries, backupEntry{Path: filepath.ToSlash(rel), Type: "absent"})
		return nil
	}
	if err != nil {
		return err
	}
	target := filepath.Join(backup, "files", rel)
	if err = os.MkdirAll(filepath.Dir(target), 0700); err != nil {
		return err
	}
	entry := backupEntry{Path: filepath.ToSlash(rel), Mode: uint32(info.Mode().Perm())}
	switch {
	case info.Mode()&os.ModeSymlink != 0:
		entry.Type = "symlink"
		entry.Target, err = os.Readlink(source)
		if err == nil {
			err = os.Symlink(entry.Target, target)
		}
	case info.IsDir():
		entry.Type = "directory"
		if err = os.MkdirAll(target, 0700); err != nil {
			return err
		}
		children, readErr := os.ReadDir(source)
		if readErr != nil {
			return readErr
		}
		for _, child := range children {
			if err = copyBackupTree(root, backup, filepath.Join(rel, child.Name()), entries); err != nil {
				return err
			}
		}
		// 目录保留 mode 信息在清单内；备份目录保持可读取，便于恢复。
	case info.Mode().IsRegular():
		entry.Type = "file"
		input, openErr := os.Open(source)
		if openErr != nil {
			return openErr
		}
		defer input.Close()
		output, openErr := os.OpenFile(target, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
		if openErr != nil {
			return openErr
		}
		hash := sha256.New()
		n, copyErr := io.Copy(io.MultiWriter(output, hash), input)
		if copyErr == nil && n != info.Size() {
			copyErr = io.ErrShortWrite
		}
		if copyErr == nil {
			copyErr = output.Chmod(info.Mode().Perm())
		}
		if copyErr == nil {
			copyErr = output.Sync()
		}
		closeErr := output.Close()
		if copyErr != nil {
			return copyErr
		}
		if closeErr != nil {
			return closeErr
		}
		entry.SHA256 = hex.EncodeToString(hash.Sum(nil))
	default:
		return fmt.Errorf("不支持备份特殊文件: %s", source)
	}
	if err != nil {
		return err
	}
	*entries = append(*entries, entry)
	return nil
}

func verifyBackup(root, backup string, entries []backupEntry) error {
	for _, entry := range entries {
		for _, base := range []string{root, filepath.Join(backup, "files")} {
			path := filepath.Join(base, filepath.FromSlash(entry.Path))
			info, err := os.Lstat(path)
			if entry.Type == "absent" {
				if !os.IsNotExist(err) {
					return fmt.Errorf("备份期间路径变化: %s", path)
				}
				continue
			}
			if err != nil {
				return err
			}
			switch entry.Type {
			case "file":
				if !info.Mode().IsRegular() || uint32(info.Mode().Perm()) != entry.Mode {
					return fmt.Errorf("文件类型或权限变化: %s", path)
				}
				input, err := os.Open(path)
				if err != nil {
					return err
				}
				hash := sha256.New()
				_, err = io.Copy(hash, input)
				closeErr := input.Close()
				if err != nil {
					return err
				}
				if closeErr != nil {
					return closeErr
				}
				if hex.EncodeToString(hash.Sum(nil)) != entry.SHA256 {
					return fmt.Errorf("备份字节不一致: %s", path)
				}
			case "directory":
				if !info.IsDir() {
					return fmt.Errorf("目录类型变化: %s", path)
				}
			case "symlink":
				link, err := os.Readlink(path)
				if err != nil || link != entry.Target {
					return fmt.Errorf("符号链接变化: %s", path)
				}
			}
		}
	}
	// 再核对文件集合，不能遗漏复制期间新增或删除的目录项。
	for _, base := range []string{root, filepath.Join(backup, "files")} {
		expected := map[string]bool{}
		for _, entry := range entries {
			if entry.Type != "absent" {
				expected[entry.Path] = true
			}
		}
		for _, entry := range entries {
			if entry.Type != "directory" {
				continue
			}
			children, err := os.ReadDir(filepath.Join(base, entry.Path))
			if err != nil {
				return err
			}
			for _, child := range children {
				rel := filepath.ToSlash(filepath.Join(entry.Path, child.Name()))
				if !expected[rel] {
					return fmt.Errorf("备份目录项集合发生变化: %s", rel)
				}
			}
		}
	}
	return nil
}

func writeBackupFile(path string, body []byte, mode os.FileMode) error {
	file, err := os.OpenFile(path, os.O_CREATE|os.O_EXCL|os.O_WRONLY, mode)
	if err != nil {
		return err
	}
	n, err := file.Write(body)
	if err == nil && n != len(body) {
		err = io.ErrShortWrite
	}
	if err == nil {
		err = file.Sync()
	}
	closeErr := file.Close()
	if err != nil {
		return err
	}
	return closeErr
}
