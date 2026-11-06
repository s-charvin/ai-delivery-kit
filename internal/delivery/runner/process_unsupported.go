//go:build !darwin && !linux && !freebsd && !openbsd && !netbsd && !dragonfly && !windows

package runner

import (
	"fmt"
	"os/exec"
)

func prepareProcess(*exec.Cmd) error {
	return fmt.Errorf("当前平台尚不支持可靠原生进程清理")
}
func startedProcess(*exec.Cmd) (func() (bool, error), error) {
	return nil, fmt.Errorf("当前平台不支持运行")
}
func processSignal(*exec.Cmd) string { return "" }
