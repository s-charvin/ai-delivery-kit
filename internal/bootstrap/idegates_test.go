package bootstrap

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

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
	current := []byte(`{ "third_party": 9007199254740993, "current": true }` + "\n")
	if err := os.WriteFile(settings, current, 0o644); err != nil {
		t.Fatal(err)
	}

	stamp := "2026-07-01T00-00-00Z"
	backupFile := filepath.Join(root, filepath.FromSlash(ideGateBackupRelRoot), stamp, ".claude", "settings.json")
	if err := os.MkdirAll(filepath.Dir(backupFile), 0o755); err != nil {
		t.Fatal(err)
	}
	old := []byte(`{ "third_party": 9007199254740995, "old": true }` + "\n")
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
	if !bytes.Equal(body, old) {
		t.Fatalf("expected restored content, got %s", string(body))
	}
	if report.BackupStamp != "2026-07-10T12-00-00Z" {
		t.Fatalf("expected pre-restore backup, got %#v", report)
	}
	preRestore, err := os.ReadFile(filepath.Join(report.BackupDir, ".claude", "settings.json"))
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(preRestore, current) {
		t.Fatalf("expected current content backed up, got %s", string(preRestore))
	}
}

func TestManagedConflictPathsSkipsAmendableManaged(t *testing.T) {
	for _, path := range ManagedConflictPaths() {
		if isAmendableManagedTarget(path) {
			t.Fatalf("amendable managed target should not be a hard conflict: %s", path)
		}
	}
}

func TestUpsertAgentsMDSectionPreservesForeignContent(t *testing.T) {
	existing := []byte("# Project Agents\n\nKeep me.\n")
	desired := []byte(agentsGateStart + "\n# UI Contract Gate\nrule\n" + agentsGateEnd + "\n")
	merged := upsertAgentsMDSection(existing, desired)
	if !strings.Contains(string(merged), "Keep me.") {
		t.Fatalf("expected foreign content preserved, got %s", merged)
	}
	if !strings.Contains(string(merged), agentsGateStart) || !strings.Contains(string(merged), "UI Contract Gate") {
		t.Fatalf("expected gate section inserted, got %s", merged)
	}

	updated := []byte(agentsGateStart + "\n# UI Contract Gate\nupdated\n" + agentsGateEnd + "\n")
	again := upsertAgentsMDSection(merged, updated)
	if strings.Count(string(again), agentsGateStart) != 1 {
		t.Fatalf("expected single gate section, got %s", again)
	}
	if !strings.Contains(string(again), "updated") {
		t.Fatalf("expected section replaced, got %s", again)
	}
}
