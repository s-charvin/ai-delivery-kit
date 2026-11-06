package bootstrap

import "testing"

func TestMetadataPathsRejectPortableEscapeAndInvalidUnicode(t *testing.T) {
	for _, path := range []string{"C:/outside", "C:outside", "a\x00b", "a/{unknown}/file", "a/{req_id.__class__}"} {
		if safeMetadataTemplate(path) {
			t.Errorf("非法布局路径被接受: %q", path)
		}
	}
	if _, err := currentObject([]byte("{\"value\":\"\xff\"}")); err == nil {
		t.Error("非法 UTF-8 被静默替换")
	}
}
