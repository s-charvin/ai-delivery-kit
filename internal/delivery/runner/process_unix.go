//go:build darwin || linux || freebsd || openbsd || netbsd || dragonfly

package runner

import (
	"fmt"
	"os/exec"
	"sync"
	"syscall"
	"time"
)

func prepareProcess(cmd *exec.Cmd) error {
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
	return nil
}
func startedProcess(cmd *exec.Cmd) (func() (bool, error), error) {
	var once sync.Once
	var result error
	var forced bool
	return func() (bool, error) {
		once.Do(func() {
			if err := syscall.Kill(-cmd.Process.Pid, 0); err == syscall.ESRCH {
				return
			}
			err := syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL)
			if err == syscall.ESRCH {
				return
			}
			if err != nil {
				result = fmt.Errorf("发送进程组终止信号: %w", err)
				return
			}
			forced = true
			ticker := time.NewTicker(10 * time.Millisecond)
			defer ticker.Stop()
			deadline := time.NewTimer(5 * time.Second)
			defer deadline.Stop()
			for {
				if err := syscall.Kill(-cmd.Process.Pid, 0); err == syscall.ESRCH {
					return
				} else if err != nil && err != syscall.EPERM {
					result = fmt.Errorf("查询进程组退出: %w", err)
					return
				}
				select {
				case <-ticker.C:
				case <-deadline.C:
					result = fmt.Errorf("无法确认原生进程组已全部退出")
					return
				}
			}
		})
		return forced, result
	}, nil
}
func processSignal(cmd *exec.Cmd) string {
	if cmd.ProcessState == nil {
		return ""
	}
	if s, ok := cmd.ProcessState.Sys().(syscall.WaitStatus); ok && s.Signaled() {
		return s.Signal().String()
	}
	return ""
}
