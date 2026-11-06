package workspace

import (
	"fmt"
	"strings"

	kitassets "github.com/s-charvin/ai-delivery-kit"
	"github.com/s-charvin/ai-delivery-kit/internal/assets"
)

const resourcePrefix = "kit://ai-delivery-orchestrator/references/"

func GuidanceURI(role string) (string, error) {
	name, ok := map[string]string{"analysis": "scenario-guidance.md", "design": "stage-design-and-spec.md", "ui": "stage-ui-truth.md", "implement": "stage-implementation.md", "review": "stage-implementation.md", "recovery": "reconcile-rules.md", "finish": "stage-implementation.md"}[role]
	if !ok {
		return "", fmt.Errorf("未知上下文角色: %q", role)
	}
	return resourcePrefix + name, nil
}
func Resource(uri string) ([]byte, error) {
	if !strings.HasPrefix(uri, "kit://") {
		return nil, fmt.Errorf("未知内嵌资源: %s", uri)
	}
	name := strings.TrimPrefix(uri, "kit://")
	root := ".agents/skills/"
	if strings.HasPrefix(name, "zh/") {
		root = ".agents-zh/skills/"
		name = strings.TrimPrefix(name, "zh/")
	}
	clean, err := NormalizePath(name)
	if err != nil || clean != name {
		return nil, fmt.Errorf("非法资源路径: %s", uri)
	}
	return kitassets.Embedded.ReadFile(root + name)
}
func ResourceDigest() (string, error) { return assets.Digest() }
