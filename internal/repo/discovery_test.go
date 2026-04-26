package repo

import (
	"os"
	"path/filepath"
	"testing"
)

func TestDiscoverResolvesGitRootFromNestedPath(t *testing.T) {
	root := t.TempDir()
	nested := filepath.Join(root, "app", "src")
	if err := os.Mkdir(filepath.Join(root, ".git"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(nested, 0o755); err != nil {
		t.Fatal(err)
	}

	info, err := Discover(nested)
	if err != nil {
		t.Fatalf("discover failed: %v", err)
	}

	if info.Root != root {
		t.Fatalf("expected root %s, got %s", root, info.Root)
	}
}

func TestDiscoverReportsManagedConflicts(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".git"), 0o755); err != nil {
		t.Fatal(err)
	}
	conflict := filepath.Join(root, ".agents", "skills", "requirement-breakdown")
	if err := os.MkdirAll(conflict, 0o755); err != nil {
		t.Fatal(err)
	}

	info, err := Discover(root)
	if err != nil {
		t.Fatalf("discover failed: %v", err)
	}

	if len(info.ManagedConflicts) != 1 || info.ManagedConflicts[0] != conflict {
		t.Fatalf("expected managed conflict %s, got %#v", conflict, info.ManagedConflicts)
	}
}

func TestDiscoverReportsSeededManagedFileConflicts(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".git"), 0o755); err != nil {
		t.Fatal(err)
	}
	conflict := filepath.Join(root, ".ai-delivery", "meta", "project-binding.json")
	if err := os.MkdirAll(filepath.Dir(conflict), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(conflict, []byte("{}\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	info, err := Discover(root)
	if err != nil {
		t.Fatalf("discover failed: %v", err)
	}

	if len(info.ManagedConflicts) != 1 || info.ManagedConflicts[0] != conflict {
		t.Fatalf("expected seeded managed conflict %s, got %#v", conflict, info.ManagedConflicts)
	}
}

func TestDiscoverRejectsPathOutsideGitRepository(t *testing.T) {
	if _, err := Discover(t.TempDir()); err == nil {
		t.Fatal("expected git repository error, got nil")
	}
}
