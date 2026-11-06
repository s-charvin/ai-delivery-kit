//go:build darwin || linux || freebsd || openbsd || netbsd || dragonfly

package bootstrap

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestProjectLockCoordinatesWithNativeProcessAndStaysOutsideDataRoot(t *testing.T) {
	root, old := resetFixture(t)
	unlock, err := projectLock(root, true)
	if err != nil {
		t.Fatal(err)
	}
	defer unlock()
	report := ResetReport{}
	if err := (Engine{}).Run(Config{RepoRoot: root, AllowManagedUpdate: true, ResetData: ".ai-delivery", ResetReport: &report}); err == nil {
		t.Fatal("locked reset proceeded")
	}
	if report.BackupDir != "" {
		t.Fatal("locked reset published backup")
	}
	if _, err := os.Stat(filepath.Join(old, "meta/workflow-policy.json")); err != nil {
		t.Fatal("locked reset changed source")
	}
	exe, err := os.Executable()
	if err != nil {
		t.Fatal(err)
	}
	cmd := exec.Command(exe, "-test.run=^TestNativeLockProbe$")
	cmd.Env = append(os.Environ(), "AI_DELIVERY_LOCK_PROBE="+root)
	out, err := cmd.CombinedOutput()
	if err != nil || !strings.Contains(string(out), "locked") {
		t.Fatalf("原生进程未共享锁: %s %v", out, err)
	}

}

func TestProjectLockRejectsSymlink(t *testing.T) {
	root := t.TempDir()
	outside := filepath.Join(t.TempDir(), "external")
	writeFixture(t, outside, "external")
	if err := os.Symlink(outside, filepath.Join(root, ".ai-delivery.lock")); err != nil {
		t.Fatal(err)
	}
	if unlock, err := projectLock(root, true); err == nil {
		unlock()
		t.Fatal("linked lock accepted")
	}
	body, _ := os.ReadFile(outside)
	if string(body) != "external" {
		t.Fatal("external modified")
	}
}

func TestNativeLockProbe(t *testing.T) {
	root := os.Getenv("AI_DELIVERY_LOCK_PROBE")
	if root == "" {
		return
	}
	unlock, err := projectLock(root, true)
	if err == nil {
		unlock()
		t.Fatal("unlocked")
	}
	fmt.Println("locked")
}
