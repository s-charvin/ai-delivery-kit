package bootstrap

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestMergeAmendableJSONPreservesForeignHooks(t *testing.T) {
	existing := []byte(`{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{"type":"command","command":"echo keep-me"}]
      }
    ],
    "Notification": [
      {
        "matcher": "",
        "hooks": [{"type":"command","command":"echo notify"}]
      }
    ]
  },
  "permissions": {"allow": ["Bash"]}
}
`)
	desired := []byte(`{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$(git rev-parse --show-toplevel)/.claude/hooks/validate-ui-contract.sh\"",
            "timeout": 60,
            "statusMessage": "Validating UI acceptance contract"
          }
        ]
      }
    ]
  }
}
`)

	merged, err := mergeAmendableJSON(existing, desired)
	if err != nil {
		t.Fatalf("merge failed: %v", err)
	}

	var obj map[string]any
	if err := json.Unmarshal(merged, &obj); err != nil {
		t.Fatalf("merged json invalid: %v", err)
	}
	if _, ok := obj["permissions"]; !ok {
		t.Fatal("expected existing top-level permissions to be preserved")
	}
	hooks := obj["hooks"].(map[string]any)
	if _, ok := hooks["Notification"]; !ok {
		t.Fatal("expected existing Notification hooks to be preserved")
	}
	post := hooks["PostToolUse"].([]any)
	if len(post) != 2 {
		t.Fatalf("expected 2 PostToolUse groups, got %d: %s", len(post), string(merged))
	}
	if !strings.Contains(string(merged), "echo keep-me") {
		t.Fatalf("expected foreign Bash hook preserved, got %s", string(merged))
	}
	if !strings.Contains(string(merged), "validate-ui-contract.sh") {
		t.Fatalf("expected UI contract gate inserted, got %s", string(merged))
	}
}

func TestMergeAmendableJSONReplacesOwnedGateOnly(t *testing.T) {
	existing := []byte(`{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash old/validate-ui-contract.sh",
            "timeout": 10
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [{"type":"command","command":"echo keep-me"}]
      }
    ]
  }
}
`)
	desired := []byte(`{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$(git rev-parse --show-toplevel)/.claude/hooks/validate-ui-contract.sh\"",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
`)

	merged, err := mergeAmendableJSON(existing, desired)
	if err != nil {
		t.Fatalf("merge failed: %v", err)
	}
	if strings.Contains(string(merged), "old/validate-ui-contract.sh") {
		t.Fatalf("expected owned gate replaced, got %s", string(merged))
	}
	if !strings.Contains(string(merged), "echo keep-me") {
		t.Fatalf("expected foreign hook preserved, got %s", string(merged))
	}
	if strings.Count(string(merged), "validate-ui-contract.sh") != 1 {
		t.Fatalf("expected exactly one owned gate entry, got %s", string(merged))
	}
}

func TestWriteAmendableJSONDoesNotClobberExistingSettings(t *testing.T) {
	dir := t.TempDir()
	target := filepath.Join(dir, ".claude", "settings.json")
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		t.Fatal(err)
	}
	existing := []byte(`{
  "hooks": {
    "Stop": [{"hooks":[{"type":"command","command":"echo stop"}]}]
  },
  "env": {"FOO":"bar"}
}
`)
	if err := os.WriteFile(target, existing, 0o644); err != nil {
		t.Fatal(err)
	}

	desired, err := os.ReadFile(filepath.Join("..", "..", ".claude", "settings.json"))
	if err != nil {
		// fallback to relative from module root via embed source path in repo
		desired = []byte(`{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$(git rev-parse --show-toplevel)/.claude/hooks/validate-ui-contract.sh\"",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
`)
	}

	if err := writeAmendableJSON(target, desired); err != nil {
		t.Fatalf("writeAmendableJSON failed: %v", err)
	}

	body, err := os.ReadFile(target)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(body), `"FOO": "bar"`) && !strings.Contains(string(body), `"FOO":"bar"`) {
		t.Fatalf("expected env preserved, got %s", string(body))
	}
	if !strings.Contains(string(body), "echo stop") {
		t.Fatalf("expected Stop hook preserved, got %s", string(body))
	}
	if !strings.Contains(string(body), "validate-ui-contract.sh") {
		t.Fatalf("expected gate inserted, got %s", string(body))
	}
}

func TestManagedConflictPathsSkipsAmendableJSON(t *testing.T) {
	for _, path := range ManagedConflictPaths() {
		if isAmendableJSONTarget(path) {
			t.Fatalf("amendable JSON should not be a hard conflict: %s", path)
		}
	}
}

func TestReapplyIDEGatesMergesExistingClaudeSettings(t *testing.T) {
	root := t.TempDir()
	settings := filepath.Join(root, ".claude", "settings.json")
	if err := os.MkdirAll(filepath.Dir(settings), 0o755); err != nil {
		t.Fatal(err)
	}
	existing := []byte(`{
  "hooks": {
    "Stop": [{"hooks":[{"type":"command","command":"echo stop-hook"}]}]
  },
  "env": {"KEEP":"yes"}
}
`)
	if err := os.WriteFile(settings, existing, 0o644); err != nil {
		t.Fatal(err)
	}

	if err := ReapplyIDEGates(root); err != nil {
		t.Fatalf("ReapplyIDEGates failed: %v", err)
	}

	body, err := os.ReadFile(settings)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(body), "echo stop-hook") {
		t.Fatalf("expected existing Stop hook preserved, got %s", string(body))
	}
	if !strings.Contains(string(body), `"KEEP"`) {
		t.Fatalf("expected existing env preserved, got %s", string(body))
	}
	if !strings.Contains(string(body), "validate-ui-contract.sh") {
		t.Fatalf("expected UI contract gate merged, got %s", string(body))
	}
	if _, err := os.Stat(filepath.Join(root, ".claude/hooks/validate-ui-contract.sh")); err != nil {
		t.Fatalf("expected adapter script written: %v", err)
	}
}

func TestReapplyIDEGatesNoopsMissingRoot(t *testing.T) {
	if err := ReapplyIDEGates(filepath.Join(t.TempDir(), "missing")); err != nil {
		t.Fatalf("expected no-op for missing root, got %v", err)
	}
}
