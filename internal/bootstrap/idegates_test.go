package bootstrap

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
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

func TestWriteAmendableJSONBacksUpExistingSettings(t *testing.T) {
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

	fixed := time.Date(2026, 7, 10, 6, 43, 0, 0, time.UTC)
	report := AmendReport{}
	session := newAmendSession(dir, func() time.Time { return fixed }, &report)
	if err := session.writeAmendableJSON(".claude/settings.json", target, desired); err != nil {
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

	if report.BackupStamp != "2026-07-10T06-43-00Z" {
		t.Fatalf("expected backup stamp, got %#v", report)
	}
	backupFile := filepath.Join(report.BackupDir, ".claude", "settings.json")
	backupBody, err := os.ReadFile(backupFile)
	if err != nil {
		t.Fatalf("expected backup file: %v", err)
	}
	if !strings.Contains(string(backupBody), "echo stop") {
		t.Fatalf("expected original content in backup, got %s", string(backupBody))
	}
}

func TestWriteAmendableJSONSkipsBackupOnCreate(t *testing.T) {
	dir := t.TempDir()
	target := filepath.Join(dir, ".claude", "settings.json")
	desired := []byte(`{"hooks":{}}`)
	report := AmendReport{}
	session := newAmendSession(dir, nil, &report)
	if err := session.writeAmendableJSON(".claude/settings.json", target, desired); err != nil {
		t.Fatalf("writeAmendableJSON failed: %v", err)
	}
	if !report.Empty() {
		t.Fatalf("expected no backup on create, got %#v", report)
	}
	if _, err := os.Stat(filepath.Join(dir, filepath.FromSlash(ideGateBackupRelRoot))); !os.IsNotExist(err) {
		t.Fatalf("expected no backup dir on create, err=%v", err)
	}
}

func TestPruneIDEGateBackupsKeepsThree(t *testing.T) {
	root := t.TempDir()
	backupRoot := filepath.Join(root, filepath.FromSlash(ideGateBackupRelRoot))
	for _, stamp := range []string{"2026-01-01T00-00-00Z", "2026-01-02T00-00-00Z", "2026-01-03T00-00-00Z", "2026-01-04T00-00-00Z"} {
		if err := os.MkdirAll(filepath.Join(backupRoot, stamp), 0o755); err != nil {
			t.Fatal(err)
		}
	}
	if err := pruneIDEGateBackups(root, ideGateBackupKeep); err != nil {
		t.Fatalf("prune failed: %v", err)
	}
	stamps, err := ListIDEGateBackups(root)
	if err != nil {
		t.Fatal(err)
	}
	if len(stamps) != 3 {
		t.Fatalf("expected 3 backups, got %v", stamps)
	}
	if stamps[0] != "2026-01-04T00-00-00Z" || stamps[2] != "2026-01-02T00-00-00Z" {
		t.Fatalf("unexpected stamps after prune: %v", stamps)
	}
	if _, err := os.Stat(filepath.Join(backupRoot, "2026-01-01T00-00-00Z")); !os.IsNotExist(err) {
		t.Fatal("expected oldest backup pruned")
	}
}

func TestRestoreIDEGateBackupRestoresAndBacksUpCurrent(t *testing.T) {
	root := t.TempDir()
	settings := filepath.Join(root, ".claude", "settings.json")
	if err := os.MkdirAll(filepath.Dir(settings), 0o755); err != nil {
		t.Fatal(err)
	}
	current := []byte(`{"hooks":{"Stop":[{"hooks":[{"type":"command","command":"echo current"}]}]}}`)
	if err := os.WriteFile(settings, current, 0o644); err != nil {
		t.Fatal(err)
	}

	stamp := "2026-07-01T00-00-00Z"
	backupFile := filepath.Join(root, filepath.FromSlash(ideGateBackupRelRoot), stamp, ".claude", "settings.json")
	if err := os.MkdirAll(filepath.Dir(backupFile), 0o755); err != nil {
		t.Fatal(err)
	}
	old := []byte(`{"hooks":{"Stop":[{"hooks":[{"type":"command","command":"echo old"}]}]}}`)
	if err := os.WriteFile(backupFile, old, 0o644); err != nil {
		t.Fatal(err)
	}

	fixed := time.Date(2026, 7, 10, 12, 0, 0, 0, time.UTC)
	report, err := RestoreIDEGateBackup(root, stamp, func() time.Time { return fixed })
	if err != nil {
		t.Fatalf("restore failed: %v", err)
	}
	body, err := os.ReadFile(settings)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(body), "echo old") {
		t.Fatalf("expected restored content, got %s", string(body))
	}
	if report.BackupStamp != "2026-07-10T12-00-00Z" {
		t.Fatalf("expected pre-restore backup, got %#v", report)
	}
	preRestore, err := os.ReadFile(filepath.Join(report.BackupDir, ".claude", "settings.json"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(preRestore), "echo current") {
		t.Fatalf("expected current content backed up, got %s", string(preRestore))
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

	report, err := ReapplyIDEGates(root, nil)
	if err != nil {
		t.Fatalf("ReapplyIDEGates failed: %v", err)
	}
	if report.Empty() {
		t.Fatal("expected amend report with backup for existing settings")
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
	report, err := ReapplyIDEGates(filepath.Join(t.TempDir(), "missing"), nil)
	if err != nil {
		t.Fatalf("expected no-op for missing root, got %v", err)
	}
	if !report.Empty() {
		t.Fatalf("expected empty report for missing root, got %#v", report)
	}
}
