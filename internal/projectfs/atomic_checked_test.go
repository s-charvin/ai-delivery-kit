package projectfs

import (
	"errors"
	"os"
	"path/filepath"
	"testing"
)

func TestCheckedAtomicPublicationRejectsAbortAndTemporaryReplacement(t *testing.T) {
	for _, kind := range []string{"abort", "symlink", "bytes", "replace", "rename"} {
		t.Run(kind, func(t *testing.T) {
			root := t.TempDir()
			target := filepath.Join(root, "status.json")
			original := []byte(`{"status":"old"}`)
			if e := os.WriteFile(target, original, 0600); e != nil {
				t.Fatal(e)
			}
			other := filepath.Join(t.TempDir(), "untouched")
			os.WriteFile(other, []byte("用户资源"), 0600)
			retained := filepath.Join(t.TempDir(), "staged-original")
			stagedBody := []byte(`{"status":"new"}`)
			e := AtomicWriteFileChecked(target, stagedBody, 0644, func(tmp string) error {
				switch kind {
				case "abort":
					return errors.New("写前漂移或中断")
				case "symlink":
					if e := os.Rename(tmp, retained); e != nil {
						t.Fatal("未能注入暂存路径替换", e)
					}
					if e := os.Symlink(other, tmp); e != nil {
						t.Fatal("未能注入暂存链接", e)
					}
				case "bytes":
					if e := os.WriteFile(tmp, []byte("外部替换"), 0600); e != nil {
						t.Fatal("未能注入暂存内容改写", e)
					}
				case "replace":
					if e := os.Rename(tmp, retained); e != nil {
						t.Fatal("未能移开原始暂存文件", e)
					}
					if e := os.WriteFile(tmp, stagedBody, 0600); e != nil {
						t.Fatal("未能注入相同内容的新文件", e)
					}
				case "rename":
					if e := os.Rename(target, target+".external"); e != nil {
						return e
					}
					return os.Mkdir(target, 0700)
				}
				return nil
			})
			if e == nil {
				t.Fatal("发布未拒绝", kind)
			}
			read := target
			if kind == "rename" {
				read += ".external"
			}
			body, _ := os.ReadFile(read)
			if string(body) != string(original) {
				t.Fatal(string(body))
			}
			body, _ = os.ReadFile(other)
			if string(body) != "用户资源" {
				t.Fatal("改变链接目标")
			}
			entries, _ := filepath.Glob(filepath.Join(root, ".ai-delivery-write-*"))
			if len(entries) != 0 {
				t.Fatal(entries)
			}
		})
	}
}

func TestAtomicStageCreationFailurePreservesOriginal(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(root, "status.json")
	os.WriteFile(target, []byte("旧件"), 0600)
	if e := os.Chmod(root, 0500); e != nil {
		t.Fatal(e)
	}
	defer os.Chmod(root, 0700)
	e := AtomicWriteFile(target, []byte("新件"), 0600)
	if e == nil {
		t.Skip("当前权限环境允许写只读目录")
	}
	b, _ := os.ReadFile(target)
	if string(b) != "旧件" {
		t.Fatal(string(b))
	}
}
