package runner

import (
	"context"
	"os"
	"path/filepath"
	"testing"
)

func TestCapturedLogRetainsIdentityWithIdenticalReplacement(t *testing.T) {
	path := filepath.Join(t.TempDir(), "stdout.log")
	c, err := newCapturedLog(path)
	if err != nil {
		t.Fatal(err)
	}
	defer c.close()
	body := []byte("原生采集内容")
	if _, err := c.writer.Write(body); err != nil {
		t.Fatal(err)
	}
	c.writer.Close()
	if err := c.finish(context.Background()); err != nil {
		t.Fatal(err)
	}
	if err := os.Rename(path, path+".original"); err != nil {
		t.Fatal("未能注入路径替换", err)
	}
	if err := os.WriteFile(path, body, 0600); err != nil {
		t.Fatal(err)
	}
	if err := c.validate(); err == nil {
		t.Fatal("相同内容的新文件替代了原始采集身份")
	}
}

func TestCapturedLogCreationCannotOverwriteExistingEvidence(t *testing.T) {
	path := filepath.Join(t.TempDir(), "stdout.log")
	body := []byte("已有证据")
	if err := os.WriteFile(path, body, 0600); err != nil {
		t.Fatal(err)
	}
	if c, err := newCapturedLog(path); err == nil {
		c.close()
		t.Fatal("创建采集流覆盖了已有证据")
	}
	stored, err := os.ReadFile(path)
	if err != nil || string(stored) != string(body) {
		t.Fatal("已有证据改变", string(stored), err)
	}
}
