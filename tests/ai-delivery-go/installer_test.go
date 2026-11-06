package aideliverygo_test

import (
	"archive/tar"
	"compress/gzip"
	"crypto/sha256"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestUnixInstallerPublishesOnlyCompiledProgramAndPreservesFailedUpdate(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("Windows 安装便利入口由 PowerShell 实机 CI 单独验证")
	}
	_, src, _, _ := runtime.Caller(0)
	repo := filepath.Clean(filepath.Join(filepath.Dir(src), "../.."))
	root := t.TempDir()
	bin := filepath.Join(root, "candidate")
	cmd := exec.Command("go", "build", "-o", bin, "./cmd/ai-delivery")
	cmd.Dir = repo
	cmd.Env = append(os.Environ(), "CGO_ENABLED=0")
	if out, err := cmd.CombinedOutput(); err != nil {
		t.Fatalf("构建: %v %s", err, out)
	}
	candidate, err := os.ReadFile(bin)
	if err != nil {
		t.Fatal(err)
	}
	archiveName := "ai-delivery_" + runtime.GOOS + "_" + runtime.GOARCH + ".tar.gz"
	publish := func(body []byte) {
		t.Helper()
		f, err := os.Create(filepath.Join(root, archiveName))
		if err != nil {
			t.Fatal(err)
		}
		z := gzip.NewWriter(f)
		tarWriter := tar.NewWriter(z)
		if err = tarWriter.WriteHeader(&tar.Header{Name: "ai-delivery", Mode: 0755, Size: int64(len(body))}); err != nil {
			t.Fatal(err)
		}
		if _, err = tarWriter.Write(body); err != nil {
			t.Fatal(err)
		}
		if err = tarWriter.Close(); err != nil {
			t.Fatal(err)
		}
		if err = z.Close(); err != nil {
			t.Fatal(err)
		}
		if err = f.Close(); err != nil {
			t.Fatal(err)
		}
		raw, err := os.ReadFile(filepath.Join(root, archiveName))
		if err != nil {
			t.Fatal(err)
		}
		if err = os.WriteFile(filepath.Join(root, "checksums.txt"), []byte(fmt.Sprintf("%x  %s\n", sha256.Sum256(raw), archiveName)), 0644); err != nil {
			t.Fatal(err)
		}
	}
	installDir := filepath.Join(root, "external install '$` with space")
	install := func(wantSuccess bool) {
		t.Helper()
		cmd := exec.Command("bash", filepath.Join(repo, "scripts/install-ai-delivery.sh"), "--version", "v-fixture", "--download-base-url", "file://"+filepath.ToSlash(root), "--install-dir", installDir)
		cmd.Dir = root
		env := []string{}
		for _, v := range os.Environ() {
			if !strings.HasPrefix(v, "AI_DELIVERY_") && !strings.HasPrefix(v, "GITHUB_TOKEN=") {
				env = append(env, v)
			}
		}
		cmd.Env = env
		out, err := cmd.CombinedOutput()
		if (err == nil) != wantSuccess {
			t.Fatalf("install成功=%t: %v %s", wantSuccess, err, out)
		}
	}
	publish(candidate)
	install(true)
	installed := filepath.Join(installDir, "ai-delivery")
	before, err := os.ReadFile(installed)
	if err != nil {
		t.Fatal(err)
	}
	if sha256.Sum256(before) != sha256.Sum256(candidate) {
		t.Fatal("安装字节非选择的程序")
	}
	entries, err := os.ReadDir(installDir)
	if err != nil || len(entries) != 1 {
		t.Fatal("程序安装夹带其他资源或核心", err)
	}
	if err = os.WriteFile(filepath.Join(root, "checksums.txt"), []byte(strings.Repeat("0", 64)+"  "+archiveName+"\n"), 0644); err != nil {
		t.Fatal(err)
	}
	install(false)
	after, _ := os.ReadFile(installed)
	if sha256.Sum256(after) != sha256.Sum256(before) {
		t.Fatal("校验失败覆盖原程序")
	}
	publish([]byte("not an executable binary\n"))
	install(false)
	after, _ = os.ReadFile(installed)
	if sha256.Sum256(after) != sha256.Sum256(before) {
		t.Fatal("目标平台无法执行仍覆盖原程序")
	}
	entries, _ = os.ReadDir(installDir)
	if len(entries) != 1 {
		t.Fatal("失败暂存未清理")
	}
}
