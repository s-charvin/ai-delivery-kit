package bootstrap

import "github.com/s-charvin/ai-delivery-kit/internal/projectfs"

func projectLock(root string, _ bool) (func(), error) {
	return projectfs.ProjectLock(root)
}
