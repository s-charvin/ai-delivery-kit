package bootstrap

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	kitassets "github.com/s-charvin/ai-delivery-kit"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
)

// UpgradeInstructions 来自随发行包提供的同一份资料，不写入旧宿主即可读取。
func UpgradeInstructions() string {
	body, err := kitassets.Embedded.ReadFile(".agents/skills/ai-delivery-orchestrator/references/version-upgrade.md")
	if err != nil {
		return "请使用自己的 AI 备份并迁移到当前模板，或显式运行 ai-delivery init --upgrade --reset-data <项目路径>。"
	}
	return string(body)
}

func compatibilityError(root, path, field string, actual, expected any) error {
	guide := filepath.Join(root, ".agents/skills/ai-delivery-orchestrator/references/version-upgrade.md")
	help := "升级指引：" + guide
	if _, err := os.Stat(guide); err != nil {
		help += "\n当前发行包中的指引：\n" + UpgradeInstructions()
	}
	resetFlag := "--reset-data"
	if filepath.Base(filepath.Dir(path)) == "meta" {
		if rel, err := filepath.Rel(root, filepath.Dir(filepath.Dir(path))); err == nil && rel != ".ai-delivery" && safeMetadataTemplate(rel) {
			resetFlag += "=" + filepath.ToSlash(rel)
		}
	}
	quote := func(text string) string { return "'" + strings.ReplaceAll(text, "'", "'\"'\"'") + "'" }
	command := "ai-delivery init --upgrade " + quote(resetFlag) + " " + quote(root)
	return fmt.Errorf("无法继续：交付数据不符合当前协议。\n文件：%s\n字段：%s\n实际：%v\n要求：%v\nA. 复制升级指引中的提示词，使用自己的 AI 备份并迁移。\nB. 显式备份重建：%s\n普通升级未转换或重置数据。\n%s", path, field, actual, expected, command, help)
}

// checkCurrentMetadata 只检查本次升级实际消费的元数据，不扫描或解释历史需求。
func checkCurrentMetadata(root, deliveryPath string) error {
	ad := filepath.Join(root, deliveryPath)
	if _, err := os.Lstat(ad); os.IsNotExist(err) {
		initialized := false
		for _, asset := range Manifest() {
			if asset.Kind == "dir" {
				if _, err := os.Lstat(filepath.Join(root, asset.Target)); err == nil {
					initialized = true
				}
			}
		}
		if !initialized {
			return nil
		}
	}
	for _, spec := range []struct {
		name string
		kind string
	}{
		{"project-binding.json", "binding"},
		{"workflow-policy.json", "policy"},
	} {
		path := filepath.Join(ad, "meta", spec.name)
		if err := noLinkedParents(root, path); err != nil {
			return compatibilityError(root, path, "path", err, "项目内普通元数据文件")
		}
		body, err := os.ReadFile(path)
		if err != nil {
			return compatibilityError(root, path, "file", err, "存在且可读取的当前 JSON 对象")
		}
		data, err := currentObject(body)
		if err != nil {
			return compatibilityError(root, path, "JSON", err, "无重复键的 JSON 对象")
		}
		if spec.name == "project-binding.json" {
			declared, exists := data["ai_delivery_path"]
			if !exists {
				declared = ".ai-delivery"
			}
			if text, ok := declared.(string); !ok || !safeMetadataTemplate(text) || filepath.Clean(text) != deliveryPath {
				return compatibilityError(root, path, "ai_delivery_path", declared, deliveryPath)
			}
		}
		if err := protocol.ValidateMetadata(spec.kind, data); err != nil {
			return compatibilityError(root, path, "protocol", err, "当前协议元数据")
		}
	}
	return nil
}

func currentObject(body []byte) (map[string]any, error) {
	return protocol.Object(body)
}

func safeMetadataTemplate(text string) bool {
	return protocol.SafeMetadataTemplate(text)
}

// 与读端的有界根发现保持一致，不扫描旧需求或备份。
func currentDeliveryPath(root string, hints ...string) (string, error) {
	if len(hints) > 0 && hints[0] != "" {
		if !safeMetadataTemplate(hints[0]) || filepath.Clean(hints[0]) == "." {
			return "", fmt.Errorf("当前数据根提示必须是项目内相对目录")
		}
		if err := noLinkedParents(root, filepath.Join(root, hints[0])); err != nil {
			return "", err
		}
		return filepath.Clean(hints[0]), nil
	}
	standard := filepath.Join(root, ".ai-delivery")
	if _, err := os.Lstat(standard); !os.IsNotExist(err) {
		return ".ai-delivery", nil
	}
	children, err := os.ReadDir(root)
	if err != nil {
		return "", err
	}
	found := ""
	for _, child := range children {
		if !child.IsDir() {
			continue
		}
		switch child.Name() {
		case ".git", ".agents", ".agents-zh", ".codex", ".claude", ".cursor", ".ai-delivery-backups", ".worktrees", ".superpowers":
			continue
		}
		candidate := filepath.Join(root, child.Name(), "meta/project-binding.json")
		marked := false
		for _, name := range []string{"project-binding.json", "workflow-policy.json"} {
			if _, err := os.Lstat(filepath.Join(root, child.Name(), "meta", name)); err == nil {
				marked = true
			} else if !os.IsNotExist(err) {
				return "", err
			}
		}
		if !marked {
			continue
		}
		if found != "" {
			return "", compatibilityError(root, candidate, "ai_delivery_path", found+", "+child.Name(), "唯一当前交付根；先明确工作区")
		}
		found = child.Name()
	}
	if found == "" {
		found = ".ai-delivery"
	}
	return found, nil
}

// DeliveryPathHint 使用用户已明确提供的根，不递归扫描项目或解释旧数据。
func DeliveryPathHint(root, target string) (string, error) {
	absolute, err := filepath.Abs(target)
	if err != nil {
		return "", err
	}
	rel, err := filepath.Rel(root, absolute)
	if err != nil {
		return "", err
	}
	rel = filepath.ToSlash(rel)
	if rel == "." {
		return "", nil
	}
	if !safeMetadataTemplate(rel) {
		return "", fmt.Errorf("目标不在项目内: %s", target)
	}
	for _, name := range []string{"project-binding.json", "workflow-policy.json"} {
		if _, err := os.Lstat(filepath.Join(absolute, "meta", name)); err == nil {
			return rel, nil
		} else if !os.IsNotExist(err) {
			return "", err
		}
	}
	return "", nil
}
