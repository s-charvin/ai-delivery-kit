package workspace_test

import (
	"testing"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

func TestNormalizePathRejectsRootedAndVolumePathsOnEveryPlatform(t *testing.T) {
	for _, value := range []string{
		"/outside", "//server/share/file.go", `\outside`,
		"C:outside", "C:/outside", `C:\outside`, `\\server\share\file.go`,
	} {
		t.Run(value, func(t *testing.T) {
			if normalized, err := workspace.NormalizePath(value); err == nil {
				t.Fatalf("非项目相对路径被接受: %q -> %q", value, normalized)
			}
		})
	}
	if normalized, err := workspace.NormalizePath("src/旧 文件.go"); err != nil || normalized != "src/旧 文件.go" {
		t.Fatalf("合法 UTF-8 项目路径未保留: %q, %v", normalized, err)
	}
}
