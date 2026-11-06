package kitassets_test

import (
	kitassets "github.com/s-charvin/ai-delivery-kit"
	"io/fs"
	"path/filepath"
	"testing"
)

func TestReleaseEmbedsNoKitInterpreterCore(t *testing.T) {
	err := fs.WalkDir(kitassets.Embedded, ".", func(p string, d fs.DirEntry, e error) error {
		if e != nil {
			return e
		}
		if d.IsDir() {
			return nil
		}
		switch filepath.Ext(p) {
		case ".py", ".sh":
			t.Errorf("发行包含 kit 解释器入口: %s", p)
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
}
