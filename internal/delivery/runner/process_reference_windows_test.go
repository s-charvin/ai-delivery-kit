package runner

import (
	"net"
	"os/exec"
	"path/filepath"
	"syscall"
	"testing"
	"time"
)

func TestWindowsCleanupDoesNotForceExitedProcessWithRetainedReference(t *testing.T) {
	helper := filepath.Join(t.TempDir(), "native-helper.exe")
	if out, err := exec.Command("go", "build", "-o", helper, "./testdata/native-helper").CombinedOutput(); err != nil {
		t.Fatal(string(out), err)
	}
	listener, err := net.ListenTCP("tcp", &net.TCPAddr{IP: net.IPv4(127, 0, 0, 1)})
	if err != nil {
		t.Fatal(err)
	}
	defer listener.Close()
	if err := listener.SetDeadline(time.Now().Add(10 * time.Second)); err != nil {
		t.Fatal(err)
	}
	cmd := exec.Command(helper, "handshake", listener.Addr().String())
	if err := prepareProcess(cmd); err != nil {
		t.Fatal(err)
	}
	if err := cmd.Start(); err != nil {
		t.Fatal(err)
	}
	waited := false
	var cleanup func() (bool, error)
	defer func() {
		if !waited {
			cmd.Process.Kill()
			cmd.Wait()
		}
		if cleanup != nil {
			cleanup()
		}
	}()
	// 在恢复执行前持有额外引用；进程正常退出后仍保留该句柄。
	retained, err := syscall.OpenProcess(syscall.SYNCHRONIZE|syscall.PROCESS_QUERY_INFORMATION, false, uint32(cmd.Process.Pid))
	if err != nil {
		t.Fatal(err)
	}
	defer syscall.CloseHandle(retained)
	cleanup, err = startedProcess(cmd)
	if err != nil {
		t.Fatal(err)
	}
	conn, err := listener.AcceptTCP()
	if err != nil {
		t.Fatal(err)
	}
	defer conn.Close()
	if _, err := conn.Write([]byte("正常退出\n")); err != nil {
		t.Fatal(err)
	}
	err = cmd.Wait()
	waited = true
	if err != nil {
		t.Fatal("宿主未正常退出", err)
	}
	state, err := syscall.WaitForSingleObject(retained, 0)
	if err != nil || state != syscall.WAIT_OBJECT_0 {
		t.Fatalf("保留引用指向的进程尚未退出: state=%d err=%v", state, err)
	}
	forced, err := cleanup()
	if err != nil || forced {
		t.Fatalf("已退出进程的额外引用被当成活进程: forced=%v err=%v", forced, err)
	}
}
