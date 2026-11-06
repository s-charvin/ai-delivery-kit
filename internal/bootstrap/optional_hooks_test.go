package bootstrap

import (
	"bytes"
	"github.com/s-charvin/ai-delivery-kit/internal/assets"
	"os"
	"path/filepath"
	"testing"
)

func TestInstallKeepsHooksOptionalAndUserConfig(t *testing.T) {
	for _, config := range []string{"", "[features]\nhooks = false\n# 用户配置\n", "[features]\nhooks = true\n[third_party]\nkeep = 1\n"} {
		t.Run(config, func(t *testing.T) {
			root := t.TempDir()
			p := filepath.Join(root, ".codex/config.toml")
			if config != "" {
				writeFixture(t, p, config)
			}
			// reviewer 原始反例；字节与整数词形都是 oracle，不经 float64 解码。
			foreign := "{ \"third_party\": 9007199254740993, \"hooks\": {\"SessionStart\":[{\"hooks\":[{\"type\":\"command\",\"command\":\"third-party command\"}]}]} }\n"
			writeFixture(t, filepath.Join(root, ".codex/hooks.json"), foreign)
			for _, upgrade := range []bool{false, true} {
				report := AmendReport{}
				if err := (Engine{}).Run(Config{RepoRoot: root, AllowManagedUpdate: upgrade, Report: &report}); err != nil {
					t.Fatal(err)
				}
				got, err := os.ReadFile(p)
				if config == "" {
					if !os.IsNotExist(err) {
						t.Fatalf("默认安装创建/开启Codex配置: %q %v", got, err)
					}
				} else if err != nil || !bytes.Equal(got, []byte(config)) {
					t.Fatalf("用户配置被改写: %q %v", got, err)
				}
				if err := assets.Verify(".ai-delivery", func(rel string) ([]byte, bool, error) {
					b, e := os.ReadFile(filepath.Join(root, rel))
					return b, e == nil, e
				}); err != nil {
					t.Fatal(err)
				}
				current, err := os.ReadFile(filepath.Join(root, ".codex/hooks.json"))
				if err != nil {
					t.Fatal(err)
				}
				if !bytes.Equal([]byte(foreign), current) {
					t.Fatalf("第三方定义被修改或自动安装了 kit hook: %s", current)
				}
				if !report.Empty() {
					t.Fatalf("无 owned 变化却发布备份: %+v", report)
				}
				for _, rel := range []string{".claude/settings.json", ".cursor/hooks.json"} {
					if _, err := os.Stat(filepath.Join(root, rel)); !os.IsNotExist(err) {
						t.Fatalf("创建可选配置 %s: %v", rel, err)
					}
				}
			}
		})
	}
}

func TestUserOptionalNativeHookDoesNotInvalidateResources(t *testing.T) {
	root := t.TempDir()
	if err := (Engine{}).Run(Config{RepoRoot: root}); err != nil {
		t.Fatal(err)
	}
	writeFixture(t, filepath.Join(root, ".codex/hooks.json"), `{"hooks":{"PreToolUse":[{"matcher":"apply_patch","hooks":[{"type":"command","command":"ai-delivery hook --host codex --event PreToolUse --project /p --req R --subreq SR-001 --intent implement --to in_dev"}]}]}}`)
	if err := assets.Verify(".ai-delivery", func(rel string) ([]byte, bool, error) {
		b, e := os.ReadFile(filepath.Join(root, rel))
		return b, e == nil, e
	}); err != nil {
		t.Fatal("用户可选接入不应破坏资源身份", err)
	}
}

func TestOptionalHostFilesRemainByteExactAcrossRefreshAndReset(t *testing.T) {
	root := t.TempDir()
	files := map[string]string{
		".codex/hooks.json":     "{ \"third_party\": 9007199254740993, \"hooks\": {\"SessionStart\":[{\"hooks\":[{\"type\":\"command\",\"command\":\"third-party command\"}]}]} }\n",
		".claude/settings.json": "{ \"permissions\": {\"allow\":[]}, \"number\":9007199254740993 }\n",
		".cursor/hooks.json":    "{ \"version\":1, \"hooks\":{}, \"number\":9007199254740993 }\n",
	}
	for p, body := range files {
		writeFixture(t, filepath.Join(root, p), body)
	}
	for _, mode := range []string{"init", "upgrade", "reset"} {
		cfg := Config{RepoRoot: root, AllowManagedUpdate: mode != "init"}
		if mode == "reset" {
			cfg.ResetData = ".ai-delivery"
		}
		report := AmendReport{}
		cfg.Report = &report
		if err := (Engine{}).Run(cfg); err != nil {
			t.Fatal(mode, err)
		}
		for p, body := range files {
			got, err := os.ReadFile(filepath.Join(root, p))
			if err != nil || !bytes.Equal(got, []byte(body)) {
				t.Fatalf("%s 改写/移动可选原件 %s: %q %v", mode, p, got, err)
			}
		}
		if !report.Empty() {
			t.Fatalf("无 owned 变化生成 IDE 发布/备份: %+v", report)
		}
	}
}

func TestBootstrapDoesNotTouchOptionalHostSymlink(t *testing.T) {
	root, outside := t.TempDir(), t.TempDir()
	original := "{ invalid user config; not kit input }\n"
	writeFixture(t, filepath.Join(outside, "hooks.json"), original)
	if err := os.Symlink(outside, filepath.Join(root, ".codex")); err != nil {
		t.Skipf("无法创建链接: %v", err)
	}
	for _, upgrade := range []bool{false, true} {
		if err := (Engine{}).Run(Config{RepoRoot: root, AllowManagedUpdate: upgrade}); err != nil {
			t.Fatal(err)
		}
	}
	got, err := os.ReadFile(filepath.Join(outside, "hooks.json"))
	if err != nil || string(got) != original {
		t.Fatalf("可选外部配置被碰触: %q %v", got, err)
	}
}
